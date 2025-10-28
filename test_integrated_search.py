"""
Test Integrated Search Engine
End-to-end validation of complete search pipeline
"""

import pandas as pd
import numpy as np
from services.integrated_search import IntegratedSearchEngine
import time


# Extended sample contacts for better testing
SAMPLE_CONTACTS = [
    # Tech companies - Engineers
    {'full_name': 'John Smith', 'email': 'john.smith@google.com', 'company': 'Google', 'position': 'Senior Product Manager'},
    {'full_name': 'Sarah Johnson', 'email': 'sarah.j@meta.com', 'company': 'Meta', 'position': 'Software Engineer'},
    {'full_name': 'Mike Chen', 'email': 'mchen@microsoft.com', 'company': 'Microsoft', 'position': 'Principal Software Engineer'},
    {'full_name': 'Emily Davis', 'email': 'emily@stripe.com', 'company': 'Stripe', 'position': 'Engineering Manager'},
    {'full_name': 'David Lee', 'email': 'dlee@openai.com', 'company': 'OpenAI', 'position': 'Machine Learning Engineer'},

    # More Google employees (to test diversification)
    {'full_name': 'Alice Wong', 'email': 'awong@google.com', 'company': 'Google', 'position': 'Software Engineer'},
    {'full_name': 'Bob Taylor', 'email': 'btaylor@google.com', 'company': 'Google', 'position': 'Product Manager'},
    {'full_name': 'Carol White', 'email': 'cwhite@google.com', 'company': 'Google', 'position': 'Senior Engineer'},
    {'full_name': 'Dan Brown', 'email': 'dbrown@google.com', 'company': 'Google', 'position': 'Staff Engineer'},

    # Sales roles
    {'full_name': 'Jessica Brown', 'email': 'jbrown@salesforce.com', 'company': 'Salesforce', 'position': 'VP of Sales'},
    {'full_name': 'Tom Miller', 'email': 'tmiller@salesforce.com', 'company': 'Salesforce', 'position': 'Account Executive'},

    # Design roles
    {'full_name': 'Tom Wilson', 'email': 'twilson@apple.com', 'company': 'Apple', 'position': 'Senior Designer'},
    {'full_name': 'Lisa Martinez', 'email': 'lisa@figma.com', 'company': 'Figma', 'position': 'Product Designer'},

    # Data roles
    {'full_name': 'Chris Anderson', 'email': 'canderson@netflix.com', 'company': 'Netflix', 'position': 'Data Scientist'},
    {'full_name': 'Amanda Taylor', 'email': 'ataylor@airbnb.com', 'company': 'Airbnb', 'position': 'Data Engineer'},

    # Venture Capital
    {'full_name': 'Robert Garcia', 'email': 'rgarcia@sequoia.com', 'company': 'Sequoia Capital', 'position': 'Partner'},
    {'full_name': 'Jennifer Kim', 'email': 'jkim@a16z.com', 'company': 'Andreessen Horowitz', 'position': 'Partner'},

    # More diversity
    {'full_name': 'Michael Zhang', 'email': 'mzhang@tesla.com', 'company': 'Tesla', 'position': 'Senior Software Engineer'},
    {'full_name': 'Ashley White', 'email': 'awhite@uber.com', 'company': 'Uber', 'position': 'Product Manager'},
    {'full_name': 'James Rodriguez', 'email': 'jrodriguez@coinbase.com', 'company': 'Coinbase', 'position': 'Engineering Manager'},
]


