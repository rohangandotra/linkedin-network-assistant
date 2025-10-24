# Phase 3B: Search Improvements - REVISED PLAN
## Based on Engineer Feedback

---

## 🎯 Executive Summary

**Original Plan:** Build custom BM25 search engine in Python
**Engineer's Recommendation:** Use production search engine (Typesense/Meilisearch) + local embeddings
**Why:** Ship 10x faster, hit latency targets, lower costs

---

## 📊 Key Changes from Original Plan

| Original | Revised | Why |
|----------|---------|-----|
| Custom BM25 in Python (rank-bm25) | **Typesense or Meilisearch** | Won't hit <100ms at scale; built-in features |
| Levenshtein for typos | **SymSpell or built-in** | O(V) → O(1) performance |
| Repeat tokens for field boosts | **Native field weights** | Cleaner, doesn't distort BM25 |
| OpenAI embeddings ($0.001/search) | **Local bge-small ($0/search)** | Optional: cuts cost to $0 |
| GPT for industry classification | **Offline taxonomy + tiny classifier** | 90% cheaper, consistent |
| Hash entire DataFrame for cache | **contacts_version + normalized query** | Faster, more stable |
| No evaluation framework | **Golden set with MRR@10/Precision@5** | Release gate for quality |

---

## 🏗️ Revised Architecture

### Tier 1: Typesense/Meilisearch (95% of queries)
**Cost:** $0-10/month (self-hosted or cloud)
**Latency:** <50ms
**Handles:** Simple keyword searches

**Features:**
- Native BM25 ranking
- Built-in typo tolerance (edit distance 2)
- Per-field boosts: `name:3, company:2, position:1.5, email:0.5`
- Synonyms (William↔Bill, CEO↔Chief Executive)
- Faceted search (filter by company, seniority)
- Highlighting ("why this result matched")
- Prefix matching (autocomplete)

**Example:**
```python
# Query: "John Google engineer"
typesense.search({
    'q': 'John Google engineer',
    'query_by': 'full_name,company,position,email',
    'query_by_weights': '3,2,1.5,0.5',
    'typo_tolerance': 2,
    'max_hits': 20
})
```

### Tier 2: Semantic Search (30% of queries)
**Cost:** $0 (local) or $0.001 (OpenAI)
**Latency:** <300ms

**Option A: Local Embeddings (RECOMMENDED)**
- Model: `bge-small-en-v1.5` (sentence-transformers)
- Vector store: FAISS or pgvector
- Cost: $0 (runs in your app)
- Latency: 200-300ms

**Option B: OpenAI Embeddings**
- Model: `text-embedding-3-small`
- Cache aggressively
- Cost: ~$0.001/search

**When to use:** Conceptual queries ("ML expert", "creative roles")

### Tier 3: GPT Reasoning (5% of queries)
**Cost:** $0.02/search
**Latency:** 2-5 seconds

**Only use for:**
- Complex multi-criteria: "senior engineers at pre-IPO startups"
- Analytics: "how many people work in finance?"
- True reasoning tasks GPT excels at

**Don't use for:**
- Industry classification (use offline taxonomy)
- Simple title matching (use classifier)
- Keyword searches (use Tier 1)

---

## 🚀 Revised Implementation Plan

### Phase 3B.1: Typesense/Meilisearch Setup (3-5 days)

**Goal:** Replace current GPT-heavy search with fast keyword search

#### Day 1-2: Choose & Deploy Search Engine

**Typesense vs Meilisearch:**

| Feature | Typesense | Meilisearch |
|---------|-----------|-------------|
| Speed | Sub-10ms | Sub-20ms |
| Typo tolerance | ✅ Edit distance 2 | ✅ Edit distance 2 |
| Field weights | ✅ Native | ✅ Native |
| Synonyms | ✅ | ✅ |
| Facets/Filters | ✅ | ✅ |
| Highlighting | ✅ | ✅ |
| Cloud hosting | Typesense Cloud ($0.03/hr) | Meilisearch Cloud (free tier) |
| Self-hosted | Docker image | Docker image |
| License | GPL v3 | MIT |

**Recommendation:** **Meilisearch** (MIT license, easier to start, good free tier)

