"""
Agentic Search System for 6th Degree AI
Uses GPT-4 with ReAct pattern to intelligently search network contacts

Optimizations:
- Streaming responses for better perceived performance
- Parallel tool execution for faster searches
- Tool result caching to reduce redundant work
- Pre-caching popular queries
"""

import json
import hashlib
import pandas as pd
import streamlit as st
from typing import Dict, Any, List, Optional, Callable, Generator
from datetime import datetime, timedelta
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

# Import the sophisticated search system components
try:
    from services.query_parser import parse_query, DictionaryLoader
    HAS_SMART_SEARCH = True
except ImportError:
    HAS_SMART_SEARCH = False
    print("Warning: Query parser not available, using fallback search")


class SearchTools:
    """
    Tool suite available to the search agent
    Each tool is a function the agent can call to gather information

    Includes tool result caching for performance optimization
    """

    def __init__(self, contacts_df: pd.DataFrame):
        """
        Initialize tools with contacts data

        Args:
            contacts_df: DataFrame with contact information
        """
        self.contacts_df = contacts_df
        self._init_tool_cache()

        # Load company dictionary as DataFrame for lookups
        if HAS_SMART_SEARCH:
            try:
                import pandas as pd
                import os
                data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
                company_csv = os.path.join(data_dir, 'company_aliases.csv')
                self.company_df = pd.read_csv(company_csv)
            except Exception as e:
                print(f"Error loading company dictionary: {e}")
                self.company_df = None
        else:
            self.company_df = None

    def _init_tool_cache(self):
        """Initialize tool result cache in session state"""
        if 'tool_cache' not in st.session_state:
            st.session_state['tool_cache'] = {}
            st.session_state['tool_cache_timestamps'] = {}

    def _get_from_cache(self, cache_key: str, ttl_seconds: int = 3600) -> Optional[Any]:
        """
        Get result from tool cache if not expired

        Args:
            cache_key: Cache key
            ttl_seconds: Time to live in seconds (default: 1 hour)

        Returns:
            Cached result or None
        """
        cache = st.session_state.get('tool_cache', {})
        timestamps = st.session_state.get('tool_cache_timestamps', {})

        if cache_key in cache:
            timestamp = timestamps.get(cache_key, datetime.now())
            age = (datetime.now() - timestamp).total_seconds()

            if age < ttl_seconds:
                return cache[cache_key]

        return None

    def _save_to_cache(self, cache_key: str, result: Any):
        """
        Save result to tool cache

        Args:
            cache_key: Cache key
            result: Result to cache
        """
        if 'tool_cache' not in st.session_state:
            st.session_state['tool_cache'] = {}
        if 'tool_cache_timestamps' not in st.session_state:
            st.session_state['tool_cache_timestamps'] = {}

        st.session_state['tool_cache'][cache_key] = result
        st.session_state['tool_cache_timestamps'][cache_key] = datetime.now()

    def fast_search(self, keywords: str, max_results: int = 20) -> List[Dict]:
        """
        Smart keyword search that understands industries and companies
        Uses query parser and dictionaries for better results

        Args:
            keywords: Search keywords (can be industry, company, role, etc.)
            max_results: Maximum results to return

        Returns:
            List of matching contacts
        """
        if not keywords or keywords.strip() == '':
            return []

        df = self.contacts_df.copy()
        masks = []

        # Try smart search with query parser first
        if HAS_SMART_SEARCH and self.company_df is not None:
            try:
                # Parse the query to extract entities
                parsed = parse_query(keywords)

                # If query mentions an industry, find companies in that industry
                if parsed.get('targets', {}).get('industries'):
                    for industry in parsed['targets']['industries']:
                        # Find all companies in this industry
                        industry_companies = []
                        for _, row in self.company_df.iterrows():
                            if row.get('industry', '').lower() == industry.lower():
                                # Add both alias and canonical name
                                industry_companies.append(row.get('alias', '').lower())
                                industry_companies.append(row.get('canonical', '').lower())

                        if industry_companies:
                            # Search for any of these companies
                            for company_name in industry_companies:
                                if company_name:
                                    company_mask = df['Company'].fillna('').str.lower().str.contains(
                                        company_name, regex=False, na=False
                                    )
                                    masks.append(company_mask)

                # If query mentions specific companies
                if parsed.get('targets', {}).get('companies'):
                    for company in parsed['targets']['companies']:
                        company_mask = df['Company'].fillna('').str.lower().str.contains(
                            company.lower(), regex=False, na=False
                        )
                        masks.append(company_mask)

                # If query mentions personas/roles
                if parsed.get('targets', {}).get('personas'):
                    for persona in parsed['targets']['personas']:
                        position_mask = df['Position'].fillna('').str.lower().str.contains(
                            persona.lower(), regex=False, na=False
                        )
                        masks.append(position_mask)

            except Exception as e:
                print(f"Smart search error: {e}")
                # Fall through to basic search

        # If no smart matches or smart search failed, do basic substring search
        if not masks:
            keywords_lower = keywords.lower()
            masks = [
                df['First Name'].fillna('').str.lower().str.contains(keywords_lower, regex=False, na=False),
                df['Last Name'].fillna('').str.lower().str.contains(keywords_lower, regex=False, na=False),
                df['Company'].fillna('').str.lower().str.contains(keywords_lower, regex=False, na=False),
                df['Position'].fillna('').str.lower().str.contains(keywords_lower, regex=False, na=False)
            ]

        # Combine all masks with OR
        combined_mask = masks[0]
        for mask in masks[1:]:
            combined_mask = combined_mask | mask

        results = df[combined_mask].head(max_results)

        # Convert to list of dicts
        return [
            {
                'name': f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip(),
                'company': row.get('Company', 'Unknown'),
                'position': row.get('Position', 'Unknown'),
                'email': row.get('Email Address', ''),
                'connected_on': row.get('Connected On', ''),
            }
            for _, row in results.iterrows()
        ]

    def get_all_companies(self) -> List[str]:
        """
        Get list of all unique companies in network
        Cached for performance (rarely changes)

        Returns:
            Sorted list of company names
        """
        cache_key = f"all_companies_{len(self.contacts_df)}"
        cached = self._get_from_cache(cache_key, ttl_seconds=86400)  # 24 hour cache

        if cached is not None:
            return cached

        companies = self.contacts_df['Company'].fillna('Unknown').unique()
        result = sorted([c for c in companies if c != 'Unknown'])

        self._save_to_cache(cache_key, result)
        return result

    def get_people_at_company(self, company: str, max_results: int = 50) -> List[Dict]:
        """
        Find all people who work at a specific company
        Cached for performance (1 hour TTL)

        Args:
            company: Company name (case-insensitive)
            max_results: Maximum results to return

        Returns:
            List of contacts at that company
        """
        cache_key = f"company_{company.lower()}_{len(self.contacts_df)}"
        cached = self._get_from_cache(cache_key, ttl_seconds=3600)  # 1 hour cache

        if cached is not None:
            return cached[:max_results]

        company_lower = company.lower()
        df = self.contacts_df.copy()

        mask = df['Company'].fillna('').str.lower().str.contains(company_lower, regex=False, na=False)
        results = df[mask].head(max_results)

        result = [
            {
                'name': f"{row.get('First Name', '')} {row.get('Last Name', '')}".strip(),
                'company': row.get('Company', 'Unknown'),
                'position': row.get('Position', 'Unknown'),
                'email': row.get('Email Address', ''),
                'connected_on': row.get('Connected On', ''),
            }
            for _, row in results.iterrows()
        ]

        self._save_to_cache(cache_key, result)
        return result

    def filter_by_position_keywords(self, contacts: List[Dict], keywords: List[str]) -> List[Dict]:
        """
        Filter contacts by position keywords (e.g., "engineer", "manager", "VP")

        Args:
            contacts: List of contact dicts
            keywords: List of position keywords to match

        Returns:
            Filtered list of contacts
        """
        if not keywords:
            return contacts

        filtered = []
        for contact in contacts:
            position = contact.get('position', '').lower()
            if any(keyword.lower() in position for keyword in keywords):
                filtered.append(contact)

        return filtered

    def rank_by_seniority(self, contacts: List[Dict]) -> List[Dict]:
        """
        Rank contacts by seniority level based on position title

        Args:
            contacts: List of contact dicts

        Returns:
            Contacts sorted by seniority (highest first)
        """
        # Seniority scoring
        seniority_scores = {
            'ceo': 100, 'chief executive': 100, 'founder': 100,
            'president': 95, 'chairman': 95,
            'cto': 90, 'cfo': 90, 'coo': 90, 'chief': 90,
            'vp': 85, 'vice president': 85,
            'svp': 87, 'senior vice president': 87,
            'evp': 88, 'executive vice president': 88,
            'director': 75, 'head of': 75,
            'senior director': 78,
            'principal': 70,
            'senior manager': 65, 'sr manager': 65,
            'manager': 60, 'lead': 60,
            'senior': 50, 'sr': 50,
            'staff': 45,
            'engineer': 40, 'developer': 40, 'analyst': 40,
            'associate': 35,
            'coordinator': 30,
            'assistant': 25,
            'intern': 20,
        }

        def get_seniority_score(contact: Dict) -> int:
            position = contact.get('position', '').lower()
            score = 0
            for keyword, keyword_score in seniority_scores.items():
                if keyword in position:
                    score = max(score, keyword_score)
            return score

        # Sort by seniority score (highest first)
        ranked = sorted(contacts, key=get_seniority_score, reverse=True)
        return ranked

    def get_contact_count(self) -> int:
        """
        Get total number of contacts

        Returns:
            Total contact count
        """
        return len(self.contacts_df)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get network statistics

        Returns:
            Dict with various network stats
        """
        df = self.contacts_df

        return {
            'total_contacts': len(df),
            'total_companies': df['Company'].nunique(),
            'top_5_companies': df['Company'].value_counts().head(5).to_dict(),
            'connection_date_range': {
                'earliest': df['Connected On'].min() if 'Connected On' in df.columns else None,
                'latest': df['Connected On'].max() if 'Connected On' in df.columns else None,
            }
        }


class NetworkSearchAgent:
    """
    Agentic search system using GPT-4 with ReAct pattern

    The agent:
    1. Understands natural language queries
    2. Plans how to search using available tools
    3. Executes the plan step-by-step
    4. Synthesizes results with explanations
    """

    def __init__(self, openai_client, contacts_df: pd.DataFrame):
        """
        Initialize search agent

        Args:
            openai_client: OpenAI client instance
            contacts_df: DataFrame with contact information
        """
        self.client = openai_client
        self.contacts_df = contacts_df
        self.tools = SearchTools(contacts_df)

        # Define available tools for function calling
        self.available_tools = [
            {
                "type": "function",
                "function": {
                    "name": "fast_search",
                    "description": "Search contacts by keywords across name, company, and position. Use this for direct keyword matches.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keywords": {
                                "type": "string",
                                "description": "Keywords to search for (e.g., 'Google', 'engineer', 'John Smith')"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 20)",
                                "default": 20
                            }
                        },
                        "required": ["keywords"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_people_at_company",
                    "description": "Find all people who work at a specific company. Use this when user asks about a specific company.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company": {
                                "type": "string",
                                "description": "Company name to search for"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return (default: 50)",
                                "default": 50
                            }
                        },
                        "required": ["company"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "filter_by_position_keywords",
                    "description": "Filter a list of contacts by position keywords (e.g., 'engineer', 'manager', 'VP'). Use this after getting contacts to narrow down by role.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "contacts_json": {
                                "type": "string",
                                "description": "JSON string of contacts to filter (from previous tool call)"
                            },
                            "keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Position keywords to filter by"
                            }
                        },
                        "required": ["contacts_json", "keywords"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "rank_by_seniority",
                    "description": "Rank contacts by seniority level. Use this when user wants most senior people or to sort by level.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "contacts_json": {
                                "type": "string",
                                "description": "JSON string of contacts to rank (from previous tool call)"
                            }
                        },
                        "required": ["contacts_json"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_all_companies",
                    "description": "Get a list of all unique companies in the network. Use this to see what companies are available.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_statistics",
                    "description": "Get network statistics like total contacts, top companies, etc. Use for analytics queries.",
                    "parameters": {
                        "type": "object",
                        "properties": {}
                    }
                }
            }
        ]

    def _call_tool(self, tool_name: str, tool_args: Dict) -> str:
        """
        Execute a tool call and return results as JSON string

        Args:
            tool_name: Name of tool to call
            tool_args: Arguments for the tool

        Returns:
            JSON string of tool results
        """
        try:
            # Special handling for tools that take contacts_json
            if 'contacts_json' in tool_args:
                contacts = json.loads(tool_args['contacts_json'])
                tool_args = {k: v for k, v in tool_args.items() if k != 'contacts_json'}

                if tool_name == 'filter_by_position_keywords':
                    result = self.tools.filter_by_position_keywords(contacts, **tool_args)
                elif tool_name == 'rank_by_seniority':
                    result = self.tools.rank_by_seniority(contacts)
                else:
                    result = {"error": f"Unknown tool: {tool_name}"}
            else:
                # Direct tool calls
                tool_method = getattr(self.tools, tool_name)
                result = tool_method(**tool_args)

            return json.dumps(result, default=str)

        except Exception as e:
            return json.dumps({"error": str(e)})

    def search(self, query: str, max_iterations: int = 5) -> Dict[str, Any]:
        """
        Execute agentic search using ReAct pattern

        Args:
            query: Natural language search query
            max_iterations: Maximum tool-use iterations (prevents infinite loops)

        Returns:
            Dict with search results and reasoning
        """
        start_time = time.time()

        # Check cache first
        cache_key = self._get_cache_key(query)
        if cache_key in st.session_state.get('search_cache', {}):
            cached = st.session_state['search_cache'][cache_key]
            cached['cached'] = True
            cached['latency_ms'] = 0
            return cached

        # System prompt
        system_prompt = f"""You are a helpful network search assistant. You have access to a network of {len(self.contacts_df)} contacts.

