"""
Collaboration Module for LinkedIn Network Assistant
Handles user connections, network sharing, and introduction requests
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv
from supabase import create_client, Client
import pandas as pd

# Load environment variables
load_dotenv()

# Import auth module for Supabase client
import auth

# ============================================
# USER CONNECTION MANAGEMENT
# ============================================

def search_users(search_query: str, current_user_id: str) -> List[Dict[str, Any]]:
    """
    Search for users by name and/or organization

    Args:
        search_query: Name or organization to search for
        current_user_id: ID of current user (to exclude from results)

    Returns:
        List of matching users
    """
    supabase = auth.get_supabase_client()

    try:
        # Search by name or organization
        response = supabase.table('users')\
            .select('id, email, full_name, organization, created_at')\
            .neq('id', current_user_id)\
            .or_(f'full_name.ilike.%{search_query}%,organization.ilike.%{search_query}%')\
            .execute()

        return response.data if response.data else []

    except Exception as e:
        print(f"Error searching users: {e}")
        return []


def send_connection_request(user_id: str, target_user_id: str) -> Dict[str, Any]:
    """
    Send a connection request to another user

    Args:
        user_id: ID of user sending request
        target_user_id: ID of user to connect with

    Returns:
        dict with 'success' boolean and 'message' or 'connection_id'
    """
    supabase = auth.get_supabase_client()

    try:
        # Check if connection already exists
        existing = supabase.table('user_connections')\
            .select('*')\
            .or_(f'and(user_id.eq.{user_id},connected_user_id.eq.{target_user_id}),and(user_id.eq.{target_user_id},connected_user_id.eq.{user_id})')\
            .execute()

        if existing.data and len(existing.data) > 0:
            return {
                'success': False,
                'message': 'Connection already exists or request pending'
            }

        # Create connection request
        response = supabase.table('user_connections').insert({
            'user_id': user_id,
            'connected_user_id': target_user_id,
            'status': 'pending',
            'network_sharing_enabled': True
        }).execute()

        if response.data and len(response.data) > 0:
            return {
                'success': True,
                'message': 'Connection request sent!',
                'connection_id': response.data[0]['id']
            }
        else:
            return {
                'success': False,
                'message': 'Failed to send connection request'
            }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


def accept_connection_request(connection_id: str, share_network: bool = True) -> Dict[str, Any]:
    """
    Accept a connection request

    Args:
        connection_id: ID of connection to accept
        share_network: Whether to share network with this connection

    Returns:
        dict with 'success' boolean and 'message'
    """
    supabase = auth.get_supabase_client()

    try:
        response = supabase.table('user_connections').update({
            'status': 'accepted',
            'accepted_at': datetime.now().isoformat(),
            'network_sharing_enabled': share_network
        }).eq('id', connection_id).execute()

        if response.data and len(response.data) > 0:
            return {
                'success': True,
                'message': 'Connection accepted!'
            }
        else:
            return {
                'success': False,
                'message': 'Failed to accept connection'
            }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


def decline_connection_request(connection_id: str) -> Dict[str, Any]:
    """
    Decline a connection request

    Args:
        connection_id: ID of connection to decline

    Returns:
        dict with 'success' boolean and 'message'
    """
    supabase = auth.get_supabase_client()

    try:
        response = supabase.table('user_connections').update({
            'status': 'declined',
            'declined_at': datetime.now().isoformat()
        }).eq('id', connection_id).execute()

        if response.data and len(response.data) > 0:
            return {
                'success': True,
                'message': 'Connection declined'
            }
        else:
            return {
                'success': False,
                'message': 'Failed to decline connection'
            }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


def get_user_connections(user_id: str, status: str = 'accepted') -> List[Dict[str, Any]]:
    """
    Get all connections for a user

    Args:
        user_id: User's UUID
        status: Filter by status (default: 'accepted')

    Returns:
        List of connections with user details
    """
    supabase = auth.get_supabase_client()

    try:
        # Get connections where user is either the requester or the target
        response = supabase.table('user_connections')\
            .select('*, users!user_connections_connected_user_id_fkey(id, email, full_name, organization)')\
            .eq('user_id', user_id)\
            .eq('status', status)\
            .execute()

        connections_as_requester = response.data if response.data else []

        # Also get connections where user is the target
        response2 = supabase.table('user_connections')\
            .select('*, users!user_connections_user_id_fkey(id, email, full_name, organization)')\
            .eq('connected_user_id', user_id)\
            .eq('status', status)\
            .execute()

        connections_as_target = response2.data if response2.data else []

        # Combine and format
        all_connections = []

        for conn in connections_as_requester:
            all_connections.append({
                'connection_id': conn['id'],
                'user_id': conn['connected_user_id'],
                'email': conn['users']['email'],
                'full_name': conn['users']['full_name'],
                'organization': conn['users'].get('organization'),
                'network_sharing_enabled': conn['network_sharing_enabled'],
                'connected_at': conn.get('accepted_at', conn.get('created_at'))
            })

        for conn in connections_as_target:
            all_connections.append({
                'connection_id': conn['id'],
                'user_id': conn['user_id'],
                'email': conn['users']['email'],
                'full_name': conn['users']['full_name'],
                'organization': conn['users'].get('organization'),
                'network_sharing_enabled': conn['network_sharing_enabled'],
                'connected_at': conn.get('accepted_at', conn.get('created_at'))
            })

        return all_connections

    except Exception as e:
        print(f"Error getting connections: {e}")
        return []


def get_pending_connection_requests(user_id: str) -> List[Dict[str, Any]]:
    """
    Get pending connection requests received by user

    Args:
        user_id: User's UUID

    Returns:
        List of pending requests with requester details
    """
    supabase = auth.get_supabase_client()

    try:
        # Get requests where user is the target (connected_user_id)
        response = supabase.table('user_connections')\
            .select('*, users!user_connections_user_id_fkey(id, email, full_name, organization)')\
            .eq('connected_user_id', user_id)\
            .eq('status', 'pending')\
            .execute()

        requests = []
        for req in (response.data if response.data else []):
            requests.append({
                'connection_id': req['id'],
                'requester_id': req['user_id'],
                'requester_email': req['users']['email'],
                'requester_name': req['users']['full_name'],
                'requester_organization': req['users'].get('organization'),
                'requested_at': req['requested_at']
            })

        return requests

    except Exception as e:
        print(f"Error getting pending requests: {e}")
        return []


def update_network_sharing(connection_id: str, share_network: bool) -> Dict[str, Any]:
    """
    Update network sharing permission for a connection

    Args:
        connection_id: ID of connection to update
        share_network: Whether to share network

    Returns:
        dict with 'success' boolean and 'message'
    """
    supabase = auth.get_supabase_client()

    try:
        response = supabase.table('user_connections').update({
            'network_sharing_enabled': share_network
        }).eq('id', connection_id).execute()

        if response.data and len(response.data) > 0:
            return {
                'success': True,
                'message': 'Network sharing updated'
            }
        else:
            return {
                'success': False,
                'message': 'Failed to update sharing settings'
            }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


# ============================================
# EXTENDED NETWORK SEARCH
# ============================================

def get_contacts_from_connected_users(user_id: str) -> pd.DataFrame:
    """
    Get all contacts from users connected to the given user
    (only if network_sharing_enabled is True)

    Args:
        user_id: User's UUID

    Returns:
        DataFrame with contacts and owner information
    """
    supabase = auth.get_supabase_client()

    try:
        # Get accepted connections with network sharing enabled
        connections = get_user_connections(user_id, status='accepted')

        # Filter for connections with network sharing enabled
        sharing_connections = [c for c in connections if c['network_sharing_enabled']]

        if not sharing_connections:
            return pd.DataFrame()

        # Get contacts from all sharing connections
        all_contacts = []

        for conn in sharing_connections:
            # Get contacts for this user
            response = supabase.table('contacts')\
                .select('*')\
                .eq('user_id', conn['user_id'])\
                .execute()

            if response.data:
                for contact in response.data:
                    contact['owner_user_id'] = conn['user_id']
                    contact['owner_name'] = conn['full_name']
                    contact['owner_email'] = conn['email']
                    all_contacts.append(contact)

        if all_contacts:
            df = pd.DataFrame(all_contacts)
            return df
        else:
            return pd.DataFrame()

    except Exception as e:
        print(f"Error getting connected users' contacts: {e}")
        return pd.DataFrame()


def search_extended_network(user_id: str, query: str, user_contacts_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Search across user's own network + connected users' networks

    Args:
        user_id: User's UUID
        query: Search query
        user_contacts_df: User's own contacts DataFrame

    Returns:
        Dict with 'own_contacts' and 'extended_contacts' DataFrames
    """
    # This will be used by the main app's search function
    # Returns both own contacts and extended network contacts

    extended_df = get_contacts_from_connected_users(user_id)

    return {
        'own_contacts': user_contacts_df,
        'extended_contacts': extended_df
    }


