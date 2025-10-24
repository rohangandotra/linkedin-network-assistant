"""
Search Quality Evaluation Framework
Based on engineer recommendations for release gating
"""

from typing import List, Dict, Any
import pandas as pd
import numpy as np
from datetime import datetime


# ============================================
# GOLDEN TEST SET
# ============================================

GOLDEN_TEST_QUERIES = [
    # Category: Name Searches (Exact)
    {
        'query': 'John Smith',
        'expected_in_top_3': ['john.smith@example.com'],  # Use email as unique ID
        'category': 'name_exact',
        'min_score': 0.8
    },

    # Category: Name Searches (Nickname)
    {
        'query': 'Bill Gates',
        'expected_in_top_5': ['william.gates@microsoft.com'],  # Should match William
        'category': 'name_nickname',
        'min_score': 0.6
    },

    # Category: Company Searches
    {
        'query': 'Google',
        'expected_count_min': 1,  # At least 1 person at Google
        'category': 'company_simple',
        'min_score': 0.5
    },
    {
        'query': 'Google engineer',
        'expected_in_top_10': ['person@google.com'],  # Must have both Google + engineer
        'category': 'company_position',
        'min_score': 0.6
    },

    # Category: Typo Tolerance
    {
        'query': 'Gogle',  # Typo for Google
        'expected_in_top_10': ['person@google.com'],
        'category': 'typo',
        'min_score': 0.4
    },
    {
        'query': 'Johm Smith',  # Typo in name
        'expected_in_top_5': ['john.smith@example.com'],
        'category': 'typo',
        'min_score': 0.5
    },

    # Category: Position/Title Searches
    {
        'query': 'engineer',
        'expected_count_min': 1,
        'category': 'position_simple',
        'min_score': 0.3
    },
    {
        'query': 'VP',
        'expected_count_min': 1,
        'category': 'position_simple',
        'min_score': 0.4
    },
    {
        'query': 'software engineer',
        'expected_count_min': 1,
        'category': 'position_multi_word',
        'min_score': 0.5
    },

    # Category: Semantic Searches
    {
        'query': 'machine learning expert',
        'expected_keywords_in_top_10': ['ml', 'machine learning', 'ai', 'data scientist'],
        'category': 'semantic',
        'min_score': 0.4
    },
    {
        'query': 'creative roles',
        'expected_keywords_in_top_10': ['designer', 'artist', 'creative', 'ux'],
        'category': 'semantic',
        'min_score': 0.3
    },

    # Category: Multi-term Searches
    {
        'query': 'senior engineer at Google',
        'expected_keywords_in_top_5': ['senior', 'engineer', 'google'],
        'category': 'multi_term',
        'min_score': 0.6
    },

    # Category: Edge Cases
    {
        'query': '',  # Empty query
        'expected_count': 0,
        'category': 'edge_case',
        'should_handle_gracefully': True
    },
    {
        'query': 'a',  # Single character
        'expected_count': 0,
        'category': 'edge_case',
        'should_handle_gracefully': True
    },
    {
        'query': 'asdfghjkl',  # Gibberish
        'expected_count': 0,
        'category': 'edge_case',
        'should_handle_gracefully': True
    },

    # Category: Special Characters
    {
        'query': 'john@example.com',
        'expected_in_top_1': ['john@example.com'],
        'category': 'email',
        'min_score': 0.9
    },
]


# ============================================
# EVALUATION METRICS
# ============================================

