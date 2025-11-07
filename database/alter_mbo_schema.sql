-- Migration: Alter mbo_data schema for Java MBO consumer
-- Date: 2025-11-06
-- Purpose: Change order_id to VARCHAR and size to DOUBLE PRECISION

-- Step 1: Drop the primary key constraint (includes order_id)
ALTER TABLE mbo_data DROP CONSTRAINT IF EXISTS mbo_data_pkey;

-- Step 2: Change order_id from BIGINT to VARCHAR(100)
ALTER TABLE mbo_data ALTER COLUMN order_id TYPE VARCHAR(100) USING order_id::VARCHAR;

-- Step 3: Change size from BIGINT to DOUBLE PRECISION
ALTER TABLE mbo_data ALTER COLUMN size TYPE DOUBLE PRECISION;

-- Step 4: Recreate primary key
ALTER TABLE mbo_data ADD PRIMARY KEY (timestamp, symbol, order_id);

-- Step 5: Update data_type for existing records (in batches to avoid decompression limit)
-- This will be done by the Java consumer for new records only
-- Existing records will remain with default 'MBO' value

-- Verify changes
SELECT 
    column_name, 
    data_type, 
    column_default,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'mbo_data' 
AND column_name IN ('data_type', 'order_id', 'size')
ORDER BY column_name;

-- Show sample of data
SELECT 
    data_type,
    COUNT(*) as count,
    MIN(timestamp) as first_record,
    MAX(timestamp) as last_record
FROM mbo_data
GROUP BY data_type;
