# Quarterly Theory Analysis Service

## Overview

The Quarterly Theory Analysis Service is a Python backend that analyzes BookMap trading data (Absorption, Stops/Icebergs, MBO) to determine AMDX vs XAMD cycles and provide real-time phase tracking for the NQ (Nasdaq futures) instrument.

## Core Functionality

### 1. Pre-9:45 AM Determination

**Goal**: Determine whether the trading day will follow an AMDX or XAMD profile before 9:45 AM EST.

**Process**:

- Analyzes Asia session (6 PM - 12 AM EST) for Accumulation vs Expansion characteristics
- Analyzes London session (12 AM - 6 AM EST) for confirmation
- Analyzes Pre-NY session (7:30 AM - 9:30 AM EST) for validation
- Combines all three sessions to determine cycle type with confidence score
- Writes results to `quarterly_cycles` table

**Output Example**:

```
Daily Cycle: AMDX ✓ (87% confidence)
Current Quarter: Q2 (Manipulation)
Phase Status: MANIPULATION ACTIVE - Liquidity sweep in progress
Time to Next Quarter: Q3 expected at 12:00 PM (45 minutes)
Actionable Insight: Wait for manipulation sweep completion. Look for distribution entries in Q3 after True Open.
Bias: BULLISH (price in discount zone, accumulation showed strength)
Entry Window: NOT YET OPEN - Wait for Q3
```

### 2. Real-Time Phase Tracking

**Goal**: Track quarter and phase transitions every 60 seconds during active trading hours (7:30 AM - 8 PM EST).

**Process**:

- Determines current quarter based on time windows and price action
- Identifies phase within quarter (Accumulation, Manipulation, Distribution, Continuation)
- Detects phase transition triggers (displacement, liquidity sweep, time window end)
- Calculates entry window status (CLOSED, OPENING, OPEN, OPTIMAL, CLOSING)
- Writes updates to `session_bias` table

**Phases Explained**:

#### AMDX Profile

- **Q1 (12 AM - 6 AM)**: Accumulation - Two-sided flow, balanced absorption, range building
- **Q2 (6 AM - 12 PM)**: Manipulation - Liquidity sweeps, fake moves, stop runs
- **Q3 (12 PM - 6 PM)**: Distribution - Real move confirmed, directional flow, **ENTRY WINDOW**
- **Q4 (6 PM - 12 AM)**: Continuation - Trend extension or consolidation

#### XAMD Profile

- **Q1 (12 AM - 6 AM)**: Continuation - Expansion from previous day
- **Q2 (6 AM - 12 PM)**: Accumulation - Consolidation, range building
- **Q3 (12 PM - 6 PM)**: Manipulation - Liquidity sweeps, fake moves
- **Q4 (6 PM - 12 AM)**: Distribution - Real move confirmed, **ENTRY WINDOW**

### 3. Fake vs Real Move Detection

**Goal**: Classify moves as FAKE (manipulation) or REAL (distribution) based on quarterly context.

**Indicators**:

- **Fake Move**: Occurs during Q2 Manipulation phase. Characteristics: Liquidity sweep, stops triggered with immediate reversal, no displacement, absorption appears then disappears
- **Real Move**: Occurs during Q3 Distribution phase. Characteristics: Displacement (>50 ticks in <5 min), FVG creation, directional absorption (>60% one side), aggressive orders >70%, iceberg stacking

**Flags Written to Database**:

- `fake_move_detected` (BOOLEAN) - Set to TRUE during Q2 manipulation
- `real_move_confirmed` (BOOLEAN) - Set to TRUE during Q3 distribution with displacement

## Architecture

### Components

```
quarterly_theory_engine.py
├── DatabaseManager - TimescaleDB connection management
├── RedisManager - Redis connection for real-time data
├── DataFetcher - Fetches absorption, stops, icebergs, MBO data
└── Time window definitions (Q1, Q2, Q3, Q4)

quarterly_analysis_core.py
├── SessionAnalyzer - Analyzes Asia/London/Pre-NY sessions
├── CycleDeterminator - Determines AMDX vs XAMD with confidence
└── PhaseTracker - Tracks real-time phase within quarters

quarterly_service.py
├── QuarterlyDatabaseWriter - Writes results to TimescaleDB tables
└── QuarterlyTheoryService - Main orchestrator
    ├── run_pre_market_determination() - 9:00-9:45 AM
    └── run_realtime_tracking() - Every 60 seconds during active hours

start_service.py
└── Launcher with configuration loading and logging setup
```

### Database Tables

**quarterly_cycles** - Daily cycle determinations

