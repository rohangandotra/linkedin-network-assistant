"""
Advanced Search Engine for LinkedIn Network Assistant
Implements 3-tier hybrid search based on engineer recommendations

Tier 1: SQLite FTS5 + SymSpell (95% of queries, <50ms)
Tier 2: Local embeddings + FAISS (30% of queries, <300ms)
Tier 3: GPT reasoning (5% of queries, 2-5s)
"""

import sqlite3
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
import re
import hashlib
import json
from datetime import datetime
import os

# Tier-1 imports
try:
    from symspellpy import SymSpell, Verbosity
    HAS_SYMSPELL = True
except ImportError:
    HAS_SYMSPELL = False
    print("⚠️  SymSpell not available. Install with: pip install symspellpy")

# Tier-2 imports
try:
    from sentence_transformers import SentenceTransformer
    import faiss
    HAS_EMBEDDINGS = True
except ImportError:
    HAS_EMBEDDINGS = False
    print("⚠️  Embeddings not available. Install with: pip install sentence-transformers faiss-cpu")


# ============================================
# TIER 1: FAST KEYWORD SEARCH (SQLite FTS5)
# ============================================

class Tier1KeywordSearch:
    """
    Fast keyword search using SQLite FTS5
    Features: BM25 ranking, field boosts, prefix matching
    Latency: <50ms
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path
        self.conn = None
        self.symspell = None
        self.current_user_id = None

        # Initialize SymSpell for typo correction
        if HAS_SYMSPELL:
            self._init_symspell()

    def _init_symspell(self):
        """Initialize SymSpell for fast fuzzy matching"""
        self.symspell = SymSpell(max_dictionary_edit_distance=2, prefix_length=7)

    def _get_db_path(self, user_id: str) -> str:
        """Get database file path for user"""
        if self.db_path:
            return self.db_path
        return f'search_index_{user_id}.db'

    def index_exists(self, user_id: str) -> bool:
        """Check if index exists on disk"""
        db_file = self._get_db_path(user_id)
        if db_file == ':memory:':
            return False
        return os.path.exists(db_file)

    def load_index(self, user_id: str) -> bool:
        """
        Load existing index from disk

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            db_file = self._get_db_path(user_id)
            if not os.path.exists(db_file):
                return False

            # Connect to existing database
            self.conn = sqlite3.connect(db_file)
            self.current_user_id = user_id

            # Verify table exists
            cursor = self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='contacts_fts'"
            )
            if not cursor.fetchone():
                return False

            print(f"✅ Loaded FTS5 index from disk for user {user_id}")
            return True

        except Exception as e:
            print(f"⚠️  Failed to load FTS5 index: {e}")
            return False

    def build_index(self, user_id: str, contacts_df: pd.DataFrame):
        """
        Build FTS5 index for user's contacts

        Args:
            user_id: User ID
            contacts_df: DataFrame with contacts
        """
        # Create connection to disk-based database
        db_file = self._get_db_path(user_id)
        self.conn = sqlite3.connect(db_file)
        self.current_user_id = user_id

        # Create FTS5 table with field weights
        # FTS5 supports BM25 ranking natively
        self.conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS contacts_fts USING fts5(
                id,
                full_name,
                company,
                position,
                email,
                tokenize='porter unicode61'
            )
        """)

        # Clear existing data
        self.conn.execute("DELETE FROM contacts_fts")

        # Insert contacts
        for idx, row in contacts_df.iterrows():
            self.conn.execute("""
                INSERT INTO contacts_fts (id, full_name, company, position, email)
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(idx),
                row.get('full_name', ''),
                row.get('company', ''),
                row.get('position', ''),
                row.get('email', '')
            ))

        self.conn.commit()

        # Build SymSpell dictionary from contact data
        if self.symspell:
            self._build_symspell_dict(contacts_df)

    def _build_symspell_dict(self, contacts_df: pd.DataFrame):
        """Build SymSpell dictionary from contacts"""
        # Collect all unique terms
        terms = set()

        for col in ['full_name', 'company', 'position']:
            if col in contacts_df.columns:
                for val in contacts_df[col].dropna():
                    # Tokenize
                    tokens = re.findall(r'\w+', str(val).lower())
                    terms.update(tokens)

        # Add to SymSpell
        for term in terms:
            self.symspell.create_dictionary_entry(term, 1)

    def search(
        self,
        query: str,
        contacts_df: pd.DataFrame,
        top_k: int = 20,
        enable_typo_correction: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search contacts using FTS5

        Args:
            query: Search query
            contacts_df: Original contacts DataFrame (for result enrichment)
            top_k: Number of results
            enable_typo_correction: Use SymSpell for typo correction

        Returns:
            List of search results with scores
        """
        if not self.conn:
            return []

        # Normalize query
        query_normalized = self._normalize_query(query)

        if not query_normalized:
            return []

        # Apply typo correction
        if enable_typo_correction and self.symspell:
            query_normalized = self._correct_typos(query_normalized)

        # Build FTS5 query with field boosts
        # FTS5 syntax: field:term for field-specific search
        fts_query = self._build_fts_query(query_normalized)

        try:
            # Execute FTS5 search with BM25 ranking
            cursor = self.conn.execute(f"""
                SELECT
                    id,
                    full_name,
                    company,
                    position,
                    email,
                    bm25(contacts_fts, 3.0, 2.0, 1.5, 0.5) as score
                FROM contacts_fts
                WHERE contacts_fts MATCH ?
                ORDER BY score DESC
                LIMIT ?
            """, (fts_query, top_k))

            results = []
            for row in cursor.fetchall():
                contact_id, name, company, position, email, score = row

                # Get full contact data from DataFrame
                try:
                    idx = int(contact_id)
                    if idx < len(contacts_df):
                        contact_data = contacts_df.iloc[idx].to_dict()
                    else:
                        contact_data = {
                            'full_name': name,
                            'company': company,
                            'position': position,
                            'email': email
                        }
                except:
                    contact_data = {
                        'full_name': name,
                        'company': company,
                        'position': position,
                        'email': email
                    }

                # Identify matched fields
                matched_fields = self._identify_matched_fields(
                    contact_data, query_normalized
                )

                results.append({
                    'contact': contact_data,
                    'relevance_score': abs(float(score)),  # FTS5 BM25 returns negative scores
                    'matched_fields': matched_fields,
                    'search_tier': 'tier1_keyword'
                })

            return results

        except Exception as e:
            print(f"FTS5 search error: {e}")
            return []

    def _normalize_query(self, query: str) -> str:
        """Normalize query string"""
        # Lowercase, trim, collapse spaces
        return ' '.join(query.lower().strip().split())

    def _correct_typos(self, query: str) -> str:
        """Correct typos using SymSpell"""
        if not self.symspell:
            return query

        tokens = query.split()
        corrected = []

        for token in tokens:
            # Lookup corrections
            suggestions = self.symspell.lookup(
                token,
                Verbosity.CLOSEST,
                max_edit_distance=2
            )

            if suggestions:
                corrected.append(suggestions[0].term)
            else:
                corrected.append(token)

        return ' '.join(corrected)

    def _build_fts_query(self, query: str) -> str:
        """
        Build FTS5 query with field boosting
        FTS5 uses BM25 weights in the bm25() function
        """
        # For now, simple query
        # Could enhance with: field:term syntax, phrase matching, etc.
        return query

    def _identify_matched_fields(self, contact: Dict, query: str) -> List[str]:
        """Identify which fields matched the query"""
        matched = []
        query_terms = set(query.lower().split())

        for field in ['full_name', 'company', 'position', 'email']:
            if field in contact and contact[field]:
                value_terms = set(str(contact[field]).lower().split())
                if query_terms & value_terms:  # Intersection
                    matched.append(field)

        return matched

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# ============================================
# TIER 2: SEMANTIC SEARCH (Local Embeddings)
# ============================================

class Tier2SemanticSearch:
    """
    Semantic search using local embeddings
    Model: bge-small-en-v1.5 (384 dimensions)
    Cost: $0 (local), Latency: 200-300ms
    """

    def __init__(self, model_name: str = 'BAAI/bge-small-en-v1.5', cache_dir: str = './models'):
        self.model_name = model_name
        self.cache_dir = cache_dir
        self.model = None
        self.dimension = 384
        self.indexes = {}  # user_id -> FAISS index
        self.contact_maps = {}  # user_id -> list of contacts

        if HAS_EMBEDDINGS:
            self._init_model()

    def _init_model(self):
        """Initialize sentence transformer model"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            self.model = SentenceTransformer(self.model_name, cache_folder=self.cache_dir)
            print(f"✅ Loaded embedding model: {self.model_name}")
        except Exception as e:
            print(f"❌ Failed to load embedding model: {e}")
            self.model = None

    def index_exists(self, user_id: str) -> bool:
        """Check if index exists on disk"""
        index_file = f'faiss_index_{user_id}.bin'
        contact_map_file = f'contact_map_{user_id}.json'
        return os.path.exists(index_file) and os.path.exists(contact_map_file)

    def load_index(self, user_id: str) -> bool:
        """
        Load existing index from disk

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            index_file = f'faiss_index_{user_id}.bin'
            contact_map_file = f'contact_map_{user_id}.json'

            if not os.path.exists(index_file) or not os.path.exists(contact_map_file):
                return False

            # Load FAISS index
            self.indexes[user_id] = faiss.read_index(index_file)

            # Load contact map
            with open(contact_map_file, 'r') as f:
                self.contact_maps[user_id] = json.load(f)

            print(f"✅ Loaded semantic index from disk for user {user_id}")
            return True

        except Exception as e:
            print(f"⚠️  Failed to load semantic index: {e}")
            return False

    def build_index(self, user_id: str, contacts_df: pd.DataFrame):
        """
        Build FAISS index for user's contacts

        Args:
            user_id: User ID
            contacts_df: DataFrame with contacts
        """
        if not self.model:
            print("⚠️  Embedding model not available")
            return

        # Create searchable text for each contact
        texts = []
        for _, row in contacts_df.iterrows():
            # Combine fields with importance weighting (repeat high-value fields)
            parts = []

            # Name (3x weight)
            if pd.notna(row.get('full_name')):
                parts.extend([row['full_name']] * 3)

            # Company (2x weight)
            if pd.notna(row.get('company')):
                parts.extend([row['company']] * 2)

            # Position (1.5x ≈ 2x for simplicity)
            if pd.notna(row.get('position')):
                parts.extend([row['position']] * 2)

            text = ' '.join(parts)
            texts.append(text)

        try:
            # Generate embeddings
            print(f"Generating embeddings for {len(texts)} contacts...")
            embeddings = self.model.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True
            )

            # Build FAISS index (HNSW for fast ANN search)
            index = faiss.IndexHNSWFlat(self.dimension, 32)
            index.add(embeddings.astype('float32'))

            # Store in memory
            self.indexes[user_id] = index
            self.contact_maps[user_id] = contacts_df.to_dict('records')

            # Persist to disk
            index_file = f'faiss_index_{user_id}.bin'
            faiss.write_index(index, index_file)

            # Persist contact map to disk
            contact_map_file = f'contact_map_{user_id}.json'
            with open(contact_map_file, 'w') as f:
                json.dump(self.contact_maps[user_id], f)

            print(f"✅ Built semantic index: {len(texts)} contacts")

        except Exception as e:
            print(f"❌ Failed to build semantic index: {e}")

    def search(
        self,
        user_id: str,
        query: str,
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Semantic search using embeddings

        Args:
            user_id: User ID
            query: Search query
            top_k: Number of results

        Returns:
            List of search results with semantic scores
        """
        if not self.model:
            return []

        # Load index if not in memory
        if user_id not in self.indexes:
            try:
                index_file = f'faiss_index_{user_id}.bin'
                self.indexes[user_id] = faiss.read_index(index_file)
            except:
                print(f"⚠️  No semantic index for user {user_id}")
                return []

        if user_id not in self.contact_maps:
            print(f"⚠️  No contact map for user {user_id}")
            return []

        try:
            # Embed query
            query_vector = self.model.encode([query], convert_to_numpy=True)

            # Search FAISS
            distances, indices = self.indexes[user_id].search(
                query_vector.astype('float32'),
                top_k
            )

            # Format results
            results = []
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx == -1:  # FAISS returns -1 for empty slots
                    continue

                # Convert L2 distance to similarity score (0-1)
                # For normalized vectors: similarity ≈ 1 - (distance² / 4)
                similarity = max(0, 1 - (dist / 4))

                results.append({
                    'contact': self.contact_maps[user_id][idx],
                    'semantic_score': float(similarity),
                    'search_tier': 'tier2_semantic',
                    'rank': i + 1
                })

            return results

        except Exception as e:
            print(f"❌ Semantic search error: {e}")
            return []


# ============================================
# TIER 3: GPT REASONING (Minimal Usage)
# ============================================

class Tier3GPTSearch:
    """
    GPT-powered search for complex queries
    Only use when Tier 1 & 2 can't handle the query
    Cost: $0.02/search, Latency: 2-5s
    """

    def __init__(self, openai_client=None):
        self.client = openai_client

    def should_use_gpt(self, query: str, tier1_results: List, tier2_results: List) -> bool:
        """
        Determine if GPT is needed

        Only use GPT for:
        - Analytics queries ("how many", "breakdown")
        - Complex multi-criteria ("senior engineers at pre-IPO startups")
        - Industry classification ("who works in tech?")
        """
        query_lower = query.lower()

        # Analytics keywords
        analytics_keywords = [
            'how many', 'count', 'breakdown', 'analyze',
            'distribution', 'percentage', 'statistics'
        ]
        if any(kw in query_lower for kw in analytics_keywords):
            return True

        # Complex multi-criteria (multiple filters)
        filter_keywords = ['and', 'or', 'at', 'in', 'with']
        complexity_score = sum(1 for kw in filter_keywords if kw in query_lower.split())
        if complexity_score >= 3:
            return True

        # Industry/category queries
        industry_keywords = [
            'in tech', 'in finance', 'in healthcare', 'in consulting',
            'at startups', 'at big companies', 'at faang'
        ]
        if any(kw in query_lower for kw in industry_keywords):
            return True

        # Low confidence from Tier 1 & 2
        if not tier1_results and not tier2_results:
            return False  # No results at all - GPT won't help

        return False

    def search(
        self,
        query: str,
        contacts_df: pd.DataFrame,
        existing_results: List = None
    ) -> Dict[str, Any]:
        """
        Use GPT for complex search/analytics

        Returns:
            Dict with search results or analytics
        """
        if not self.client:
            return {'type': 'error', 'message': 'GPT client not available'}

        # This would call the existing extract_search_intent function
        # For now, return placeholder
        return {
            'type': 'gpt_search',
            'message': 'GPT search not yet implemented in this tier'
        }


# ============================================
# NAME VARIATIONS & SYNONYMS
# ============================================

# Nickname mappings
NICKNAMES = {
    'william': ['bill', 'will', 'billy', 'willy'],
    'elizabeth': ['liz', 'beth', 'betty', 'lizzy', 'eliza'],
    'robert': ['rob', 'bob', 'bobby', 'robbie'],
    'michael': ['mike', 'mick', 'mickey'],
    'jonathan': ['jon', 'john', 'jonny'],
    'jennifer': ['jen', 'jenny', 'jenn'],
    'richard': ['rick', 'dick', 'ricky', 'rich'],
    'charles': ['charlie', 'chuck', 'chas'],
    'christopher': ['chris', 'topher'],
    'daniel': ['dan', 'danny'],
    'david': ['dave', 'davy'],
    'james': ['jim', 'jimmy', 'jamie'],
    'joseph': ['joe', 'joey'],
    'matthew': ['matt', 'matty'],
    'nicholas': ['nick', 'nicky'],
    'thomas': ['tom', 'tommy'],
    'anthony': ['tony'],
    'andrew': ['andy', 'drew'],
    'katherine': ['kate', 'kathy', 'katie', 'kat'],
    'margaret': ['maggie', 'meg', 'peggy'],
    'patricia': ['pat', 'patty', 'tricia'],
    'susan': ['sue', 'susie', 'suzy'],
    'timothy': ['tim', 'timmy'],
}

# Job title synonyms
TITLE_SYNONYMS = {
    'engineer': ['developer', 'swe', 'software engineer', 'programmer', 'coder'],
    'manager': ['mgr', 'lead', 'head of', 'director'],
    'vp': ['vice president', 'v.p.', 'vice-president'],
    'ceo': ['chief executive officer', 'chief executive'],
    'cto': ['chief technology officer', 'chief technical officer'],
    'cfo': ['chief financial officer'],
    'coo': ['chief operating officer'],
    'ml': ['machine learning', 'artificial intelligence', 'ai'],
    'data scientist': ['data analyst', 'analytics'],
}

def expand_query_with_variations(query: str) -> str:
    """Expand query with nicknames and synonyms"""
    tokens = query.lower().split()
    expansions = []

    for token in tokens:
        # Add nickname variations
        if token in NICKNAMES:
            expansions.extend(NICKNAMES[token])

        # Add title synonyms
        for canonical, synonyms in TITLE_SYNONYMS.items():
            if token in synonyms or token == canonical:
                expansions.extend([canonical] + synonyms)
                break

    # Return original + expansions
    if expansions:
        return f"{query} {' '.join(set(expansions))}"
    return query


# ============================================
# CACHING SYSTEM
# ============================================

class SearchCache:
    """
    Intelligent search caching
    Uses contacts_version + normalized query for stable cache keys
    """

    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0

    def get_cache_key(self, user_id: str, contacts_version: int, query: str) -> str:
        """Generate stable cache key"""
        # Normalize query
        norm_query = ' '.join(query.lower().strip().split())

        # Hash
        key_str = f"{user_id}:{contacts_version}:{norm_query}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get(self, user_id: str, contacts_version: int, query: str) -> Optional[List]:
        """Get cached results"""
        key = self.get_cache_key(user_id, contacts_version, query)

        if key in self.cache:
            self.hits += 1
            return self.cache[key]

        self.misses += 1
        return None

    def set(self, user_id: str, contacts_version: int, query: str, results: List):
        """Cache results"""
        key = self.get_cache_key(user_id, contacts_version, query)

        # Evict oldest if full
        if len(self.cache) >= self.max_size:
            # Simple FIFO eviction (could use LRU)
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[key] = results

    def invalidate(self, user_id: str):
        """Invalidate all cache for a user"""
        # In production, would use prefix matching
        # For now, just clear everything
        self.cache.clear()

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total = self.hits + self.misses
        hit_rate = self.hits / total if total > 0 else 0

        return {
            'hits': self.hits,
            'misses': self.misses,
            'hit_rate': hit_rate,
            'size': len(self.cache)
        }


# Export main classes
__all__ = [
    'Tier1KeywordSearch',
    'Tier2SemanticSearch',
    'Tier3GPTSearch',
    'SearchCache',
    'expand_query_with_variations',
    'NICKNAMES',
    'TITLE_SYNONYMS'
]
