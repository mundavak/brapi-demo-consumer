# Session Cycle Tracking - Quick Reference

## 🎯 What Was Built

Added **session-level tracking** to quarterly theory system:

- Track Asia, London, NY AM, NY PM sessions individually
- Monitor session high/low every 60 seconds
- Detect liquidity sweeps of key levels
- Identify fake moves (sweep + reversal) vs real moves

## 📊 New Database Tables

### `session_cycles` (main tracking table)

```sql
Key columns:
- session: ASIA, LONDON, NY_AM, NY_PM
- session_high/low + timestamps
- q1_high/low, q2_high/low, q3_high/low, q4_high/low
- liquidity_sweeps: JSONB array
- manipulation_detected: BOOLEAN
- is_completed: BOOLEAN
```

### `liquidity_sweeps` (sweep events table)

```sql
Key columns:
- sweep_type: SESSION_HIGH, SESSION_LOW, DAILY_HIGH, DAILY_LOW
- level_price, sweep_price, ticks_beyond
- reversal_detected, reversal_time, reversal_price
- is_fake_move, is_real_move
```

## 📝 Quick Queries

### Get Today's Session Highs/Lows

```sql
SELECT * FROM v_session_key_levels;
```

### Get Recent Liquidity Sweeps

```sql
SELECT
    timestamp,
    sweep_type,
    level_price,
    sweep_price,
    reversal_detected,
    CASE
        WHEN reversal_detected THEN 'FAKE_MOVE'
        ELSE 'REAL_MOVE'
    END as classification
FROM liquidity_sweeps
WHERE timestamp::date = CURRENT_DATE
ORDER BY timestamp DESC;
```

### Check Current Session Status

```sql
SELECT
    session,
    current_quarter,
    session_high,
    session_low,
    manipulation_detected
FROM session_cycles
WHERE is_completed = FALSE;
```

### Find All Fake Moves Today

```sql
SELECT * FROM v_recent_liquidity_sweeps
WHERE reversal_detected = TRUE
AND timestamp::date = CURRENT_DATE;
```

## 🕐 Session Time Windows

| Session | Start | End   | Quarters                |
| ------- | ----- | ----- | ----------------------- |
| ASIA    | 18:00 | 00:00 | 90 min each (Q1-Q4)     |
| LONDON  | 00:00 | 06:00 | 90 min each (Q1-Q4)     |
| NY AM   | 07:30 | 13:30 | 90 min each (Q1-Q4)     |
| NY PM   | 13:30 | 18:00 | 75/75/75/45 min (Q1-Q4) |

## 🎯 Sweep Detection Logic

**Criteria for confirmed sweep**:

- Price must CLOSE beyond level (not just wick)
- Tolerance: 2-3 ticks (3 \* 0.25 = 0.75 points for NQ)
- Example: Asia High = 18450.00 → Sweep at 18451.00 (4 ticks)

**Fake Move Classification**:

- Sweep occurs + price reverses 10+ ticks within 5 minutes
- Sets: `manipulation_detected=TRUE`, `is_fake_move=TRUE`

**Real Move Classification**:

- Sweep occurs + price continues beyond level for 5+ minutes
- Sets: `is_real_move=TRUE`

## 🔧 Key Python Methods

### SessionCycleTracker Class

| Method                         | Purpose                  | Called When      |
| ------------------------------ | ------------------------ | ---------------- |
| `initialize_session()`         | Create new session state | Session starts   |
| `update_session_high_low()`    | Update highs/lows        | Every 60 seconds |
| `detect_liquidity_sweeps()`    | Check for level sweeps   | Every 60 seconds |
| `check_reversal_after_sweep()` | Monitor for fake moves   | Every 60 seconds |
| `complete_session()`           | Finalize session data    | Session ends     |

## 📂 Files Modified

| File                                   | Changes                                | Lines |
| -------------------------------------- | -------------------------------------- | ----- |
| `database/quarterly_theory_schema.sql` | +2 tables, +3 views, +2 functions      | +460  |
| `backend/session_cycle_tracker.py`     | New module (SessionCycleTracker class) | +600  |
| `backend/quarterly_service.py`         | Integration into main loop             | +70   |