- `timestamp`, `symbol`, `timeframe`, `cycle_type` (AMDX/XAMD)
- `current_quarter` (Q1/Q2/Q3/Q4), `quarter_phase`, `confidence_score`
- `supporting_evidence` (JSONB with session analysis)

**phase_transitions** - Logs quarter/phase changes

- `timestamp`, `from_quarter`, `to_quarter`, `from_phase`, `to_phase`
- `transition_trigger` (DISPLACEMENT_DETECTED, LIQUIDITY_SWEEP, TIME_WINDOW_END, etc.)
- `price_at_transition`, `supporting_data` (JSONB)

**htf_bias** - Higher timeframe bias (weekly, daily)

- `timestamp`, `timeframe`, `bias` (BULLISH/BEARISH/NEUTRAL), `confidence_score`
- `key_levels` (JSONB with premium/discount zones), `market_structure` (JSONB)
- `valid_until`, `is_active`

**session_bias** - Intraday session tracking

- `timestamp`, `session` (LONDON/NY_AM/NY_PM), `bias`, `confidence_score`
- `current_quarter`, `quarter_phase`, `entry_window_status`
- `fake_move_detected`, `real_move_confirmed`
- `premium_zone_high`, `discount_zone_low`, `fair_value`, `current_price_zone`

## Installation

### Prerequisites

- Python 3.8+
- TimescaleDB with quarterly theory schema installed
- Redis running
- BookMap consumers (Absorption, Stops/Icebergs, MBO) actively writing data

### Step 1: Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**requirements.txt**:

```
psycopg2-binary>=2.9.0
redis>=4.0.0
pytz>=2021.3
numpy>=1.20.0
asyncio
```

### Step 2: Initialize Database Schema

```bash
psql -U postgres -d bookmap_data -f ../database/quarterly_theory_schema.sql
```

### Step 3: Configure Service

```bash
# Copy template
cp config_template.ini config.ini

# Edit config.ini with your database credentials
notepad config.ini
```

**config.ini** (update these values):

```ini
[database]
host = localhost
port = 5432
database = bookmap_data
user = postgres
password = YOUR_PASSWORD_HERE

[redis]
host = localhost
port = 6379
db = 0
```

### Step 4: Start Service

```bash
python start_service.py
```

**Expected Output**:

```
============================================================
Quarterly Theory Analysis Service
============================================================

[1/3] Loading configuration...
✓ Configuration loaded
  - Database: localhost:5432
  - Redis: localhost:6379
  - Symbol: NQ

[2/3] Setting up logging...
✓ Logging initialized
  - Log file: logs/quarterly_service.log

[3/3] Starting service...
✓ Service initialized

============================================================
Service running. Press Ctrl+C to stop.
============================================================

2025-01-29 09:15:30 - INFO - Starting Pre-9:45 AM Cycle Determination
2025-01-29 09:15:35 - INFO - Analyzing ASIA session: 2025-01-28 18:00:00 to 2025-01-29 00:00:00
2025-01-29 09:15:38 - INFO - Analyzing LONDON session: 2025-01-29 00:00:00 to 2025-01-29 06:00:00
2025-01-29 09:15:41 - INFO - Analyzing PRE_NY session: 2025-01-29 07:30:00 to 2025-01-29 09:30:00
2025-01-29 09:15:45 - INFO - Daily Cycle: AMDX ✓ (87.3% confidence)
```

## Usage Patterns

### Pattern 1: Morning Routine (8:00 AM - 9:45 AM)

1. Service auto-runs pre-market determination between 9:00-9:45 AM
2. Analyzes overnight sessions (Asia, London, Pre-NY)
3. Determines AMDX or XAMD with confidence score
4. Writes to `quarterly_cycles` table
5. Dashboard queries this table to display cycle type

### Pattern 2: Real-Time Monitoring (During Trading Hours)

1. Service runs every 60 seconds from 7:30 AM to 8:00 PM EST
2. Tracks current quarter and phase
3. Detects phase transitions (writes to `phase_transitions` table)
4. Updates entry window status (writes to `session_bias` table)
5. Dashboard queries `session_bias` for real-time display

### Pattern 3: Signal Enhancement (Integration with Pattern Library)

1. Dashboard receives absorption event from consumer
2. Queries `session_bias` for current quarter and phase
3. If Q2 Manipulation + absorption appears/disappears → classify as FAKE
4. If Q3 Distribution + absorption sustained + displacement → classify as REAL
5. Adjusts confidence score: +20 if aligned with optimal quarter, -30 if in Q2

## API Endpoints (Future Enhancement)

The service writes to database tables that can be queried by API endpoints:

### GET /api/quarterly/current-cycle

**Response**:

