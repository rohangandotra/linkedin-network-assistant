"""
Hybrid Search Orchestrator
Intelligently combines Tier-1, Tier-2, and Tier-3 search results
"""

import time
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

from search_engine import (
    Tier1KeywordSearch,
    Tier2SemanticSearch,
    Tier3GPTSearch,
    SearchCache,
    expand_query_with_variations
)


class HybridSearchEngine:
    """
    Combines all search tiers with intelligent routing

    Routing logic:
    1. Always try Tier-1 first (fast, <50ms)
    2. Use Tier-2 if Tier-1 has low confidence or semantic query detected
    3. Use Tier-3 only for complex analytics/reasoning queries

    Scoring:
    - Combines BM25 scores (Tier-1) + semantic scores (Tier-2)
    - Applies additional ranking signals (exact match, name match, etc.)
    """

    def __init__(self, openai_client=None):
        self.tier1 = Tier1KeywordSearch()
        self.tier2 = Tier2SemanticSearch()
        self.tier3 = Tier3GPTSearch(openai_client)
        self.cache = SearchCache(max_size=1000)

        # Learned weights (can be tuned with logistic regression)
        self.alpha_bm25 = 0.6
        self.alpha_semantic = 0.4

    def build_indexes(self, user_id: str, contacts_df: pd.DataFrame):
        """
        Build all search indexes for a user

        Args:
            user_id: User ID
            contacts_df: Contacts DataFrame
        """
        print(f"Building search indexes for user {user_id}...")

        # Build Tier-1 (FTS5)
        print("  • Building Tier-1 keyword index...")
        self.tier1.build_index(user_id, contacts_df)

        # Build Tier-2 (embeddings)
        print("  • Building Tier-2 semantic index...")
        self.tier2.build_index(user_id, contacts_df)

        print("✅ Search indexes built successfully")

    def search(
        self,
        user_id: str,
        query: str,
        contacts_df: pd.DataFrame,
        contacts_version: int,
        top_k: int = 20,
        enable_hybrid: bool = True
    ) -> Dict[str, Any]:
        """
        Intelligent hybrid search

        Args:
            user_id: User ID
            query: Search query
            contacts_df: Contacts DataFrame
            contacts_version: Version number for cache invalidation
            top_k: Number of results to return
            enable_hybrid: Use hybrid scoring vs Tier-1 only

        Returns:
            Dict with results, metadata, and performance metrics
        """
        start_time = time.time()

        # Check cache
        cached = self.cache.get(user_id, contacts_version, query)
        if cached:
            return {
                'results': cached,
                'cached': True,
                'latency_ms': (time.time() - start_time) * 1000,
                'tier_used': 'cache'
            }

        # Expand query with variations
        expanded_query = expand_query_with_variations(query)

        # Step 1: Always try Tier-1 first (fast)
        tier1_start = time.time()
        tier1_results = self.tier1.search(
            expanded_query,
            contacts_df,
            top_k=50  # Get more for re-ranking
        )
        tier1_latency = (time.time() - tier1_start) * 1000

        # Step 2: Decide if we need Tier-2 (semantic)
        use_tier2 = enable_hybrid and self._should_use_semantic(query, tier1_results)

        tier2_results = []
        tier2_latency = 0

        if use_tier2:
            tier2_start = time.time()
            tier2_results = self.tier2.search(user_id, query, top_k=50)
            tier2_latency = (time.time() - tier2_start) * 1000

        # Step 3: Decide if we need Tier-3 (GPT)
        use_tier3 = self.tier3.should_use_gpt(query, tier1_results, tier2_results)

        if use_tier3:
            # For analytics/complex queries, hand off to GPT
            # This would call the existing extract_search_intent flow
            tier_used = 'tier3_gpt'
            # Return signal to use old GPT flow
            return {
                'use_legacy_gpt': True,
                'tier_used': tier_used,
                'query': query
            }

        # Step 4: Combine results
        if tier2_results:
            # Hybrid scoring
            combined_results = self._combine_results(tier1_results, tier2_results)
            tier_used = 'tier1+tier2_hybrid'
        else:
            # Tier-1 only
            combined_results = tier1_results
            tier_used = 'tier1_keyword'

        # Step 5: Re-rank with additional signals
        final_results = self._rerank(combined_results, query, contacts_df)

        # Take top K
        final_results = final_results[:top_k]

        # Cache results
        self.cache.set(user_id, contacts_version, query, final_results)

        # Calculate total latency
        total_latency = (time.time() - start_time) * 1000

        return {
            'results': final_results,
            'cached': False,
            'tier_used': tier_used,
            'latency_ms': total_latency,
            'tier1_latency_ms': tier1_latency,
            'tier2_latency_ms': tier2_latency,
            'result_count': len(final_results),
            'query_expanded': expanded_query != query
        }

    def _should_use_semantic(self, query: str, tier1_results: List) -> bool:
        """
        Determine if semantic search is needed

        Triggers:
        1. Zero or very few Tier-1 results
        2. Query contains semantic keywords
        3. Low confidence from Tier-1
        """
        # Trigger 1: Few results
        if len(tier1_results) < 3:
            return True

        # Trigger 2: Semantic keywords
        semantic_keywords = [
            'expert', 'specialist', 'experienced', 'skilled',
            'passionate', 'creative', 'innovative', 'senior',
            'leader', 'focused on', 'background in', 'talented',
            'professional', 'consulting', 'strategic'
        ]

        if any(kw in query.lower() for kw in semantic_keywords):
            return True

        # Trigger 3: Low confidence (low top score)
        if tier1_results and tier1_results[0]['relevance_score'] < 0.5:
            return True

        return False

    def _combine_results(
        self,
        tier1_results: List[Dict],
        tier2_results: List[Dict]
    ) -> List[Dict]:
        """
        Combine and score results from both tiers

        Uses weighted average: final_score = alpha*BM25 + beta*semantic
        """
        # Create lookup by contact ID
        contacts = {}

        # Add Tier-1 results
        for r in tier1_results:
            # Use full_name as ID (should use actual ID in production)
            contact_key = r['contact'].get('full_name', '') + r['contact'].get('email', '')

            contacts[contact_key] = {
                'contact': r['contact'],
                'bm25_score': r['relevance_score'],
                'semantic_score': 0,
                'matched_fields': r.get('matched_fields', []),
                'search_tier': r.get('search_tier', 'tier1')
            }

        # Add/merge Tier-2 results
        for r in tier2_results:
            contact_key = r['contact'].get('full_name', '') + r['contact'].get('email', '')

            if contact_key in contacts:
                # Contact found in both tiers - merge scores
                contacts[contact_key]['semantic_score'] = r['semantic_score']
                contacts[contact_key]['search_tier'] = 'tier1+tier2'
            else:
                # Contact only in Tier-2
                contacts[contact_key] = {
                    'contact': r['contact'],
                    'bm25_score': 0,
                    'semantic_score': r['semantic_score'],
                    'matched_fields': [],
                    'search_tier': 'tier2'
                }

        # Calculate combined scores
        results = []
        for contact_key, data in contacts.items():
            # Normalize scores to 0-1 range if needed
            bm25_norm = min(1.0, data['bm25_score'] / 10.0) if data['bm25_score'] > 0 else 0
            semantic_norm = data['semantic_score']

            # Weighted average
            final_score = (
                self.alpha_bm25 * bm25_norm +
                self.alpha_semantic * semantic_norm
            )

            results.append({
                'contact': data['contact'],
                'final_score': final_score,
                'relevance_score': final_score,  # For compatibility
                'bm25_score': data['bm25_score'],
                'semantic_score': data['semantic_score'],
                'matched_fields': data['matched_fields'],
                'search_tier': data['search_tier']
            })

        # Sort by final score
        results.sort(key=lambda x: x['final_score'], reverse=True)

        return results

    def _rerank(
        self,
        results: List[Dict],
        query: str,
        contacts_df: pd.DataFrame
    ) -> List[Dict]:
        """
        Apply additional ranking signals

        Boosts:
        - Exact match: 1.5x
        - Name match: 1.2x
        - Prefix match: 1.1x
        """
        query_lower = query.lower()
        query_terms = set(query_lower.split())

        for r in results:
            contact = r['contact']
            score_boost = 1.0

            # Boost 1: Exact match in any field
            for field in ['full_name', 'company', 'position']:
                value = str(contact.get(field, '')).lower()
                if value == query_lower:
                    score_boost *= 1.5
                    break

            # Boost 2: Name field match (people search is important)
            if 'full_name' in r.get('matched_fields', []):
                score_boost *= 1.2

            # Boost 3: Prefix match (autocomplete-like)
            full_name = str(contact.get('full_name', '')).lower()
            if full_name.startswith(query_lower):
                score_boost *= 1.1

            # Boost 4: All query terms match
            name_terms = set(full_name.split())
            if query_terms.issubset(name_terms):
                score_boost *= 1.15

            # Apply boost
            r['final_score'] *= score_boost
            r['relevance_score'] *= score_boost

        # Re-sort
        results.sort(key=lambda x: x['final_score'], reverse=True)

        return results

    def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        return self.cache.get_stats()

    def invalidate_cache(self, user_id: str):
        """Invalidate cache for a user (e.g., after contact update)"""
        self.cache.invalidate(user_id)

    def close(self):
        """Clean up resources"""
        if self.tier1:
            self.tier1.close()


