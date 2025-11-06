-- Migration: Add iceberg_subtype column to stops_icebergs table
-- Purpose: Capture Bookmap iceberg sub-types (TRADE, EXECUTION, DETECTION, CANCELLATION)
-- Date: November 6, 2025

-- ============================================
-- ADD iceberg_subtype COLUMN
-- ============================================

-- Add column (nullable for backward compatibility with existing data)
ALTER TABLE stops_icebergs 
ADD COLUMN IF NOT EXISTS iceberg_subtype VARCHAR(20);

-- Add comment
COMMENT ON COLUMN stops_icebergs.iceberg_subtype IS 
'Bookmap iceberg sub-type: TRADE, EXECUTION, DETECTION, CANCELLATION, MOVEMENT. NULL for STOP events or legacy ICEBERG events.';

-- ============================================
-- UPDATE INDEXES
-- ============================================

-- Add index for filtering by subtype (useful for analysis)
CREATE INDEX IF NOT EXISTS idx_stops_iceberg_subtype 
ON stops_icebergs (symbol, event_type, iceberg_subtype, timestamp DESC) 
WHERE event_type = 'ICEBERG';

-- ============================================
-- VALIDATION
-- ============================================

-- Verify column was added
SELECT column_name, data_type, is_nullable, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'stops_icebergs' 
  AND column_name = 'iceberg_subtype';

-- Check existing data (should all be NULL before Java consumer update)
SELECT 
    COUNT(*) as total_icebergs,
    COUNT(iceberg_subtype) as with_subtype,
    COUNT(*) - COUNT(iceberg_subtype) as without_subtype
FROM stops_icebergs
WHERE event_type = 'ICEBERG';

-- ============================================
-- SAMPLE QUERIES WITH NEW FIELD
-- ============================================

-- Count by iceberg sub-type (after data starts coming in)
/*
SELECT 
    iceberg_subtype,
    COUNT(*) as count,
    COUNT(DISTINCT symbol) as symbols,
    AVG(detected_size) as avg_detected,
    AVG(estimated_total_size) as avg_estimated
FROM stops_icebergs
WHERE event_type = 'ICEBERG'
  AND iceberg_subtype IS NOT NULL
GROUP BY iceberg_subtype
ORDER BY count DESC;
*/

-- High-confidence TRADE icebergs only
/*
SELECT 
    timestamp,
    symbol,
    side,
    price,
    detected_size,
    estimated_total_size,
    iceberg_subtype
FROM stops_icebergs
WHERE event_type = 'ICEBERG'
  AND iceberg_subtype = 'TRADE'
  AND confidence_score > 0.7
ORDER BY timestamp DESC
LIMIT 100;
*/
