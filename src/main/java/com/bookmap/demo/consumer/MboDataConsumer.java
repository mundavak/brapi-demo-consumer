package com.bookmap.demo.consumer;

import velox.api.layer1.annotations.Layer1ApiVersion;
import velox.api.layer1.annotations.Layer1ApiVersionValue;
import velox.api.layer1.annotations.Layer1SimpleAttachable;
import velox.api.layer1.annotations.Layer1StrategyName;
import velox.api.layer1.data.InstrumentInfo;
import velox.api.layer1.data.TradeInfo;
import velox.api.layer1.simplified.*;
import velox.api.layer1.common.Log;

import com.bookmap.demo.consumer.database.TimescaleDBManager;
import com.bookmap.demo.consumer.database.TimescaleDBManager.MboData;
import com.bookmap.demo.consumer.database.RedisManager;
import com.bookmap.demo.consumer.database.SessionManager;
import com.bookmap.demo.consumer.utils.EventFieldExtractor;

import java.io.FileWriter;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * MBO Data Consumer using MarketByOrderDepthDataListener
 * Captures all three MBO event types: ADD (send), UPDATE (replace), DELETE
 * (cancel)
 * Optimized for high-performance data collection
 */
@Layer1SimpleAttachable
@Layer1StrategyName("MBO Data Consumer (Java)")
@Layer1ApiVersion(Layer1ApiVersionValue.VERSION2)
public class MboDataConsumer implements
        CustomModule,
        MarketByOrderDepthDataListener,
        TradeDataListener {

    // Log file path - using absolute path since Bookmap runs from its own directory
    private static final String MBO_LOG_PATH = "F:/TradingAgent/deaProjects/brapi-demo-consumer/outputs/logs/mbo_consumer.log";

    // PERFORMANCE OPTIMIZATION: Skip depth events to reduce overhead
    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

    private String alias;
    private InstrumentInfo instrumentInfo;
    private final AtomicBoolean isActive = new AtomicBoolean(false);

    // Storage managers
    private final RedisManager redisManager = RedisManager.getInstance();

    // Session tracking
    private String sessionId;

    // Batch processing for TimescaleDB
    private final BlockingQueue<MboData> mboBatchQueue = new LinkedBlockingQueue<>(10000);
    private final ScheduledExecutorService batchProcessor = Executors.newSingleThreadScheduledExecutor();

    // Async Redis write queue (decouples network I/O from event thread)
    // Increased capacity for handling initial order book snapshot bursts
    private final BlockingQueue<RedisWrite> redisWriteQueue = new LinkedBlockingQueue<>(50000);
    private final ScheduledExecutorService redisWriter = Executors.newSingleThreadScheduledExecutor();

    // Order state tracking (orderId -> isBid)
    private final Map<String, Boolean> orderSides = new ConcurrentHashMap<>();

    // Statistics
    private final Map<String, Long> eventCounts = new ConcurrentHashMap<>();
    private volatile boolean firstMboSend = true;
    private volatile boolean firstMboReplace = true;
    private volatile boolean firstMboCancel = true;
    private volatile boolean firstTrade = true;

    // MBO feed verification
    private volatile long initTime = 0;
    private volatile boolean mboDataReceived = false;
    private final ScheduledExecutorService mboVerifier = Executors.newSingleThreadScheduledExecutor();

    @Override
    public void initialize(String alias, InstrumentInfo info, Api api, InitialState initialState) {
        this.alias = alias;
        this.instrumentInfo = info;
        this.sessionId = SessionManager.getInstance().generateSessionId(alias);
        this.initTime = System.currentTimeMillis();

        // Initialize event counters
        eventCounts.put("mbo_send", 0L);
        eventCounts.put("mbo_replace", 0L);
        eventCounts.put("mbo_cancel", 0L);
        eventCounts.put("trade", 0L);

        isActive.set(true);

        // Start batch processor for TimescaleDB (every 5 seconds)
        batchProcessor.scheduleAtFixedRate(this::processBatch, 5, 5, TimeUnit.SECONDS);

        // Start async Redis writer (every 50ms - processes up to 2000 writes per batch)
        // Faster processing to handle order book snapshot bursts
        redisWriter.scheduleAtFixedRate(this::processRedisWrites, 0, 50, TimeUnit.MILLISECONDS);

        log("INFO", "MboDataConsumer initialized for " + alias + " | Session: " + sessionId);
        log("INFO", "✓ Subscribed to MBO data (MarketByOrderDepthDataListener - send/replace/cancel)");
        log("INFO", "✓ Subscribed to Trade data (TradeDataListener)");
        log("INFO", "⚡ PERFORMANCE MODE: Depth data collection disabled for optimal speed");

        // Schedule MBO feed verification after 30 seconds
        mboVerifier.schedule(this::verifyMboFeed, 30, TimeUnit.SECONDS);
    }

    @Override
    public void stop() {
        isActive.set(false);

        // Process remaining batches
        processBatch();
        processRedisWrites(); // Flush remaining Redis writes

        // Shutdown executors
        mboVerifier.shutdown();
        batchProcessor.shutdown();
        redisWriter.shutdown();
        try {
            if (!batchProcessor.awaitTermination(10, TimeUnit.SECONDS)) {
                batchProcessor.shutdownNow();
            }
            if (!mboVerifier.awaitTermination(5, TimeUnit.SECONDS)) {
                mboVerifier.shutdownNow();
            }
            if (!redisWriter.awaitTermination(5, TimeUnit.SECONDS)) {
                redisWriter.shutdownNow();
            }
        } catch (InterruptedException e) {
            batchProcessor.shutdownNow();
            mboVerifier.shutdownNow();
            redisWriter.shutdownNow();
            Thread.currentThread().interrupt();
        }

        log("INFO", "MboDataConsumer stopped. Stats: " + eventCounts);
        if (mboDataReceived) {
            log("INFO", "✓ MBO data feed was ACTIVE - received true order-by-order data");
        } else {
            log("WARN", "⚠ NO MBO data received - only trades/depth data available");
        }
    }

    /**
     * Verify that true MBO data is being received (not just trades/depth)
     */
    private void verifyMboFeed() {
        long elapsedSeconds = (System.currentTimeMillis() - initTime) / 1000;

        if (!mboDataReceived) {
            log("WARN", "═══════════════════════════════════════════════════════════");
            log("WARN", "⚠ MBO FEED CHECK: NO MBO events received after " + elapsedSeconds + " seconds!");
            log("WARN", "═══════════════════════════════════════════════════════════");
            log("WARN", "Possible reasons:");
            log("WARN", "  1. No MBO subscription active for " + alias);
            log("WARN", "  2. Market is closed or very quiet");
            log("WARN", "  3. Using aggregated data feed (trades/depth only)");
            log("WARN", "  4. MBO data not available for this instrument");
            log("WARN", "═══════════════════════════════════════════════════════════");
            log("WARN", "Current data received:");
            log("WARN", "  - Trades: " + eventCounts.get("trade"));
            log("WARN", "  - MBO events: 0 (MISSING!)");
            log("WARN", "═══════════════════════════════════════════════════════════");
        } else {
            log("INFO", "═══════════════════════════════════════════════════════════");
            log("INFO", "✓ MBO FEED VERIFIED: Receiving true order-by-order data!");
            log("INFO", "═══════════════════════════════════════════════════════════");
            log("INFO", "  - MBO SEND events: " + eventCounts.get("mbo_send"));
            log("INFO", "  - MBO REPLACE events: " + eventCounts.get("mbo_replace"));
            log("INFO", "  - MBO CANCEL events: " + eventCounts.get("mbo_cancel"));
            log("INFO", "  - Trade events: " + eventCounts.get("trade"));
            log("INFO", "═══════════════════════════════════════════════════════════");
        }
    }

    // =================================================================
    // MBO EVENT HANDLERS (MarketByOrderDepthDataListener)
    // =================================================================

    @Override
    public void send(String orderId, boolean isBid, int price, int size) {
        if (!isActive.get())
            return;

        // Mark that we received true MBO data
        if (!mboDataReceived) {
            mboDataReceived = true;
            log("INFO", "✓ TRUE MBO DATA CONFIRMED: Receiving order-by-order feed (not just aggregated trades)");
        }

        eventCounts.merge("mbo_send", 1L, Long::sum);

        try {
            // Extract all fields using reflection
            Map<String, Object> allFields = Map.of(
                    "orderId", orderId,
                    "isBid", isBid,
                    "price", price,
                    "size", size,
                    "event_type", "SEND");

            // Log first event for debugging
            if (firstMboSend) {
                log("INFO", "=== FIRST MBO SEND EVENT ===");
                log("INFO", "Fields captured: " + EventFieldExtractor.toJsonString(allFields));
                firstMboSend = false;
            }

            // Create MboData with data_type = "MBO"
            double actualPrice = price * instrumentInfo.pips;
            double actualSize = size / instrumentInfo.sizeMultiplier;

            // Track order side for future REPLACE/CANCEL events
            orderSides.put(orderId, isBid);

            // PERFORMANCE: All fields captured as empty JSON to avoid serialization
            // overhead
            // Full field extraction moved to batch processor for async handling
            MboData data = new MboData(
                    System.currentTimeMillis(),
                    alias,
                    orderId,
                    actualPrice,
                    actualSize,
                    isBid ? "BUY" : "SELL",
                    "LIMIT",
                    "ADD", // send = ADD
                    sessionId,
                    "MBO", // data_type
                    "{}"); // Empty JSON - avoid synchronous serialization

            // PERFORMANCE: Redis write queued asynchronously (no blocking network I/O on
            // event thread)
            redisWriteQueue.offer(new RedisWrite.MboOrder(alias, orderId, actualPrice, actualSize, isBid, "SEND"));

            // TimescaleDB: Cold storage (historical) - via batch queue
            mboBatchQueue.offer(data);

        } catch (Exception e) {
            log("ERROR", "Error handling MBO send: " + e.getMessage());
            e.printStackTrace();
        }
    }

    @Override
    public void replace(String orderId, int price, int size) {
        if (!isActive.get())
            return;

        // Mark that we received true MBO data
        if (!mboDataReceived) {
            mboDataReceived = true;
        }

        eventCounts.merge("mbo_replace", 1L, Long::sum);

        try {
            // Extract all fields
            Map<String, Object> allFields = Map.of(
                    "orderId", orderId,
                    "price", price,
                    "size", size,
                    "event_type", "REPLACE");

            // Log first event
            if (firstMboReplace) {
                log("INFO", "=== FIRST MBO REPLACE EVENT ===");
                log("INFO", "Fields captured: " + EventFieldExtractor.toJsonString(allFields));
                firstMboReplace = false;
            }

            // Create MboData with data_type = "MBO"
            double actualPrice = price * instrumentInfo.pips;
            double actualSize = size / instrumentInfo.sizeMultiplier;

            // Look up the side from our order tracking
            Boolean isBid = orderSides.get(orderId);
            if (isBid == null) {
                log("WARN", "REPLACE event for unknown orderId: " + orderId + " - assuming bid side");
                isBid = true;
            }

            // PERFORMANCE: All fields captured as empty JSON to avoid serialization
            // overhead
            MboData data = new MboData(
                    System.currentTimeMillis(),
                    alias,
                    orderId,
                    actualPrice,
                    actualSize,
                    isBid ? "BUY" : "SELL",
                    "LIMIT",
                    "UPDATE", // replace = UPDATE
                    sessionId,
                    "MBO", // data_type
                    "{}"); // Empty JSON - avoid synchronous serialization

            // PERFORMANCE: Redis write queued asynchronously (no blocking network I/O on
            // event thread)
            redisWriteQueue.offer(new RedisWrite.MboOrder(alias, orderId, actualPrice, actualSize, isBid, "REPLACE"));

            // TimescaleDB: Cold storage (historical) - via batch queue
            mboBatchQueue.offer(data);

        } catch (Exception e) {
            log("ERROR", "Error handling MBO replace: " + e.getMessage());
            e.printStackTrace();
        }
    }

    @Override
    public void cancel(String orderId) {
        if (!isActive.get())
            return;

        // Mark that we received true MBO data
        if (!mboDataReceived) {
            mboDataReceived = true;
        }

        eventCounts.merge("mbo_cancel", 1L, Long::sum);

        try {
            // Extract all fields
            Map<String, Object> allFields = Map.of(
                    "orderId", orderId,
                    "event_type", "CANCEL");

            // Log first event
            if (firstMboCancel) {
                log("INFO", "=== FIRST MBO CANCEL EVENT ===");
                log("INFO", "Fields captured: " + EventFieldExtractor.toJsonString(allFields));
                firstMboCancel = false;
            }

            // Look up the side from our order tracking
            Boolean isBid = orderSides.remove(orderId); // Remove from tracking map
            if (isBid == null) {
                log("WARN", "CANCEL event for unknown orderId: " + orderId + " - assuming bid side");
                isBid = true;
            }

            // PERFORMANCE: All fields captured as empty JSON to avoid serialization
            // overhead
            // Create MboData with data_type = "MBO"
            MboData data = new MboData(
                    System.currentTimeMillis(),
                    alias,
                    orderId,
                    0.0, // Price unknown for cancel
                    0.0, // Size unknown for cancel
                    isBid ? "BUY" : "SELL",
                    "LIMIT",
                    "DELETE", // cancel = DELETE
                    sessionId,
                    "MBO", // data_type
                    "{}"); // Empty JSON - avoid synchronous serialization

            // PERFORMANCE: Redis write queued asynchronously (no blocking network I/O on
            // event thread)
            // Note: CANCEL now processed in background, avoiding expensive sorted set scan
            // on event thread
            redisWriteQueue.offer(new RedisWrite.MboOrder(alias, orderId, 0.0, 0.0, isBid, "CANCEL"));

            // TimescaleDB: Cold storage (historical) - via batch queue
            mboBatchQueue.offer(data);

        } catch (Exception e) {
            log("ERROR", "Error handling MBO cancel: " + e.getMessage());
            e.printStackTrace();
        }
    }

    // =================================================================
    // TRADE DATA HANDLER (TradeDataListener)
    // =================================================================

    @Override
    public void onTrade(double price, int size, TradeInfo tradeInfo) {
        if (!isActive.get())
            return;

        eventCounts.merge("trade", 1L, Long::sum);

        try {
            // PERFORMANCE: Field extraction removed - was using reflection on every trade
            // Log first event for verification only
            if (firstTrade) {
                log("INFO", "=== FIRST TRADE EVENT ===");
                log("INFO",
                        "Trade: price=" + price + ", size=" + size + ", isBidAggressor=" + tradeInfo.isBidAggressor);
                firstTrade = false;
            }

            // Create MboData with data_type = "TRADE"
            String tradeId = "TRADE_" + System.nanoTime();
            double actualPrice = price * instrumentInfo.pips;
            double actualSize = size / instrumentInfo.sizeMultiplier;

            // PERFORMANCE: Empty JSON - avoid synchronous serialization
            MboData data = new MboData(
                    System.currentTimeMillis(),
                    alias,
                    tradeId,
                    actualPrice,
                    actualSize,
                    tradeInfo.isBidAggressor ? "SELL" : "BUY", // Aggressor side
                    "TRADE",
                    "TRADE", // action = TRADE
                    sessionId,
                    "TRADE", // data_type
                    "{}"); // Empty JSON - avoid synchronous serialization

            // PERFORMANCE: Redis write queued asynchronously (no blocking network I/O on
            // event thread)
            redisWriteQueue
                    .offer(new RedisWrite.Trade(alias, tradeId, actualPrice, actualSize, tradeInfo.isBidAggressor));

            // TimescaleDB: Cold storage (historical) - via batch queue
            mboBatchQueue.offer(data);

        } catch (Exception e) {
            log("ERROR", "Error handling trade: " + e.getMessage());
            e.printStackTrace();
        }
    }

    // DEPTH DATA REMOVED FOR PERFORMANCE
    // Depth updates occur at very high frequency and cause significant overhead
    // MBO and Trade data provide sufficient granularity for analysis

    // =================================================================
    // BATCH PROCESSING
    // =================================================================

    private void processBatch() {
        if (mboBatchQueue.isEmpty()) {
            return;
        }

        try {
            int batchSize = Math.min(mboBatchQueue.size(), 5000);
            if (batchSize == 0)
                return;

            MboData[] batch = new MboData[batchSize];
            for (int i = 0; i < batchSize; i++) {
                batch[i] = mboBatchQueue.poll(100, TimeUnit.MILLISECONDS);
                if (batch[i] == null)
                    break;
            }

            // Count events by type in this batch
            Map<String, Long> batchCounts = new HashMap<>();
            for (MboData data : batch) {
                if (data != null) {
                    String key = data.dataType + "_" + data.action;
                    batchCounts.merge(key, 1L, Long::sum);
                }
            }

            // Write to TimescaleDB (cold storage)
            try {
                TimescaleDBManager.getInstance().batchInsertMboData(batch);

                // Log batch composition ONLY on success
                log("INFO", "✓ TimescaleDB batch inserted %d records: %s | Queue remaining: %d".formatted(
                        batchSize, batchCounts, mboBatchQueue.size()));
            } catch (Exception e) {
                // CRITICAL: Log error but DO NOT rethrow
                // Rethrowing causes batch processor to retry same records → duplicate key
                // errors
                // Instead, log and discard failed batch to allow progress
                log("ERROR", "✗ TimescaleDB batch insert FAILED: " + e.getMessage());
                if (e.getMessage() != null && e.getMessage().contains("duplicate key")) {
                    log("WARN", "Duplicate key error - records already in database, discarding batch");
                } else {
                    log("ERROR", "Non-duplicate error - may indicate connection or schema issue");
                }
                // Batch is already removed from queue (polled), so just continue
            }

            // Update Redis stats (hot storage)
            long mboTotal = eventCounts.getOrDefault("mbo_send", 0L) +
                    eventCounts.getOrDefault("mbo_replace", 0L) +
                    eventCounts.getOrDefault("mbo_cancel", 0L);
            redisManager.updateMboStats(alias, sessionId, mboTotal,
                    eventCounts.getOrDefault("trade", 0L),
                    0L); // depth collection disabled for performance

            // Log progress every 1000 events
            long totalEvents = eventCounts.values().stream().mapToLong(Long::longValue).sum();
            if (totalEvents % 1000 == 0) {
                log("INFO", "Total processed: " + totalEvents + " events | Stats: " + eventCounts);
            }

        } catch (Exception e) {
            log("ERROR", "Batch processing error: " + e.getMessage());
            e.printStackTrace();
        }
    }

    // =================================================================
    // ASYNC REDIS WRITE PROCESSOR
    // =================================================================

    private void processRedisWrites() {
        if (redisWriteQueue.isEmpty()) {
            return;
        }

        try {
            // Process up to 2000 Redis writes per batch (every 50ms = 40K writes/sec max)
            int batchSize = Math.min(redisWriteQueue.size(), 2000);
            int processed = 0;

            for (int i = 0; i < batchSize; i++) {
                RedisWrite write = redisWriteQueue.poll();
                if (write == null)
                    break;

                try {
                    if (write instanceof RedisWrite.MboOrder mbo) {
                        redisManager.storeMboOrder(mbo.symbol, mbo.orderId, mbo.price,
                                mbo.size, mbo.isBid, mbo.eventType);
                    } else if (write instanceof RedisWrite.Trade trade) {
                        redisManager.storeTrade(trade.symbol, trade.tradeId, trade.price,
                                trade.size, trade.isBidAggressor);
                    }
                    processed++;
                } catch (Exception e) {
                    log("ERROR", "Redis write failed: " + e.getMessage());
                }
            }

            if (processed > 0 && redisWriteQueue.size() > 5000) {
                log("WARN", "Redis write queue backlog: " + redisWriteQueue.size() + " writes pending");
            }

        } catch (Exception e) {
            log("ERROR", "Redis batch processing error: " + e.getMessage());
            e.printStackTrace();
        }
    }

    // =================================================================
    // REDIS WRITE COMMAND (Sealed Interface)
    // =================================================================

    private sealed interface RedisWrite permits RedisWrite.MboOrder, RedisWrite.Trade {
        record MboOrder(String symbol, String orderId, double price, double size,
                boolean isBid, String eventType) implements RedisWrite {
        }

        record Trade(String symbol, String tradeId, double price, double size,
                boolean isBidAggressor) implements RedisWrite {
        }
    }

    private void log(String level, String message) {
        String logLine = "[%s] [%s] %s".formatted(dateFormat.format(new Date()), level, message);

        // Log to Bookmap's internal logger
        Log.info(logLine);

        // Also write to file for persistent logging
        try {
            // Ensure directory exists
            java.io.File logFile = new java.io.File(MBO_LOG_PATH);
            logFile.getParentFile().mkdirs();

            try (FileWriter fw = new FileWriter(MBO_LOG_PATH, true)) {
                fw.write(logLine + "\n");
            }
        } catch (IOException e) {
            // Silently fail - don't want logging to crash the addon
            Log.info("Failed to write to log file: " + e.getMessage());
        }
    }
}
