-- =====================================================
-- Quarterly Theory Database Schema
-- Purpose: Support AMDX/XAMD cycle tracking and phase analysis
-- Created: 2025-10-29
-- =====================================================

-- =====================================================
-- Table 1: quarterly_cycles
-- Purpose: Track cycle state across multiple timeframes
-- =====================================================
CREATE TABLE IF NOT EXISTS quarterly_cycles (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    timeframe VARCHAR(20) NOT NULL, -- 'weekly', 'daily', 'session', 'hourly'
    cycle_type VARCHAR(10) NOT NULL CHECK (cycle_type IN ('AMDX', 'XAMD', 'UNKNOWN')),
    current_quarter VARCHAR(5) NOT NULL CHECK (current_quarter IN ('Q1', 'Q2', 'Q3', 'Q4')),
    quarter_phase VARCHAR(20) NOT NULL CHECK (quarter_phase IN (
        'ACCUMULATION', 
        'MANIPULATION', 
        'DISTRIBUTION', 
        'CONTINUATION', 
        'REVERSAL',
        'TRANSITION'
    )),
    confidence_score DECIMAL(5,2) CHECK (confidence_score >= 0 AND confidence_score <= 100),
    cycle_start TIMESTAMPTZ,
    quarter_start TIMESTAMPTZ,
    estimated_quarter_end TIMESTAMPTZ,
    supporting_evidence JSONB DEFAULT '{}'::jsonb,
    
    -- Analysis metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_timeframe_timestamp UNIQUE (timeframe, timestamp)
);