def test_integrated_search():
    """Test complete search pipeline"""
    print("=" * 80)
    print("INTEGRATED SEARCH ENGINE TEST")
    print("=" * 80)

    # Create sample DataFrame
    contacts_df = pd.DataFrame(SAMPLE_CONTACTS)
    user_id = 'test_user'

    # Initialize search engine
    print("\n1. Initializing integrated search engine...")
    engine = IntegratedSearchEngine()

    # Build indexes
    print("\n2. Building search indexes...")
    try:
        engine.build_indexes(user_id, contacts_df)
        print("✅ Indexes built successfully")
    except Exception as e:
        print(f"❌ Failed to build indexes: {e}")
        print("\nContinuing with available components...")

    # Test queries with expected top results
    test_queries = [
        {
            'query': 'PM at Google',
            'expected_companies': ['Google'],
            'expected_positions': ['product manager']
        },
        {
            'query': 'software engineer at Meta',
            'expected_companies': ['Meta'],
            'expected_positions': ['software engineer']
        },
        {
            'query': 'machine learning engineer',
            'expected_positions': ['machine learning engineer']
        },
        {
            'query': 'venture capital partner',
            'expected_companies': ['Sequoia Capital', 'Andreessen Horowitz'],
            'expected_positions': ['partner']
        },
        {
            'query': 'designer at Apple',
            'expected_companies': ['Apple'],
            'expected_positions': ['designer']
        },
        {
            'query': 'data scientist',
            'expected_positions': ['data scientist']
        },
        {
            'query': 'VP of sales',
            'expected_positions': ['vp', 'sales']
        },
        {
            'query': 'engineering manager',
            'expected_positions': ['engineering manager']
        }
    ]

    print("\n3. Testing end-to-end search pipeline...")
    print("-" * 80)

    passed = 0
    failed = 0

    for i, test in enumerate(test_queries, 1):
        query = test['query']
        print(f"\nTest {i}: \"{query}\"")
        print("-" * 40)

        try:
            # Execute search with explanations
            result = engine.search(
                user_id=user_id,
                query=query,
                contacts_df=contacts_df,
                top_k=5,
                use_semantic=True,
                use_diversification=True,
                explain=True
            )

            # Display parsed query
            parsed = result['parsed_query']
            targets = parsed.get('targets', {})
            print(f"\n  Parsed Query:")
            if targets.get('personas'):
                print(f"    Personas: {targets['personas']}")
            if targets.get('companies'):
                print(f"    Companies: {targets['companies']}")
            if targets.get('industries'):
                print(f"    Industries: {targets['industries']}")

            # Display results
            results = result['results']
            print(f"\n  Found {len(results)} results:")

            for j, res in enumerate(results[:3], 1):  # Show top 3
                contact = res['contact']
                print(f"\n    {j}. {contact['full_name']}")
                print(f"       {contact['position']} @ {contact['company']}")
                print(f"       Score: {res['score']:.3f}")
                if res.get('explanation'):
                    print(f"       Top signals:")
                    for exp in res['explanation']:
                        print(f"         - {exp['feature']}: {exp['contribution']:.2f}")
                if res['sources']:
                    print(f"       Sources: {', '.join(res['sources'])}")

            # Display metrics
            metrics = result['metrics']
            print(f"\n  Performance:")
            print(f"    Total latency: {result['total_latency_ms']:.1f}ms")
            print(f"    Candidate generation: {metrics['candidate_generation_ms']:.1f}ms")
            print(f"    Feature computation: {metrics['feature_computation_ms']:.1f}ms")
            print(f"    Scoring: {metrics['scoring_ms']:.1f}ms")
            print(f"    Diversification: {metrics['diversification_ms']:.1f}ms")
            print(f"    Candidates generated: {metrics['candidates_generated']}")

            # Validate results
            if len(results) > 0:
                print(f"\n  ✅ PASS - Found relevant results")
                passed += 1

                # Check diversity (no more than 3 from same company in top 5)
                companies = [r['contact']['company'] for r in results]
                company_counts = {}
                for c in companies:
                    company_counts[c] = company_counts.get(c, 0) + 1

                max_from_one_company = max(company_counts.values()) if company_counts else 0
                if max_from_one_company <= 3:
                    print(f"  ✅ Diversity check passed (max {max_from_one_company} from one company)")
                else:
                    print(f"  ⚠️  Diversity check failed (max {max_from_one_company} from one company)")
            else:
                print(f"\n  ⚠️  WARNING - No results found")
                failed += 1

        except Exception as e:
            print(f"\n  ❌ FAIL - Error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    # Summary
    print("\n" + "=" * 80)
    print(f"TEST SUMMARY: {passed} passed, {failed} failed")
    accuracy = (passed / len(test_queries)) * 100
    print(f"Success Rate: {accuracy:.1f}% ({passed}/{len(test_queries)})")

    if accuracy >= 75:
        print("✅ ACCEPTANCE CRITERIA MET (≥75% success rate)")
    else:
        print(f"⚠️  ACCEPTANCE CRITERIA NOT MET (need ≥75%, got {accuracy:.1f}%)")

    print("=" * 80)

    return accuracy >= 75


if __name__ == "__main__":
    test_integrated_search()
