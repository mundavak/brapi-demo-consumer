# Quarterly Theory Service - Quick Start Guide

## 5-Minute Setup

### Prerequisites Check

```powershell
# 1. TimescaleDB running?
psql -U postgres -d bookmap_data -c "SELECT version();"

# 2. Redis running?
redis-cli ping

# 3. BookMap consumers active?
psql -U postgres -d bookmap_data -c "SELECT COUNT(*) FROM absorption_events WHERE timestamp > NOW() - INTERVAL '1 hour';"
```

### Installation (3 Steps)

#### Step 1: Database Schema (2 minutes)

```powershell
cd F:\TradingAgent\deaProjects\brapi-demo-consumer
psql -U postgres -d bookmap_data -f database\quarterly_theory_schema.sql
```

**Verify**:

```sql
\dt quarterly_*
-- Should show 4 tables: quarterly_cycles, phase_transitions, htf_bias, session_bias
```

#### Step 2: Python Setup (2 minutes)

```powershell
cd backend

# Create venv
python -m venv venv

# Activate
venv\Scripts\activate

# Install
pip install -r requirements.txt
```

#### Step 3: Configuration (1 minute)

```powershell
# Copy template
cp config_template.ini config.ini

# Edit password only
notepad config.ini
# Change: password = your_password_here
```

### Launch

```powershell
python start_service.py
```

**Expected Output**:

```
============================================================
Quarterly Theory Analysis Service
============================================================

[1/3] Loading configuration...
✓ Configuration loaded

[2/3] Setting up logging...
✓ Logging initialized

[3/3] Starting service...
✓ Service initialized

============================================================
Service running. Press Ctrl+C to stop.
============================================================
```

## Daily Operation

### Morning (9:00-9:45 AM)

Service automatically determines AMDX vs XAMD cycle.

**Check Results**:

```sql
SELECT
    cycle_type,
    confidence_score,
    current_quarter,
    quarter_phase,
    supporting_evidence->>'reasoning' as reasoning
FROM quarterly_cycles
WHERE timestamp::date = CURRENT_DATE
ORDER BY timestamp DESC
LIMIT 1;
```

**Example Output**:

```
cycle_type | confidence_score | current_quarter | quarter_phase | reasoning
-----------+------------------+-----------------+---------------+----------
AMDX       | 87.30            | Q2              | MANIPULATION  | Asia ACCUMULATION (78%), London ACCUMULATION (82%) → AMDX Q1 Accumulation starting
```

### During Trading Hours (7:30 AM - 8:00 PM)

Service tracks phase every 60 seconds.

**Check Real-Time Status**:

```sql
SELECT
    timestamp,
    session,
    current_quarter,
    quarter_phase,
    entry_window_status,
    fake_move_detected,
    real_move_confirmed,
    entry_recommendation
FROM session_bias
WHERE symbol = 'NQ'
ORDER BY timestamp DESC
LIMIT 1;
```

**Example Output**:

```
timestamp           | session | current_quarter | quarter_phase | entry_window_status | fake_move | real_move | recommendation
--------------------+---------+-----------------+---------------+---------------------+-----------+-----------+---------------
2025-01-29 10:30:15 | NY_AM   | Q2              | MANIPULATION  | CLOSED              | TRUE      | FALSE     | DO NOT TRADE - Manipulation phase active. Wait for real move in opposite direction.
```

### Phase Transitions

**Check Recent Transitions**:

```sql
SELECT * FROM v_recent_phase_transitions ORDER BY timestamp DESC LIMIT 5;
```

## Troubleshooting

### Issue: No data in quarterly_cycles

**Cause**: Service hasn't run pre-market determination yet.
**Solution**: Wait until 9:00 AM or check service is running.

### Issue: Service crashes on startup

**Cause**: Database connection failed.
**Solution**:

```powershell
# Check database credentials
psql -U postgres -d bookmap_data

# Update config.ini with correct password
```

### Issue: No session_bias updates

**Cause**: No consumer data available.
**Solution**:

```sql
-- Check if consumers are writing data
SELECT
    'absorption' as source, COUNT(*) as count FROM absorption_events WHERE timestamp > NOW() - INTERVAL '1 hour'
UNION ALL
SELECT 'stops', COUNT(*) FROM stops_icebergs_events WHERE timestamp > NOW() - INTERVAL '1 hour'
UNION ALL
SELECT 'mbo', COUNT(*) FROM mbo_events WHERE timestamp > NOW() - INTERVAL '1 hour';
```

## Service Management

### Stop Service

Press `Ctrl+C` in the terminal.

### Restart Service

```powershell
python start_service.py
```

### Check Logs

```powershell
tail -f logs\quarterly_service.log  # Linux/Git Bash
Get-Content logs\quarterly_service.log -Tail 20 -Wait  # PowerShell
```

### Run as Background Service (Windows)

```powershell
# Option 1: NSSM (Non-Sucking Service Manager)
nssm install QuarterlyTheoryService "F:\TradingAgent\deaProjects\brapi-demo-consumer\backend\venv\Scripts\python.exe" "F:\TradingAgent\deaProjects\brapi-demo-consumer\backend\start_service.py"

# Option 2: Task Scheduler
# Create task that runs at system startup:
# Program: F:\TradingAgent\deaProjects\brapi-demo-consumer\backend\venv\Scripts\python.exe
# Arguments: start_service.py
# Start in: F:\TradingAgent\deaProjects\brapi-demo-consumer\backend
```

## Dashboard Integration Queries

### Get Current Cycle (Every 60 seconds)

```javascript
const response = await fetch("/api/quarterly/current-cycle");
// Query: SELECT * FROM quarterly_cycles WHERE timeframe='daily' ORDER BY timestamp DESC LIMIT 1;
```

### Get Phase Status (Every 60 seconds)

```javascript
const response = await fetch("/api/quarterly/phase-status");
// Query: SELECT * FROM session_bias ORDER BY timestamp DESC LIMIT 1;
```

### Get Entry Window (Every 60 seconds)

```javascript
const response = await fetch("/api/quarterly/entry-window");
// Query: SELECT entry_window_status, fake_move_detected, real_move_confirmed, entry_recommendation FROM session_bias ORDER BY timestamp DESC LIMIT 1;
```

## Performance Monitoring

### Check Service Health

```sql
-- Records written in last hour
SELECT 'session_bias' as table_name, COUNT(*) as records
FROM session_bias
WHERE timestamp > NOW() - INTERVAL '1 hour'
UNION ALL
SELECT 'phase_transitions', COUNT(*)
FROM phase_transitions
WHERE timestamp > NOW() - INTERVAL '1 hour';

-- Expected: ~60 session_bias records per hour (1 per minute)
-- Expected: 0-4 phase_transitions per hour (only on quarter changes)
```

### Check Determination Accuracy (Manual Validation)

```sql
-- Compare morning determination vs actual Q3 characteristics
SELECT
    qc.timestamp as determination_time,
    qc.cycle_type as predicted_cycle,
    qc.confidence_score as confidence,
    sb.current_quarter,
    sb.quarter_phase,
    sb.real_move_confirmed
FROM quarterly_cycles qc
LEFT JOIN session_bias sb ON sb.timestamp::date = qc.timestamp::date
WHERE qc.timestamp::date = CURRENT_DATE
AND qc.timeframe = 'daily'
AND sb.current_quarter = 'Q3'
ORDER BY sb.timestamp DESC
LIMIT 1;

-- Validation:
-- If predicted AMDX: Q3 should show DISTRIBUTION with real_move_confirmed=TRUE
-- If predicted XAMD: Q3 should show MANIPULATION with fake_move_detected=TRUE
```

## Useful Queries

### Today's Timeline

```sql
SELECT
    TO_CHAR(timestamp, 'HH24:MI:SS') as time,
    current_quarter,
    quarter_phase,
    entry_window_status,
    CASE WHEN fake_move_detected THEN '⚠️ FAKE' WHEN real_move_confirmed THEN '✅ REAL' ELSE '' END as move_type
FROM session_bias
WHERE timestamp::date = CURRENT_DATE
ORDER BY timestamp ASC;
```

### Phase Duration Stats

```sql
SELECT * FROM get_phase_duration_stats('daily', 30);
-- Shows average duration of each phase over last 30 days
```

### Entry Window History

```sql
SELECT
    timestamp::date as date,
    COUNT(*) FILTER (WHERE entry_window_status = 'OPTIMAL') as optimal_minutes,
    COUNT(*) FILTER (WHERE entry_window_status = 'OPEN') as open_minutes,
    COUNT(*) FILTER (WHERE entry_window_status = 'CLOSED') as closed_minutes
FROM session_bias
WHERE timestamp > CURRENT_DATE - INTERVAL '7 days'
GROUP BY date
ORDER BY date DESC;
```

## Contact & Support

For issues or questions:

1. Check logs: `logs/quarterly_service.log`
2. Review documentation: `README_QUARTERLY_SERVICE.md`
3. Verify data flow: Run queries above
4. Check main project README: `../README.md`

---

**Quick Reference Card** (Print This):

```
┌─────────────────────────────────────────────────────────┐
│ QUARTERLY THEORY SERVICE - CHEAT SHEET                  │
├─────────────────────────────────────────────────────────┤
│ START:    python start_service.py                       │
│ STOP:     Ctrl+C                                        │
│ LOGS:     logs\quarterly_service.log                    │
│                                                          │
│ AMDX PROFILE:                                           │
│   Q1: Accumulation → Q2: Manipulation → Q3: Distribution│
│   ENTRY WINDOW: Q3 (Distribution) & Q4 (Continuation)   │
│                                                          │
│ XAMD PROFILE:                                           │
│   Q1: Continuation → Q2: Accumulation → Q3: Manipulation│
│   ENTRY WINDOW: Q4 (Distribution)                       │
│                                                          │
│ DETERMINATION: 9:00-9:45 AM (auto)                      │
│ TRACKING: Every 60 sec during 7:30 AM - 8:00 PM        │
│                                                          │
│ FAKE MOVE: Q2 Manipulation + Liquidity Sweep           │
│ REAL MOVE: Q3 Distribution + Displacement               │
│                                                          │
│ CHECK STATUS:                                           │
│   SELECT * FROM session_bias                            │
│   ORDER BY timestamp DESC LIMIT 1;                      │
└─────────────────────────────────────────────────────────┘
```