**Total**: ~1,130 lines of new code

## 🚀 Deployment Steps

### 1. Apply Database Schema

```powershell
psql -U postgres -d bookmap_data -f database/quarterly_theory_schema.sql
```

### 2. Verify Tables

```sql
\dt session_cycles
\dt liquidity_sweeps
SELECT * FROM v_session_key_levels;
```

### 3. Start Service

```powershell
cd backend
python start_service.py
```

### 4. Monitor Logs

```powershell
tail -f logs/quarterly_service.log
```

Look for:

- "Initialized [SESSION] session"
- "Updated [SESSION] session high: X"
- "LIQUIDITY SWEEP DETECTED: [LEVEL]"
- "REVERSAL DETECTED after [TIME] - FAKE MOVE"

## 🧪 Quick Tests

### Test 1: Check Data Collection (after 5 minutes)

```sql
SELECT COUNT(*) FROM session_cycles WHERE timestamp::date = CURRENT_DATE;
-- Expected: 1 (current session)

SELECT COUNT(*) FROM liquidity_sweeps WHERE timestamp::date = CURRENT_DATE;
-- Expected: 0-5 (depends on market)
```

### Test 2: Check Session High/Low Updates

```sql
SELECT
    session,
    session_high,
    session_low,
    EXTRACT(EPOCH FROM (NOW() - updated_at)) / 60 as minutes_since_update
FROM session_cycles
WHERE is_completed = FALSE;
-- Expected: minutes_since_update < 2 (updated recently)
```

### Test 3: Verify Quarter Progression

```sql
SELECT
    session,
    current_quarter,
    TO_CHAR(timestamp, 'HH24:MI') as time
FROM session_cycles
WHERE is_completed = FALSE;
-- Expected: Q1 at start → Q2 → Q3 → Q4 at end
```

## 📊 Dashboard Integration (Future)

### API Endpoints Needed

```
GET /api/session/current
GET /api/session/key-levels
GET /api/sweeps/recent
WebSocket /ws/session-updates
```

### UI Components Needed

```
<SessionCyclePanel>
  - Current session + quarter
  - Session high/low with times
  - Key levels (Asia/London/NY highs/lows)
  - Recent sweeps with classification
  - Manipulation alerts (red for fake moves)
</SessionCyclePanel>
```

## 🎓 Use Cases

### 1. Entry Validation

**Before entering long**:

```sql
-- Check if recent sweep was fake (bearish signal)
SELECT * FROM liquidity_sweeps
WHERE timestamp > NOW() - INTERVAL '10 minutes'
AND sweep_type IN ('SESSION_HIGH', 'DAILY_HIGH')
AND reversal_detected = TRUE;

-- If rows returned: DON'T ENTER LONG (manipulation zone)
```

### 2. Stop Loss Placement

**After fake move detected**:

```sql
-- Get reversal low (ideal stop below this)
SELECT reversal_price
FROM liquidity_sweeps
WHERE reversal_detected = TRUE
ORDER BY timestamp DESC
LIMIT 1;

-- Place stop 2-3 ticks below reversal_price
```

### 3. Session Analysis

**Compare session characteristics**:

```sql
-- Which session shows most manipulation?
SELECT
    session,
    COUNT(*) as total_sweeps,
    SUM(CASE WHEN reversal_detected THEN 1 ELSE 0 END) as fake_moves,
    ROUND(100.0 * SUM(CASE WHEN reversal_detected THEN 1 ELSE 0 END) / COUNT(*), 2) as fake_pct
FROM liquidity_sweeps
WHERE timestamp > NOW() - INTERVAL '30 days'
GROUP BY session
ORDER BY fake_pct DESC;

-- Result: Identify which session (Asia/London/NY) has highest fake move %
```

### 4. Key Level Monitoring

**Real-time level watch**:

