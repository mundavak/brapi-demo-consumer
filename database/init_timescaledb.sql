-- TimescaleDB Initialization Script for Trading Data Architecture
-- Database: trading_data
-- Author: AI-Assisted Development
-- Date: 2024
-- Purpose: Initialize all tables, hypertables, and indexes for hot/cold storage

-- ============================================
-- DATABASE SETUP
-- ============================================

-- Connect to postgres to create database (run this separately first)
-- CREATE DATABASE trading_data;
-- \c trading_data
-- CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ============================================
-- TABLE: mbo_data (Market By Order)
-- ============================================

CREATE TABLE IF NOT EXISTS mbo_data (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    order_id BIGINT,
    side VARCHAR(4) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    price DOUBLE PRECISION NOT NULL,
    size BIGINT NOT NULL,
    order_type VARCHAR(20),
    action VARCHAR(10) NOT NULL CHECK (action IN ('ADD', 'MODIFY', 'DELETE', 'EXECUTE')),
    session_id VARCHAR(100) NOT NULL,
    cbdr_window VARCHAR(20),
    metadata JSONB,
    PRIMARY KEY (timestamp, symbol, order_id)
);

-- Convert to hypertable with 1 day chunks
SELECT create_hypertable('mbo_data', 'timestamp', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_mbo_symbol_time ON mbo_data (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_mbo_session ON mbo_data (session_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_mbo_cbdr ON mbo_data (symbol, cbdr_window, timestamp DESC) WHERE cbdr_window IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_mbo_price ON mbo_data (symbol, price, timestamp DESC);

-- Enable compression (compress chunks older than 7 days)
ALTER TABLE mbo_data SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,session_id',
    timescaledb.compress_orderby = 'timestamp DESC'
);

SELECT add_compression_policy('mbo_data', INTERVAL '7 days', if_not_exists => TRUE);

-- Retention policy (drop chunks older than 90 days)
SELECT add_retention_policy('mbo_data', INTERVAL '90 days', if_not_exists => TRUE);

-- ============================================
-- TABLE: ohlc_candles (OHLC Data)
-- ============================================

CREATE TABLE IF NOT EXISTS ohlc_candles (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL CHECK (timeframe IN ('1m', '5m', '15m', '1h', '4h', '1d')),
    open DOUBLE PRECISION NOT NULL,
    high DOUBLE PRECISION NOT NULL,
    low DOUBLE PRECISION NOT NULL,
    close DOUBLE PRECISION NOT NULL,
    volume BIGINT NOT NULL DEFAULT 0,
    trade_count INT NOT NULL DEFAULT 0,
    vwap DOUBLE PRECISION,
    session_id VARCHAR(100) NOT NULL,
    cbdr_window VARCHAR(20),
    metadata JSONB,
    PRIMARY KEY (timestamp, symbol, timeframe)
);

-- Convert to hypertable with 7 day chunks
SELECT create_hypertable('ohlc_candles', 'timestamp',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ohlc_symbol_tf_time ON ohlc_candles (symbol, timeframe, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ohlc_session ON ohlc_candles (session_id, timeframe, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_ohlc_cbdr ON ohlc_candles (symbol, cbdr_window, timestamp DESC) WHERE cbdr_window IS NOT NULL;

-- Compression
ALTER TABLE ohlc_candles SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,timeframe',
    timescaledb.compress_orderby = 'timestamp DESC'
);

SELECT add_compression_policy('ohlc_candles', INTERVAL '30 days', if_not_exists => TRUE);

-- Retention (keep OHLC longer - 180 days)
SELECT add_retention_policy('ohlc_candles', INTERVAL '180 days', if_not_exists => TRUE);

-- ============================================
-- TABLE: stops_icebergs (Iceberg & Stop Detection)
-- ============================================

CREATE TABLE IF NOT EXISTS stops_icebergs (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('ICEBERG', 'STOP_CLUSTER')),
    side VARCHAR(4) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    price DOUBLE PRECISION NOT NULL,
    detected_size BIGINT NOT NULL,
    estimated_total_size BIGINT,
    fill_count INT NOT NULL DEFAULT 0,
    confidence_score DOUBLE PRECISION NOT NULL CHECK (confidence_score BETWEEN 0 AND 1),
    duration_ms BIGINT,
    session_id VARCHAR(100) NOT NULL,
    cbdr_window VARCHAR(20),
    metadata JSONB,
    PRIMARY KEY (timestamp, symbol, event_type, price)
);

-- Convert to hypertable
SELECT create_hypertable('stops_icebergs', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_stops_symbol_time ON stops_icebergs (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_stops_event_type ON stops_icebergs (event_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_stops_confidence ON stops_icebergs (symbol, confidence_score DESC, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_stops_cbdr ON stops_icebergs (symbol, cbdr_window, timestamp DESC) WHERE cbdr_window IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_stops_session ON stops_icebergs (session_id, timestamp DESC);

-- Compression
ALTER TABLE stops_icebergs SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,event_type',
    timescaledb.compress_orderby = 'timestamp DESC, confidence_score DESC'
);

SELECT add_compression_policy('stops_icebergs', INTERVAL '7 days', if_not_exists => TRUE);

-- Retention
SELECT add_retention_policy('stops_icebergs', INTERVAL '90 days', if_not_exists => TRUE);

-- ============================================
-- TABLE: absorption_events (Absorption & Sweeps)
-- ============================================

CREATE TABLE IF NOT EXISTS absorption_events (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('ABSORPTION', 'SWEEP')),
    side VARCHAR(4) NOT NULL CHECK (side IN ('BUY', 'SELL')),
    price DOUBLE PRECISION NOT NULL,
    absorbed_volume BIGINT NOT NULL DEFAULT 0,
    aggressor_volume BIGINT NOT NULL,
    liquidity_removed BIGINT NOT NULL DEFAULT 0,
    absorption_ratio DOUBLE PRECISION CHECK (absorption_ratio BETWEEN 0 AND 1),
    imbalance_ratio DOUBLE PRECISION CHECK (imbalance_ratio BETWEEN 0 AND 1),
    session_id VARCHAR(100) NOT NULL,
    cbdr_window VARCHAR(20),
    is_in_cbdr BOOLEAN NOT NULL DEFAULT FALSE,
    significance_score DOUBLE PRECISION NOT NULL CHECK (significance_score BETWEEN 0 AND 1),
    metadata JSONB,
    PRIMARY KEY (timestamp, symbol, event_type, price)
);

-- Convert to hypertable
SELECT create_hypertable('absorption_events', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_absorption_symbol_time ON absorption_events (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_absorption_event_type ON absorption_events (event_type, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_absorption_significance ON absorption_events (symbol, significance_score DESC, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_absorption_cbdr ON absorption_events (symbol, cbdr_window, timestamp DESC) WHERE cbdr_window IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_absorption_session ON absorption_events (session_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_absorption_in_cbdr ON absorption_events (symbol, is_in_cbdr, timestamp DESC) WHERE is_in_cbdr = TRUE;

-- Compression
ALTER TABLE absorption_events SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol,event_type,cbdr_window',
    timescaledb.compress_orderby = 'timestamp DESC, significance_score DESC'
);

SELECT add_compression_policy('absorption_events', INTERVAL '7 days', if_not_exists => TRUE);

-- Retention
SELECT add_retention_policy('absorption_events', INTERVAL '90 days', if_not_exists => TRUE);

-- ============================================
-- TABLE: trading_sessions (Session Tracking)
-- ============================================

CREATE TABLE IF NOT EXISTS trading_sessions (
    session_id VARCHAR(100) PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    session_type VARCHAR(20) NOT NULL CHECK (session_type IN ('ASIAN', 'LONDON', 'NEWYORK', 'AFTER_HOURS')),
    start_time TIMESTAMPTZ NOT NULL,
    end_time TIMESTAMPTZ,
    total_volume BIGINT NOT NULL DEFAULT 0,
    total_trades INT NOT NULL DEFAULT 0,
    avg_price DOUBLE PRECISION,
    high_price DOUBLE PRECISION,
    low_price DOUBLE PRECISION,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'CLOSED', 'SUSPENDED')),
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_sessions_symbol_time ON trading_sessions (symbol, start_time DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_type ON trading_sessions (session_type, start_time DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON trading_sessions (status, updated_at DESC);

-- ============================================
-- TABLE: market_bias (Market Direction Tracking)
-- ============================================

CREATE TABLE IF NOT EXISTS market_bias (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    direction VARCHAR(10) NOT NULL CHECK (direction IN ('BULLISH', 'BEARISH', 'NEUTRAL')),
    confidence DOUBLE PRECISION NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    supporting_factors TEXT,
    cbdr_window VARCHAR(20),
    session_id VARCHAR(100),
    buy_volume BIGINT NOT NULL DEFAULT 0,
    sell_volume BIGINT NOT NULL DEFAULT 0,
    absorption_count INT NOT NULL DEFAULT 0,
    iceberg_count INT NOT NULL DEFAULT 0,
    PRIMARY KEY (timestamp, symbol)
);

-- Convert to hypertable
SELECT create_hypertable('market_bias', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_bias_symbol_time ON market_bias (symbol, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_bias_direction ON market_bias (symbol, direction, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_bias_confidence ON market_bias (symbol, confidence DESC, timestamp DESC);

-- Compression
ALTER TABLE market_bias SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'timestamp DESC'
);

SELECT add_compression_policy('market_bias', INTERVAL '14 days', if_not_exists => TRUE);

-- Retention
SELECT add_retention_policy('market_bias', INTERVAL '90 days', if_not_exists => TRUE);

-- ============================================
-- CONTINUOUS AGGREGATES (HTF Analysis)
-- ============================================

-- Hourly OHLC aggregate for faster HTF queries
CREATE MATERIALIZED VIEW IF NOT EXISTS ohlc_1h_aggregate
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', timestamp) AS hour,
    symbol,
    first(open, timestamp) AS open,
    max(high) AS high,
    min(low) AS low,
    last(close, timestamp) AS close,
    sum(volume) AS volume,
    sum(trade_count) AS trade_count,
    avg(vwap) AS avg_vwap
FROM ohlc_candles
WHERE timeframe = '1m'
GROUP BY hour, symbol;

-- Refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('ohlc_1h_aggregate',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Daily statistics aggregate
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_statistics
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', timestamp) AS day,
    symbol,
    cbdr_window,
    count(*) AS event_count,
    count(*) FILTER (WHERE event_type = 'ABSORPTION') AS absorption_count,
    count(*) FILTER (WHERE event_type = 'SWEEP') AS sweep_count,
    avg(significance_score) AS avg_significance,
    max(significance_score) AS max_significance,
    sum(absorbed_volume) AS total_absorbed_volume,
    sum(aggressor_volume) AS total_aggressor_volume
FROM absorption_events
GROUP BY day, symbol, cbdr_window;

-- Refresh policy
SELECT add_continuous_aggregate_policy('daily_statistics',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- ============================================
-- HELPER VIEWS
-- ============================================

-- View: Recent significant events across all types
CREATE OR REPLACE VIEW recent_significant_events AS
SELECT
    'ABSORPTION' AS category,
    timestamp,
    symbol,
    event_type,
    side,
    price,
    absorbed_volume AS volume,
    significance_score AS score,
    cbdr_window
FROM absorption_events
WHERE timestamp > NOW() - INTERVAL '24 hours'
    AND significance_score > 0.7

UNION ALL

SELECT
    'ICEBERG' AS category,
    timestamp,
    symbol,
    event_type,
    side,
    price,
    detected_size AS volume,
    confidence_score AS score,
    cbdr_window
FROM stops_icebergs
WHERE timestamp > NOW() - INTERVAL '24 hours'
    AND confidence_score > 0.7
    AND event_type = 'ICEBERG'

ORDER BY timestamp DESC, score DESC
LIMIT 100;

-- View: CBDR window performance
CREATE OR REPLACE VIEW cbdr_performance AS
SELECT
    symbol,
    cbdr_window,
    COUNT(*) AS total_events,
    AVG(significance_score) AS avg_significance,
    SUM(absorbed_volume) AS total_volume,
    COUNT(DISTINCT session_id) AS sessions
FROM absorption_events
WHERE cbdr_window IS NOT NULL
    AND timestamp > NOW() - INTERVAL '7 days'
GROUP BY symbol, cbdr_window
ORDER BY avg_significance DESC;

-- ============================================
-- FUNCTIONS & PROCEDURES
-- ============================================

-- Function: Get trading bias for a symbol over last N minutes
CREATE OR REPLACE FUNCTION get_recent_bias(
    p_symbol VARCHAR(20),
    p_lookback_minutes INT DEFAULT 60
)
RETURNS TABLE (
    direction VARCHAR(10),
    confidence DOUBLE PRECISION,
    buy_volume BIGINT,
    sell_volume BIGINT,
    event_count INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        CASE
            WHEN SUM(CASE WHEN side = 'BUY' THEN absorbed_volume ELSE 0 END) > 
                 SUM(CASE WHEN side = 'SELL' THEN absorbed_volume ELSE 0 END) * 1.2 THEN 'BULLISH'::VARCHAR(10)
            WHEN SUM(CASE WHEN side = 'SELL' THEN absorbed_volume ELSE 0 END) > 
                 SUM(CASE WHEN side = 'BUY' THEN absorbed_volume ELSE 0 END) * 1.2 THEN 'BEARISH'::VARCHAR(10)
            ELSE 'NEUTRAL'::VARCHAR(10)
        END AS direction,
        AVG(significance_score) AS confidence,
        SUM(CASE WHEN side = 'BUY' THEN absorbed_volume ELSE 0 END) AS buy_volume,
        SUM(CASE WHEN side = 'SELL' THEN absorbed_volume ELSE 0 END) AS sell_volume,
        COUNT(*)::INT AS event_count
    FROM absorption_events
    WHERE symbol = p_symbol
        AND timestamp > NOW() - (p_lookback_minutes || ' minutes')::INTERVAL;
END;
$$ LANGUAGE plpgsql;

-- Function: Get HTF candles for analysis
CREATE OR REPLACE FUNCTION get_htf_candles(
    p_symbol VARCHAR(20),
    p_timeframe VARCHAR(10),
    p_count INT DEFAULT 100
)
RETURNS TABLE (
    timestamp TIMESTAMPTZ,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    vwap DOUBLE PRECISION
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.timestamp,
        c.open,
        c.high,
        c.low,
        c.close,
        c.volume,
        c.vwap
    FROM ohlc_candles c
    WHERE c.symbol = p_symbol
        AND c.timeframe = p_timeframe
    ORDER BY c.timestamp DESC
    LIMIT p_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- GRANTS (Adjust as needed for your security model)
-- ============================================

-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO trading_app;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO trading_app;

-- ============================================
-- COMPLETION MESSAGE
-- ============================================

DO $$
BEGIN
    RAISE NOTICE '========================================';
    RAISE NOTICE 'TimescaleDB Trading Data Schema Initialized';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Tables created: 6 (mbo_data, ohlc_candles, stops_icebergs, absorption_events, trading_sessions, market_bias)';
    RAISE NOTICE 'Hypertables configured: 5 with compression and retention policies';
    RAISE NOTICE 'Continuous aggregates: 2 (ohlc_1h_aggregate, daily_statistics)';
    RAISE NOTICE 'Views created: 2 (recent_significant_events, cbdr_performance)';
    RAISE NOTICE 'Functions created: 2 (get_recent_bias, get_htf_candles)';
    RAISE NOTICE '========================================';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '1. Verify compression policies: SELECT * FROM timescaledb_information.jobs;';
    RAISE NOTICE '2. Monitor chunk status: SELECT * FROM timescaledb_information.chunks;';
    RAISE NOTICE '3. Check continuous aggregates: SELECT * FROM timescaledb_information.continuous_aggregates;';
    RAISE NOTICE '========================================';
END $$;
