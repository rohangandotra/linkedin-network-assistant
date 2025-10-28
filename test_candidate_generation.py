"""
Test Candidate Generation
Validates FTS5 + FAISS candidate generation with query parser integration
"""

import pandas as pd
import numpy as np
from services.candidate_generator import CandidateGenerator
import time


# Sample contacts data
SAMPLE_CONTACTS = [
    {
        'full_name': 'John Smith',
        'email': 'john.smith@google.com',
        'company': 'Google',
        'position': 'Senior Product Manager'
    },
    {
        'full_name': 'Sarah Johnson',
        'email': 'sarah.j@meta.com',
        'company': 'Meta',
        'position': 'Software Engineer'
    },
    {
        'full_name': 'Mike Chen',
        'email': 'mchen@microsoft.com',
        'company': 'Microsoft',
        'position': 'Principal Software Engineer'
    },
    {
        'full_name': 'Emily Davis',
        'email': 'emily@stripe.com',
        'company': 'Stripe',
        'position': 'Engineering Manager'
    },
    {
        'full_name': 'David Lee',
        'email': 'dlee@openai.com',
        'company': 'OpenAI',
        'position': 'Machine Learning Engineer'
    },
    {
        'full_name': 'Jessica Brown',
        'email': 'jbrown@salesforce.com',
        'company': 'Salesforce',
        'position': 'VP of Sales'
    },
    {
        'full_name': 'Tom Wilson',
        'email': 'twilson@apple.com',
        'company': 'Apple',
        'position': 'Senior Designer'
    },
    {
        'full_name': 'Lisa Martinez',
        'email': 'lisa@figma.com',
        'company': 'Figma',
        'position': 'Product Designer'
    },
    {
        'full_name': 'Chris Anderson',
        'email': 'canderson@netflix.com',
        'company': 'Netflix',
        'position': 'Data Scientist'
    },
    {
        'full_name': 'Amanda Taylor',
        'email': 'ataylor@airbnb.com',
        'company': 'Airbnb',
        'position': 'Software Engineer'
    },
    {
        'full_name': 'Robert Garcia',
        'email': 'rgarcia@sequoia.com',
        'company': 'Sequoia Capital',
        'position': 'Partner'
    },
    {
        'full_name': 'Jennifer Kim',
        'email': 'jkim@a16z.com',
        'company': 'Andreessen Horowitz',
        'position': 'Partner'
    },
    {
        'full_name': 'Michael Zhang',
        'email': 'mzhang@tesla.com',
        'company': 'Tesla',
        'position': 'Senior Software Engineer'
    },
    {
        'full_name': 'Ashley White',
        'email': 'awhite@uber.com',
        'company': 'Uber',
        'position': 'Product Manager'
    },
    {
        'full_name': 'James Rodriguez',
        'email': 'jrodriguez@coinbase.com',
        'company': 'Coinbase',
        'position': 'Engineering Manager'
    }
]


def test_candidate_generation():
    """Test candidate generation with query parser integration"""
    print("=" * 80)
    print("CANDIDATE GENERATION TEST")
    print("=" * 80)

    # Create sample DataFrame
    contacts_df = pd.DataFrame(SAMPLE_CONTACTS)
    user_id = 'test_user'

    # Initialize candidate generator
    print("\n1. Initializing candidate generator...")
    generator = CandidateGenerator()

    # Build indexes
    print("\n2. Building search indexes...")
    try:
        generator.build_indexes(user_id, contacts_df)
        print("✅ Indexes built successfully")
    except Exception as e:
        print(f"❌ Failed to build indexes: {e}")
        print("\nNote: Semantic search requires:")
        print("  pip install sentence-transformers faiss-cpu")
        print("\nContinuing with keyword search only...")

    # Test queries
    test_queries = [
        "PM at Google",
        "software engineer at Meta",
        "machine learning engineer",
        "venture capital partner",
        "designer at Apple",
        "VP of sales"
    ]

    print("\n3. Testing candidate generation...")
    print("-" * 80)

    for i, query in enumerate(test_queries, 1):
        print(f"\nTest {i}: \"{query}\"")
        print("-" * 40)

        try:
            # Generate candidates
            start_time = time.time()
            result = generator.generate_candidates(
                user_id=user_id,
                query=query,
                contacts_df=contacts_df,
                top_k=5,
                use_semantic=True  # Try semantic, will gracefully fall back if unavailable
            )
            latency = (time.time() - start_time) * 1000

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
            if targets.get('geos'):
                print(f"    Geos: {targets['geos']}")

            # Display candidates
            candidates = result['candidates']
            print(f"\n  Found {len(candidates)} candidates:")

            for j, cand in enumerate(candidates[:3], 1):  # Show top 3
                contact = cand['contact']
                print(f"\n    {j}. {contact['full_name']}")
                print(f"       {contact['position']} @ {contact['company']}")
                print(f"       Score: {cand['combined_score']:.3f} (FTS5: {cand['tier1_score']:.3f}, Semantic: {cand['tier2_score']:.3f})")
                if cand['matched_fields']:
                    print(f"       Matched: {', '.join(cand['matched_fields'])}")
                print(f"       Sources: {', '.join(cand['sources'])}")

            # Display metrics
            metrics = result['metrics']
            provenance = result['provenance']

            print(f"\n  Performance:")
            print(f"    Total latency: {metrics['total_latency_ms']:.1f}ms")
            print(f"    Parse time: {metrics['parse_time_ms']:.1f}ms")
            print(f"    FTS5 time: {metrics['tier1_time_ms']:.1f}ms")
            print(f"    Semantic time: {metrics['tier2_time_ms']:.1f}ms")

            print(f"\n  Provenance:")
            print(f"    FTS5 only: {provenance['tier1_only']}")
            print(f"    Semantic only: {provenance['tier2_only']}")
            print(f"    Both: {provenance['both_tiers']}")

            # Success check
            if len(candidates) > 0:
                print(f"\n  ✅ PASS - Found relevant candidates")
            else:
                print(f"\n  ⚠️  WARNING - No candidates found")

        except Exception as e:
            print(f"\n  ❌ FAIL - Error: {e}")
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    test_candidate_generation()
