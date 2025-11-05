# Security Audit - 6th Degree AI

**Audit Date:** October 30, 2025
**Auditor:** Security Assessment
**Scope:** Complete application security review

---

## Executive Summary

This document outlines all security vulnerabilities found and remediation steps for 6th Degree AI.

### Risk Levels
- 🔴 **CRITICAL:** Immediate data breach risk
- 🟠 **HIGH:** Significant security concern
- 🟡 **MEDIUM:** Moderate risk, should fix soon
- 🟢 **LOW:** Best practice, fix when possible

---

## 1. SQL Injection Vulnerabilities

### Status: 🟢 LOW RISK (Using Supabase client with parameterized queries)

**Good News:** You're using Supabase's Python client which automatically parameterizes queries.

**Checked Files:**
- `auth.py` - ✅ All queries use `.select()`, `.insert()`, `.update()` with proper escaping
- `security.py` - ✅ Parameterized queries throughout
- `collaboration.py` - ✅ Safe query patterns
- `user_profile.py` - ✅ Using Supabase client correctly

**Potential Issues:**
- ❌ No raw SQL found (GOOD)
- ✅ All user inputs passed through Supabase client

**Action:** ✅ NO IMMEDIATE ACTION NEEDED

---

## 2. Cross-Site Scripting (XSS)

### Status: 🟡 MEDIUM RISK

**Vulnerabilities Found:**

#### 2.1 User-Generated Content Display
**Location:** `app.py` - Contact search results, email generation, user profiles

**Issue:** User names, companies, positions from CSV are displayed without sanitization.

**Example:**
```python
# Line ~3600 - Contact card display
st.markdown(f"<h3>{name}</h3>", unsafe_allow_html=True)
# If name = "<script>alert('XSS')</script>", this executes
```

**Risk:** 🟡 MEDIUM
- Attacker uploads CSV with malicious names
- XSS triggers when other users view search results
- Could steal session tokens, redirect users

**Remediation:**
```python
import html

# Sanitize all user-generated content
def sanitize_html(text: str) -> str:
    """Escape HTML special characters"""
    if not text:
        return ""
    return html.escape(str(text))

# Use in all displays
st.markdown(f"<h3>{sanitize_html(name)}</h3>", unsafe_allow_html=True)
```

**Files to Fix:**
- `app.py` - All contact card displays (~15 locations)
- `app.py` - Search result displays
- `app.py` - Email preview/generation
- `app.py` - Profile displays

#### 2.2 Feedback Form
**Location:** `feedback.py` - User feedback storage

**Issue:** Feedback text not sanitized before storage/display

**Remediation:** Sanitize before storing in database

---

## 3. Cross-Site Request Forgery (CSRF)

### Status: 🟠 HIGH RISK

**Issue:** No CSRF protection on any forms

**Vulnerable Forms:**
1. Login form
2. Registration form
3. Password reset form
4. Feedback form
5. Profile edit form
6. Connection request form
7. Email generation form

**Attack Scenario:**
1. User logs into 6th Degree
2. Attacker tricks user to visit malicious site
3. Malicious site submits form to 6th Degree
4. Action executes with user's session

**Current Protection:** ❌ NONE

**Remediation Required:**
```python
# Add CSRF token generation
import secrets

def generate_csrf_token():
    """Generate CSRF token"""
    token = secrets.token_urlsafe(32)
    st.session_state['csrf_token'] = token
    return token

def verify_csrf_token(submitted_token):
    """Verify CSRF token"""
    stored_token = st.session_state.get('csrf_token')
    return stored_token and secrets.compare_digest(stored_token, submitted_token)

# In forms:
with st.form("login_form"):
    csrf_token = st.hidden(generate_csrf_token())
    # ... form fields ...
    if submitted:
        if not verify_csrf_token(csrf_token):
            st.error("Invalid form submission")
            return
```

**Priority:** 🟠 HIGH - Implement in Week 1

