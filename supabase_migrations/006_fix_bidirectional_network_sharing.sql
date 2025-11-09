-- Fix Bidirectional Network Sharing
-- Run this in Supabase SQL Editor
--
-- PROBLEM:
-- The old schema only had ONE network_sharing_enabled field, but connections
-- need TWO separate sharing preferences (one for each user).
--
-- When User A requests → User B, then User B accepts:
-- - User A's original sharing choice gets overwritten by User B's choice
-- - This breaks network sharing because only one user's preference is stored
--
-- SOLUTION:
-- Add two new fields to track both users' sharing preferences separately:
-- - requester_shares_network: Does user_id want to share their network?
-- - accepter_shares_network: Does connected_user_id want to share their network?

-- 1. Add new columns for bidirectional sharing
ALTER TABLE user_connections
ADD COLUMN IF NOT EXISTS requester_shares_network BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS accepter_shares_network BOOLEAN DEFAULT TRUE;

-- 2. Migrate existing data
-- For existing connections, we'll assume both users wanted to share
-- (since the old field defaulted to TRUE)
UPDATE user_connections
SET
    requester_shares_network = COALESCE(network_sharing_enabled, TRUE),
    accepter_shares_network = COALESCE(network_sharing_enabled, TRUE)
WHERE requester_shares_network IS NULL OR accepter_shares_network IS NULL;

-- 3. Add comments for clarity
COMMENT ON COLUMN user_connections.requester_shares_network IS 'Does the requester (user_id) share their network with accepter?';
COMMENT ON COLUMN user_connections.accepter_shares_network IS 'Does the accepter (connected_user_id) share their network with requester?';
COMMENT ON COLUMN user_connections.network_sharing_enabled IS 'DEPRECATED: Use requester_shares_network and accepter_shares_network instead';

-- 4. Verification query (uncomment to test)
-- SELECT
--     id,
--     user_id,
--     connected_user_id,
--     status,
--     network_sharing_enabled as old_field,
--     requester_shares_network,
--     accepter_shares_network
-- FROM user_connections
-- LIMIT 10;
