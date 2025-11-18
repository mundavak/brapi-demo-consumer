-- Create VWAP tracking table for Judas swing detection and daily bias
-- 9:30 AM VWAP = Session anchor for detecting Judas swings (fake moves before true direction)
-- Daily VWAP = True directional bias indicator

CREATE TABLE IF NOT EXISTS vwap_levels (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    vwap_930am NUMERIC(12, 4),  -- 9:30 AM session VWAP for Judas swing detection
    vwap_daily NUMERIC(12, 4),  -- Daily VWAP for true bias detection
    session_id TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Primary key: unique per timestamp, symbol, and timeframe
    PRIMARY KEY (timestamp, symbol, timeframe)
);

-- Create hypertable for time-series optimization
SELECT create_hypertable('vwap_levels', 'timestamp', if_not_exists => TRUE);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_vwap_symbol_time ON vwap_levels (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_vwap_timeframe ON vwap_levels (timeframe, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_vwap_session ON vwap_levels (session_id) WHERE session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_vwap_daily ON vwap_levels (symbol, timeframe, timestamp DESC) WHERE vwap_daily IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_vwap_930am ON vwap_levels (symbol, timeframe, timestamp DESC) WHERE vwap_930am IS NOT NULL;

-- Comments for documentation
COMMENT ON TABLE vwap_levels IS 'VWAP tracking for Judas swing detection and daily bias analysis';
COMMENT ON COLUMN vwap_levels.vwap_930am IS '9:30 AM session VWAP - used to detect Judas swing (false moves before true direction)';
COMMENT ON COLUMN vwap_levels.vwap_daily IS 'Daily VWAP - indicates true directional bias of the trading day';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON vwap_levels TO postgres;

-- Display table info
\d vwap_levels
