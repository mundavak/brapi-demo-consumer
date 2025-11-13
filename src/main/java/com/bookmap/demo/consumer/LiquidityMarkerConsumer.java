package com.bookmap.demo.consumer;

import com.bookmap.addons.broadcasting.api.view.BroadcasterConsumer;
import com.bookmap.addons.broadcasting.api.view.GeneratorInfo;
import com.bookmap.addons.broadcasting.api.view.listeners.LiveConnectionStatusListener;
import com.bookmap.addons.broadcasting.api.view.listeners.LiveEventListener;
import com.bookmap.addons.broadcasting.api.view.listeners.ProviderStatusListener;
import com.bookmap.addons.broadcasting.implementations.view.BroadcastFactory;
import com.bookmap.demo.consumer.database.RedisManager;
import com.bookmap.demo.consumer.database.TimescaleDBManager;
import com.bookmap.demo.consumer.providers.Provider;
import com.bookmap.demo.consumer.utils.SessionManager;
import com.bookmap.demo.consumer.utils.EventFieldExtractor;
import velox.api.layer1.Layer1ApiAdminAdapter;
import velox.api.layer1.Layer1ApiFinishable;
import velox.api.layer1.Layer1ApiInstrumentAdapter;
import velox.api.layer1.Layer1ApiProvider;
import velox.api.layer1.Layer1CustomPanelsGetter;
import velox.api.layer1.annotations.Layer1ApiVersion;
import velox.api.layer1.annotations.Layer1ApiVersionValue;
import velox.api.layer1.annotations.Layer1Attachable;
import velox.api.layer1.annotations.Layer1StrategyName;
import velox.api.layer1.common.ListenableHelper;
import velox.api.layer1.data.InstrumentInfo;
import velox.api.layer1.messages.Layer1ApiUserMessageReloadStrategyGui;
import velox.api.layer1.messages.UserMessageLayersChainCreatedTargeted;
import velox.gui.StrategyPanel;

import javax.swing.*;
import java.awt.*;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.List;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Consumer for Bookmap Liquidity Markers Indicator Broadcasting API
 * Captures liquidity level events (significant support/resistance zones
 * identified by institutional order flow analysis)
 * and stores them in Redis (hot storage) + TimescaleDB (cold storage).
 * 
 * Liquidity levels indicate price barriers where significant volume rests,
 * often representing institutional buy/sell zones.
 */
