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
import com.bookmap.addons.broadcasting.implementations.base.CastUtilities;
import com.bookmap.addons.broadcasting.implementations.base.FailedToCastObject;
import velox.indicators.absorption.broadcasting.module.EventInterface;
import velox.indicators.absorption.broadcasting.module.implementations.TradeEvent;
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
 * Consumer for Bookmap Sweeps Indicator Broadcasting API
 * Captures sweep events (aggressive market orders that clear multiple price
 * levels)
 * and stores them in Redis (hot storage) + TimescaleDB (cold storage).
 * 
 * Sweeps indicate aggressive institutional activity and potential momentum
 * shifts.
 */
@Layer1Attachable
@Layer1StrategyName("Sweeps Broadcasting Consumer")
@Layer1ApiVersion(Layer1ApiVersionValue.VERSION2)
public class SweepsConsumer implements
        Layer1ApiFinishable,
        Layer1ApiAdminAdapter,
        Layer1ApiInstrumentAdapter,
        Layer1CustomPanelsGetter {

    private static final String SWEEPS_LOG_PATH = "F:/Databases/Logs/sweeps_consumer.log";
    private static final String ADDON_NAME = "Sweeps Broadcasting Consumer";

    // Database managers (singleton pattern)
    private final RedisManager redisManager;
    private final TimescaleDBManager dbManager;

    // Batch processing for TimescaleDB
    private final BlockingQueue<TimescaleDBManager.AbsorptionEvent> batchQueue;
    private final ScheduledExecutorService batchProcessor;

    // Session tracking
    private String currentSessionId;

    // UI components
    private JTextArea logArea;
    private JLabel statsLabel;

    // Event tracking
    private final List<Map<String, Object>> sweepEvents = Collections.synchronizedList(new ArrayList<>());
    private final AtomicInteger sweepCount = new AtomicInteger(0);
    private final AtomicInteger bidSweepCount = new AtomicInteger(0);
    private final AtomicInteger askSweepCount = new AtomicInteger(0);
    private final Map<String, Integer> sweepTypeCounts = new ConcurrentHashMap<>();

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

    // Sweep feed verification (similar to MboDataConsumer)
    private volatile boolean firstSweepReceived = false;
    private final ScheduledExecutorService verificationExecutor = Executors.newSingleThreadScheduledExecutor();

    public SweepsConsumer(Layer1ApiProvider provider) {
        this.dateFormat.setTimeZone(TimeZone.getTimeZone("UTC"));
        ListenableHelper.addListeners(provider, this);
        this.provider = provider;

        log("INFO", "========================================");
        log("INFO", "Sweeps Broadcasting Consumer: STARTING UP");
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
        this.connector = new Connector(provider, this.broadcaster, Provider.SWEEPS_INDICATOR);

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

        log("INFO", "SweepsConsumer: Broadcaster created (waiting for chain creation)");
        log("INFO", "Log file: " + SWEEPS_LOG_PATH);
        log("INFO", "Redis: Hot storage enabled");
        log("INFO", "TimescaleDB: Cold storage enabled (batch writes every 5 seconds)");
    }

    /**
     * Batch write queued events to TimescaleDB
     */
    private void processBatch() {
        try {
            List<TimescaleDBManager.AbsorptionEvent> batch = new ArrayList<>();
            batchQueue.drainTo(batch, 500);

            if (!batch.isEmpty()) {
                dbManager.batchInsertAbsorptionEvents(batch);
                log("INFO", String.format("[BATCH] Wrote %d sweep events to TimescaleDB", batch.size()));
            }
        } catch (Exception e) {
            log("ERROR", "[BATCH] Error processing batch: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * Connect to Sweeps Indicator provider
     */
    private void connectToProvider() {
        log("INFO", "Connecting to Sweeps Indicator provider...");

        try {
            connector.connect();

            // Give connection time to establish
            ExecutorsUtilities.getExecutor().submit(() -> {
                try {
                    Thread.sleep(1000);

                    if (connector.isConnected()) {
                        log("INFO", "✓ Successfully connected to Sweeps Indicator");

                        // Get available generators
                        List<String> generators = connector.getGeneratorsNames();
                        log("INFO", "Found " + generators.size() + " generator(s)");

                        // Subscribe to each generator
                        for (String generatorName : generators) {
                            log("INFO", "Subscribing to generator: " + generatorName);
                            subscribeToGenerator(generatorName);
                        }

                        // Start sweep feed verification (30 seconds)
                        scheduleSweepFeedVerification();

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
     * Schedule sweep feed verification (similar to MBO verification)
     */
    private void scheduleSweepFeedVerification() {
        verificationExecutor.schedule(() -> {
            if (!firstSweepReceived) {
                log("WARN", "═══════════════════════════════════════════════════════════");
                log("WARN", "⚠ SWEEP FEED CHECK: NO sweep events received after 30 seconds!");
                log("WARN", "═══════════════════════════════════════════════════════════");
                log("WARN", "Possible reasons:");
                log("WARN", "  1. Sweeps Indicator not enabled for this instrument");
                log("WARN", "  2. Market is quiet (no aggressive sweeps occurring)");
                log("WARN", "  3. Insufficient market activity to trigger sweeps");
                log("WARN", "  4. Generator not properly subscribed");
                log("WARN", "═══════════════════════════════════════════════════════════");
            } else {
                log("INFO", "═══════════════════════════════════════════════════════════");
                log("INFO", "✓ SWEEP FEED VERIFIED: Receiving sweep events!");
                log("INFO", "═══════════════════════════════════════════════════════════");
                log("INFO", String.format("  - Total sweeps: %d", sweepCount.get()));
                log("INFO", String.format("  - Bid sweeps: %d", bidSweepCount.get()));
                log("INFO", String.format("  - Ask sweeps: %d", askSweepCount.get()));
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
                    Provider.SWEEPS_INDICATOR.getFullName(),
                    generatorName,
                    eventListener,
                    connectionListener);

        } catch (Exception e) {
            log("ERROR", "Failed to subscribe to generator " + generatorName + ": " + e.getMessage());
        }
    }

    /**
     * Process incoming sweep events from BrAPI
     * Note: Sweeps Indicator sends TradeEvent objects (same as Absorption
     * Indicator)
     */
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
                    log("INFO", "Broadcaster STARTED - Now listening for Sweep events");
                    log("INFO", "========================================");

                    connectToProvider();

                    ExecutorsUtilities.getExecutor()
                            .submit(() -> provider.sendUserMessage(new Layer1ApiUserMessageReloadStrategyGui()));
                }
                return;
            }

            if (!isWorking.get())
                return;

            // Note: Sweep events come through LiveEventListener, not onUserMessage

        } catch (Exception e) {
            log("ERROR", "Error in onUserMessage: " + e.getMessage());
            e.printStackTrace();
        }
    }

    /**
     * Process sweep event from Sweeps Indicator (sent as TradeEvent)
     * Note: The Sweeps Indicator uses the same TradeEvent class as Absorption
     * Indicator
     */
    private void processTradeEvent(TradeEvent tradeEvent) {
        try {
            // Mark that we received first sweep (for verification)
            if (!firstSweepReceived) {
                firstSweepReceived = true;
                log("INFO", "✓ First sweep event received - feed is active!");
            }

            // Extract ALL available fields using reflection
            Map<String, Object> allFields = EventFieldExtractor.extractAllFields(tradeEvent);
            String additionalDataJson = EventFieldExtractor.toJsonString(allFields);

            // Log all extracted fields on first event for debugging
            if (sweepCount.get() == 0) {
                log("INFO", "===== ALL EXTRACTED SWEEP FIELDS =====");
                log("INFO", additionalDataJson);
            }

            // Direct field access from TradeEvent - NO REFLECTION
            long timestampNanos = tradeEvent.getTime();
            double price = tradeEvent.getPrice();
            int size = tradeEvent.getValue(); // getValue() returns size
            boolean isBid = tradeEvent.isBid();
            int maxChainSize = tradeEvent.getMaxChainSize();

            // CRITICAL: Convert price by multiplying by 0.25 (NQ tick to index point)
            // For other instruments, this multiplier may be different
            double convertedPrice = price * 0.25;

            // Determine side (use BUY/SELL for database, BID/ASK for display)
            String sideDisplay = isBid ? "BID" : "ASK";
            String sideDb = isBid ? "BUY" : "SELL"; // Database constraint expects BUY/SELL

            // Get instrument name
            String instrument = instrumentsInfo.isEmpty() ? "" : instrumentsInfo.keySet().iterator().next();

            // Estimate levels swept based on maxChainSize (indicator of aggressive sweep)
            int levelsSwept = maxChainSize > 0 ? maxChainSize : 1;

            // Classify sweep type
            String sweepType = maxChainSize > 5 ? "AGGRESSIVE" : "STANDARD";

            // Calculate significance score
            double significance = calculateSweepSignificance(levelsSwept, size);

            // Update counters
            sweepCount.incrementAndGet();
            if (isBid) {
                bidSweepCount.incrementAndGet();
            } else {
                askSweepCount.incrementAndGet();
            }

            // Track sweep types
            sweepTypeCounts.merge(sweepType, 1, Integer::sum);

            // Log every 10th sweep
            if (sweepCount.get() % 10 == 0) {
                log("INFO", String.format("Sweep #%d: %s @ %.2f, Size: %d, ChainSize: %d, Significance: %.2f",
                        sweepCount.get(), sideDisplay, convertedPrice, size, maxChainSize, significance));
            }

            // Store to Redis (hot storage)
            Map<String, Object> sweepData = new HashMap<>();
            sweepData.put("timestamp", dateFormat.format(new Date(timestampNanos / 1_000_000))); // nanos to millis
            sweepData.put("type", "sweep");
            sweepData.put("instrument", instrument);
            sweepData.put("price", convertedPrice);
            sweepData.put("side", sideDisplay); // Use BID/ASK for display
            sweepData.put("size", size);
            sweepData.put("maxChainSize", maxChainSize);
            sweepData.put("levelsSwept", levelsSwept);
            sweepData.put("sweepType", sweepType);
            sweepData.put("significance", significance);
            sweepData.put("allFields", additionalDataJson);

            String eventJson = EventFieldExtractor.toJsonString(sweepData);
            redisManager.addSweepEvent(instrument, sideDisplay, convertedPrice, size, eventJson);

            // Queue for TimescaleDB (cold storage)
            TimescaleDBManager.AbsorptionEvent dbEvent = new TimescaleDBManager.AbsorptionEvent();
            dbEvent.symbol = instrument;
            dbEvent.timestamp = timestampNanos;
            dbEvent.eventType = "SWEEP";
            dbEvent.side = sideDb; // Use BUY/SELL for database constraint
            dbEvent.price = convertedPrice;
            dbEvent.absorbedVolume = 0; // N/A for sweeps
            dbEvent.aggressorVolume = size;
            dbEvent.liquidityRemoved = size;
            dbEvent.absorptionRatio = 0.0; // N/A for sweeps
            dbEvent.imbalanceRatio = 0.0; // N/A for sweeps
            dbEvent.sessionId = getCurrentSessionId(instrument);
            dbEvent.cbdrWindow = getCurrentCBDRWindow();
            dbEvent.isInCbdr = isInCbdr(dbEvent.cbdrWindow);
            dbEvent.significance = significance;
            dbEvent.metadata = String.format("{\"levelsSwept\":%d,\"sweepType\":\"%s\",\"maxChainSize\":%d}",
                    levelsSwept, sweepType, maxChainSize);
            dbEvent.additionalData = additionalDataJson;

            if (!batchQueue.offer(dbEvent)) {
                log("WARN", "Batch queue full, sweep event dropped");
            }

            // Update UI
            updateUI();

        } catch (Exception e) {
            log("ERROR", "Error processing sweep event: " + e.getMessage());
            StringWriter sw = new StringWriter();
            e.printStackTrace(new PrintWriter(sw));
            log("ERROR", sw.toString());
        }
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
                        "<html><b>Sweeps:</b> %d | <b>Bid:</b> %d | <b>Ask:</b> %d | <b>Types:</b> %d</html>",
                        sweepCount.get(),
                        bidSweepCount.get(),
                        askSweepCount.get(),
                        sweepTypeCounts.size()));
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

        StrategyPanel panel = new StrategyPanel("Sweeps Consumer");
        panel.setLayout(new BorderLayout(5, 5));

        // Stats label at top
        statsLabel = new JLabel("Waiting for sweep data...");
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
        infoPanel.add(new JLabel("Provider: Sweeps Indicator"));
        infoPanel.add(new JLabel("Log: " + SWEEPS_LOG_PATH));
        infoPanel.add(new JLabel("Storage: Redis (hot) + TimescaleDB (cold)"));
        panel.add(infoPanel, BorderLayout.SOUTH);

        updateUI();

        return new StrategyPanel[] { panel };
    }

    @Override
    public void finish() {
        log("INFO", "========================================");
        log("INFO", "Sweeps Consumer: SHUTTING DOWN");
        log("INFO", "========================================");
        log("INFO", String.format("Final Statistics - Total: %d, Bid: %d, Ask: %d",
                sweepCount.get(), bidSweepCount.get(), askSweepCount.get()));

        // Report sweep feed status
        if (firstSweepReceived) {
            log("INFO", "✓ Sweep feed was ACTIVE during session");
        } else {
            log("WARN", "⚠ NO sweep events received during session");
        }

        // Log sweep type breakdown
        if (!sweepTypeCounts.isEmpty()) {
            log("INFO", "Sweep type breakdown:");
            sweepTypeCounts.forEach((type, count) -> log("INFO", String.format("  %s: %d", type, count)));
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
        try (FileWriter fw = new FileWriter(SWEEPS_LOG_PATH, true);
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
