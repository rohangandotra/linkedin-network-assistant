"""
6th Degree AI Security Services Module

Provides comprehensive security features:
- Rate limiting to prevent abuse and control costs
- Input validation and sanitization (XSS, SQL injection, prompt injection)
- CSRF protection for all forms
- Security event logging and monitoring
"""

from .rate_limiter import (
    RateLimiter,
    get_rate_limiter,
    check_rate_limit,
    get_remaining_attempts
)

from .input_validator import (
    InputValidator,
    sanitize_html,
    validate_email,
    validate_search_query,
    sanitize_csv_data
)

from .csrf import (
    CSRFProtection,
    get_csrf_protection,
    generate_csrf_token,
    validate_csrf_token,
    validate_csrf_token_detailed,
    cleanup_csrf_tokens
)

from .security_logger import (
    SecurityLogger,
    get_security_logger,
    log_security_event,
    log_failed_login,
    log_successful_login,
    log_csrf_failure,
    log_rate_limit,
    log_malicious_input
)

__all__ = [
    # Rate Limiter
    'RateLimiter',
    'get_rate_limiter',
    'check_rate_limit',
    'get_remaining_attempts',

    # Input Validator
    'InputValidator',
    'sanitize_html',
    'validate_email',
    'validate_search_query',
    'sanitize_csv_data',

    # CSRF Protection
    'CSRFProtection',
    'get_csrf_protection',
    'generate_csrf_token',
    'validate_csrf_token',
    'validate_csrf_token_detailed',
    'cleanup_csrf_tokens',

    # Security Logger
    'SecurityLogger',
    'get_security_logger',
    'log_security_event',
    'log_failed_login',
    'log_successful_login',
    'log_csrf_failure',
    'log_rate_limit',
    'log_malicious_input',
]
