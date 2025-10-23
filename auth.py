"""
Authentication Module for LinkedIn Network Assistant
Handles user registration, login, and session management
"""

import os
import bcrypt
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
from typing import Optional, Dict, Any

# Load environment variables
load_dotenv()

# Initialize Supabase client
def get_supabase_client() -> Client:
    """Get Supabase client instance - checks both Streamlit secrets and environment variables"""
    url = None
    key = None

    # Debug: Print what we're checking
    debug_info = []

    # Try to import streamlit INSIDE the function to access current session's secrets
    try:
        import streamlit as st
        has_streamlit = True
        debug_info.append("Streamlit import successful")
    except ImportError:
        has_streamlit = False
        debug_info.append("Streamlit not available (ImportError)")

    # Try Streamlit secrets first (for Streamlit Cloud and local Streamlit runs)
    if has_streamlit:
        try:
            # Check if st.secrets exists and is accessible
            secrets_dict = dict(st.secrets) if hasattr(st, 'secrets') else {}
            debug_info.append(f"st.secrets keys: {list(secrets_dict.keys())}")

            if 'SUPABASE_URL' in secrets_dict:
                url = str(secrets_dict["SUPABASE_URL"]).strip()
                debug_info.append(f"Found SUPABASE_URL in st.secrets: {url[:30]}...")
            else:
                debug_info.append("SUPABASE_URL NOT in st.secrets")

            if 'SUPABASE_SERVICE_KEY' in secrets_dict:
                key = str(secrets_dict["SUPABASE_SERVICE_KEY"]).strip()
                debug_info.append(f"Found SUPABASE_SERVICE_KEY in st.secrets (length: {len(key)})")
            else:
                debug_info.append("SUPABASE_SERVICE_KEY NOT in st.secrets")
        except Exception as e:
            debug_info.append(f"Error accessing st.secrets: {type(e).__name__}: {str(e)}")
    else:
        debug_info.append("Streamlit is NOT available")

    # Fall back to environment variables
    if not url:
        url = os.getenv("SUPABASE_URL")
        if url:
            debug_info.append(f"Found SUPABASE_URL in os.getenv: {url[:30]}...")
        else:
            debug_info.append("SUPABASE_URL NOT in os.getenv")

    if not key:
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if key:
            debug_info.append(f"Found SUPABASE_SERVICE_KEY in os.getenv (length: {len(key)})")
        else:
            debug_info.append("SUPABASE_SERVICE_KEY NOT in os.getenv")

    # Only print debug info if we're missing credentials
    if not url or not key:
        print("\n🔍 SUPABASE CLIENT DEBUG INFO:")
        for info in debug_info:
            print(f"  - {info}")
        print(f"  - Final URL: {'✅ Found' if url else '❌ Missing'}")
        print(f"  - Final KEY: {'✅ Found' if key else '❌ Missing'}")
        print()
        error_msg = (
            "Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in environment.\n"
            "Please check:\n"
            "  1. .env file exists in project root\n"
            "  2. .streamlit/secrets.toml exists with correct values\n"
            "  3. Restart Streamlit completely (pkill -f streamlit)\n\n"
            f"Debug info: {'; '.join(debug_info)}"
        )
        raise ValueError(error_msg)

    return create_client(url, key)

# Password hashing functions
def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# User registration
def register_user(email: str, password: str, full_name: str) -> Dict[str, Any]:
    """
    Register a new user

    Args:
        email: User's email address
        password: Plain text password (will be hashed)
        full_name: User's full name

    Returns:
        dict with 'success' boolean and 'message' or 'user' data
    """
    supabase = get_supabase_client()

    try:
        # Check if user already exists
        existing = supabase.table('users').select("*").eq('email', email).execute()

        if existing.data and len(existing.data) > 0:
            return {
                'success': False,
                'message': 'Email already registered. Please log in instead.'
            }

        # Hash password
        password_hash = hash_password(password)

        # Insert new user
        response = supabase.table('users').insert({
            'email': email,
            'password_hash': password_hash,
            'full_name': full_name,
            'created_at': datetime.now().isoformat(),
            'is_verified': True,  # Auto-verify for MVP
            'plan_tier': 'free'
        }).execute()

        if response.data and len(response.data) > 0:
            user = response.data[0]
            return {
                'success': True,
                'message': 'Account created successfully!',
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'full_name': user['full_name']
                }
            }
        else:
            return {
                'success': False,
                'message': 'Failed to create account. Please try again.'
            }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }

# User login
def login_user(email: str, password: str) -> Dict[str, Any]:
    """
    Log in a user

    Args:
        email: User's email address
        password: Plain text password

    Returns:
        dict with 'success' boolean and 'message' or 'user' data
    """
    supabase = get_supabase_client()

    try:
        # Find user by email
        response = supabase.table('users').select("*").eq('email', email).execute()

        if not response.data or len(response.data) == 0:
            return {
                'success': False,
                'message': 'Invalid email or password.'
            }

        user = response.data[0]

        # Verify password
        if not verify_password(password, user['password_hash']):
            return {
                'success': False,
                'message': 'Invalid email or password.'
            }

        # Update last login
        supabase.table('users').update({
            'last_login': datetime.now().isoformat()
        }).eq('id', user['id']).execute()

        return {
            'success': True,
            'message': 'Login successful!',
            'user': {
                'id': user['id'],
                'email': user['email'],
                'full_name': user['full_name'],
                'plan_tier': user.get('plan_tier', 'free')
            }
        }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }

