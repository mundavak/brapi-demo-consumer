package com.bookmap.demo.consumer;

import velox.api.layer1.annotations.Layer1ApiVersion;
import velox.api.layer1.annotations.Layer1ApiVersionValue;
import velox.api.layer1.annotations.Layer1SimpleAttachable;
import velox.api.layer1.annotations.Layer1StrategyName;
import velox.api.layer1.data.InstrumentInfo;
import velox.api.layer1.data.TradeInfo;
import velox.api.layer1.simplified.*;
import velox.api.layer1.common.Log;

import java.io.FileWriter;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Raw MBO Data Logger - Captures EVERYTHING from the MBO feed
 * Logs all events with all available fields to rawmbo.log
 * No processing, no filtering, no storage - just raw logging
 */
@Layer1SimpleAttachable
@Layer1StrategyName("Raw MBO Data Logger")
@Layer1ApiVersion(Layer1ApiVersionValue.VERSION2)
public class RawMboDataLogger implements
        CustomModule,
        MarketByOrderDepthDataListener,
        TradeDataListener {

    // Track order sides for replace/cancel events (they don't provide side)
    private final Map<String, Boolean> orderSides = new ConcurrentHashMap<>();

    // Log file path
    private static final String RAW_LOG_PATH = "F:/TradingAgent/deaProjects/brapi-demo-consumer/outputs/logs/rawmbo.log";

    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
    private final AtomicBoolean isActive = new AtomicBoolean(false);

    private String alias;
    private InstrumentInfo instrumentInfo;
    private FileWriter logWriter;

    // Event counters for summary
    private final AtomicLong sendCount = new AtomicLong(0);
    private final AtomicLong replaceCount = new AtomicLong(0);
    private final AtomicLong cancelCount = new AtomicLong(0);
    private final AtomicLong tradeCount = new AtomicLong(0);

    // Track initialization time
    private long initTime;

    @Override
    public void initialize(String alias, InstrumentInfo info, Api api, InitialState initialState) {
        this.alias = alias;
        this.instrumentInfo = info;
        this.initTime = System.currentTimeMillis();

        try {
            // Ensure log directory exists
            java.io.File logFile = new java.io.File(RAW_LOG_PATH);
            logFile.getParentFile().mkdirs();

            // Open log file
            logWriter = new FileWriter(RAW_LOG_PATH, false); // false = overwrite existing

            // Write header
            writeLog("════════════════════════════════════════════════════════════════");
            writeLog("RAW MBO DATA LOGGER - CAPTURE STARTED");
            writeLog("════════════════════════════════════════════════════════════════");
            writeLog("Symbol: " + alias);
            writeLog("Instrument Info:");
            writeLog("  - Full Name: " + info.fullName);
            writeLog("  - Exchange: " + info.exchange);
            writeLog("  - Type: " + info.type);
            writeLog("  - Pips: " + info.pips);
            writeLog("  - Size Multiplier: " + info.sizeMultiplier);
            writeLog("  - Multiplier: " + info.multiplier);
            writeLog("  - Symbol: " + info.symbol);
            writeLog("Timestamp: " + dateFormat.format(new Date()));
            writeLog("════════════════════════════════════════════════════════════════");
            writeLog("");
            writeLog("CAPTURING ALL MBO EVENTS:");
            writeLog("  ✓ MBO Send (new orders)");
            writeLog("  ✓ MBO Replace (order modifications)");
            writeLog("  ✓ MBO Cancel (order deletions)");
            writeLog("  ✓ Trades (executions)");
            writeLog("");
            writeLog("────────────────────────────────────────────────────────────────");
            writeLog("");

            isActive.set(true);
            Log.info("RawMboDataLogger initialized for: " + alias);

        } catch (IOException e) {
            Log.error("Failed to initialize RawMboDataLogger", e);
        }
    }

    // =================================================================
    // MARKET BY ORDER (MBO) HANDLERS
    // =================================================================

    @Override
    public void send(String orderId, boolean isBuy, int price, int size) {
        if (!isActive.get())
            return;

        try {
            long count = sendCount.incrementAndGet();
            double priceReal = price * instrumentInfo.pips;
            double sizeReal = size / instrumentInfo.sizeMultiplier;

            writeLog(String.format("[%d] MBO SEND", count));
            writeLog(String.format("    Time:     %s", dateFormat.format(new Date())));
            writeLog(String.format("    OrderID:  %s", orderId));
            writeLog(String.format("    Side:     %s", isBuy ? "BUY" : "SELL"));
            writeLog(String.format("    Price:    %.2f (raw: %d)", priceReal, price));
            writeLog(String.format("    Size:     %.2f (raw: %d)", sizeReal, size));
            writeLog("");

            // Track order side for later events
            orderSides.put(orderId, isBuy);

            if (count % 100 == 0) {
                logWriter.flush(); // Periodic flush
            }

        } catch (IOException e) {
            Log.error("Error logging SEND event", e);
        }
    }

    @Override
    public void replace(String orderId, int price, int size) {
        if (!isActive.get())
            return;

        try {
            long count = replaceCount.incrementAndGet();
            double priceReal = price * instrumentInfo.pips;
            double sizeReal = size / instrumentInfo.sizeMultiplier;

            // Look up side from tracking map
            Boolean isBuy = orderSides.get(orderId);
            String sideStr = (isBuy == null) ? "UNKNOWN" : (isBuy ? "BUY" : "SELL");

            writeLog(String.format("[%d] MBO REPLACE", count));
            writeLog(String.format("    Time:     %s", dateFormat.format(new Date())));
            writeLog(String.format("    OrderID:  %s", orderId));
            writeLog(String.format("    Side:     %s", sideStr));
            writeLog(String.format("    New Price: %.2f (raw: %d)", priceReal, price));
            writeLog(String.format("    New Size:  %.2f (raw: %d)", sizeReal, size));
            writeLog("");

            if (count % 100 == 0) {
                logWriter.flush();
            }

        } catch (IOException e) {
            Log.error("Error logging REPLACE event", e);
        }
    }

    @Override
    public void cancel(String orderId) {
        if (!isActive.get())
            return;

        try {
            long count = cancelCount.incrementAndGet();

            // Look up and remove from tracking map
            Boolean isBuy = orderSides.remove(orderId);
            String sideStr = (isBuy == null) ? "UNKNOWN" : (isBuy ? "BUY" : "SELL");

            writeLog(String.format("[%d] MBO CANCEL", count));
            writeLog(String.format("    Time:     %s", dateFormat.format(new Date())));
            writeLog(String.format("    OrderID:  %s", orderId));
            writeLog(String.format("    Side:     %s", sideStr));
            writeLog("");

            if (count % 100 == 0) {
                logWriter.flush();
            }

        } catch (IOException e) {
            Log.error("Error logging CANCEL event", e);
        }
    }

    // =================================================================
    // TRADE HANDLER
    // =================================================================

    @Override
    public void onTrade(double price, int size, TradeInfo tradeInfo) {
        if (!isActive.get())
            return;

        try {
            long count = tradeCount.incrementAndGet();
            double priceReal = price * instrumentInfo.pips;
            double sizeReal = size / instrumentInfo.sizeMultiplier;

            writeLog(String.format("[%d] TRADE", count));
            writeLog(String.format("    Time:       %s", dateFormat.format(new Date())));
            writeLog(String.format("    Price:      %.2f (raw: %.2f)", priceReal, price));
            writeLog(String.format("    Size:       %.2f (raw: %d)", sizeReal, size));
            writeLog(String.format("    Aggressor:  %s",
                    tradeInfo.isBidAggressor ? "BID (Sell order filled)" : "ASK (Buy order filled)"));
            writeLog("");

            // Log every 50 trades for better visibility of trade activity
            if (count % 50 == 0) {
                logWriter.flush();
            }

        } catch (IOException e) {
            Log.error("Error logging TRADE event", e);
        }
    }

    // =================================================================
    // LIFECYCLE & UTILITIES
    // =================================================================

    @Override
    public void stop() {
        isActive.set(false);

        try {
            if (logWriter != null) {
                // Write summary
                long uptime = System.currentTimeMillis() - initTime;
                writeLog("");
                writeLog("════════════════════════════════════════════════════════════════");
                writeLog("RAW MBO DATA LOGGER - CAPTURE STOPPED");
                writeLog("════════════════════════════════════════════════════════════════");
                writeLog("Session Summary:");
                writeLog(String.format("  MBO Sends:    %,d", sendCount.get()));
                writeLog(String.format("  MBO Replaces: %,d", replaceCount.get()));
                writeLog(String.format("  MBO Cancels:  %,d", cancelCount.get()));
                writeLog(String.format("  Trades:       %,d", tradeCount.get()));
                writeLog(String.format("  Total Events: %,d",
                        sendCount.get() + replaceCount.get() + cancelCount.get() + tradeCount.get()));
                writeLog(String.format("  Uptime:       %,d ms (%.2f seconds)",
                        uptime, uptime / 1000.0));
                writeLog("════════════════════════════════════════════════════════════════");

                logWriter.close();
                Log.info("RawMboDataLogger stopped. Logged " +
                        (sendCount.get() + replaceCount.get() + cancelCount.get() + tradeCount.get()) +
                        " events for " + alias);
            }
        } catch (IOException e) {
            Log.error("Error closing RawMboDataLogger", e);
        }
    }

    private void writeLog(String message) throws IOException {
        if (logWriter != null) {
            logWriter.write(message + "\n");
        }
    }

    @Override
    public String toString() {
        return "RawMboDataLogger[" + alias + "]";
    }
}
