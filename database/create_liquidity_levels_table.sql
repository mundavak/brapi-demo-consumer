--
-- Liquidity Levels Table for Liquidity Marker Indicator
-- Stores significant support/resistance levels identified by Bookmap's Liquidity Markers
--

CREATE TABLE IF NOT EXISTS liquidity_levels (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    session_id VARCHAR(100),
    price DOUBLE PRECISION NOT NULL,
    level_type VARCHAR(20) NOT NULL,  -- SUPPORT, RESISTANCE, UNKNOWN
    strength_score DOUBLE PRECISION DEFAULT 0.0,
    volume_at_level BIGINT DEFAULT 0,
    touches_count INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL,
    last_updated_at TIMESTAMPTZ NOT NULL,
    metadata JSONB,
    PRIMARY KEY (timestamp, symbol, price)
);

-- Convert to hypertable
SELECT create_hypertable('liquidity_levels', 'timestamp', if_not_exists => TRUE);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_liquidity_symbol_time 
    ON liquidity_levels (symbol, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_liquidity_level_type 
    ON liquidity_levels (symbol, level_type, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_liquidity_strength 
    ON liquidity_levels (symbol, strength_score DESC, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_liquidity_session 
    ON liquidity_levels (session_id, timestamp DESC);

-- Index for price range queries
CREATE INDEX IF NOT EXISTS idx_liquidity_price_range 
    ON liquidity_levels (symbol, price, timestamp DESC);

-- JSONB index for metadata queries
CREATE INDEX IF NOT EXISTS idx_liquidity_metadata 
    ON liquidity_levels USING GIN (metadata);

-- Check constraint for level_type
ALTER TABLE liquidity_levels 
    DROP CONSTRAINT IF EXISTS check_level_type;

ALTER TABLE liquidity_levels 
    ADD CONSTRAINT check_level_type 
    CHECK (level_type IN ('SUPPORT', 'RESISTANCE', 'UNKNOWN'));

-- Add column comments
COMMENT ON COLUMN liquidity_levels.timestamp IS 'Event timestamp in EST/EDT timezone';
COMMENT ON COLUMN liquidity_levels.symbol IS 'Trading symbol (e.g., MNQZ5.CME@RITHMIC)';
COMMENT ON COLUMN liquidity_levels.session_id IS 'Trading session identifier';
COMMENT ON COLUMN liquidity_levels.price IS 'Price level (converted to index points for futures)';
COMMENT ON COLUMN liquidity_levels.level_type IS 'Type of liquidity level: SUPPORT, RESISTANCE, or UNKNOWN';
COMMENT ON COLUMN liquidity_levels.strength_score IS 'Strength score 0.0-1.0 based on volume and touches';
COMMENT ON COLUMN liquidity_levels.volume_at_level IS 'Total volume resting at this level';
COMMENT ON COLUMN liquidity_levels.touches_count IS 'Number of times price tested this level';
COMMENT ON COLUMN liquidity_levels.created_at IS 'When the level was first detected';
COMMENT ON COLUMN liquidity_levels.last_updated_at IS 'Last time the level was updated';
COMMENT ON COLUMN liquidity_levels.metadata IS 'Additional Liquidity Marker event data as JSON';

-- Table comment
COMMENT ON TABLE liquidity_levels IS 'Liquidity levels from Bookmap Liquidity Markers indicator - significant support/resistance zones';
