"""
Integrated Search Engine for 6th Degree
Complete end-to-end search pipeline

Pipeline:
1. Parse query → structured entities
2. Generate candidates → FTS5 + FAISS
3. Compute features → relevance signals
4. Score candidates → s0 scorer
5. Diversify results → variety across companies/industries
6. Return top-k → ranked, diverse results
"""

import pandas as pd
import time
from typing import Dict, List, Any

from services.query_parser import parse_query
from services.candidate_generator import CandidateGenerator
from services.feature_factory import FeatureFactory, S0Scorer, Diversifier


class IntegratedSearchEngine:
    """
    Complete search engine integrating all components

    Features:
    - Query understanding (parser)
    - Candidate generation (FTS5 + FAISS)
    - Feature computation (relevance signals)
    - Scoring (s0 hand-tuned weights)
    - Diversification (company/industry variety)
    """

    def __init__(self, openai_client=None):
        """
        Initialize integrated search engine

        Args:
            openai_client: Optional OpenAI client for LLM fallback
        """
        self.candidate_generator = CandidateGenerator(openai_client)
        self.feature_factory = FeatureFactory()
        self.scorer = S0Scorer()
        self.diversifier = Diversifier(max_per_company=3, max_per_industry=5)
        self.openai_client = openai_client

    def indexes_exist(self, user_id: str) -> bool:
        """
        Check if indexes exist on disk for user

        Args:
            user_id: User ID

        Returns:
            True if indexes exist
        """
        return self.candidate_generator.indexes_exist(user_id)

    def load_indexes(self, user_id: str) -> bool:
        """
        Load existing indexes from disk

        Args:
            user_id: User ID

        Returns:
            True if loaded successfully
        """
        return self.candidate_generator.load_indexes(user_id)

    def build_indexes(self, user_id: str, contacts_df: pd.DataFrame):
        """
        Build search indexes for a user

        Args:
            user_id: User ID
            contacts_df: Contacts DataFrame
        """
        self.candidate_generator.build_indexes(user_id, contacts_df)

    def search(
        self,
        user_id: str,
        query: str,
        contacts_df: pd.DataFrame,
        top_k: int = 10,
        use_semantic: bool = True,
        use_diversification: bool = True,
        explain: bool = False
    ) -> Dict[str, Any]:
        """
        Execute end-to-end search

        Args:
            user_id: User ID
            query: Search query
            contacts_df: Contacts DataFrame
            top_k: Number of results to return
            use_semantic: Enable semantic search (FAISS)
            use_diversification: Enable result diversification
            explain: Include explanations for scoring

        Returns:
            Dict with results and metadata
        """
        start_time = time.time()

        # Step 1: Generate candidates
        candidate_result = self.candidate_generator.generate_candidates(
            user_id=user_id,
            query=query,
            contacts_df=contacts_df,
            top_k=100,  # Get more candidates for better ranking
            use_semantic=use_semantic
        )

        candidates = candidate_result['candidates']
        parsed_query = candidate_result['parsed_query']

        if not candidates:
            return {
                'success': True,
                'results': [],
                'query': query,
                'parsed_query': parsed_query,
                'total_latency_ms': (time.time() - start_time) * 1000,
                'metrics': {
                    'candidate_generation_ms': candidate_result['metrics']['total_latency_ms'],
                    'feature_computation_ms': 0,
                    'scoring_ms': 0,
                    'diversification_ms': 0,
                    'candidates_generated': 0,
                    'results_returned': 0
                },
                'message': 'No candidates found'
            }

        # Step 2: Compute features for each candidate
        feature_start = time.time()
        for candidate in candidates:
            features = self.feature_factory.compute_features(
                candidate, parsed_query, query
            )
            candidate['features'] = features

        feature_time = (time.time() - feature_start) * 1000

        # Step 3: Score candidates
        score_start = time.time()
        for candidate in candidates:
            if explain:
                score, top_features = self.scorer.score_with_explanation(candidate['features'])
                candidate['score'] = score
                candidate['top_features'] = top_features
            else:
                score = self.scorer.score(candidate['features'])
                candidate['score'] = score

        # Sort by score
        candidates.sort(key=lambda x: x['score'], reverse=True)
        score_time = (time.time() - score_start) * 1000

        # Step 4: Diversify
        diversify_start = time.time()
        if use_diversification:
            results = self.diversifier.diversify(candidates, top_k=top_k)
        else:
            results = candidates[:top_k]
        diversify_time = (time.time() - diversify_start) * 1000

        total_time = (time.time() - start_time) * 1000

        # Format results
        formatted_results = []
        for i, candidate in enumerate(results, 1):
            result = {
                'rank': i,
                'contact': candidate['contact'],
                'score': candidate['score'],
                'sources': candidate.get('sources', []),
                'matched_fields': candidate.get('matched_fields', [])
            }

            if explain:
                result['explanation'] = [
                    {
                        'feature': f['feature'],
                        'contribution': f['contribution']
                    }
                    for f in candidate.get('top_features', [])
                ]

            formatted_results.append(result)

        return {
            'success': True,
            'results': formatted_results,
            'query': query,
            'parsed_query': parsed_query,
            'total_latency_ms': total_time,
            'metrics': {
                'candidate_generation_ms': candidate_result['metrics']['total_latency_ms'],
                'feature_computation_ms': feature_time,
                'scoring_ms': score_time,
                'diversification_ms': diversify_time,
                'candidates_generated': len(candidates),
                'results_returned': len(results)
            }
        }


# Export
__all__ = ['IntegratedSearchEngine']
