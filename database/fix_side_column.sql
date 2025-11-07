-- Fix side column size to accommodate all values
-- Date: 2025-11-06
-- Issue: side VARCHAR(4) too small for "UNKNOWN" (7 chars)

-- Alter column to VARCHAR(10)
ALTER TABLE mbo_data ALTER COLUMN side TYPE VARCHAR(10);

-- Update CHECK constraint to allow new values
ALTER TABLE mbo_data DROP CONSTRAINT IF EXISTS mbo_data_side_check;
ALTER TABLE mbo_data ADD CONSTRAINT mbo_data_side_check 
    CHECK (side IN ('BUY', 'SELL', 'N/A'));

-- Verify
SELECT column_name, data_type, character_maximum_length 
FROM information_schema.columns 
WHERE table_name = 'mbo_data' AND column_name = 'side';
