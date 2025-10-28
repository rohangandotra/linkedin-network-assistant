-- Feedback Table for User Feedback and Bug Reports
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Feedback content
    feedback_text TEXT NOT NULL,
    feedback_type VARCHAR(50) DEFAULT 'general', -- bug, feature, general, praise
    page_context VARCHAR(200), -- Which page/section user was on

    -- User info
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    user_email VARCHAR(255), -- In case anonymous user provides email

    -- Metadata (browser, screen size, etc.)
    metadata JSONB DEFAULT '{}',

    -- Status tracking
    status VARCHAR(20) DEFAULT 'new', -- new, reviewed, resolved

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_feedback_status ON feedback(status);
CREATE INDEX IF NOT EXISTS idx_feedback_user_id ON feedback(user_id);
CREATE INDEX IF NOT EXISTS idx_feedback_created_at ON feedback(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_type ON feedback(feedback_type);

-- Enable Row Level Security
ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;

-- Policy: Anyone can submit feedback (insert)
CREATE POLICY "Anyone can submit feedback"
    ON feedback
    FOR INSERT
    TO authenticated, anon
    WITH CHECK (true);

-- Policy: Users can view their own feedback
CREATE POLICY "Users can view own feedback"
    ON feedback
    FOR SELECT
    TO authenticated
    USING (user_id = auth.uid());

-- Policy: Admin can view all feedback (you'll need to set is_admin flag)
-- For now, you can manually query as service role

-- Add comment
COMMENT ON TABLE feedback IS 'User feedback and bug reports from 6th Degree AI application';
