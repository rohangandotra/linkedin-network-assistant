"""
Feature Factory for 6th Degree Search
Computes relevance features for ranking candidates

Features:
- Exact match features (name, company, position, location)
- Semantic match features (industry alignment, role similarity)
- Source confidence features (FTS5 score, semantic score, provenance)
- Diversity features (industry, company, geo spread)
"""

import re
from typing import Dict, List, Any
import pandas as pd


class FeatureFactory:
    """
    Computes features for search candidates

    Feature Categories:
    1. Exact Match: Binary indicators for exact/partial matches
    2. Text Similarity: String similarity scores
    3. Source Scores: BM25, semantic similarity from search engines
    4. Provenance: Which sources found this candidate
    """

    def __init__(self):
        """Initialize feature factory"""
        pass

    def compute_features(
        self,
        candidate: Dict[str, Any],
        parsed_query: Dict[str, Any],
        query: str
    ) -> Dict[str, float]:
        """
        Compute all features for a candidate

        Args:
            candidate: Candidate dict from candidate generator
            parsed_query: Parsed query structure
            query: Original query string

        Returns:
            Dict of feature_name -> feature_value
        """
        contact = candidate['contact']
        targets = parsed_query.get('targets', {})

        features = {}

        # 1. Exact Match Features
        features.update(self._compute_exact_match_features(contact, targets))

        # 2. Text Similarity Features
        features.update(self._compute_text_similarity_features(contact, query, targets))

        # 3. Source Score Features
        features.update(self._compute_source_features(candidate))

        # 4. Provenance Features
        features.update(self._compute_provenance_features(candidate))

        return features

    def _compute_exact_match_features(
        self,
        contact: Dict[str, Any],
        targets: Dict[str, List[str]]
    ) -> Dict[str, float]:
        """
        Compute exact/partial match features

        Args:
            contact: Contact dict
            targets: Parsed query targets

        Returns:
            Dict of match features
        """
        features = {}

        # Name match
        name = str(contact.get('full_name', '')).lower()

        # Company exact match
        company = str(contact.get('company', '')).lower()
        query_companies = [c.lower() for c in targets.get('companies', [])]
        features['company_exact_match'] = 1.0 if any(qc in company for qc in query_companies) else 0.0

        # Position/role match
        position = str(contact.get('position', '')).lower()
        query_personas = [p.lower() for p in targets.get('personas', [])]
        features['position_exact_match'] = 1.0 if any(qp in position for qp in query_personas) else 0.0

        # Industry match (approximate - check if industry keywords in company/position)
        query_industries = [i.lower() for i in targets.get('industries', [])]
        company_position = f"{company} {position}".lower()
        features['industry_match'] = 1.0 if any(qi in company_position for qi in query_industries) else 0.0

        # Location match
        # Note: Location data not in contacts, so we skip for now
        # In production, would check email domain or other signals
        features['location_match'] = 0.0

        return features

    def _compute_text_similarity_features(
        self,
        contact: Dict[str, Any],
        query: str,
        targets: Dict[str, List[str]]
    ) -> Dict[str, float]:
        """
        Compute text similarity features

        Args:
            contact: Contact dict
            query: Original query
            targets: Parsed query targets

        Returns:
            Dict of similarity features
        """
        features = {}

        # Token overlap between query and contact fields
        query_tokens = set(query.lower().split())

        # Name overlap
        name_tokens = set(str(contact.get('full_name', '')).lower().split())
        features['name_token_overlap'] = len(query_tokens & name_tokens) / max(len(query_tokens), 1)

        # Company overlap
        company_tokens = set(str(contact.get('company', '')).lower().split())
        features['company_token_overlap'] = len(query_tokens & company_tokens) / max(len(query_tokens), 1)

        # Position overlap
        position_tokens = set(str(contact.get('position', '')).lower().split())
        features['position_token_overlap'] = len(query_tokens & position_tokens) / max(len(query_tokens), 1)

        # Overall contact field match
        contact_text = f"{contact.get('full_name', '')} {contact.get('company', '')} {contact.get('position', '')}".lower()
        contact_tokens = set(contact_text.split())
        features['overall_token_overlap'] = len(query_tokens & contact_tokens) / max(len(query_tokens), 1)

        return features

    def _compute_source_features(self, candidate: Dict[str, Any]) -> Dict[str, float]:
        """
        Compute source score features

        Args:
            candidate: Candidate dict

        Returns:
            Dict of source features
        """
        features = {}

        # BM25 score from FTS5
        features['bm25_score'] = float(candidate.get('tier1_score', 0.0))

        # Semantic score from FAISS
        features['semantic_score'] = float(candidate.get('tier2_score', 0.0))

        # Combined score (already computed by candidate generator)
        features['combined_score'] = float(candidate.get('combined_score', 0.0))

        # Normalize scores to 0-1 range (BM25 can be large)
        if features['bm25_score'] > 0:
            features['bm25_score_normalized'] = min(features['bm25_score'] / 10.0, 1.0)
        else:
            features['bm25_score_normalized'] = 0.0

        return features

    def _compute_provenance_features(self, candidate: Dict[str, Any]) -> Dict[str, float]:
        """
        Compute provenance features

        Args:
            candidate: Candidate dict

        Returns:
            Dict of provenance features
        """
        features = {}

        sources = candidate.get('sources', [])

        # Binary indicators for which sources found this candidate
        features['found_by_fts5'] = 1.0 if 'tier1' in sources else 0.0
        features['found_by_faiss'] = 1.0 if 'tier2' in sources else 0.0
        features['found_by_both'] = 1.0 if len(sources) >= 2 else 0.0

        return features


