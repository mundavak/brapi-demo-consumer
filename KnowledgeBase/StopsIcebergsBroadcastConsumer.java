package com.bookmap.demo.consumer;

import com.bookmap.addons.broadcasting.api.view.BroadcasterConsumer;
import com.bookmap.addons.broadcasting.api.view.Event;
import com.bookmap.addons.broadcasting.api.view.GeneratorInfo;
import com.bookmap.addons.broadcasting.api.view.listeners.ConnectionStatusListener;
import com.bookmap.addons.broadcasting.api.view.listeners.LiveConnectionStatusListener;
import com.bookmap.addons.broadcasting.api.view.listeners.LiveEventListener;
import com.bookmap.addons.broadcasting.api.view.listeners.ProviderStatusListener;
import com.bookmap.addons.broadcasting.implementations.view.BroadcastFactory;
import com.bookmap.demo.consumer.database.RedisManager;
import com.bookmap.demo.consumer.database.TimescaleDBManager;
import com.bookmap.demo.consumer.providers.Provider;
import com.bookmap.demo.consumer.utils.SessionManager;
import velox.api.layer1.*;
import velox.api.layer1.annotations.*;
import velox.api.layer1.common.ListenableHelper;
import velox.api.layer1.common.Log;
import velox.api.layer1.data.*;
import velox.api.layer1.messages.UserMessageLayersChainCreatedTargeted;

import java.io.FileWriter;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Stops & Icebergs Broadcasting Consumer
 * Subscribes to SIT_INDICATOR provider and stores detected events to
 * TimescaleDB
 */