**Setup:**
```bash
# Option 1: Docker (local dev)
docker run -p 7700:7700 -v $(pwd)/meili_data:/meili_data getmeili/meilisearch

# Option 2: Meilisearch Cloud (production)
# Sign up at https://www.meilisearch.com/cloud
```

#### Day 2-3: Index Contacts

**Create indexing script:**
```python
# search_indexer.py
import meilisearch
import pandas as pd

def index_contacts(user_id, contacts_df):
    """Index user's contacts in Meilisearch"""

    client = meilisearch.Client('http://localhost:7700', 'your-master-key')

    # Create index per user (or shared index with user_id filter)
    index_name = f"contacts_{user_id}"
    index = client.index(index_name)

    # Configure searchable attributes with weights
    index.update_searchable_attributes([
        'full_name',  # Weight: 3
        'company',    # Weight: 2
        'position',   # Weight: 1.5
        'email'       # Weight: 0.5
    ])

    # Configure ranking rules
    index.update_ranking_rules([
        'words',      # Number of matched words
        'typo',       # Fewer typos = better
        'proximity',  # Words close together = better
        'attribute',  # Match in name > company > position
        'sort',
        'exactness'   # Exact match > prefix match
    ])

    # Configure typo tolerance
    index.update_typo_tolerance({
        'enabled': True,
        'minWordSizeForTypos': {
            'oneTypo': 4,   # Allow 1 typo for words ≥4 chars
            'twoTypos': 8   # Allow 2 typos for words ≥8 chars
        }
    })

    # Add documents
    documents = contacts_df.to_dict('records')

    # Add unique ID for each contact
    for i, doc in enumerate(documents):
        doc['id'] = f"{user_id}_{i}"
        doc['user_id'] = user_id

    # Batch index
    index.add_documents(documents)

    return index

# Usage
contacts_df = pd.read_csv('contacts.csv')
index = index_contacts(user_id='user123', contacts_df=contacts_df)
```

#### Day 3-4: Implement Search Function

**Create search module:**
```python
# search_tier1.py
import meilisearch
from typing import List, Dict, Any
import hashlib
import streamlit as st

class Tier1Search:
    """
    Fast keyword search using Meilisearch
    Handles 95% of queries with <50ms latency
    """

    def __init__(self, meili_url='http://localhost:7700', api_key='your-key'):
        self.client = meilisearch.Client(meili_url, api_key)
        self.cache = {}  # In-memory cache (use Redis for production)

    def normalize_query(self, query: str) -> str:
        """Normalize query for consistent caching"""
        return " ".join(query.lower().strip().split())

    def get_cache_key(self, user_id: str, contacts_version: int, query: str) -> str:
        """Generate stable cache key"""
        norm_query = self.normalize_query(query)
        key_str = f"{user_id}:{contacts_version}:{norm_query}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def search(
        self,
        user_id: str,
        query: str,
        contacts_version: int,
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search contacts with Meilisearch

        Args:
            user_id: User ID
            query: Search query
            contacts_version: Version of contact list (for cache invalidation)
            top_k: Number of results

        Returns:
            List of matching contacts with scores
        """

        # Check cache
        cache_key = self.get_cache_key(user_id, contacts_version, query)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Search index
        index = self.client.index(f'contacts_{user_id}')

        results = index.search(
            query,
            {
                'limit': top_k,
                'attributesToHighlight': ['full_name', 'company', 'position'],
                'showMatchesPosition': True,
                'attributesToRetrieve': ['*']
            }
        )

        # Format results
        formatted = []
        for hit in results['hits']:
            formatted.append({
                'contact': hit,
                'relevance_score': hit.get('_rankingScore', 0),
                'matched_fields': self._extract_matched_fields(hit),
                'highlights': hit.get('_formatted', {})
            })

        # Cache results
        self.cache[cache_key] = formatted

        return formatted

    def _extract_matched_fields(self, hit: Dict) -> List[str]:
        """Extract which fields matched from highlight info"""
        matched = []
        formatted = hit.get('_formatted', {})

        for field in ['full_name', 'company', 'position', 'email']:
            if field in formatted and '<em>' in str(formatted.get(field, '')):
                matched.append(field)

        return matched

# Usage in app.py
if 'tier1_search' not in st.session_state:
    st.session_state['tier1_search'] = Tier1Search()

results = st.session_state['tier1_search'].search(
    user_id=st.session_state['user']['id'],
    query="John Google engineer",
    contacts_version=st.session_state.get('contacts_version', 0),
    top_k=20
)
```