# Get user profile
def get_user_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user profile by ID

    Args:
        user_id: User's UUID

    Returns:
        User profile dict or None if not found
    """
    supabase = get_supabase_client()

    try:
        response = supabase.table('users').select("*").eq('id', user_id).execute()

        if response.data and len(response.data) > 0:
            user = response.data[0]
            return {
                'id': user['id'],
                'email': user['email'],
                'full_name': user['full_name'],
                'plan_tier': user.get('plan_tier', 'free'),
                'created_at': user['created_at'],
                'last_login': user.get('last_login')
            }

        return None

    except Exception as e:
        print(f"Error getting user profile: {e}")
        return None

# Update user profile
def update_user_profile(user_id: str, full_name: Optional[str] = None) -> bool:
    """
    Update user profile

    Args:
        user_id: User's UUID
        full_name: New full name (optional)

    Returns:
        True if update successful, False otherwise
    """
    supabase = get_supabase_client()

    try:
        updates = {}
        if full_name:
            updates['full_name'] = full_name

        if not updates:
            return True  # Nothing to update

        supabase.table('users').update(updates).eq('id', user_id).execute()
        return True

    except Exception as e:
        print(f"Error updating profile: {e}")
        return False

# Change password
def change_password(user_id: str, old_password: str, new_password: str) -> Dict[str, Any]:
    """
    Change user password

    Args:
        user_id: User's UUID
        old_password: Current password
        new_password: New password

    Returns:
        dict with 'success' boolean and 'message'
    """
    supabase = get_supabase_client()

    try:
        # Get current user
        response = supabase.table('users').select("*").eq('id', user_id).execute()

        if not response.data or len(response.data) == 0:
            return {
                'success': False,
                'message': 'User not found.'
            }

        user = response.data[0]

        # Verify old password
        if not verify_password(old_password, user['password_hash']):
            return {
                'success': False,
                'message': 'Current password is incorrect.'
            }

        # Hash new password
        new_hash = hash_password(new_password)

        # Update password
        supabase.table('users').update({
            'password_hash': new_hash
        }).eq('id', user_id).execute()

        return {
            'success': True,
            'message': 'Password changed successfully!'
        }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }

# Contact Management Functions

def save_contacts_to_db(user_id: str, contacts_df) -> Dict[str, Any]:
    """
    Save user's LinkedIn contacts to database

    Args:
        user_id: User's UUID
        contacts_df: Pandas DataFrame with contacts

    Returns:
        dict with 'success' boolean and 'message' or count
    """
    import pandas as pd
    supabase = get_supabase_client()

    try:
        # Only keep columns that exist in database schema
        db_columns = ['first_name', 'last_name', 'full_name', 'company', 'position', 'email', 'connected_on']

        # Filter DataFrame to only include columns we have in the DB
        df_filtered = contacts_df[[col for col in db_columns if col in contacts_df.columns]].copy()

        # Convert DataFrame to list of dicts
        contacts_list = df_filtered.to_dict('records')

        # Add user_id to each contact and ensure proper types
        for contact in contacts_list:
            contact['user_id'] = user_id
            # Ensure all required fields are strings or None
            contact['first_name'] = str(contact.get('first_name', '')) if pd.notna(contact.get('first_name')) else None
            contact['last_name'] = str(contact.get('last_name', '')) if pd.notna(contact.get('last_name')) else None
            contact['full_name'] = str(contact.get('full_name', '')) if pd.notna(contact.get('full_name')) else None
            contact['company'] = str(contact.get('company', '')) if pd.notna(contact.get('company')) else None
            contact['position'] = str(contact.get('position', '')) if pd.notna(contact.get('position')) else None
            contact['email'] = str(contact.get('email', '')) if pd.notna(contact.get('email')) else None
            # connected_on can be None or a date string
            if 'connected_on' in contact and pd.notna(contact.get('connected_on')):
                contact['connected_on'] = str(contact['connected_on'])
            else:
                contact['connected_on'] = None

        # Insert contacts in batch
        supabase.table('contacts').insert(contacts_list).execute()

        # Track upload
        supabase.table('csv_uploads').insert({
            'user_id': user_id,
            'contacts_count': len(contacts_list)
        }).execute()

        return {
            'success': True,
            'message': f'Successfully saved {len(contacts_list)} contacts',
            'count': len(contacts_list)
        }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error saving contacts: {str(e)}'
        }

def load_user_contacts(user_id: str) -> Optional[Any]:
    """
    Load user's contacts from database

    Args:
        user_id: User's UUID

    Returns:
        Pandas DataFrame with contacts or None if no contacts found
    """
    import pandas as pd
    supabase = get_supabase_client()

    try:
        response = supabase.table('contacts').select("*").eq('user_id', user_id).execute()

        if response.data and len(response.data) > 0:
            # Convert to DataFrame
            df = pd.DataFrame(response.data)
            # Remove internal columns for display
            columns_to_drop = ['user_id', 'id', 'last_updated']
            df = df.drop([col for col in columns_to_drop if col in df.columns], axis=1)

            return df

        return None

    except Exception as e:
        print(f"Error loading contacts: {e}")
        return None

def get_contact_count(user_id: str) -> int:
    """
    Get count of user's contacts

    Args:
        user_id: User's UUID

    Returns:
        Number of contacts
    """
    supabase = get_supabase_client()

    try:
        response = supabase.table('contacts').select("id", count='exact').eq('user_id', user_id).execute()
        return response.count if hasattr(response, 'count') else 0

    except Exception as e:
        print(f"Error getting contact count: {e}")
        return 0

def delete_user_contacts(user_id: str) -> bool:
    """
    Delete all contacts for a user (for replacing CSV)

    Args:
        user_id: User's UUID

    Returns:
        True if successful, False otherwise
    """
    supabase = get_supabase_client()

    try:
        supabase.table('contacts').delete().eq('user_id', user_id).execute()
        return True

    except Exception as e:
        print(f"Error deleting contacts: {e}")
        return False
