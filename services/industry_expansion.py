"""
Industry Query Expansion for 6th Degree AI
Expand vague industry terms to specific company names

Example:
- "tech" → [Google, Apple, Meta, Amazon, Microsoft, ...]
- "VC" → [Sequoia Capital, a16z, Benchmark, ...]
- "AI" → [OpenAI, Anthropic, DeepMind, ...]

Conservative approach: Only expand VERY obvious vague terms
"""

from typing import List, Dict, Set, Optional


class IndustryExpander:
    """
    Expand vague industry terms to company lists

    Very conservative - only expands obvious vague terms like "tech", "VC", "AI"
    """

    # Industry → Companies mapping
    EXPANSIONS = {
        # Technology (broad)
        'tech': [
            'Google', 'Apple', 'Meta', 'Facebook', 'Amazon', 'Microsoft',
            'Netflix', 'Tesla', 'Uber', 'Lyft', 'Airbnb', 'DoorDash',
            'Stripe', 'Square', 'Plaid', 'Coinbase', 'Robinhood',
            'Salesforce', 'Oracle', 'Adobe', 'IBM', 'Intel', 'NVIDIA',
            'AMD', 'Qualcomm', 'Cisco', 'VMware', 'Twitter', 'X',
            'Snap', 'TikTok', 'Pinterest', 'Reddit', 'LinkedIn',
            'Slack', 'Zoom', 'Dropbox', 'Atlassian', 'GitHub', 'GitLab',
            'Figma', 'Notion', 'Asana', 'Monday.com', 'Airtable'
        ],
        'technology': [  # Same as tech
            'Google', 'Apple', 'Meta', 'Facebook', 'Amazon', 'Microsoft',
            'Netflix', 'Tesla', 'Uber', 'Lyft', 'Airbnb', 'DoorDash',
            'Stripe', 'Square', 'Plaid', 'Coinbase', 'Robinhood',
            'Salesforce', 'Oracle', 'Adobe', 'IBM', 'Intel', 'NVIDIA'
        ],

        # Venture Capital
        'vc': [
            'Sequoia Capital', 'Sequoia', 'Andreessen Horowitz', 'a16z',
            'Benchmark', 'Accel', 'Greylock', 'Greylock Partners',
            'Kleiner Perkins', 'Google Ventures', 'GV', 'NEA',
            'Lightspeed', 'Bessemer', 'Index Ventures', 'Insight Partners',
            'Tiger Global', 'Coatue', 'General Catalyst', 'Founders Fund',
            'Y Combinator', 'YC', 'Techstars'
        ],
        'venture capital': [  # Same as vc
            'Sequoia Capital', 'Sequoia', 'Andreessen Horowitz', 'a16z',
            'Benchmark', 'Accel', 'Greylock', 'Kleiner Perkins',
            'Google Ventures', 'GV', 'NEA', 'Lightspeed', 'Bessemer'
        ],
        'investor': [  # Same as vc
            'Sequoia Capital', 'Sequoia', 'Andreessen Horowitz', 'a16z',
            'Benchmark', 'Accel', 'Greylock', 'Kleiner Perkins'
        ],

        # AI / Machine Learning
        'ai': [
            'OpenAI', 'Anthropic', 'DeepMind', 'Google DeepMind',
            'Meta AI', 'Microsoft AI', 'Nvidia', 'Hugging Face',
            'Cohere', 'Stability AI', 'Midjourney', 'Character.AI',
            'Inflection', 'Adept', 'Scale AI', 'Databricks'
        ],
        'artificial intelligence': [  # Same as ai
            'OpenAI', 'Anthropic', 'DeepMind', 'Google DeepMind',
            'Meta AI', 'Nvidia', 'Hugging Face', 'Cohere', 'Stability AI'
        ],
        'machine learning': [  # Same as ai
            'OpenAI', 'Anthropic', 'DeepMind', 'Google DeepMind',
            'Meta AI', 'Nvidia', 'Hugging Face', 'Scale AI', 'Databricks'
        ],
        'ml': [  # Same as ai
            'OpenAI', 'Anthropic', 'DeepMind', 'Meta AI', 'Nvidia', 'Scale AI'
        ],

        # Fintech
        'fintech': [
            'Stripe', 'Square', 'Block', 'Plaid', 'Chime', 'Affirm',
            'Robinhood', 'Coinbase', 'Checkout.com', 'Marqeta', 'Brex',
            'Ramp', 'Mercury', 'Wise', 'Revolut'
        ],
        'financial technology': [  # Same as fintech
            'Stripe', 'Square', 'Plaid', 'Chime', 'Affirm', 'Robinhood',
            'Coinbase', 'Brex', 'Ramp', 'Mercury'
        ],

        # Crypto
        'crypto': [
            'Coinbase', 'Binance', 'Kraken', 'Gemini', 'FTX',
            'Circle', 'Chainalysis', 'Ripple', 'Alchemy', 'Infura'
        ],
        'cryptocurrency': [  # Same as crypto
            'Coinbase', 'Binance', 'Kraken', 'Gemini', 'Circle', 'Ripple'
        ],
        'blockchain': [  # Same as crypto
            'Coinbase', 'Binance', 'Circle', 'Chainalysis', 'Ripple', 'Alchemy'
        ],
        'web3': [  # Same as crypto
            'Coinbase', 'Alchemy', 'Infura', 'OpenSea', 'Uniswap'
        ],

        # Finance (traditional)
        'finance': [
            'Goldman Sachs', 'JPMorgan', 'JPMorgan Chase', 'Morgan Stanley',
            'Citigroup', 'Citi', 'Bank of America', 'BlackRock', 'Vanguard',
            'Fidelity', 'Wells Fargo', 'Charles Schwab'
        ],
        'banking': [
            'Goldman Sachs', 'JPMorgan', 'Morgan Stanley', 'Citigroup',
            'Bank of America', 'Wells Fargo', 'Charles Schwab'
        ],

        # Consulting
        'consulting': [
            'McKinsey', 'McKinsey & Company', 'Bain', 'Bain & Company',
            'BCG', 'Boston Consulting Group', 'Deloitte', 'PwC',
            'EY', 'KPMG', 'Accenture'
        ],

        # Startup (general)
        'startup': [
            'Stripe', 'Notion', 'Figma', 'Retool', 'Linear', 'Vercel',
            'Supabase', 'Railway', 'Fly.io', 'Replit'
        ],
        'startups': [  # Same as startup
            'Stripe', 'Notion', 'Figma', 'Retool', 'Linear', 'Vercel'
        ],
    }

    def __init__(self):
        """Initialize industry expander"""
        self.stats = {
            'queries_processed': 0,
            'queries_expanded': 0,
            'queries_unchanged': 0
        }

    def should_expand(self, query: str) -> bool:
        """
        Check if query should be expanded

        Args:
            query: Search query

        Returns:
            True if query contains expandable terms

        Example:
            should_expand("Who works in tech?") → True
            should_expand("software engineer") → False
        """
        query_lower = query.lower().strip()

        # Check if any expansion term is in the query
        for term in self.EXPANSIONS.keys():
            if term in query_lower:
                return True

        return False

    def expand_query(self, query: str) -> Dict[str, any]:
        """
        Expand query with industry terms

        Args:
            query: Search query

        Returns:
            {
                'original_query': str,
                'should_expand': bool,
                'expansion_terms': List[str],  # Terms that triggered expansion
                'companies': List[str],  # Companies to search for
                'search_companies': bool  # Whether to use company list
            }

        Example:
            expand_query("Who works in tech?")
            → {
                'original_query': 'Who works in tech?',
                'should_expand': True,
                'expansion_terms': ['tech'],
                'companies': ['Google', 'Apple', 'Meta', ...],
                'search_companies': True
            }
        """
        self.stats['queries_processed'] += 1

        query_lower = query.lower().strip()

        result = {
            'original_query': query,
            'should_expand': False,
            'expansion_terms': [],
            'companies': [],
            'search_companies': False
        }

        # Find all expansion terms in query
        expansion_terms_found = []
        companies_set = set()

        for term, companies in self.EXPANSIONS.items():
            if term in query_lower:
                expansion_terms_found.append(term)
                companies_set.update(companies)

        # If we found expansion terms, expand
        if expansion_terms_found:
            result['should_expand'] = True
            result['expansion_terms'] = expansion_terms_found
            result['companies'] = sorted(list(companies_set))
            result['search_companies'] = True
            self.stats['queries_expanded'] += 1
        else:
            self.stats['queries_unchanged'] += 1

        return result

    def get_stats(self) -> Dict:
        """Get expansion statistics"""
        return self.stats.copy()


