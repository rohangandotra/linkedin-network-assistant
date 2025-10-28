"""
Query Parser for 6th Degree Search
Deterministic parser with LLM fallback
"""

import csv
import os
import re
from typing import Dict, List, Optional, Any
import json

# ============================================
# DICTIONARY LOADING
# ============================================

class DictionaryLoader:
    """Load and manage dictionaries"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.abbreviations = {}
        self.roles = {}
        self.industries = {}
        self.geos = {}
        self.company_aliases = {}

        self._load_all()

    def _load_csv(self, filename: str) -> List[Dict]:
        """Load a CSV file"""
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found")
            return []

        rows = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        return rows

    def _load_all(self):
        """Load all dictionaries"""
        # Abbreviations
        for row in self._load_csv('abbreviations.csv'):
            abbrev = row['abbreviation'].lower()
            expansion = row['expansion'].lower()
            self.abbreviations[abbrev] = expansion

        # Roles
        for row in self._load_csv('roles.csv'):
            role = row['role'].lower()
            canonical = row['canonical'].lower()
            self.roles[role] = canonical

        # Industries
        for row in self._load_csv('industries.csv'):
            industry = row['industry'].lower()
            canonical = row['canonical'].lower()
            self.industries[industry] = canonical

        # Geos
        for row in self._load_csv('geos.csv'):
            location = row['location'].lower()
            canonical = row['canonical'].lower()
            metro = row.get('metro', '').lower()
            country = row.get('country', '').lower()
            self.geos[location] = {
                'canonical': canonical,
                'metro': metro,
                'country': country
            }

        # Company aliases
        for row in self._load_csv('company_aliases.csv'):
            alias = row['alias'].lower()
            canonical = row['canonical'].lower()
            parent = row.get('parent_company', '').lower()
            self.company_aliases[alias] = {
                'canonical': canonical,
                'parent': parent or canonical
            }

    def expand_abbreviations(self, text: str) -> str:
        """Expand abbreviations in text"""
        text_lower = text.lower()

        # Sort by length (longest first) to avoid partial replacements
        sorted_abbrevs = sorted(self.abbreviations.items(), key=lambda x: len(x[0]), reverse=True)

        for abbrev, expansion in sorted_abbrevs:
            # Match whole words only (with word boundaries)
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            text_lower = re.sub(pattern, expansion, text_lower)

        return text_lower


# Global dictionary loader (singleton)
_dict_loader = None

def get_dict_loader() -> DictionaryLoader:
    """Get or create dictionary loader"""
    global _dict_loader
    if _dict_loader is None:
        _dict_loader = DictionaryLoader()
    return _dict_loader


# ============================================
# DETERMINISTIC PARSER
# ============================================

def extract_companies_with_positions(text: str, dict_loader: DictionaryLoader, existing_positions: set = None) -> tuple:
    """Extract company mentions from text, tracking positions"""
    if existing_positions is None:
        existing_positions = set()

    text_lower = text.lower()
    companies = []
    matched_positions = set()

    # Sort by length (longest first) to avoid partial matches
    sorted_companies = sorted(dict_loader.company_aliases.items(), key=lambda x: len(x[0]), reverse=True)

    for alias, info in sorted_companies:
        # Use word boundaries to avoid partial matches
        pattern = r'\b' + re.escape(alias) + r'\b'
        match = re.search(pattern, text_lower)
        if match:
            canonical = info['canonical']
            if canonical not in companies:
                start, end = match.span()
                overlap = any(pos in range(start, end) for pos in existing_positions) or \
                          any(pos in range(start, end) for pos in matched_positions)

                if not overlap:
                    companies.append(canonical)
                    for pos in range(start, end):
                        matched_positions.add(pos)

    return companies, matched_positions


def extract_company_mentions(text: str, dict_loader: DictionaryLoader) -> List[str]:
    """Extract company mentions from text (backwards compatible)"""
    companies, _ = extract_companies_with_positions(text, dict_loader)
    return companies


def extract_roles_with_positions(text: str, dict_loader: DictionaryLoader, existing_positions: set = None) -> tuple:
    """Extract roles/personas from text, tracking positions"""
    if existing_positions is None:
        existing_positions = set()

    text_lower = text.lower()
    roles = []
    matched_positions = set()

    # Sort by canonical length first (longest canonical forms first to catch "software engineer" before "engineer")
    sorted_roles = sorted(dict_loader.roles.items(), key=lambda x: len(x[1]), reverse=True)

    for role, canonical in sorted_roles:
        # Match against both the role key AND canonical value (for abbreviation handling)
        pattern_key = r'\b' + re.escape(role) + r'\b'
        pattern_canonical = r'\b' + re.escape(canonical) + r'\b'

        match = re.search(pattern_key, text_lower) or re.search(pattern_canonical, text_lower)
        if match and canonical not in roles:
            # Check if this position overlaps with already matched text
            start, end = match.span()
            overlap = any(pos in range(start, end) for pos in existing_positions) or \
                      any(pos in range(start, end) for pos in matched_positions)

            if not overlap:
                roles.append(canonical)
                # Mark these positions as matched
                for pos in range(start, end):
                    matched_positions.add(pos)

    return roles, matched_positions


def extract_roles(text: str, dict_loader: DictionaryLoader) -> List[str]:
    """Extract roles/personas from text (backwards compatible)"""
    roles, _ = extract_roles_with_positions(text, dict_loader)
    return roles


def extract_industries_with_positions(text: str, dict_loader: DictionaryLoader, existing_positions: set = None) -> tuple:
    """Extract industries from text, tracking positions"""
    if existing_positions is None:
        existing_positions = set()

    text_lower = text.lower()
    industries = []
    matched_positions = set()

    # Sort by canonical length first (longest first)
    sorted_industries = sorted(dict_loader.industries.items(), key=lambda x: len(x[1]), reverse=True)

    for industry, canonical in sorted_industries:
        # Match against both the industry key AND canonical value
        pattern_key = r'\b' + re.escape(industry) + r'\b'
        pattern_canonical = r'\b' + re.escape(canonical) + r'\b'

        match = re.search(pattern_key, text_lower) or re.search(pattern_canonical, text_lower)
        if match and canonical not in industries:
            # Check if this position overlaps with already matched text
            start, end = match.span()
            overlap = any(pos in range(start, end) for pos in existing_positions) or \
                      any(pos in range(start, end) for pos in matched_positions)

            if not overlap:
                industries.append(canonical)
                # Mark these positions as matched
                for pos in range(start, end):
                    matched_positions.add(pos)

    return industries, matched_positions


def extract_industries(text: str, dict_loader: DictionaryLoader) -> List[str]:
    """Extract industries from text (backwards compatible)"""
    industries, _ = extract_industries_with_positions(text, dict_loader)
    return industries


def extract_geos_with_positions(text: str, dict_loader: DictionaryLoader, existing_positions: set = None) -> tuple:
    """Extract geographic locations from text, tracking positions"""
    if existing_positions is None:
        existing_positions = set()

    text_lower = text.lower()
    geos = []
    seen_canonicals = set()
    matched_positions = set()

    # Sort by canonical length first (longest first)
    sorted_geos = sorted(dict_loader.geos.items(), key=lambda x: len(x[1]['canonical']), reverse=True)

    for location, info in sorted_geos:
        canonical = info['canonical']

        # Match against both the location key AND canonical value
        pattern_key = r'\b' + re.escape(location) + r'\b'
        pattern_canonical = r'\b' + re.escape(canonical) + r'\b'

        match = re.search(pattern_key, text_lower) or re.search(pattern_canonical, text_lower)
        if match and canonical not in seen_canonicals:
            # Check if this position overlaps with already matched text
            start, end = match.span()
            overlap = any(pos in range(start, end) for pos in existing_positions) or \
                      any(pos in range(start, end) for pos in matched_positions)

            if not overlap:
                geos.append({
                    'location': canonical,
                    'metro': info.get('metro', ''),
                    'country': info.get('country', '')
                })
                seen_canonicals.add(canonical)
                # Mark these positions as matched
                for pos in range(start, end):
                    matched_positions.add(pos)

    return geos, matched_positions


def extract_geos(text: str, dict_loader: DictionaryLoader) -> List[Dict[str, str]]:
    """Extract geographic locations from text (backwards compatible)"""
    geos, _ = extract_geos_with_positions(text, dict_loader)
    return geos


def parse_query_deterministic(query: str) -> Dict[str, Any]:
    """
    Deterministic query parser

    Parses query into structured JSON:
    {
        'targets': {
            'personas': [...],
            'companies': [...],
            'industries': [...],
            'geos': [...]
        },
        'introducer_constraints': {
            'max_hops': 2,
            'min_strength': 0.2
        },
        'must_have': [],
        'nice_to_have': []
    }
    """
    dict_loader = get_dict_loader()

    # Expand abbreviations
    expanded_query = dict_loader.expand_abbreviations(query)

    # Extract entities with shared position tracking to avoid overlaps across categories
    global_matched_positions = set()

    # Extract in priority order: personas, companies, industries, geos
    # This prevents industries from matching text already identified as roles
    personas, role_positions = extract_roles_with_positions(expanded_query, dict_loader, global_matched_positions)
    global_matched_positions.update(role_positions)

    companies, company_positions = extract_companies_with_positions(expanded_query, dict_loader, global_matched_positions)
    global_matched_positions.update(company_positions)

    industries, industry_positions = extract_industries_with_positions(expanded_query, dict_loader, global_matched_positions)
    global_matched_positions.update(industry_positions)

    geos, geo_positions = extract_geos_with_positions(expanded_query, dict_loader, global_matched_positions)
    global_matched_positions.update(geo_positions)

    return {
        'targets': {
            'personas': personas,
            'companies': companies,
            'industries': industries,
            'geos': [g['location'] for g in geos]
        },
        'introducer_constraints': {
            'max_hops': 2,
            'min_strength': 0.2
        },
        'must_have': [],
        'nice_to_have': [],
        'original_query': query,
        'expanded_query': expanded_query
    }


# ============================================
# LLM FALLBACK PARSER
# ============================================

def llm_parse_json(query: str, openai_client=None) -> Dict[str, Any]:
    """
    LLM-based parser fallback using strict JSON schema

    Args:
        query: Natural language query
        openai_client: OpenAI client instance

    Returns:
        Parsed query dict
    """
    if not openai_client:
        # Return empty structure if no client
        return {
            'targets': {
                'personas': [],
                'companies': [],
                'industries': [],
                'geos': []
            },
            'introducer_constraints': {
                'max_hops': 2,
                'min_strength': 0.2
            },
            'must_have': [],
            'nice_to_have': []
        }

    # JSON schema for structured output
    schema = {
        "type": "object",
        "properties": {
            "personas": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Job titles, roles, or personas (e.g., 'CEO', 'product manager', 'software engineer')"
            },
            "companies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Company names (e.g., 'Google', 'Microsoft', 'Y Combinator')"
            },
            "industries": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Industries or sectors (e.g., 'fintech', 'healthcare', 'AI')"
            },
            "geos": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Geographic locations (e.g., 'San Francisco', 'New York', 'remote')"
            },
            "must_have": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Required qualifications or attributes"
            },
            "nice_to_have": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Preferred but not required qualifications"
            }
        },
        "required": ["personas", "companies", "industries", "geos"]
    }

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a query parser. Extract structured information from search queries. Return JSON only."
                },
                {
                    "role": "user",
                    "content": f"Parse this search query into JSON:\n\n{query}\n\nExtract: personas (roles/titles), companies, industries, and locations (geos)."
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=500
        )

        # Parse response
        result = json.loads(response.choices[0].message.content)

        # Normalize to expected structure
        return {
            'targets': {
                'personas': result.get('personas', []),
                'companies': result.get('companies', []),
                'industries': result.get('industries', []),
                'geos': result.get('geos', [])
            },
            'introducer_constraints': {
                'max_hops': 2,
                'min_strength': 0.2
            },
            'must_have': result.get('must_have', []),
            'nice_to_have': result.get('nice_to_have', []),
            'original_query': query,
            'parsed_via': 'llm'
        }

    except Exception as e:
        print(f"LLM parse error: {e}")
        # Return empty structure on error
        return {
            'targets': {
                'personas': [],
                'companies': [],
                'industries': [],
                'geos': []
            },
            'introducer_constraints': {
                'max_hops': 2,
                'min_strength': 0.2
            },
            'must_have': [],
            'nice_to_have': [],
            'error': str(e)
        }


# ============================================
# MAIN PARSER (Deterministic + LLM Fallback)
# ============================================

def parse_query(query: str, openai_client=None) -> Dict[str, Any]:
    """
    Main query parser: Deterministic first, LLM fallback

    Args:
        query: Natural language search query
        openai_client: Optional OpenAI client for LLM fallback

    Returns:
        Parsed query dict with extracted entities
    """
    # Try deterministic parser first
    result = parse_query_deterministic(query)

    # Check if we extracted anything meaningful
    targets = result['targets']
    has_entities = any([
        targets['personas'],
        targets['companies'],
        targets['industries'],
        targets['geos']
    ])

    # If nothing extracted and LLM available, try LLM fallback
    if not has_entities and openai_client:
        print(f"Deterministic parser found nothing, trying LLM fallback...")
        result = llm_parse_json(query, openai_client)
        result['fallback_used'] = True
    else:
        result['fallback_used'] = False
        result['parsed_via'] = 'deterministic'

    return result


# Export
__all__ = [
    'parse_query',
    'parse_query_deterministic',
    'llm_parse_json',
    'get_dict_loader'
]