def find_connectors_for_contact(user_id: str, contact_name: str, contact_company: str = None) -> List[Dict[str, Any]]:
    """
    Find which connected users have a specific contact

    Args:
        user_id: Current user's UUID
        contact_name: Name of person to find
        contact_company: Optional company name

    Returns:
        List of users who have this contact with contact details
    """
    supabase = auth.get_supabase_client()

    try:
        # Get connections with network sharing enabled
        connections = get_user_connections(user_id, status='accepted')
        sharing_connections = [c for c in connections if c['network_sharing_enabled']]

        connectors = []

        for conn in sharing_connections:
            # Search for contact in this user's network
            query = supabase.table('contacts')\
                .select('*')\
                .eq('user_id', conn['user_id'])\
                .ilike('full_name', f'%{contact_name}%')

            if contact_company:
                query = query.ilike('company', f'%{contact_company}%')

            response = query.execute()

            if response.data and len(response.data) > 0:
                # This connection has the contact
                for contact in response.data:
                    connectors.append({
                        'connector_user_id': conn['user_id'],
                        'connector_name': conn['full_name'],
                        'connector_email': conn['email'],
                        'contact_id': contact['id'],
                        'contact_name': contact['full_name'],
                        'contact_company': contact.get('company'),
                        'contact_position': contact.get('position'),
                        'contact_email': contact.get('email')
                    })

        return connectors

    except Exception as e:
        print(f"Error finding connectors: {e}")
        return []


