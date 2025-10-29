"""
Candidate Generation for 6th Degree Search
Integrates query parser with FTS5/FAISS search indexes

Architecture:
1. Parse query → extract structured entities (personas, companies, industries, geos)
2. Generate candidates from FTS5 (lexical matching)
3. Generate candidates from FAISS (semantic matching)
4. Union + deduplicate with provenance tracking
5. Return ranked candidates for feature factory
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Set, Tuple
import time

from services.query_parser import parse_query
from search_engine import Tier1KeywordSearch, Tier2SemanticSearch


class CandidateGenerator:
    """
    Generates search candidates using parsed query structure

    Features:
    - Structured query understanding (personas, companies, industries, geos)
    - Dual recall: FTS5 (keyword) + FAISS (semantic)
    - Candidate union with deduplication
    - Provenance tracking (which index found which candidate)
    """

    def __init__(self, openai_client=None):
        """
        Initialize candidate generator

        Args:
            openai_client: Optional OpenAI client for LLM fallback parser
        """
        self.tier1 = Tier1KeywordSearch()
        self.tier2 = Tier2SemanticSearch()
        self.openai_client = openai_client

    def indexes_exist(self, user_id: str) -> bool:
        """
        Check if indexes exist on disk for user

        Args:
            user_id: User ID

        Returns:
            True if both FTS5 and FAISS indexes exist
        """
        return self.tier1.index_exists(user_id) and self.tier2.index_exists(user_id)

    def load_indexes(self, user_id: str) -> bool:
        """
        Load existing indexes from disk

        Args:
            user_id: User ID

        Returns:
            True if loaded successfully, False otherwise
        """
        print(f"Loading search indexes for user {user_id}...")

        # Load Tier-1 (FTS5)
        tier1_loaded = self.tier1.load_index(user_id)

        # Load Tier-2 (FAISS)
        tier2_loaded = self.tier2.load_index(user_id)

        if tier1_loaded and tier2_loaded:
            print("✅ Search indexes loaded from disk successfully")
            return True
        else:
            print("⚠️  Failed to load one or more indexes")
            return False

    def build_indexes(self, user_id: str, contacts_df: pd.DataFrame):
        """
        Build search indexes for a user

        Args:
            user_id: User ID
            contacts_df: Contacts DataFrame
        """
        print(f"Building search indexes for user {user_id}...")

        # Build Tier-1 (FTS5)
        print("  • Building Tier-1 keyword index (SQLite FTS5)...")
        self.tier1.build_index(user_id, contacts_df)

        # Build Tier-2 (embeddings + FAISS)
        print("  • Building Tier-2 semantic index (FAISS HNSW)...")
        self.tier2.build_index(user_id, contacts_df)

        print("✅ Search indexes built successfully")

    def generate_candidates(
        self,
        user_id: str,
        query: str,
        contacts_df: pd.DataFrame,
        top_k: int = 100,
        use_semantic: bool = True
    ) -> Dict[str, Any]:
        """
        Generate search candidates from query

        Args:
            user_id: User ID
            query: Natural language search query
            contacts_df: Contacts DataFrame
            top_k: Number of candidates to generate
            use_semantic: Enable semantic search (Tier-2)

        Returns:
            Dict with candidates and metadata:
            {
                'candidates': [...],  # List of candidate dicts
                'parsed_query': {...},  # Parsed query structure
                'provenance': {...},  # Which sources found which candidates
                'metrics': {...}  # Performance metrics
            }
        """
        start_time = time.time()

        # Step 1: Parse query
        parse_start = time.time()
        parsed_query = parse_query(query, self.openai_client)
        parse_time = (time.time() - parse_start) * 1000

        # Step 2: Generate lexical candidates (FTS5)
        tier1_start = time.time()
        tier1_candidates = self._generate_lexical_candidates(
            query, parsed_query, contacts_df, top_k
        )
        tier1_time = (time.time() - tier1_start) * 1000

        # Step 3: Generate semantic candidates (FAISS) if enabled
        tier2_candidates = []
        tier2_time = 0

        if use_semantic:
            tier2_start = time.time()
            tier2_candidates = self._generate_semantic_candidates(
                user_id, query, parsed_query, top_k
            )
            tier2_time = (time.time() - tier2_start) * 1000

        # Step 4: Union + deduplicate
        union_start = time.time()
        candidates, provenance = self._union_candidates(
            tier1_candidates, tier2_candidates, top_k
        )
        union_time = (time.time() - union_start) * 1000

        total_time = (time.time() - start_time) * 1000

        return {
            'candidates': candidates,
            'parsed_query': parsed_query,
            'provenance': provenance,
            'metrics': {
                'total_latency_ms': total_time,
                'parse_time_ms': parse_time,
                'tier1_time_ms': tier1_time,
                'tier2_time_ms': tier2_time,
                'union_time_ms': union_time,
                'tier1_count': len(tier1_candidates),
                'tier2_count': len(tier2_candidates),
                'final_count': len(candidates)
            }
        }

    def _generate_lexical_candidates(
        self,
        query: str,
        parsed_query: Dict,
        contacts_df: pd.DataFrame,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Generate candidates using FTS5 lexical search

        Args:
            query: Original query
            parsed_query: Parsed query structure
            contacts_df: Contacts DataFrame
            top_k: Number of candidates

        Returns:
            List of candidates with FTS5 scores
        """
        # Build enhanced query from parsed structure
        enhanced_query = self._build_enhanced_query(parsed_query)

        # Search FTS5
        results = self.tier1.search(
            enhanced_query if enhanced_query else query,
            contacts_df,
            top_k=top_k
        )

        return results

    def _generate_semantic_candidates(
        self,
        user_id: str,
        query: str,
        parsed_query: Dict,
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Generate candidates using FAISS semantic search

        Args:
            user_id: User ID
            query: Original query
            parsed_query: Parsed query structure
            top_k: Number of candidates

        Returns:
            List of candidates with semantic scores
        """
        # Build semantic query (could be enhanced with parsed structure)
        semantic_query = self._build_semantic_query(parsed_query)

        # Search FAISS
        results = self.tier2.search(
            user_id,
            semantic_query if semantic_query else query,
            top_k=top_k
        )

        return results

    def _build_enhanced_query(self, parsed_query: Dict) -> str:
        """
        Build enhanced query from parsed structure for FTS5

        Args:
            parsed_query: Parsed query structure

        Returns:
            Enhanced query string
        """
        targets = parsed_query.get('targets', {})
        parts = []

        # Add personas
        personas = targets.get('personas', [])
        if personas:
            parts.extend(personas)

        # Add companies
        companies = targets.get('companies', [])
        if companies:
            parts.extend(companies)

        # Add industries
        industries = targets.get('industries', [])
        if industries:
            parts.extend(industries)

        # Add geos
        geos = targets.get('geos', [])
        if geos:
            parts.extend(geos)

        if not parts:
            # Return expanded query if available
            return parsed_query.get('expanded_query', parsed_query.get('original_query', ''))

        return ' '.join(parts)

    def _build_semantic_query(self, parsed_query: Dict) -> str:
        """
        Build semantic query from parsed structure for FAISS

        Args:
            parsed_query: Parsed query structure

        Returns:
            Semantic query string
        """
        # For semantic search, use more natural language
        targets = parsed_query.get('targets', {})
        parts = []

        personas = targets.get('personas', [])
        if personas:
            parts.append(' '.join(personas))

        companies = targets.get('companies', [])
        if companies:
            parts.append(' '.join(companies))

        industries = targets.get('industries', [])
        if industries:
            parts.append(' '.join(industries))

        geos = targets.get('geos', [])
        if geos:
            parts.append(' '.join(geos))

        if not parts:
            return parsed_query.get('original_query', '')

        return ' '.join(parts)

    def _union_candidates(
        self,
        tier1_candidates: List[Dict],
        tier2_candidates: List[Dict],
        top_k: int
    ) -> Tuple[List[Dict], Dict[str, Any]]:
        """
        Union and deduplicate candidates from multiple sources

        Args:
            tier1_candidates: FTS5 candidates
            tier2_candidates: FAISS candidates
            top_k: Maximum candidates to return

        Returns:
            Tuple of (candidates, provenance)
        """
        # Track provenance
        provenance = {
            'tier1_only': 0,
            'tier2_only': 0,
            'both_tiers': 0
        }

        # Build candidate map: contact_id -> candidate info
        candidate_map = {}

        # Add Tier-1 candidates
        for cand in tier1_candidates:
            contact = cand['contact']
            contact_id = self._get_contact_id(contact)

            if contact_id not in candidate_map:
                candidate_map[contact_id] = {
                    'contact': contact,
                    'sources': ['tier1'],
                    'tier1_score': cand.get('relevance_score', 0),
                    'tier2_score': 0,
                    'matched_fields': cand.get('matched_fields', [])
                }
            else:
                candidate_map[contact_id]['sources'].append('tier1')
                candidate_map[contact_id]['tier1_score'] = cand.get('relevance_score', 0)

        # Add Tier-2 candidates
        for cand in tier2_candidates:
            contact = cand['contact']
            contact_id = self._get_contact_id(contact)

            if contact_id not in candidate_map:
                candidate_map[contact_id] = {
                    'contact': contact,
                    'sources': ['tier2'],
                    'tier1_score': 0,
                    'tier2_score': cand.get('semantic_score', 0),
                    'matched_fields': []
                }
            else:
                candidate_map[contact_id]['sources'].append('tier2')
                candidate_map[contact_id]['tier2_score'] = cand.get('semantic_score', 0)

        # Calculate provenance stats
        for cand_info in candidate_map.values():
            sources = set(cand_info['sources'])
            if sources == {'tier1'}:
                provenance['tier1_only'] += 1
            elif sources == {'tier2'}:
                provenance['tier2_only'] += 1
            else:
                provenance['both_tiers'] += 1

        # Convert to list and sort by combined score
        candidates = []
        for contact_id, cand_info in candidate_map.items():
            # Simple combined score (can be improved with learned weights)
            combined_score = 0.6 * cand_info['tier1_score'] + 0.4 * cand_info['tier2_score']

            candidates.append({
                'contact': cand_info['contact'],
                'contact_id': contact_id,
                'combined_score': combined_score,
                'tier1_score': cand_info['tier1_score'],
                'tier2_score': cand_info['tier2_score'],
                'sources': cand_info['sources'],
                'matched_fields': cand_info['matched_fields']
            })

        # Sort by combined score
        candidates.sort(key=lambda x: x['combined_score'], reverse=True)

        # Return top K
        return candidates[:top_k], provenance

    def _get_contact_id(self, contact: Dict) -> str:
        """
        Generate unique ID for contact (for deduplication)

        Args:
            contact: Contact dict

        Returns:
            Unique contact ID
        """
        # Use email if available, otherwise name+company
        if contact.get('email'):
            return contact['email'].lower()

        name = contact.get('full_name', '').lower()
        company = contact.get('company', '').lower()
        return f"{name}_{company}"


# Export
__all__ = ['CandidateGenerator']