@Layer1Attachable
@Layer1StrategyName("Stops & Icebergs Consumer")
@Layer1ApiVersion(Layer1ApiVersionValue.VERSION2)
public class StopsIcebergsBroadcastConsumer implements
        Layer1ApiFinishable,
        Layer1ApiAdminAdapter,
        Layer1ApiInstrumentAdapter {

    private static final String ADDON_NAME = "Stops & Icebergs Consumer";
    private static final String LOG_FILE = "F:/TradingAgent/stops_icebergs_broadcast.log";
    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
    private static final Provider PROVIDER = Provider.SIT_INDICATOR;

    private final Layer1ApiProvider provider;
    private BroadcasterConsumer broadcaster;
    private final AtomicBoolean isWorking = new AtomicBoolean(false);

    // Session tracking
    private final Map<String, String> activeSymbols = new ConcurrentHashMap<>();
    private final Map<String, String> sessionIds = new ConcurrentHashMap<>();

    // Batch processing
    private final BlockingQueue<TimescaleDBManager.StopIcebergEvent> batchQueue = new LinkedBlockingQueue<>(5000);
    private final ScheduledExecutorService batchProcessor = Executors.newSingleThreadScheduledExecutor(
            r -> new Thread(r, "StopsIcebergs-BatchProcessor"));

    // Database manager
    private final RedisManager redisManager = RedisManager.getInstance();
    private final TimescaleDBManager dbManager = TimescaleDBManager.getInstance();
    private final SessionManager sessionManager = SessionManager.getInstance();

    /**
     * File logging helper - writes to both console (via Log) and file
     * Same pattern as old StopsIcebergsConsumer.java
     */
    private void log(String level, String message) {
        String logLine = String.format("[%s] [%s] %s", 
            dateFormat.format(new Date()), level, message);
        
        // Write to Bookmap console using Log (same as old consumer)
        Log.info(logLine);
        
        // Write to file
        try (FileWriter writer = new FileWriter(LOG_FILE, true)) {
            writer.write(logLine + "\n");
        } catch (IOException e) {
            Log.error("Failed to write to log file", e);
        }
    }

    public StopsIcebergsBroadcastConsumer(Layer1ApiProvider provider) {
        ListenableHelper.addListeners(provider, this);
        this.provider = provider;

        // Start batch processing every 5 seconds
        batchProcessor.scheduleAtFixedRate(this::processBatch, 5, 5, TimeUnit.SECONDS);
        
        // Use direct Log.info() calls for startup (same as old consumer)
        Log.info("========================================");
        Log.info("Stops & Icebergs Consumer: STARTING UP");
        Log.info("========================================");
        log("INFO", "[StopsIcebergsConsumer] Initialized");
        log("INFO", "Log file: " + LOG_FILE);
    }

    @Override
    public void onUserMessage(Object data) {
        if (data instanceof UserMessageLayersChainCreatedTargeted message) {
            if (message.targetClass == getClass()) {
                isWorking.set(true);
                broadcaster = BroadcastFactory.getBroadcasterConsumer(provider, ADDON_NAME, this.getClass());

                // Set provider status listener
                broadcaster.setProviderStatusListener(new ProviderStatusListener() {
                    @Override
                    public void providerUpdateGenerator(String providerName, String providerId,
                            GeneratorInfo generator, boolean isOnline) {
                        log("INFO", String.format("Provider update: %s, generator: %s, online: %s",
                                providerName, generator != null ? generator.getGeneratorName() : "null", isOnline));
                    }
                });

                broadcaster.start();

                Log.info("========================================");
                Log.info("Broadcaster STARTED - Now listening for Stop/Iceberg events");
                Log.info("========================================");

                // Delay connection to allow broadcaster to discover providers
                batchProcessor.schedule(() -> {
                    connectToProvider();
                }, 2, TimeUnit.SECONDS);

                log("INFO", "[StopsIcebergsConsumer] Started, will attempt connection in 2 seconds");
            }
        }
    }

    private void connectToProvider() {
        Log.info("[StopsIcebergsConsumer] Attempting to connect to provider: " + PROVIDER.getFullName());

        // List all available providers for debugging
        try {
            java.util.List<String> availableProviders = broadcaster.getAvailableProviders();
            Log.info("[StopsIcebergsConsumer] Available providers: " + availableProviders);
        } catch (Exception e) {
            Log.warn("[StopsIcebergsConsumer] Could not list available providers", e);
        }

        // Use proper ConnectionStatusListener instead of inline callback
        broadcaster.connectToProvider(PROVIDER.getFullName(), new ConnectionStatusListener() {
            @Override
            public void reactToStatusChanges(boolean isConnected) {
                if (isConnected) {
                    Log.info("[StopsIcebergsConsumer] Successfully connected to " + PROVIDER.getShortName());
                    subscribeToGenerators();
                } else {
                    Log.warn("[StopsIcebergsConsumer] Failed to connect to " + PROVIDER.getShortName() +
                            ". Provider may not be loaded on this instrument. Will retry in 5 seconds...");

                    // Retry connection after 5 seconds
                    batchProcessor.schedule(() -> connectToProvider(), 5, TimeUnit.SECONDS);
                }
            }
        });
    }

    private void subscribeToGenerators() {
        try {
            List<GeneratorInfo> generators = broadcaster.getGeneratorsInfo(PROVIDER.getFullName());
            if (generators == null || generators.isEmpty()) {
                Log.warn("[StopsIcebergsConsumer] No generators found for " + PROVIDER.getShortName());
                return;
            }

            for (GeneratorInfo genInfo : generators) {
                subscribeToGenerator(genInfo);
            }
        } catch (Exception e) {
            Log.warn("[StopsIcebergsConsumer] Error subscribing to generators", e);
        }
    }

    private void subscribeToGenerator(GeneratorInfo genInfo) {
        try {
            String generatorName = genInfo.getGeneratorName();
            Log.info("[StopsIcebergsConsumer] Setting up event listener for generator: " + generatorName);

            // Request historical data for last 24 hours to backfill CBDR gaps
            requestHistoricalData(generatorName);

            LiveEventListener eventListener = o -> {
                try {
                    Log.info("[StopsIcebergsConsumer] ✓ Event received from generator: " + generatorName +
                            ", event class: " + (o != null ? o.getClass().getName() : "null"));

                    // Find the instrument alias for this event
                    String symbol = null;
                    String sessionId = null;

                    for (Map.Entry<String, String> entry : activeSymbols.entrySet()) {
                        symbol = entry.getValue();
                        sessionId = sessionIds.get(entry.getKey());
                        break; // Use first active symbol
                    }

                    if (symbol == null || sessionId == null) {
                        Log.warn("[StopsIcebergsConsumer] No active symbol/session, skipping event");
                        return;
                    }

                    boolean inCbdr = sessionManager.isInCbdrWindow();
                    String cbdrWindow = sessionManager.getCbdrWindow(System.currentTimeMillis());

                    // Filter events outside CBDR windows
                    if (!inCbdr) {
                        return;
                    }

                    Log.info("[StopsIcebergsConsumer] Symbol: " + symbol + ", CBDR: " + cbdrWindow);

                    // Cast the event using the SitValueHandler
                    Event event = PROVIDER.getValueHandler().castEventInOurClassLoader(o);
                    if (event == null) {
                        Log.warn("[StopsIcebergsConsumer] Failed to cast event");
                        return;
                    }

                    // Cast to EventInterface to access methods
                    velox.indicators.sionchart.broadcasting.EventInterface sitEvent = (velox.indicators.sionchart.broadcasting.EventInterface) event;

                    // Create StopIcebergEvent object
                    TimescaleDBManager.StopIcebergEvent dbEvent = new TimescaleDBManager.StopIcebergEvent();
                    dbEvent.symbol = symbol;
                    dbEvent.timestamp = event.getTime();
                    dbEvent.eventType = sitEvent.getType() != null ? sitEvent.getType().toString() : "UNKNOWN";
                    dbEvent.side = sitEvent.isBid() ? "BID" : "ASK";
                    dbEvent.price = sitEvent.getPrice();
                    dbEvent.detectedSize = (long) sitEvent.getSize();
                    dbEvent.estimatedTotal = (long) sitEvent.getTotalSize();
                    dbEvent.fillCount = 1;
                    dbEvent.confidence = 0.8;
                    dbEvent.durationMs = 0;
                    dbEvent.sessionId = sessionId;
                    dbEvent.cbdrWindow = cbdrWindow;
                    dbEvent.metadata = String.format("{\"price\":%.2f,\"size\":%d}",
                            (double) sitEvent.getPrice(), (long) sitEvent.getSize());

                    Log.info(String.format("[StopsIcebergsConsumer] %s %s @ %.2f, size=%d, total=%d %s",
                            dbEvent.eventType, dbEvent.side, (double) dbEvent.price,
                            (long) dbEvent.detectedSize, (long) dbEvent.estimatedTotal,
                            inCbdr ? "[CBDR:" + cbdrWindow + "]" : ""));

                    // *** Write to Redis immediately for hot storage ***
                    try {
                        String eventJson = String.format(
                            "{\"symbol\":\"%s\",\"timestamp\":%d,\"eventType\":\"%s\",\"side\":\"%s\"," +
                            "\"price\":%.2f,\"detectedSize\":%d,\"estimatedTotal\":%d,\"sessionId\":\"%s\"," +
                            "\"cbdrWindow\":\"%s\",\"metadata\":%s}",
                            dbEvent.symbol, dbEvent.timestamp, dbEvent.eventType, dbEvent.side,
                            (double) dbEvent.price, (long) dbEvent.detectedSize, (long) dbEvent.estimatedTotal,
                            dbEvent.sessionId, dbEvent.cbdrWindow, dbEvent.metadata);
                        
                        redisManager.addStopIcebergEvent(dbEvent.symbol, dbEvent.eventType, dbEvent.timestamp, eventJson);
                        
                        Log.info(String.format("[StopsIcebergsConsumer] ✓ Wrote to Redis: %s:%s", 
                            dbEvent.eventType, dbEvent.symbol));
                    } catch (Exception redisEx) {
                        Log.warn("[StopsIcebergsConsumer] Failed to write to Redis: " + redisEx.getMessage());
                    }

                    // Queue for batch write to TimescaleDB
                    if (!batchQueue.offer(dbEvent)) {
                        log("WARN", "Event queue full, dropping event for " + symbol);
                    } else {
                        Log.info(String.format("[StopsIcebergsConsumer] Queued for DB (queue: %d/%d)",
                                batchQueue.size(), batchQueue.remainingCapacity() + batchQueue.size()));
                    }

                } catch (Exception e) {
                    log("WARN", "Error processing event: " + e.getMessage());
                    Log.warn("[StopsIcebergsConsumer] Exception: " + e.getClass().getName() + ": " + e.getMessage());
                }
            };

            LiveConnectionStatusListener subscriptionListener = isSubscribed -> {
                if (isSubscribed) {
                    Log.info("[StopsIcebergsConsumer] Successfully subscribed to live data: " + generatorName);
                } else {
                    Log.info("[StopsIcebergsConsumer] Unsubscribed from live data: " + generatorName);
                }
            };

            broadcaster.subscribeToLiveData(PROVIDER.getFullName(), generatorName,
                    eventListener, subscriptionListener);

            Log.info("[StopsIcebergsConsumer] Subscribed to generator: " + generatorName);
        } catch (Exception e) {
            Log.warn("[StopsIcebergsConsumer] Error subscribing to generator", e);
        }
    }

    /**
     * Request historical data for last 24 hours to backfill CBDR gaps
     */
    private void requestHistoricalData(String generatorName) {
        try {
            // Get data structure interface for querying historical data
            com.bookmap.addons.broadcasting.api.view.BrDataStructureInterface dataStructureInterface = broadcaster
                    .getDataStructureInterface(PROVIDER.getFullName());

            if (dataStructureInterface == null) {
                Log.warn("[StopsIcebergsConsumer] Data structure interface not available for historical data");
                return;
            }

            // Calculate time range: last 24 hours
            long endTime = System.currentTimeMillis();
            long startTime = endTime - (24 * 60 * 60 * 1000L); // 24 hours ago

            // Get instrument alias from active symbols
            String alias = null;
            for (Map.Entry<String, String> entry : activeSymbols.entrySet()) {
                alias = entry.getKey();
                break; // Use first active instrument
            }

            if (alias == null) {
                Log.warn("[StopsIcebergsConsumer] No active instrument for historical data request");
                return;
            }

            Log.info("[StopsIcebergsConsumer] Requesting historical data: " + generatorName +
                    " from " + new java.util.Date(startTime) + " to " + new java.util.Date(endTime));

            // Request historical data from provider
            List<Object> historicalData = PROVIDER.getValueHandler().requestHistoricalData(
                    dataStructureInterface, generatorName, startTime, endTime, alias);

            if (historicalData == null || historicalData.isEmpty()) {
                Log.info("[StopsIcebergsConsumer] No historical data available for past 24 hours");
                return;
            }

            // Cast and process historical events
            List<Event> events = PROVIDER.getValueHandler().castEventsInOurClassLoader(historicalData);
            int processedCount = 0;
            int filteredCount = 0;

            for (Event event : events) {
                long eventTime = event.getTime();

                // Check if event was during CBDR window
                String cbdrWindow = sessionManager.getCbdrWindow(eventTime);

                if (cbdrWindow != null) {
                    // Process the historical event (same logic as live events)
                    processHistoricalEvent(event, generatorName, cbdrWindow);
                    processedCount++;
                } else {
                    filteredCount++;
                }
            }

            Log.info("[StopsIcebergsConsumer] Historical data processed: " + processedCount +
                    " events stored, " + filteredCount + " filtered (outside CBDR)");

        } catch (Exception e) {
            Log.warn("[StopsIcebergsConsumer] Error requesting historical data", e);
        }
    }

    /**
     * Process historical event with same logic as live events
     */
    private void processHistoricalEvent(Event event, String generatorName, String cbdrWindow) {
        try {
            // Get symbol and session
            String symbol = null;
            String sessionId = null;
            for (Map.Entry<String, String> entry : activeSymbols.entrySet()) {
                symbol = entry.getValue();
                sessionId = sessionIds.get(entry.getKey());
                break;
            }

            if (symbol == null || sessionId == null) {
                return;
            }

            // Cast to EventInterface to access methods
            velox.indicators.sionchart.broadcasting.EventInterface sitEvent = (velox.indicators.sionchart.broadcasting.EventInterface) event;

            // Create StopIcebergEvent object
            TimescaleDBManager.StopIcebergEvent dbEvent = new TimescaleDBManager.StopIcebergEvent();
            dbEvent.symbol = symbol;
            dbEvent.timestamp = event.getTime();
            dbEvent.eventType = sitEvent.getType() != null ? sitEvent.getType().toString() : "UNKNOWN";
            dbEvent.side = sitEvent.isBid() ? "BID" : "ASK";
            dbEvent.price = sitEvent.getPrice();
            dbEvent.detectedSize = (long) sitEvent.getSize();
            dbEvent.estimatedTotal = (long) sitEvent.getTotalSize();
            dbEvent.fillCount = 1;
            dbEvent.confidence = 0.8;
            dbEvent.durationMs = 0;
            dbEvent.sessionId = sessionId;
            dbEvent.cbdrWindow = cbdrWindow;
            dbEvent.metadata = String.format("{\"price\":%.2f,\"size\":%d,\"historical\":true}",
                    (double) sitEvent.getPrice(), (long) sitEvent.getSize());

            // Queue for batch processing
            if (!batchQueue.offer(dbEvent)) {
                log("WARN", "[StopsIcebergsConsumer] Historical event queue full, dropping event");
            }
        } catch (Exception e) {
            Log.warn("[StopsIcebergsConsumer] Error processing historical event", e);
        }
    }

    @Override
    public void onInstrumentAdded(String alias, InstrumentInfo instrumentInfo) {
        activeSymbols.put(alias, instrumentInfo.symbol);
        String sessionId = sessionManager.generateSessionId(instrumentInfo.symbol);
        sessionIds.put(alias, sessionId);
        Log.info("[StopsIcebergsConsumer] Instrument added: " + instrumentInfo.symbol + " -> " + sessionId);
    }

    @Override
    public void onInstrumentRemoved(String alias) {
        String symbol = activeSymbols.remove(alias);
        sessionIds.remove(alias);
        Log.info("[StopsIcebergsConsumer] Instrument removed: " + symbol);
    }

    @Override
    public void finish() {
        try {
            if (broadcaster != null) {
                broadcaster.finish();
            }
            batchProcessor.shutdown();
            if (!batchProcessor.awaitTermination(10, TimeUnit.SECONDS)) {
                batchProcessor.shutdownNow();
            }
            processBatch();
            Log.info("[StopsIcebergsConsumer] Finished and cleaned up");
        } catch (Exception e) {
            Log.warn("[StopsIcebergsConsumer] Error during finish", e);
        }
    }

    private void processBatch() {
        List<TimescaleDBManager.StopIcebergEvent> batch = new ArrayList<>();
        batchQueue.drainTo(batch, 500);

        if (!batch.isEmpty()) {
            log("INFO", String.format("[StopsIcebergsConsumer] Processing batch of %d events to TimescaleDB...",
                    batch.size()));
            dbManager.batchInsertStopIcebergEvents(batch);
            log("INFO", String.format(
                    "[StopsIcebergsConsumer] ✓ Successfully wrote %d stop/iceberg events to TimescaleDB", batch.size()));
        }
        // Empty queue - no logging needed to avoid spam
    }
}