#### Day 4-5: Add Advanced Features

**1. Synonyms:**
```python
# Add to indexing
index.update_synonyms({
    'ceo': ['chief executive officer', 'chief executive'],
    'cto': ['chief technology officer', 'chief technical officer'],
    'vp': ['vice president', 'v.p.'],
    'engineer': ['developer', 'swe', 'software engineer'],
    'ml': ['machine learning', 'artificial intelligence', 'ai']
})
```

**2. Name variations:**
```python
# Nickname mapping
NICKNAMES = {
    'william': ['bill', 'will', 'billy'],
    'elizabeth': ['liz', 'beth', 'betty', 'lizzy'],
    'robert': ['rob', 'bob', 'bobby'],
    'michael': ['mike', 'mick', 'mickey'],
    'jonathan': ['jon', 'john'],
    'jennifer': ['jen', 'jenny'],
    # ... add more
}

def expand_name_query(query):
    """Expand query with nickname variants"""
    tokens = query.lower().split()
    expanded = []

    for token in tokens:
        if token in NICKNAMES:
            expanded.extend(NICKNAMES[token])

    return f"{query} {' '.join(expanded)}"
```

**3. Faceted filtering:**
```python
# Add filters to search
results = index.search(
    'engineer',
    {
        'filter': 'company = "Google" OR company = "Meta"',
        'facets': ['company', 'position']
    }
)

# Get facet counts
print(results['facetDistribution'])
# {'company': {'Google': 15, 'Meta': 8}, 'position': {...}}
```

**Success Criteria for Phase 3B.1:**
- ✅ Search completes in <50ms for 95% of queries
- ✅ Typos within 2 edits are handled correctly
- ✅ Results are relevance-ranked
- ✅ Cache hit rate >60%
- ✅ Cost: ~$10/month for hosting

---

### Phase 3B.2: Semantic Search (3-4 days)

**Goal:** Add semantic understanding for conceptual queries

#### Option A: Local Embeddings (RECOMMENDED)

**Day 1: Setup Model**
```bash
pip install sentence-transformers faiss-cpu
```

```python
# search_tier2.py
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import pickle

class Tier2SemanticSearch:
    """
    Semantic search using local embeddings
    Cost: $0, Latency: 200-300ms
    """

    def __init__(self, model_name='BAAI/bge-small-en-v1.5'):
        # Load model (384-dimensional embeddings)
        self.model = SentenceTransformer(model_name)
        self.dimension = 384
        self.indexes = {}  # user_id -> FAISS index
        self.contact_maps = {}  # user_id -> list of contacts

    def build_index(self, user_id: str, contacts_df):
        """Build FAISS index for user's contacts"""

        # Create searchable text for each contact
        texts = []
        for _, row in contacts_df.iterrows():
            text = f"{row['full_name']} {row['company']} {row['position']}"
            texts.append(text)

        # Generate embeddings
        embeddings = self.model.encode(texts, show_progress_bar=True)

        # Build FAISS index (HNSW for fast ANN)
        index = faiss.IndexHNSWFlat(self.dimension, 32)
        index.add(np.array(embeddings).astype('float32'))

        # Store
        self.indexes[user_id] = index
        self.contact_maps[user_id] = contacts_df.to_dict('records')

        # Persist to disk
        faiss.write_index(index, f'faiss_index_{user_id}.bin')
        with open(f'contacts_map_{user_id}.pkl', 'wb') as f:
            pickle.dump(self.contact_maps[user_id], f)

    def search(self, user_id: str, query: str, top_k: int = 20):
        """Semantic search"""

        if user_id not in self.indexes:
            # Load from disk
            self.indexes[user_id] = faiss.read_index(f'faiss_index_{user_id}.bin')
            with open(f'contacts_map_{user_id}.pkl', 'rb') as f:
                self.contact_maps[user_id] = pickle.load(f)

        # Embed query
        query_vector = self.model.encode([query])

        # Search FAISS
        distances, indices = self.indexes[user_id].search(
            query_vector.astype('float32'),
            top_k
        )

        # Format results
        results = []
        for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
            # Convert distance to similarity (cosine similarity ≈ 1 - distance/2)
            similarity = 1 - (dist / 2)

            results.append({
                'contact': self.contact_maps[user_id][idx],
                'semantic_score': float(similarity),
                'rank': i + 1
            })

        return results
```

