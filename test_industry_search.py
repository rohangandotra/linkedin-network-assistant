"""
Test industry expansion in search_integration
"""

import pandas as pd
import sys
sys.path.insert(0, '/Users/rohangandotra/prd-to-app')

# Create dummy contacts
contacts = [
    {'full_name': 'John Smith', 'company': 'Google', 'position': 'Software Engineer', 'email': 'john@google.com'},
    {'full_name': 'Sarah Johnson', 'company': 'Meta', 'position': 'Product Manager', 'email': 'sarah@meta.com'},
    {'full_name': 'Alex Chen', 'company': 'Andreessen Horowitz', 'position': 'Partner', 'email': 'alex@a16z.com'},
    {'full_name': 'Maria Garcia', 'company': 'Stripe', 'position': 'Engineer', 'email': 'maria@stripe.com'},
    {'full_name': 'David Lee', 'company': 'OpenAI', 'position': 'Researcher', 'email': 'david@openai.com'},
    {'full_name': 'Emily Brown', 'company': 'Acme Corp', 'position': 'Manager', 'email': 'emily@acme.com'},
    {'full_name': 'Tom Wilson', 'company': 'Apple', 'position': 'Designer', 'email': 'tom@apple.com'},
]

df = pd.DataFrame(contacts)

print("Test Contacts:")
print(df[['full_name', 'company', 'position']])
print()

# Test queries
test_queries = [
    ("Who works in tech?", True, ['Google', 'Meta', 'Apple']),
    ("Show me people in VC", True, ['Andreessen Horowitz']),
    ("Who works in AI?", True, ['OpenAI']),
    ("software engineer", False, ['Google']),  # Should use regular search, but should still find Google
    ("product manager", False, ['Meta']),  # Should use regular search
]

print("=" * 80)
print("TESTING INDUSTRY EXPANSION IN SEARCH")
print("=" * 80)
print()

from services.industry_expansion import expand_industry_query

for query, should_expand, expected_companies in test_queries:
    print(f"Query: \"{query}\"")

    # Test expansion
    expansion = expand_industry_query(query)
    print(f"  Should expand: {expansion['should_expand']} (expected: {should_expand})")

    if expansion['should_expand']:
        print(f"  Expansion terms: {expansion['expansion_terms']}")
        print(f"  Companies to search: {len(expansion['companies'])}")

        # Simulate search
        companies = expansion['companies']
        mask = pd.Series([False] * len(df), index=df.index)

        for company in companies:
            company_lower = company.lower()
            company_mask = df['company'].fillna('').str.lower().str.contains(
                company_lower, regex=False, na=False
            )
            mask = mask | company_mask

        results = df[mask]
        print(f"  Results found: {len(results)}")
        if not results.empty:
            print(f"  Companies in results: {results['company'].tolist()}")

            # Check if expected companies are found
            found_companies = results['company'].tolist()
            for exp in expected_companies:
                if exp in found_companies:
                    print(f"    ✅ Found {exp}")
                else:
                    print(f"    ❌ Missing {exp}")
        else:
            print(f"    ❌ No results found!")
    else:
        print(f"  ✅ No expansion (will use regular search)")

    print()

print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)
