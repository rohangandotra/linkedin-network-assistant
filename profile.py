"""
Profile Module for 6th Degree
Handles user profile creation, updates, and retrieval
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Import auth module for Supabase client
import auth


# ============================================
# PROFILE CRUD OPERATIONS
# ============================================

def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user profile by user ID

    Args:
        user_id: User's UUID

    Returns:
        Profile dict or None if not found
    """
    supabase = auth.get_supabase_client()

    try:
        response = supabase.table('user_profiles')\
            .select('*')\
            .eq('user_id', user_id)\
            .execute()

        if response.data and len(response.data) > 0:
            return response.data[0]
        return None

    except Exception as e:
        print(f"Error getting profile: {e}")
        return None


def profile_exists(user_id: str) -> bool:
    """
    Check if user has completed their profile

    Args:
        user_id: User's UUID

    Returns:
        True if profile exists and is completed
    """
    profile = get_profile(user_id)
    return profile is not None and profile.get('profile_completed', False)


def create_profile(
    user_id: str,
    current_role: str,
    industry: str,
    location_city: str,
    current_company: str = None,
    company_stage: str = None,
    location_country: str = None,
    goals: List[str] = None,
    interests: List[str] = None,
    seeking_connections: List[str] = None,
    privacy_settings: Dict[str, bool] = None
) -> Dict[str, Any]:
    """
    Create a new user profile

    Args:
        user_id: User's UUID
        current_role: User's current job title (required)
        industry: User's industry (required)
        location_city: User's city (required)
        current_company: User's current company (optional)
        company_stage: Company stage (optional)
        location_country: User's country (optional)
        goals: List of user goals (optional)
        interests: List of user interests (optional)
        seeking_connections: List of connection types seeking (optional)
        privacy_settings: Per-field visibility settings (optional)

    Returns:
        dict with 'success' boolean and 'message' or 'profile' data
    """
    supabase = auth.get_supabase_client()

    try:
        # Check if profile already exists
        existing = get_profile(user_id)
        if existing:
            return {
                'success': False,
                'message': 'Profile already exists. Use update_profile() instead.'
            }

        # Build profile data
        profile_data = {
            'user_id': user_id,
            'current_role': current_role,
            'industry': industry,
            'location_city': location_city,
            'profile_completed': True,
            'profile_completed_at': datetime.now().isoformat()
        }

        # Add optional fields
        if current_company:
            profile_data['current_company'] = current_company
        if company_stage:
            profile_data['company_stage'] = company_stage
        if location_country:
            profile_data['location_country'] = location_country

        # Add JSON array fields (default to empty arrays)
        profile_data['goals'] = json.dumps(goals if goals else [])
        profile_data['interests'] = json.dumps(interests if interests else [])
        profile_data['seeking_connections'] = json.dumps(seeking_connections if seeking_connections else [])

        # Add privacy settings (use provided or defaults)
        if privacy_settings:
            profile_data['privacy_settings'] = json.dumps(privacy_settings)
        # else: use database default

        # Insert profile
        response = supabase.table('user_profiles').insert(profile_data).execute()

        if response.data and len(response.data) > 0:
            return {
                'success': True,
                'message': 'Profile created successfully!',
                'profile': response.data[0]
            }
        else:
            return {
                'success': False,
                'message': 'Failed to create profile'
            }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error creating profile: {str(e)}'
        }


