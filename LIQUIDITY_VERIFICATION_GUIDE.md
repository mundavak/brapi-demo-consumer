# Liquidity Marker Consumer - Verification Guide

## Overview

LiquidityMarkerConsumer addon captures support/resistance levels from Bookmap's Liquidity Markers indicator and stores them in Redis (hot) + TimescaleDB (cold) for institutional order flow analysis.

## Prerequisites

- ✅ Bookmap 7.6+ installed and running
- ✅ Liquidity Markers indicator installed (providers/modules/7.6.0.1---7.6.1.9999---2---liquidity-marker---0.27)
- ✅ Redis running (localhost:6379)
- ✅ TimescaleDB running (localhost:5432, database: trading_data)
- ✅ JAR built and copied to F:/Bookmap/Python/build/

## Activation Steps

### 1. Restart Bookmap

**Why**: Bookmap doesn't cache addon classes - full restart required to load new addon.

```powershell
# Close Bookmap completely
# Reopen Bookmap
```

### 2. Enable LiquidityMarkerConsumer Addon

1. **Settings → Manage Addons** (or **Settings → API plugins configuration**)
2. Find **"Liquidity Marker Broadcasting Consumer"**
3. Click checkbox to enable
4. Click **Apply** or **OK**

### 3. Add Liquidity Markers Indicator to Chart

1. Open chart with instrument (e.g., MNQZ5.CME@RITHMIC)
2. Right-click chart → **Indicators**
3. Find **"Liquidity Markers"** indicator
4. Click **Add** and configure settings
5. Ensure indicator is **enabled** (green checkmark)

### 4. Add Consumer to Same Chart

1. Right-click chart → **Indicators**
2. Find **"Liquidity Marker Broadcasting Consumer"**
3. Click **Add**
4. Consumer panel should appear with log area

## Verification Steps

### Step 1: Check Startup Logs

Consumer log panel should show:

```
[2025-11-11 XX:XX:XX] [INFO] ========================================
[2025-11-11 XX:XX:XX] [INFO] Liquidity Marker Broadcasting Consumer: STARTING UP
[2025-11-11 XX:XX:XX] [INFO] ========================================
[2025-11-11 XX:XX:XX] [INFO] LiquidityMarkerConsumer: Broadcaster created (waiting for chain creation)
[2025-11-11 XX:XX:XX] [INFO] Log file: F:/Databases/Logs/liquidity_consumer.log
[2025-11-11 XX:XX:XX] [INFO] Redis: Hot storage enabled
[2025-11-11 XX:XX:XX] [INFO] TimescaleDB: Cold storage enabled (batch writes every 5 seconds)
[2025-11-11 XX:XX:XX] [INFO] ========================================
[2025-11-11 XX:XX:XX] [INFO] Broadcaster STARTED - Now listening for Liquidity events
[2025-11-11 XX:XX:XX] [INFO] ========================================
[2025-11-11 XX:XX:XX] [INFO] Connecting to Liquidity Markers provider...
```

### Step 2: Connection Verification (10 seconds)

Within 10 seconds, you should see:

```
[INFO] ✓ Successfully connected to Liquidity Markers
[INFO] Found X generator(s)
[INFO] Subscribing to generator: [generator_name]
[INFO] ✓ Successfully subscribed to live data: [generator_name]
```

### Step 3: First Event Verification (30 seconds)

Within 30 seconds of market activity, you should see:

```
[INFO] First event class: [full_class_name]
[INFO] Event package: [package_name]
[INFO] ✓ First liquidity event received - feed is active!
[INFO] ===== ALL EXTRACTED LIQUIDITY FIELDS =====
[INFO] {"timestamp":..., "price":..., "levelType":..., "strengthScore":...}
```

**If no events after 30 seconds**, you'll see:

```
[WARN] ═══════════════════════════════════════════════════════════
[WARN] ⚠ LIQUIDITY FEED CHECK: NO liquidity events received after 30 seconds!
[WARN] ═══════════════════════════════════════════════════════════
[WARN] Possible reasons:
[WARN]   1. Liquidity Markers not enabled for this instrument
[WARN]   2. Market is quiet (no significant liquidity levels detected)
[WARN]   3. Insufficient market activity to form liquidity levels
[WARN]   4. Generator not properly subscribed
```

**Action**: If you see this warning, verify Liquidity Markers indicator is enabled and showing levels on chart.

### Step 4: Event Processing Verification

