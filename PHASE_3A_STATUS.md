# Phase 3A: Security & Authentication - STATUS

## ✅ COMPLETED

### 1. Database Schema Created
- **File:** `security_schema.sql`
- **Tables Created:**
  - `password_reset_tokens` - For password reset links
  - `login_attempts` - Track login attempts for rate limiting
  - `api_rate_limits` - Rate limit API calls
  - `security_events` - Audit log of security events
- **Fields Added:**
  - `email_verified` - Track email verification status
  - `verification_token` - Token for email verification

### 2. Security Backend Module Built
- **File:** `security.py`
- **Functions Created:**
  - `request_password_reset()` - Generate & send reset email
  - `verify_reset_token()` - Validate reset tokens
  - `reset_password_with_token()` - Reset password
  - `send_verification_email()` - Send email verification
  - `verify_email_token()` - Verify email
  - `check_login_rate_limit()` - Prevent brute force
  - `log_login_attempt()` - Track login attempts
  - `log_security_event()` - Audit logging
  - `check_password_strength()` - Validate passwords
  - `sanitize_input()` - Prevent XSS
  - `send_email()` - Email sending via SMTP

---

## 🚧 TODO - UI Integration

### 3. Update Login Page (app.py)
**Add to login form:**
```python
# After password input, before submit button:
forgot_password = st.form_submit_button("Forgot Password?", type="secondary")

# After form:
if forgot_password:
    st.session_state['show_forgot_password'] = True
    st.rerun()

# In submit handler, add rate limiting:
rate_limit = security.check_login_rate_limit(email)
if not rate_limit['allowed']:
    st.error(rate_limit['message'])
    return

# After login attempt:
security.log_login_attempt(email, result['success'])

# Check email verification:
if result['success']:
    user = result['user']
    # Check if email verified (get from DB)
    if not user.get('email_verified'):
        st.warning("Please verify your email to continue. Check your inbox.")
        # Show resend verification button
        return
```

### 4. Add Password Reset Page
**Create function:**
```python
def show_password_reset_page():
    st.markdown("### Reset Your Password")

    with st.form("reset_request_form"):
        email = st.text_input("Enter your email")
        submit = st.form_submit_button("Send Reset Link")

        if submit and email:
            result = security.request_password_reset(email)
            st.success(result['message'])
```

### 5. Add Password Reset Form (URL Token)
**Check URL parameters:**
```python
# At top of main():
query_params = st.query_params
if 'reset_token' in query_params:
    show_password_reset_form(query_params['reset_token'])
    return

def show_password_reset_form(token):
    st.markdown("### Set New Password")

    with st.form("reset_form"):
        new_password = st.text_input("New Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Reset Password")

        if submit:
            if new_password != confirm:
                st.error("Passwords don't match")
            else:
                result = security.reset_password_with_token(token, new_password)
                if result['success']:
                    st.success(result['message'])
                    # Redirect to login
```

### 6. Update Registration
**Add password strength check:**
```python
# Before creating account:
strength = security.check_password_strength(password)
if not strength['strong']:
    st.error(strength['message'])
    return

# After successful registration:
security.send_verification_email(
    user_id=result['user']['id'],
    email=email,
    full_name=full_name
)
st.info("✉️ Verification email sent! Please check your inbox.")
```

### 7. Add Email Verification Handler
**Check URL parameters:**
```python
if 'verify_email' in query_params:
    result = security.verify_email_token(query_params['verify_email'])
    if result['success']:
        st.success(result['message'])
    else:
        st.error(result['message'])
```

---

## ⚙️ CONFIGURATION NEEDED

### Environment Variables (.env and Streamlit Secrets)
Add these to both `.env` and `.streamlit/secrets.toml`:

```bash
# Email Configuration (Gmail Example)
SMTP_SERVER="smtp.gmail.com"
SMTP_PORT=587
SMTP_USERNAME="your-email@gmail.com"
SMTP_PASSWORD="your-app-specific-password"
FROM_EMAIL="noreply@your-domain.com"

# App URL
APP_URL="https://linkedin-network-assistant.streamlit.app"
```

**Gmail Setup:**
1. Go to Google Account → Security
2. Enable 2-Factor Authentication
3. Create "App Password" for "Mail"
4. Use that password (not your regular password)

---

## 🔒 SECURITY AUDIT CHECKLIST

### SQL Injection Protection
- ✅ Using Supabase client (parameterized queries)
- ✅ No raw SQL in application code
- ✅ RLS policies prevent unauthorized access

### XSS Protection
- ✅ `sanitize_input()` function created
- ⚠️ Need to apply to all user inputs
- ⚠️ Streamlit auto-escapes most HTML (verify)

### Authentication Security
- ✅ Passwords hashed with bcrypt
- ✅ Rate limiting on login attempts
- ✅ Session tokens (Streamlit handles this)
- ✅ Password reset tokens expire (15 min)
- ✅ Email verification tokens expire (7 days)

### RLS Policy Review
**Run in Supabase:**
```sql
-- Check all RLS policies
SELECT tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
```

**Verify:**
- ✅ users table - users can only see own data
- ✅ contacts table - users can only see own contacts
- ✅ user_connections - users see connections they're part of
- ✅ intro_requests - users see requests they're involved in
- ✅ password_reset_tokens - service role only
- ✅ login_attempts - users see own attempts
- ✅ security_events - users see own events

### Session Security
- ⚠️ Add session timeout (currently indefinite)
- ⚠️ Add "Remember me" option
- ⚠️ Force re-auth for sensitive actions

### Rate Limiting Status
- ✅ Login attempts: 5 per 15 minutes
- ⚠️ Connection requests: Not implemented yet
- ⚠️ Search queries: Not implemented yet
- ⚠️ Intro requests: Not implemented yet

---

## 📋 DEPLOYMENT STEPS

1. **Run SQL Schema in Supabase:**
   ```bash
   # Open Supabase SQL Editor
   # Paste contents of security_schema.sql
   # Click Run
   ```

2. **Add Environment Variables:**
   - Update `.env` file locally
   - Update Streamlit Cloud secrets

3. **Complete UI Integration:**
   - Follow TODO section above
   - Test each flow locally

4. **Deploy:**
   ```bash
   git add .
   git commit -m "Add Phase 3A: Security & Authentication"
   git push origin main
   ```

5. **Test on Production:**
   - Test password reset flow
   - Test email verification
   - Test rate limiting
   - Verify RLS policies

---

## 🎯 NEXT STEPS

**Option A: Complete Phase 3A Now**
- Finish UI integration (2-3 hours)
- Configure email sending
- Test all flows
- Deploy

**Option B: Deploy Core Security, Finish UI Later**
- Deploy database schema now
- Deploy security.py module now
- Add UI features incrementally

**Option C: Move to Phase 3B (Search Improvements)**
- Come back to email verification later
- Focus on search relevance
- Password reset can wait

**Recommendation:** Option A - Complete Phase 3A now. Security is critical and the foundation is built. Just needs UI integration.

---

## 📞 NEED HELP?

If deploying, run:
```bash
python3 -m py_compile security.py  # Check syntax
```

If errors, check:
- Circular imports (security.py imports auth.py)
- Missing dependencies (smtplib is built-in)
- Supabase client connection
