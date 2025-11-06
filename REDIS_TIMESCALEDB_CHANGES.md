# Changes Required to Integrate Redis + TimescaleDB

## Summary
Converting `StopsIcebergsConsumer.java` from SQLite to Redis (hot storage) + TimescaleDB (cold storage).

## Changes Made So Far

### 1. Import Statements (COMPLETED)
```java
// Added these imports:
import com.bookmap.demo.consumer.database.RedisManager;
import com.bookmap.demo.consumer.database.TimescaleDBManager;
import com.bookmap.demo.consumer.utils.SessionManager;

// Changed:
import java.util.concurrent.*;  // Added concurrent package
```

### 2. Field Declarations (COMPLETED)
```java
// REMOVED:
private static final String SI_DB_PATH = "F:/TradingAgent/si_events_db.csv";
private static final String SQLITE_DB_PATH = "F:/TradingAgent/enhanced_market_monitor_mbo.db";
private Connection dbConnection;

// ADDED:
private final RedisManager redisManager;
private final TimescaleDBManager dbManager;
private final BlockingQueue<StopIcebergEvent> batchQueue;
private final ScheduledExecutorService batchProcessor;
private String currentSessionId;
```

### 3. Constructor Changes (COMPLETED)
```java
// REMOVED:
initializeDatabase();  // SQLite initialization

// ADDED:
this.redisManager = RedisManager.getInstance();
this.dbManager = TimescaleDBManager.getInstance();
this.batchQueue = new LinkedBlockingQueue<>(5000);
this.batchProcessor = Executors.newSingleThreadScheduledExecutor();
this.batchProcessor.scheduleAtFixedRate(this::processBatch, 5, 5, TimeUnit.SECONDS);
```

### 4. Removed Methods (COMPLETED)
```java
// REMOVED entire method:
private void initializeDatabase() { ... }  // 50 lines of SQLite setup

// ADDED new method:
private void processBatch() {
    try {
        List<StopIcebergEvent> batch = new ArrayList<>();
        batchQueue.drainTo(batch, 500);
        if (!batch.isEmpty()) {
            dbManager.batchInsertStopIcebergEvents(batch);
            log("INFO", String.format("[BATCH] Wrote %d events to TimescaleDB", batch.size()));
        }
    } catch (Exception e) {
        log("ERROR", "[BATCH] Error processing batch: " + e.getMessage());
    }
}
```

### 5. Event Processing - onStopEvent() (COMPLETED)
```java
// ADDED after log("STOP", logMsg); and updateUI();:

// Write to Redis (hot storage) and queue for TimescaleDB (cold storage)
try {
    String symbol = instrumentsInfo.isEmpty() ? "UNKNOWN" : instrumentsInfo.keySet().iterator().next();
    if (currentSessionId == null) {
        currentSessionId = SessionManager.getInstance().generateSessionId(symbol);
    }
    
    long timestamp = stopData.get("time") != null ? ((Number) stopData.get("time")).longValue() : System.nanoTime();
    String eventType = (String) stopData.getOrDefault("eventType", "STOP");
    String side = (String) stopData.getOrDefault("side", "UNKNOWN");
    double price = stopData.get("price") != null ? ((Number) stopData.get("price")).doubleValue() : 0.0;
    double size = stopData.get("size") != null ? ((Number) stopData.get("size")).doubleValue() : 0.0;
    double totalSize = stopData.get("totalSize") != null ? ((Number) stopData.get("totalSize")).doubleValue() : 0.0;
    String cbdrWindow = "UNFILTERED";

    // Write to Redis immediately (HOT STORAGE)
    redisManager.addStopIcebergEvent(symbol, timestamp, eventType, side, price, size, totalSize, currentSessionId, cbdrWindow);
    
    // Queue for TimescaleDB batch insert (COLD STORAGE)
    StopIcebergEvent dbEvent = new StopIcebergEvent(symbol, timestamp, eventType, side, price, size, totalSize, currentSessionId, cbdrWindow);
    if (!batchQueue.offer(dbEvent)) {
        log("WARN", "Batch queue full, event dropped");
    }
} catch (Exception e) {
    log("ERROR", "Failed to write to databases: " + e.getMessage());
}
```

### 6. Event Processing - onIcebergEvent() (COMPLETED)
Same pattern as onStopEvent() - added Redis write and TimescaleDB queue after logging.

### 7. Cleanup - finish() Method (COMPLETED)
```java
// REMOVED:
if (dbConnection != null) {
    try {
        dbConnection.close();
        log("INFO", "Database connection closed successfully");
    } catch (SQLException e) {
        log("ERROR", "Error closing database connection: " + e.getMessage());
    }
}

// ADDED:
if (batchProcessor != null) {
    try {
        log("INFO", "Shutting down batch processor...");
        batchProcessor.shutdown();
        if (!batchProcessor.awaitTermination(10, TimeUnit.SECONDS)) {
            batchProcessor.shutdownNow();
        }
        processBatch();  // Process remaining events
        log("INFO", "Batch processor shutdown complete");
    } catch (InterruptedException e) {
        batchProcessor.shutdownNow();
        Thread.currentThread().interrupt();
    }
}
```

