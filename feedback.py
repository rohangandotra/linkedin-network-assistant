"""
Feedback Module for 6th Degree AI
Handles user feedback and bug reports
"""

from datetime import datetime
from typing import Dict, Any, Optional
import auth  # Import to access Supabase client


def submit_feedback(
    feedback_text: str,
    feedback_type: str = "general",
    page_context: str = "unknown",
    user_id: Optional[str] = None,
    user_email: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Submit user feedback to database

    Args:
        feedback_text: The feedback message
        feedback_type: Type of feedback (bug, feature, general, praise)
        page_context: Which page/section user was on
        user_id: User ID if authenticated
        user_email: User email if provided
        metadata: Additional context (browser, screen size, etc.)

    Returns:
        dict with 'success' boolean and 'message'
    """
    if not feedback_text or not feedback_text.strip():
        return {
            'success': False,
            'message': 'Please enter your feedback'
        }

    try:
        supabase = auth.get_supabase_client()

        feedback_data = {
            'feedback_text': feedback_text.strip(),
            'feedback_type': feedback_type,
            'page_context': page_context,
            'user_id': user_id,
            'user_email': user_email,
            'metadata': metadata or {},
            'created_at': datetime.now().isoformat(),
            'status': 'new'  # new, reviewed, resolved
        }

        response = supabase.table('feedback').insert(feedback_data).execute()

        if response.data and len(response.data) > 0:
            return {
                'success': True,
                'message': 'Thank you! Your feedback has been submitted.'
            }
        else:
            return {
                'success': False,
                'message': 'Failed to submit feedback. Please try again.'
            }

    except Exception as e:
        print(f"Error submitting feedback: {e}")
        # If database fails, at least log it locally
        log_feedback_locally(feedback_text, feedback_type, user_id)

        return {
            'success': False,
            'message': f'Error submitting feedback: {str(e)}'
        }


def log_feedback_locally(feedback_text: str, feedback_type: str, user_id: Optional[str]):
    """
    Fallback: Log feedback to local file if database unavailable
    """
    try:
        with open('feedback_log.txt', 'a') as f:
            timestamp = datetime.now().isoformat()
            f.write(f"\n[{timestamp}] Type: {feedback_type} | User: {user_id or 'anonymous'}\n")
            f.write(f"{feedback_text}\n")
            f.write("-" * 80 + "\n")
    except Exception as e:
        print(f"Failed to log feedback locally: {e}")


def get_all_feedback(status: Optional[str] = None, limit: int = 100) -> list:
    """
    Get feedback submissions (admin only)

    Args:
        status: Filter by status (new, reviewed, resolved)
        limit: Max number of results

    Returns:
        List of feedback submissions
    """
    try:
        supabase = auth.get_supabase_client()

        query = supabase.table('feedback').select("*").order('created_at', desc=True).limit(limit)

        if status:
            query = query.eq('status', status)

        response = query.execute()

        if response.data:
            return response.data

        return []

    except Exception as e:
        print(f"Error fetching feedback: {e}")
        return []


def update_feedback_status(feedback_id: str, new_status: str) -> bool:
    """
    Update feedback status (admin only)

    Args:
        feedback_id: Feedback UUID
        new_status: new, reviewed, resolved

    Returns:
        True if successful, False otherwise
    """
    try:
        supabase = auth.get_supabase_client()

        supabase.table('feedback').update({
            'status': new_status,
            'updated_at': datetime.now().isoformat()
        }).eq('id', feedback_id).execute()

        return True

    except Exception as e:
        print(f"Error updating feedback status: {e}")
        return False
