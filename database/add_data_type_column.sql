-- Migration: Add data_type column and update mbo_data schema
-- Date: 2025-11-06
-- Purpose: Split MBO, Trade, and Depth data with data_type marker

-- Add data_type column to mbo_data table
ALTER TABLE mbo_data ADD COLUMN IF NOT EXISTS data_type VARCHAR(20) DEFAULT 'MBO';

-- Add index on data_type for efficient filtering
CREATE INDEX IF NOT EXISTS idx_mbo_data_type ON mbo_data(data_type);

-- Add composite index for common queries
CREATE INDEX IF NOT EXISTS idx_mbo_data_symbol_type_timestamp 
ON mbo_data(symbol, data_type, timestamp DESC);

-- Update existing records to have data_type = 'MBO'
UPDATE mbo_data SET data_type = 'MBO' WHERE data_type IS NULL;

-- Add comment to data_type column
COMMENT ON COLUMN mbo_data.data_type IS 'Type of market data: MBO (order-level), TRADE (execution), or DEPTH (aggregated level)';

-- Note: order_id should be VARCHAR (not BIGINT) to support string IDs like "TRADE_12345" and "DEPTH_67890"
-- Note: size should be DOUBLE PRECISION (not BIGINT) to support fractional sizes after division by size_multiplier
-- If needed, run these alterations (requires data migration):
-- ALTER TABLE mbo_data ALTER COLUMN order_id TYPE VARCHAR(100);
-- ALTER TABLE mbo_data ALTER COLUMN size TYPE DOUBLE PRECISION;

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
