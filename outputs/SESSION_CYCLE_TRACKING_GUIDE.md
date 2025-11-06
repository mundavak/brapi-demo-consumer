# Session Cycle Tracking - Implementation Guide

## Overview

Session cycle tracking extends the quarterly theory system by tracking **individual session cycles** (Asia, London, NY AM, NY PM) with real-time high/low monitoring and liquidity sweep detection. This enables precise identification of manipulation patterns within each session.

## New Components Added

### 1. Database Tables

#### **session_cycles**

Tracks individual session cycles with high/low data and quarter progression.

**Key Columns**:

- `session`: ASIA, LONDON, NY_AM, NY_PM
- `session_high/low`: Highest/lowest price during session
- `session_high_time/low_time`: When highs/lows occurred
- `q1_high/low` through `q4_high/low`: Quarter-specific extremes
- `liquidity_sweeps`: JSONB array of sweep events
- `manipulation_detected`: Boolean flag
- `is_completed`: Session end marker

**SQL Creation**:

```sql
CREATE TABLE session_cycles (
    timestamp TIMESTAMPTZ NOT NULL,
    session VARCHAR(20) CHECK (session IN ('ASIA', 'LONDON', 'NY_AM', 'NY_PM')),
    session_high/low DECIMAL(12,4),
    q1_high/low through q4_high/low DECIMAL(12,4),
    liquidity_sweeps JSONB DEFAULT '[]'::jsonb,
    ...
);
```

#### **liquidity_sweeps**

Records every liquidity sweep event with reversal tracking.

**Key Columns**:

- `sweep_type`: SESSION_HIGH, SESSION_LOW, DAILY_HIGH, DAILY_LOW, etc.
- `level_price`: The price level that was swept
- `level_source`: Where the level came from (e.g., 'ASIA_HIGH', 'LONDON_LOW')
- `sweep_price`: Actual price that broke the level
- `ticks_beyond`: How far beyond the level (2-3 ticks = confirmed)
- `reversal_detected`: Boolean - Did price reverse after sweep?
- `reversal_time/price/duration_seconds`: Reversal details
- `is_fake_move/is_real_move`: Classification flags

**SQL Creation**:

```sql
CREATE TABLE liquidity_sweeps (
    timestamp TIMESTAMPTZ NOT NULL,
    sweep_type VARCHAR(20) CHECK (sweep_type IN ('SESSION_HIGH', 'SESSION_LOW', ...)),
    level_price DECIMAL(12,4) NOT NULL,
    reversal_detected BOOLEAN DEFAULT FALSE,
    is_fake_move BOOLEAN,
    is_real_move BOOLEAN,
    ...
);
```

### 2. Helper Views

#### **v_current_session_cycles**

Shows all active session cycles for today:

```sql
SELECT session, cycle_type, current_quarter, session_high, session_low,
       manipulation_detected, liquidity_sweeps
FROM session_cycles
WHERE timestamp::date = CURRENT_DATE
ORDER BY session_start DESC;
```

#### **v_recent_liquidity_sweeps**

Shows recent sweeps with classification:

```sql
SELECT ls.*,
       CASE WHEN reversal_detected THEN 'FAKE_MOVE'
            WHEN sweep_confirmed AND NOT reversal_detected THEN 'REAL_MOVE'
            ELSE 'PENDING' END as move_classification
FROM liquidity_sweeps ls
WHERE timestamp > NOW() - INTERVAL '24 hours';
```

#### **v_session_key_levels**

Daily summary of all session highs/lows:

```sql
SELECT date, asia_high, asia_low, london_high, london_low,
       ny_am_high, ny_am_low, ny_pm_high, ny_pm_low
FROM session_cycles
WHERE timestamp::date = CURRENT_DATE;
```

### 3. Helper Functions

#### **detect_liquidity_sweep()**

Determines if current price swept a level:

```sql
SELECT detect_liquidity_sweep(
    p_current_price := 18455.50,
    p_level_price := 18450.00,
    p_sweep_type := 'SESSION_HIGH',
    p_tolerance_ticks := 3
) as is_sweep;
-- Returns TRUE if price >= level + (3 * 0.25 ticks)
```

#### **get_key_levels_for_sweep()**

Returns all key levels that could be swept:

```sql
SELECT * FROM get_key_levels_for_sweep(NOW(), 'NQ');
-- Returns: PREVIOUS_DAY_HIGH/LOW, ASIA_HIGH/LOW, LONDON_HIGH/LOW, etc.
```

### 4. Python Module: `session_cycle_tracker.py`

