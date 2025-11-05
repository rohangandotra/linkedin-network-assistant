"""
Agentic Search Integration for app.py
Drop-in replacement that uses GPT-4 agent for all searches

Includes streaming responses and pre-caching for better performance
"""

import streamlit as st
import pandas as pd
from typing import Dict, Any
import time

from services.search_agent import (
    get_search_agent,
    NetworkSearchAgent,
    pre_cache_popular_queries,
    clear_tool_cache,
    get_cache_stats
)


def agentic_search(query: str, contacts_df: pd.DataFrame, openai_client) -> Dict[str, Any]:
    """
    Execute agentic search using GPT-4 with tools

    This is a drop-in replacement for smart_search() in search_integration.py

    Args:
        query: Search query
        contacts_df: Contacts DataFrame
        openai_client: OpenAI client instance

    Returns:
        Dict with results compatible with existing app.py format
    """
    if not query or query.strip() == '':
        return {
            'success': False,
            'results': [],
            'filtered_df': pd.DataFrame(),
            'message': 'Empty query',
            'reasoning': None,
            'cost_estimate': 0
        }

    try:
        # Get agent instance
        agent = get_search_agent(openai_client, contacts_df)

        # Execute search
        search_result = agent.search(query, max_iterations=5)

        # Check if cached
        if search_result.get('cached'):
            # Return cached result immediately
            return _format_result(search_result, query)

        # Format result for app.py compatibility
        return _format_result(search_result, query)

    except Exception as e:
        st.error(f"Agent search error: {e}")
        import traceback
        traceback.print_exc()

        return {
            'success': False,
            'results': [],
            'filtered_df': pd.DataFrame(),
            'message': f'Search failed: {str(e)}',
            'reasoning': None,
            'cost_estimate': 0
        }


def _format_result(search_result: Dict, query: str) -> Dict[str, Any]:
    """
    Format agent result for app.py compatibility

    Args:
        search_result: Result from NetworkSearchAgent
        query: Original query

    Returns:
        Formatted result dict
    """
    contacts = search_result.get('results', [])

    # Convert to DataFrame
    if contacts:
        # Map agent format to app.py format
        formatted_contacts = []
        for contact in contacts:
            formatted_contacts.append({
                'First Name': contact.get('name', '').split()[0] if contact.get('name') else '',
                'Last Name': ' '.join(contact.get('name', '').split()[1:]) if contact.get('name') else '',
                'Company': contact.get('company', 'Unknown'),
                'Position': contact.get('position', 'Unknown'),
                'Email Address': contact.get('email', ''),
                'Connected On': contact.get('connected_on', ''),
            })

        filtered_df = pd.DataFrame(formatted_contacts)
    else:
        filtered_df = pd.DataFrame()

    return {
        'success': True,
        'results': contacts,
        'filtered_df': filtered_df,
        'tier_used': 'agentic',
        'latency_ms': search_result.get('latency_ms', 0),
        'cached': search_result.get('cached', False),
        'result_count': len(contacts),
        'reasoning': search_result.get('reasoning', ''),
        'tool_calls': search_result.get('tool_calls', []),
        'iterations': search_result.get('iterations', 0),
        'cost_estimate': search_result.get('cost_estimate', 0),
        'query': query
    }


def display_agent_reasoning(search_result: Dict):
    """
    Display agent reasoning and tool usage in UI

    Args:
        search_result: Result from agentic_search()
    """
    if not search_result.get('success'):
        return

    reasoning = search_result.get('reasoning', '')
    tool_calls = search_result.get('tool_calls', [])
    iterations = search_result.get('iterations', 0)
    cost_estimate = search_result.get('cost_estimate', 0)
    cached = search_result.get('cached', False)

    # Show performance badge
    if cached:
        st.success(f"⚡ Instant (cached) • {search_result.get('result_count', 0)} results • $0.00")
    else:
        latency = search_result.get('latency_ms', 0)
        st.success(f"🤖 AI Search • {search_result.get('result_count', 0)} results • {latency:.0f}ms • ${cost_estimate:.4f}")

    # Show reasoning in expander
    if reasoning and not cached:
        with st.expander("🧠 How AI found these results", expanded=False):
            st.markdown(reasoning)

            # Show tool usage
            if tool_calls:
                st.markdown("**Tools used:**")
                for i, tool_call in enumerate(tool_calls, 1):
                    tool_name = tool_call.get('tool', 'unknown')
                    tool_args = tool_call.get('args', {})
                    st.markdown(f"{i}. `{tool_name}` → {tool_args}")

            st.caption(f"Completed in {iterations} iteration(s)")