### 8. Inner Class Added (COMPLETED)
```java
// ADDED at end of class (before final closing brace):
public static class StopIcebergEvent {
    public final String symbol;
    public final long timestamp;
    public final String eventType;
    public final String side;
    public final double price;
    public final double detectedSize;
    public final double estimatedTotal;
    public final String sessionId;
    public final String cbdrWindow;

    public StopIcebergEvent(String symbol, long timestamp, String eventType, String side,
            double price, double detectedSize, double estimatedTotal, String sessionId, String cbdrWindow) {
        this.symbol = symbol;
        this.timestamp = timestamp;
        this.eventType = eventType;
        this.side = side;
        this.price = price;
        this.detectedSize = detectedSize;
        this.estimatedTotal = estimatedTotal;
        this.sessionId = sessionId;
        this.cbdrWindow = cbdrWindow;
    }
}
```

## Compilation Errors to Fix

### Error 1: StopIcebergEvent Type Mismatch
**Line 182**: `dbManager.batchInsertStopIcebergEvents(batch);`
- **Problem**: Our inner class `StopsIcebergsConsumer.StopIcebergEvent` doesn't match `TimescaleDBManager.StopIcebergEvent`
- **Solution**: Use the correct type from TimescaleDBManager
- **Fix**: Change field declaration to:
  ```java
  private final BlockingQueue<TimescaleDBManager.StopIcebergEvent> batchQueue;
  ```
- **And update instantiation** in both onStopEvent() and onIcebergEvent():
  ```java
  TimescaleDBManager.StopIcebergEvent dbEvent = new TimescaleDBManager.StopIcebergEvent(symbol, timestamp, eventType, side, price, size, totalSize, currentSessionId, cbdrWindow);
  ```

### Error 2 & 3: RedisManager Method Signature
**Lines 487, 602**: `redisManager.addStopIcebergEvent(...)`
- **Problem**: Wrong method signature - RedisManager expects different parameters
- **Current Signature**: `addStopIcebergEvent(String symbol, String sessionId, long timestamp, String eventType)`
- **We're Calling**: `addStopIcebergEvent(symbol, timestamp, eventType, side, price, size, totalSize, currentSessionId, cbdrWindow)`
- **Solution**: Check RedisManager.java to see actual method signature and match it
- **Expected Fix**:
  ```java
  redisManager.addStopIcebergEvent(symbol, currentSessionId, timestamp, eventType);
  ```

### Error 4: SI_DB_PATH Not Found
**Line 843**: `try (FileWriter writer = new FileWriter(SI_DB_PATH, true))`
- **Problem**: We removed `SI_DB_PATH` constant but it's still used in `exportEventToDb()` method
- **Solution**: Either restore the constant OR remove/comment the method
- **Recommended**: Restore the constant (it's just for CSV export, not harmful)
  ```java
  private static final String SI_DB_PATH = "F:/TradingAgent/si_events_db.csv";
  ```

### Error 5, 6, 7, 8: SQL-Related Symbols
**Lines 866, 877**: `dbConnection`, `PreparedStatement`, `SQLException`
- **Problem**: We removed SQL imports but `saveEventToSQLite()` method still uses them
- **Solution**: Restore SQL imports since these methods still exist:
  ```java
  import java.sql.Connection;
  import java.sql.DriverManager;
  import java.sql.PreparedStatement;
  import java.sql.SQLException;
  import java.sql.Statement;
  ```

## Files to Reference for Correct Signatures

### RedisManager.addStopIcebergEvent()
**File**: `src/main/java/com/bookmap/demo/consumer/database/RedisManager.java`
**Check**: What are the actual parameters?

### TimescaleDBManager.StopIcebergEvent
**File**: `src/main/java/com/bookmap/demo/consumer/database/TimescaleDBManager.java`
**Check**: What fields does this class have?

### TimescaleDBManager.batchInsertStopIcebergEvents()
**File**: `src/main/java/com/bookmap/demo/consumer/database/TimescaleDBManager.java`
**Check**: What type does it expect?

## What's Working
- ✅ Imports added correctly
- ✅ Fields declared correctly
- ✅ Constructor initializes Redis and TimescaleDB managers
- ✅ Batch processor scheduled every 5 seconds
- ✅ processBatch() method created
- ✅ Event processing adds database writes
- ✅ Cleanup in finish() method

## What Needs Fixing
- ❌ Match RedisManager method signature
- ❌ Use correct StopIcebergEvent type from TimescaleDBManager
- ❌ Restore SQL imports for legacy methods
- ❌ Restore SI_DB_PATH constant for CSV export

## Next Steps
1. Check RedisManager.java for correct `addStopIcebergEvent()` signature
2. Remove our inner class `StopIcebergEvent` and use `TimescaleDBManager.StopIcebergEvent`
3. Restore SQL imports and SI_DB_PATH constant
4. Rebuild and test

## Expected Behavior After Fix
1. **Events logged** to `F:/TradingAgent/si_events.log` (existing)
2. **Redis writes** - Immediate hot storage with 1-day TTL
3. **TimescaleDB writes** - Batch inserts every 5 seconds (cold storage)
4. **JSON export** - Every 10 events (existing)
5. **CSV export** - Every event (existing, legacy)
6. **SQLite export** - Every event (existing, legacy)

The consumer will write to ALL storage systems - Redis/TimescaleDB are added, not replacing old ones.
