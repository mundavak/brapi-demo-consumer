package com.bookmap.demo.consumer;

import com.bookmap.addons.broadcasting.api.view.BroadcasterConsumer;
import com.bookmap.addons.broadcasting.api.view.Event;
import com.bookmap.addons.broadcasting.api.view.GeneratorInfo;
import com.bookmap.addons.broadcasting.api.view.listeners.ConnectionStatusListener;
import com.bookmap.addons.broadcasting.api.view.listeners.LiveConnectionStatusListener;
import com.bookmap.addons.broadcasting.api.view.listeners.LiveEventListener;
import com.bookmap.addons.broadcasting.api.view.listeners.ProviderStatusListener;
import com.bookmap.addons.broadcasting.implementations.view.BroadcastFactory;
import com.bookmap.addons.broadcasting.implementations.base.CastUtilities;
import com.bookmap.addons.broadcasting.implementations.base.FailedToCastObject;
import com.bookmap.demo.consumer.Connector;
import com.bookmap.demo.consumer.database.RedisManager;
import com.bookmap.demo.consumer.database.TimescaleDBManager;
import com.bookmap.demo.consumer.providers.Provider;
import com.bookmap.demo.consumer.utils.SessionManager;
import com.bookmap.demo.consumer.utils.LoggingConfig;

import com.google.gson.Gson;
import velox.indicators.absorption.broadcasting.module.EventInterface;
import velox.indicators.absorption.broadcasting.module.implementations.TradeEvent;
import velox.api.layer1.*;
import velox.api.layer1.annotations.*;
import velox.api.layer1.common.ListenableHelper;
import velox.api.layer1.common.Log;
import velox.api.layer1.data.*;
import velox.api.layer1.messages.UserMessageLayersChainCreatedTargeted;
import velox.gui.StrategyPanel;

import javax.swing.*;
import java.awt.*;
import java.io.FileWriter;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Absorption Consumer - Subscribes to Absorption Indicator provider
 * Detects absorption events and liquidity sweeps during CBDR windows
 */