Every 10th liquidity event should log:

```
[INFO] Liquidity #10: SUPPORT @ 20100.00, Strength: 0.85, Volume: 150000, Touches: 3
[INFO] Liquidity #20: RESISTANCE @ 20110.50, Strength: 0.92, Volume: 200000, Touches: 5
```

Stats label at top of panel should update:

```
Liquidity: 42 | Support: 25 | Resistance: 17 | Types: 2
```

### Step 5: Batch Write Verification (Every 5 seconds)

Every 5 seconds, batch writes occur:

```
[INFO] [BATCH] Wrote 15 liquidity events to TimescaleDB
[INFO] [BATCH] Wrote 8 liquidity events to TimescaleDB
```

### Step 6: Redis Verification

Check Redis for stored liquidity levels:

```powershell
redis-cli
```

```redis
# Check liquidity keys for your symbol (example: MNQZ5.CME@RITHMIC)
KEYS liquidity:*

# Example output:
# 1) "liquidity:MNQZ5.CME@RITHMIC:SUPPORT"
# 2) "liquidity:MNQZ5.CME@RITHMIC:RESISTANCE"
# 3) "liquidity:strength:MNQZ5.CME@RITHMIC:SUPPORT"
# 4) "liquidity:strength:MNQZ5.CME@RITHMIC:RESISTANCE"
# 5) "stream:liquidity:MNQZ5.CME@RITHMIC"

# Check support levels (sorted by price)
ZRANGE liquidity:MNQZ5.CME@RITHMIC:SUPPORT 0 -1

# Check resistance levels (sorted by price)
ZRANGE liquidity:MNQZ5.CME@RITHMIC:RESISTANCE 0 -1

# Check strongest support levels (sorted by strength)
ZREVRANGE liquidity:strength:MNQZ5.CME@RITHMIC:SUPPORT 0 4 WITHSCORES

# Check liquidity event stream (latest 10)
XREVRANGE stream:liquidity:MNQZ5.CME@RITHMIC + - COUNT 10
```

**Expected**: JSON objects with price, levelType, strengthScore, volume, touches.

### Step 7: TimescaleDB Verification

Check PostgreSQL for historical data:

```powershell
$env:PGPASSWORD='X74Ot*BvtjgKuCBx'
psql -h localhost -U postgres -d trading_data
```

```sql
-- Count total liquidity levels
SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
FROM liquidity_levels;

-- Latest 10 liquidity events
SELECT timestamp, symbol, price, level_type, strength_score, touches_count
FROM liquidity_levels
ORDER BY timestamp DESC
LIMIT 10;

-- Support vs Resistance breakdown
SELECT level_type, COUNT(*) as count, AVG(strength_score) as avg_strength
FROM liquidity_levels
GROUP BY level_type;

-- Top 10 strongest levels (all time)
SELECT timestamp, price, level_type, strength_score, volume_at_level, touches_count
FROM liquidity_levels
ORDER BY strength_score DESC
LIMIT 10;

-- Liquidity levels from last hour
SELECT timestamp, price, level_type, strength_score, touches_count
FROM liquidity_levels
WHERE timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;

-- Check specific session
SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
FROM liquidity_levels
WHERE session_id = 'YOUR_SESSION_ID';
```

**Expected**: Rows with timestamp, symbol, price, level_type (SUPPORT/RESISTANCE/UNKNOWN), strength_score, volume_at_level, touches_count.

## Troubleshooting

### Problem: "No such provider" error

**Cause**: Liquidity Markers indicator not installed or provider name mismatch.

**Solution**:

1. Check providers/modules/ for liquidity marker folder
2. Verify provider class: `velox.api.layer1.addons.liquidity.LiquidityMarkersOverlay`
3. Check Provider.java enum has LIQUIDITY_MARKERS entry

### Problem: "No events received after 30 seconds"

**Cause**: Liquidity Markers not enabled, market quiet, or no significant levels detected.

**Solution**:

1. Verify Liquidity Markers indicator is **enabled** on same chart
2. Check Liquidity Markers is showing levels on chart (visual confirmation)
3. Wait for market activity - liquidity levels may take time to form
4. Check log: `F:/Databases/Logs/liquidity_consumer.log` for detailed errors

### Problem: Redis connection failed

**Cause**: Redis not running or wrong port.

**Solution**:

```powershell
# Start Redis
redis-server

# Or check if running
redis-cli ping
# Should return: PONG
```

### Problem: TimescaleDB connection failed

**Cause**: PostgreSQL not running, wrong credentials, or database doesn't exist.

**Solution**:

```powershell
# Verify PostgreSQL is running
# Check services.msc for "postgresql-x64-17"

# Test connection
$env:PGPASSWORD='X74Ot*BvtjgKuCBx'
psql -h localhost -U postgres -d trading_data -c "SELECT 1;"

# If database doesn't exist, create it
psql -h localhost -U postgres -c "CREATE DATABASE trading_data;"
```

### Problem: "Batch queue full, liquidity event dropped"

**Cause**: Events arriving faster than batch processor can handle (5000 event queue).

**Solution**:

1. Increase queue size in constructor: `new LinkedBlockingQueue<>(10000)`
2. Decrease batch interval: `scheduleAtFixedRate(this::processBatch, 2, 2, TimeUnit.SECONDS)`
3. Check database performance

### Problem: Events logged but not appearing in database

**Cause**: Batch processor not running or database write errors.

**Solution**:

1. Check logs for "[BATCH] Error processing batch" messages
2. Verify liquidity_levels table exists: `\d liquidity_levels` in psql
3. Check database permissions: postgres user should have write access
4. Manually process batch by waiting 5+ seconds

## Expected Behavior Summary

✅ **Connection**: Within 10 seconds of enabling addon  
✅ **First Event**: Within 30 seconds of market activity (if Liquidity Markers shows levels)  
✅ **Event Frequency**: Depends on market volatility and Liquidity Markers settings  
✅ **Batch Writes**: Every 5 seconds (if events in queue)  
✅ **Redis TTL**: 12 hours (43200 seconds) - matches absorption TTL  
✅ **Database Storage**: Permanent (hypertable with automatic compression after 1 week)

## Session Tracking

Session ID format: `{symbol}_{yyyyMMdd_HHmmss}_{UUID}`

Example: `MNQZ5.CME@RITHMIC_20251111_083045_a7f8c3d9-2e4b-4a1c-9f5d-1c8e7b3a6d2e`

All liquidity events in same session share the same session_id for analysis.

## Integration with Other Consumers

LiquidityMarkerConsumer complements:

- **MboDataConsumer** - Large institutional orders
- **AbsorptionConsumer** - Order flow absorption patterns
- **StopsIcebergsConsumer** - Hidden iceberg orders and stop clusters
- **SweepsConsumer** - Aggressive sweep events

**Analysis**: Liquidity levels where multiple indicators converge = high-confidence institutional zones.

## Shutdown Verification

When closing Bookmap or disabling addon:

```
[INFO] ========================================
[INFO] Liquidity Consumer: SHUTTING DOWN
[INFO] ========================================
[INFO] Final Statistics - Total: 157, Support: 89, Resistance: 68
[INFO] ✓ Liquidity feed was ACTIVE during session
[INFO] Liquidity level type breakdown:
[INFO]   SUPPORT: 89
[INFO]   RESISTANCE: 68
[INFO] [BATCH] Wrote 12 liquidity events to TimescaleDB
[INFO] ✓ Cleanup completed successfully
[INFO] ========================================
```

## Log File Location

**Primary Log**: `F:/Databases/Logs/liquidity_consumer.log`

Contains:

- Startup/shutdown messages
- Connection status
- Event processing logs
- Batch write confirmations
- Error messages with stack traces

## Data Retention

**Redis** (Hot Storage):

- TTL: 12 hours (43200 seconds)
- Auto-expires after 12 hours of inactivity
- Sorted sets for efficient price/strength queries
- Stream for real-time notifications (max 500 events)

**TimescaleDB** (Cold Storage):

- Permanent storage with hypertable compression
- Indexes on: symbol+time, level_type, strength_score, session_id
- JSONB metadata for flexible queries
- ON CONFLICT: Updates existing levels (same timestamp+symbol+price)

## Next Steps

After verification:

1. **Integrate with morning_trading_analysis.py**: Fetch liquidity levels for pre-market bias
2. **Build liquidity heatmap**: Visualize strongest support/resistance zones
3. **Confluence analysis**: Combine with MBO, Absorption, Icebergs, Sweeps
4. **Alert system**: Notify when price approaches strong liquidity levels
5. **Backtest**: Historical analysis of price reactions at liquidity zones

---

**Status**: ✅ LiquidityMarkerConsumer fully implemented and ready for testing!