```sql
-- Get all key levels with current price distance
WITH current_price AS (
    SELECT session_high as price
    FROM session_cycles
    WHERE is_completed = FALSE
    ORDER BY updated_at DESC
    LIMIT 1
),
levels AS (
    SELECT 'ASIA_HIGH' as name, asia_high as price FROM v_session_key_levels
    UNION ALL
    SELECT 'ASIA_LOW', asia_low FROM v_session_key_levels
    UNION ALL
    SELECT 'LONDON_HIGH', london_high FROM v_session_key_levels
    -- etc.
)
SELECT
    l.name,
    l.price,
    ABS(l.price - cp.price) / 0.25 as ticks_away,
    CASE
        WHEN ABS(l.price - cp.price) / 0.25 < 5 THEN '⚠️ CLOSE'
        WHEN ABS(l.price - cp.price) / 0.25 < 20 THEN '👀 WATCH'
        ELSE '✅ FAR'
    END as alert
FROM levels l, current_price cp
WHERE l.price IS NOT NULL
ORDER BY ticks_away;
```

## 🐛 Troubleshooting

| Issue                         | Solution                                                            |
| ----------------------------- | ------------------------------------------------------------------- |
| No sessions in database       | Check service is running during session hours (after 6 PM for Asia) |
| No sweeps detected            | Wait for price to exceed session high/low by 3+ ticks               |
| Sweeps always "PENDING"       | Wait 5 minutes after sweep for reversal detection                   |
| Session high/low not updating | Check service logs for errors, verify data fetcher working          |
| Service crashes on startup    | Verify database connection config, check Python dependencies        |

## 📈 Performance Metrics

**Expected**:

- Query speed: < 50ms for recent data
- Update frequency: Every 60 seconds
- Database growth: ~100KB per day
- Memory usage: +50MB for session tracking
- Service runs 24/7 without restart

## 🎯 Next Features

**Priority 1** (Critical):

- [ ] Dashboard UI showing session data
- [ ] Real-time sweep alerts (WebSocket)
- [ ] Session-level AMDX/XAMD classification

**Priority 2** (Important):

- [ ] Historical sweep pattern analysis
- [ ] Machine learning for fake move prediction
- [ ] Multi-timeframe level clustering

**Priority 3** (Nice to Have):

- [ ] Session replay functionality
- [ ] Automated entry signals based on sweeps
- [ ] Performance analytics (win rate per session)

## 📚 Documentation Files

| File                                         | Purpose                        |
| -------------------------------------------- | ------------------------------ |
| `SESSION_CYCLE_TRACKING_GUIDE.md`            | Complete implementation guide  |
| `SESSION_TRACKING_TEST_PLAN.md`              | Testing procedures             |
| `SESSION_TRACKING_QUICK_REF.md`              | This file - quick reference    |
| `QUARTERLY_THEORY_IMPLEMENTATION_SUMMARY.md` | Original quarterly theory docs |

## 🔗 Related Systems

**Integrates with**:

- Quarterly Theory Engine (daily cycle determination)
- Pattern Library (signal confidence adjustment)
- Database Manager (TimescaleDB writes)
- Data Fetcher (real-time price updates)

**Used by** (future):

- Dashboard UI (visualization)
- Alert System (sweep notifications)
- Backtesting Engine (historical analysis)
- Signal Generator (entry timing)

---

## ⚡ TL;DR

**What**: Session-level tracking with liquidity sweep detection
**Why**: Identify manipulation patterns (fake moves) for better entries
**How**: Monitor session highs/lows every 60s, detect sweeps, check for reversals
**Result**: Database tables (`session_cycles`, `liquidity_sweeps`) with real-time tracking

**Key Benefit**: Know when a level sweep is manipulation (fake) vs breakout (real) within 2-5 minutes

**To Deploy**:

1. Run schema SQL file
2. Start service
3. Monitor logs
4. Query `v_recent_liquidity_sweeps` for results

**To Use**:

```sql
-- Get recent fake moves
SELECT * FROM v_recent_liquidity_sweeps
WHERE reversal_detected = TRUE;

-- Get session highs/lows
SELECT * FROM v_session_key_levels;
```

**Status**: ✅ Implementation complete, ready for testing
