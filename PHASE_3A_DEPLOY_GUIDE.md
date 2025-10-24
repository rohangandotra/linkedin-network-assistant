# Phase 3A Deployment Guide
## Security & Authentication Features

---

## 🎯 What's Been Built

### ✅ Features Implemented:
1. **Password Reset Flow**
   - "Forgot Password?" link on login page
   - Email with secure reset link (15-minute expiry)
   - Set new password form

2. **Email Verification**
   - Verification email sent on registration
   - Users must verify before full access
   - Resend verification option

3. **Rate Limiting**
   - 5 login attempts per 15 minutes
   - Prevents brute force attacks
   - Shows remaining attempts

4. **Password Strength Checking**
   - Requires 8+ characters
   - Must have uppercase, lowercase, number
   - Enforced on registration and password reset

5. **Security Audit Logging**
   - All security events logged
   - Track failed logins, password resets, etc.
   - Viewable in Supabase dashboard

---

## 📋 DEPLOYMENT STEPS

### Step 1: Run SQL Schema in Supabase

1. Open Supabase Dashboard: https://supabase.com/dashboard
2. Select your project
3. Go to **SQL Editor**
4. Click **New Query**
5. Copy the ENTIRE contents of `security_schema.sql`
6. Paste and click **Run**
7. You should see: **"Success. No rows returned"**

**Verify tables created:**
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('password_reset_tokens', 'login_attempts', 'api_rate_limits', 'security_events')
ORDER BY table_name;
```

Should return 4 tables.

---

### Step 2: Configure Email Sending (REQUIRED)

**Option A: Gmail (Recommended for Testing)**

1. Go to your Google Account → Security
2. Enable **2-Factor Authentication**
3. Go to **App Passwords**: https://myaccount.google.com/apppasswords
4. Create app password for "Mail"
5. Copy the 16-character password

**Add to `.env` file:**
```bash
# Email Configuration
SMTP_SERVER="smtp.gmail.com"
SMTP_PORT=587
SMTP_USERNAME="your-email@gmail.com"
SMTP_PASSWORD="your-16-char-app-password"
FROM_EMAIL="noreply@your-domain.com"

# App URL
APP_URL="https://linkedin-network-assistant.streamlit.app"
```

**Add to `.streamlit/secrets.toml` (for local testing):**
```toml
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "your-email@gmail.com"
SMTP_PASSWORD = "your-16-char-app-password"
FROM_EMAIL = "noreply@your-domain.com"
APP_URL = "https://linkedin-network-assistant.streamlit.app"
```

**Add to Streamlit Cloud Secrets:**
1. Go to https://share.streamlit.io/
2. Click on your app
3. Go to **Settings** → **Secrets**
4. Add the same variables (in TOML format)

**Option B: SendGrid (Recommended for Production)**

1. Sign up at https://sendgrid.com/ (free tier: 100 emails/day)
2. Create API key
3. Verify sender identity (your email or domain)

```bash
# SendGrid Configuration
SMTP_SERVER="smtp.sendgrid.net"
SMTP_PORT=587
SMTP_USERNAME="apikey"
SMTP_PASSWORD="your-sendgrid-api-key"
FROM_EMAIL="noreply@your-verified-domain.com"
APP_URL="https://linkedin-network-assistant.streamlit.app"
```

---

### Step 3: Test Locally (Optional but Recommended)

```bash
# Make sure email config is in .env
python3 -m streamlit run app.py
```

**Test these flows:**
1. **Registration:** Create account → should receive verification email
2. **Email Verification:** Click link in email → should verify successfully
3. **Login:** Try logging in without verification → should prompt to verify
4. **Password Reset:** Click "Forgot Password?" → enter email → receive reset link
5. **Set New Password:** Click reset link → set new password → log in
6. **Rate Limiting:** Try 6 wrong passwords → should be blocked

---

### Step 4: Deploy to Production

```bash
# Commit all changes
git add security.py security_schema.sql app.py PHASE_3A_DEPLOY_GUIDE.md PHASE_3A_STATUS.md

git commit -m "Add Phase 3A: Security & Authentication

✅ Password reset flow with email
✅ Email verification on signup
✅ Rate limiting (5 attempts/15min)
✅ Password strength requirements
✅ Security event logging
✅ Brute force protection