---

## 4. Rate Limiting

### Status: 🟠 HIGH RISK

**Current State:**
- ✅ Login attempts: 5 failed attempts in 15 minutes (security.py:444-460)
- ❌ Search queries: NO LIMIT
- ❌ Email generation: NO LIMIT
- ❌ API endpoints: NO LIMIT
- ❌ Connection requests: NO LIMIT
- ❌ Feedback submissions: NO LIMIT

**Attack Scenarios:**
1. **Search Spam:** Attacker makes 1000s of searches → OpenAI bill explodes
2. **Email Spam:** Generate 1000s of emails → OpenAI bill explodes
3. **Connection Spam:** Send 1000s of connection requests → Database overload
4. **Feedback Spam:** Submit 1000s of feedback → Database pollution

**Cost Impact:** Could result in $1000s in OpenAI charges

**Remediation:**
```python
# services/rate_limiter.py
from datetime import datetime, timedelta
from collections import defaultdict

class RateLimiter:
    def __init__(self):
        self.limits = {
            'search': (20, 300),  # 20 searches per 5 minutes
            'email_gen': (10, 300),  # 10 emails per 5 minutes
            'connection_request': (5, 3600),  # 5 requests per hour
            'feedback': (3, 3600),  # 3 feedback per hour
        }
        self.attempts = defaultdict(list)

    def check_limit(self, user_id: str, action: str) -> bool:
        """Check if user has exceeded rate limit"""
        if action not in self.limits:
            return True

        max_attempts, window = self.limits[action]
        now = datetime.now()
        cutoff = now - timedelta(seconds=window)

        # Clean old attempts
        key = f"{user_id}:{action}"
        self.attempts[key] = [t for t in self.attempts[key] if t > cutoff]

        # Check limit
        if len(self.attempts[key]) >= max_attempts:
            return False

        # Record attempt
        self.attempts[key].append(now)
        return True
```

**Priority:** 🟠 HIGH - Implement in Week 1

---

## 5. Authentication & Session Management

### Status: 🟡 MEDIUM RISK

**Current State:**
- ✅ Password hashing with bcrypt
- ✅ Email verification required
- ✅ Session state managed by Streamlit
- ❌ No session timeout
- ❌ No "remember me" with secure cookies
- ❌ Sessions not invalidated on password change

**Issues:**

#### 5.1 Session Timeout
**Risk:** User walks away from computer, session stays active

**Remediation:**
```python
# Add session timeout (30 minutes)
if 'last_activity' in st.session_state:
    inactive_time = datetime.now() - st.session_state['last_activity']
    if inactive_time > timedelta(minutes=30):
        st.session_state['authenticated'] = False
        st.warning("Session expired. Please log in again.")
        st.rerun()

st.session_state['last_activity'] = datetime.now()
```

#### 5.2 Password Strength
**Current:** Basic requirements (8 chars, upper, lower, digit)

**Recommended:** Add complexity scoring
```python
def check_password_strength_enhanced(password: str):
    score = 0
    issues = []

    if len(password) < 12:
        issues.append("at least 12 characters")
    else:
        score += 1

    if not any(c.isupper() for c in password):
        issues.append("one uppercase letter")
    else:
        score += 1

    if not any(c.islower() for c in password):
        issues.append("one lowercase letter")
    else:
        score += 1

    if not any(c.isdigit() for c in password):
        issues.append("one number")
    else:
        score += 1

    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        issues.append("one special character")
    else:
        score += 1

    # Check against common passwords
    common_passwords = ['password', '12345678', 'qwerty123', 'admin123']
    if password.lower() in common_passwords:
        return {'strong': False, 'message': 'Password is too common'}

    if score < 3:
        return {'strong': False, 'message': f"Password must contain {', '.join(issues)}"}

    return {'strong': True, 'message': 'Strong password'}
```