# ============================================
# QUERY CLASSIFICATION
# ============================================

def classify_query_complexity(query: str) -> str:
    """
    Classify query complexity to route to appropriate tier

    Returns:
        'simple' - Tier-1 only
        'semantic' - Tier-1 + Tier-2
        'complex' - Tier-3 (GPT)
    """
    query_lower = query.lower()

    # Simple patterns (Tier-1 only)
    simple_patterns = [
        r'^[\w\s]+$',  # Just words
        r'^\w+@[\w\.]+',  # Email-like
    ]

    import re
    if len(query_lower.split()) <= 2:
        for pattern in simple_patterns:
            if re.match(pattern, query_lower):
                return 'simple'

    # Semantic patterns (Tier-1 + Tier-2)
    semantic_keywords = [
        'expert', 'specialist', 'creative', 'innovative', 'experienced',
        'skilled in', 'background in', 'passionate about', 'focused on'
    ]
    if any(kw in query_lower for kw in semantic_keywords):
        return 'semantic'

    # Complex patterns (Tier-3 GPT)
    complex_keywords = [
        'in tech', 'in finance', 'in healthcare',
        'most senior', 'highest level', 'top',
        'how many', 'breakdown', 'analyze',
        'at startups', 'at big companies',
        'pre-ipo', 'series a', 'series b'
    ]
    if any(kw in query_lower for kw in complex_keywords):
        return 'complex'

    # Default to semantic (middle ground)
    return 'semantic'


# Export
__all__ = ['HybridSearchEngine', 'classify_query_complexity']