**Day 2-3: Integrate with Tier 1**

**When to trigger Tier 2:**
```python
def should_use_semantic_search(query: str, tier1_results: List) -> bool:
    """Determine if we need semantic search"""

    # Trigger semantic if:
    # 1. Zero or very few Tier-1 results
    if len(tier1_results) < 3:
        return True

    # 2. Query contains semantic keywords
    semantic_keywords = [
        'expert', 'specialist', 'experienced', 'skilled',
        'passionate', 'creative', 'innovative', 'senior',
        'leader', 'focused on', 'background in'
    ]

    if any(kw in query.lower() for kw in semantic_keywords):
        return True

    # 3. Low confidence from Tier-1
    if tier1_results and tier1_results[0]['relevance_score'] < 0.5:
        return True

    return False
```

**Day 4: Batch Embedding on Upload**

```python
# In auth.py or contacts upload handler
def save_contacts_with_embeddings(user_id, contacts_df):
    """Save contacts and build search indexes"""

    # 1. Save to database
    save_contacts_to_db(user_id, contacts_df)

    # 2. Index in Meilisearch (Tier-1)
    tier1_indexer.index_contacts(user_id, contacts_df)

    # 3. Build embeddings (Tier-2)
    tier2_search.build_index(user_id, contacts_df)

    # 4. Increment contacts_version
    increment_contacts_version(user_id)
```

---

### Phase 3B.3: Hybrid Scoring (2-3 days)

**Goal:** Combine Tier-1 + Tier-2 results intelligently

```python
# search_hybrid.py
from typing import List, Dict
import numpy as np

class HybridSearch:
    """
    Combines BM25 (Tier-1) and semantic (Tier-2) scores
    """

    def __init__(self, tier1: Tier1Search, tier2: Tier2SemanticSearch):
        self.tier1 = tier1
        self.tier2 = tier2

        # Learned weights (can tune with logistic regression)
        self.alpha_bm25 = 0.6
        self.alpha_semantic = 0.4

    def search(self, user_id: str, query: str, contacts_version: int, top_k: int = 20):
        """Hybrid search with intelligent routing"""

        # Step 1: Always try Tier-1 first (fast)
        tier1_results = self.tier1.search(user_id, query, contacts_version, top_k=50)

        # Step 2: Decide if we need Tier-2
        if should_use_semantic_search(query, tier1_results):
            tier2_results = self.tier2.search(user_id, query, top_k=50)

            # Combine scores
            combined = self._combine_results(tier1_results, tier2_results)
        else:
            # Just use Tier-1
            combined = tier1_results

        # Step 3: Re-rank with additional signals
        final = self._rerank(combined, query)

        return final[:top_k]

    def _combine_results(self, tier1_results, tier2_results):
        """Merge and score results from both tiers"""

        # Create lookup by contact ID
        contacts = {}

        # Add Tier-1 results
        for r in tier1_results:
            contact_id = r['contact'].get('id')
            contacts[contact_id] = {
                'contact': r['contact'],
                'bm25_score': r['relevance_score'],
                'semantic_score': 0,
                'matched_fields': r.get('matched_fields', [])
            }

        # Add/merge Tier-2 results
        for r in tier2_results:
            contact_id = r['contact'].get('id')
            if contact_id in contacts:
                contacts[contact_id]['semantic_score'] = r['semantic_score']
            else:
                contacts[contact_id] = {
                    'contact': r['contact'],
                    'bm25_score': 0,
                    'semantic_score': r['semantic_score'],
                    'matched_fields': []
                }

        # Calculate combined score
        results = []
        for contact_id, data in contacts.items():
            # Weighted average
            final_score = (
                self.alpha_bm25 * data['bm25_score'] +
                self.alpha_semantic * data['semantic_score']
            )

            results.append({
                'contact': data['contact'],
                'final_score': final_score,
                'bm25_score': data['bm25_score'],
                'semantic_score': data['semantic_score'],
                'matched_fields': data['matched_fields']
            })

        # Sort by final score
        results.sort(key=lambda x: x['final_score'], reverse=True)

        return results

    def _rerank(self, results, query):
        """Apply additional ranking signals"""

        for r in results:
            # Boost exact matches
            if self._is_exact_match(r['contact'], query):
                r['final_score'] *= 1.5

            # Boost if name matches (people search more important)
            if 'full_name' in r.get('matched_fields', []):
                r['final_score'] *= 1.2

        # Re-sort
        results.sort(key=lambda x: x['final_score'], reverse=True)

        return results

    def _is_exact_match(self, contact, query):
        """Check if query exactly matches any field"""
        query_lower = query.lower()

        for field in ['full_name', 'company', 'position']:
            value = contact.get(field, '').lower()
            if query_lower == value:
                return True

        return False
```