**Priority:** 🟡 MEDIUM - Implement in Week 2

---

## 6. Input Validation & Sanitization

### Status: 🟠 HIGH RISK

**Current State:**
- ❌ No systematic input validation
- ❌ CSV uploads not validated for malicious content
- ❌ Email inputs not validated (beyond regex)
- ❌ Search queries not sanitized

**Vulnerabilities:**

#### 6.1 CSV Upload Validation
**Risk:** Malicious CSV with XSS payloads

**Current:** `parse_linkedin_csv()` doesn't validate content

**Remediation:**
```python
def sanitize_csv_data(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitize all CSV data"""
    import html

    # Sanitize all string columns
    for col in df.columns:
        if df[col].dtype == 'object':  # String column
            df[col] = df[col].apply(lambda x: html.escape(str(x)) if pd.notna(x) else x)

    # Validate email format
    if 'Email Address' in df.columns:
        df = df[df['Email Address'].str.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', na=False)]

    return df
```

#### 6.2 Search Query Validation
**Risk:** Malicious queries to OpenAI

**Remediation:**
```python
def validate_search_query(query: str) -> dict:
    """Validate and sanitize search query"""
    if not query or not query.strip():
        return {'valid': False, 'message': 'Query cannot be empty'}

    if len(query) > 500:
        return {'valid': False, 'message': 'Query too long (max 500 characters)'}

    # Check for prompt injection attempts
    dangerous_patterns = [
        'ignore previous instructions',
        'disregard all',
        'system:',
        '<script>',
        'DROP TABLE',
    ]

    query_lower = query.lower()
    for pattern in dangerous_patterns:
        if pattern in query_lower:
            return {'valid': False, 'message': 'Invalid query'}

    return {'valid': True, 'query': html.escape(query.strip())}
```

**Priority:** 🟠 HIGH - Implement in Week 1

---

## 7. Security Headers

### Status: 🟠 HIGH RISK

**Current State:** ❌ No security headers

**Missing Headers:**
1. **Content-Security-Policy (CSP)** - Prevents XSS
2. **X-Frame-Options** - Prevents clickjacking
3. **X-Content-Type-Options** - Prevents MIME sniffing
4. **Strict-Transport-Security (HSTS)** - Forces HTTPS
5. **Referrer-Policy** - Controls referrer information

**Remediation:**
```python
# Add to app.py (top level)
st.markdown("""
<script>
// Add security headers via meta tags (Streamlit limitation workaround)
document.addEventListener('DOMContentLoaded', function() {
    var meta = document.createElement('meta');
    meta.httpEquiv = "Content-Security-Policy";
    meta.content = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';";
    document.getElementsByTagName('head')[0].appendChild(meta);
});
</script>
""", unsafe_allow_html=True)
```

**Note:** Streamlit Cloud limitations make this tricky. Best done during FastAPI migration.

**Priority:** 🟡 MEDIUM - Document for future migration

---

## 8. Secrets Management

### Status: 🔴 CRITICAL

**Issues Found:**

#### 8.1 Secrets in Git History
**Risk:** API keys, database URLs exposed in git history

**Check Required:**
```bash
# Search git history for secrets
git log -p | grep -i "api_key"
git log -p | grep -i "password"
git log -p | grep -i "secret"
```

**If Found:**
1. Rotate ALL secrets immediately
2. Use `git filter-repo` to remove from history
3. Force push (breaks history, but necessary)

#### 8.2 Environment Variables
**Current:** Using `.env` file (good)

**Verify:**
- [ ] `.env` in `.gitignore`
- [ ] Streamlit Secrets configured correctly
- [ ] Supabase keys are "service_role" (not "anon")
- [ ] OpenAI API key has spending limits

**Priority:** 🔴 CRITICAL - Check immediately

---

## 9. Logging & Monitoring

### Status: 🟠 HIGH RISK