#### **SessionCycleTracker Class**

**Core Methods**:

**`initialize_session(session, current_time)`**

- Creates new `SessionCycleState` object
- Sets session start/end times based on session type
- Gets first price as session open
- Example:

```python
state = tracker.initialize_session('LONDON', datetime.now(EST))
# state.session_start = today 00:00 EST
# state.session_end = today 06:00 EST
```

**`update_session_high_low(session, current_time, current_price)`**

- Updates session high if price exceeds previous high
- Updates session low if price falls below previous low
- Determines current quarter (Q1/Q2/Q3/Q4) within session
- Updates quarter-specific highs/lows
- Called every 60 seconds during active session
- Example:

```python
tracker.update_session_high_low('LONDON', now, 18455.75)
# Updates: session_high, session_high_time
# Updates: q2_high (if in Q2), q2_low
```

**`detect_liquidity_sweeps(session, current_time, current_price)`**

- Gets key levels from cache/database
- Checks if current price swept any level (tolerance: 2-3 ticks)
- Records sweep event in `liquidity_sweeps` list
- Writes to `liquidity_sweeps` table
- Example:

```python
# Key level: ASIA_HIGH = 18450.00
# Current price: 18451.00 (4 ticks beyond)
# Result: LIQUIDITY SWEEP DETECTED
```

**`check_reversal_after_sweep(session, current_time, current_price)`**

- Monitors recent sweeps (last 5 minutes)
- Detects if price reversed significantly (10+ ticks)
- Updates sweep record with reversal data
- Sets `manipulation_detected = TRUE`
- Example:

```python
# Sweep at 18451.00
# Current price: 18448.50 (10 ticks reversal in 3 minutes)
# Classification: FAKE MOVE (manipulation)
```

**`complete_session(session)`**

- Marks session as completed
- Gets final price as session close
- Calculates volatility (high - low)
- Writes final data to `session_cycles` table
- Example:

```python
tracker.complete_session('LONDON')
# Writes: session_high=18455, session_low=18435, volatility=20
```

### 5. Integration with Main Service

The `QuarterlyTheoryService` now includes session tracking in `run_realtime_tracking()`:

**Workflow (Every 60 Seconds)**:

```python
1. Determine current session (ASIA, LONDON, NY_AM, NY_PM)
2. If session changed:
   - Complete previous session
   - Initialize new session
3. Get current price
4. Update session high/low
5. Detect liquidity sweeps
6. Check for reversals after sweeps
7. Continue with existing quarterly tracking...
```

**Code Flow**:

```python
async def run_realtime_tracking(self):
    now = datetime.now(EST)

    # Determine current session
    new_session = self._determine_current_session(now)

    # Session transition
    if new_session != self.current_session:
        if self.current_session:
            self.session_tracker.complete_session(self.current_session)
        if new_session:
            self.session_tracker.initialize_session(new_session, now)
        self.current_session = new_session

    # Update high/low tracking
    if self.current_session:
        current_price = self.data_fetcher.get_latest_price()
        self.session_tracker.update_session_high_low(self.current_session, now, current_price)
        self.session_tracker.detect_liquidity_sweeps(self.current_session, now, current_price)
        self.session_tracker.check_reversal_after_sweep(self.current_session, now, current_price)

    # ... existing quarterly tracking continues ...
```

## Session Quarter Time Windows

### ASIA Session (18:00-00:00 EST)

```
Q1: 18:00-19:30 (90 minutes)
Q2: 19:30-21:00 (90 minutes)
Q3: 21:00-22:30 (90 minutes)
Q4: 22:30-00:00 (90 minutes)
```

### LONDON Session (00:00-06:00 EST)

```
Q1: 00:00-01:30 (90 minutes)
Q2: 01:30-03:00 (90 minutes)
Q3: 03:00-04:30 (90 minutes)
Q4: 04:30-06:00 (90 minutes)
```

### NY AM Session (07:30-13:30 EST)

```
Q1: 07:30-09:00 (90 minutes)
Q2: 09:00-10:30 (90 minutes)
Q3: 10:30-12:00 (90 minutes)
Q4: 12:00-13:30 (90 minutes)
```

### NY PM Session (13:30-18:00 EST)

```
Q1: 13:30-14:45 (75 minutes)
Q2: 14:45-16:00 (75 minutes)
Q3: 16:00-17:15 (75 minutes)
Q4: 17:15-18:00 (45 minutes)
```

## Liquidity Sweep Detection Logic

### Key Levels Monitored

