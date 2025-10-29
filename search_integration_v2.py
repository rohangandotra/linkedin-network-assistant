"""
Search Integration for app.py (Version 2 - Using IntegratedSearchEngine)
Drop-in replacement for expensive GPT search using new 4-stage pipeline
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any, List
import time

# Import new integrated search system
from services.integrated_search import IntegratedSearchEngine


# ============================================
# INITIALIZATION
# ============================================

def get_search_engine():
    """
    Get or create search engine instance
    Stored in session state to persist across reruns
    """
    # Check if we need to recreate the engine (e.g., after code update)
    needs_recreation = False

    if 'integrated_search_engine' not in st.session_state:
        needs_recreation = True
    else:
        # Check if the instance has the new methods (indexes_exist, load_indexes)
        engine = st.session_state['integrated_search_engine']
        if not hasattr(engine, 'indexes_exist') or not hasattr(engine, 'load_indexes'):
            print("⚠️  Detected old search engine instance, recreating...")
            needs_recreation = True

    if needs_recreation:
        # Initialize with OpenAI client (for LLM fallback in parser)
        try:
            from app import get_client
            client = get_client()
        except:
            client = None

        st.session_state['integrated_search_engine'] = IntegratedSearchEngine(openai_client=client)

    return st.session_state['integrated_search_engine']


def initialize_search_for_user(user_id: str, contacts_df: pd.DataFrame, force_rebuild: bool = False):
    """
    Initialize search indexes for a user with three-tier caching

    Three-tier caching strategy:
    - L1 Cache (Session State): Instant, lasts for session
    - L2 Cache (Disk): ~500ms, lasts until app restart
    - L3 Cache (Rebuild): 2-5s, when both fail

    Args:
        user_id: User ID
        contacts_df: Contacts DataFrame
        force_rebuild: Force rebuild indexes even if cached

    Returns:
        True if indexes are ready, False otherwise
    """
    search_engine = get_search_engine()

    # Check current contacts version
    current_version = st.session_state.get('contacts_version', 0)
    stored_user_id = st.session_state.get('indexed_user_id', None)

    # L1 Cache: Check session state (already in memory)
    if not force_rebuild and stored_user_id == user_id:
        # Indexes already loaded in this session
        print(f"✅ L1 Cache HIT: Using in-memory indexes for user {user_id}")
        return True

    # L2 Cache: Check disk
    if not force_rebuild and search_engine.indexes_exist(user_id):
        with st.spinner("Loading search indexes from cache..."):
            try:
                success = search_engine.load_indexes(user_id)
                if success:
                    # Store in session state for L1 cache
                    st.session_state['indexed_user_id'] = user_id
                    if 'contacts_version' not in st.session_state:
                        st.session_state['contacts_version'] = current_version + 1

                    print(f"✅ L2 Cache HIT: Loaded indexes from disk for user {user_id}")
                    st.success("Search indexes loaded! Searches will be fast.")
                    return True
                else:
                    print(f"⚠️  L2 Cache MISS: Failed to load from disk, rebuilding...")
            except Exception as e:
                print(f"⚠️  L2 Cache MISS: Error loading from disk: {e}")

    # L3 Cache: Rebuild indexes from scratch
    with st.spinner("Building search indexes for faster searches..."):
        try:
            search_engine.build_indexes(user_id, contacts_df)

            # Store in session state for L1 cache
            st.session_state['indexed_user_id'] = user_id
            st.session_state['contacts_version'] = current_version + 1

            print(f"✅ L3 Cache: Built new indexes for user {user_id}")
            return True

        except Exception as e:
            st.error(f"Failed to build search indexes: {e}")
            import traceback
            traceback.print_exc()
            return False


# ============================================
# SEARCH FUNCTION (Drop-in replacement)
# ============================================

def smart_search(query: str, contacts_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Intelligent search using new 4-stage pipeline

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

    # Get search engine
    search_engine = get_search_engine()

    # Execute search
    try:
        search_result = search_engine.search(
            user_id=user_id,
            query=query,
            contacts_df=contacts_df,
            top_k=20,  # Return top 20 results
            use_semantic=True,
            use_diversification=True,
            explain=False  # Don't need explanations in UI for now
        )

        # Check if search succeeded
        if not search_result.get('success'):
            return {
                'success': False,
                'results': [],
                'tier_used': 'integrated_search',
                'message': search_result.get('message', 'Search failed')
            }

        # Convert to old format for compatibility
        results = search_result.get('results', [])

        # Extract contacts for filtered_df
        filtered_contacts = []
        for r in results:
            contact = r['contact'].copy()
            contact['relevance_score'] = r.get('score', 0)
            filtered_contacts.append(contact)

        filtered_df = pd.DataFrame(filtered_contacts) if filtered_contacts else pd.DataFrame()

        # Determine tier used (for analytics)
        metrics = search_result.get('metrics', {})
        tier_used = 'integrated_search'  # Our new 4-stage pipeline

        return {
            'success': True,
            'results': results,
            'filtered_df': filtered_df,
            'tier_used': tier_used,
            'latency_ms': search_result.get('total_latency_ms', 0),
            'cached': False,  # No caching yet in v1
            'result_count': len(results),
            'parsed_query': search_result.get('parsed_query', {}),
            'metrics': metrics
        }

    except Exception as e:
        st.error(f"Search error: {e}")
        import traceback
        traceback.print_exc()

        # Return error response
        return {
            'success': False,
            'results': [],
            'tier_used': 'error',
            'error': str(e),
            'message': f'Search failed: {str(e)}'
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

    # Build summary
    parts = []

    # Result count
    if result_count == 0:
        parts.append("No matches found")
    elif result_count == 1:
        parts.append("Found 1 match")
    else:
        parts.append(f"Found {result_count} matches")

    # Performance info
    perf_parts = []

    if latency < 100:
        perf_parts.append(f"Lightning fast ({latency:.0f}ms)")
    elif latency < 500:
        perf_parts.append(f"Fast ({latency:.0f}ms)")
    else:
        perf_parts.append(f"({latency:.0f}ms)")

    # Method info
    if tier == 'integrated_search':
        perf_parts.append("Advanced multi-signal ranking")

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
            score = result.get('score', 0)
            matched_fields = result.get('matched_fields', [])
            sources = result.get('sources', [])

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
                    if sources:
                        source_display = ', '.join(s.replace('tier1', 'Keyword').replace('tier2', 'Semantic') for s in sources)
                        st.markdown(f"**Method:** {source_display}")


# ============================================
# MIGRATION UTILITIES
# ============================================

def should_use_new_search() -> bool:
    """
    Determine if new search should be used
    Always returns True since this IS the new search
    """
    return True


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

    # Build indexes
    st.info("Building search indexes for faster searches...")
    success = initialize_search_for_user(user_id, contacts_df)

    if success:
        st.success("Search indexes built! Searches will now be faster.")
    else:
        st.warning("Could not build search indexes. Search may be slower.")


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
