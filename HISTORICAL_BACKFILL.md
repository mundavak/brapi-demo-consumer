# Historical Data Backfill Implementation

## Overview
Both `StopsIcebergsBroadcastConsumer` and `AbsorptionConsumer` now support automatic backfill of historical data from the past 24 hours during CBDR windows when they start up.

## Implementation Details

### What Was Added

#### StopsIcebergsBroadcastConsumer
- **requestHistoricalData(String generatorName)** method:
  - Queries last 24 hours of data via Broadcasting API
  - Filters events to only CBDR windows using `SessionManager.getCbdrWindow(timestamp)`
  - Processes valid events through `processHistoricalEvent()`
  - Logs: "Historical data processed: X events stored, Y filtered (outside CBDR)"

- **processHistoricalEvent(Event event, String generatorName, String cbdrWindow)** method:
  - Casts events to `EventInterface` same as live processing
  - Creates `TimescaleDBManager.StopIcebergEvent` objects
  - Populates all fields: symbol, timestamp, eventType, side, price, detectedSize, etc.
  - Adds `"historical":true` flag to metadata JSON
  - Queues to `batchQueue` for batch processing (same as live events)

#### AbsorptionConsumer
- **requestHistoricalData(String generatorName)** method:
  - Same 24-hour query pattern as StopsIcebergs
  - Filters to CBDR windows only
  - Processes through `processHistoricalAbsorptionEvent()`

- **processHistoricalAbsorptionEvent(Event event, String cbdrWindow)** method:
  - Uses reflection to access provider-specific fields (price, size, isBid)
  - Calculates significance score using `calculateSignificance()`
  - Filters events with significance < 0.5 threshold
  - Creates `TimescaleDBManager.AbsorptionEvent` objects
  - Marks `isInCbdr = true` and `cbdrWindow` for all historical events
  - Queues to `batchQueue` for batch processing

### API Pattern Used

```java
// Get data structure interface
BrDataStructureInterface dataStructureInterface = 
    broadcaster.getDataStructureInterface(PROVIDER.getFullName());

// Calculate time range
long endTime = System.currentTimeMillis();
long startTime = endTime - (24 * 60 * 60 * 1000L); // 24 hours ago

// Request historical data from provider
List<Object> historicalData = PROVIDER.getValueHandler().requestHistoricalData(
    dataStructureInterface, generatorName, startTime, endTime, alias);

// Cast events
List<Event> events = PROVIDER.getValueHandler().castEventsInOurClassLoader(historicalData);

// Filter by CBDR windows
for (Event event : events) {
    String cbdrWindow = sessionManager.getCbdrWindow(event.getTime());
    if (cbdrWindow != null) {
        // Process event - it was during CBDR window
    }
}
```

### When Backfill Happens
- Triggered automatically when addon subscribes to a generator
- Runs after live data subscription is established
- Happens once per generator when addon starts
- Does NOT run continuously - only at startup

### CBDR Window Detection
Historical events are validated using:
```java
String cbdrWindow = sessionManager.getCbdrWindow(timestamp);
if (cbdrWindow != null) {
    // Event was during PM 16:00-20:00, London 02:00-05:00, or Pre-NY 07:30-09:30 EST
    // cbdrWindow contains: "PM_SESSION", "LONDON_SESSION", or "PRE_NY_SESSION"
}
```

### Database Storage
- Historical events use the SAME storage mechanism as live events:
  - Queued to `BlockingQueue<Event>` (capacity: 5000 events)
  - Batch processor runs every 5 seconds
  - Writes to TimescaleDB in batches of 500 events
  - No separate tables or schemas needed

- Metadata JSON includes `"historical":true` flag to distinguish from live events