```json
{
  "date": "2025-01-29",
  "cycle_type": "AMDX",
  "confidence": 87.3,
  "current_quarter": "Q2",
  "quarter_phase": "MANIPULATION",
  "determination_time": "2025-01-29T09:15:45-05:00"
}
```

### GET /api/quarterly/phase-status

**Response**:

```json
{
  "quarter": "Q2",
  "phase": "MANIPULATION",
  "confidence": 85.2,
  "triggers_active": ["LIQUIDITY_SWEEP"],
  "status_message": "MANIPULATION phase (Q2) ACTIVE. Liquidity sweep in progress. DO NOT CHASE - Let fake move complete.",
  "timestamp": "2025-01-29T10:30:15-05:00"
}
```

### GET /api/quarterly/entry-window

**Response**:

```json
{
  "status": "CLOSED",
  "reason": "Currently in Q2 Manipulation - Entry window opens in Q3 at 12:00 PM",
  "minutes_until_open": 90,
  "fake_move_detected": true,
  "real_move_confirmed": false,
  "recommendation": "DO NOT TRADE - Manipulation phase active. Wait for real move in opposite direction."
}
```

## Troubleshooting

### Issue: "No cycle type determined yet"

**Cause**: Service hasn't run pre-market determination or it's before 9:00 AM.
**Solution**: Wait until 9:00 AM or manually query database for previous determination.

### Issue: "Database connection failed"

**Cause**: TimescaleDB not running or incorrect credentials.
**Solution**:

```bash
# Check if PostgreSQL is running
psql -U postgres -d bookmap_data

# Verify quarterly theory schema exists
\dt quarterly_*
```

### Issue: "Redis connection failed"

**Cause**: Redis not running.
**Solution**:

```bash
# Start Redis
redis-server

# Test connection
redis-cli ping
# Should return: PONG
```

### Issue: "No data returned from consumers"

**Cause**: BookMap consumers not running or not writing to database.
**Solution**:

- Verify Absorption Consumer is active in BookMap
- Check TimescaleDB for recent data:

```sql
SELECT COUNT(*) FROM absorption_events WHERE timestamp > NOW() - INTERVAL '1 hour';
SELECT COUNT(*) FROM stops_icebergs_events WHERE timestamp > NOW() - INTERVAL '1 hour';
```

## Performance Considerations

- **Database Queries**: Service queries last 5 minutes of data for real-time analysis. Uses TimescaleDB compression for older data (>7 days).
- **Update Frequency**: 60-second interval balances real-time responsiveness with system load.
- **Memory Usage**: ~100-200 MB for service + data structures.
- **CPU Usage**: Minimal - mostly I/O bound (database queries).

## Testing

### Manual Test: Pre-Market Determination

```python
# Run this between 9:00-9:45 AM to test determination
python -c "
import asyncio
from quarterly_service import QuarterlyTheoryService

async def test():
    service = QuarterlyTheoryService(db_config, redis_config)
    result = await service.run_pre_market_determination()
    print(result)

asyncio.run(test())
"
```

### Manual Test: Real-Time Tracking

```sql
-- Query latest session bias
SELECT
    timestamp,
    session,
    current_quarter,
    quarter_phase,
    entry_window_status,
    fake_move_detected,
    real_move_confirmed
FROM session_bias
WHERE symbol = 'NQ'
ORDER BY timestamp DESC
LIMIT 5;
```

## Integration with Dashboard

The React dashboard should query these tables every 60 seconds:

**Dashboard Query Pattern**:

```javascript
// Fetch current cycle
const cycle = await fetch("/api/quarterly/current-cycle").then((r) => r.json());

// Fetch phase status
const phase = await fetch("/api/quarterly/phase-status").then((r) => r.json());

// Fetch entry window
const entry = await fetch("/api/quarterly/entry-window").then((r) => r.json());

// Display in UI
<QuarterlyTheoryPanel
  cycleType={cycle.cycle_type}
  confidence={cycle.confidence}
  currentQuarter={cycle.current_quarter}
  phase={phase.phase}
  entryWindowStatus={entry.status}
  recommendation={entry.recommendation}
/>;
```

## Future Enhancements

1. **Backtesting Mode**: Run service on historical data to validate accuracy
2. **Pattern Library Integration**: Directly connect with fake/real pattern detection
3. **Machine Learning**: Train model on historical cycles to improve confidence scores
4. **Multi-Timeframe Analysis**: Track weekly cycles in addition to daily
5. **Alert System**: Send notifications when entry window opens
6. **Performance Metrics**: Track determination accuracy over time

## License

Part of the brapi-demo-consumer project. Internal use only.

## Contact

For issues or questions, refer to main project documentation in `../README.md`.
