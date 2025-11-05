"""
Test script for smart search with entity resolver
Tests that queries like "Who works in tech?" properly expand to company lists
"""

import sys
sys.path.insert(0, '/Users/rohangandotra/prd-to-app')

import pandas as pd
from services.entity_resolver import get_entity_resolver


def test_entity_resolver():
    """Test entity resolver with 20 diverse queries"""

    print("=" * 80)
    print("TESTING ENTITY RESOLVER - PHASE 1")
    print("=" * 80)

    resolver = get_entity_resolver()

    # Show stats
    stats = resolver.get_stats()
    print("\nEntity Resolver Stats:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Test queries
    test_queries = [
        # Industry queries
        "Who works in tech?",
        "Show me people in venture capital",
        "Find people at VC firms",
        "Who works in fintech?",
        "People in crypto",
        "Show me AI companies",
        "Who works in finance?",

        # Role queries (should not expand, use substring)
        "Who is an engineer?",
        "Show me product managers",
        "Find executives",

        # Company queries (should not expand, use substring)
        "Who works at Google?",
        "People at Meta",
        "Show me Sequoia partners",

        # Mixed queries
        "Engineers in tech",
        "Product managers at startups",
        "Who works in AI?",

        # Vague queries that should expand
        "tech people",
        "VC contacts",
        "blockchain companies",
        "machine learning experts"
    ]

    print("\n" + "=" * 80)
    print("QUERY EXPANSION TESTS")
    print("=" * 80)

    success_count = 0
    fail_count = 0

    for i, query in enumerate(test_queries, 1):
        result = resolver.resolve_query(query)

        print(f"\n{i}. Query: \"{query}\"")

        if result['expansion_used']:
            print(f"   ✅ EXPANDED: {len(result['expanded_companies'])} companies")
            print(f"   Terms: {result['original_terms']}")
            print(f"   Sample companies: {result['expanded_companies'][:5]}")
            success_count += 1
        else:
            print(f"   ⚠️  NO EXPANSION (will use substring search)")
            print(f"   Fallback: \"{result['fallback_substring']}\"")
            fail_count += 1

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Queries tested: {len(test_queries)}")
    print(f"Expanded: {success_count}")
    print(f"No expansion: {fail_count}")
    print(f"Expansion rate: {success_count / len(test_queries) * 100:.1f}%")

    # Specific industry checks
    print("\n" + "=" * 80)
    print("INDUSTRY COVERAGE CHECKS")
    print("=" * 80)

    industries_to_check = [
        ('tech', 'Technology companies'),
        ('vc', 'Venture capital firms'),
        ('ai', 'AI companies'),
        ('fintech', 'Fintech companies'),
        ('crypto', 'Crypto/blockchain companies'),
        ('finance', 'Finance companies')
    ]

    for term, description in industries_to_check:
        expanded = resolver.expand_query_term(term)
        print(f"\n{description} ({term}):")
        print(f"  Count: {len(expanded)}")
        print(f"  Companies: {sorted(list(expanded))[:10]}")

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)

    # Check if critical expansions work
    critical_checks = {
        'tech': 50,  # Should have at least 50 tech companies
        'vc': 10,    # Should have at least 10 VC firms
        'ai': 3,     # Should have at least 3 AI companies
        'fintech': 3 # Should have at least 3 fintech companies
    }

    all_passed = True
    print("\nCRITICAL CHECKS:")
    for term, min_count in critical_checks.items():
        expanded = resolver.expand_query_term(term)
        passed = len(expanded) >= min_count
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: '{term}' has {len(expanded)} companies (need {min_count})")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n🎉 ALL CRITICAL CHECKS PASSED - READY TO DEPLOY")
    else:
        print("\n⚠️  SOME CHECKS FAILED - NEEDS INVESTIGATION")

    return all_passed


if __name__ == "__main__":
    success = test_entity_resolver()
    sys.exit(0 if success else 1)
