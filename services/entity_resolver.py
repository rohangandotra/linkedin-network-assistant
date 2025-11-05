"""
Entity Resolution for 6th Degree Search
Maps vague terms to specific entities (companies, industries, roles)

Example:
- "tech" → [Google, Apple, Meta, Amazon, Microsoft, ...]
- "VC" → [Sequoia Capital, a16z, Benchmark, ...]
- "AI" → [OpenAI, Anthropic, Google DeepMind, ...]
"""

import pandas as pd
import os
from typing import List, Dict, Set, Optional


class EntityResolver:
    """
    Resolves vague search terms to specific entities

    Handles:
    - Industry mappings (tech → list of tech companies)
    - Common abbreviations (VC → venture capital)
    - Semantic expansions (AI companies, crypto companies)
    """

    def __init__(self, data_dir: str = None):
        """
        Initialize entity resolver

        Args:
            data_dir: Path to data directory (defaults to ../data relative to this file)
        """
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')

        self.data_dir = data_dir
        self.company_df = None
        self.industry_map = {}  # industry → list of companies
        self.term_expansions = {}  # vague term → specific terms

        self._load_dictionaries()
        self._build_indices()

    def _load_dictionaries(self):
        """Load company and industry dictionaries"""
        try:
            company_csv = os.path.join(self.data_dir, 'company_aliases.csv')
            self.company_df = pd.read_csv(company_csv)
            print(f"Loaded {len(self.company_df)} companies from dictionary")
        except Exception as e:
            print(f"Error loading company dictionary: {e}")
            self.company_df = pd.DataFrame()

    def _build_indices(self):
        """Build fast lookup indices"""
        if self.company_df.empty:
            return

        # Build industry → companies mapping
        for _, row in self.company_df.iterrows():
            industry = row.get('industry', '').lower().strip()
            if not industry:
                continue

            if industry not in self.industry_map:
                self.industry_map[industry] = set()

            # Add both alias and canonical name
            alias = row.get('alias', '').lower().strip()
            canonical = row.get('canonical', '').lower().strip()

            if alias:
                self.industry_map[industry].add(alias)
            if canonical and canonical != alias:
                self.industry_map[industry].add(canonical)

        # Build common term expansions
        self._build_term_expansions()

        print(f"Built indices for {len(self.industry_map)} industries")

    def _build_term_expansions(self):
        """Build mappings for common vague terms"""

        # Technology companies
        tech_industries = ['technology', 'software', 'internet', 'saas', 'enterprise software']
        tech_companies = set()
        for industry in tech_industries:
            tech_companies.update(self.industry_map.get(industry, set()))
        self.term_expansions['tech'] = tech_companies
        self.term_expansions['technology'] = tech_companies

        # Venture capital
        vc_companies = self.industry_map.get('venture capital', set())
        self.term_expansions['vc'] = vc_companies
        self.term_expansions['venture capital'] = vc_companies
        self.term_expansions['investor'] = vc_companies

        # Finance
        finance_industries = ['financial services', 'banking', 'investment banking', 'private equity', 'hedge fund']
        finance_companies = set()
        for industry in finance_industries:
            finance_companies.update(self.industry_map.get(industry, set()))
        self.term_expansions['finance'] = finance_companies
        self.term_expansions['financial'] = finance_companies

        # Fintech
        fintech_companies = self.industry_map.get('fintech', set()).union(
            self.industry_map.get('financial technology', set())
        )
        self.term_expansions['fintech'] = fintech_companies

        # Crypto
        crypto_companies = self.industry_map.get('cryptocurrency', set()).union(
            self.industry_map.get('blockchain', set())
        )
        self.term_expansions['crypto'] = crypto_companies
        self.term_expansions['blockchain'] = crypto_companies
        self.term_expansions['web3'] = crypto_companies

        # AI companies (explicit list of known AI companies)
        known_ai_companies = [
            'openai', 'anthropic', 'deepmind', 'google deepmind',
            'meta ai', 'facebook ai', 'microsoft ai', 'apple ml',
            'nvidia', 'hugging face', 'cohere', 'stability ai',
            'midjourney', 'character.ai', 'inflection', 'adept',
            'scale ai', 'databricks'
        ]
        ai_companies = set()
        for _, row in self.company_df.iterrows():
            alias = row.get('alias', '').lower().strip()
            canonical = row.get('canonical', '').lower().strip()
            # Check if company name matches known AI companies
            if alias in known_ai_companies or canonical in known_ai_companies:
                if alias:
                    ai_companies.add(alias)
                if canonical and canonical != alias:
                    ai_companies.add(canonical)
        self.term_expansions['ai'] = ai_companies
        self.term_expansions['artificial intelligence'] = ai_companies
        self.term_expansions['machine learning'] = ai_companies

        print(f"Built expansions for {len(self.term_expansions)} common terms")

    def expand_query_term(self, term: str) -> Set[str]:
        """
        Expand a vague query term to specific company names

        Args:
            term: Query term (e.g., "tech", "VC", "AI")

        Returns:
            Set of company names that match this term

        Example:
            expand_query_term("tech") → {"google", "apple", "meta", ...}
        """
        term_lower = term.lower().strip()

        # Check direct term expansions first
        if term_lower in self.term_expansions:
            return self.term_expansions[term_lower]

        # Check industry mappings
        if term_lower in self.industry_map:
            return self.industry_map[term_lower]

        # No expansion found
        return set()

    def get_companies_for_industry(self, industry: str) -> List[str]:
        """
        Get all companies in a specific industry

        Args:
            industry: Industry name

        Returns:
            List of company names
        """
        industry_lower = industry.lower().strip()
        companies = self.industry_map.get(industry_lower, set())
        return sorted(list(companies))

    def get_all_industries(self) -> List[str]:
        """Get list of all industries"""
        return sorted(list(self.industry_map.keys()))

    def resolve_query(self, query: str) -> Dict[str, any]:
        """
        Resolve a natural language query to structured search terms

        Args:
            query: Natural language query

        Returns:
            Dict with resolved entities and search strategy

        Example:
            resolve_query("Who works in tech?")
            → {
                "expanded_companies": ["google", "apple", "meta", ...],
                "original_term": "tech",
                "expansion_used": True,
                "fallback_substring": "tech"
              }
        """
        import re

        query_lower = query.lower()

        result = {
            "expanded_companies": [],
            "original_terms": [],
            "expansion_used": False,
            "fallback_substring": query_lower
        }

        # Clean query: remove punctuation for better word matching
        cleaned_query = re.sub(r'[^\w\s]', ' ', query_lower)
        words = cleaned_query.split()

        # Try to expand each word in the query
        for word in words:
            word_clean = word.strip()
            if not word_clean:
                continue

            expanded = self.expand_query_term(word_clean)
            if expanded:
                result["expanded_companies"].extend(expanded)
                result["original_terms"].append(word_clean)
                result["expansion_used"] = True

        # Remove duplicates
        result["expanded_companies"] = list(set(result["expanded_companies"]))

        return result

    def get_stats(self) -> Dict[str, int]:
        """Get statistics about loaded data"""
        return {
            "total_companies": len(self.company_df),
            "total_industries": len(self.industry_map),
            "term_expansions": len(self.term_expansions),
            "tech_companies": len(self.term_expansions.get('tech', set())),
            "vc_firms": len(self.term_expansions.get('vc', set()))
        }


# Singleton instance for efficient reuse
_resolver_instance = None

def get_entity_resolver() -> EntityResolver:
    """
    Get singleton entity resolver instance

    Returns:
        EntityResolver instance
    """
    global _resolver_instance
    if _resolver_instance is None:
        _resolver_instance = EntityResolver()
    return _resolver_instance


if __name__ == "__main__":
    # Test the entity resolver
    print("Testing Entity Resolver...\n")

    resolver = EntityResolver()

    # Show stats
    print("Stats:")
    stats = resolver.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Test query resolution
    print("\nTest Queries:")
    test_queries = [
        "Who works in tech?",
        "Show me people in VC",
        "Find engineers at AI companies",
        "Who works in fintech?",
        "People in crypto"
    ]

    for query in test_queries:
        result = resolver.resolve_query(query)
        print(f"\nQuery: {query}")
        print(f"  Expansion used: {result['expansion_used']}")
        if result['expanded_companies']:
            print(f"  Found {len(result['expanded_companies'])} companies")
            print(f"  First 5: {result['expanded_companies'][:5]}")
        else:
            print(f"  No expansion, will use substring: {result['fallback_substring']}")
