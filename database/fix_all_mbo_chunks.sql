-- Fix all mbo_data chunks to allow new action types
-- Date: 2025-11-06
-- Issue: Hypertable chunks have old CHECK constraint, causing silent failures

-- Step 1: Drop constraint from all chunks (using CASCADE)
DO $$ 
DECLARE
    chunk_table TEXT;
BEGIN
    FOR chunk_table IN 
        SELECT format('%I.%I', chunk_schema, chunk_name) AS full_name
        FROM timescaledb_information.chunks
        WHERE hypertable_name = 'mbo_data'
    LOOP
        BEGIN
            EXECUTE format('ALTER TABLE %s DROP CONSTRAINT IF EXISTS mbo_data_action_check CASCADE', chunk_table);
            RAISE NOTICE 'Dropped constraint from %', chunk_table;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Skipped % (error: %)', chunk_table, SQLERRM;
        END;
    END LOOP;
END $$;

-- Step 2: Drop from parent table
ALTER TABLE mbo_data DROP CONSTRAINT IF EXISTS mbo_data_action_check CASCADE;

-- Step 3: Add new constraint to parent (will be inherited by new chunks)
ALTER TABLE mbo_data ADD CONSTRAINT mbo_data_action_check 
    CHECK (action IN ('ADD', 'MODIFY', 'UPDATE', 'DELETE', 'EXECUTE', 'TRADE', 'DEPTH'));

-- Step 4: Verify (should show new constraint)
SELECT conname, pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conrelid = 'mbo_data'::regclass 
AND conname = 'mbo_data_action_check';

-- Step 5: Test insert (should succeed)
DO $$
BEGIN
    INSERT INTO mbo_data (timestamp, symbol, order_id, side, price, size, order_type, action, session_id, data_type, cbdr_window, additional_data)
    VALUES 
        (NOW(), 'TEST', 1, 'BUY', 100.0, 1, 'LIMIT', 'TRADE', 'TEST_SESSION', 'TRADE', NULL, '{}'),
        (NOW(), 'TEST', 2, 'SELL', 100.0, 1, 'LIMIT', 'DEPTH', 'TEST_SESSION', 'DEPTH', NULL, '{}'),
        (NOW(), 'TEST', 3, 'BUY', 100.0, 1, 'LIMIT', 'UPDATE', 'TEST_SESSION', 'MBO', NULL, '{}');
    
    DELETE FROM mbo_data WHERE symbol = 'TEST';
    RAISE NOTICE 'Test successful: All action types work!';
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'Test failed: %', SQLERRM;
    ROLLBACK;
END $$;
