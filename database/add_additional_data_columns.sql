-- Add additional_data JSONB column to all event tables to capture ALL BrAPI fields
-- This ensures we never lose any data provided by Bookmap addons

-- 1. Add additional_data to stops_icebergs table
ALTER TABLE IF EXISTS stops_icebergs
ADD COLUMN IF NOT EXISTS additional_data JSONB;

COMMENT ON COLUMN stops_icebergs.additional_data IS 'Complete JSON dump of all BrAPI event fields not captured in dedicated columns';

CREATE INDEX IF NOT EXISTS idx_stops_icebergs_additional_data_gin 
ON stops_icebergs USING GIN (additional_data);

-- 2. Add additional_data to absorption_events table
ALTER TABLE IF EXISTS absorption_events
ADD COLUMN IF NOT EXISTS additional_data JSONB;

COMMENT ON COLUMN absorption_events.additional_data IS 'Complete JSON dump of all BrAPI event fields not captured in dedicated columns';

CREATE INDEX IF NOT EXISTS idx_absorption_additional_data_gin 
ON absorption_events USING GIN (additional_data);

-- 3. Add additional_data to mbo_data table
ALTER TABLE IF EXISTS mbo_data
ADD COLUMN IF NOT EXISTS additional_data JSONB;

COMMENT ON COLUMN mbo_data.additional_data IS 'Complete JSON dump of all MBO event fields not captured in dedicated columns';

CREATE INDEX IF NOT EXISTS idx_mbo_additional_data_gin 
ON mbo_data USING GIN (additional_data);

-- 4. Add additional_data to ohlc_candles table
ALTER TABLE IF EXISTS ohlc_candles
ADD COLUMN IF NOT EXISTS additional_data JSONB;

COMMENT ON COLUMN ohlc_candles.additional_data IS 'Complete JSON dump of all OHLC event fields not captured in dedicated columns';

CREATE INDEX IF NOT EXISTS idx_ohlc_additional_data_gin 
ON ohlc_candles USING GIN (additional_data);

-- Verify additions
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'public'
  AND column_name = 'additional_data'
ORDER BY table_name;

COMMENT ON INDEX idx_stops_icebergs_additional_data_gin IS 'GIN index for fast JSONB queries on stops_icebergs additional_data';
COMMENT ON INDEX idx_absorption_additional_data_gin IS 'GIN index for fast JSONB queries on absorption_events additional_data';
COMMENT ON INDEX idx_mbo_additional_data_gin IS 'GIN index for fast JSONB queries on mbo_data additional_data';
COMMENT ON INDEX idx_ohlc_additional_data_gin IS 'GIN index for fast JSONB queries on ohlc_candles additional_data';

-- Example queries to use additional_data:

-- Find all icebergs with specific field value
-- SELECT * FROM stops_icebergs WHERE additional_data->>'orderId' = '12345';

-- Find all events with a specific nested field
-- SELECT * FROM stops_icebergs WHERE additional_data->'details'->>'level' = 'high';

-- Check which unique field names are captured (discover what data we're getting)
-- SELECT DISTINCT jsonb_object_keys(additional_data) FROM stops_icebergs LIMIT 100;