def update_profile(
    user_id: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update user profile

    Args:
        user_id: User's UUID
        updates: Dict of fields to update

    Returns:
        dict with 'success' boolean and 'message' or 'profile' data
    """
    supabase = auth.get_supabase_client()

    try:
        # Verify profile exists
        existing = get_profile(user_id)
        if not existing:
            return {
                'success': False,
                'message': 'Profile does not exist. Create one first.'
            }

        # Convert list fields to JSON strings if needed
        if 'goals' in updates and isinstance(updates['goals'], list):
            updates['goals'] = json.dumps(updates['goals'])
        if 'interests' in updates and isinstance(updates['interests'], list):
            updates['interests'] = json.dumps(updates['interests'])
        if 'seeking_connections' in updates and isinstance(updates['seeking_connections'], list):
            updates['seeking_connections'] = json.dumps(updates['seeking_connections'])
        if 'privacy_settings' in updates and isinstance(updates['privacy_settings'], dict):
            updates['privacy_settings'] = json.dumps(updates['privacy_settings'])

        # Update profile
        response = supabase.table('user_profiles')\
            .update(updates)\
            .eq('user_id', user_id)\
            .execute()

        if response.data and len(response.data) > 0:
            return {
                'success': True,
                'message': 'Profile updated successfully!',
                'profile': response.data[0]
            }
        else:
            return {
                'success': False,
                'message': 'Failed to update profile'
            }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error updating profile: {str(e)}'
        }


def delete_profile(user_id: str) -> Dict[str, Any]:
    """
    Delete user profile

    Args:
        user_id: User's UUID

    Returns:
        dict with 'success' boolean and 'message'
    """
    supabase = auth.get_supabase_client()

    try:
        response = supabase.table('user_profiles')\
            .delete()\
            .eq('user_id', user_id)\
            .execute()

        return {
            'success': True,
            'message': 'Profile deleted successfully'
        }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error deleting profile: {str(e)}'
        }


# ============================================
# PROFILE VISIBILITY & PRIVACY
# ============================================

def get_visible_profile_fields(user_id: str) -> Dict[str, Any]:
    """
    Get only the visible fields from a user's profile (respecting privacy settings)

    Args:
        user_id: User's UUID

    Returns:
        Dict with only visible fields
    """
    profile = get_profile(user_id)
    if not profile:
        return {}

    # Get privacy settings
    privacy_settings = profile.get('privacy_settings', {})
    if isinstance(privacy_settings, str):
        privacy_settings = json.loads(privacy_settings)

    # Build visible profile
    visible_profile = {
        'user_id': user_id
    }

    # Check each field's visibility
    fields_to_check = [
        'current_role', 'current_company', 'industry', 'company_stage',
        'location_city', 'location_country', 'goals', 'interests', 'seeking_connections'
    ]

    for field in fields_to_check:
        if privacy_settings.get(field, True):  # Default to visible if not specified
            visible_profile[field] = profile.get(field)

    return visible_profile


# ============================================
# PREDEFINED OPTIONS (for dropdowns)
# ============================================

INDUSTRY_OPTIONS = [
    'Technology', 'Finance', 'Healthcare', 'Education', 'E-commerce',
    'SaaS', 'Fintech', 'Biotech', 'Climate Tech', 'Web3/Crypto',
    'Venture Capital', 'Consulting', 'Real Estate', 'Media',
    'Manufacturing', 'Retail', 'Hospitality', 'Non-profit', 'Government',
    'Other'
]

COMPANY_STAGE_OPTIONS = [
    'Pre-seed', 'Seed', 'Series A', 'Series B', 'Series C+',
    'Public', 'Enterprise', 'Not applicable'
]

GOAL_OPTIONS = [
    'Raising funding',
    'Hiring talent',
    'Finding customers/clients',
    'Business partnerships',
    'Career opportunities',
    'Learning/mentorship',
    'Other'
]

INTEREST_OPTIONS = [
    'AI/ML', 'Web3/Crypto', 'SaaS', 'Climate Tech', 'Fintech',
    'Healthcare', 'Education', 'E-commerce', 'Developer Tools',
    'APIs', 'Infrastructure', 'Security', 'Data', 'Mobile',
    'Hardware', 'Robotics', 'Space Tech', 'Biotech', 'Other'
]

CONNECTION_TYPE_OPTIONS = [
    'Investors/VCs',
    'Engineers/Developers',
    'Designers',
    'Product Managers',
    'Executives/C-Level',
    'Founders/Entrepreneurs',
    'Sales/Business Development',
    'Recruiters/HR',
    'Mentors/Advisors',
    'Other'
]


# Export all functions
__all__ = [
    'get_profile',
    'profile_exists',
    'create_profile',
    'update_profile',
    'delete_profile',
    'get_visible_profile_fields',
    'INDUSTRY_OPTIONS',
    'COMPANY_STAGE_OPTIONS',
    'GOAL_OPTIONS',
    'INTEREST_OPTIONS',
    'CONNECTION_TYPE_OPTIONS'
]