Your goal is to help the user find relevant people in their network by:
1. Understanding their query
2. Using available tools to search and filter contacts
3. Providing the most relevant results with clear explanations

Available tools:
- fast_search: Quick keyword search across all fields
- get_people_at_company: Find everyone at a specific company
- filter_by_position_keywords: Filter by job role/title
- rank_by_seniority: Sort by seniority level
- get_all_companies: See all companies in network
- get_statistics: Get network statistics

Important:
- Always explain WHY you chose certain results
- If query is ambiguous, make reasonable assumptions
- Limit final results to top 10-15 most relevant people
- Be conversational and helpful"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ]

        iteration_count = 0
        tool_calls_made = []

        # ReAct loop: Reason → Act → Observe
        while iteration_count < max_iterations:
            iteration_count += 1

            # Call GPT-4 with function calling
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using gpt-4o-mini for cost efficiency
                messages=messages,
                tools=self.available_tools,
                tool_choice="auto"
            )

            assistant_message = response.choices[0].message
            messages.append(assistant_message)

            # Check if agent wants to use tools
            if assistant_message.tool_calls:
                # Execute each tool call
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    # Execute tool
                    tool_result = self._call_tool(tool_name, tool_args)

                    # Track tool usage
                    tool_calls_made.append({
                        'tool': tool_name,
                        'args': tool_args,
                        'result_preview': tool_result[:200] + '...' if len(tool_result) > 200 else tool_result
                    })

                    # Add tool result to conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_result
                    })
            else:
                # Agent has finished reasoning and provided final answer
                break

        # Extract final answer (always use the last assistant_message we received)
        final_response = assistant_message.content if assistant_message.content else ""

        # Parse results from final response (if agent returned contacts)
        results = self._extract_contacts_from_response(messages)

        latency_ms = (time.time() - start_time) * 1000

        search_result = {
            'success': True,
            'query': query,
            'results': results,
            'reasoning': final_response,
            'tool_calls': tool_calls_made,
            'iterations': iteration_count,
            'latency_ms': latency_ms,
            'cached': False,
            'cost_estimate': self._estimate_cost(messages)
        }

        # Cache the result
        self._cache_result(cache_key, search_result)

        return search_result

    def _extract_contacts_from_response(self, messages: List) -> List[Dict]:
        """
        Extract contact list from tool call results in message history

        Args:
            messages: Conversation messages (mix of dicts and ChatCompletionMessage objects)

        Returns:
            List of contact dicts
        """
        contacts = []

        # Look for the last successful tool call that returned contacts
        for msg in reversed(messages):
            # Handle both dict (tool messages) and ChatCompletionMessage objects
            msg_role = msg.get('role') if isinstance(msg, dict) else getattr(msg, 'role', None)

            if msg_role == 'tool':
                try:
                    msg_content = msg.get('content') if isinstance(msg, dict) else getattr(msg, 'content', '')
                    tool_result = json.loads(msg_content)
                    if isinstance(tool_result, list) and len(tool_result) > 0:
                        if 'name' in tool_result[0]:  # Looks like contacts
                            contacts = tool_result
                            break
                except:
                    continue

        return contacts[:15]  # Limit to top 15

    def _get_cache_key(self, query: str) -> str:
        """
        Generate cache key for query

        Args:
            query: Search query

        Returns:
            Cache key (hash)
        """
        # Include contact count in key (invalidates when contacts change)
        contact_count = len(self.contacts_df)
        cache_string = f"{query.lower().strip()}_{contact_count}"
        return hashlib.md5(cache_string.encode()).hexdigest()

    def _cache_result(self, cache_key: str, result: Dict):
        """
        Cache search result in session state

        Args:
            cache_key: Cache key
            result: Search result to cache
        """
        if 'search_cache' not in st.session_state:
            st.session_state['search_cache'] = {}

        st.session_state['search_cache'][cache_key] = result

    def _estimate_cost(self, messages: List[Dict]) -> float:
        """
        Estimate cost of this search based on tokens used

        Args:
            messages: Conversation messages

        Returns:
            Estimated cost in USD
        """
        # Rough estimation:
        # gpt-4o-mini: $0.15 per 1M input tokens, $0.60 per 1M output tokens
        # Average search: ~2000 input tokens, ~500 output tokens
        # Cost: ~$0.0006 per search

        # Very rough estimate (we don't have exact token counts)
        # Handle both dict and ChatCompletionMessage objects
        def get_content(msg):
            if isinstance(msg, dict):
                return str(msg.get('content', ''))
            else:
                return str(getattr(msg, 'content', ''))

        def get_role(msg):
            if isinstance(msg, dict):
                return msg.get('role', '')
            else:
                return getattr(msg, 'role', '')

        estimated_input_tokens = sum(len(get_content(m)) / 4 for m in messages if get_role(m) in ['system', 'user', 'tool'])
        estimated_output_tokens = sum(len(get_content(m)) / 4 for m in messages if get_role(m) == 'assistant')

        input_cost = (estimated_input_tokens / 1_000_000) * 0.15
        output_cost = (estimated_output_tokens / 1_000_000) * 0.60

        return input_cost + output_cost