@Layer1Attachable
@Layer1StrategyName("Absorption Consumer")
@Layer1ApiVersion(Layer1ApiVersionValue.VERSION2)
public class AbsorptionConsumer implements
        Layer1ApiFinishable,
        Layer1ApiAdminAdapter,
        Layer1ApiInstrumentAdapter,
        Layer1CustomPanelsGetter {

    private static final String ADDON_NAME = "Absorption Consumer";
    private static final String LOG_FILE = "F:/TradingAgent/absorption_consumer.log";
    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
    private static final Provider PROVIDER = Provider.ABSORPTION_INDICATOR;
    private static final Gson gson = new Gson();

    private final Layer1ApiProvider provider;
    private BroadcasterConsumer broadcaster;
    private Connector connector;
    private final AtomicBoolean isWorking = new AtomicBoolean(false);

    private RedisManager redisManager;
    private TimescaleDBManager timescaleDBManager;
    private SessionManager sessionManager;

    // Tracking structures
    private final Map<String, String> activeSymbols = new ConcurrentHashMap<>();
    private final Map<String, String> sessionIds = new ConcurrentHashMap<>();
    private final Map<String, OrderBook> orderBooks = new ConcurrentHashMap<>();
    private final Map<String, java.util.List<InternalTradeEvent>> recentTrades = new ConcurrentHashMap<>();

    // UI components
    private JTextArea logArea;
    private JLabel statsLabel;

    // Event counters for logging
    private final java.util.concurrent.atomic.AtomicInteger stopCount = new java.util.concurrent.atomic.AtomicInteger(
            0);
    private final java.util.concurrent.atomic.AtomicInteger sweepCount = new java.util.concurrent.atomic.AtomicInteger(
            0);

    // Detection parameters
    private static final double ABSORPTION_RATIO_THRESHOLD = 0.6; // 60% absorption
    private static final long ABSORPTION_WINDOW_MS = 2000; // 2 second window
    private static final int MIN_VOLUME_THRESHOLD = 10; // Minimum volume to consider
    private static final double IMBALANCE_THRESHOLD = 0.7; // 70% imbalance

    // Batch processing
    private final BlockingQueue<TimescaleDBManager.AbsorptionEvent> batchQueue = new LinkedBlockingQueue<>(5000);
    private final ScheduledExecutorService batchProcessor = Executors.newSingleThreadScheduledExecutor(
            r -> new Thread(r, "Absorption-BatchProcessor"));
    private final ScheduledExecutorService analyzer = Executors.newSingleThreadScheduledExecutor(
            r -> new Thread(r, "Absorption-Analyzer"));
    private final ScheduledExecutorService cbdrMonitor = Executors.newSingleThreadScheduledExecutor(
            r -> new Thread(r, "Absorption-CBDRMonitor"));

    /**
     * File logging helper - writes to console, file, and UI
     */
    private void log(String level, String message) {
        String logLine = "[%s] [%s] %s".formatted(
                dateFormat.format(new Date()), level, message);

        // Write to Bookmap console using Log
        Log.info(logLine);

        // Write to file
        try (FileWriter writer = new FileWriter(LOG_FILE, true)) {
            writer.write(logLine + "\n");
        } catch (IOException e) {
            Log.error("Failed to write to log file", e);
        }

        // Update UI log area
        if (this.logArea != null) {
            SwingUtilities.invokeLater(() -> {
                this.logArea.append(logLine + "\n");
                this.logArea.setCaretPosition(this.logArea.getDocument().getLength());
            });
        }
    }

    public AbsorptionConsumer(Layer1ApiProvider provider) {
        ListenableHelper.addListeners(provider, this);
        this.provider = provider;

        // Initialize managers early (before onInstrumentAdded can be called)
        redisManager = RedisManager.getInstance();
        timescaleDBManager = TimescaleDBManager.getInstance();
        sessionManager = SessionManager.getInstance();

        // Use direct Log.info() calls for startup (same as old consumer)
        Log.info("========================================");
        Log.info("Absorption Consumer: STARTING UP");
        Log.info("========================================");
        log("INFO", "[AbsorptionConsumer] Initialized");
        log("INFO", "Log file: " + LOG_FILE);
    }

    @Override
    public void onUserMessage(Object data) {
        if (data instanceof UserMessageLayersChainCreatedTargeted message) {
            if (message.targetClass == getClass()) {
                isWorking.set(true);

                // Initialize broadcaster
                broadcaster = BroadcastFactory.getBroadcasterConsumer(provider, ADDON_NAME, this.getClass());

                // Initialize connector (same pattern as StopsIcebergsConsumer)
                connector = new Connector(provider, broadcaster, PROVIDER);

                // Set provider status listener
                broadcaster.setProviderStatusListener(new ProviderStatusListener() {
                    @Override
                    public void providerUpdateGenerator(String providerName, String providerId,
                            GeneratorInfo generator, boolean isOnline) {
                        log("INFO", "Provider update: %s, generator: %s, online: %s".formatted(
                                providerName, generator != null ? generator.getGeneratorName() : "null", isOnline));
                    }
                });

                broadcaster.start();

                Log.info("========================================");
                Log.info("Broadcaster STARTED - Now listening for Absorption events");
                Log.info("========================================");

                // Delay connection attempt to allow broadcaster to discover providers
                analyzer.schedule(() -> {
                    connectToProvider();
                }, 2, TimeUnit.SECONDS);

                // Start batch processor (every 5 seconds)
                batchProcessor.scheduleAtFixedRate(this::processBatch, 5, 5, TimeUnit.SECONDS);

                log("INFO",
                        "[AbsorptionConsumer] Started, will attempt connection to Absorption indicator in 2 seconds");
            }
        }
    }

    private void connectToProvider() {
        log("INFO", "Connecting to Absorption Indicator provider...");
        try {
            connector.connect();
            analyzer.schedule(() -> {
                try {
                    Thread.sleep(1000L);
                    if (connector.isConnected()) {
                        log("INFO", "✓ Successfully connected to Absorption Indicator");
                        java.util.List<String> generators = connector.getGeneratorsNames();
                        log("INFO", "Found " + generators.size() + " generator(s)");
                        for (String generatorName : generators) {
                            log("INFO", "Subscribing to generator: " + generatorName);
                            subscribeToGenerator(generatorName);
                        }
                    } else {
                        log("WARN", "Connection not yet established, will retry in 2 seconds...");
                        Thread.sleep(2000L);
                        connectToProvider();
                    }
                } catch (Exception e) {
                    log("ERROR", "Error during connection setup: " + e.getMessage());
                }
            }, 0, TimeUnit.MILLISECONDS);
        } catch (Exception e) {
            log("ERROR", "Failed to connect to provider: " + e.getMessage());
        }
    }

    private void subscribeToGenerator(String generatorName) {
        try {
            if (!connector.isConnected()) {
                log("WARN", "Not connected, cannot subscribe to " + generatorName);
                return;
            }

            LiveEventListener eventListener = event -> {
                if (event != null) {
                    processIncomingEvent(event);
                }
            };

            LiveConnectionStatusListener connectionListener = isSubscribed -> {
                if (isSubscribed) {
                    log("INFO", "✓ Successfully subscribed to live data: " + generatorName);
                } else {
                    log("WARN", "✗ Unsubscribed from: " + generatorName);
                }
            };

            broadcaster.subscribeToLiveData(PROVIDER.getFullName(), generatorName, eventListener, connectionListener);
        } catch (Exception e) {
            log("ERROR", "Failed to subscribe to generator " + generatorName + ": " + e.getMessage());
        }
    }

    private void processIncomingEvent(Object event) {
        try {
            // ✅ Use CastUtilities as documented in provider README
            EventInterface eventInterface = CastUtilities.castObject(event, TradeEvent.class);

            if (eventInterface instanceof TradeEvent tradeEvent) {
                processTradeEvent(tradeEvent);
            } else {
                log("WARN", "Unexpected event type: " + eventInterface.getClass().getName());
            }

        } catch (FailedToCastObject e) {
            log("ERROR", "Failed to cast event to TradeEvent: " + e.getMessage());
        } catch (Exception e) {
            log("ERROR", "Error processing incoming event: " + e.getMessage());
        }
    }

    private void processTradeEvent(TradeEvent tradeEvent) {
        try {
            // Direct field access - NO REFLECTION
            long timestampNanos = tradeEvent.getTime();
            double price = tradeEvent.getPrice();
            int size = tradeEvent.getValue(); // getValue() returns size
            boolean isBid = tradeEvent.isBid();
            int maxChainSize = tradeEvent.getMaxChainSize();

            // CRITICAL: Convert price by multiplying by 0.25 (NQ tick to index point)
            double convertedPrice = price * 0.25;

            String side = isBid ? "BUY" : "SELL";

            // Get symbol from active instruments
            String symbol = activeSymbols.isEmpty() ? "UNKNOWN" : activeSymbols.values().iterator().next();
            String sessionId = sessionIds.getOrDefault(symbol, "UNKNOWN");

            // Convert timestamp: nanoseconds → seconds for PostgreSQL (for JSON storage
            // only)
            double timestampSeconds = timestampNanos / 1_000_000_000.0;

            // Calculate significance using converted price
            double significance = calculateSignificance(convertedPrice, size, maxChainSize, isBid);

            // Log every 10th event with significance (show converted price)
            if (stopCount.incrementAndGet() % 10 == 0) {
                log("INFO",
                        "TradeEvent: %s @ %.2f (raw: %.2f), size=%d, chain=%d, significance=%.2f (threshold: 0.5)".formatted(
                                side, convertedPrice, price, size, maxChainSize, significance));
            }

            // Only store if significant
            if (significance >= 0.5) {
                // Create DB event
                TimescaleDBManager.AbsorptionEvent dbEvent = new TimescaleDBManager.AbsorptionEvent();
                dbEvent.symbol = symbol;
                dbEvent.timestamp = timestampNanos; // CRITICAL FIX: Store nanoseconds directly (TimescaleDBManager
                                                    // converts to seconds)
                dbEvent.eventType = "ABSORPTION";
                dbEvent.side = side;
                dbEvent.price = convertedPrice; // CRITICAL FIX: Use converted price (raw * 0.25)
                dbEvent.absorbedVolume = size;
                dbEvent.aggressorVolume = size;
                dbEvent.liquidityRemoved = size;
                dbEvent.absorptionRatio = maxChainSize > 0 ? (double) size / maxChainSize : 0.0;
                dbEvent.imbalanceRatio = 0.0;
                dbEvent.sessionId = sessionId;
                dbEvent.cbdrWindow = "REGULAR"; // TODO: Get actual CBDR window
                dbEvent.isInCbdr = false; // TODO: Check actual CBDR status
                dbEvent.significance = significance;
                dbEvent.metadata = "{\"maxChainSize\":%d,\"rawPrice\":%.2f}".formatted(maxChainSize, price);

                // Store to Redis with converted price
                String eventJson = gson.toJson(Map.of(
                        "timestamp", timestampSeconds,
                        "price", convertedPrice, // CRITICAL FIX: Use converted price
                        "rawPrice", price, // Store raw price for reference
                        "size", size,
                        "side", side,
                        "maxChainSize", maxChainSize,
                        "significance", significance));
                redisManager.addAbsorptionEvent(symbol, dbEvent.cbdrWindow, significance, eventJson);

                // Queue for TimescaleDB
                batchQueue.put(dbEvent);

                // Update UI
                updateUI();

                log("INFO", "✓ Stored absorption event: %s %s @ %.2f (raw: %.2f, sig=%.2f)".formatted(
                        symbol, side, convertedPrice, price, significance));
            }

        } catch (Exception e) {
            log("ERROR", "Error processing TradeEvent: " + e.getMessage());
        }
    }

    private double calculateSignificance(double price, int size, int maxChainSize, boolean isBid) {
        // Consider maxChainSize in the calculation
        double chainRatio = maxChainSize > 0 ? (double) size / maxChainSize : 1.0;
        double volumeScore = Math.min(1.0, size / 100.0);

        // Weight chain ratio heavily (absorption chains are key indicator)
        return (chainRatio * 0.6) + (volumeScore * 0.4);
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
                Log.warn("[AbsorptionConsumer] Data structure interface not available for historical data");
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
                Log.warn("[AbsorptionConsumer] No active instrument for historical data request");
                return;
            }

            Log.info("[AbsorptionConsumer] Requesting historical data: " + generatorName +
                    " from " + new java.util.Date(startTime) + " to " + new java.util.Date(endTime));

            // Request historical data from provider
            java.util.List<Object> historicalData = PROVIDER.getValueHandler().requestHistoricalData(
                    dataStructureInterface, generatorName, startTime, endTime, alias);

            if (historicalData == null || historicalData.isEmpty()) {
                Log.info("[AbsorptionConsumer] No historical data available for past 24 hours");
                return;
            }

            // Cast and process historical events
            java.util.List<Event> events = PROVIDER.getValueHandler().castEventsInOurClassLoader(historicalData);
            int processedCount = 0;
            int filteredCount = 0;

            for (Event event : events) {
                long eventTime = event.getTime();

                // Check if event was during CBDR window
                String cbdrWindow = sessionManager.getCbdrWindow(eventTime);

                if (cbdrWindow != null) {
                    // Process the historical event (same logic as live events)
                    processHistoricalAbsorptionEvent(event, cbdrWindow);
                    processedCount++;
                } else {
                    filteredCount++;
                }
            }

            Log.info("[AbsorptionConsumer] Historical data processed: " + processedCount +
                    " events stored, " + filteredCount + " filtered (outside CBDR)");

        } catch (Exception e) {
            Log.warn("[AbsorptionConsumer] Error requesting historical data", e);
        }
    }

    /**
     * Process historical absorption event with same logic as live events
     */
    private void processHistoricalAbsorptionEvent(Event event, String cbdrWindow) {
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

            long timestamp = event.getTime();

            // Determine event type
            String eventType = event.getClass().getSimpleName();
            boolean isAbsorption = eventType.contains("Absorption") || eventType.equals("TradeEvent");
            boolean isSweep = eventType.contains("Sweep");

            // Use reflection to access provider-specific fields
            double price = (double) event.getClass().getMethod("getPrice").invoke(event);
            double sizeDouble = (double) event.getClass().getMethod("getSize").invoke(event);
            long size = (long) sizeDouble;
            boolean isBid = (boolean) event.getClass().getMethod("isBid").invoke(event);
            String side = isBid ? "BUY" : "SELL";

            // Calculate significance
            double absorptionRatio = 0.8;
            double significance = calculateSignificance(absorptionRatio, size, true); // Historical = in CBDR

            // Skip low significance events
            if (significance < 0.5) {
                return;
            }

            // Create absorption event for database
            TimescaleDBManager.AbsorptionEvent dbEvent = new TimescaleDBManager.AbsorptionEvent();
            dbEvent.symbol = symbol;
            dbEvent.timestamp = timestamp;
            dbEvent.eventType = isAbsorption ? "ABSORPTION" : (isSweep ? "SWEEP" : "UNKNOWN");
            dbEvent.side = side;
            dbEvent.price = price;
            dbEvent.absorbedVolume = size;
            dbEvent.aggressorVolume = size;
            dbEvent.liquidityRemoved = size;
            dbEvent.absorptionRatio = absorptionRatio;
            dbEvent.imbalanceRatio = 0;
            dbEvent.sessionId = sessionId;
            dbEvent.cbdrWindow = cbdrWindow;
            dbEvent.isInCbdr = true; // Historical events are only from CBDR windows
            dbEvent.significance = significance;
            dbEvent.metadata = "{\"historical\":true}";

            // Queue for batch processing
            if (!batchQueue.offer(dbEvent)) {
                log("WARN", "[AbsorptionConsumer] Historical event queue full, dropping event");
            }
        } catch (Exception e) {
            Log.warn("[AbsorptionConsumer] Error processing historical absorption event", e);
        }
    }

    // OLD REFLECTION-BASED METHODS REMOVED - Now using CastUtilities pattern
    // See processTradeEvent() method above for the correct implementation

    @Override
    public void onInstrumentAdded(String alias, InstrumentInfo instrumentInfo) {
        String symbol = instrumentInfo.symbol;
        activeSymbols.put(alias, symbol);

        // Generate session ID
        String sessionId = sessionManager.generateSessionId(symbol);
        sessionIds.put(symbol, sessionId);

        // Initialize tracking structures
        orderBooks.put(symbol, new OrderBook(symbol));
        recentTrades.put(symbol, new CopyOnWriteArrayList<>());

        // Start analyzer for this symbol (every 500ms)
        analyzer.scheduleAtFixedRate(() -> analyzeAbsorption(symbol), 500, 500, TimeUnit.MILLISECONDS);

        // Start CBDR monitor for this symbol (every 10 seconds)
        cbdrMonitor.scheduleAtFixedRate(() -> updateCbdrState(symbol), 10, 10, TimeUnit.SECONDS);

        Log.info("[AbsorptionConsumer] Instrument added: " + symbol + " -> " + sessionId);
    }

    @Override
    public void onInstrumentRemoved(String alias) {
        String symbol = activeSymbols.remove(alias);
        if (symbol != null) {
            sessionIds.remove(symbol);
            orderBooks.remove(symbol);
            recentTrades.remove(symbol);
        }
        Log.info("[AbsorptionConsumer] Instrument removed: " + symbol);
    }

    /**
     * Analyze recent trades for absorption patterns
     */
    private void analyzeAbsorption(String symbol) {
        java.util.List<InternalTradeEvent> trades = recentTrades.get(symbol);
        if (trades == null || trades.isEmpty())
            return;

        long now = System.currentTimeMillis();
        long windowStart = now - ABSORPTION_WINDOW_MS;

        // Group trades by price level within the window
        Map<Double, LevelAbsorption> levels = new HashMap<>();

        for (InternalTradeEvent trade : trades) {
            if (trade.timestamp < windowStart)
                continue;

            LevelAbsorption level = levels.computeIfAbsent(trade.price, k -> new LevelAbsorption(trade.price));
            if (trade.isBuy) {
                level.buyVolume += trade.size;
            } else {
                level.sellVolume += trade.size;
            }
            level.totalVolume += trade.size;
            level.lastTimestamp = trade.timestamp;
        }

        // Analyze each level for absorption
        for (LevelAbsorption level : levels.values()) {
            if (level.totalVolume < MIN_VOLUME_THRESHOLD)
                continue;

            double absorptionRatio = calculateAbsorptionRatio(level);
            double imbalanceRatio = calculateImbalanceRatio(level);

            if (absorptionRatio >= ABSORPTION_RATIO_THRESHOLD) {
                detectAbsorption(symbol, level, absorptionRatio, imbalanceRatio, now);
            } else if (imbalanceRatio >= IMBALANCE_THRESHOLD) {
                detectSweep(symbol, level, imbalanceRatio, now);
            }
        }
    }

    /**
     * Calculate absorption ratio (passive liquidity absorbed vs aggressive volume)
     */
    private double calculateAbsorptionRatio(LevelAbsorption level) {
        long aggressorVolume = Math.max(level.buyVolume, level.sellVolume);
        long passiveVolume = Math.min(level.buyVolume, level.sellVolume);

        if (aggressorVolume == 0)
            return 0;

        // Higher ratio means more absorption (liquidity soaking up aggression)
        return (double) passiveVolume / aggressorVolume;
    }

    /**
     * Calculate imbalance ratio (directional bias)
     */
    private double calculateImbalanceRatio(LevelAbsorption level) {
        if (level.totalVolume == 0)
            return 0;

        long dominantVolume = Math.max(level.buyVolume, level.sellVolume);
        return (double) dominantVolume / level.totalVolume;
    }

    /**
     * Detect and record absorption event
     */
    private void detectAbsorption(String symbol, LevelAbsorption level, double absorptionRatio,
            double imbalanceRatio, long timestamp) {
        String sessionId = sessionIds.get(symbol);
        String cbdrWindow = sessionManager.getCbdrWindow(timestamp);
        boolean isInCbdr = cbdrWindow != null;

        // Determine side (who's absorbing)
        String side = level.buyVolume > level.sellVolume ? "SELL" : "BUY"; // Passive side
        long absorbedVolume = Math.min(level.buyVolume, level.sellVolume);
        long aggressorVolume = Math.max(level.buyVolume, level.sellVolume);

        // Calculate significance (higher during CBDR windows)
        double significance = calculateSignificance(absorptionRatio, level.totalVolume, isInCbdr);

        // Only record significant events
        if (significance < 0.5)
            return;

        // Create event data for Redis
        Map<String, Object> eventData = new HashMap<>();
        eventData.put("event_id", "absorption_" + timestamp);
        eventData.put("timestamp", timestamp);
        eventData.put("price", level.price);
        eventData.put("absorbed_volume", absorbedVolume);
        eventData.put("aggressor_volume", aggressorVolume);
        eventData.put("absorption_ratio", absorptionRatio);
        eventData.put("imbalance_ratio", imbalanceRatio);
        eventData.put("side", side);
        eventData.put("cbdr_window", cbdrWindow);
        eventData.put("is_in_cbdr", isInCbdr);
        eventData.put("significance", significance);

        String eventJson = gson.toJson(eventData);

        // Store in Redis
        if (isInCbdr) {
            redisManager.addAbsorptionEvent(symbol, cbdrWindow, significance, eventJson);
        } else {
            redisManager.addAbsorptionEvent(symbol, "REGULAR", significance, eventJson);
        }

        // Create metadata
        Map<String, Object> metadata = new HashMap<>();
        metadata.put("buy_volume", level.buyVolume);
        metadata.put("sell_volume", level.sellVolume);
        metadata.put("trading_mode", sessionManager.getRecommendedTradingMode());

        // Queue for TimescaleDB
        TimescaleDBManager.AbsorptionEvent dbEvent = new TimescaleDBManager.AbsorptionEvent();
        dbEvent.symbol = symbol;
        dbEvent.timestamp = timestamp;
        dbEvent.eventType = "ABSORPTION";
        dbEvent.side = side;
        dbEvent.price = level.price;
        dbEvent.absorbedVolume = absorbedVolume;
        dbEvent.aggressorVolume = aggressorVolume;
        dbEvent.liquidityRemoved = absorbedVolume;
        dbEvent.absorptionRatio = absorptionRatio;
        dbEvent.imbalanceRatio = imbalanceRatio;
        dbEvent.sessionId = sessionId;
        dbEvent.cbdrWindow = cbdrWindow;
        dbEvent.isInCbdr = isInCbdr;
        dbEvent.significance = significance;
        dbEvent.metadata = gson.toJson(metadata);

        try {
            batchQueue.put(dbEvent);
        } catch (InterruptedException e) {
            log("WARN", "Failed to queue absorption event: " + e.getMessage());
        }

        log("INFO", "ABSORPTION detected: %s at %.2f, ratio: %.2f, significance: %.2f %s".formatted(
                symbol, level.price, absorptionRatio, significance,
                isInCbdr ? "[CBDR: " + cbdrWindow + "]" : ""));

        // Publish signal if significant
        if (significance >= 0.7) {
            String signal = "ABSORPTION:%s:%.2f:%.2f:%s".formatted(
                    side, level.price, significance, cbdrWindow != null ? cbdrWindow : "REGULAR");
            redisManager.publishSignal(symbol, signal);
        }
    }

    /**
     * Detect liquidity sweep
     */
    private void detectSweep(String symbol, LevelAbsorption level, double imbalanceRatio, long timestamp) {
        String sessionId = sessionIds.get(symbol);
        String cbdrWindow = sessionManager.getCbdrWindow(timestamp);
        boolean isInCbdr = cbdrWindow != null;

        String side = level.buyVolume > level.sellVolume ? "BUY" : "SELL";
        long dominantVolume = Math.max(level.buyVolume, level.sellVolume);

        double significance = calculateSignificance(imbalanceRatio, level.totalVolume, isInCbdr);

        if (significance < 0.6)
            return;

        // Create event
        Map<String, Object> eventData = new HashMap<>();
        eventData.put("event_id", "sweep_" + timestamp);
        eventData.put("timestamp", timestamp);
        eventData.put("price", level.price);
        eventData.put("volume", dominantVolume);
        eventData.put("imbalance_ratio", imbalanceRatio);
        eventData.put("side", side);
        eventData.put("significance", significance);

        String eventJson = gson.toJson(eventData);

        if (isInCbdr) {
            redisManager.addAbsorptionEvent(symbol, cbdrWindow, significance, eventJson);
        }

        // Queue for TimescaleDB
        TimescaleDBManager.AbsorptionEvent dbEvent = new TimescaleDBManager.AbsorptionEvent();
        dbEvent.symbol = symbol;
        dbEvent.timestamp = timestamp;
        dbEvent.eventType = "SWEEP";
        dbEvent.side = side;
        dbEvent.price = level.price;
        dbEvent.absorbedVolume = 0;
        dbEvent.aggressorVolume = dominantVolume;
        dbEvent.liquidityRemoved = dominantVolume;
        dbEvent.absorptionRatio = 0;
        dbEvent.imbalanceRatio = imbalanceRatio;
        dbEvent.sessionId = sessionId;
        dbEvent.cbdrWindow = cbdrWindow;
        dbEvent.isInCbdr = isInCbdr;
        dbEvent.significance = significance;
        dbEvent.metadata = "{}";

        try {
            batchQueue.put(dbEvent);
        } catch (InterruptedException e) {
            log("WARN", "Failed to queue sweep event: " + e.getMessage());
        }

        log("INFO", "SWEEP detected: %s %s at %.2f, volume: %d".formatted(
                symbol, side, level.price, dominantVolume));
    }

    /**
     * Calculate significance score based on multiple factors
     */
    private double calculateSignificance(double ratio, long volume, boolean isInCbdr) {
        double significance = 0;

        // Base score from ratio
        significance += ratio * 0.5;

        // Volume contribution (normalized)
        double volumeScore = Math.min(1.0, volume / 100.0);
        significance += volumeScore * 0.3;

        // CBDR bonus
        if (isInCbdr) {
            significance += 0.2;
        }

        return Math.min(1.0, significance);
    }

    /**
     * Update CBDR window state in Redis
     */
    private void updateCbdrState(String symbol) {
        long now = System.currentTimeMillis();
        String cbdrWindow = sessionManager.getCbdrWindow(now);

        if (cbdrWindow != null) {
            // Get recent absorption events for this window
            java.util.List<String> recentEvents = redisManager.getTopAbsorptionEvents(symbol, cbdrWindow, 20);

            // Calculate window bias
            int bullishEvents = 0;
            int bearishEvents = 0;

            for (String eventJson : recentEvents) {
                try {
                    Map<String, Object> event = gson.fromJson(eventJson, Map.class);
                    String side = (String) event.get("side");
                    if ("BUY".equals(side))
                        bullishEvents++;
                    else if ("SELL".equals(side))
                        bearishEvents++;
                } catch (Exception e) {
                    // Skip invalid events
                }
            }

            String bias = "NEUTRAL";
            if (bullishEvents > bearishEvents * 1.5) {
                bias = "BULLISH";
            } else if (bearishEvents > bullishEvents * 1.5) {
                bias = "BEARISH";
            }

            // Update CBDR state in Redis
            Map<String, String> cbdrData = new HashMap<>();
            cbdrData.put("status", "ACTIVE");
            cbdrData.put("bias", bias);
            cbdrData.put("start_time", String.valueOf(sessionManager.getCbdrWindowStart(cbdrWindow, now)));
            cbdrData.put("end_time", String.valueOf(sessionManager.getCbdrWindowEnd(cbdrWindow, now)));
            cbdrData.put("event_count", String.valueOf(recentEvents.size()));
            cbdrData.put("bullish_events", String.valueOf(bullishEvents));
            cbdrData.put("bearish_events", String.valueOf(bearishEvents));

            redisManager.updateCbdrWindow(symbol, cbdrWindow, cbdrData);

            // Update market bias if strong signal
            if (!bias.equals("NEUTRAL")) {
                double confidence = Math.abs(bullishEvents - bearishEvents)
                        / (double) Math.max(1, bullishEvents + bearishEvents);
                redisManager.updateMarketBias(symbol, bias, confidence,
                        "%s window absorption: %d vs %d".formatted(cbdrWindow, bullishEvents, bearishEvents));
            }
        }
    }

    /**
     * Process batch to TimescaleDB
     */
    private void processBatch() {
        java.util.List<TimescaleDBManager.AbsorptionEvent> batch = new ArrayList<>();
        batchQueue.drainTo(batch, 500);

        if (!batch.isEmpty()) {
            log("INFO", "[AbsorptionConsumer] Processing batch of %d events to TimescaleDB...".formatted(
                    batch.size()));
            timescaleDBManager.batchInsertAbsorptionEvents(batch);
            log("INFO", "✓ [AbsorptionConsumer] Successfully wrote %d absorption events to TimescaleDB".formatted(
                    batch.size()));
        }
        // Removed LOGGER.fine() - no need to spam logs for empty queue
    }

    @Override
    public void finish() {
        try {
            if (broadcaster != null) {
                broadcaster.finish();
            }

            // Process remaining batch
            processBatch();

            // Shutdown executors
            batchProcessor.shutdown();
            analyzer.shutdown();
            cbdrMonitor.shutdown();

            if (!batchProcessor.awaitTermination(10, TimeUnit.SECONDS)) {
                batchProcessor.shutdownNow();
            }
            if (!analyzer.awaitTermination(10, TimeUnit.SECONDS)) {
                analyzer.shutdownNow();
            }
            if (!cbdrMonitor.awaitTermination(10, TimeUnit.SECONDS)) {
                cbdrMonitor.shutdownNow();
            }

            Log.info("[AbsorptionConsumer] Finished and cleaned up");
        } catch (Exception e) {
            Log.warn("[AbsorptionConsumer] Error during finish", e);
            batchProcessor.shutdownNow();
            analyzer.shutdownNow();
            cbdrMonitor.shutdownNow();
        }
    }

    /**
     * Trade event data structure (internal use)
     */
    private static class InternalTradeEvent {
        long timestamp;
        double price;
        long size;
        boolean isBuy;
    }

    /**
     * Level absorption tracker
     */
    private static class LevelAbsorption {
        double price;
        long buyVolume;
        long sellVolume;
        long totalVolume;
        long lastTimestamp;

        LevelAbsorption(double price) {
            this.price = price;
        }
    }

    /**
     * Order book tracker
     */
    private static class OrderBook {
        String symbol;
        Map<Double, Long> bids = new ConcurrentHashMap<>();
        Map<Double, Long> asks = new ConcurrentHashMap<>();

        OrderBook(String symbol) {
            this.symbol = symbol;
        }

        void processTrade(InternalTradeEvent trade) {
            // Update liquidity after trade
            Map<Double, Long> levels = trade.isBuy ? asks : bids;
            levels.compute(trade.price, (k, v) -> {
                if (v == null)
                    return 0L;
                long remaining = v - trade.size;
                return remaining > 0 ? remaining : null;
            });
        }
    }

    /**
     * Update UI statistics display
     */
    private void updateUI() {
        if (this.statsLabel != null) {
            SwingUtilities.invokeLater(() -> {
                StringBuilder stats = new StringBuilder("<html>");
                stats.append("<b>ABSORPTION EVENTS STATISTICS</b><br><br>");
                stats.append("<b>Event Counts:</b><br>");
                stats.append("&nbsp;&nbsp;Absorption Events: ").append(this.stopCount.get()).append("<br>");
                stats.append("&nbsp;&nbsp;Sweep Events: ").append(this.sweepCount.get()).append("<br><br>");
                stats.append("<b>Active Instruments:</b><br>");
                stats.append("&nbsp;&nbsp;Count: ").append(this.activeSymbols.size()).append("<br>");
                if (!this.activeSymbols.isEmpty()) {
                    stats.append("&nbsp;&nbsp;Symbols: ").append(String.join(", ", this.activeSymbols.keySet()))
                            .append("<br>");
                }
                stats.append("</html>");
                this.statsLabel.setText(stats.toString());
            });
        }
    }

    /**
     * Create custom GUI panel for this addon
     */
    @Override
    public StrategyPanel[] getCustomGuiFor(String alias, String indicatorName) {
        if (!this.isWorking.get()) {
            return new StrategyPanel[0];
        }

        StrategyPanel mainPanel = new StrategyPanel("Absorption Events - " + alias);
        mainPanel.setLayout(new BorderLayout());

        // Statistics panel at top
        this.statsLabel = new JLabel("<html><b>Waiting for events...</b></html>");
        JPanel statsPanel = new JPanel(new BorderLayout());
        statsPanel.add(this.statsLabel, BorderLayout.NORTH);

        // Log area in center with scrolling
        this.logArea = new JTextArea(20, 60);
        this.logArea.setEditable(false);
        this.logArea.setBackground(Color.BLACK);
        this.logArea.setForeground(Color.GREEN);
        this.logArea.setFont(new Font("Monospaced", Font.PLAIN, 12));
        JScrollPane scrollPane = new JScrollPane(this.logArea);

        mainPanel.add(statsPanel, BorderLayout.NORTH);
        mainPanel.add(scrollPane, BorderLayout.CENTER);

        return new StrategyPanel[] { mainPanel };
    }
}
