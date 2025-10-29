-- User Profiles Table
-- Stores user professional information and preferences for personalized search

CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE NOT NULL,

    -- Professional Info (Questions 1-5, mandatory)
    current_role VARCHAR(255) NOT NULL,
    current_company VARCHAR(255),
    industry VARCHAR(100) NOT NULL,
    company_stage VARCHAR(50),
    location_city VARCHAR(255) NOT NULL,
    location_country VARCHAR(100),

    -- Goals & Interests (Questions 6-7, optional, stored as JSON arrays)
    goals JSONB DEFAULT '[]'::jsonb,  -- ['fundraising', 'hiring', 'partnerships', 'career', 'learning', 'other']
    interests JSONB DEFAULT '[]'::jsonb,  -- ['ai', 'web3', 'saas', 'climate', etc.]
    seeking_connections JSONB DEFAULT '[]'::jsonb,  -- ['investors', 'engineers', 'designers', 'executives', etc.]

    -- Privacy Settings (per-field visibility)
    privacy_settings JSONB DEFAULT '{
        "current_role": true,
        "current_company": true,
        "industry": true,
        "company_stage": true,
        "location_city": true,
        "location_country": true,
        "goals": false,
        "interests": true,
        "seeking_connections": true
    }'::jsonb,

    -- Profile Metadata
    profile_completed BOOLEAN DEFAULT TRUE,  -- Set to true when user completes onboarding
    profile_completed_at TIMESTAMP DEFAULT NOW(),

    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_industry ON user_profiles(industry);
CREATE INDEX idx_user_profiles_location_city ON user_profiles(location_city);

-- Enable Row Level Security
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

-- RLS Policies

-- Users can view their own profile
CREATE POLICY "Users can view own profile"
    ON user_profiles
    FOR SELECT
    USING (auth.uid() = user_id);

-- Users can insert their own profile
CREATE POLICY "Users can insert own profile"
    ON user_profiles
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- Users can update their own profile
CREATE POLICY "Users can update own profile"
    ON user_profiles
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- Users can delete their own profile
CREATE POLICY "Users can delete own profile"
    ON user_profiles
    FOR DELETE
    USING (auth.uid() = user_id);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_user_profiles_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
CREATE TRIGGER user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_user_profiles_updated_at();

-- Comments for documentation
COMMENT ON TABLE user_profiles IS 'Stores user professional information and preferences for personalized search and connections';
COMMENT ON COLUMN user_profiles.goals IS 'User goals as JSON array: fundraising, hiring, partnerships, career, learning, other';
COMMENT ON COLUMN user_profiles.interests IS 'User interests/topics as JSON array: ai, web3, saas, climate, etc.';
COMMENT ON COLUMN user_profiles.seeking_connections IS 'Types of people user wants to connect with: investors, engineers, designers, executives, etc.';
COMMENT ON COLUMN user_profiles.privacy_settings IS 'Per-field visibility settings as JSON object with boolean values';