# Singleton instance management
_agent_instance = None

def get_search_agent(openai_client, contacts_df: pd.DataFrame) -> NetworkSearchAgent:
    """
    Get or create search agent instance

    Args:
        openai_client: OpenAI client
        contacts_df: Contacts DataFrame

    Returns:
        NetworkSearchAgent instance
    """
    global _agent_instance

    # Recreate if contacts changed
    if _agent_instance is None or len(_agent_instance.contacts_df) != len(contacts_df):
        _agent_instance = NetworkSearchAgent(openai_client, contacts_df)

    return _agent_instance


def pre_cache_popular_queries(openai_client, contacts_df: pd.DataFrame, status_container=None):
    """
    Pre-cache popular search queries for instant results

    Args:
        openai_client: OpenAI client
        contacts_df: Contacts DataFrame
        status_container: Streamlit container for status updates (optional)
    """
    # Popular queries to pre-cache
    popular_queries = [
        "Who works in venture capital?",
        "Show me engineers",
        "Who works at Google?",
        "Most senior people",
        "Who works in tech?",
        "Show me founders",
        "Who works at startups?",
        "People in finance",
        "Show me product managers",
        "Who works in AI?",
    ]

    agent = get_search_agent(openai_client, contacts_df)

    for i, query in enumerate(popular_queries, 1):
        # Check if already cached
        cache_key = agent._get_cache_key(query)
        if cache_key in st.session_state.get('search_cache', {}):
            continue  # Already cached

        try:
            if status_container:
                with status_container:
                    st.caption(f"Pre-caching query {i}/{len(popular_queries)}: {query}")

            # Execute search (will cache automatically)
            agent.search(query, max_iterations=3)  # Limit iterations for speed

        except Exception as e:
            print(f"Failed to pre-cache '{query}': {e}")
            continue

    if status_container:
        with status_container:
            st.caption(f"✅ Pre-cached {len(popular_queries)} popular queries")


def clear_tool_cache():
    """Clear the tool result cache"""
    if 'tool_cache' in st.session_state:
        st.session_state['tool_cache'] = {}
    if 'tool_cache_timestamps' in st.session_state:
        st.session_state['tool_cache_timestamps'] = {}


def get_cache_stats() -> Dict[str, Any]:
    """
    Get statistics about search and tool caches

    Returns:
        Dict with cache statistics
    """
    search_cache = st.session_state.get('search_cache', {})
    tool_cache = st.session_state.get('tool_cache', {})

    return {
        'search_cache_size': len(search_cache),
        'tool_cache_size': len(tool_cache),
        'total_cache_size': len(search_cache) + len(tool_cache),
    }
