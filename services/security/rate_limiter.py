"""
Rate Limiting Service for 6th Degree AI
Prevents abuse and controls costs by limiting API calls
"""

from datetime import datetime, timedelta
from typing import Dict, Tuple, Optional
from collections import defaultdict
import streamlit as st


class RateLimiter:
    """
    Rate limiter to prevent abuse and control costs

    Uses sliding window algorithm with in-memory storage
    For production, consider Redis or database storage
    """

    # Rate limits: (max_attempts, window_seconds)
    LIMITS = {
        'search': (20, 300),           # 20 searches per 5 minutes
        'email_gen': (10, 300),         # 10 emails per 5 minutes
        'connection_request': (5, 3600), # 5 requests per hour
        'feedback': (3, 3600),          # 3 feedback per hour
        'csv_upload': (3, 3600),        # 3 uploads per hour
        'intro_request': (10, 3600),    # 10 intro requests per hour
    }

    def __init__(self):
        """Initialize rate limiter with in-memory storage"""
        # Store attempts: {user_id:action -> [timestamps]}
        if 'rate_limiter_attempts' not in st.session_state:
            st.session_state['rate_limiter_attempts'] = defaultdict(list)

        self.attempts = st.session_state['rate_limiter_attempts']

    def check_limit(self, user_id: str, action: str) -> Tuple[bool, Optional[str]]:
        """
        Check if user has exceeded rate limit for an action

        Args:
            user_id: User identifier (or IP for anonymous)
            action: Action type (search, email_gen, etc.)

        Returns:
            (allowed: bool, message: Optional[str])
            - (True, None) if allowed
            - (False, "error message") if rate limited
        """
        if action not in self.LIMITS:
            # Unknown action, allow by default
            return True, None

        max_attempts, window = self.LIMITS[action]
        now = datetime.now()
        cutoff = now - timedelta(seconds=window)

        # Clean old attempts
        key = f"{user_id}:{action}"
        self.attempts[key] = [t for t in self.attempts[key] if t > cutoff]

        # Check limit
        current_count = len(self.attempts[key])
        if current_count >= max_attempts:
            # Calculate when they can retry
            oldest_attempt = min(self.attempts[key])
            retry_after = oldest_attempt + timedelta(seconds=window)
            wait_minutes = int((retry_after - now).total_seconds() / 60) + 1

            message = f"Rate limit exceeded. You can try again in {wait_minutes} minute(s)."
            return False, message

        # Record attempt
        self.attempts[key].append(now)

        # Update session state
        st.session_state['rate_limiter_attempts'] = self.attempts

        return True, None

    def get_remaining(self, user_id: str, action: str) -> Tuple[int, int]:
        """
        Get remaining attempts for a user/action

        Args:
            user_id: User identifier
            action: Action type

        Returns:
            (remaining: int, max: int)
        """
        if action not in self.LIMITS:
            return -1, -1  # Unknown action

        max_attempts, window = self.LIMITS[action]
        now = datetime.now()
        cutoff = now - timedelta(seconds=window)

        # Clean old attempts
        key = f"{user_id}:{action}"
        self.attempts[key] = [t for t in self.attempts[key] if t > cutoff]

        current_count = len(self.attempts[key])
        remaining = max(0, max_attempts - current_count)

        return remaining, max_attempts

    def reset_limit(self, user_id: str, action: str):
        """
        Reset rate limit for a user/action (admin function)

        Args:
            user_id: User identifier
            action: Action type
        """
        key = f"{user_id}:{action}"
        if key in self.attempts:
            self.attempts[key] = []
            st.session_state['rate_limiter_attempts'] = self.attempts

    def get_all_limits(self) -> Dict[str, Tuple[int, int]]:
        """
        Get all configured rate limits

        Returns:
            Dict of {action: (max_attempts, window_seconds)}
        """
        return self.LIMITS.copy()


# Singleton instance for app-wide use
_rate_limiter_instance = None

def get_rate_limiter() -> RateLimiter:
    """
    Get singleton rate limiter instance

    Returns:
        RateLimiter instance
    """
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        _rate_limiter_instance = RateLimiter()
    return _rate_limiter_instance


# Convenience functions
def check_rate_limit(user_id: str, action: str) -> Tuple[bool, Optional[str]]:
    """
    Check rate limit for a user/action

    Args:
        user_id: User identifier
        action: Action type (search, email_gen, etc.)

    Returns:
        (allowed: bool, error_message: Optional[str])

    Example:
        allowed, error = check_rate_limit(user_id, 'search')
        if not allowed:
            st.error(error)
            return
    """
    limiter = get_rate_limiter()
    return limiter.check_limit(user_id, action)


def get_remaining_attempts(user_id: str, action: str) -> Tuple[int, int]:
    """
    Get remaining attempts for a user/action

    Args:
        user_id: User identifier
        action: Action type

    Returns:
        (remaining: int, max: int)

    Example:
        remaining, max_attempts = get_remaining_attempts(user_id, 'search')
        st.info(f"You have {remaining}/{max_attempts} searches remaining")
    """
    limiter = get_rate_limiter()
    return limiter.get_remaining(user_id, action)


if __name__ == "__main__":
    # Test the rate limiter
    print("Testing Rate Limiter...")

    limiter = RateLimiter()
    user_id = "test_user"

    # Test search rate limit (20 per 5 min)
    print("\n1. Testing search rate limit (20 per 5 min):")
    for i in range(25):
        allowed, message = limiter.check_limit(user_id, 'search')
        remaining, max_attempts = limiter.get_remaining(user_id, 'search')

        if allowed:
            print(f"  Search {i+1}: ✅ Allowed (Remaining: {remaining}/{max_attempts})")
        else:
            print(f"  Search {i+1}: ❌ Blocked - {message}")

    # Test email generation limit (10 per 5 min)
    print("\n2. Testing email generation limit (10 per 5 min):")
    for i in range(12):
        allowed, message = limiter.check_limit(user_id, 'email_gen')
        remaining, max_attempts = limiter.get_remaining(user_id, 'email_gen')

        if allowed:
            print(f"  Email {i+1}: ✅ Allowed (Remaining: {remaining}/{max_attempts})")
        else:
            print(f"  Email {i+1}: ❌ Blocked - {message}")

    # Test reset
    print("\n3. Testing reset:")
    print(f"  Before reset: {limiter.get_remaining(user_id, 'search')}")
    limiter.reset_limit(user_id, 'search')
    print(f"  After reset: {limiter.get_remaining(user_id, 'search')}")

    print("\n✅ Rate limiter tests complete!")
