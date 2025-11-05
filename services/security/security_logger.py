"""
Security Logging Service for 6th Degree AI
Structured logging for security events, monitoring, and auditing
"""

import logging
import json
import streamlit as st
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path
from collections import defaultdict


class SecurityLogger:
    """
    Security event logging and monitoring service

    Provides methods to:
    - Log security events (failed logins, CSRF failures, rate limits, etc.)
    - Track suspicious activity patterns
    - Monitor error rates
    - Generate security alerts
    - Provide audit trail
    """

    # Security event types
    EVENT_TYPES = {
        'login_failed': 'high',          # Failed login attempt
        'login_success': 'info',         # Successful login
        'csrf_failure': 'high',          # CSRF token validation failed
        'rate_limit_exceeded': 'medium', # Rate limit hit
        'xss_attempt': 'critical',       # XSS attack detected
        'sql_injection_attempt': 'critical', # SQL injection detected
        'prompt_injection': 'high',      # Prompt injection detected
        'malicious_csv': 'high',         # Malicious CSV upload
        'unauthorized_access': 'critical', # Unauthorized access attempt
        'password_reset': 'info',        # Password reset initiated
        'email_verified': 'info',        # Email verification
        'session_expired': 'info',       # Session timeout
        'api_error': 'medium',           # API error
        'data_access': 'info',           # Data access (for audit)
    }

    # Alert thresholds
    ALERT_THRESHOLDS = {
        'login_failed': 5,          # 5 failed logins
        'csrf_failure': 3,          # 3 CSRF failures
        'xss_attempt': 1,           # 1 XSS attempt
        'sql_injection_attempt': 1, # 1 SQL injection attempt
        'rate_limit_exceeded': 10,  # 10 rate limit hits
    }

    def __init__(self, log_file: str = 'security.log', console: bool = True):
        """
        Initialize security logger

        Args:
            log_file: Path to log file
            console: Whether to also log to console
        """
        self.log_file = log_file
        self.console = console

        # Setup logger
        self.logger = logging.getLogger('6th_degree_security')
        self.logger.setLevel(logging.INFO)

        # Clear existing handlers
        self.logger.handlers = []

        # File handler (JSON format for structured logging)
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(message)s'))  # JSON only
        self.logger.addHandler(file_handler)

        # Console handler (human-readable)
        if console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.WARNING)  # Only warnings and above
            console_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            )
            self.logger.addHandler(console_handler)

        # Initialize session state for event tracking
        if 'security_events' not in st.session_state:
            st.session_state['security_events'] = defaultdict(list)

    def log_event(
        self,
        event_type: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        severity: Optional[str] = None
    ):
        """
        Log a security event

        Args:
            event_type: Type of security event (from EVENT_TYPES)
            user_id: User identifier (or IP for anonymous)
            details: Additional event details
            severity: Override default severity (info, medium, high, critical)

        Example:
            logger.log_event(
                'login_failed',
                user_id='user@example.com',
                details={'ip': '192.168.1.1', 'reason': 'invalid_password'}
            )
        """
        # Determine severity
        if severity is None:
            severity = self.EVENT_TYPES.get(event_type, 'info')

        # Build log entry
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'severity': severity,
            'user_id': user_id or 'anonymous',
            'details': details or {},
            'session_id': st.session_state.get('session_id', 'unknown')
        }

        # Log to file (JSON format)
        self.logger.info(json.dumps(log_entry))

        # Track in session state for real-time monitoring
        if user_id:
            st.session_state['security_events'][user_id].append({
                'event_type': event_type,
                'timestamp': datetime.now(),
                'severity': severity
            })

        # Check alert thresholds
        self._check_alerts(event_type, user_id)

        # Print to console if critical
        if severity == 'critical':
            print(f"🚨 CRITICAL SECURITY EVENT: {event_type} - User: {user_id}")
            print(f"   Details: {details}")

    def log_failed_login(self, email: str, ip: str, reason: str):
        """Log failed login attempt"""
        self.log_event(
            'login_failed',
            user_id=email,
            details={'ip': ip, 'reason': reason}
        )

    def log_successful_login(self, user_id: str, email: str, ip: str):
        """Log successful login"""
        self.log_event(
            'login_success',
            user_id=user_id,
            details={'email': email, 'ip': ip}
        )

    def log_csrf_failure(self, form_id: str, user_id: Optional[str], reason: str):
        """Log CSRF validation failure"""
        self.log_event(
            'csrf_failure',
            user_id=user_id,
            details={'form_id': form_id, 'reason': reason},
            severity='high'
        )

    def log_rate_limit(self, user_id: str, action: str, wait_minutes: int):
        """Log rate limit hit"""
        self.log_event(
            'rate_limit_exceeded',
            user_id=user_id,
            details={'action': action, 'wait_minutes': wait_minutes}
        )

    def log_malicious_input(self, input_type: str, user_id: Optional[str], patterns: List[str], severity: str):
        """Log detected malicious input"""
        event_mapping = {
            'xss': 'xss_attempt',
            'sql': 'sql_injection_attempt',
            'prompt': 'prompt_injection'
        }
        event_type = event_mapping.get(input_type, 'xss_attempt')

        self.log_event(
            event_type,
            user_id=user_id,
            details={'patterns': patterns},
            severity=severity
        )

    def log_api_error(self, api: str, error: str, user_id: Optional[str] = None):
        """Log API error"""
        self.log_event(
            'api_error',
            user_id=user_id,
            details={'api': api, 'error': str(error)}
        )

    def log_data_access(self, user_id: str, resource: str, action: str):
        """Log data access for audit trail"""
        self.log_event(
            'data_access',
            user_id=user_id,
            details={'resource': resource, 'action': action},
            severity='info'
        )

    def _check_alerts(self, event_type: str, user_id: Optional[str]):
        """
        Check if event triggers alert threshold

        Args:
            event_type: Type of event
            user_id: User identifier
        """
        if event_type not in self.ALERT_THRESHOLDS:
            return

        if not user_id:
            return

        # Count recent events of this type for this user
        events = st.session_state['security_events'].get(user_id, [])
        recent_events = [
            e for e in events
            if e['event_type'] == event_type and
            (datetime.now() - e['timestamp']).total_seconds() < 3600  # Last hour
        ]

        threshold = self.ALERT_THRESHOLDS[event_type]
        if len(recent_events) >= threshold:
            self._trigger_alert(event_type, user_id, len(recent_events))

    def _trigger_alert(self, event_type: str, user_id: str, count: int):
        """
        Trigger security alert

        Args:
            event_type: Type of event
            user_id: User identifier
            count: Number of events
        """
        alert = {
            'timestamp': datetime.now().isoformat(),
            'alert_type': f'threshold_exceeded_{event_type}',
            'user_id': user_id,
            'event_count': count,
            'threshold': self.ALERT_THRESHOLDS[event_type],
            'severity': 'critical'
        }

        # Log alert
        self.logger.warning(f"ALERT: {json.dumps(alert)}")

        # Print to console
        print(f"\n🚨 SECURITY ALERT 🚨")
        print(f"   Type: {event_type}")
        print(f"   User: {user_id}")
        print(f"   Count: {count} (Threshold: {self.ALERT_THRESHOLDS[event_type]})")
        print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

        # TODO: Send email alert to admin
        # TODO: Add to admin dashboard

    def get_user_events(self, user_id: str, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get security events for a user

        Args:
            user_id: User identifier
            event_type: Filter by event type (optional)

        Returns:
            List of events
        """
        events = st.session_state['security_events'].get(user_id, [])

        if event_type:
            events = [e for e in events if e['event_type'] == event_type]

        return events

    def get_event_summary(self) -> Dict[str, int]:
        """
        Get summary of all security events

        Returns:
            Dict of event_type -> count
        """
        summary = defaultdict(int)

        for user_events in st.session_state['security_events'].values():
            for event in user_events:
                summary[event['event_type']] += 1

        return dict(summary)

    def clear_user_events(self, user_id: str):
        """Clear events for a user (admin function)"""
        if user_id in st.session_state['security_events']:
            del st.session_state['security_events'][user_id]

    def parse_log_file(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Parse security log file

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of log entries (most recent first)
        """
        try:
            with open(self.log_file, 'r') as f:
                lines = f.readlines()

            # Parse JSON lines
            entries = []
            for line in reversed(lines[-limit:]):
                try:
                    entry = json.loads(line.strip())
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue

            return entries

        except FileNotFoundError:
            return []


# Singleton instance for app-wide use
_security_logger_instance = None

def get_security_logger() -> SecurityLogger:
    """
    Get singleton security logger instance

    Returns:
        SecurityLogger instance
    """
    global _security_logger_instance
    if _security_logger_instance is None:
        _security_logger_instance = SecurityLogger()
    return _security_logger_instance


# Convenience functions
def log_security_event(
    event_type: str,
    user_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    severity: Optional[str] = None
):
    """
    Log a security event

    Example:
        log_security_event('login_failed', 'user@example.com', {'reason': 'wrong_password'})
    """
    logger = get_security_logger()
    logger.log_event(event_type, user_id, details, severity)


def log_failed_login(email: str, ip: str, reason: str):
    """Log failed login attempt"""
    logger = get_security_logger()
    logger.log_failed_login(email, ip, reason)


def log_successful_login(user_id: str, email: str, ip: str):
    """Log successful login"""
    logger = get_security_logger()
    logger.log_successful_login(user_id, email, ip)


def log_csrf_failure(form_id: str, user_id: Optional[str], reason: str):
    """Log CSRF failure"""
    logger = get_security_logger()
    logger.log_csrf_failure(form_id, user_id, reason)


def log_rate_limit(user_id: str, action: str, wait_minutes: int):
    """Log rate limit hit"""
    logger = get_security_logger()
    logger.log_rate_limit(user_id, action, wait_minutes)


def log_malicious_input(input_type: str, user_id: Optional[str], patterns: List[str], severity: str = 'high'):
    """Log malicious input detection"""
    logger = get_security_logger()
    logger.log_malicious_input(input_type, user_id, patterns, severity)


if __name__ == "__main__":
    # Test the security logger
    print("Testing Security Logger...")

    logger = SecurityLogger(log_file='test_security.log')

    # Test 1: Failed login
    print("\n1. Logging Failed Login:")
    logger.log_failed_login('test@example.com', '192.168.1.1', 'invalid_password')
    print("  ✅ Failed login logged")

    # Test 2: Successful login
    print("\n2. Logging Successful Login:")
    logger.log_successful_login('user123', 'test@example.com', '192.168.1.1')
    print("  ✅ Successful login logged")

    # Test 3: CSRF failure
    print("\n3. Logging CSRF Failure:")
    logger.log_csrf_failure('login_form', 'user123', 'token_mismatch')
    print("  ✅ CSRF failure logged")

    # Test 4: Rate limit
    print("\n4. Logging Rate Limit:")
    logger.log_rate_limit('user123', 'search', 5)
    print("  ✅ Rate limit logged")

    # Test 5: Malicious input
    print("\n5. Logging Malicious Input (XSS):")
    logger.log_malicious_input('xss', 'attacker@example.com', ['<script>alert("xss")</script>'], 'critical')
    print("  ✅ XSS attempt logged")

    # Test 6: Alert threshold (simulate multiple failed logins)
    print("\n6. Testing Alert Threshold (5 failed logins):")
    for i in range(6):
        logger.log_failed_login('repeat@example.com', '192.168.1.1', 'brute_force')
    print("  ✅ Alert should have triggered above")

    # Test 7: Event summary
    print("\n7. Event Summary:")
    summary = logger.get_event_summary()
    for event_type, count in summary.items():
        print(f"  {event_type}: {count}")

    # Test 8: Parse log file
    print("\n8. Parsing Log File (last 5 entries):")
    entries = logger.parse_log_file(limit=5)
    for entry in entries:
        print(f"  [{entry['timestamp']}] {entry['event_type']} - {entry['user_id']}")

    # Cleanup
    import os
    if os.path.exists('test_security.log'):
        os.remove('test_security.log')

    print("\n✅ Security logger tests complete!")
