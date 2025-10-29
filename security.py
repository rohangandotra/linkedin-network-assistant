"""
Security Module for 6th Degree
Handles password reset, email verification, rate limiting, and security auditing
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from supabase import create_client, Client
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables
load_dotenv()

# Import auth module for Supabase client and password hashing
import auth

# ============================================
# EMAIL SENDING
# ============================================

def send_email(to_email: str, subject: str, html_body: str, text_body: str = None, bcc_email: str = None) -> bool:
    """
    Send an email using SMTP (Gmail or custom SMTP server)

    Args:
        to_email: Recipient email
        subject: Email subject
        html_body: HTML email body
        text_body: Plain text fallback (optional)
        bcc_email: BCC recipient email (optional)

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Get SMTP settings from environment
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        from_email = os.getenv('FROM_EMAIL', smtp_username)

        if not smtp_username or not smtp_password:
            print("⚠️ SMTP credentials not configured. Email not sent.")
            print(f"Would have sent to {to_email}: {subject}")
            print(f"Body: {text_body or html_body[:200]}")
            return False

        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email

        # Add BCC if provided
        if bcc_email:
            msg['Bcc'] = bcc_email

        # Add plain text and HTML parts
        if text_body:
            part1 = MIMEText(text_body, 'plain')
            msg.attach(part1)

        part2 = MIMEText(html_body, 'html')
        msg.attach(part2)

        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)

        print(f"✅ Email sent to {to_email}" + (f" (BCC: {bcc_email})" if bcc_email else ""))
        return True

    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return False


# ============================================
# PASSWORD RESET
# ============================================

def generate_reset_token() -> str:
    """Generate a secure random token for password reset"""
    return secrets.token_urlsafe(32)


def request_password_reset(email: str) -> Dict[str, Any]:
    """
    Request a password reset for an email address

    Args:
        email: User's email address

    Returns:
        dict with 'success' boolean and 'message'
    """
    supabase = auth.get_supabase_client()

    try:
        # Check if user exists
        response = supabase.table('users').select('*').eq('email', email).execute()

        if not response.data or len(response.data) == 0:
            # Don't reveal if email exists (security best practice)
            return {
                'success': True,
                'message': 'If that email exists, a password reset link has been sent.'
            }

        user = response.data[0]
        user_id = user['id']

        # Generate reset token
        token = generate_reset_token()
        expires_at = datetime.now() + timedelta(minutes=15)  # 15 minute expiry

        # Save token to database
        supabase.table('password_reset_tokens').insert({
            'user_id': user_id,
            'token': token,
            'expires_at': expires_at.isoformat(),
            'used': False
        }).execute()

        # Log security event
        log_security_event(user_id, email, 'password_reset_requested')

        # Send email with reset link
        app_url = os.getenv('APP_URL', 'https://6thdegree.streamlit.app')
        reset_link = f"{app_url}?reset_token={token}"

        html_body = f"""
        <html>
        <body style='font-family: Arial, sans-serif;'>
            <h2>Password Reset Request</h2>
            <p>Hi {user['full_name']},</p>
            <p>You requested to reset your password for 6th Degree.</p>
            <p>Click the link below to reset your password:</p>
            <p><a href='{reset_link}' style='background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;'>Reset Password</a></p>
            <p>Or copy and paste this link: <br>{reset_link}</p>
            <p><strong>This link expires in 15 minutes.</strong></p>
            <p>If you didn't request this, please ignore this email.</p>
            <br>
            <p>Best,<br>6th Degree Team</p>
        </body>
        </html>
        """

        text_body = f"""
        Password Reset Request

        Hi {user['full_name']},

        You requested to reset your password for 6th Degree.

        Click this link to reset your password:
        {reset_link}

        This link expires in 15 minutes.

        If you didn't request this, please ignore this email.

        Best,
        6th Degree Team
        """

        send_email(email, "Reset Your Password", html_body, text_body)

        return {
            'success': True,
            'message': 'If that email exists, a password reset link has been sent.'
        }

    except Exception as e:
        print(f"Error in request_password_reset: {e}")
        return {
            'success': False,
            'message': 'An error occurred. Please try again.'
        }