# ============================================
# INTRODUCTION REQUESTS
# ============================================

def create_intro_request(
    requester_id: str,
    connector_id: str,
    target_contact_id: str,
    target_name: str,
    target_company: str,
    target_position: str,
    target_email: str,
    request_message: str,
    context_for_connector: str = None
) -> Dict[str, Any]:
    """
    Create an introduction request

    Args:
        requester_id: User requesting the intro
        connector_id: User who will make the intro
        target_contact_id: Contact ID in connector's network
        target_name: Name of person to meet
        target_company: Company of person to meet
        target_position: Position of person to meet
        target_email: Email of person to meet
        request_message: Why requester wants the intro
        context_for_connector: Additional context for connector

    Returns:
        dict with 'success' boolean and 'message' or 'request_id'
    """
    supabase = auth.get_supabase_client()

    try:
        response = supabase.table('intro_requests').insert({
            'requester_id': requester_id,
            'connector_id': connector_id,
            'target_contact_id': target_contact_id,
            'target_name': target_name,
            'target_company': target_company,
            'target_position': target_position,
            'target_email': target_email,
            'request_message': request_message,
            'context_for_connector': context_for_connector,
            'status': 'pending'
        }).execute()

        if response.data and len(response.data) > 0:
            return {
                'success': True,
                'message': 'Introduction request sent!',
                'request_id': response.data[0]['id']
            }
        else:
            return {
                'success': False,
                'message': 'Failed to create intro request'
            }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


def get_sent_intro_requests(user_id: str) -> List[Dict[str, Any]]:
    """
    Get intro requests sent by user

    Args:
        user_id: User's UUID

    Returns:
        List of sent intro requests
    """
    supabase = auth.get_supabase_client()

    try:
        response = supabase.table('intro_requests')\
            .select('*, users!intro_requests_connector_id_fkey(full_name, email)')\
            .eq('requester_id', user_id)\
            .order('created_at', desc=True)\
            .execute()

        return response.data if response.data else []

    except Exception as e:
        print(f"Error getting sent requests: {e}")
        return []


def get_received_intro_requests(user_id: str, status: str = 'pending') -> List[Dict[str, Any]]:
    """
    Get intro requests received by user (requests for them to make intros)

    Args:
        user_id: User's UUID
        status: Filter by status (default: 'pending')

    Returns:
        List of received intro requests
    """
    supabase = auth.get_supabase_client()

    try:
        query = supabase.table('intro_requests')\
            .select('*, users!intro_requests_requester_id_fkey(full_name, email)')\
            .eq('connector_id', user_id)\
            .order('created_at', desc=True)

        if status:
            query = query.eq('status', status)

        response = query.execute()

        return response.data if response.data else []

    except Exception as e:
        print(f"Error getting received requests: {e}")
        return []


def accept_intro_request(request_id: str, connector_notes: str = None) -> Dict[str, Any]:
    """
    Accept an intro request

    Args:
        request_id: ID of intro request
        connector_notes: Optional notes from connector

    Returns:
        dict with 'success' boolean and 'message'
    """
    supabase = auth.get_supabase_client()

    try:
        update_data = {
            'status': 'accepted',
            'responded_at': datetime.now().isoformat()
        }

        if connector_notes:
            update_data['response_message'] = connector_notes

        response = supabase.table('intro_requests').update(update_data).eq('id', request_id).execute()

        if response.data and len(response.data) > 0:
            return {
                'success': True,
                'message': 'Introduction request accepted!',
                'request': response.data[0]
            }
        else:
            return {
                'success': False,
                'message': 'Failed to accept intro request'
            }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


def decline_intro_request(request_id: str, reason: str) -> Dict[str, Any]:
    """
    Decline an intro request

    Args:
        request_id: ID of intro request
        reason: Reason for declining

    Returns:
        dict with 'success' boolean and 'message'
    """
    supabase = auth.get_supabase_client()

    try:
        response = supabase.table('intro_requests').update({
            'status': 'declined',
            'response_message': reason,
            'responded_at': datetime.now().isoformat()
        }).eq('id', request_id).execute()

        if response.data and len(response.data) > 0:
            return {
                'success': True,
                'message': 'Introduction request declined'
            }
        else:
            return {
                'success': False,
                'message': 'Failed to decline intro request'
            }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }


def mark_intro_completed(request_id: str) -> Dict[str, Any]:
    """
    Mark an intro request as completed (intro was made)

    Args:
        request_id: ID of intro request

    Returns:
        dict with 'success' boolean and 'message'
    """
    supabase = auth.get_supabase_client()

    try:
        response = supabase.table('intro_requests').update({
            'status': 'completed',
            'intro_email_sent': True
        }).eq('id', request_id).execute()

        if response.data and len(response.data) > 0:
            return {
                'success': True,
                'message': 'Introduction marked as completed'
            }
        else:
            return {
                'success': False,
                'message': 'Failed to update intro request'
            }

    except Exception as e:
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }
