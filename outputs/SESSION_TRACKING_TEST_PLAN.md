# Session Cycle Tracking - Test Plan

## Pre-Deployment Checklist

### 1. Database Schema Migration

```powershell
# Apply schema updates to database
psql -U postgres -d bookmap_data -f database/quarterly_theory_schema.sql

# Verify tables created
psql -U postgres -d bookmap_data
```

```sql
-- Check tables exist
\dt session_cycles
\dt liquidity_sweeps

-- Expected output:
-- public | session_cycles    | table | postgres
-- public | liquidity_sweeps  | table | postgres

-- Check views exist
\dv v_current_session_cycles
\dv v_recent_liquidity_sweeps
\dv v_session_key_levels

-- Check functions exist
\df detect_liquidity_sweep
\df get_key_levels_for_sweep

-- Verify table structure
\d session_cycles
-- Should show: session, session_high/low, q1-q4 highs/lows, liquidity_sweeps JSONB, etc.

\d liquidity_sweeps
-- Should show: sweep_type, level_price, reversal_detected, is_fake_move, etc.
```

### 2. Python Module Imports

```bash
cd backend
python -c "from session_cycle_tracker import SessionCycleTracker; print('✅ Import successful')"
python -c "from quarterly_service import QuarterlyTheoryService; print('✅ Service import successful')"
```

### 3. Configuration Verification

```bash
# Check database connection config
cat config/database_config.properties

# Expected:
# db.host=localhost
# db.port=5432
# db.name=bookmap_data
# db.user=postgres
# db.password=<your_password>
```

## Unit Tests

### Test 1: Session Initialization

**Objective**: Verify SessionCycleTracker creates session state correctly

```python
# backend/test_session_tracker.py
from session_cycle_tracker import SessionCycleTracker, SESSION_DEFINITIONS
from datetime import datetime
import pytz

EST = pytz.timezone('US/Eastern')

def test_initialize_session():
    # Mock dependencies
    db_manager = MockDBManager()
    data_fetcher = MockDataFetcher(initial_price=18450.00)

    tracker = SessionCycleTracker(db_manager, data_fetcher)

    # Initialize London session
    test_time = datetime(2025, 10, 30, 2, 0, 0, tzinfo=EST)  # 2 AM EST
    tracker.initialize_session('LONDON', test_time)

    state = tracker.session_states['LONDON']

    # Assertions
    assert state.session == 'LONDON'
    assert state.session_start.hour == 0  # London starts 00:00
    assert state.session_end.hour == 6    # London ends 06:00
    assert state.session_open == 18450.00
    assert state.session_high == 18450.00
    assert state.session_low == 18450.00
    assert state.is_completed == False

    print("✅ Test 1 PASSED: Session initialization")

test_initialize_session()
```

### Test 2: High/Low Tracking

**Objective**: Verify highs/lows update correctly

```python
def test_update_high_low():
    tracker = SessionCycleTracker(MockDBManager(), MockDataFetcher())
    tracker.initialize_session('LONDON', datetime.now(EST))

    # Update with higher price
    tracker.update_session_high_low('LONDON', datetime.now(EST), 18460.00)
    state = tracker.session_states['LONDON']
    assert state.session_high == 18460.00

    # Update with lower price
    tracker.update_session_high_low('LONDON', datetime.now(EST), 18430.00)
    assert state.session_low == 18430.00

    # Update with middle price (no change)
    tracker.update_session_high_low('LONDON', datetime.now(EST), 18445.00)
    assert state.session_high == 18460.00  # Unchanged
    assert state.session_low == 18430.00   # Unchanged

    print("✅ Test 2 PASSED: High/Low tracking")

test_update_high_low()
```

### Test 3: Quarter Determination

**Objective**: Verify quarter logic for each session

```python
def test_determine_quarter():
    tracker = SessionCycleTracker(MockDBManager(), MockDataFetcher())

    # Test LONDON quarters
    assert tracker._determine_quarter('LONDON', datetime(2025, 10, 30, 0, 30, 0, tzinfo=EST)) == 'Q1'  # 00:30
    assert tracker._determine_quarter('LONDON', datetime(2025, 10, 30, 2, 0, 0, tzinfo=EST)) == 'Q2'   # 02:00
    assert tracker._determine_quarter('LONDON', datetime(2025, 10, 30, 4, 0, 0, tzinfo=EST)) == 'Q3'   # 04:00
    assert tracker._determine_quarter('LONDON', datetime(2025, 10, 30, 5, 30, 0, tzinfo=EST)) == 'Q4'  # 05:30

    # Test NY_AM quarters
    assert tracker._determine_quarter('NY_AM', datetime(2025, 10, 30, 8, 0, 0, tzinfo=EST)) == 'Q1'    # 08:00
    assert tracker._determine_quarter('NY_AM', datetime(2025, 10, 30, 10, 0, 0, tzinfo=EST)) == 'Q2'   # 10:00
    assert tracker._determine_quarter('NY_AM', datetime(2025, 10, 30, 11, 30, 0, tzinfo=EST)) == 'Q3'  # 11:30
    assert tracker._determine_quarter('NY_AM', datetime(2025, 10, 30, 13, 0, 0, tzinfo=EST)) == 'Q4'   # 13:00

    print("✅ Test 3 PASSED: Quarter determination")

test_determine_quarter()
```

### Test 4: Liquidity Sweep Detection

**Objective**: Verify sweep detection with tolerance

```python
def test_liquidity_sweep_detection():
    db_manager = MockDBManager()
    tracker = SessionCycleTracker(db_manager, MockDataFetcher())
    tracker.initialize_session('LONDON', datetime.now(EST))

    # Mock key levels
    tracker.key_levels_cache[(datetime.now(EST).date(), 'NQ')] = [
        {'name': 'ASIA_HIGH', 'price': 18450.00, 'type': 'SESSION_HIGH'}
    ]

    # Price 1 tick beyond (not confirmed - within tolerance)
    tracker.detect_liquidity_sweeps('LONDON', datetime.now(EST), 18450.25)
    assert len(tracker.session_states['LONDON'].liquidity_sweeps) == 0

    # Price 4 ticks beyond (confirmed - outside tolerance)
    tracker.detect_liquidity_sweeps('LONDON', datetime.now(EST), 18451.00)
    assert len(tracker.session_states['LONDON'].liquidity_sweeps) == 1
    assert tracker.session_states['LONDON'].liquidity_sweeps[0]['level_name'] == 'ASIA_HIGH'
    assert tracker.session_states['LONDON'].liquidity_sweeps[0]['confirmed'] == True

    print("✅ Test 4 PASSED: Liquidity sweep detection")

test_liquidity_sweep_detection()
```

### Test 5: Reversal Detection (Fake Move)

**Objective**: Verify reversal detection after sweep

```python
def test_reversal_detection():
    db_manager = MockDBManager()
    tracker = SessionCycleTracker(db_manager, MockDataFetcher())
    tracker.initialize_session('LONDON', datetime.now(EST))

    # Create sweep event
    sweep_time = datetime.now(EST)
    tracker.session_states['LONDON'].liquidity_sweeps.append({
        'timestamp': sweep_time.isoformat(),
        'level_name': 'ASIA_HIGH',
        'level_price': 18450.00,
        'sweep_price': 18451.00,
        'ticks_beyond': 4,
        'confirmed': True,
        'reversal_checked': False
    })

    # Check reversal (price dropped 10 ticks within 3 minutes)
    reversal_time = sweep_time + timedelta(minutes=3)
    reversal_price = 18448.50  # 10 ticks down from 18451

    tracker.check_reversal_after_sweep('LONDON', reversal_time, reversal_price)

    state = tracker.session_states['LONDON']
    assert state.manipulation_detected == True
    assert state.reversal_after_sweep == True

    # Verify database update was called
    assert db_manager.update_sweep_reversal_called == True

    print("✅ Test 5 PASSED: Reversal detection")

test_reversal_detection()
```

## Integration Tests

### Test 6: Service Loop Integration

**Objective**: Verify session tracking integrates with quarterly service

```python
# backend/test_integration.py
from quarterly_service import QuarterlyTheoryService
from datetime import datetime
import pytz

EST = pytz.timezone('US/Eastern')

async def test_service_integration():
    service = QuarterlyTheoryService()

    # Simulate London session time (2 AM EST)
    test_time = datetime(2025, 10, 30, 2, 0, 0, tzinfo=EST)

    # Override current time (mock)
    service._get_current_time = lambda: test_time

    # Run one iteration
    await service.run_realtime_tracking()

    # Verify session initialized
    assert service.current_session == 'LONDON'
    assert 'LONDON' in service.session_tracker.session_states

    # Verify session high/low updated
    state = service.session_tracker.session_states['LONDON']
    assert state.session_high is not None
    assert state.session_low is not None

    print("✅ Test 6 PASSED: Service integration")

import asyncio
asyncio.run(test_service_integration())
```

