"""
Test AI Search Agent with dummy data
"""

import pandas as pd
import sys
import os
sys.path.insert(0, '/Users/rohangandotra/prd-to-app')

from openai import OpenAI
from services.ai_search_agent import create_ai_search_agent

# Get OpenAI API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("❌ OPENAI_API_KEY not set. Set it with:")
    print("export OPENAI_API_KEY='your-key-here'")
    sys.exit(1)

# Create OpenAI client
client = OpenAI(api_key=api_key)

# Create dummy contacts
contacts = [
    {'full_name': 'John Smith', 'company': 'Google', 'position': 'Senior Software Engineer', 'email': 'john@google.com'},
    {'full_name': 'Sarah Johnson', 'company': 'Meta', 'position': 'Product Manager', 'email': 'sarah@meta.com'},
    {'full_name': 'Alex Chen', 'company': 'Andreessen Horowitz', 'position': 'Partner', 'email': 'alex@a16z.com'},
    {'full_name': 'Maria Garcia', 'company': 'Stripe', 'position': 'Engineering Manager', 'email': 'maria@stripe.com'},
    {'full_name': 'David Lee', 'company': 'OpenAI', 'position': 'ML Researcher', 'email': 'david@openai.com'},
    {'full_name': 'Emily Brown', 'company': 'Acme Corp', 'position': 'VP of Sales', 'email': 'emily@acme.com'},
    {'full_name': 'Tom Wilson', 'company': 'Apple', 'position': 'Senior Designer', 'email': 'tom@apple.com'},
    {'full_name': 'Lisa Anderson', 'company': 'Google', 'position': 'Product Manager', 'email': 'lisa@google.com'},
    {'full_name': 'Mike Rodriguez', 'company': 'Sequoia Capital', 'position': 'Investor', 'email': 'mike@sequoiacap.com'},
    {'full_name': 'Jennifer Davis', 'company': 'Meta', 'position': 'Engineering Manager', 'email': 'jennifer@meta.com'},
]

df = pd.DataFrame(contacts)

print("Test Contacts:")
print(df[['full_name', 'company', 'position']])
print()

# Create AI agent
print("Creating AI Search Agent...")
agent = create_ai_search_agent(client, df)
print("✅ Agent created")
print()

# Test queries
test_queries = [
    "Who works at Google?",
    "Show me product managers",
    "Find engineers at Meta",
    "Who works in venture capital?",
    "Show me senior people",
]

print("=" * 80)
print("TESTING AI SEARCH AGENT")
print("=" * 80)
print()

for i, query in enumerate(test_queries, 1):
    print(f"\n{i}. Query: \"{query}\"")
    print("-" * 60)

    result = agent.search(query)

    if result['success']:
        print(f"✅ SUCCESS")
        print(f"Results found: {len(result['results'])}")
        print(f"Reasoning: {result['reasoning']}")
        print(f"Tool calls: {len(result['tool_calls'])}")
        for tc in result['tool_calls']:
            print(f"  - {tc['tool']}({tc['args']}) → {tc['results_count']} results")

        if result['results']:
            print(f"\nTop results:")
            for r in result['results'][:3]:
                print(f"  - {r['name']} • {r['position']} • {r['company']}")

        print(f"\nCost: ${result['cost_estimate']:.4f}")
    else:
        print(f"❌ FAILED: {result['reasoning']}")

    print()

print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)