1. **Previous Day High/Low** - From all sessions yesterday
2. **Asia Session High/Low** - From today's Asia session
3. **London Session High/Low** - From today's London session
4. **Current Session Quarter Highs/Lows** - From earlier quarters within session

### Sweep Confirmation

**Criteria**:

- Price must **close beyond** the level (not just wick through)
- Tolerance: **2-3 ticks beyond** the level to confirm sweep
- NQ tick size: **0.25 points**

**Example**:

```
Asia High: 18450.00
Current Price: 18451.00 (4 ticks beyond = 18450.00 + (4 * 0.25))
Result: SWEEP CONFIRMED (beyond 3-tick tolerance)
```

### Fake Move Detection

**Criteria**:

- Liquidity sweep occurred
- Price reversed **within 2-5 minutes**
- Reversal magnitude: **10+ ticks** in opposite direction

**Example**:

```
10:15 AM: Asia High (18450) swept → Price reaches 18451
10:17 AM: Price reverses to 18448.50 (10 ticks down)
Duration: 2 minutes
Classification: FAKE MOVE (manipulation detected)
```

### Real Move Detection

**Criteria**:

- Liquidity sweep occurred
- Price **continued** beyond level (no reversal)
- Follow-through for **5+ minutes**

**Example**:

```
10:15 AM: Asia High (18450) swept → Price reaches 18451
10:20 AM: Price continues to 18455 (20 ticks beyond)
Duration: 5 minutes, no reversal
Classification: REAL MOVE (true breakout)
```

## Usage Examples

### Query Session Highs/Lows

```sql
-- Get today's session key levels
SELECT * FROM v_session_key_levels;

-- Result:
-- date       | asia_high | asia_low | london_high | london_low | ny_am_high | ny_am_low
-- 2025-10-30 | 18455.00  | 18430.00 | 18462.00    | 18435.00   | 18475.00   | 18450.00
```

### Query Recent Liquidity Sweeps

```sql
-- Get recent sweeps with classification
SELECT
    timestamp,
    sweep_type,
    level_price,
    sweep_price,
    ticks_beyond,
    reversal_detected,
    CASE
        WHEN reversal_detected THEN 'FAKE_MOVE'
        WHEN NOT reversal_detected THEN 'REAL_MOVE'
    END as classification
FROM liquidity_sweeps
WHERE timestamp::date = CURRENT_DATE
ORDER BY timestamp DESC;

-- Result:
-- timestamp           | sweep_type    | level_price | sweep_price | ticks_beyond | reversal | classification
-- 2025-10-30 10:17:00 | SESSION_HIGH  | 18450.00    | 18451.00    | 4.0          | TRUE     | FAKE_MOVE
-- 2025-10-30 09:45:00 | DAILY_LOW     | 18430.00    | 18428.50    | 6.0          | FALSE    | REAL_MOVE
```

### Check Session Manipulation

```sql
-- Check if manipulation detected in any session today
SELECT
    session,
    session_high,
    session_low,
    manipulation_detected,
    reversal_after_sweep,
    jsonb_array_length(liquidity_sweeps) as sweep_count
FROM session_cycles
WHERE timestamp::date = CURRENT_DATE
AND manipulation_detected = TRUE;

-- Result:
-- session | session_high | session_low | manipulation | reversal | sweep_count
-- LONDON  | 18462.00     | 18435.00    | TRUE         | TRUE     | 2
```

### Get Sweep Details from Session

```sql
-- Get all sweeps from London session with details
SELECT
    sc.session,
    sweep->>'timestamp' as sweep_time,
    sweep->>'level_name' as level_swept,
    (sweep->>'level_price')::decimal as level_price,
    (sweep->>'sweep_price')::decimal as sweep_price,
    sweep->>'confirmed' as confirmed
FROM session_cycles sc,
     jsonb_array_elements(liquidity_sweeps) as sweep
WHERE session = 'LONDON'
AND timestamp::date = CURRENT_DATE;
```

## Dashboard Integration

### Real-Time Display Panel

**Session Cycle Panel**:

```jsx
<SessionCyclePanel>
  <CurrentSession>
    Session: LONDON Quarter: Q3 High: 18462.00 (03:45 AM) Low: 18435.00 (01:20
    AM) Volatility: 27 ticks
  </CurrentSession>

  <LiquiditySweeps>
    ⚠️ SWEEP DETECTED: Asia High (18450) at 03:15 AM ⚠️ REVERSAL: Price reversed
    to 18445 (3 min later) Classification: FAKE MOVE - Manipulation
  </LiquiditySweeps>

  <KeyLevels>
    Previous Day High: 18475.00 Asia High: 18450.00 ← SWEPT London High:
    18462.00 ← CURRENT SESSION
  </KeyLevels>
</SessionCyclePanel>
```

