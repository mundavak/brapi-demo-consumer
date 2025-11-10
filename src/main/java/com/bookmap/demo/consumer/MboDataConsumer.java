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
 * Separates MBO, Trade, and Depth data with data_type markers
 */
@Layer1SimpleAttachable
@Layer1StrategyName("MBO Data Consumer (Java)")
@Layer1ApiVersion(Layer1ApiVersionValue.VERSION2)
public class MboDataConsumer implements
        CustomModule,
        MarketByOrderDepthDataListener,
        TradeDataListener,
        DepthDataListener {

    private static final String MBO_LOG_PATH = "F:/Databases/Logs/mbo_consumer.log";
    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");

    private String alias;
    private InstrumentInfo instrumentInfo;
    private final AtomicBoolean isActive = new AtomicBoolean(false);

    // Storage managers
    private final RedisManager redisManager = RedisManager.getInstance();

    // Session tracking
    private String sessionId;

    // Batch processing
    private final BlockingQueue<MboData> mboBatchQueue = new LinkedBlockingQueue<>(10000);
    private final ScheduledExecutorService batchProcessor = Executors.newSingleThreadScheduledExecutor();

    // Order state tracking (orderId -> isBid)
    private final Map<String, Boolean> orderSides = new ConcurrentHashMap<>();

    // Statistics
    private final Map<String, Long> eventCounts = new ConcurrentHashMap<>();
    private volatile boolean firstMboSend = true;
    private volatile boolean firstMboReplace = true;
    private volatile boolean firstMboCancel = true;
    private volatile boolean firstTrade = true;
    private volatile boolean firstDepth = true;

    @Override
    public void initialize(String alias, InstrumentInfo info, Api api, InitialState initialState) {
        this.alias = alias;
        this.instrumentInfo = info;
        this.sessionId = SessionManager.getInstance().generateSessionId(alias);

        // Initialize event counters
        eventCounts.put("mbo_send", 0L);
        eventCounts.put("mbo_replace", 0L);
        eventCounts.put("mbo_cancel", 0L);
        eventCounts.put("trade", 0L);
        eventCounts.put("depth", 0L);

        isActive.set(true);

        // Start batch processor (every 5 seconds)
        batchProcessor.scheduleAtFixedRate(this::processBatch, 5, 5, TimeUnit.SECONDS);

        log("INFO", "MboDataConsumer initialized for " + alias + " | Session: " + sessionId);
        log("INFO", "✓ Subscribed to MBO data (MarketByOrderDepthDataListener - send/replace/cancel)");
        log("INFO", "✓ Subscribed to Trade data (TradeDataListener)");
        log("INFO", "✓ Subscribed to Depth data (DepthDataListener)");
    }

    @Override
    public void stop() {
        isActive.set(false);

        // Process remaining batches
        processBatch();

        // Shutdown executor
        batchProcessor.shutdown();
        try {
            if (!batchProcessor.awaitTermination(10, TimeUnit.SECONDS)) {
                batchProcessor.shutdownNow();
            }
        } catch (InterruptedException e) {
            batchProcessor.shutdownNow();
            Thread.currentThread().interrupt();
        }

        log("INFO", "MboDataConsumer stopped. Stats: " + eventCounts);
    }

    // =================================================================
    // MBO EVENT HANDLERS (MarketByOrderDepthDataListener)
    // =================================================================

    @Override
    public void send(String orderId, boolean isBid, int price, int size) {
        if (!isActive.get())
            return;

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
                    EventFieldExtractor.toJsonString(allFields));

            // Redis: Hot storage (real-time)
            redisManager.storeMboOrder(alias, orderId, actualPrice, actualSize, isBid, "SEND");

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
                    EventFieldExtractor.toJsonString(allFields));

            // Redis: Hot storage (real-time) - update with new size
            redisManager.storeMboOrder(alias, orderId, actualPrice, actualSize, isBid, "REPLACE");

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
                    EventFieldExtractor.toJsonString(allFields));

            // Redis: Hot storage (real-time) - remove order from book
            redisManager.storeMboOrder(alias, orderId, 0.0, 0.0, isBid, "CANCEL");

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
            // Extract all fields using reflection
            Map<String, Object> allFields = EventFieldExtractor.extractAllFields(tradeInfo);
            allFields.put("price", price);
            allFields.put("size", size);
            allFields.put("data_type", "TRADE");

            // Log first event
            if (firstTrade) {
                log("INFO", "=== FIRST TRADE EVENT ===");
                log("INFO", "Fields captured: " + EventFieldExtractor.toJsonString(allFields));
                firstTrade = false;
            }

            // Create MboData with data_type = "TRADE"
            String tradeId = "TRADE_" + System.nanoTime();
            double actualSize = size / instrumentInfo.sizeMultiplier;

            MboData data = new MboData(
                    System.currentTimeMillis(),
                    alias,
                    tradeId,
                    price,
                    actualSize,
                    tradeInfo.isBidAggressor ? "SELL" : "BUY", // Aggressor side
                    "TRADE",
                    "TRADE", // action = TRADE
                    sessionId,
                    "TRADE", // data_type
                    EventFieldExtractor.toJsonString(allFields));

            // Redis: Hot storage (real-time) - store in Stream
            redisManager.storeTrade(alias, tradeId, price, actualSize, tradeInfo.isBidAggressor);

            // TimescaleDB: Cold storage (historical) - via batch queue
            mboBatchQueue.offer(data);

        } catch (Exception e) {
            log("ERROR", "Error handling trade: " + e.getMessage());
            e.printStackTrace();
        }
    }

    // =================================================================
    // DEPTH DATA HANDLER (DepthDataListener)
    // =================================================================

    @Override
    public void onDepth(boolean isBid, int price, int size) {
        if (!isActive.get())
            return;

        eventCounts.merge("depth", 1L, Long::sum);

        try {
            // Extract all fields
            Map<String, Object> allFields = Map.of(
                    "isBid", isBid,
                    "price", price,
                    "size", size,
                    "data_type", "DEPTH");

            // Log first event (less frequently to avoid spam)
            if (firstDepth && eventCounts.get("depth") % 100 == 0) {
                log("INFO", "=== FIRST DEPTH EVENT (every 100) ===");
                log("INFO", "Fields captured: " + EventFieldExtractor.toJsonString(allFields));
                firstDepth = false;
            }

            // Create MboData with data_type = "DEPTH"
            double actualPrice = price * instrumentInfo.pips;
            double actualSize = size / instrumentInfo.sizeMultiplier;

            MboData data = new MboData(
                    System.currentTimeMillis(),
                    alias,
                    "DEPTH_" + System.nanoTime(), // Generate unique ID
                    actualPrice,
                    actualSize,
                    isBid ? "BUY" : "SELL",
                    "DEPTH",
                    "DEPTH", // action = DEPTH
                    sessionId,
                    "DEPTH", // data_type
                    EventFieldExtractor.toJsonString(allFields));

            // Redis: Hot storage (real-time) - store aggregated depth
            redisManager.storeDepth(alias, actualPrice, actualSize, isBid);

            // TimescaleDB: Cold storage (historical) - via batch queue
            mboBatchQueue.offer(data);

        } catch (Exception e) {
            log("ERROR", "Error handling depth: " + e.getMessage());
            e.printStackTrace();
        }
    }

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
            TimescaleDBManager.getInstance().batchInsertMboData(batch);

            // Update Redis stats (hot storage)
            long mboTotal = eventCounts.getOrDefault("mbo_send", 0L) +
                    eventCounts.getOrDefault("mbo_replace", 0L) +
                    eventCounts.getOrDefault("mbo_cancel", 0L);
            redisManager.updateMboStats(alias, sessionId, mboTotal,
                    eventCounts.getOrDefault("trade", 0L),
                    eventCounts.getOrDefault("depth", 0L));

            // Log batch composition
            log("INFO", "Batch inserted %d records: %s | Queue remaining: %d".formatted(
                    batchSize, batchCounts, mboBatchQueue.size()));

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

    private void log(String level, String message) {
        String logLine = "[%s] [%s] %s".formatted(dateFormat.format(new Date()), level, message);
        Log.info(logLine);
        try (FileWriter writer = new FileWriter(MBO_LOG_PATH, true)) {
            writer.write(logLine + "\n");
        } catch (IOException e) {
            Log.error("Failed to write to log file", e);
        }
    }
}