---

### Phase 3B.4: Quality & Evaluation (2-3 days)

**Goal:** Ensure search quality doesn't degrade

#### Day 1: Create Golden Test Set

```python
# test_queries.py
"""
Golden test set for search evaluation
50-200 labeled queries with expected results
"""

GOLDEN_QUERIES = [
    # Name searches
    {
        'query': 'John Smith',
        'expected_top_3': ['john_smith_id_1', 'john_smith_id_2'],
        'category': 'name_exact'
    },
    {
        'query': 'Jon Smith',  # Nickname
        'expected_top_3': ['john_smith_id_1'],
        'category': 'name_fuzzy'
    },

    # Company searches
    {
        'query': 'Google engineer',
        'expected_top_3': ['person1', 'person2', 'person3'],
        'category': 'company_position'
    },
    {
        'query': 'Gogle',  # Typo
        'expected_in_top_10': ['person_at_google_1'],
        'category': 'typo'
    },

    # Semantic searches
    {
        'query': 'machine learning expert',
        'expected_top_5': ['ml_engineer_1', 'ai_researcher_1', 'data_scientist_1'],
        'category': 'semantic'
    },
    {
        'query': 'creative roles',
        'expected_top_5': ['designer_1', 'artist_1', 'content_creator_1'],
        'category': 'semantic'
    },

    # Complex queries
    {
        'query': 'senior engineers at tech companies',
        'expected_top_10': ['senior_eng_google', 'vp_meta', 'staff_eng_amazon'],
        'category': 'complex'
    },

    # Edge cases
    {
        'query': 'a',  # Single char
        'expected_count': 0,
        'category': 'edge_case'
    },
    {
        'query': '',  # Empty
        'expected_count': 0,
        'category': 'edge_case'
    }
]
```

#### Day 2: Implement Evaluation Metrics

```python
# search_evaluator.py
from typing import List, Dict
import numpy as np

class SearchEvaluator:
    """
    Evaluate search quality using golden test set
    """

    def __init__(self, golden_queries: List[Dict]):
        self.golden_queries = golden_queries

    def evaluate(self, search_engine) -> Dict[str, float]:
        """Run evaluation and return metrics"""

        results = {
            'mrr': [],  # Mean Reciprocal Rank
            'precision_at_5': [],
            'recall_at_10': [],
            'zero_result_rate': []
        }

        for test_case in self.golden_queries:
            query = test_case['query']

            # Run search
            search_results = search_engine.search(query=query, top_k=20)

            # Extract result IDs
            result_ids = [r['contact']['id'] for r in search_results]

            # Calculate MRR
            expected_ids = test_case.get('expected_top_3', [])
            if expected_ids:
                mrr = self._calculate_mrr(result_ids, expected_ids)
                results['mrr'].append(mrr)

            # Calculate Precision@5
            expected_top_5 = test_case.get('expected_top_5', expected_ids)
            if expected_top_5:
                p5 = self._calculate_precision_at_k(result_ids[:5], expected_top_5)
                results['precision_at_5'].append(p5)

            # Zero results check
            expected_count = test_case.get('expected_count')
            if expected_count is not None:
                has_zero_results = (len(search_results) == 0)
                should_have_zero = (expected_count == 0)
                results['zero_result_rate'].append(has_zero_results == should_have_zero)

        # Aggregate metrics
        metrics = {
            'MRR@10': np.mean(results['mrr']) if results['mrr'] else 0,
            'Precision@5': np.mean(results['precision_at_5']) if results['precision_at_5'] else 0,
            'Zero Result Accuracy': np.mean(results['zero_result_rate']) if results['zero_result_rate'] else 0
        }

        return metrics

    def _calculate_mrr(self, results: List[str], expected: List[str]) -> float:
        """Mean Reciprocal Rank"""
        for i, result_id in enumerate(results):
            if result_id in expected:
                return 1.0 / (i + 1)
        return 0.0

    def _calculate_precision_at_k(self, results: List[str], expected: List[str]) -> float:
        """Precision at K"""
        if not results:
            return 0.0

        relevant = sum(1 for r in results if r in expected)
        return relevant / len(results)
```