### API Endpoints (Future)

**GET /api/session/current**

```json
{
  "session": "LONDON",
  "current_quarter": "Q3",
  "session_high": 18462.0,
  "session_low": 18435.0,
  "session_start": "2025-10-30T00:00:00-05:00",
  "session_end": "2025-10-30T06:00:00-05:00",
  "manipulation_detected": true,
  "liquidity_sweeps": [
    {
      "level_name": "ASIA_HIGH",
      "level_price": 18450.0,
      "sweep_time": "2025-10-30T03:15:00-05:00",
      "reversal_detected": true,
      "classification": "FAKE_MOVE"
    }
  ]
}
```

**GET /api/session/key-levels**

```json
{
  "date": "2025-10-30",
  "levels": {
    "previous_day_high": 18475.0,
    "previous_day_low": 18420.0,
    "asia_high": 18450.0,
    "asia_low": 18430.0,
    "london_high": 18462.0,
    "london_low": 18435.0,
    "current_price": 18455.0,
    "nearest_level_above": {
      "name": "LONDON_HIGH",
      "price": 18462.0,
      "distance": 7.0
    },
    "nearest_level_below": {
      "name": "ASIA_HIGH",
      "price": 18450.0,
      "distance": 5.0
    }
  }
}
```

## Benefits of Session Cycle Tracking

1. **Precise Manipulation Detection**: Identify fake moves within 2-5 minutes of occurrence
2. **Entry Timing**: Know exact levels where liquidity was swept for entry setups
3. **Risk Management**: Place stops below/above swept levels (fake move extremes)
4. **Multi-Session Analysis**: Compare Asia accumulation vs London manipulation
5. **Historical Patterns**: Backtest which sessions show most manipulation
6. **Real-Time Alerts**: Alert trader when Asia high swept during London Q2

## Verification Queries

### Check Service is Writing Data

```sql
-- Check if sessions are being tracked today
SELECT COUNT(*) FROM session_cycles WHERE timestamp::date = CURRENT_DATE;
-- Expected: 1-4 (depending on how many sessions completed)

-- Check if sweeps are being detected
SELECT COUNT(*) FROM liquidity_sweeps WHERE timestamp::date = CURRENT_DATE;
-- Expected: 0-10 (varies based on market activity)

-- Check latest session update
SELECT session, session_high, session_low, is_completed, updated_at
FROM session_cycles
ORDER BY updated_at DESC
LIMIT 1;
```

### Validate High/Low Tracking

```sql
-- Verify highs/lows are updating every minute
SELECT
    session,
    session_high,
    session_low,
    EXTRACT(EPOCH FROM (NOW() - updated_at)) / 60 as minutes_since_update
FROM session_cycles
WHERE is_completed = FALSE
ORDER BY updated_at DESC;
-- Expected: minutes_since_update < 2 (updated within last 2 minutes)
```

## Troubleshooting

**Issue**: No session cycles being created

- **Check**: Service is running and reached active session hours (after 6 PM for Asia)
- **Solution**: Wait until session start time or check `_determine_current_session()` logic

**Issue**: Liquidity sweeps not being detected

- **Check**: Key levels exist in database (previous day high/low, session highs/lows)
- **Solution**: Run service for full day to populate session_cycles table with historical levels

**Issue**: All sweeps showing as "PENDING" classification

- **Check**: Reversal detection running (needs 5 minutes after sweep to confirm)
- **Solution**: Wait 5+ minutes after sweep, check `reversal_detected` flag updates

## Next Steps

1. **Test with Live Data**: Run service during active hours, verify session tracking
2. **Dashboard UI**: Create session cycle panel showing current highs/lows and sweeps
3. **Alerts**: Add notification when manipulation detected (sweep + reversal)
4. **Backtesting**: Analyze historical sweep patterns to validate fake vs real classification
5. **Machine Learning**: Train model to predict sweep reversals based on order flow data

---

**Files Modified**:

- `database/quarterly_theory_schema.sql` - Added session_cycles and liquidity_sweeps tables
- `backend/session_cycle_tracker.py` - New module (500+ lines)
- `backend/quarterly_service.py` - Integrated session tracking into realtime loop

**Total Addition**: ~800 lines of code + 2 new tables + 4 views + 2 functions