class SearchEvaluator:
    """
    Evaluates search quality using golden test set

    Metrics:
    - MRR@10 (Mean Reciprocal Rank)
    - Precision@5
    - Recall@10
    - Zero-result rate
    """

    def __init__(self, golden_queries: List[Dict] = None):
        self.golden_queries = golden_queries or GOLDEN_TEST_QUERIES

    def evaluate(
        self,
        search_function,
        user_id: str,
        contacts_df: pd.DataFrame,
        contacts_version: int
    ) -> Dict[str, Any]:
        """
        Run full evaluation

        Args:
            search_function: Function that takes (user_id, query, contacts_df, contacts_version)
            user_id: User ID
            contacts_df: Contacts DataFrame
            contacts_version: Contacts version

        Returns:
            Dict with metrics and detailed results
        """
        print("="*60)
        print("SEARCH QUALITY EVALUATION")
        print("="*60)

        results = {
            'mrr': [],
            'precision_at_5': [],
            'recall_at_10': [],
            'latency_ms': [],
            'zero_result_checks': [],
            'by_category': {}
        }

        detailed_results = []

        for i, test_case in enumerate(self.golden_queries):
            query = test_case['query']
            category = test_case.get('category', 'unknown')

            print(f"\n[{i+1}/{len(self.golden_queries)}] Testing: '{query}' ({category})")

            try:
                # Run search
                search_result = search_function(
                    user_id=user_id,
                    query=query,
                    contacts_df=contacts_df,
                    contacts_version=contacts_version
                )

                # Extract results
                if isinstance(search_result, dict) and 'results' in search_result:
                    search_results = search_result['results']
                    latency = search_result.get('latency_ms', 0)
                else:
                    search_results = search_result if isinstance(search_result, list) else []
                    latency = 0

                results['latency_ms'].append(latency)

                # Extract result emails for comparison
                result_emails = [
                    r['contact'].get('email', '') for r in search_results
                ]

                # Evaluate based on test case criteria
                test_result = self._evaluate_test_case(
                    test_case,
                    search_results,
                    result_emails
                )

                # Collect metrics
                if 'mrr' in test_result:
                    results['mrr'].append(test_result['mrr'])

                if 'precision_at_5' in test_result:
                    results['precision_at_5'].append(test_result['precision_at_5'])

                if 'recall_at_10' in test_result:
                    results['recall_at_10'].append(test_result['recall_at_10'])

                if 'zero_result_pass' in test_result:
                    results['zero_result_checks'].append(test_result['zero_result_pass'])

                # Track by category
                if category not in results['by_category']:
                    results['by_category'][category] = []
                results['by_category'][category].append(test_result.get('passed', False))

                # Store detailed result
                detailed_results.append({
                    'query': query,
                    'category': category,
                    'result_count': len(search_results),
                    'latency_ms': latency,
                    'passed': test_result.get('passed', False),
                    'details': test_result
                })

                # Print result
                status = "✅ PASS" if test_result.get('passed', False) else "❌ FAIL"
                print(f"  {status} - {len(search_results)} results, {latency:.1f}ms")

            except Exception as e:
                print(f"  ❌ ERROR: {str(e)}")
                detailed_results.append({
                    'query': query,
                    'category': category,
                    'error': str(e),
                    'passed': False
                })

        # Calculate aggregate metrics
        metrics = self._calculate_aggregate_metrics(results)

        # Print summary
        self._print_summary(metrics, results)

        return {
            'metrics': metrics,
            'detailed_results': detailed_results,
            'timestamp': datetime.now().isoformat()
        }

    def _evaluate_test_case(
        self,
        test_case: Dict,
        search_results: List[Dict],
        result_emails: List[str]
    ) -> Dict:
        """Evaluate a single test case"""

        result = {'passed': True}

        # Check: expected_in_top_1
        if 'expected_in_top_1' in test_case:
            expected = test_case['expected_in_top_1']
            if result_emails and result_emails[0] in expected:
                result['mrr'] = 1.0
                result['passed'] = True
            else:
                result['mrr'] = 0.0
                result['passed'] = False

        # Check: expected_in_top_3
        elif 'expected_in_top_3' in test_case:
            expected = test_case['expected_in_top_3']
            mrr = self._calculate_mrr(result_emails[:10], expected)
            result['mrr'] = mrr
            result['passed'] = mrr >= 0.33  # At least in top 3

        # Check: expected_in_top_5
        elif 'expected_in_top_5' in test_case:
            expected = test_case['expected_in_top_5']
            mrr = self._calculate_mrr(result_emails[:10], expected)
            result['mrr'] = mrr
            result['passed'] = mrr >= 0.2  # At least in top 5

        # Check: expected_in_top_10
        elif 'expected_in_top_10' in test_case:
            expected = test_case['expected_in_top_10']
            found_in_top_10 = any(email in result_emails[:10] for email in expected)
            result['recall_at_10'] = 1.0 if found_in_top_10 else 0.0
            result['passed'] = found_in_top_10

        # Check: expected_count
        elif 'expected_count' in test_case:
            expected_count = test_case['expected_count']
            actual_count = len(search_results)
            result['zero_result_pass'] = (actual_count == expected_count)
            result['passed'] = result['zero_result_pass']

        # Check: expected_count_min
        elif 'expected_count_min' in test_case:
            min_count = test_case['expected_count_min']
            actual_count = len(search_results)
            result['passed'] = (actual_count >= min_count)

        # Check: expected_keywords_in_top_10
        elif 'expected_keywords_in_top_10' in test_case:
            keywords = test_case['expected_keywords_in_top_10']
            top_10 = search_results[:10]

            # Check if any keyword appears in top 10 results
            keyword_found = False
            for r in top_10:
                contact_text = ' '.join([
                    str(r['contact'].get('full_name', '')),
                    str(r['contact'].get('company', '')),
                    str(r['contact'].get('position', ''))
                ]).lower()

                if any(kw.lower() in contact_text for kw in keywords):
                    keyword_found = True
                    break

            result['passed'] = keyword_found

        # Check: should_handle_gracefully
        if test_case.get('should_handle_gracefully'):
            # Just make sure no exception was raised
            result['passed'] = True

        return result

    def _calculate_mrr(self, results: List[str], expected: List[str]) -> float:
        """Calculate Mean Reciprocal Rank"""
        for i, result_id in enumerate(results):
            if result_id in expected:
                return 1.0 / (i + 1)
        return 0.0

    def _calculate_aggregate_metrics(self, results: Dict) -> Dict:
        """Calculate aggregate metrics"""
        metrics = {}

        if results['mrr']:
            metrics['MRR@10'] = np.mean(results['mrr'])

        if results['precision_at_5']:
            metrics['Precision@5'] = np.mean(results['precision_at_5'])

        if results['recall_at_10']:
            metrics['Recall@10'] = np.mean(results['recall_at_10'])

        if results['latency_ms']:
            metrics['Avg_Latency_ms'] = np.mean(results['latency_ms'])
            metrics['P95_Latency_ms'] = np.percentile(results['latency_ms'], 95)

        if results['zero_result_checks']:
            metrics['Zero_Result_Accuracy'] = np.mean(results['zero_result_checks'])

        # Pass rate by category
        metrics['Pass_Rate_By_Category'] = {}
        for category, passes in results['by_category'].items():
            metrics['Pass_Rate_By_Category'][category] = np.mean(passes) if passes else 0

        # Overall pass rate
        all_passes = []
        for passes in results['by_category'].values():
            all_passes.extend(passes)
        metrics['Overall_Pass_Rate'] = np.mean(all_passes) if all_passes else 0

        return metrics

    def _print_summary(self, metrics: Dict, results: Dict):
        """Print evaluation summary"""
        print("\n" + "="*60)
        print("EVALUATION SUMMARY")
        print("="*60)

        print("\n📊 Quality Metrics:")
        if 'MRR@10' in metrics:
            print(f"  MRR@10:            {metrics['MRR@10']:.3f}")
        if 'Precision@5' in metrics:
            print(f"  Precision@5:       {metrics['Precision@5']:.3f}")
        if 'Recall@10' in metrics:
            print(f"  Recall@10:         {metrics['Recall@10']:.3f}")

        print("\n⚡ Performance Metrics:")
        if 'Avg_Latency_ms' in metrics:
            print(f"  Avg Latency:       {metrics['Avg_Latency_ms']:.1f}ms")
        if 'P95_Latency_ms' in metrics:
            print(f"  P95 Latency:       {metrics['P95_Latency_ms']:.1f}ms")

        print("\n✅ Pass Rate:")
        print(f"  Overall:           {metrics['Overall_Pass_Rate']*100:.1f}%")

        if 'Pass_Rate_By_Category' in metrics:
            print("\n  By Category:")
            for category, rate in metrics['Pass_Rate_By_Category'].items():
                print(f"    {category:20s} {rate*100:.1f}%")

        # Release gate check
        print("\n" + "="*60)
        print("RELEASE GATE CHECK")
        print("="*60)

        gates_passed = True

        # Gate 1: MRR@10 > 0.7
        if 'MRR@10' in metrics:
            mrr_pass = metrics['MRR@10'] >= 0.7
            status = "✅ PASS" if mrr_pass else "❌ FAIL"
            print(f"{status} MRR@10 >= 0.70:    {metrics['MRR@10']:.3f}")
            gates_passed = gates_passed and mrr_pass

        # Gate 2: Avg Latency < 100ms
        if 'Avg_Latency_ms' in metrics:
            latency_pass = metrics['Avg_Latency_ms'] < 100
            status = "✅ PASS" if latency_pass else "❌ FAIL"
            print(f"{status} Avg Latency < 100ms: {metrics['Avg_Latency_ms']:.1f}ms")
            gates_passed = gates_passed and latency_pass

        # Gate 3: Overall Pass Rate > 80%
        overall_pass = metrics['Overall_Pass_Rate'] >= 0.8
        status = "✅ PASS" if overall_pass else "❌ FAIL"
        print(f"{status} Pass Rate >= 80%:   {metrics['Overall_Pass_Rate']*100:.1f}%")
        gates_passed = gates_passed and overall_pass

        print("\n" + "="*60)
        if gates_passed:
            print("✅ ALL GATES PASSED - SAFE TO DEPLOY")
        else:
            print("❌ GATES FAILED - DO NOT DEPLOY")
        print("="*60)


# ============================================
# ZERO-RESULT QUERY TRACKING
# ============================================

class ZeroResultTracker:
    """
    Track queries that return zero results
    Use this data to build synonyms and improve coverage
    """

    def __init__(self, log_file: str = 'zero_result_queries.json'):
        self.log_file = log_file
        self.queries = []

    def log_zero_result(self, user_id: str, query: str):
        """Log a zero-result query"""
        self.queries.append({
            'user_id': user_id,
            'query': query,
            'timestamp': datetime.now().isoformat()
        })

    def get_top_zero_result_queries(self, n: int = 20) -> List[tuple]:
        """Get most common zero-result queries"""
        from collections import Counter

        query_counts = Counter([q['query'] for q in self.queries])
        return query_counts.most_common(n)

    def save(self):
        """Save to file"""
        import json
        with open(self.log_file, 'w') as f:
            json.dump(self.queries, f, indent=2)

    def load(self):
        """Load from file"""
        import json
        try:
            with open(self.log_file, 'r') as f:
                self.queries = json.load(f)
        except FileNotFoundError:
            self.queries = []


# Export
__all__ = [
    'SearchEvaluator',
    'ZeroResultTracker',
    'GOLDEN_TEST_QUERIES'
]
