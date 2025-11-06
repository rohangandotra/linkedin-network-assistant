"""
AI Search Agent for 6th Degree AI
GPT-4 powered intelligent search that understands natural language

Example:
- "Who can introduce me to a PM at Google?" → Plans multi-step search
- "Find senior engineers who worked at startups" → Understands seniority + history
- "Show me founders in fintech" → Combines role + industry
"""

import pandas as pd
import json
from typing import Dict, List, Optional, Any
from openai import OpenAI


class AISearchAgent:
    """
    Intelligent search agent powered by GPT-4

    Uses function calling to execute searches and explain results
    """

    def __init__(self, openai_client: OpenAI):
        """
        Initialize AI search agent

        Args:
            openai_client: OpenAI client instance
        """
        self.client = openai_client
        self.contacts_df = None

    def set_contacts(self, contacts_df: pd.DataFrame):
        """Set contacts DataFrame for searching"""
        self.contacts_df = contacts_df

    # ============================================
    # SEARCH TOOLS (Called by GPT-4)
    # ============================================

    def search_by_company(self, company_name: str, limit: int = 20) -> List[Dict]:
        """
        Search contacts by company name

        Args:
            company_name: Company name to search for
            limit: Maximum results

        Returns:
            List of matching contacts
        """
        if self.contacts_df is None or self.contacts_df.empty:
            return []

        company_lower = company_name.lower()
        mask = self.contacts_df['company'].fillna('').str.lower().str.contains(
            company_lower, regex=False, na=False
        )

        results = self.contacts_df[mask].head(limit)
        return self._df_to_contacts(results)

    def search_by_role(self, role_keywords: str, limit: int = 20) -> List[Dict]:
        """
        Search contacts by role/position keywords

        Args:
            role_keywords: Keywords to search in position field
            limit: Maximum results

        Returns:
            List of matching contacts
        """
        if self.contacts_df is None or self.contacts_df.empty:
            return []

        keywords_lower = role_keywords.lower()
        mask = self.contacts_df['position'].fillna('').str.lower().str.contains(
            keywords_lower, regex=False, na=False
        )

        results = self.contacts_df[mask].head(limit)
        return self._df_to_contacts(results)

    def search_by_name(self, name: str, limit: int = 10) -> List[Dict]:
        """
        Search contacts by name

        Args:
            name: Name to search for
            limit: Maximum results

        Returns:
            List of matching contacts
        """
        if self.contacts_df is None or self.contacts_df.empty:
            return []

        name_lower = name.lower()
        mask = self.contacts_df['full_name'].fillna('').str.lower().str.contains(
            name_lower, regex=False, na=False
        )

        results = self.contacts_df[mask].head(limit)
        return self._df_to_contacts(results)

    def search_combined(self, company: Optional[str] = None, role: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """
        Search with multiple criteria

        Args:
            company: Company name (optional)
            role: Role keywords (optional)
            limit: Maximum results

        Returns:
            List of matching contacts
        """
        if self.contacts_df is None or self.contacts_df.empty:
            return []

        mask = pd.Series([True] * len(self.contacts_df), index=self.contacts_df.index)

        if company:
            company_lower = company.lower()
            company_mask = self.contacts_df['company'].fillna('').str.lower().str.contains(
                company_lower, regex=False, na=False
            )
            mask = mask & company_mask

        if role:
            role_lower = role.lower()
            role_mask = self.contacts_df['position'].fillna('').str.lower().str.contains(
                role_lower, regex=False, na=False
            )
            mask = mask & role_mask

        results = self.contacts_df[mask].head(limit)
        return self._df_to_contacts(results)

    def get_contact_count(self) -> int:
        """Get total number of contacts"""
        if self.contacts_df is None:
            return 0
        return len(self.contacts_df)

    def _df_to_contacts(self, df: pd.DataFrame) -> List[Dict]:
        """Convert DataFrame to list of contact dicts"""
        contacts = []
        for _, row in df.iterrows():
            contacts.append({
                'name': row.get('full_name', ''),
                'company': row.get('company', ''),
                'position': row.get('position', ''),
                'email': row.get('email', ''),
            })
        return contacts

    # ============================================
    # GPT-4 FUNCTION DEFINITIONS
    # ============================================

    def get_tools(self) -> List[Dict]:
        """Get tool definitions for GPT-4 function calling"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_by_company",
                    "description": "Search contacts who work at a specific company. Use this when user asks about people at a company.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company_name": {
                                "type": "string",
                                "description": "The company name to search for (e.g., 'Google', 'Meta', 'Stripe')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 20
                            }
                        },
                        "required": ["company_name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_by_role",
                    "description": "Search contacts by their role or position. Use this when user asks about people with specific job titles or roles.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "role_keywords": {
                                "type": "string",
                                "description": "Keywords to search in position/role field (e.g., 'engineer', 'product manager', 'CEO')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 20
                            }
                        },
                        "required": ["role_keywords"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_combined",
                    "description": "Search with multiple criteria (company AND role). Use this when user asks about specific roles at specific companies.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "company": {
                                "type": "string",
                                "description": "Company name to filter by"
                            },
                            "role": {
                                "type": "string",
                                "description": "Role keywords to filter by"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 20
                            }
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_by_name",
                    "description": "Search for a specific person by name. Use this when user asks about a specific individual.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string",
                                "description": "The person's name to search for"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 10
                            }
                        },
                        "required": ["name"]
                    }
                }
            }
        ]

    # ============================================
    # MAIN SEARCH METHOD
    # ============================================

    def search(self, query: str, max_iterations: int = 3) -> Dict[str, Any]:
        """
        Execute intelligent search using GPT-4

        Args:
            query: Natural language search query
            max_iterations: Maximum tool calling iterations

        Returns:
            {
                'success': bool,
                'results': List[Dict],  # Found contacts
                'reasoning': str,  # AI's explanation
                'tool_calls': List[Dict],  # Tools used
                'cost_estimate': float  # Estimated cost in USD
            }
        """
        if self.contacts_df is None or self.contacts_df.empty:
            return {
                'success': False,
                'results': [],
                'reasoning': 'No contacts available to search',
                'tool_calls': [],
                'cost_estimate': 0
            }

        try:
            # Build system prompt
            system_prompt = f"""You are an intelligent search assistant for a professional network of {len(self.contacts_df)} contacts.

Your job is to understand the user's search query and use the available tools to find relevant contacts.

Available information for each contact:
- Name
- Company (current company)
- Position (current role)
- Email

IMPORTANT INSTRUCTIONS:
1. Use tools to search - don't make up results
2. If searching for roles, use broad terms (e.g., "manager" not "product manager" if user just says "manager")
3. If no results found, try alternative search terms
4. After getting results, provide a brief summary

Be helpful and concise."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]

            tool_calls_made = []
            all_results = []

            # Iterative tool calling
            for iteration in range(max_iterations):
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    tools=self.get_tools(),
                    temperature=0.1
                )

                message = response.choices[0].message

                # If no tool calls, we're done
                if not message.tool_calls:
                    reasoning = message.content or "Search completed."
                    break

                # Execute tool calls
                messages.append(message)

                for tool_call in message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)

                    # Execute the tool
                    if function_name == "search_by_company":
                        results = self.search_by_company(**function_args)
                    elif function_name == "search_by_role":
                        results = self.search_by_role(**function_args)
                    elif function_name == "search_combined":
                        results = self.search_combined(**function_args)
                    elif function_name == "search_by_name":
                        results = self.search_by_name(**function_args)
                    else:
                        results = []

                    # Record tool call
                    tool_calls_made.append({
                        'tool': function_name,
                        'args': function_args,
                        'results_count': len(results)
                    })

                    # Add results to messages
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps({
                            'count': len(results),
                            'results': results[:5]  # Only send first 5 to save tokens
                        })
                    })

                    # Collect all results
                    all_results.extend(results)

            # Get final response with reasoning
            if not message.tool_calls:
                reasoning = message.content
            else:
                # Get one more response for explanation
                final_response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages + [{"role": "user", "content": "Summarize what you found in one sentence."}],
                    temperature=0.1
                )
                reasoning = final_response.choices[0].message.content

            # Deduplicate results by email
            seen_emails = set()
            unique_results = []
            for result in all_results:
                email = result.get('email', '')
                if email and email not in seen_emails:
                    seen_emails.add(email)
                    unique_results.append(result)
                elif not email:  # Include contacts without email
                    unique_results.append(result)

            # Estimate cost (rough estimate)
            cost_estimate = 0.0006  # ~$0.0006 per search with gpt-4o-mini

            return {
                'success': True,
                'results': unique_results[:20],  # Limit to 20
                'reasoning': reasoning,
                'tool_calls': tool_calls_made,
                'cost_estimate': cost_estimate,
                'iterations': len(tool_calls_made)
            }

        except Exception as e:
            return {
                'success': False,
                'results': [],
                'reasoning': f'Search failed: {str(e)}',
                'tool_calls': [],
                'cost_estimate': 0
            }


# Convenience function
def create_ai_search_agent(openai_client: OpenAI, contacts_df: pd.DataFrame) -> AISearchAgent:
    """
    Create and initialize AI search agent

    Args:
        openai_client: OpenAI client
        contacts_df: Contacts DataFrame

    Returns:
        Initialized AISearchAgent
    """
    agent = AISearchAgent(openai_client)
    agent.set_contacts(contacts_df)
    return agent