# Singleton instance
_expander_instance = None

def get_industry_expander() -> IndustryExpander:
    """Get singleton industry expander instance"""
    global _expander_instance
    if _expander_instance is None:
        _expander_instance = IndustryExpander()
    return _expander_instance


def expand_industry_query(query: str) -> Dict[str, any]:
    """
    Convenience function to expand query

    Args:
        query: Search query

    Returns:
        Expansion result dict
    """
    expander = get_industry_expander()
    return expander.expand_query(query)


if __name__ == "__main__":
    # Test the industry expander
    print("Testing Industry Expander...\n")

    expander = IndustryExpander()

    # Test cases
    test_queries = [
        "Who works in tech?",
        "Show me people in venture capital",
        "Find VCs",
        "Who works in AI?",
        "People at fintech companies",
        "Show me crypto people",
        "software engineer",  # Should NOT expand
        "product manager at Google",  # Should NOT expand
        "Who works in finance?",
        "machine learning engineers",
    ]

    for query in test_queries:
        result = expander.expand_query(query)
        print(f"Query: \"{query}\"")
        if result['should_expand']:
            print(f"  ✅ EXPAND")
            print(f"  Terms: {result['expansion_terms']}")
            print(f"  Companies: {len(result['companies'])} total")
            print(f"  Sample: {result['companies'][:5]}")
        else:
            print(f"  ⚠️  NO EXPANSION (use normal search)")
        print()

    print("\nStatistics:")
    for key, value in expander.get_stats().items():
        print(f"  {key}: {value}")
    print()

    print(f"✅ Expansion rate: {expander.stats['queries_expanded']}/{expander.stats['queries_processed']} ({expander.stats['queries_expanded']/expander.stats['queries_processed']*100:.1f}%)")
