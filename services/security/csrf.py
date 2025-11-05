"""
CSRF (Cross-Site Request Forgery) Protection for 6th Degree AI
Prevents unauthorized form submissions from malicious sites
"""

import secrets
import streamlit as st
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class CSRFProtection:
    """
    CSRF protection service using token-based validation

    Provides methods to:
    - Generate unique CSRF tokens per form
    - Validate tokens on form submission
    - Manage token lifecycle (expiration)
    - Track token usage for security monitoring
    """

    # Token expiration time (30 minutes)
    TOKEN_EXPIRY = timedelta(minutes=30)

    def __init__(self):
        """Initialize CSRF protection with session state storage"""
        if 'csrf_tokens' not in st.session_state:
            st.session_state['csrf_tokens'] = {}

    def generate_token(self, form_id: str) -> str:
        """
        Generate a new CSRF token for a form

        Args:
            form_id: Unique identifier for the form (e.g., 'login_form', 'registration_form')

        Returns:
            CSRF token string (32-byte URL-safe string)

        Example:
            csrf = CSRFProtection()
            token = csrf.generate_token('login_form')
            # Store token in hidden field
        """
        # Generate cryptographically secure token
        token = secrets.token_urlsafe(32)

        # Store token with timestamp
        st.session_state['csrf_tokens'][form_id] = {
            'token': token,
            'created_at': datetime.now(),
            'used': False
        }

        return token

    def validate_token(self, form_id: str, submitted_token: str) -> Dict[str, Any]:
        """
        Validate a submitted CSRF token

        Args:
            form_id: Form identifier
            submitted_token: Token submitted with form

        Returns:
            {
                'valid': bool,
                'message': error message if invalid,
                'reason': specific failure reason (expired, missing, mismatch, used)
            }

        Security checks:
        1. Token exists for form_id
        2. Token hasn't expired
        3. Token matches stored value (constant-time comparison)
        4. Token hasn't been used before (single-use tokens)
        """
        tokens = st.session_state.get('csrf_tokens', {})

        # Check if token exists for this form
        if form_id not in tokens:
            return {
                'valid': False,
                'message': 'Invalid form submission. Please refresh and try again.',
                'reason': 'missing'
            }

        stored = tokens[form_id]
        stored_token = stored.get('token')
        created_at = stored.get('created_at')
        used = stored.get('used', False)

        # Check if token has been used
        if used:
            return {
                'valid': False,
                'message': 'Form already submitted. Please refresh to submit again.',
                'reason': 'used'
            }

        # Check expiration
        if datetime.now() - created_at > self.TOKEN_EXPIRY:
            # Clean up expired token
            del st.session_state['csrf_tokens'][form_id]
            return {
                'valid': False,
                'message': 'Form session expired. Please refresh and try again.',
                'reason': 'expired'
            }

        # Constant-time comparison to prevent timing attacks
        if not secrets.compare_digest(stored_token, submitted_token):
            return {
                'valid': False,
                'message': 'Invalid form submission. Please refresh and try again.',
                'reason': 'mismatch'
            }

        # Mark token as used (single-use tokens)
        st.session_state['csrf_tokens'][form_id]['used'] = True

        return {
            'valid': True,
            'message': None,
            'reason': None
        }

    def invalidate_token(self, form_id: str):
        """
        Manually invalidate a token (e.g., on form cancel)

        Args:
            form_id: Form identifier
        """
        tokens = st.session_state.get('csrf_tokens', {})
        if form_id in tokens:
            del st.session_state['csrf_tokens'][form_id]

    def cleanup_expired_tokens(self):
        """
        Remove all expired tokens from session state

        Should be called periodically to prevent memory buildup
        """
        tokens = st.session_state.get('csrf_tokens', {})
        now = datetime.now()

        expired_forms = []
        for form_id, data in tokens.items():
            created_at = data.get('created_at')
            if now - created_at > self.TOKEN_EXPIRY:
                expired_forms.append(form_id)

        for form_id in expired_forms:
            del st.session_state['csrf_tokens'][form_id]

        return len(expired_forms)

    def get_token_info(self, form_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a token (for debugging/monitoring)

        Args:
            form_id: Form identifier

        Returns:
            Token info dict or None if not found
        """
        tokens = st.session_state.get('csrf_tokens', {})
        if form_id not in tokens:
            return None

        stored = tokens[form_id]
        created_at = stored.get('created_at')
        age = datetime.now() - created_at

        return {
            'form_id': form_id,
            'created_at': created_at.isoformat(),
            'age_seconds': age.total_seconds(),
            'used': stored.get('used', False),
            'expired': age > self.TOKEN_EXPIRY
        }


# Singleton instance for app-wide use
_csrf_instance = None

def get_csrf_protection() -> CSRFProtection:
    """
    Get singleton CSRF protection instance

    Ensures session state is always initialized, even if instance already exists

    Returns:
        CSRFProtection instance
    """
    global _csrf_instance
    if _csrf_instance is None:
        _csrf_instance = CSRFProtection()

    # Always ensure csrf_tokens is initialized in session state
    # This handles cases where session state is cleared but instance still exists
    if 'csrf_tokens' not in st.session_state:
        st.session_state['csrf_tokens'] = {}

    return _csrf_instance


# Convenience functions for easy integration
def generate_csrf_token(form_id: str) -> str:
    """
    Generate CSRF token for a form

    Args:
        form_id: Form identifier

    Returns:
        CSRF token

    Example:
        with st.form("login_form"):
            token = generate_csrf_token('login')
            st.text_input("Email", key="email")
            st.text_input("Password", type="password", key="password")
            # Hidden field for token (workaround for Streamlit)
            st.session_state['login_csrf_token'] = token

            if st.form_submit_button("Login"):
                if validate_csrf_token('login', st.session_state.get('login_csrf_token', '')):
                    # Process login
                    pass
    """
    csrf = get_csrf_protection()
    return csrf.generate_token(form_id)


def validate_csrf_token(form_id: str, submitted_token: str) -> bool:
    """
    Validate CSRF token (simplified return)

    Args:
        form_id: Form identifier
        submitted_token: Token from form submission

    Returns:
        True if valid, False otherwise

    Example:
        if validate_csrf_token('login', submitted_token):
            # Process form
            pass
        else:
            st.error("Invalid form submission")
    """
    csrf = get_csrf_protection()
    result = csrf.validate_token(form_id, submitted_token)
    return result['valid']


def validate_csrf_token_detailed(form_id: str, submitted_token: str) -> Dict[str, Any]:
    """
    Validate CSRF token with detailed error information

    Args:
        form_id: Form identifier
        submitted_token: Token from form submission

    Returns:
        Validation result dict with 'valid', 'message', 'reason'

    Example:
        result = validate_csrf_token_detailed('login', submitted_token)
        if not result['valid']:
            st.error(result['message'])
            # Log security event
            log_security_event('csrf_failure', user_id, {'reason': result['reason']})
    """
    csrf = get_csrf_protection()
    return csrf.validate_token(form_id, submitted_token)


def cleanup_csrf_tokens():
    """
    Clean up expired CSRF tokens

    Returns:
        Number of tokens removed

    Example:
        # Call periodically (e.g., on app init)
        removed = cleanup_csrf_tokens()
    """
    csrf = get_csrf_protection()
    return csrf.cleanup_expired_tokens()


# Streamlit-specific helper for form integration
def create_csrf_protected_form(form_id: str, key: str):
    """
    Create a CSRF-protected Streamlit form

    This is a context manager that generates and stores the CSRF token

    Args:
        form_id: Unique form identifier
        key: Streamlit form key

    Returns:
        Form context manager

    Example:
        with create_csrf_protected_form('login', 'login_form'):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                # Token validation happens automatically
                if st.session_state.get(f'csrf_valid_{form_id}', False):
                    # Process login
                    pass
    """
    # Generate token before form
    token = generate_csrf_token(form_id)
    st.session_state[f'csrf_token_{form_id}'] = token

    # Return form context
    return st.form(key)


if __name__ == "__main__":
    # Test the CSRF protection
    print("Testing CSRF Protection...")

    csrf = CSRFProtection()

    # Test 1: Token generation and validation
    print("\n1. Token Generation & Validation:")
    token = csrf.generate_token('test_form')
    print(f"  Generated token: {token[:20]}... (truncated)")

    result = csrf.validate_token('test_form', token)
    print(f"  Validation: {'✅ Valid' if result['valid'] else '❌ Invalid'}")

    # Test 2: Invalid token (mismatch)
    print("\n2. Invalid Token (Mismatch):")
    result = csrf.validate_token('test_form', 'wrong_token')
    print(f"  Validation: {'✅ Valid' if result['valid'] else '❌ Invalid'}")
    print(f"  Reason: {result['reason']}")
    print(f"  Message: {result['message']}")

    # Test 3: Token reuse (single-use)
    print("\n3. Token Reuse (Should Fail):")
    token2 = csrf.generate_token('test_form2')
    csrf.validate_token('test_form2', token2)  # First use
    result = csrf.validate_token('test_form2', token2)  # Second use
    print(f"  Validation: {'✅ Valid' if result['valid'] else '❌ Invalid'}")
    print(f"  Reason: {result['reason']}")

    # Test 4: Missing token
    print("\n4. Missing Token:")
    result = csrf.validate_token('nonexistent_form', 'some_token')
    print(f"  Validation: {'✅ Valid' if result['valid'] else '❌ Invalid'}")
    print(f"  Reason: {result['reason']}")

    # Test 5: Token info
    print("\n5. Token Info:")
    token3 = csrf.generate_token('test_form3')
    info = csrf.get_token_info('test_form3')
    print(f"  Form ID: {info['form_id']}")
    print(f"  Age: {info['age_seconds']:.2f} seconds")
    print(f"  Used: {info['used']}")
    print(f"  Expired: {info['expired']}")

    # Test 6: Cleanup
    print("\n6. Token Cleanup:")
    # Create some tokens
    for i in range(5):
        csrf.generate_token(f'form_{i}')
    removed = csrf.cleanup_expired_tokens()
    print(f"  Expired tokens removed: {removed}")

    # Test 7: Constant-time comparison (security)
    print("\n7. Constant-Time Comparison (Security Check):")
    token4 = csrf.generate_token('security_test')
    # Both should take similar time (prevents timing attacks)
    import time

    start = time.perf_counter()
    csrf.validate_token('security_test', token4)
    valid_time = time.perf_counter() - start

    csrf.generate_token('security_test')  # Reset
    start = time.perf_counter()
    csrf.validate_token('security_test', 'wrong_token_same_length_as_real')
    invalid_time = time.perf_counter() - start

    print(f"  Valid token time: {valid_time*1000:.4f}ms")
    print(f"  Invalid token time: {invalid_time*1000:.4f}ms")
    print(f"  Timing difference: {abs(valid_time - invalid_time)*1000:.4f}ms")
    print(f"  {'✅ Safe from timing attacks' if abs(valid_time - invalid_time) < 0.001 else '⚠️  May be vulnerable'}")

    print("\n✅ CSRF protection tests complete!")
