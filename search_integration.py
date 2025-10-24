"""
Search Integration for app.py
Drop-in replacement for expensive GPT search
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List
import time

# Import new search system
from search_hybrid import HybridSearchEngine, classify_query_complexity


# ============================================
# INITIALIZATION
# ============================================

def get_search_engine():
    """
    Get or create search engine instance
    Stored in session state to persist across reruns
    """
    if 'hybrid_search_engine' not in st.session_state:
        # Initialize with OpenAI client
        from app import get_client
        client = get_client()

        st.session_state['hybrid_search_engine'] = HybridSearchEngine(openai_client=client)

    return st.session_state['hybrid_search_engine']


def initialize_search_for_user(user_id: str, contacts_df: pd.DataFrame):
    """
    Build search indexes for a user
    Call this after user logs in or uploads contacts

    Args:
        user_id: User ID
        contacts_df: Contacts DataFrame
    """
    search_engine = get_search_engine()

    # Build indexes
    with st.spinner("🔨 Building search indexes..."):
        try:
            search_engine.build_indexes(user_id, contacts_df)

            # Store contacts version for cache invalidation
            if 'contacts_version' not in st.session_state:
                st.session_state['contacts_version'] = 1
            else:
                st.session_state['contacts_version'] += 1

            return True

        except Exception as e:
            st.error(f"Failed to build search indexes: {e}")
            return False


# ============================================
# SEARCH FUNCTION (Drop-in replacement)
# ============================================

def smart_search(query: str, contacts_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Intelligent search that routes to appropriate tier

    This is a drop-in replacement for the old extract_search_intent + filter_contacts flow

    Args:
        query: Search query
        contacts_df: Contacts DataFrame

    Returns:
        Dict with results compatible with old format
    """
    if not query or query.strip() == '':
        return {
            'success': False,
            'results': [],
            'tier_used': 'none',
            'message': 'Empty query'
        }

    # Get user info
    user_id = st.session_state.get('user', {}).get('id', 'default_user')
    contacts_version = st.session_state.get('contacts_version', 1)

    # Get search engine
    search_engine = get_search_engine()

    # Classify query complexity
    complexity = classify_query_complexity(query)

    # Route based on complexity
    if complexity == 'complex':
        # Use old GPT flow for complex analytics queries
        return {
            'use_legacy_gpt': True,
            'query': query,
            'complexity': complexity
        }

    # Use new hybrid search
    try:
        search_result = search_engine.search(
            user_id=user_id,
            query=query,
            contacts_df=contacts_df,
            contacts_version=contacts_version,
            top_k=50  # Get more results for better UX
        )

        # Check if we should fall back to GPT
        if search_result.get('use_legacy_gpt'):
            return {
                'use_legacy_gpt': True,
                'query': query,
                'complexity': 'complex'
            }

        # Convert to old format for compatibility
        results = search_result.get('results', [])

        # Extract contacts
        filtered_contacts = []
        for r in results:
            filtered_contacts.append(r['contact'])

        filtered_df = pd.DataFrame(filtered_contacts) if filtered_contacts else pd.DataFrame()

        return {
            'success': True,
            'results': results,
            'filtered_df': filtered_df,
            'tier_used': search_result.get('tier_used', 'unknown'),
            'latency_ms': search_result.get('latency_ms', 0),
            'cached': search_result.get('cached', False),
            'result_count': len(results),
            'complexity': complexity
        }

    except Exception as e:
        st.error(f"Search error: {e}")
        import traceback
        traceback.print_exc()

        # Fallback to GPT on error
        return {
            'use_legacy_gpt': True,
            'query': query,
            'error': str(e)
        }


# ============================================
# HELPER FUNCTIONS
# ============================================

