"""
Agentic Search System for 6th Degree AI
Uses GPT-4 with ReAct pattern to intelligently search network contacts
"""

import json
import hashlib
import pandas as pd
import streamlit as st
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import time


class SearchTools:
    """
    Tool suite available to the search agent
    Each tool is a function the agent can call to gather information
    """

    def __init__(self, contacts_df: pd.DataFrame):
        """
        Initialize tools with contacts data

        Args:
            contacts_df: DataFrame with contact information
        """
        self.contacts_df = contacts_df

    def fast_search(self, keywords: str, max_results: int = 20) -> List[Dict]:
        """
        Fast keyword search across name, company, position
        Uses case-insensitive substring matching

        Args:
            keywords: Search keywords
            max_results: Maximum results to return

        Returns:
            List of matching contacts
        """
        if not keywords or keywords.strip() == '':
            return []

        keywords_lower = keywords.lower()
        df = self.contacts_df.copy()

        # Search across multiple fields
        mask = (
            df['First Name'].fillna('').str.lower().str.contains(keywords_lower, regex=False, na=False) |
            df['Last Name'].fillna('').str.lower().str.contains(keywords_lower, regex=False, na=False) |
            df['Company'].fillna('').str.lower().str.contains(keywords_lower, regex=False, na=False) |
            df['Position'].fillna('').str.lower().str.contains(keywords_lower, regex=False, na=False)
        )

        results = df[mask].head(max_results)

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

        Returns:
            Sorted list of company names
        """
        companies = self.contacts_df['Company'].fillna('Unknown').unique()
        return sorted([c for c in companies if c != 'Unknown'])

    def get_people_at_company(self, company: str, max_results: int = 50) -> List[Dict]:
        """
        Find all people who work at a specific company

        Args:
            company: Company name (case-insensitive)
            max_results: Maximum results to return

        Returns:
            List of contacts at that company
        """
        company_lower = company.lower()
        df = self.contacts_df.copy()

        mask = df['Company'].fillna('').str.lower().str.contains(company_lower, regex=False, na=False)
        results = df[mask].head(max_results)

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

        # Extract final answer
        final_response = messages[-1].content if messages[-1].get('role') == 'assistant' else assistant_message.content

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

    def _extract_contacts_from_response(self, messages: List[Dict]) -> List[Dict]:
        """
        Extract contact list from tool call results in message history

        Args:
            messages: Conversation messages

        Returns:
            List of contact dicts
        """
        contacts = []

        # Look for the last successful tool call that returned contacts
        for msg in reversed(messages):
            if msg.get('role') == 'tool':
                try:
                    tool_result = json.loads(msg['content'])
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
        estimated_input_tokens = sum(len(str(m.get('content', ''))) / 4 for m in messages if m.get('role') in ['system', 'user', 'tool'])
        estimated_output_tokens = sum(len(str(m.get('content', ''))) / 4 for m in messages if m.get('role') == 'assistant')

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