**Current State:**
- ✅ Basic print statements for debugging
- ❌ No structured logging
- ❌ No error tracking (Sentry, etc.)
- ❌ No security event logging
- ❌ No alerting for suspicious activity

**Missing Visibility:**
- Failed login attempts (beyond rate limit)
- Unusual search patterns
- Large CSV uploads
- Error rates
- API costs

**Remediation:**
```python
# Add structured logging
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('security.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('6th_degree_security')

# Log security events
def log_security_event(event_type: str, user_id: str, details: dict):
    logger.warning(f"SECURITY: {event_type}", extra={
        'user_id': user_id,
        'timestamp': datetime.now().isoformat(),
        'details': details
    })

# Add Sentry for error tracking
# import sentry_sdk
# sentry_sdk.init(dsn="YOUR_DSN", traces_sample_rate=0.1)
```

**Priority:** 🟠 HIGH - Implement in Week 2

---

## 10. Dependency Vulnerabilities

### Status: 🟡 MEDIUM RISK

**Action Required:**
```bash
# Install safety
pip install safety

# Check dependencies
safety check --json

# Setup Dependabot
# Create .github/dependabot.yml
```

**Dependabot Config:**
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
```

**Priority:** 🟡 MEDIUM - Setup in Week 2

---

## Implementation Priority

### Week 1 (Days 1-7): Critical Fixes
1. 🔴 **Day 1:** Check secrets in git history, rotate if needed
2. 🟠 **Day 2-3:** Add rate limiting (search, email, connections)
3. 🟠 **Day 3-4:** Add CSRF protection to all forms
4. 🟠 **Day 5:** Add input validation and sanitization
5. 🟠 **Day 6-7:** Add XSS protection (HTML escaping)

### Week 2 (Days 8-14): Infrastructure
1. 🟠 **Day 8-9:** Add structured logging and monitoring
2. 🟡 **Day 10:** Enhance password strength requirements
3. 🟡 **Day 11:** Add session timeout
4. 🟡 **Day 12:** Setup Dependabot
5. 🟡 **Day 13:** Run automated security scan
6. 🟡 **Day 14:** Document security practices

---

## Testing Checklist

After implementation, test:

### Authentication
- [ ] Cannot login with wrong password
- [ ] Rate limiting works after 5 failed attempts
- [ ] Session expires after 30 minutes
- [ ] Password reset works
- [ ] Email verification required

### Input Validation
- [ ] XSS payloads in CSV are escaped
- [ ] Malicious search queries rejected
- [ ] Form validation catches invalid data

### Rate Limiting
- [ ] Cannot make 21 searches in 5 minutes
- [ ] Cannot generate 11 emails in 5 minutes
- [ ] Cannot send 6 connection requests in 1 hour

### CSRF Protection
- [ ] Forms work with valid CSRF token
- [ ] Forms fail with invalid/missing token
- [ ] Token regenerates on each form

---

## Post-Audit Actions

1. **Document Changes:** Update README with security practices
2. **Train Team:** Share security guidelines
3. **Schedule Reviews:** Quarterly security audits
4. **Monitor:** Set up alerting for security events
5. **Update:** Keep dependencies patched

---

## Compliance Considerations

### GDPR (If serving EU users):
- [ ] Privacy policy
- [ ] User data export
- [ ] Right to deletion
- [ ] Consent management

### CCPA (If serving CA users):
- [ ] Privacy policy
- [ ] Data sharing disclosure
- [ ] Opt-out mechanism

**Note:** Consult lawyer for compliance requirements.

---

## Resources

- **OWASP Top 10:** https://owasp.org/www-project-top-ten/
- **Security Headers:** https://securityheaders.com/
- **Snyk:** https://snyk.io/
- **Sentry:** https://sentry.io/

---

## Sign-Off

This audit identifies vulnerabilities but does not guarantee complete security. Ongoing monitoring and updates are required.

**Next Steps:** Begin Week 1 implementation following priority order above.