#### Day 3: Set Up Nightly Evaluation

```python
# run_evaluation.py
"""
Nightly evaluation script
Run this before deploying any search changes
"""

def run_nightly_eval():
    # Load test set
    from test_queries import GOLDEN_QUERIES

    # Initialize search engines
    tier1 = Tier1Search()
    tier2 = Tier2SemanticSearch()
    hybrid = HybridSearch(tier1, tier2)

    # Evaluate
    evaluator = SearchEvaluator(GOLDEN_QUERIES)

    print("Evaluating Tier-1 (BM25)...")
    tier1_metrics = evaluator.evaluate(tier1)

    print("Evaluating Hybrid (BM25 + Semantic)...")
    hybrid_metrics = evaluator.evaluate(hybrid)

    # Print results
    print("\n=== EVALUATION RESULTS ===")
    print(f"Tier-1 MRR@10: {tier1_metrics['MRR@10']:.3f}")
    print(f"Hybrid MRR@10: {hybrid_metrics['MRR@10']:.3f}")

    # Check thresholds (release gate)
    if hybrid_metrics['MRR@10'] < 0.7:
        print("⚠️  WARNING: MRR below threshold (0.7)")
        print("   Do not deploy!")
        return False

    if hybrid_metrics['Precision@5'] < 0.8:
        print("⚠️  WARNING: Precision@5 below threshold (0.8)")
        print("   Do not deploy!")
        return False

    print("✅ All quality checks passed!")
    return True

if __name__ == '__main__':
    run_nightly_eval()
```

---

## 📊 Cost & Performance Estimates (Revised)

### Before (Current State):
- **Cost per search:** $0.025 (all GPT)
- **Latency:** 2-5 seconds
- **Monthly cost (100 users, 10 searches/day):** $750

### After (Revised Plan):

**Tier-1 (Meilisearch): 70%**
- Cost: $0
- Latency: <50ms
- Monthly searches: 21,000
- Monthly cost: $0

**Tier-2 (Local embeddings): 25%**
- Cost: $0 (local model)
- Latency: <300ms
- Monthly searches: 7,500
- Monthly cost: $0

**Tier-3 (GPT): 5%**
- Cost: $0.025/search
- Latency: 2-5 seconds
- Monthly searches: 1,500
- Monthly cost: $37.50

**Total Monthly Cost:** **$37.50** (95% reduction ✅)
**Average Latency:** **~120ms** (25x faster ✅)

---

## 🎯 Success Criteria

Phase 3B is successful when:

- ✅ 95% of searches complete in <100ms
- ✅ Cost reduced by >90% (from $750/mo → <$75/mo)
- ✅ Typos handled correctly (edit distance ≤2)
- ✅ MRR@10 >0.7 on golden test set
- ✅ Precision@5 >0.8 on golden test set
- ✅ Zero-result rate <5%
- ✅ Cache hit rate >60%

---

## 🚀 Next Steps

1. **Choose search engine:** Meilisearch (recommended) or Typesense
2. **Start Phase 3B.1:** Set up Meilisearch + basic indexing (3-5 days)
3. **Add Phase 3B.2:** Local embeddings with bge-small (3-4 days)
4. **Implement Phase 3B.3:** Hybrid scoring (2-3 days)
5. **Create Phase 3B.4:** Golden test set + evaluation (2-3 days)

**Total time:** 10-15 days
**Total cost:** ~$10/month (hosting)

---

## 📞 Questions?

Your engineer offered to help with:
- Minimal Typesense/Meilisearch schema + indexing script
- Tiny hybrid ranker with logistic weights
- Golden-set harness (MRR/NDCG) for CI

**Should we proceed with Meilisearch or would you prefer Typesense?**

---

**Last Updated:** 2025-10-24
**Status:** Ready to implement based on engineer feedback