def verify_reset_token(token: str) -> Optional[str]:
    """
    Verify a password reset token

    Args:
        token: Reset token from URL

    Returns:
        user_id if token is valid, None otherwise
    """
    supabase = auth.get_supabase_client()

    try:
        # Find token
        response = supabase.table('password_reset_tokens')\
            .select('*')\
            .eq('token', token)\
            .eq('used', False)\
            .execute()

        if not response.data or len(response.data) == 0:
            return None

        token_data = response.data[0]

        # Check if expired
        expires_at = datetime.fromisoformat(token_data['expires_at'].replace('Z', '+00:00'))
        if datetime.now(expires_at.tzinfo) > expires_at:
            return None

        return token_data['user_id']

    except Exception as e:
        print(f"Error in verify_reset_token: {e}")
        return None


def reset_password_with_token(token: str, new_password: str) -> Dict[str, Any]:
    """
    Reset password using a valid token

    Args:
        token: Reset token
        new_password: New password

    Returns:
        dict with 'success' boolean and 'message'
    """
    supabase = auth.get_supabase_client()

    try:
        # Verify token
        user_id = verify_reset_token(token)

        if not user_id:
            return {
                'success': False,
                'message': 'Invalid or expired reset link.'
            }

        # Hash new password
        new_hash = auth.hash_password(new_password)

        # Update password
        supabase.table('users').update({
            'password_hash': new_hash
        }).eq('id', user_id).execute()

        # Mark token as used
        supabase.table('password_reset_tokens').update({
            'used': True,
            'used_at': datetime.now().isoformat()
        }).eq('token', token).execute()

        # Get user email for logging
        user_response = supabase.table('users').select('email').eq('id', user_id).execute()
        email = user_response.data[0]['email'] if user_response.data else None

        # Log security event
        log_security_event(user_id, email, 'password_reset_completed')

        return {
            'success': True,
            'message': 'Password reset successfully! You can now log in.'
        }

    except Exception as e:
        print(f"Error in reset_password_with_token: {e}")
        return {
            'success': False,
            'message': 'An error occurred. Please try again.'
        }


# ============================================
# EMAIL VERIFICATION
# ============================================

def send_verification_email(user_id: str, email: str, full_name: str) -> bool:
    """
    Send email verification link

    Args:
        user_id: User's UUID
        email: User's email
        full_name: User's name

    Returns:
        True if sent successfully
    """
    supabase = auth.get_supabase_client()

    try:
        # Generate verification token
        token = generate_reset_token()
        expires_at = datetime.now() + timedelta(days=7)  # 7 day expiry

        # Save token to users table
        supabase.table('users').update({
            'verification_token': token,
            'verification_token_expires': expires_at.isoformat()
        }).eq('id', user_id).execute()

        # Log security event
        log_security_event(user_id, email, 'verification_email_sent')

        # Send email
        app_url = os.getenv('APP_URL', 'https://6thdegree.streamlit.app')
        verify_link = f"{app_url}?verify_email={token}"

        html_body = f"""
        <html>
        <body style='font-family: Arial, sans-serif;'>
            <h2>Verify Your Email</h2>
            <p>Hi {full_name},</p>
            <p>Welcome to 6th Degree! Please verify your email to get started.</p>
            <p><a href='{verify_link}' style='background: #10b981; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block;'>Verify Email</a></p>
            <p>Or copy and paste this link: <br>{verify_link}</p>
            <p>This link expires in 7 days.</p>
            <br>
            <p>Best,<br>6th Degree Team</p>
        </body>
        </html>
        """

        text_body = f"""
        Verify Your Email

        Hi {full_name},

        Welcome to 6th Degree! Please verify your email to get started.

        Click this link: {verify_link}

        This link expires in 7 days.

        Best,
        6th Degree Team
        """

        # BCC admin email on all verification emails
        admin_bcc = "noreply.6thdegree@gmail.com"
        return send_email(email, "Verify Your Email", html_body, text_body, bcc_email=admin_bcc)

    except Exception as e:
        print(f"Error sending verification email: {e}")
        return False


def verify_email_token(token: str) -> Dict[str, Any]:
    """
    Verify email using token

    Args:
        token: Verification token from URL

    Returns:
        dict with 'success' boolean and 'message'
    """
    supabase = auth.get_supabase_client()

    try:
        # Find user with this token
        response = supabase.table('users')\
            .select('*')\
            .eq('verification_token', token)\
            .execute()

        if not response.data or len(response.data) == 0:
            return {
                'success': False,
                'message': 'Invalid verification link.'
            }

        user = response.data[0]

        # Check if already verified
        if user.get('email_verified'):
            return {
                'success': True,
                'message': 'Email already verified! You can log in.'
            }

        # Check if expired
        if user.get('verification_token_expires'):
            expires_at = datetime.fromisoformat(user['verification_token_expires'].replace('Z', '+00:00'))
            if datetime.now(expires_at.tzinfo) > expires_at:
                return {
                    'success': False,
                    'message': 'Verification link expired. Please request a new one.'
                }

        # Mark as verified
        supabase.table('users').update({
            'email_verified': True,
            'is_verified': True,  # Keep for backwards compatibility
            'verification_token': None
        }).eq('id', user['id']).execute()

        # Log security event
        log_security_event(user['id'], user['email'], 'email_verified')

        return {
            'success': True,
            'message': 'Email verified successfully! You can now log in.'
        }

    except Exception as e:
        print(f"Error in verify_email_token: {e}")
        return {
            'success': False,
            'message': 'An error occurred. Please try again.'
        }