### Test 7: Session Transition

**Objective**: Verify session completes and new session starts

```python
async def test_session_transition():
    service = QuarterlyTheoryService()

    # Start in London (2 AM)
    london_time = datetime(2025, 10, 30, 2, 0, 0, tzinfo=EST)
    service._get_current_time = lambda: london_time
    await service.run_realtime_tracking()

    assert service.current_session == 'LONDON'
    london_state = service.session_tracker.session_states['LONDON']
    assert london_state.is_completed == False

    # Transition to NY_AM (8 AM)
    ny_am_time = datetime(2025, 10, 30, 8, 0, 0, tzinfo=EST)
    service._get_current_time = lambda: ny_am_time
    await service.run_realtime_tracking()

    assert service.current_session == 'NY_AM'

    # Verify London session completed
    assert london_state.is_completed == True

    # Verify NY_AM session initialized
    assert 'NY_AM' in service.session_tracker.session_states
    ny_am_state = service.session_tracker.session_states['NY_AM']
    assert ny_am_state.is_completed == False

    print("✅ Test 7 PASSED: Session transition")

asyncio.run(test_session_transition())
```

## Live Testing

### Test 8: Database Write Verification

**Steps**:

1. Start service during active session (after 6 PM for Asia)
2. Wait 5 minutes
3. Check database for session data

```sql
-- Check session_cycles table
SELECT
    session,
    session_start,
    session_end,
    session_high,
    session_low,
    current_quarter,
    is_completed,
    updated_at
FROM session_cycles
WHERE timestamp::date = CURRENT_DATE
ORDER BY session_start DESC;

-- Expected: 1 row with current session, is_completed=FALSE, updated_at recent

-- Check session high/low updating
-- Wait 2 minutes and re-query - updated_at should change
```

### Test 9: Liquidity Sweep Recording

**Steps**:

1. Note current price and session high
2. Wait for price to exceed session high by 4+ ticks
3. Check liquidity_sweeps table

```sql
-- Check sweeps detected
SELECT
    timestamp,
    session,
    sweep_type,
    level_price,
    sweep_price,
    ticks_beyond,
    sweep_confirmed,
    reversal_detected
FROM liquidity_sweeps
WHERE timestamp::date = CURRENT_DATE
ORDER BY timestamp DESC
LIMIT 5;

-- Expected: New row when session high swept, sweep_confirmed=TRUE
```

### Test 10: Reversal Detection

**Steps**:

1. Wait for liquidity sweep to occur
2. Monitor if price reverses within 5 minutes
3. Check reversal flags update

```sql
-- Check for fake moves
SELECT
    ls.timestamp,
    ls.sweep_type,
    ls.level_price,
    ls.sweep_price,
    ls.reversal_detected,
    ls.reversal_time,
    ls.reversal_price,
    ls.is_fake_move,
    EXTRACT(EPOCH FROM (ls.reversal_time - ls.timestamp)) / 60 as reversal_duration_minutes
FROM liquidity_sweeps ls
WHERE timestamp::date = CURRENT_DATE
AND reversal_detected = TRUE;

-- Expected: Row appears if reversal occurs, is_fake_move=TRUE
```

### Test 11: View Functionality

```sql
-- Test v_current_session_cycles
SELECT * FROM v_current_session_cycles;

-- Expected: Shows all sessions from today with completion status

-- Test v_recent_liquidity_sweeps
SELECT * FROM v_recent_liquidity_sweeps;

-- Expected: Shows recent sweeps with move classification (FAKE_MOVE/REAL_MOVE/PENDING)

-- Test v_session_key_levels
SELECT * FROM v_session_key_levels;

-- Expected: Shows asia_high, asia_low, london_high/low, ny_am_high/low, ny_pm_high/low
```

### Test 12: Helper Functions

```sql
-- Test detect_liquidity_sweep function
SELECT detect_liquidity_sweep(
    18451.00,  -- current_price
    18450.00,  -- level_price
    'SESSION_HIGH',  -- sweep_type
    3  -- tolerance_ticks
) as is_sweep;

-- Expected: TRUE (4 ticks beyond = sweep)

-- Test with price within tolerance
SELECT detect_liquidity_sweep(
    18450.50,  -- only 2 ticks beyond
    18450.00,
    'SESSION_HIGH',
    3
) as is_sweep;

-- Expected: FALSE (within tolerance)

-- Test get_key_levels_for_sweep
SELECT * FROM get_key_levels_for_sweep(NOW(), 'NQ');

-- Expected: Returns rows with level names, prices, timestamps, types
```