-- Convert to hypertable for time-series optimization
SELECT create_hypertable('quarterly_cycles', 'timestamp', 
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX idx_qc_timestamp_desc ON quarterly_cycles (timestamp DESC);
CREATE INDEX idx_qc_timeframe ON quarterly_cycles (timeframe);
CREATE INDEX idx_qc_cycle_type ON quarterly_cycles (cycle_type);
CREATE INDEX idx_qc_quarter ON quarterly_cycles (current_quarter);
CREATE INDEX idx_qc_phase ON quarterly_cycles (quarter_phase);
CREATE INDEX idx_qc_confidence ON quarterly_cycles (confidence_score DESC);
CREATE INDEX idx_qc_evidence ON quarterly_cycles USING GIN (supporting_evidence);

-- Compression policy (keep recent data uncompressed for fast access)
SELECT add_compression_policy('quarterly_cycles', INTERVAL '7 days');

-- Retention policies
SELECT add_retention_policy('quarterly_cycles', INTERVAL '6 months');

-- =====================================================
-- Table 2: phase_transitions
-- Purpose: Log when phases change for backtesting
-- =====================================================
CREATE TABLE IF NOT EXISTS phase_transitions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    timeframe VARCHAR(20) NOT NULL,
    
    -- Transition details
    from_quarter VARCHAR(5),
    to_quarter VARCHAR(5),
    from_phase VARCHAR(20),
    to_phase VARCHAR(20),
    
    -- Trigger information
    transition_trigger VARCHAR(50) NOT NULL, -- 'DISPLACEMENT_DETECTED', 'LIQUIDITY_SWEEP', 'TIME_WINDOW_END', etc.
    price_at_transition DECIMAL(10,2),
    
    -- Supporting data from consumers
    supporting_data JSONB DEFAULT '{}'::jsonb, -- absorption, stops, icebergs
    
    -- Validation
    was_predicted BOOLEAN DEFAULT FALSE,
    prediction_accuracy DECIMAL(5,2), -- If predicted, how accurate (0-100)
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable
SELECT create_hypertable('phase_transitions', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX idx_pt_timestamp_desc ON phase_transitions (timestamp DESC);
CREATE INDEX idx_pt_timeframe ON phase_transitions (timeframe);
CREATE INDEX idx_pt_trigger ON phase_transitions (transition_trigger);
CREATE INDEX idx_pt_quarters ON phase_transitions (from_quarter, to_quarter);
CREATE INDEX idx_pt_phases ON phase_transitions (from_phase, to_phase);
CREATE INDEX idx_pt_supporting ON phase_transitions USING GIN (supporting_data);

-- Retention policy
SELECT add_retention_policy('phase_transitions', INTERVAL '6 months');

-- =====================================================
-- Table 3: htf_bias
-- Purpose: Store higher timeframe bias analysis
-- =====================================================
CREATE TABLE IF NOT EXISTS htf_bias (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    timeframe VARCHAR(20) NOT NULL, -- 'weekly', 'daily'
    
    -- Bias determination
    bias VARCHAR(10) NOT NULL CHECK (bias IN ('BULLISH', 'BEARISH', 'NEUTRAL')),
    confidence_score DECIMAL(5,2) CHECK (confidence_score >= 0 AND confidence_score <= 100),
    
    -- Key levels
    key_levels JSONB DEFAULT '{}'::jsonb, -- premium/discount zones, IRL/ERL
    
    -- Market structure analysis
    market_structure JSONB DEFAULT '{}'::jsonb, -- displacement, manipulation, one-sided analysis
    
    -- Explanation
    determination_method TEXT,
    
    -- Validity
    valid_until TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable
SELECT create_hypertable('htf_bias', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX idx_htf_timestamp_desc ON htf_bias (timestamp DESC);
CREATE INDEX idx_htf_timeframe ON htf_bias (timeframe);
CREATE INDEX idx_htf_bias ON htf_bias (bias);
CREATE INDEX idx_htf_active ON htf_bias (is_active) WHERE is_active = TRUE;
CREATE INDEX idx_htf_confidence ON htf_bias (confidence_score DESC);
CREATE INDEX idx_htf_valid_until ON htf_bias (valid_until);
CREATE INDEX idx_htf_levels ON htf_bias USING GIN (key_levels);
CREATE INDEX idx_htf_structure ON htf_bias USING GIN (market_structure);

-- Retention policy
SELECT add_retention_policy('htf_bias', INTERVAL '6 months');

-- =====================================================
-- Table 4: session_bias
-- Purpose: Track intraday session-specific bias
-- =====================================================
CREATE TABLE IF NOT EXISTS session_bias (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    session VARCHAR(20) NOT NULL, -- 'LONDON', 'NY_AM', 'NY_PM', 'ASIA'
    
    -- Bias determination
    bias VARCHAR(10) NOT NULL CHECK (bias IN ('BULLISH', 'BEARISH', 'NEUTRAL')),
    confidence_score DECIMAL(5,2) CHECK (confidence_score >= 0 AND confidence_score <= 100),
    
    -- Session details
    true_open_price DECIMAL(10,2),
    current_quarter VARCHAR(5),
    quarter_phase VARCHAR(20),
    
    -- Price zones
    premium_zone_high DECIMAL(10,2),
    discount_zone_low DECIMAL(10,2),
    fair_value DECIMAL(10,2),
    current_price_zone VARCHAR(20), -- 'PREMIUM', 'FAIR_VALUE', 'DISCOUNT'
    
    -- Entry guidance
    entry_recommendation TEXT,
    fake_move_detected BOOLEAN DEFAULT FALSE,
    real_move_confirmed BOOLEAN DEFAULT FALSE,
    entry_window_status VARCHAR(20), -- 'CLOSED', 'OPENING', 'OPEN', 'OPTIMAL', 'CLOSING'
    
    -- Supporting data
    supporting_data JSONB DEFAULT '{}'::jsonb,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable
SELECT create_hypertable('session_bias', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX idx_sb_timestamp_desc ON session_bias (timestamp DESC);
CREATE INDEX idx_sb_session ON session_bias (session);
CREATE INDEX idx_sb_bias ON session_bias (bias);
CREATE INDEX idx_sb_quarter ON session_bias (current_quarter);
CREATE INDEX idx_sb_phase ON session_bias (quarter_phase);
CREATE INDEX idx_sb_fake_move ON session_bias (fake_move_detected) WHERE fake_move_detected = TRUE;
CREATE INDEX idx_sb_real_move ON session_bias (real_move_confirmed) WHERE real_move_confirmed = TRUE;
CREATE INDEX idx_sb_entry_window ON session_bias (entry_window_status);
CREATE INDEX idx_sb_confidence ON session_bias (confidence_score DESC);
CREATE INDEX idx_sb_supporting ON session_bias USING GIN (supporting_data);

-- Retention policy
SELECT add_retention_policy('session_bias', INTERVAL '1 month');

-- =====================================================
-- Table 5: session_cycles
-- Purpose: Track individual session cycles (Asia, London, NY AM, NY PM)
--          with high/low tracking for liquidity sweep detection
-- =====================================================
CREATE TABLE IF NOT EXISTS session_cycles (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL DEFAULT 'NQ',
    session VARCHAR(20) NOT NULL CHECK (session IN ('ASIA', 'LONDON', 'NY_AM', 'NY_PM')),
    
    -- Session time boundaries
    session_start TIMESTAMPTZ NOT NULL,
    session_end TIMESTAMPTZ NOT NULL,
    
    -- Cycle classification
    cycle_type VARCHAR(10) CHECK (cycle_type IN ('AMDX', 'XAMD', 'UNKNOWN')),
    confidence_score DECIMAL(5,2) CHECK (confidence_score >= 0 AND confidence_score <= 100),
    
    -- Quarter progression within session
    current_quarter VARCHAR(5) CHECK (current_quarter IN ('Q1', 'Q2', 'Q3', 'Q4')),
    quarter_phase VARCHAR(20) CHECK (quarter_phase IN (
        'ACCUMULATION', 
        'MANIPULATION', 
        'DISTRIBUTION', 
        'CONTINUATION'
    )),
    
    -- High/Low tracking
    session_high DECIMAL(12,4),
    session_low DECIMAL(12,4),
    session_high_time TIMESTAMPTZ,
    session_low_time TIMESTAMPTZ,
    session_open DECIMAL(12,4),
    session_close DECIMAL(12,4),
    
    -- Quarter-specific highs/lows (within session)
    q1_high DECIMAL(12,4),
    q1_low DECIMAL(12,4),
    q2_high DECIMAL(12,4),
    q2_low DECIMAL(12,4),
    q3_high DECIMAL(12,4),
    q3_low DECIMAL(12,4),
    q4_high DECIMAL(12,4),
    q4_low DECIMAL(12,4),
    
    -- Liquidity sweep tracking
    liquidity_sweeps JSONB DEFAULT '[]'::jsonb, -- Array of sweep events
    manipulation_detected BOOLEAN DEFAULT FALSE,
    reversal_after_sweep BOOLEAN DEFAULT FALSE,
    
    -- Session characteristics
    volatility DECIMAL(12,4), -- Session range (high - low)
    total_volume BIGINT,
    aggressive_buy_volume BIGINT,
    aggressive_sell_volume BIGINT,
    directional_bias VARCHAR(10) CHECK (directional_bias IN ('BULLISH', 'BEARISH', 'NEUTRAL')),
    
    -- Supporting data
    supporting_evidence JSONB DEFAULT '{}'::jsonb,
    
    -- Session completion flag
    is_completed BOOLEAN DEFAULT FALSE,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT unique_session_timestamp UNIQUE (symbol, session, session_start)
);

-- Convert to hypertable
SELECT create_hypertable('session_cycles', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX idx_sc_timestamp_desc ON session_cycles (timestamp DESC);
CREATE INDEX idx_sc_symbol ON session_cycles (symbol);
CREATE INDEX idx_sc_session ON session_cycles (session);
CREATE INDEX idx_sc_session_start ON session_cycles (session_start);
CREATE INDEX idx_sc_cycle_type ON session_cycles (cycle_type);
CREATE INDEX idx_sc_completed ON session_cycles (is_completed);
CREATE INDEX idx_sc_manipulation ON session_cycles (manipulation_detected) WHERE manipulation_detected = TRUE;
CREATE INDEX idx_sc_sweeps ON session_cycles USING GIN (liquidity_sweeps);
CREATE INDEX idx_sc_supporting ON session_cycles USING GIN (supporting_evidence);

-- Compression policy (compress after 7 days)
SELECT add_compression_policy('session_cycles', INTERVAL '7 days');

-- Retention policy (keep 3 months of session data)
SELECT add_retention_policy('session_cycles', INTERVAL '3 months');

-- =====================================================
-- Table 6: liquidity_sweeps
-- Purpose: Track all liquidity sweep events across sessions
-- =====================================================
CREATE TABLE IF NOT EXISTS liquidity_sweeps (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL DEFAULT 'NQ',
    session VARCHAR(20) NOT NULL,
    
    -- Sweep details
    sweep_type VARCHAR(20) NOT NULL CHECK (sweep_type IN (
        'SESSION_HIGH', 'SESSION_LOW',
        'DAILY_HIGH', 'DAILY_LOW',
        'WEEKLY_HIGH', 'WEEKLY_LOW',
        'PREVIOUS_QUARTER_HIGH', 'PREVIOUS_QUARTER_LOW'
    )),
    
    -- Level that was swept
    level_price DECIMAL(12,4) NOT NULL,
    level_timestamp TIMESTAMPTZ, -- When the level was established
    level_source VARCHAR(50), -- e.g., 'ASIA_HIGH', 'LONDON_LOW', 'PREVIOUS_DAY_HIGH'
    
    -- Sweep execution
    sweep_price DECIMAL(12,4) NOT NULL, -- Price that broke the level
    ticks_beyond DECIMAL(8,2), -- How many ticks beyond the level
    sweep_confirmed BOOLEAN DEFAULT FALSE, -- Close beyond level (not just wick)
    
    -- Reversal tracking
    reversal_detected BOOLEAN DEFAULT FALSE,
    reversal_time TIMESTAMPTZ,
    reversal_price DECIMAL(12,4),
    reversal_duration_seconds INT, -- Time between sweep and reversal
    
    -- Classification
    is_fake_move BOOLEAN, -- Sweep + quick reversal = manipulation
    is_real_move BOOLEAN, -- Sweep + continuation = true breakout
    
    -- Market context at sweep
    current_quarter VARCHAR(5),
    quarter_phase VARCHAR(20),
    daily_cycle_type VARCHAR(10),
    
    -- Supporting data
    absorption_at_sweep JSONB, -- Absorption data snapshot
    stops_triggered INT, -- Number of stops triggered
    aggressive_orders_pct DECIMAL(5,2), -- Aggressive order % during sweep
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Convert to hypertable
SELECT create_hypertable('liquidity_sweeps', 'timestamp',
    chunk_time_interval => INTERVAL '1 day',
    if_not_exists => TRUE
);

-- Indexes
CREATE INDEX idx_ls_timestamp_desc ON liquidity_sweeps (timestamp DESC);
CREATE INDEX idx_ls_symbol ON liquidity_sweeps (symbol);
CREATE INDEX idx_ls_session ON liquidity_sweeps (session);
CREATE INDEX idx_ls_sweep_type ON liquidity_sweeps (sweep_type);
CREATE INDEX idx_ls_fake_move ON liquidity_sweeps (is_fake_move) WHERE is_fake_move = TRUE;
CREATE INDEX idx_ls_real_move ON liquidity_sweeps (is_real_move) WHERE is_real_move = TRUE;
CREATE INDEX idx_ls_reversal ON liquidity_sweeps (reversal_detected) WHERE reversal_detected = TRUE;
CREATE INDEX idx_ls_level_price ON liquidity_sweeps (level_price);
CREATE INDEX idx_ls_quarter ON liquidity_sweeps (current_quarter);

-- Retention policy (keep 3 months)
SELECT add_retention_policy('liquidity_sweeps', INTERVAL '3 months');

-- =====================================================
-- Helper Views for Common Queries
-- =====================================================

-- View: Current Daily Cycle State
CREATE OR REPLACE VIEW v_current_daily_cycle AS
SELECT 
    qc.*,
    sb.session,
    sb.bias as session_bias,
    sb.entry_window_status,
    sb.fake_move_detected,
    sb.real_move_confirmed
FROM quarterly_cycles qc
LEFT JOIN LATERAL (
    SELECT * FROM session_bias 
    WHERE session_bias.timestamp <= qc.timestamp
    ORDER BY timestamp DESC 
    LIMIT 1
) sb ON TRUE
WHERE qc.timeframe = 'daily'
ORDER BY qc.timestamp DESC
LIMIT 1;

-- View: Latest HTF Bias
CREATE OR REPLACE VIEW v_latest_htf_bias AS
SELECT 
    timeframe,
    bias,
    confidence_score,
    key_levels,
    market_structure,
    valid_until,
    CASE 
        WHEN valid_until > NOW() THEN TRUE
        ELSE FALSE
    END as is_valid
FROM htf_bias
WHERE is_active = TRUE
ORDER BY timestamp DESC;

-- View: Recent Phase Transitions
CREATE OR REPLACE VIEW v_recent_phase_transitions AS
SELECT 
    pt.*,
    EXTRACT(EPOCH FROM (LAG(timestamp) OVER (PARTITION BY timeframe ORDER BY timestamp DESC) - timestamp)) / 60 as minutes_in_phase
FROM phase_transitions pt
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- View: Current Session Cycles (All Active Sessions)
CREATE OR REPLACE VIEW v_current_session_cycles AS
SELECT 
    session,
    cycle_type,
    current_quarter,
    quarter_phase,
    session_high,
    session_low,
    session_open,
    session_close,
    volatility,
    directional_bias,
    manipulation_detected,
    liquidity_sweeps,
    is_completed,
    session_start,
    session_end
FROM session_cycles
WHERE timestamp::date = CURRENT_DATE
ORDER BY session_start DESC;

-- View: Recent Liquidity Sweeps
CREATE OR REPLACE VIEW v_recent_liquidity_sweeps AS
SELECT 
    ls.*,
    CASE 
        WHEN ls.reversal_detected THEN 'FAKE_MOVE'
        WHEN ls.sweep_confirmed AND NOT ls.reversal_detected THEN 'REAL_MOVE'
        ELSE 'PENDING'
    END as move_classification,
    sc.session_high,
    sc.session_low,
    sc.cycle_type as session_cycle_type
FROM liquidity_sweeps ls
LEFT JOIN session_cycles sc ON 
    ls.session = sc.session 
    AND ls.timestamp >= sc.session_start 
    AND ls.timestamp <= sc.session_end
WHERE ls.timestamp > NOW() - INTERVAL '24 hours'
ORDER BY ls.timestamp DESC;

-- View: Session Highs and Lows Summary
CREATE OR REPLACE VIEW v_session_key_levels AS
SELECT 
    CURRENT_DATE as date,
    MAX(CASE WHEN session = 'ASIA' THEN session_high END) as asia_high,
    MIN(CASE WHEN session = 'ASIA' THEN session_low END) as asia_low,
    MAX(CASE WHEN session = 'LONDON' THEN session_high END) as london_high,
    MIN(CASE WHEN session = 'LONDON' THEN session_low END) as london_low,
    MAX(CASE WHEN session = 'NY_AM' THEN session_high END) as ny_am_high,
    MIN(CASE WHEN session = 'NY_AM' THEN session_low END) as ny_am_low,
    MAX(CASE WHEN session = 'NY_PM' THEN session_high END) as ny_pm_high,
    MIN(CASE WHEN session = 'NY_PM' THEN session_low END) as ny_pm_low,
    MAX(session_high) as daily_high,
    MIN(session_low) as daily_low
FROM session_cycles
WHERE timestamp::date = CURRENT_DATE
GROUP BY CURRENT_DATE;

-- =====================================================
-- Functions for Analysis
-- =====================================================

-- Function: Get current quarter for timeframe
CREATE OR REPLACE FUNCTION get_current_quarter(
    p_timeframe VARCHAR(20)
) RETURNS TABLE (
    cycle_type VARCHAR(10),
    current_quarter VARCHAR(5),
    quarter_phase VARCHAR(20),
    confidence_score DECIMAL(5,2),
    quarter_start TIMESTAMPTZ,
    estimated_quarter_end TIMESTAMPTZ
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        qc.cycle_type,
        qc.current_quarter,
        qc.quarter_phase,
        qc.confidence_score,
        qc.quarter_start,
        qc.estimated_quarter_end
    FROM quarterly_cycles qc
    WHERE qc.timeframe = p_timeframe
    ORDER BY qc.timestamp DESC
    LIMIT 1;
END;
$$ LANGUAGE plpgsql;

-- Function: Calculate phase duration statistics
CREATE OR REPLACE FUNCTION get_phase_duration_stats(
    p_timeframe VARCHAR(20),
    p_days_back INTEGER DEFAULT 30
) RETURNS TABLE (
    phase VARCHAR(20),
    avg_duration_minutes NUMERIC,
    min_duration_minutes NUMERIC,
    max_duration_minutes NUMERIC,
    occurrence_count BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        pt.to_phase,
        AVG(EXTRACT(EPOCH FROM (next_transition - pt.timestamp)) / 60)::NUMERIC as avg_duration,
        MIN(EXTRACT(EPOCH FROM (next_transition - pt.timestamp)) / 60)::NUMERIC as min_duration,
        MAX(EXTRACT(EPOCH FROM (next_transition - pt.timestamp)) / 60)::NUMERIC as max_duration,
        COUNT(*) as occurrence_count
    FROM phase_transitions pt
    LEFT JOIN LATERAL (
        SELECT timestamp as next_transition
        FROM phase_transitions
        WHERE timeframe = pt.timeframe
          AND timestamp > pt.timestamp
        ORDER BY timestamp ASC
        LIMIT 1
    ) next ON TRUE
    WHERE pt.timeframe = p_timeframe
      AND pt.timestamp > NOW() - (p_days_back || ' days')::INTERVAL
      AND next_transition IS NOT NULL
    GROUP BY pt.to_phase
    ORDER BY occurrence_count DESC;
END;
$$ LANGUAGE plpgsql;

-- Function: Check if in entry window
CREATE OR REPLACE FUNCTION is_entry_window_open(
    p_timestamp TIMESTAMPTZ DEFAULT NOW()
) RETURNS TABLE (
    is_open BOOLEAN,
    window_status VARCHAR(20),
    reason TEXT
) AS $$
DECLARE
    v_quarter VARCHAR(5);
    v_phase VARCHAR(20);
    v_bias VARCHAR(10);
    v_fake_detected BOOLEAN;
BEGIN
    -- Get latest session bias
    SELECT 
        current_quarter,
        quarter_phase,
        bias,
        fake_move_detected
    INTO v_quarter, v_phase, v_bias, v_fake_detected
    FROM session_bias
    WHERE timestamp <= p_timestamp
    ORDER BY timestamp DESC
    LIMIT 1;
    
    -- Determine entry window status
    IF v_quarter IN ('Q3', 'Q4') AND v_fake_detected = FALSE AND v_phase IN ('DISTRIBUTION', 'CONTINUATION') THEN
        RETURN QUERY SELECT TRUE, 'OPEN'::VARCHAR(20), 'Q3/Q4 distribution active, fake move cleared'::TEXT;
    ELSIF v_quarter = 'Q2' AND v_phase = 'MANIPULATION' THEN
        RETURN QUERY SELECT FALSE, 'OPENING'::VARCHAR(20), 'Q2 manipulation completing, Q3 approaching'::TEXT;
    ELSIF v_quarter = 'Q1' THEN
        RETURN QUERY SELECT FALSE, 'CLOSED'::VARCHAR(20), 'Q1 accumulation, wait for manipulation'::TEXT;
    ELSE
        RETURN QUERY SELECT FALSE, 'CLOSED'::VARCHAR(20), 'Conditions not met for entry'::TEXT;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- Materialized Views for Performance
-- =====================================================

-- Materialized view: Daily cycle summary (refresh every 5 minutes)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_cycle_summary AS
SELECT 
    date_trunc('day', timestamp) as trading_day,
    cycle_type,
    COUNT(DISTINCT current_quarter) as quarters_observed,
    MAX(confidence_score) as max_confidence,
    AVG(confidence_score) as avg_confidence,
    jsonb_agg(
        jsonb_build_object(
            'quarter', current_quarter,
            'phase', quarter_phase,
            'start', quarter_start,
            'end', estimated_quarter_end
        ) ORDER BY quarter_start
    ) as quarter_progression
FROM quarterly_cycles
WHERE timeframe = 'daily'
  AND timestamp > NOW() - INTERVAL '30 days'
GROUP BY trading_day, cycle_type
ORDER BY trading_day DESC;

-- Index on materialized view
CREATE INDEX idx_mv_daily_trading_day ON mv_daily_cycle_summary (trading_day DESC);

-- Refresh function (call every 5 minutes)
CREATE OR REPLACE FUNCTION refresh_cycle_summaries()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_cycle_summary;
END;
$$ LANGUAGE plpgsql;

-- =====================================================
-- Initial Data / Configuration
-- =====================================================

-- Insert configuration for time windows (stored as JSONB in a config table if needed)
-- This can be referenced by the analysis engine

-- Function: Detect liquidity sweep
CREATE OR REPLACE FUNCTION detect_liquidity_sweep(
    p_current_price DECIMAL(12,4),
    p_level_price DECIMAL(12,4),
    p_sweep_type VARCHAR(20),
    p_tolerance_ticks INT DEFAULT 3
) RETURNS BOOLEAN AS $$
DECLARE
    tick_size DECIMAL(6,4) := 0.25; -- NQ tick size
    tolerance DECIMAL(12,4);
    is_sweep BOOLEAN := FALSE;
BEGIN
    tolerance := tick_size * p_tolerance_ticks;
    
    -- Check if price swept the level
    IF p_sweep_type LIKE '%HIGH' THEN
        -- Sweeping a high requires price to go above
        is_sweep := (p_current_price >= p_level_price + tolerance);
    ELSIF p_sweep_type LIKE '%LOW' THEN
        -- Sweeping a low requires price to go below
        is_sweep := (p_current_price <= p_level_price - tolerance);
    END IF;
    
    RETURN is_sweep;
END;
$$ LANGUAGE plpgsql;

-- Function: Get key levels for sweep detection
CREATE OR REPLACE FUNCTION get_key_levels_for_sweep(
    p_timestamp TIMESTAMPTZ,
    p_symbol VARCHAR(20) DEFAULT 'NQ'
) RETURNS TABLE (
    level_name VARCHAR(50),
    level_price DECIMAL(12,4),
    level_timestamp TIMESTAMPTZ,
    level_type VARCHAR(20)
) AS $$
BEGIN
    -- Return all key levels that could be swept
    RETURN QUERY
    
    -- Previous day high/low
    SELECT 
        'PREVIOUS_DAY_HIGH' as level_name,
        MAX(session_high) as level_price,
        MAX(session_end) as level_timestamp,
        'DAILY_HIGH'::VARCHAR(20) as level_type
    FROM session_cycles
    WHERE symbol = p_symbol
    AND session_end::date = (p_timestamp::date - INTERVAL '1 day')
    
    UNION ALL
    
    SELECT 
        'PREVIOUS_DAY_LOW' as level_name,
        MIN(session_low) as level_price,
        MAX(session_end) as level_timestamp,
        'DAILY_LOW'::VARCHAR(20) as level_type
    FROM session_cycles
    WHERE symbol = p_symbol
    AND session_end::date = (p_timestamp::date - INTERVAL '1 day')
    
    UNION ALL
    
    -- Asia session high/low
    SELECT 
        'ASIA_HIGH' as level_name,
        session_high as level_price,
        session_end as level_timestamp,
        'SESSION_HIGH'::VARCHAR(20) as level_type
    FROM session_cycles
    WHERE symbol = p_symbol
    AND session = 'ASIA'
    AND session_start::date = p_timestamp::date
    
    UNION ALL
    
    SELECT 
        'ASIA_LOW' as level_name,
        session_low as level_price,
        session_end as level_timestamp,
        'SESSION_LOW'::VARCHAR(20) as level_type
    FROM session_cycles
    WHERE symbol = p_symbol
    AND session = 'ASIA'
    AND session_start::date = p_timestamp::date
    
    UNION ALL
    
    -- London session high/low
    SELECT 
        'LONDON_HIGH' as level_name,
        session_high as level_price,
        session_end as level_timestamp,
        'SESSION_HIGH'::VARCHAR(20) as level_type
    FROM session_cycles
    WHERE symbol = p_symbol
    AND session = 'LONDON'
    AND session_start::date = p_timestamp::date
    
    UNION ALL
    
    SELECT 
        'LONDON_LOW' as level_name,
        session_low as level_price,
        session_end as level_timestamp,
        'SESSION_LOW'::VARCHAR(20) as level_type
    FROM session_cycles
    WHERE symbol = p_symbol
    AND session = 'LONDON'
    AND session_start::date = p_timestamp::date;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE quarterly_cycles IS 'Tracks AMDX/XAMD cycle state across weekly, daily, session, and hourly timeframes';
COMMENT ON TABLE phase_transitions IS 'Logs all quarter and phase transitions with triggers and supporting data';
COMMENT ON TABLE htf_bias IS 'Stores weekly and daily bias determinations with key levels';
COMMENT ON TABLE session_bias IS 'Tracks London, NY AM, NY PM, and Asia session bias with entry guidance';
COMMENT ON TABLE session_cycles IS 'Tracks individual session cycles (Asia, London, NY AM, NY PM) with high/low tracking for liquidity sweep detection';
COMMENT ON TABLE liquidity_sweeps IS 'Records all liquidity sweep events with reversal tracking to identify fake vs real moves';

COMMENT ON COLUMN quarterly_cycles.cycle_type IS 'AMDX (Accumulation→Manipulation→Distribution→Continuation) or XAMD (Continuation→Accumulation→Manipulation→Distribution)';
COMMENT ON COLUMN quarterly_cycles.quarter_phase IS 'Current phase within quarter: ACCUMULATION, MANIPULATION, DISTRIBUTION, CONTINUATION, or REVERSAL';
COMMENT ON COLUMN quarterly_cycles.supporting_evidence IS 'JSON object containing absorption data, stops/icebergs, MBO metrics that support the classification';

COMMENT ON COLUMN phase_transitions.transition_trigger IS 'What caused the phase transition: DISPLACEMENT_DETECTED, LIQUIDITY_SWEEP, TIME_WINDOW_END, CONSOLIDATION_BREAK, etc.';
COMMENT ON COLUMN phase_transitions.supporting_data IS 'Snapshot of absorption, stops, icebergs, MBO data at transition moment';

COMMENT ON COLUMN htf_bias.key_levels IS 'JSON with premium zone, discount zone, fair value, IRL (FVGs), ERL (highs/lows)';
COMMENT ON COLUMN htf_bias.market_structure IS 'JSON with displacement status, manipulation detected, one-sided vs two-sided analysis';

COMMENT ON COLUMN session_bias.entry_window_status IS 'CLOSED (Q1/Q2), OPENING (Q2 late), OPEN (Q3), OPTIMAL (Q3/Q4 transition), CLOSING (Q4 late)';

-- =====================================================
-- Grants (adjust based on your user roles)
-- =====================================================
-- GRANT SELECT, INSERT, UPDATE ON quarterly_cycles TO dashboard_user;
-- GRANT SELECT, INSERT ON phase_transitions TO dashboard_user;
-- GRANT SELECT, INSERT, UPDATE ON htf_bias TO dashboard_user;
-- GRANT SELECT, INSERT, UPDATE ON session_bias TO dashboard_user;

-- =====================================================
-- Complete
-- =====================================================
-- Run this migration to set up the quarterly theory database schema
-- Next steps: Implement the analysis engine to populate these tables