### Performance Considerations
- Historical queries can return large datasets (provider-dependent)
- CBDR filtering happens in-memory before queuing
- Batch queue has 5000 event capacity - monitors queue size
- If queue full, logs warning and drops event (shouldn't happen with 24hr range)

## Testing

### Verification Steps
1. **Enable Consumers**: Settings → Manage Addons → Enable both consumers
2. **Add to Chart**: Right-click chart → Indicators → Add StopsIcebergs/Absorption
3. **Check Logs**: Look for these messages in Bookmap logs:
   ```
   [StopsIcebergsConsumer] Requesting historical data: generator_name from ... to ...
   [StopsIcebergsConsumer] Historical data processed: X events stored, Y filtered (outside CBDR)
   
   [AbsorptionConsumer] Requesting historical data: generator_name from ... to ...
   [AbsorptionConsumer] Historical data processed: X events stored, Y filtered (outside CBDR)
   ```

4. **Query Database**: Check TimescaleDB for historical events:
   ```sql
   -- Stops & Icebergs
   SELECT symbol, timestamp, event_type, price, detected_size, cbdr_window, metadata
   FROM stops_icebergs
   WHERE metadata LIKE '%historical%'
   ORDER BY timestamp DESC
   LIMIT 20;
   
   -- Absorption
   SELECT symbol, timestamp, event_type, side, price, absorbed_volume, cbdr_window, metadata
   FROM absorption_events
   WHERE metadata LIKE '%historical%'
   ORDER BY timestamp DESC
   LIMIT 20;
   ```

5. **Monitor Performance**: Watch for:
   - Queue full warnings (shouldn't appear for 24hr range)
   - Processing time (log timestamps)
   - Database batch write times

### Expected Behavior
- **During CBDR Window**: May see recent events from current session backfilled
- **Outside CBDR Window**: Backfills events from previous CBDR sessions (yesterday's PM, this morning's London/Pre-NY)
- **No Data**: If providers weren't active 24 hours ago, may return 0 events
- **Provider Limitations**: Some providers may not support historical data or limit time ranges

## Troubleshooting

### No Historical Data Returned
- **Cause**: Provider may not have historical data API implemented
- **Solution**: Check provider documentation for `requestHistoricalData()` support

### "Data structure interface not available"
- **Cause**: Provider not fully connected yet
- **Solution**: Wait for connection complete, then restart addon

### Queue Full Warnings
- **Cause**: Too many historical events for 5000 event queue capacity
- **Solution**: Increase `batchQueue` capacity or reduce query time range

### Events Not Filtered Correctly
- **Cause**: CBDR window detection may have timezone issues
- **Solution**: Verify `SessionManager.getCbdrWindow()` uses correct EST timezone

### Historical Events Missing in Database
- **Cause**: Batch processor may not be running or database connection failed
- **Solution**: Check TimescaleDBManager logs for connection errors

## Configuration

### Adjusting Time Range
Change the time range in `requestHistoricalData()`:
```java
// From 24 hours to 48 hours
long startTime = endTime - (48 * 60 * 60 * 1000L);

// From 24 hours to 7 days
long startTime = endTime - (7 * 24 * 60 * 60 * 1000L);
```

### Adjusting Queue Capacity
In class constructor:
```java
// From 5000 to 10000 events
private final BlockingQueue<Event> batchQueue = new LinkedBlockingQueue<>(10000);
```

### Disabling Historical Backfill
Comment out the call in `subscribeToGenerator()`:
```java
// requestHistoricalData(generatorName); // Disabled for testing
```

## Benefits
1. **Eliminates Data Gaps**: Captures events that occurred when addon wasn't running
2. **CBDR Completeness**: Ensures full coverage of important trading windows
3. **Session Continuity**: Backfills missed events from previous sessions
4. **Automatic**: No manual intervention needed - runs on startup
5. **Efficient**: Uses same batch processing as live events

## Limitations
1. **Time Range**: Currently limited to 24 hours (configurable)
2. **Provider Support**: Depends on provider implementing historical data API
3. **Memory**: Large time ranges may consume significant memory
4. **One-Time**: Only runs at startup, not continuously
5. **CBDR Only**: Filters out all non-CBDR events (by design)

## Build & Deploy
```powershell
# Build JARs
.\gradlew.bat clean build

# Auto-copy to Bookmap
# (Already configured in build.gradle copyJars task)

# Restart Bookmap to load new version
```

JAR locations:
- Demo Consumer: `F:/Bookmap/Python/build/Demo-Consumer-3.0.0.jar`
- Python Consumer: `F:/Bookmap/Python/build/MBO_Consumer_Python-1.0.0.jar`