## Performance Tests

### Test 13: Query Performance

```sql
-- Test session_cycles query speed
EXPLAIN ANALYZE
SELECT * FROM session_cycles
WHERE timestamp > NOW() - INTERVAL '7 days'
AND session = 'LONDON';

-- Expected execution time: < 50ms

-- Test liquidity_sweeps query speed
EXPLAIN ANALYZE
SELECT * FROM liquidity_sweeps
WHERE timestamp > NOW() - INTERVAL '24 hours'
AND reversal_detected = TRUE;

-- Expected execution time: < 50ms
```

### Test 14: Write Performance

**Objective**: Verify service can handle rapid updates (every 60 seconds)

```bash
# Monitor service logs
tail -f backend/logs/quarterly_service.log

# Look for:
# - "Updated LONDON session high" messages every 60 seconds
# - "LIQUIDITY SWEEP DETECTED" messages when sweeps occur
# - No error messages or exceptions
# - Update cycle completes in < 5 seconds
```

## Error Handling Tests

### Test 15: Database Connection Loss

**Steps**:

1. Start service
2. Stop PostgreSQL/TimescaleDB
3. Check service continues (errors logged but doesn't crash)
4. Restart database
5. Verify service reconnects and continues

### Test 16: Invalid Price Data

**Steps**:

1. Mock data fetcher to return None/NaN/inf
2. Verify service handles gracefully (skips update, logs warning)
3. No exceptions thrown

### Test 17: Session Crossing Midnight (Asia)

**Steps**:

1. Start service at 11:55 PM (during Asia session)
2. Wait for midnight rollover
3. Verify session doesn't complete early
4. Verify session_end is next day 00:00

## Validation Checklist

After running all tests, verify:

- [ ] `session_cycles` table has data for current day
- [ ] `session_high` and `session_low` update every 60 seconds
- [ ] `current_quarter` progresses from Q1 → Q2 → Q3 → Q4
- [ ] `liquidity_sweeps` table records sweeps when price exceeds levels
- [ ] `reversal_detected` flag updates within 5 minutes of sweep
- [ ] `is_fake_move` set to TRUE when reversal occurs
- [ ] Session completes and writes to database on session close
- [ ] New session initializes automatically after transition
- [ ] All views return correct data
- [ ] Helper functions work as expected
- [ ] No errors in service logs
- [ ] Service runs for 24+ hours without crashes
- [ ] Database storage grows as expected (~100KB per day)
- [ ] Query performance remains fast (< 100ms)

## Rollback Plan

If issues occur in production:

```sql
-- Remove session tracking tables
DROP TABLE IF EXISTS liquidity_sweeps CASCADE;
DROP TABLE IF EXISTS session_cycles CASCADE;

-- Remove views
DROP VIEW IF EXISTS v_current_session_cycles;
DROP VIEW IF EXISTS v_recent_liquidity_sweeps;
DROP VIEW IF EXISTS v_session_key_levels;

-- Remove functions
DROP FUNCTION IF EXISTS detect_liquidity_sweep;
DROP FUNCTION IF EXISTS get_key_levels_for_sweep;
```

```python
# Rollback code changes
# Comment out session tracking in quarterly_service.py:

# In run_realtime_tracking():
"""
# DISABLED: Session tracking
# new_session = self._determine_current_session(now)
# if new_session != self.current_session:
#     ... (session transition logic)
"""
```

## Success Criteria

✅ **All unit tests pass** (Tests 1-5)
✅ **All integration tests pass** (Tests 6-7)
✅ **Live testing shows data collection** (Tests 8-12)
✅ **Performance acceptable** (Tests 13-14)
✅ **Error handling robust** (Tests 15-17)
✅ **Service runs 24+ hours without issues**
✅ **Database queries fast and accurate**

---

**Next Steps After Testing**:

1. Deploy to production during pre-market hours (before Asia session)
2. Monitor first full day for any issues
3. Validate all 4 sessions complete correctly
4. Build dashboard UI showing session data
5. Add real-time alerts for liquidity sweeps
