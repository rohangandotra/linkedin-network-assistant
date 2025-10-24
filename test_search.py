"""
Test Search System
Run this to test the new hybrid search engine
"""

import pandas as pd
import sys
from search_hybrid import HybridSearchEngine
from search_evaluation import SearchEvaluator


def test_search_interactive(user_id: str, contacts_file: str):
    """
    Interactive search testing

    Args:
        user_id: User ID
        contacts_file: Path to contacts CSV
    """
    print("="*60)
    print("INTERACTIVE SEARCH TESTING")
    print("="*60)

    # Load contacts
    try:
        contacts_df = pd.read_csv(contacts_file)
        print(f"✅ Loaded {len(contacts_df)} contacts\n")
    except Exception as e:
        print(f"❌ Failed to load contacts: {e}")
        return

    # Normalize column names
    if 'Full Name' in contacts_df.columns:
        contacts_df['full_name'] = contacts_df['Full Name']
    if 'Company' in contacts_df.columns:
        contacts_df['company'] = contacts_df['Company']
    if 'Position' in contacts_df.columns:
        contacts_df['position'] = contacts_df['Position']
    if 'Email Address' in contacts_df.columns:
        contacts_df['email'] = contacts_df['Email Address']

    # Initialize search engine
    search_engine = HybridSearchEngine()

    # Build indexes
    print("Building search indexes...")
    try:
        search_engine.build_indexes(user_id, contacts_df)
        print("✅ Indexes built\n")
    except Exception as e:
        print(f"❌ Failed to build indexes: {e}")
        return

    contacts_version = 1

    # Interactive search loop
    print("Enter search queries (or 'quit' to exit):\n")

    while True:
        query = input("Search: ").strip()

        if query.lower() in ['quit', 'exit', 'q']:
            break

        if not query:
            continue

        try:
            # Run search
            result = search_engine.search(
                user_id=user_id,
                query=query,
                contacts_df=contacts_df,
                contacts_version=contacts_version,
                top_k=10
            )

            # Display results
            print("\n" + "-"*60)
            print(f"Query: '{query}'")
            print(f"Tier: {result.get('tier_used', 'unknown')}")
            print(f"Latency: {result.get('latency_ms', 0):.1f}ms")
            print(f"Results: {result.get('result_count', 0)}")
            print(f"Cached: {'Yes' if result.get('cached') else 'No'}")

            if result.get('results'):
                print("\nTop Results:")
                for i, r in enumerate(result['results'][:5], 1):
                    contact = r['contact']
                    score = r.get('relevance_score', 0)
                    matched = r.get('matched_fields', [])

                    name = contact.get('full_name', 'N/A')
                    company = contact.get('company', 'N/A')
                    position = contact.get('position', 'N/A')

                    print(f"\n  {i}. {name}")
                    print(f"     {position} @ {company}")
                    print(f"     Score: {score:.3f} | Matched: {', '.join(matched)}")
            else:
                print("\nNo results found")

            print("-"*60 + "\n")

        except Exception as e:
            print(f"\n❌ Search error: {e}\n")
            import traceback
            traceback.print_exc()

    # Print cache stats
    stats = search_engine.get_cache_stats()
    print("\n" + "="*60)
    print("CACHE STATISTICS")
    print("="*60)
    print(f"Hits: {stats['hits']}")
    print(f"Misses: {stats['misses']}")
    print(f"Hit Rate: {stats['hit_rate']*100:.1f}%")
    print(f"Cache Size: {stats['size']}")
    print("="*60)


def run_evaluation(user_id: str, contacts_file: str):
    """
    Run full evaluation with golden test set

    Args:
        user_id: User ID
        contacts_file: Path to contacts CSV
    """
    print("="*60)
    print("RUNNING SEARCH EVALUATION")
    print("="*60)

    # Load contacts
    try:
        contacts_df = pd.read_csv(contacts_file)
        print(f"✅ Loaded {len(contacts_df)} contacts\n")
    except Exception as e:
        print(f"❌ Failed to load contacts: {e}")
        return

    # Normalize column names
    if 'Full Name' in contacts_df.columns:
        contacts_df['full_name'] = contacts_df['Full Name']
    if 'Company' in contacts_df.columns:
        contacts_df['company'] = contacts_df['Company']
    if 'Position' in contacts_df.columns:
        contacts_df['position'] = contacts_df['Position']
    if 'Email Address' in contacts_df.columns:
        contacts_df['email'] = contacts_df['Email Address']

    # Initialize search engine
    search_engine = HybridSearchEngine()

    # Build indexes
    print("Building search indexes...")
    search_engine.build_indexes(user_id, contacts_df)
    print("✅ Indexes built\n")

    contacts_version = 1

    # Create search function wrapper
    def search_fn(user_id, query, contacts_df, contacts_version):
        return search_engine.search(user_id, query, contacts_df, contacts_version)

    # Run evaluation
    evaluator = SearchEvaluator()
    eval_results = evaluator.evaluate(
        search_function=search_fn,
        user_id=user_id,
        contacts_df=contacts_df,
        contacts_version=contacts_version
    )

    # Save results
    import json
    with open('search_evaluation_results.json', 'w') as f:
        json.dump(eval_results, f, indent=2)

    print("\n✅ Evaluation results saved to: search_evaluation_results.json")


def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  Interactive: python test_search.py <user_id> <contacts.csv>")
        print("  Evaluation:  python test_search.py <user_id> <contacts.csv> --eval")
        print("\nExample:")
        print("  python test_search.py user123 sample_contacts.csv")
        sys.exit(1)

    user_id = sys.argv[1]
    contacts_file = sys.argv[2]
    run_eval = '--eval' in sys.argv

    if run_eval:
        run_evaluation(user_id, contacts_file)
    else:
        test_search_interactive(user_id, contacts_file)


if __name__ == '__main__':
    main()