def get_search_cost_summary() -> Dict[str, Any]:
    """
    Get summary of search costs from session

    Returns:
        Dict with cost statistics
    """
    # Track costs in session state
    if 'search_cost_log' not in st.session_state:
        st.session_state['search_cost_log'] = []

    log = st.session_state['search_cost_log']

    return {
        'total_searches': len(log),
        'total_cost': sum(entry['cost'] for entry in log),
        'cached_searches': sum(1 for entry in log if entry.get('cached', False)),
        'cache_hit_rate': sum(1 for entry in log if entry.get('cached', False)) / len(log) if log else 0,
        'avg_cost_per_search': sum(entry['cost'] for entry in log) / len(log) if log else 0
    }


def log_search_cost(query: str, cost: float, cached: bool = False):
    """
    Log search cost for tracking

    Args:
        query: Search query
        cost: Estimated cost in USD
        cached: Whether result was cached
    """
    if 'search_cost_log' not in st.session_state:
        st.session_state['search_cost_log'] = []

    st.session_state['search_cost_log'].append({
        'query': query,
        'cost': cost,
        'cached': cached,
        'timestamp': time.time()
    })

    # Keep only last 100 searches
    if len(st.session_state['search_cost_log']) > 100:
        st.session_state['search_cost_log'] = st.session_state['search_cost_log'][-100:]


def clear_search_cache():
    """
    Clear the search cache (useful for testing or after contact updates)
    """
    if 'search_cache' in st.session_state:
        st.session_state['search_cache'] = {}
    st.success("Search cache cleared")


def agentic_search_with_streaming(query: str, contacts_df: pd.DataFrame, openai_client, status_container) -> Dict[str, Any]:
    """
    Execute agentic search with real-time streaming updates

    Args:
        query: Search query
        contacts_df: Contacts DataFrame
        openai_client: OpenAI client instance
        status_container: Streamlit container for status updates

    Returns:
        Dict with results compatible with existing app.py format
    """
    if not query or query.strip() == '':
        return {
            'success': False,
            'results': [],
            'filtered_df': pd.DataFrame(),
            'message': 'Empty query',
            'reasoning': None,
            'cost_estimate': 0
        }

    try:
        # Get agent instance
        agent = get_search_agent(openai_client, contacts_df)

        # Check cache first
        cache_key = agent._get_cache_key(query)
        if cache_key in st.session_state.get('search_cache', {}):
            with status_container:
                st.info("⚡ Loading from cache...")
            cached = st.session_state['search_cache'][cache_key]
            cached['cached'] = True
            cached['latency_ms'] = 0
            return _format_result(cached, query)

        # Show thinking process
        with status_container:
            st.info("🤔 Understanding your query...")
            time.sleep(0.2)  # Small delay for UX

        with status_container:
            st.info("🔍 Searching network...")

        # Execute search
        search_result = agent.search(query, max_iterations=5)

        with status_container:
            st.info("✨ Ranking results...")
            time.sleep(0.1)  # Small delay for UX

        # Format result
        return _format_result(search_result, query)

    except Exception as e:
        with status_container:
            st.error(f"Search error: {e}")
        import traceback
        traceback.print_exc()

        return {
            'success': False,
            'results': [],
            'filtered_df': pd.DataFrame(),
            'message': f'Search failed: {str(e)}',
            'reasoning': None,
            'cost_estimate': 0
        }


def initialize_search_caching(openai_client, contacts_df: pd.DataFrame):
    """
    Initialize search system with pre-caching for popular queries
    Call this once when user loads contacts

    Args:
        openai_client: OpenAI client
        contacts_df: Contacts DataFrame
    """
    # Check if already pre-cached for this user
    if 'search_pre_cached' in st.session_state:
        return  # Already done

    # Run pre-caching in background
    with st.spinner("Optimizing search for speed..."):
        pre_cache_popular_queries(openai_client, contacts_df)

    st.session_state['search_pre_cached'] = True


# Export functions for app.py
__all__ = [
    'agentic_search',
    'agentic_search_with_streaming',
    'display_agent_reasoning',
    'get_search_cost_summary',
    'log_search_cost',
    'clear_search_cache',
    'initialize_search_caching',
    'pre_cache_popular_queries',
    'clear_tool_cache',
    'get_cache_stats'
]