class S0Scorer:
    """
    s0 Scorer: Hand-tuned linear combination of features

    This is a baseline scoring function that can be later replaced
    with learned weights (logistic regression, gradient boosting, etc.)
    """

    def __init__(self):
        """
        Initialize scorer with hand-tuned weights

        Weights are based on intuition and can be tuned with labeled data
        """
        # Exact match features (highest weight - very strong signal)
        self.weights = {
            'company_exact_match': 3.0,
            'position_exact_match': 2.5,
            'industry_match': 2.0,
            'location_match': 1.5,

            # Text similarity features (medium weight)
            'name_token_overlap': 2.0,
            'company_token_overlap': 1.5,
            'position_token_overlap': 1.5,
            'overall_token_overlap': 1.0,

            # Source score features (important but already factored in)
            'bm25_score_normalized': 2.0,
            'semantic_score': 1.5,

            # Provenance features (bonus for multi-source agreement)
            'found_by_both': 1.0,
            'found_by_fts5': 0.5,
            'found_by_faiss': 0.5,
        }

    def score(self, features: Dict[str, float]) -> float:
        """
        Compute final score from features

        Args:
            features: Feature dict

        Returns:
            Final relevance score
        """
        score = 0.0

        for feature_name, weight in self.weights.items():
            feature_value = features.get(feature_name, 0.0)
            score += weight * feature_value

        return score

    def score_with_explanation(self, features: Dict[str, float]) -> tuple:
        """
        Compute score with explanation of top contributors

        Args:
            features: Feature dict

        Returns:
            Tuple of (score, top_features)
        """
        contributions = []

        for feature_name, weight in self.weights.items():
            feature_value = features.get(feature_name, 0.0)
            contribution = weight * feature_value

            if contribution > 0:
                contributions.append({
                    'feature': feature_name,
                    'value': feature_value,
                    'weight': weight,
                    'contribution': contribution
                })

        # Sort by contribution
        contributions.sort(key=lambda x: x['contribution'], reverse=True)

        # Calculate total score
        total_score = sum(c['contribution'] for c in contributions)

        # Get top 3 contributors
        top_features = contributions[:3]

        return total_score, top_features


class Diversifier:
    """
    Diversifies search results to avoid redundancy

    Ensures variety across:
    - Companies (don't show 10 people from same company)
    - Industries (balance across different sectors)
    - Geographies (if available)
    """

    def __init__(self, max_per_company: int = 3, max_per_industry: int = 5):
        """
        Initialize diversifier

        Args:
            max_per_company: Max results from same company
            max_per_industry: Max results from same industry (approximate)
        """
        self.max_per_company = max_per_company
        self.max_per_industry = max_per_industry

    def diversify(
        self,
        candidates: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Diversify candidate list

        Args:
            candidates: Scored and sorted candidates
            top_k: Number of results to return

        Returns:
            Diversified list of top_k candidates
        """
        if len(candidates) <= top_k:
            return candidates

        # Track counts
        company_counts = {}
        industry_counts = {}

        diversified = []

        for candidate in candidates:
            if len(diversified) >= top_k:
                break

            contact = candidate['contact']
            company = str(contact.get('company', 'unknown')).lower()

            # Approximate industry from company/position
            position = str(contact.get('position', '')).lower()
            industry = self._infer_industry(company, position)

            # Check company quota
            company_count = company_counts.get(company, 0)
            if company_count >= self.max_per_company:
                continue  # Skip, too many from this company

            # Check industry quota
            industry_count = industry_counts.get(industry, 0)
            if industry_count >= self.max_per_industry:
                continue  # Skip, too many from this industry

            # Add to diversified list
            diversified.append(candidate)

            # Update counts
            company_counts[company] = company_count + 1
            industry_counts[industry] = industry_count + 1

        # If we didn't get enough, add remaining candidates without quotas
        if len(diversified) < top_k:
            for candidate in candidates:
                if candidate not in diversified:
                    diversified.append(candidate)
                    if len(diversified) >= top_k:
                        break

        return diversified[:top_k]

    def _infer_industry(self, company: str, position: str) -> str:
        """
        Infer industry from company name and position

        Args:
            company: Company name
            position: Position title

        Returns:
            Inferred industry (rough approximation)
        """
        text = f"{company} {position}".lower()

        # Simple keyword-based industry inference
        industry_keywords = {
            'tech': ['google', 'meta', 'microsoft', 'apple', 'amazon', 'software', 'engineer'],
            'fintech': ['stripe', 'coinbase', 'robinhood', 'paypal', 'fintech', 'finance'],
            'healthcare': ['healthcare', 'medical', 'health', 'biotech', 'pharma'],
            'venture_capital': ['sequoia', 'andreessen', 'a16z', 'partner', 'vc', 'venture'],
            'ecommerce': ['amazon', 'shopify', 'ecommerce', 'retail'],
            'social': ['meta', 'facebook', 'twitter', 'linkedin', 'social'],
        }

        for industry, keywords in industry_keywords.items():
            if any(kw in text for kw in keywords):
                return industry

        return 'other'


# Export
__all__ = ['FeatureFactory', 'S0Scorer', 'Diversifier']
