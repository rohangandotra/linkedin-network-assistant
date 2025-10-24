-- ============================================
-- PHASE 3A: SECURITY & AUTHENTICATION SCHEMA
-- Run this in Supabase SQL Editor
-- ============================================

-- 1. Add email verification fields to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token_expires TIMESTAMP;

-- Update existing is_verified to email_verified for consistency
UPDATE users SET email_verified = is_verified WHERE email_verified IS NULL;

-- 2. Create password_reset_tokens table
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) NOT NULL UNIQUE,
    expires_at TIMESTAMP NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    used_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at);

-- 3. Create login_attempts table (for rate limiting)
CREATE TABLE IF NOT EXISTS login_attempts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) NOT NULL,
    ip_address VARCHAR(45),  -- IPv6 max length
    success BOOLEAN NOT NULL,
    attempted_at TIMESTAMP DEFAULT NOW(),
    user_agent TEXT
);

CREATE INDEX IF NOT EXISTS idx_login_attempts_email ON login_attempts(email);
CREATE INDEX IF NOT EXISTS idx_login_attempts_ip ON login_attempts(ip_address);
CREATE INDEX IF NOT EXISTS idx_login_attempts_attempted_at ON login_attempts(attempted_at);

-- 4. Create api_rate_limits table (for API rate limiting)
CREATE TABLE IF NOT EXISTS api_rate_limits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    ip_address VARCHAR(45),
    endpoint VARCHAR(255) NOT NULL,
    request_count INTEGER DEFAULT 1,
    window_start TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, endpoint, window_start),
    UNIQUE(ip_address, endpoint, window_start)
);

CREATE INDEX IF NOT EXISTS idx_api_rate_limits_user_id ON api_rate_limits(user_id);
CREATE INDEX IF NOT EXISTS idx_api_rate_limits_ip ON api_rate_limits(ip_address);
CREATE INDEX IF NOT EXISTS idx_api_rate_limits_window_start ON api_rate_limits(window_start);

-- 5. Function to clean up expired tokens (run daily)
CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS void AS $$
BEGIN
    -- Delete expired password reset tokens
    DELETE FROM password_reset_tokens
    WHERE expires_at < NOW();

    -- Delete old login attempts (keep last 30 days)
    DELETE FROM login_attempts
    WHERE attempted_at < NOW() - INTERVAL '30 days';

    -- Delete old rate limit records (keep last 24 hours)
    DELETE FROM api_rate_limits
    WHERE window_start < NOW() - INTERVAL '24 hours';
END;
$$ LANGUAGE plpgsql;

-- 6. Enable Row Level Security
ALTER TABLE password_reset_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE login_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_rate_limits ENABLE ROW LEVEL SECURITY;

-- RLS Policies for password_reset_tokens
-- Only allow service role to access (no user access needed)
CREATE POLICY "Service role only for password_reset_tokens"
    ON password_reset_tokens
    USING (false);  -- Users cannot read

-- RLS Policies for login_attempts
-- Users can only see their own login attempts
CREATE POLICY "Users can view their own login attempts"
    ON login_attempts FOR SELECT
    USING (email IN (SELECT email FROM users WHERE id::text = auth.uid()::text));

-- RLS Policies for api_rate_limits
-- Users can only see their own rate limits
CREATE POLICY "Users can view their own rate limits"
    ON api_rate_limits FOR SELECT
    USING (user_id::text = auth.uid()::text);

-- 7. Add security event logging table
CREATE TABLE IF NOT EXISTS security_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    email VARCHAR(255),
    event_type VARCHAR(100) NOT NULL,  -- 'password_reset_requested', 'email_verified', 'failed_login', etc.
    ip_address VARCHAR(45),
    user_agent TEXT,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_security_events_user_id ON security_events(user_id);
CREATE INDEX IF NOT EXISTS idx_security_events_email ON security_events(email);
CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type);
CREATE INDEX IF NOT EXISTS idx_security_events_created_at ON security_events(created_at);

ALTER TABLE security_events ENABLE ROW LEVEL SECURITY;

-- Users can only see their own security events
CREATE POLICY "Users can view their own security events"
    ON security_events FOR SELECT
    USING (user_id::text = auth.uid()::text OR email IN (SELECT email FROM users WHERE id::text = auth.uid()::text));

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Check password_reset_tokens table
-- SELECT * FROM password_reset_tokens LIMIT 5;

-- Check login_attempts table
-- SELECT * FROM login_attempts LIMIT 5;

-- Check api_rate_limits table
-- SELECT * FROM api_rate_limits LIMIT 5;

-- Check security_events table
-- SELECT * FROM security_events LIMIT 5;

-- Check email_verified field was added
-- SELECT id, email, email_verified, verification_token FROM users LIMIT 5;