@Layer1Attachable
@Layer1StrategyName("Liquidity Marker Broadcasting Consumer")
@Layer1ApiVersion(Layer1ApiVersionValue.VERSION2)
public class LiquidityMarkerConsumer implements
        Layer1ApiFinishable,
        Layer1ApiAdminAdapter,
        Layer1ApiInstrumentAdapter,
        Layer1CustomPanelsGetter {

    private static final String LIQUIDITY_LOG_PATH = "F:/Databases/Logs/liquidity_consumer.log";
    private static final String ADDON_NAME = "Liquidity Marker Broadcasting Consumer";

    // Database managers (singleton pattern)
    private final RedisManager redisManager;
    private final TimescaleDBManager dbManager;

    // Batch processing for TimescaleDB
    private final BlockingQueue<LiquidityEvent> batchQueue;
    private final ScheduledExecutorService batchProcessor;

    // Session tracking
    private String currentSessionId;

    // UI components
    private JTextArea logArea;
    private JLabel statsLabel;

    // Event tracking
    private final List<Map<String, Object>> liquidityEvents = Collections.synchronizedList(new ArrayList<>());
    private final AtomicInteger liquidityCount = new AtomicInteger(0);
    private final AtomicInteger supportCount = new AtomicInteger(0);
    private final AtomicInteger resistanceCount = new AtomicInteger(0);
    private final Map<String, Integer> levelTypeCounts = new ConcurrentHashMap<>();

    // Instrument tracking
    private final Map<String, InstrumentInfo> instrumentsInfo = new ConcurrentHashMap<>();
    private final Map<String, Double> instrumentPips = new ConcurrentHashMap<>();

    // Date formatting
    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");

    // BrAPI components
    private final Layer1ApiProvider provider;
    private final BroadcasterConsumer broadcaster;
    private final AtomicBoolean isWorking = new AtomicBoolean(false);
    private final Connector connector;

    // Liquidity feed verification (similar to MboDataConsumer)
    private volatile boolean firstLiquidityReceived = false;
    private final ScheduledExecutorService verificationExecutor = Executors.newSingleThreadScheduledExecutor();

    public LiquidityMarkerConsumer(Layer1ApiProvider provider) {
        this.dateFormat.setTimeZone(TimeZone.getTimeZone("UTC"));
        ListenableHelper.addListeners(provider, this);
        this.provider = provider;

        log("INFO", "========================================");
        log("INFO", "Liquidity Marker Broadcasting Consumer: STARTING UP");
        log("INFO", "========================================");

        // Initialize database managers
        this.redisManager = RedisManager.getInstance();
        this.dbManager = TimescaleDBManager.getInstance();

        // Initialize batch processing (write every 5 seconds)
        this.batchQueue = new LinkedBlockingQueue<>(5000);
        this.batchProcessor = Executors.newSingleThreadScheduledExecutor();
        this.batchProcessor.scheduleAtFixedRate(this::processBatch, 5, 5, TimeUnit.SECONDS);

        // Initialize broadcaster
        this.broadcaster = BroadcastFactory.getBroadcasterConsumer(provider, ADDON_NAME, this.getClass());
        this.connector = new Connector(provider, this.broadcaster, Provider.LIQUIDITY_MARKERS);

        // Setup provider status listener
        this.broadcaster.setProviderStatusListener(new ProviderStatusListener() {
            @Override
            public void providerUpdateGenerator(String providerName, String providerId,
                    GeneratorInfo generator, boolean isOnline) {
                log("INFO", String.format("Provider update: %s, generator: %s, online: %s",
                        providerName,
                        generator != null ? generator.getGeneratorName() : "null",
                        isOnline));

                if (isWorking.get()) {
                    ExecutorsUtilities.getExecutor()
                            .submit(() -> provider.sendUserMessage(new Layer1ApiUserMessageReloadStrategyGui()));
                }
            }
        });

        log("INFO", "LiquidityMarkerConsumer: Broadcaster created (waiting for chain creation)");
        log("INFO", "Log file: " + LIQUIDITY_LOG_PATH);
        log("INFO", "Redis: Hot storage enabled");
        log("INFO", "TimescaleDB: Cold storage enabled (batch writes every 5 seconds)");
    }

    /**
     * Batch write queued liquidity events to TimescaleDB
     */
    private void processBatch() {
        try {
            List<LiquidityEvent> batch = new ArrayList<>();
            batchQueue.drainTo(batch, 500);

            if (!batch.isEmpty()) {
                dbManager.batchInsertLiquidityLevels(batch);
                log("INFO", String.format("[BATCH] Wrote %d liquidity events to TimescaleDB", batch.size()));
            }
        } catch (Exception e) {
            log("ERROR", "[BATCH] Error processing batch: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * Connect to Liquidity Markers provider
     */
    private void connectToProvider() {
        log("INFO", "Connecting to Liquidity Markers provider...");

        try {
            connector.connect();

            // Give connection time to establish
            ExecutorsUtilities.getExecutor().submit(() -> {
                try {
                    Thread.sleep(1000);

                    if (connector.isConnected()) {
                        log("INFO", "✓ Successfully connected to Liquidity Markers");

                        // Get available generators
                        List<String> generators = connector.getGeneratorsNames();
                        log("INFO", "Found " + generators.size() + " generator(s)");

                        // Subscribe to each generator
                        for (String generatorName : generators) {
                            log("INFO", "Subscribing to generator: " + generatorName);
                            subscribeToGenerator(generatorName);
                        }

                        // Start liquidity feed verification (30 seconds)
                        scheduleLiquidityFeedVerification();

                    } else {
                        log("WARN", "Connection not yet established, will retry in 2 seconds...");
                        Thread.sleep(2000);
                        connectToProvider();
                    }
                } catch (Exception e) {
                    log("ERROR", "Error during connection setup: " + e.getMessage());
                }
            });

        } catch (Exception e) {
            log("ERROR", "Failed to connect to provider: " + e.getMessage());
        }
    }

    /**
     * Schedule liquidity feed verification (similar to MBO verification)
     */
    private void scheduleLiquidityFeedVerification() {
        verificationExecutor.schedule(() -> {
            if (!firstLiquidityReceived) {
                log("WARN", "═══════════════════════════════════════════════════════════");
                log("WARN", "⚠ LIQUIDITY FEED CHECK: NO liquidity events received after 30 seconds!");
                log("WARN", "═══════════════════════════════════════════════════════════");
                log("WARN", "Possible reasons:");
                log("WARN", "  1. Liquidity Markers not enabled for this instrument");
                log("WARN", "  2. Market is quiet (no significant liquidity levels detected)");
                log("WARN", "  3. Insufficient market activity to form liquidity levels");
                log("WARN", "  4. Generator not properly subscribed");
                log("WARN", "═══════════════════════════════════════════════════════════");
            } else {
                log("INFO", "═══════════════════════════════════════════════════════════");
                log("INFO", "✓ LIQUIDITY FEED VERIFIED: Receiving liquidity events!");
                log("INFO", "═══════════════════════════════════════════════════════════");
                log("INFO", String.format("  - Total liquidity levels: %d", liquidityCount.get()));
                log("INFO", String.format("  - Support levels: %d", supportCount.get()));
                log("INFO", String.format("  - Resistance levels: %d", resistanceCount.get()));
                log("INFO", "═══════════════════════════════════════════════════════════");
            }
        }, 30, TimeUnit.SECONDS);
    }

    /**
     * Subscribe to a specific generator's live data
     */
    private void subscribeToGenerator(String generatorName) {
        try {
            if (!connector.isConnected()) {
                log("WARN", "Not connected, cannot subscribe to " + generatorName);
                return;
            }

            // Event listener
            LiveEventListener eventListener = event -> {
                if (event != null) {
                    processIncomingEvent(event);
                }
            };

            // Connection status listener
            LiveConnectionStatusListener connectionListener = isSubscribed -> {
                if (isSubscribed) {
                    log("INFO", "✓ Successfully subscribed to live data: " + generatorName);
                } else {
                    log("WARN", "✗ Unsubscribed from: " + generatorName);
                }
            };

            broadcaster.subscribeToLiveData(
                    Provider.LIQUIDITY_MARKERS.getFullName(),
                    generatorName,
                    eventListener,
                    connectionListener);

        } catch (Exception e) {
            log("ERROR", "Failed to subscribe to generator " + generatorName + ": " + e.getMessage());
        }
    }

    /**
     * Process incoming liquidity events from BrAPI
     * Note: Liquidity Markers sends custom event objects that we handle via
     * reflection
     */
    private void processIncomingEvent(Object event) {
        try {
            if (event == null) {
                log("WARN", "Received null event");
                return;
            }

            // Log event class for debugging (first event only)
            if (liquidityCount.get() == 0) {
                log("INFO", "First event class: " + event.getClass().getName());
                log("INFO", "Event package: " + event.getClass().getPackage().getName());
            }

            // Process the liquidity event using reflection
            // We don't have direct access to the event class, so we extract fields via
            // reflection
            processLiquidityEvent(event);

        } catch (Exception e) {
            log("ERROR", "Error processing incoming event: " + e.getMessage());
            StringWriter sw = new StringWriter();
            e.printStackTrace(new PrintWriter(sw));
            log("ERROR", sw.toString());
        }
    }

    @Override
    public void onUserMessage(Object data) {
        try {
            if (data == null)
                return;

            // Handle chain creation (addon initialization)
            if (data.getClass() == UserMessageLayersChainCreatedTargeted.class) {
                UserMessageLayersChainCreatedTargeted message = (UserMessageLayersChainCreatedTargeted) data;

                if (message.targetClass == this.getClass()) {
                    isWorking.set(true);
                    broadcaster.start();

                    log("INFO", "========================================");
                    log("INFO", "Broadcaster STARTED - Now listening for Liquidity events");
                    log("INFO", "========================================");

                    connectToProvider();

                    ExecutorsUtilities.getExecutor()
                            .submit(() -> provider.sendUserMessage(new Layer1ApiUserMessageReloadStrategyGui()));
                }
                return;
            }

            if (!isWorking.get())
                return;

            // Note: Liquidity events come through LiveEventListener, not onUserMessage

        } catch (Exception e) {
            log("ERROR", "Error in onUserMessage: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * Process liquidity event from Liquidity Markers indicator
     * Uses reflection since we don't have direct access to the event class
     */
    private void processLiquidityEvent(Object event) {
        try {
            // Mark that we received first liquidity event (for verification)
            if (!firstLiquidityReceived) {
                firstLiquidityReceived = true;
                log("INFO", "✓ First liquidity event received - feed is active!");
            }

            // Extract ALL available fields using reflection
            Map<String, Object> allFields = EventFieldExtractor.extractAllFields(event);
            String additionalDataJson = EventFieldExtractor.toJsonString(allFields);

            // Log all extracted fields on first event for debugging
            if (liquidityCount.get() == 0) {
                log("INFO", "===== ALL EXTRACTED LIQUIDITY FIELDS =====");
                log("INFO", additionalDataJson);
            }

            // Extract fields using reflection (since we don't have direct class access)
            long timestampNanos = extractLong(event, "time", "timestamp");
            double price = extractDouble(event, "price");
            double strengthScore = extractDouble(event, "strength", "score");
            long volumeAtLevel = extractLong(event, "volume");
            int touchesCount = extractInt(event, "touches", "count");
            String levelType = extractString(event, "levelType", "type");

            // Normalize level type
            if (levelType == null || levelType.isEmpty()) {
                // Try to infer from price relationship or other fields
                levelType = "UNKNOWN";
            } else {
                levelType = levelType.toUpperCase();
            }

            // CRITICAL: Convert price by multiplying by 0.25 (NQ tick to index point)
            // For other instruments, this multiplier may be different
            double convertedPrice = price * 0.25;

            // Get instrument name
            String instrument = instrumentsInfo.isEmpty() ? "" : instrumentsInfo.keySet().iterator().next();

            // Update counters
            liquidityCount.incrementAndGet();
            if (levelType.contains("SUPPORT")) {
                supportCount.incrementAndGet();
            } else if (levelType.contains("RESISTANCE")) {
                resistanceCount.incrementAndGet();
            }

            // Track level types
            levelTypeCounts.merge(levelType, 1, Integer::sum);

            // Log every 10th liquidity level
            if (liquidityCount.get() % 10 == 0) {
                log("INFO", String.format("Liquidity #%d: %s @ %.2f, Strength: %.2f, Volume: %d, Touches: %d",
                        liquidityCount.get(), levelType, convertedPrice, strengthScore, volumeAtLevel, touchesCount));
            }

            // Store to Redis (hot storage)
            Map<String, Object> liquidityData = new HashMap<>();
            liquidityData.put("timestamp", dateFormat.format(new Date(timestampNanos / 1_000_000))); // nanos to millis
            liquidityData.put("type", "liquidity");
            liquidityData.put("instrument", instrument);
            liquidityData.put("price", convertedPrice);
            liquidityData.put("levelType", levelType);
            liquidityData.put("strengthScore", strengthScore);
            liquidityData.put("volumeAtLevel", volumeAtLevel);
            liquidityData.put("touchesCount", touchesCount);
            liquidityData.put("allFields", additionalDataJson);

            String eventJson = EventFieldExtractor.toJsonString(liquidityData);
            redisManager.addLiquidityLevel(instrument, levelType, convertedPrice, strengthScore, eventJson);

            // Create LiquidityEvent for TimescaleDB batch processing
            LiquidityEvent dbEvent = new LiquidityEvent();
            dbEvent.timestamp = timestampNanos;
            dbEvent.symbol = instrument;
            dbEvent.sessionId = getCurrentSessionId(instrument);
            dbEvent.price = convertedPrice;
            dbEvent.levelType = levelType;
            dbEvent.strengthScore = strengthScore;
            dbEvent.volumeAtLevel = volumeAtLevel;
            dbEvent.touchesCount = touchesCount;
            dbEvent.createdAt = timestampNanos;
            dbEvent.lastUpdatedAt = timestampNanos;
            dbEvent.metadata = additionalDataJson;

            // Queue for batch processing
            if (!batchQueue.offer(dbEvent)) {
                log("WARN", "Batch queue full, liquidity event dropped");
            }

            // Update UI
            updateUI();

        } catch (Exception e) {
            log("ERROR", "Error processing liquidity event: " + e.getMessage());
            StringWriter sw = new StringWriter();
            e.printStackTrace(new PrintWriter(sw));
            log("ERROR", sw.toString());
        }
    }

    // Inner class for liquidity events
    public static class LiquidityEvent {
        public long timestamp;
        public String symbol;
        public String sessionId;
        public double price;
        public String levelType;
        public double strengthScore;
        public long volumeAtLevel;
        public int touchesCount;
        public long createdAt;
        public long lastUpdatedAt;
        public String metadata;
    }

    // Reflection helper methods for extracting fields from liquidity events
    private long extractLong(Object obj, String... fieldNames) {
        for (String fieldName : fieldNames) {
            try {
                // Try getter method first
                String methodName = "get" + fieldName.substring(0, 1).toUpperCase() + fieldName.substring(1);
                java.lang.reflect.Method method = obj.getClass().getMethod(methodName);
                Object result = method.invoke(obj);
                if (result instanceof Number) {
                    return ((Number) result).longValue();
                }
            } catch (Exception e) {
                // Try field access
                try {
                    java.lang.reflect.Field field = obj.getClass().getDeclaredField(fieldName);
                    field.setAccessible(true);
                    Object result = field.get(obj);
                    if (result instanceof Number) {
                        return ((Number) result).longValue();
                    }
                } catch (Exception ex) {
                    // Continue to next field name
                }
            }
        }
        return 0L;
    }

    private double extractDouble(Object obj, String... fieldNames) {
        for (String fieldName : fieldNames) {
            try {
                String methodName = "get" + fieldName.substring(0, 1).toUpperCase() + fieldName.substring(1);
                java.lang.reflect.Method method = obj.getClass().getMethod(methodName);
                Object result = method.invoke(obj);
                if (result instanceof Number) {
                    return ((Number) result).doubleValue();
                }
            } catch (Exception e) {
                try {
                    java.lang.reflect.Field field = obj.getClass().getDeclaredField(fieldName);
                    field.setAccessible(true);
                    Object result = field.get(obj);
                    if (result instanceof Number) {
                        return ((Number) result).doubleValue();
                    }
                } catch (Exception ex) {
                    // Continue
                }
            }
        }
        return 0.0;
    }

    private int extractInt(Object obj, String... fieldNames) {
        for (String fieldName : fieldNames) {
            try {
                String methodName = "get" + fieldName.substring(0, 1).toUpperCase() + fieldName.substring(1);
                java.lang.reflect.Method method = obj.getClass().getMethod(methodName);
                Object result = method.invoke(obj);
                if (result instanceof Number) {
                    return ((Number) result).intValue();
                }
            } catch (Exception e) {
                try {
                    java.lang.reflect.Field field = obj.getClass().getDeclaredField(fieldName);
                    field.setAccessible(true);
                    Object result = field.get(obj);
                    if (result instanceof Number) {
                        return ((Number) result).intValue();
                    }
                } catch (Exception ex) {
                    // Continue
                }
            }
        }
        return 0;
    }

    private String extractString(Object obj, String... fieldNames) {
        for (String fieldName : fieldNames) {
            try {
                String methodName = "get" + fieldName.substring(0, 1).toUpperCase() + fieldName.substring(1);
                java.lang.reflect.Method method = obj.getClass().getMethod(methodName);
                Object result = method.invoke(obj);
                if (result != null) {
                    return result.toString();
                }
            } catch (Exception e) {
                try {
                    java.lang.reflect.Field field = obj.getClass().getDeclaredField(fieldName);
                    field.setAccessible(true);
                    Object result = field.get(obj);
                    if (result != null) {
                        return result.toString();
                    }
                } catch (Exception ex) {
                    // Continue
                }
            }
        }
        return null;
    }

    /**
     * Get current session ID for instrument
     */
    private String getCurrentSessionId(String symbol) {
        if (currentSessionId == null) {
            currentSessionId = SessionManager.getInstance().generateSessionId(symbol);
        }
        return currentSessionId;
    }

    /**
     * Get current CBDR window
     */
    private String getCurrentCBDRWindow() {
        // TODO: Implement CBDR window detection based on time
        Calendar cal = Calendar.getInstance(TimeZone.getTimeZone("America/New_York"));
        int hour = cal.get(Calendar.HOUR_OF_DAY);

        if (hour >= 0 && hour < 8)
            return "ASIAN";
        if (hour >= 8 && hour < 9)
            return "LONDON_OPEN";
        if (hour >= 9 && hour < 16)
            return "NEW_YORK";
        if (hour >= 16 && hour < 20)
            return "LONDON_CLOSE";
        return "AFTER_HOURS";
    }

    /**
     * Check if current time is within CBDR window
     */
    private boolean isInCbdr(String cbdrWindow) {
        if (cbdrWindow == null)
            return false;
        return cbdrWindow.equals("LONDON_OPEN") || cbdrWindow.equals("NEW_YORK");
    }

    /**
     * Calculate sweep significance score (0.0 to 1.0)
     */
    private double calculateSweepSignificance(int levelsSwept, int totalVolume) {
        // Simple heuristic: combine levels and volume
        // Normalize to 0-1 range
        double levelScore = Math.min(levelsSwept / 10.0, 1.0); // 10 levels = max
        double volumeScore = Math.min(totalVolume / 1000.0, 1.0); // 1000 volume = max
        return (levelScore * 0.6) + (volumeScore * 0.4); // Weighted average
    }

    /**
     * Update UI with current statistics
     */
    private void updateUI() {
        if (statsLabel != null) {
            SwingUtilities.invokeLater(() -> {
                statsLabel.setText(String.format(
                        "<html><b>Liquidity:</b> %d | <b>Support:</b> %d | <b>Resistance:</b> %d | <b>Types:</b> %d</html>",
                        liquidityCount.get(),
                        supportCount.get(),
                        resistanceCount.get(),
                        levelTypeCounts.size()));
            });
        }
    }

    /**
     * Convert price from ticks to actual price
     */
    private double convertPrice(int priceTicks, String alias) {
        Double pips = instrumentPips.get(alias);
        if (pips == null)
            return priceTicks;
        return priceTicks * pips;
    }

    /**
     * Get field value from event using reflection
     */
    private Object getFieldValue(Object event, String fieldName) {
        try {
            // Try direct field access
            try {
                Field field = event.getClass().getDeclaredField(fieldName);
                field.setAccessible(true);
                return field.get(event);
            } catch (NoSuchFieldException e) {
                // Try getter method
                String getterName = "get" + fieldName.substring(0, 1).toUpperCase() + fieldName.substring(1);
                Method method = event.getClass().getMethod(getterName);
                return method.invoke(event);
            }
        } catch (Exception e) {
            // Field doesn't exist, return null
            return null;
        }
    }

    /**
     * Log event structure for debugging
     */
    private void logEventStructure(String eventType, Object event) {
        log("INFO", "===== " + eventType + " STRUCTURE =====");
        log("INFO", "Class: " + event.getClass().getName());

        // Log all fields
        Field[] fields = event.getClass().getDeclaredFields();
        for (Field field : fields) {
            try {
                field.setAccessible(true);
                Object value = field.get(event);
                log("INFO", String.format("  Field: %s = %s (%s)",
                        field.getName(),
                        value,
                        field.getType().getSimpleName()));
            } catch (Exception e) {
                log("ERROR", "  Field: " + field.getName() + " - ERROR: " + e.getMessage());
            }
        }

        // Log all methods
        Method[] methods = event.getClass().getDeclaredMethods();
        log("INFO", "Methods (" + methods.length + "):");
        for (Method method : methods) {
            if (method.getName().startsWith("get") && method.getParameterCount() == 0) {
                try {
                    Object value = method.invoke(event);
                    log("INFO", String.format("  Method: %s() = %s",
                            method.getName(),
                            value));
                } catch (Exception e) {
                    log("ERROR", "  Method: " + method.getName() + "() - ERROR: " + e.getMessage());
                }
            }
        }
        log("INFO", "===================================");
    }

    @Override
    public void onInstrumentAdded(String alias, InstrumentInfo instrumentInfo) {
        instrumentsInfo.put(alias, instrumentInfo);
        instrumentPips.put(alias, instrumentInfo.pips);

        log("INFO", String.format("Instrument added: %s (pips: %.5f)",
                alias, instrumentInfo.pips));

        // Generate session ID when instrument is added
        if (currentSessionId == null) {
            currentSessionId = SessionManager.getInstance().generateSessionId(alias);
            log("INFO", "Session ID: " + currentSessionId);
        }
    }

    @Override
    public void onInstrumentRemoved(String alias) {
        instrumentsInfo.remove(alias);
        instrumentPips.remove(alias);
        log("INFO", "Instrument removed: " + alias);
    }

    @Override
    public StrategyPanel[] getCustomGuiFor(String alias, String indicatorName) {
        if (!isWorking.get())
            return null;

        StrategyPanel panel = new StrategyPanel("Liquidity Consumer");
        panel.setLayout(new BorderLayout(5, 5));

        // Stats label at top
        statsLabel = new JLabel("Waiting for liquidity data...");
        statsLabel.setBorder(BorderFactory.createEmptyBorder(5, 5, 5, 5));
        panel.add(statsLabel, BorderLayout.NORTH);

        // Log area in center
        logArea = new JTextArea(15, 50);
        logArea.setEditable(false);
        logArea.setFont(new Font("Monospaced", Font.PLAIN, 11));
        JScrollPane scrollPane = new JScrollPane(logArea);
        panel.add(scrollPane, BorderLayout.CENTER);

        // Info panel at bottom
        JPanel infoPanel = new JPanel(new GridLayout(3, 1));
        infoPanel.add(new JLabel("Provider: Liquidity Markers"));
        infoPanel.add(new JLabel("Log: " + LIQUIDITY_LOG_PATH));
        infoPanel.add(new JLabel("Storage: Redis (hot) + TimescaleDB (cold)"));
        panel.add(infoPanel, BorderLayout.SOUTH);

        updateUI();

        return new StrategyPanel[] { panel };
    }

    @Override
    public void finish() {
        log("INFO", "========================================");
        log("INFO", "Liquidity Consumer: SHUTTING DOWN");
        log("INFO", "========================================");
        log("INFO", String.format("Final Statistics - Total: %d, Support: %d, Resistance: %d",
                liquidityCount.get(), supportCount.get(), resistanceCount.get()));

        // Report liquidity feed status
        if (firstLiquidityReceived) {
            log("INFO", "✓ Liquidity feed was ACTIVE during session");
        } else {
            log("WARN", "⚠ NO liquidity events received during session");
        }

        // Log level type breakdown
        if (!levelTypeCounts.isEmpty()) {
            log("INFO", "Liquidity level type breakdown:");
            levelTypeCounts.forEach((type, count) -> log("INFO", String.format("  %s: %d", type, count)));
        }

        isWorking.set(false);

        try {
            // Process remaining batched events
            processBatch();

            // Shutdown executors
            batchProcessor.shutdown();
            batchProcessor.awaitTermination(5, TimeUnit.SECONDS);

            verificationExecutor.shutdown();
            verificationExecutor.awaitTermination(2, TimeUnit.SECONDS);

            // Disconnect broadcaster
            if (connector != null) {
                connector.disconnect();
            }
            if (broadcaster != null) {
                broadcaster.finish();
            }

            log("INFO", "✓ Cleanup completed successfully");

        } catch (Exception e) {
            log("ERROR", "Error during cleanup: " + e.getMessage());
        }

        log("INFO", "========================================");
    }

    /**
     * Log message to file and console
     */
    private void log(String level, String message) {
        String timestamp = dateFormat.format(new Date());
        String logMessage = String.format("[%s] [%s] %s", timestamp, level, message);

        // Log to console
        System.out.println(logMessage);

        // Log to file
        try (FileWriter fw = new FileWriter(LIQUIDITY_LOG_PATH, true);
                PrintWriter pw = new PrintWriter(fw)) {
            pw.println(logMessage);
        } catch (IOException e) {
            System.err.println("Failed to write to log file: " + e.getMessage());
        }

        // Update UI log area
        if (logArea != null) {
            SwingUtilities.invokeLater(() -> {
                logArea.append(logMessage + "\n");
                logArea.setCaretPosition(logArea.getDocument().getLength());
            });
        }
    }

    /**
     * Utility class for executor management
     */
    private static class ExecutorsUtilities {
        private static final ExecutorService executor = Executors.newCachedThreadPool();

        public static ExecutorService getExecutor() {
            return executor;
        }
    }
}