Security improvements:
- RLS policies protect all new tables
- Tokens expire (15min for reset, 7 days for verification)
- All security events logged for audit
- Password requirements: 8+ chars, uppercase, lowercase, number

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin main
```

---

### Step 5: Verify Deployment

1. Wait 2-3 minutes for Streamlit Cloud to deploy
2. Visit: https://linkedin-network-assistant.streamlit.app/
3. Test all flows:
   - Create account
   - Check email for verification
   - Click verification link
   - Log in
   - Test password reset

---

## 🔒 Security Checklist

### Database Security
- ✅ RLS policies on all tables
- ✅ Password reset tokens expire in 15 minutes
- ✅ Email verification tokens expire in 7 days
- ✅ Tokens invalidated after use
- ✅ All sensitive data logged in security_events table

### Application Security
- ✅ Passwords hashed with bcrypt
- ✅ Rate limiting prevents brute force
- ✅ Password strength requirements enforced
- ✅ Email verification required for full access
- ✅ XSS protection (input sanitization)
- ✅ SQL injection protected (Supabase client)

### Audit Logging
All events logged in `security_events` table:
- `password_reset_requested`
- `password_reset_completed`
- `verification_email_sent`
- `email_verified`
- `failed_login`

**View logs in Supabase:**
```sql
SELECT * FROM security_events
WHERE created_at > NOW() - INTERVAL '7 days'
ORDER BY created_at DESC;
```

---

## 🐛 Troubleshooting

### "Email not sending"
**Check:**
1. SMTP credentials correct in secrets
2. Gmail: App password (not regular password)
3. Gmail: 2FA enabled
4. SendGrid: Sender verified
5. Check Streamlit logs for errors

**Temporary workaround:**
- Emails won't send without SMTP config
- App will print email to console instead
- Users can still sign up (email_verified defaults to FALSE)

### "Rate limit not working"
**Check:**
1. `login_attempts` table exists
2. RLS policies created
3. Check Supabase logs

### "Password reset link expired"
- Tokens expire in 15 minutes
- Request new reset link

### "Email verification required but never received email"
**Admin workaround:**
```sql
-- Manually verify a user in Supabase
UPDATE users
SET email_verified = TRUE, is_verified = TRUE
WHERE email = 'user@example.com';
```

---

## 📊 Monitoring

### Check Security Events
```sql
-- Failed logins in last 24 hours
SELECT email, COUNT(*) as attempts, MAX(created_at) as last_attempt
FROM security_events
WHERE event_type = 'failed_login'
AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY email
ORDER BY attempts DESC;
```

### Check Rate Limiting
```sql
-- Users hitting rate limits
SELECT email, COUNT(*) as failed_attempts
FROM login_attempts
WHERE success = FALSE
AND attempted_at > NOW() - INTERVAL '1 hour'
GROUP BY email
HAVING COUNT(*) >= 5
ORDER BY failed_attempts DESC;
```

### Cleanup Old Data
```sql
-- Run this weekly to clean up old tokens/logs
SELECT cleanup_expired_tokens();
```

---

## 🎯 What's Next (Future Enhancements)

**Not included in Phase 3A (can add later):**
- Multi-factor authentication (2FA)
- Social login (Google, LinkedIn OAuth)
- Remember me checkbox
- Session timeout (auto-logout)
- IP-based blocking
- CAPTCHA after failed attempts
- Email notifications for security events
- Password change history
- Account deletion

---

## ✅ Deployment Checklist

- [ ] Run `security_schema.sql` in Supabase
- [ ] Verify tables created
- [ ] Configure Gmail app password OR SendGrid
- [ ] Add SMTP secrets to `.env`
- [ ] Add SMTP secrets to Streamlit Cloud
- [ ] Test locally (registration, login, reset)
- [ ] Commit and push to GitHub
- [ ] Wait for deployment
- [ ] Test on production
- [ ] Create test account and verify email works
- [ ] Test password reset flow
- [ ] Verify rate limiting works

---

## 📞 Support

**If deployment fails:**
1. Check Streamlit logs for errors
2. Verify all SQL ran successfully
3. Check email credentials
4. Test locally first

**Common Issues:**
- Circular import: Make sure `security.py` imports `auth`, not vice versa
- Missing tables: Re-run SQL schema
- Email not sending: Check SMTP credentials
