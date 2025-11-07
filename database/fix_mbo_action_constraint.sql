-- Fix mbo_data action constraint to allow new event types
-- Date: 2025-11-06
-- Issue: CHECK constraint only allows ADD/MODIFY/DELETE/EXECUTE
-- Solution: Drop old constraint and add new one with all event types

-- Drop the old constraint
ALTER TABLE mbo_data DROP CONSTRAINT IF EXISTS mbo_data_action_check;

-- Add new constraint with all event types
ALTER TABLE mbo_data ADD CONSTRAINT mbo_data_action_check 
    CHECK (action IN ('ADD', 'MODIFY', 'UPDATE', 'DELETE', 'EXECUTE', 'TRADE', 'DEPTH'));

-- Verify the constraint
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'mbo_data'::regclass 
AND conname = 'mbo_data_action_check';
