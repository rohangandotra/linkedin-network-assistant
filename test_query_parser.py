"""
Test Query Parser
Validates parser accuracy on sample queries
"""

from services.query_parser import parse_query
import json

# Test queries with expected outputs
TEST_QUERIES = [
    {
        "query": "PM at Google in SF",
        "expected": {
            "personas": ["product manager"],
            "companies": ["google"],
            "geos": ["san francisco"]
        }
    },
    {
        "query": "software engineer at Meta in New York",
        "expected": {
            "personas": ["software engineer"],
            "companies": ["meta"],
            "geos": ["new york"]
        }
    },
    {
        "query": "VP of engineering at a fintech startup",
        "expected": {
            "personas": ["vice president"],
            "industries": ["financial technology"]
        }
    },
    {
        "query": "AI researcher at Stanford",
        "expected": {
            "personas": ["ai researcher"],
            "companies": []  # Stanford not in company list (it's a university)
        }
    },
    {
        "query": "CEO in healthcare",
        "expected": {
            "personas": ["chief executive officer"],
            "industries": ["healthcare"]
        }
    },
    {
        "query": "product designer at Figma",
        "expected": {
            "personas": ["product designer"],
            "companies": ["figma"]
        }
    },
    {
        "query": "data scientist in biotech",
        "expected": {
            "personas": ["data scientist"],
            "industries": ["biotechnology"]
        }
    },
    {
        "query": "venture capital partner in Silicon Valley",
        "expected": {
            "personas": ["partner"],
            "industries": ["venture capital"],
            "geos": ["silicon valley"]
        }
    },
    {
        "query": "machine learning engineer at OpenAI",
        "expected": {
            "personas": ["machine learning engineer"],
            "companies": ["openai"]
        }
    },
    {
        "query": "founder in crypto",
        "expected": {
            "personas": ["founder"],
            "industries": ["cryptocurrency"]
        }
    },
    {
        "query": "sales at Salesforce in Austin",
        "expected": {
            "personas": ["sales"],
            "companies": ["salesforce"],
            "geos": ["austin"]
        }
    },
    {
        "query": "CTO at a SaaS company in Seattle",
        "expected": {
            "personas": ["chief technology officer"],
            "industries": ["software as a service"],
            "geos": ["seattle"]
        }
    },
    {
        "query": "investor in climate tech",
        "expected": {
            "personas": ["investor"],
            "industries": ["climate"]
        }
    },
    {
        "query": "product manager at Stripe",
        "expected": {
            "personas": ["product manager"],
            "companies": ["stripe"]
        }
    },
    {
        "query": "designer at Apple in Cupertino",
        "expected": {
            "personas": ["designer"],
            "companies": ["apple"],
            "geos": ["cupertino"]
        }
    },
    {
        "query": "engineering manager in edtech",
        "expected": {
            "personas": [],  # "engineering manager" not in our basic role list
            "industries": ["education technology"]
        }
    },
    {
        "query": "marketing at Airbnb",
        "expected": {
            "personas": ["marketing manager"],  # Will match "marketing"
            "companies": ["airbnb"]
        }
    },
    {
        "query": "SWE at Microsoft in Redmond",
        "expected": {
            "personas": ["software engineer"],  # SWE abbreviation
            "companies": ["microsoft"],
            "geos": ["redmond"]
        }
    },
    {
        "query": "VC in Boston",
        "expected": {
            "personas": [],
            "industries": ["venture capital"],  # VC abbreviation
            "geos": ["boston"]
        }
    },
    {
        "query": "recruiter in HR tech",
        "expected": {
            "personas": ["recruiter"],
            "industries": ["human resources technology"]
        }
    }
]


def test_parser():
    """Test query parser on sample queries"""
    print("=" * 80)
    print("QUERY PARSER TEST")
    print("=" * 80)

    passed = 0
    failed = 0
    partial = 0

    for i, test in enumerate(TEST_QUERIES, 1):
        query = test['query']
        expected = test['expected']

        # Parse query
        result = parse_query(query)
        actual = result['targets']

        # Check accuracy
        correct_personas = set(expected.get('personas', [])) == set(actual.get('personas', []))
        correct_companies = set(expected.get('companies', [])) == set(actual.get('companies', []))
        correct_industries = set(expected.get('industries', [])).issubset(set(actual.get('industries', [])))
        correct_geos = set(expected.get('geos', [])).issubset(set(actual.get('geos', [])))

        all_correct = correct_personas and correct_companies and correct_industries and correct_geos
        some_correct = any([correct_personas, correct_companies, correct_industries, correct_geos])

        # Update counts
        if all_correct:
            status = "✅ PASS"
            passed += 1
        elif some_correct:
            status = "⚠️  PARTIAL"
            partial += 1
        else:
            status = "❌ FAIL"
            failed += 1

        print(f"\n{i}. {status} | Query: \"{query}\"")
        print(f"   Expected: {json.dumps(expected, indent=6)}")
        print(f"   Actual:   {json.dumps(actual, indent=6)}")

        if not all_correct:
            print(f"   Personas:   {'✓' if correct_personas else '✗'}")
            print(f"   Companies:  {'✓' if correct_companies else '✗'}")
            print(f"   Industries: {'✓' if correct_industries else '✗'}")
            print(f"   Geos:       {'✓' if correct_geos else '✗'}")

    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {partial} partial, {failed} failed")
    accuracy = (passed / len(TEST_QUERIES)) * 100
    print(f"Accuracy: {accuracy:.1f}% ({passed}/{len(TEST_QUERIES)})")

    # Acceptance criteria: ≥90% accuracy
    if accuracy >= 90:
        print("✅ ACCEPTANCE CRITERIA MET (≥90% accuracy)")
    else:
        print(f"⚠️  ACCEPTANCE CRITERIA NOT MET (need ≥90%, got {accuracy:.1f}%)")

    print("=" * 80)

    return accuracy >= 90


if __name__ == "__main__":
    test_parser()
