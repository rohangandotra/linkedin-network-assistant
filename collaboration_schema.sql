-- ============================================
-- COLLABORATION FEATURE DATABASE SCHEMA
-- Run this in Supabase SQL Editor
-- ============================================

-- 1. Add organization field to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS organization VARCHAR(255);

-- 2. Create user_connections table
CREATE TABLE IF NOT EXISTS user_connections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    connected_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined')),
    network_sharing_enabled BOOLEAN DEFAULT TRUE, -- Can this connection see my network?
    requested_at TIMESTAMP DEFAULT NOW(),
    accepted_at TIMESTAMP,
    declined_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, connected_user_id), -- Prevent duplicate connections
    CHECK (user_id != connected_user_id) -- Prevent self-connections
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_connections_user_id ON user_connections(user_id);
CREATE INDEX IF NOT EXISTS idx_user_connections_connected_user_id ON user_connections(connected_user_id);
CREATE INDEX IF NOT EXISTS idx_user_connections_status ON user_connections(status);

-- 3. Create intro_requests table
CREATE TABLE IF NOT EXISTS intro_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    requester_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, -- Person asking for intro
    connector_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE, -- Person making the intro
    target_contact_id UUID REFERENCES contacts(id) ON DELETE SET NULL, -- Person they want to meet

    -- Store contact details in case contact is deleted
    target_name VARCHAR(255) NOT NULL,
    target_company VARCHAR(255),
    target_position VARCHAR(255),
    target_email VARCHAR(255),

    -- Request details
    request_message TEXT NOT NULL, -- Why they want the intro
    context_for_connector TEXT, -- Additional context for the person making intro
    response_message TEXT, -- Connector's response if declined

    -- Status tracking
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined', 'completed', 'cancelled')),
    intro_email_sent BOOLEAN DEFAULT FALSE,

    -- Cancellation tracking
    cancelled_reason TEXT,
    cancelled_at TIMESTAMP,

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    responded_at TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_intro_requests_requester_id ON intro_requests(requester_id);
CREATE INDEX IF NOT EXISTS idx_intro_requests_connector_id ON intro_requests(connector_id);
CREATE INDEX IF NOT EXISTS idx_intro_requests_status ON intro_requests(status);
CREATE INDEX IF NOT EXISTS idx_intro_requests_target_contact_id ON intro_requests(target_contact_id);

-- 4. Create function to auto-cancel intro requests when contact is deleted
CREATE OR REPLACE FUNCTION cancel_intro_requests_on_contact_delete()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE intro_requests
    SET
        status = 'cancelled',
        cancelled_reason = 'Contact deleted by owner',
        cancelled_at = NOW(),
        updated_at = NOW()
    WHERE
        target_contact_id = OLD.id
        AND status = 'pending';

    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
DROP TRIGGER IF EXISTS trigger_cancel_intro_requests_on_contact_delete ON contacts;
CREATE TRIGGER trigger_cancel_intro_requests_on_contact_delete
    BEFORE DELETE ON contacts
    FOR EACH ROW
    EXECUTE FUNCTION cancel_intro_requests_on_contact_delete();

-- 5. Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for updated_at
DROP TRIGGER IF EXISTS update_user_connections_updated_at ON user_connections;
CREATE TRIGGER update_user_connections_updated_at
    BEFORE UPDATE ON user_connections
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_intro_requests_updated_at ON intro_requests;
CREATE TRIGGER update_intro_requests_updated_at
    BEFORE UPDATE ON intro_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 6. Enable Row Level Security (RLS) - IMPORTANT FOR SECURITY
ALTER TABLE user_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE intro_requests ENABLE ROW LEVEL SECURITY;

-- RLS Policies for user_connections
-- Users can see connections where they are either user_id or connected_user_id
CREATE POLICY "Users can view their own connections"
    ON user_connections FOR SELECT
    USING (auth.uid()::text = user_id::text OR auth.uid()::text = connected_user_id::text);

-- Users can insert connections where they are the user_id
CREATE POLICY "Users can create connections"
    ON user_connections FOR INSERT
    WITH CHECK (auth.uid()::text = user_id::text);

-- Users can update connections where they are involved
CREATE POLICY "Users can update their connections"
    ON user_connections FOR UPDATE
    USING (auth.uid()::text = user_id::text OR auth.uid()::text = connected_user_id::text);

-- RLS Policies for intro_requests
-- Users can see requests where they are requester or connector
CREATE POLICY "Users can view their intro requests"
    ON intro_requests FOR SELECT
    USING (auth.uid()::text = requester_id::text OR auth.uid()::text = connector_id::text);

-- Users can create requests where they are the requester
CREATE POLICY "Users can create intro requests"
    ON intro_requests FOR INSERT
    WITH CHECK (auth.uid()::text = requester_id::text);

-- Users can update requests where they are involved
CREATE POLICY "Users can update intro requests"
    ON intro_requests FOR UPDATE
    USING (auth.uid()::text = requester_id::text OR auth.uid()::text = connector_id::text);

-- ============================================
-- VERIFICATION QUERIES
-- Run these to verify tables were created
-- ============================================

-- Check user_connections table
-- SELECT * FROM user_connections LIMIT 5;

-- Check intro_requests table
-- SELECT * FROM intro_requests LIMIT 5;

-- Check if organization column was added to users
-- SELECT id, email, full_name, organization FROM users LIMIT 5;