# ============================================
# RATE LIMITING
# ============================================

def check_login_rate_limit(email: str, ip_address: str = None) -> Dict[str, Any]:
    """
    Check if user has exceeded login attempt rate limit

    Args:
        email: Email address attempting to log in
        ip_address: IP address (optional)

    Returns:
        dict with 'allowed' boolean and 'message'
    """
    supabase = auth.get_supabase_client()

    try:
        # Check last 15 minutes of failed attempts
        fifteen_min_ago = datetime.now() - timedelta(minutes=15)

        response = supabase.table('login_attempts')\
            .select('*')\
            .eq('email', email)\
            .eq('success', False)\
            .gte('attempted_at', fifteen_min_ago.isoformat())\
            .execute()

        failed_attempts = len(response.data) if response.data else 0

        if failed_attempts >= 5:
            return {
                'allowed': False,
                'message': 'Too many failed login attempts. Please try again in 15 minutes.'
            }

        return {
            'allowed': True,
            'remaining_attempts': 5 - failed_attempts
        }

    except Exception as e:
        print(f"Error checking rate limit: {e}")
        # Allow login if rate limit check fails (fail open)
        return {'allowed': True}


def log_login_attempt(email: str, success: bool, ip_address: str = None, user_agent: str = None):
    """
    Log a login attempt

    Args:
        email: Email address
        success: Whether login was successful
        ip_address: IP address (optional)
        user_agent: User agent string (optional)
    """
    supabase = auth.get_supabase_client()

    try:
        supabase.table('login_attempts').insert({
            'email': email,
            'success': success,
            'ip_address': ip_address,
            'user_agent': user_agent
        }).execute()

        # Log security event for failed logins
        if not success:
            # Get user_id if exists
            user_response = supabase.table('users').select('id').eq('email', email).execute()
            user_id = user_response.data[0]['id'] if user_response.data else None

            log_security_event(user_id, email, 'failed_login', {
                'ip_address': ip_address,
                'user_agent': user_agent
            })

    except Exception as e:
        print(f"Error logging login attempt: {e}")


# ============================================
# SECURITY EVENT LOGGING
# ============================================

def log_security_event(
    user_id: Optional[str],
    email: Optional[str],
    event_type: str,
    metadata: Dict[str, Any] = None,
    ip_address: str = None,
    user_agent: str = None
):
    """
    Log a security event

    Args:
        user_id: User UUID (optional)
        email: User email (optional)
        event_type: Type of event
        metadata: Additional data (optional)
        ip_address: IP address (optional)
        user_agent: User agent (optional)
    """
    supabase = auth.get_supabase_client()

    try:
        supabase.table('security_events').insert({
            'user_id': user_id,
            'email': email,
            'event_type': event_type,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'metadata': metadata
        }).execute()
    except Exception as e:
        print(f"Error logging security event: {e}")


# ============================================
# SECURITY AUDIT FUNCTIONS
# ============================================

def check_password_strength(password: str) -> Dict[str, Any]:
    """
    Check password strength

    Args:
        password: Password to check

    Returns:
        dict with 'strong' boolean and 'message'
    """
    issues = []

    if len(password) < 8:
        issues.append("at least 8 characters")
    if not any(c.isupper() for c in password):
        issues.append("one uppercase letter")
    if not any(c.islower() for c in password):
        issues.append("one lowercase letter")
    if not any(c.isdigit() for c in password):
        issues.append("one number")

    if issues:
        return {
            'strong': False,
            'message': f"Password must contain {', '.join(issues)}."
        }

    return {
        'strong': True,
        'message': 'Password is strong'
    }


def sanitize_input(text: str) -> str:
    """
    Sanitize user input to prevent XSS

    Args:
        text: User input

    Returns:
        Sanitized text
    """
    if not text:
        return text

    # Basic HTML escaping
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&#x27;')

    return text
