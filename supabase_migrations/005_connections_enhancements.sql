-- Connections Enhancements for 6th Degree AI
-- Run this in Supabase SQL Editor

-- Add request_message column to user_connections table
-- Allows users to include a personal message with connection requests
ALTER TABLE user_connections
ADD COLUMN IF NOT EXISTS request_message TEXT;

-- Add comment
COMMENT ON COLUMN user_connections.request_message IS 'Optional personal message included with connection request';