def get_search_summary(search_result: Dict, query: str) -> str:
    """
    Generate a summary of search results

    Args:
        search_result: Result from smart_search()
        query: Original query

    Returns:
        HTML summary string
    """
    if not search_result.get('success'):
        return "No results found."

    result_count = search_result.get('result_count', 0)
    tier = search_result.get('tier_used', 'unknown')
    latency = search_result.get('latency_ms', 0)
    cached = search_result.get('cached', False)

    # Build summary
    parts = []

    # Result count
    if result_count == 0:
        parts.append("❌ No matches found")
    elif result_count == 1:
        parts.append("✅ Found 1 match")
    else:
        parts.append(f"✅ Found {result_count} matches")

    # Performance info
    perf_parts = []

    if cached:
        perf_parts.append("⚡ Instant (cached)")
    elif latency < 100:
        perf_parts.append(f"⚡ Lightning fast ({latency:.0f}ms)")
    elif latency < 500:
        perf_parts.append(f"⚡ Fast ({latency:.0f}ms)")
    else:
        perf_parts.append(f"({latency:.0f}ms)")

    # Tier info
    if tier == 'tier1_keyword':
        perf_parts.append("Keyword search")
    elif tier == 'tier1+tier2_hybrid':
        perf_parts.append("Semantic search")
    elif tier == 'tier2_semantic':
        perf_parts.append("AI semantic search")

    if perf_parts:
        parts.append(" • ".join(perf_parts))

    return " | ".join(parts)


def display_search_results(search_result: Dict, query: str):
    """
    Display search results in Streamlit

    Args:
        search_result: Result from smart_search()
        query: Original query
    """
    # Summary
    summary = get_search_summary(search_result, query)
    st.markdown(f"""
    <div class='results-summary'>
        <strong>Search Results for "{query}"</strong><br>
        {summary}
    </div>
    """, unsafe_allow_html=True)

    # Results
    results = search_result.get('results', [])

    if results:
        st.markdown("<br>", unsafe_allow_html=True)

        for i, result in enumerate(results[:20], 1):  # Show top 20
            contact = result['contact']
            score = result.get('relevance_score', 0)
            matched_fields = result.get('matched_fields', [])
            tier = result.get('search_tier', '')

            # Contact card
            with st.expander(
                f"**{i}. {contact.get('full_name', 'N/A')}** - "
                f"{contact.get('position', 'N/A')} @ {contact.get('company', 'N/A')} "
                f"(Score: {score:.2f})"
            ):
                cols = st.columns([3, 1])

                with cols[0]:
                    st.markdown(f"**Position:** {contact.get('position', 'N/A')}")
                    st.markdown(f"**Company:** {contact.get('company', 'N/A')}")
                    if contact.get('email'):
                        st.markdown(f"**Email:** {contact.get('email', 'N/A')}")

                with cols[1]:
                    st.markdown(f"**Relevance:** {score:.2f}")
                    if matched_fields:
                        st.markdown(f"**Matched:** {', '.join(matched_fields)}")
                    if tier:
                        tier_display = tier.replace('tier1', 'Keyword').replace('tier2', 'Semantic')
                        st.markdown(f"**Method:** {tier_display}")


# ============================================
# MIGRATION UTILITIES
# ============================================

def should_use_new_search() -> bool:
    """
    Determine if new search should be used
    Can be used for gradual rollout / A/B testing
    """
    # Check if search indexes exist
    user_id = st.session_state.get('user', {}).get('id')
    if not user_id:
        return False

    # Check if indexes are built
    try:
        import os
        index_file = f'faiss_index_{user_id}.bin'
        return os.path.exists(index_file)
    except:
        return False


def migrate_to_new_search():
    """
    One-time migration to build indexes for existing users
    """
    if 'user' not in st.session_state:
        return

    user_id = st.session_state['user']['id']
    contacts_df = st.session_state.get('contacts_df')

    if contacts_df is None or contacts_df.empty:
        return

    # Check if already migrated
    if should_use_new_search():
        return

    # Build indexes
    st.info("🔨 Building search indexes for faster searches...")
    success = initialize_search_for_user(user_id, contacts_df)

    if success:
        st.success("✅ Search indexes built! Future searches will be faster.")
    else:
        st.warning("⚠️  Could not build search indexes. Using legacy search.")


# Export
__all__ = [
    'get_search_engine',
    'initialize_search_for_user',
    'smart_search',
    'get_search_summary',
    'display_search_results',
    'should_use_new_search',
    'migrate_to_new_search'
]
