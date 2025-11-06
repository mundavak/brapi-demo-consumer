package com.bookmap.demo.consumer;

import com.bookmap.addons.broadcasting.api.view.BroadcasterConsumer;
import com.bookmap.addons.broadcasting.api.view.GeneratorInfo;
import com.bookmap.addons.broadcasting.api.view.listeners.LiveConnectionStatusListener;
import com.bookmap.addons.broadcasting.api.view.listeners.LiveEventListener;
import com.bookmap.addons.broadcasting.api.view.listeners.ProviderStatusListener;
import com.bookmap.addons.broadcasting.implementations.view.BroadcastFactory;
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
import velox.api.layer1.common.Log;
import velox.api.layer1.data.InstrumentInfo;
import velox.api.layer1.messages.Layer1ApiUserMessageReloadStrategyGui;
import velox.api.layer1.messages.UserMessageLayersChainCreatedTargeted;
import velox.gui.StrategyPanel;

// Import Stops & Icebergs event classes
import velox.indicators.sionchart.broadcasting.implementations.StopEvent;
import velox.indicators.sionchart.broadcasting.implementations.IcebergEvent;

import javax.swing.*;
import java.awt.*;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Statement;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Consumer for Stops & Icebergs On-Chart broadcasting events
 * Receives and logs StopEvent and IcebergEvent broadcasts
 */
@Layer1Attachable
@Layer1StrategyName("SI Broadcasting Consumer")
@Layer1ApiVersion(Layer1ApiVersionValue.VERSION2)
public class StopsIcebergsConsumer implements
        Layer1ApiFinishable,
        Layer1ApiAdminAdapter,
        Layer1ApiInstrumentAdapter,
        Layer1CustomPanelsGetter {

    // File paths for logging and export
    private static final String SI_LOG_PATH = "F:/TradingAgent/si_events.log";
    private static final String SI_JSON_PATH = "F:/TradingAgent/si_data.json";
    private static final String SI_DB_PATH = "F:/TradingAgent/si_events_db.csv";
    private static final String SQLITE_DB_PATH = "F:/TradingAgent/enhanced_market_monitor_mbo.db";

    // Trading windows in EST (Bookmap times are in UTC-4)
    private static final int[][] TRADING_WINDOWS_EST = {
        {16, 0, 20, 0},  // CBDR PM/Asian: 16:00-20:00 EST
        {2, 0, 5, 0},    // CBDR London: 02:00-05:00 EST
        {7, 30, 9, 30}   // Pre-NY: 07:30-09:30 EST
    };

    // UI components
    private JTextArea logArea;
    private JLabel statsLabel;

    // Data storage
    private final List<Map<String, Object>> stopEvents = new ArrayList<>();
    private final List<Map<String, Object>> icebergEvents = new ArrayList<>();
    private final AtomicInteger stopCount = new AtomicInteger(0);
    private final AtomicInteger icebergCount = new AtomicInteger(0);
    private final Map<String, Integer> icebergTypeCounts = new HashMap<>();

    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
    private final Map<String, InstrumentInfo> instrumentsInfo = new ConcurrentHashMap<>();
    private final Map<String, Double> instrumentPips = new ConcurrentHashMap<>();

    private final Layer1ApiProvider provider;
    private final BroadcasterConsumer broadcaster;
    private Connection dbConnection;
    private final AtomicBoolean isWorking = new AtomicBoolean(false);
    private final Connector connector;

    public StopsIcebergsConsumer(Layer1ApiProvider provider) {
        dateFormat.setTimeZone(TimeZone.getTimeZone("UTC"));
        ListenableHelper.addListeners(provider, this);
        this.provider = provider;

        Log.info("========================================");
        Log.info("SI Broadcasting Consumer: STARTING UP");
        Log.info("========================================");

        // Initialize SQLite database
        initializeDatabase();

        this.broadcaster = BroadcastFactory.getBroadcasterConsumer(provider, "SI Broadcasting Consumer", this.getClass());

        // Create connector for Stops & Icebergs On-Chart provider
        this.connector = new Connector(provider, broadcaster, com.bookmap.demo.consumer.providers.Provider.SIT_INDICATOR);

        // Set up provider status listener to receive updates when providers come online
        broadcaster.setProviderStatusListener(new ProviderStatusListener() {
            @Override
            public void providerUpdateGenerator(String providerName, String providerId, GeneratorInfo generator, boolean isOnline) {
                log("INFO", String.format("Provider update: %s, generator: %s, online: %s",
                    providerName, generator != null ? generator.getGeneratorName() : "null", isOnline));

                // Reload GUI when provider status changes
                if (isWorking.get()) {
                    ExecutorsUtilities.getExecutor().submit(() -> {
                        StopsIcebergsConsumer.this.provider.sendUserMessage(new Layer1ApiUserMessageReloadStrategyGui());
                    });
                }
            }
        });

        Log.info("StopsIcebergsConsumer: Broadcaster created (waiting for chain creation)");
        Log.info("Log file: " + SI_LOG_PATH);
        Log.info("JSON file: " + SI_JSON_PATH);
        Log.info("DB file: " + SI_DB_PATH);
        Log.info("SQLite DB: " + SQLITE_DB_PATH);
    }

    /**
     * Check if timestamp falls within any trading window (EST)
     * Bookmap times are in UTC-4, so we convert to EST
     */
    private boolean isWithinTradingWindow(long timestampNanos) {
        long timestampMillis = timestampNanos / 1_000_000;
        Calendar cal = Calendar.getInstance(TimeZone.getTimeZone("America/New_York"));
        cal.setTimeInMillis(timestampMillis);

        int hour = cal.get(Calendar.HOUR_OF_DAY);
        int minute = cal.get(Calendar.MINUTE);
        int currentMinutes = hour * 60 + minute;

        for (int[] window : TRADING_WINDOWS_EST) {
            int startMinutes = window[0] * 60 + window[1];
            int endMinutes = window[2] * 60 + window[3];

            if (currentMinutes >= startMinutes && currentMinutes <= endMinutes) {
                return true;
            }
        }

        return false;
    }

    /**
     * Initialize SQLite database connection and create Events table if it doesn't exist
     */
    private void initializeDatabase() {
        try {
            // Load SQLite JDBC driver
            Class.forName("org.sqlite.JDBC");

            // Establish connection to the database
            String url = "jdbc:sqlite:" + SQLITE_DB_PATH;
            dbConnection = DriverManager.getConnection(url);

            // Create Events table if it doesn't exist
            String createTableSQL = """
                CREATE TABLE IF NOT EXISTS Events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    order_id TEXT,
                    price REAL,
                    size REAL,
                    side TEXT,
                    total_size REAL,
                    is_bid INTEGER,
                    instrument TEXT,
                    sub_type TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """;

            try (Statement stmt = dbConnection.createStatement()) {
                stmt.execute(createTableSQL);
                log("INFO", "SQLite database initialized successfully at: " + SQLITE_DB_PATH);
                log("INFO", "Events table created or already exists");
            }

            // Create index on timestamp for better query performance
            String createIndexSQL = "CREATE INDEX IF NOT EXISTS idx_events_timestamp ON Events(timestamp)";
            try (Statement stmt = dbConnection.createStatement()) {
                stmt.execute(createIndexSQL);
            }

        } catch (ClassNotFoundException e) {
            log("ERROR", "SQLite JDBC driver not found: " + e.getMessage());
        } catch (SQLException e) {
            log("ERROR", "Failed to initialize database: " + e.getMessage());
        }
    }

    /**
     * Connect to the Stops & Icebergs On-Chart provider and subscribe to its events
     */
    private void connectToProvider() {
        log("INFO", "Connecting to Stops & Icebergs On-Chart provider...");

        try {
            // Connect using the Connector
            connector.connect();

            // Wait a moment for connection to establish, then subscribe
            ExecutorsUtilities.getExecutor().submit(() -> {
                try {
                    Thread.sleep(1000);

                    if (connector.isConnected()) {
                        log("INFO", "✓ Successfully connected to Stops & Icebergs On-Chart");

                        // Get all available generators
                        List<String> generators = connector.getGeneratorsNames();
                        log("INFO", "Found " + generators.size() + " generator(s)");

                        // Subscribe to live events from each generator
                        for (String generatorName : generators) {
                            log("INFO", "Subscribing to generator: " + generatorName);
                            subscribeToGenerator(generatorName);
                        }
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
     * Subscribe to a specific generator to receive its live events
     */
    private void subscribeToGenerator(String generatorName) {
        try {
            if (!connector.isConnected()) {
                log("WARN", "Not connected, cannot subscribe to " + generatorName);
                return;
            }

            // Create a custom LiveEventListener that will receive events
            LiveEventListener eventListener = event -> {
                if (event != null) {
                    // Process Stop and Iceberg events
                    processIncomingEvent(event);
                }
            };

            // Create a LiveConnectionStatusListener to monitor subscription status
            LiveConnectionStatusListener connectionListener = isSubscribed -> {
                if (isSubscribed) {
                    log("INFO", "✓ Successfully subscribed to live data: " + generatorName);
                } else {
                    log("WARN", "✗ Unsubscribed from: " + generatorName);
                }
            };

            // Subscribe to live data using the broadcaster
            broadcaster.subscribeToLiveData(
                com.bookmap.demo.consumer.providers.Provider.SIT_INDICATOR.getFullName(),
                generatorName,
                eventListener,
                connectionListener
            );

        } catch (Exception e) {
            log("ERROR", "Failed to subscribe to generator " + generatorName + ": " + e.getMessage());
        }
    }

    /**
     * Process incoming events from the broadcaster
     */
    private void processIncomingEvent(Object event) {
        try {
            String className = event.getClass().getName();

            // Log ALL incoming events for debugging
            if (icebergCount.get() == 0 && stopCount.get() % 100 == 0) {
                log("INFO", "Still receiving events - Class: " + className);
            }

            // Direct type checking for Stop and Iceberg events
            if (event instanceof StopEvent) {
                log("DEBUG", "Received StopEvent (direct type)");
                onStopEvent(event);
                return;
            }

            if (event instanceof IcebergEvent) {
                log("INFO", "✓✓✓ Received IcebergEvent (direct type) ✓✓✓");
                onIcebergEvent(event);
                return;
            }

            // Fallback: Check by class name pattern
            if (className.toLowerCase().contains("stop") && className.toLowerCase().contains("event")) {
                log("DEBUG", "Received StopEvent (by name): " + className);
                onStopEvent(event);
            } else if (className.toLowerCase().contains("iceberg") && className.toLowerCase().contains("event")) {
                log("INFO", "✓✓✓ Received IcebergEvent (by name): " + className + " ✓✓✓");
                onIcebergEvent(event);
            } else {
                // Log unknown events occasionally to see if we're missing something
                if (stopCount.get() % 50 == 0) {
                    log("WARN", "Received unknown event type: " + className);
                }
            }
        } catch (Exception e) {
            log("ERROR", "Error processing incoming event: " + e.getMessage());
        }
    }

    @Override
    public void onUserMessage(Object data) {
        try {
            if (data == null) {
                return;
            }

            // Check if this is the chain creation message - start broadcaster when ready
            if (data.getClass() == UserMessageLayersChainCreatedTargeted.class) {
                UserMessageLayersChainCreatedTargeted message = (UserMessageLayersChainCreatedTargeted) data;
                if (message.targetClass == getClass()) {
                    isWorking.set(true);
                    broadcaster.start();
                    log("INFO", "========================================");
                    log("INFO", "Broadcaster STARTED - Now listening for Stop/Iceberg events");
                    log("INFO", "========================================");

                    // Connect to Stops & Icebergs On-Chart provider
                    connectToProvider();

                    // Reload GUI
                    ExecutorsUtilities.getExecutor().submit(() -> {
                        provider.sendUserMessage(new Layer1ApiUserMessageReloadStrategyGui());
                    });
                }
                return;
            }

            // Only process events if broadcaster is working
            if (!isWorking.get()) {
                return;
            }

            String className = data.getClass().getName();

            // Log ALL messages for debugging (can be filtered later)
            Log.info("SI Consumer received message: " + className);

            // Direct type checking for Stop and Iceberg events
            if (data instanceof StopEvent) {
                log("FOUND", "Detected StopEvent (direct type): " + className);
                onStopEvent(data);
                return;
            }

            if (data instanceof IcebergEvent) {
                log("FOUND", "Detected IcebergEvent (direct type): " + className);
                onIcebergEvent(data);
                return;
            }

            // Fallback: Check by class name pattern (in case of different classloaders)
            boolean isStopEvent = className.toLowerCase().contains("stop") &&
                                 className.toLowerCase().contains("event");
            boolean isIcebergEvent = className.toLowerCase().contains("iceberg") &&
                                    className.toLowerCase().contains("event");

            if (isStopEvent) {
                log("FOUND", "Detected StopEvent (by name): " + className);
                onStopEvent(data);
            } else if (isIcebergEvent) {
                log("FOUND", "Detected IcebergEvent (by name): " + className);
                onIcebergEvent(data);
            }

        } catch (Exception e) {
            StringWriter sw = new StringWriter();
            e.printStackTrace(new PrintWriter(sw));
            log("ERROR", "Error in onUserMessage: " + e.getMessage());
        }
    }

    public void onStopEvent(Object event) {
        try {
            log("INFO", "[StopsIcebergsConsumer] StopEvent received - checking trading window...");
            
            // Check if event is within trading window first
            if (event != null) {
                Object timeObj = getFieldValue(event, "time");
                if (timeObj instanceof Long) {
                    long eventTime = (Long) timeObj;
                    boolean inWindow = isWithinTradingWindow(eventTime);
                    log("INFO", String.format("[StopsIcebergsConsumer] Event time: %d, InWindow: %s", eventTime, inWindow));
                    
                    if (!inWindow) {
                        log("INFO", "[StopsIcebergsConsumer] StopEvent FILTERED - outside trading window");
                        return;
                    }
                    log("INFO", "[StopsIcebergsConsumer] StopEvent PASSED filter - processing...");
                }
            }

            Map<String, Object> stopData = new HashMap<>();
            stopData.put("timestamp", dateFormat.format(new Date()));
            stopData.put("type", "stop");

            if (event != null) {
                try {
                    // First time: Log all available fields and methods for debugging
                    if (stopCount.get() == 0) {
                        logEventStructure("StopEvent", event);
                    }

                    // Get the instrument alias for price conversion
                    String instrument = instrumentsInfo.isEmpty() ? "" : instrumentsInfo.keySet().iterator().next();

                    // Use correct field names from decompiled class
                    stopData.put("orderID", getFieldValue(event, "orderId"));

                    // Convert integer tick price to actual decimal price (same as Python: price = tick * pips)
                    Object priceObj = getFieldValue(event, "price");
                    if (priceObj instanceof Integer) {
                        int tickPrice = (Integer) priceObj;
                        double actualPrice = convertPrice(tickPrice, instrument);
                        stopData.put("price", actualPrice);
                    } else {
                        stopData.put("price", priceObj);
                    }

                    stopData.put("size", getFieldValue(event, "size"));
                    stopData.put("time", getFieldValue(event, "time"));
                    stopData.put("totalSize", getFieldValue(event, "totalSize"));

                    Boolean isBid = (Boolean) getFieldValue(event, "isBid");
                    stopData.put("isBid", isBid);
                    stopData.put("side", (isBid != null && isBid) ? "BUY" : "SELL");

                    // Get EventType enum and convert to string
                    Object typeObj = getFieldValue(event, "type");
                    if (typeObj != null) {
                        stopData.put("eventType", typeObj.toString());
                    }
                } catch (Exception e) {
                    log("ERROR", "Failed to extract StopEvent fields: " + e.getMessage());
                }
            }

            stopEvents.add(stopData);
            int count = stopCount.incrementAndGet();

            String logMsg = String.format("[STOP #%d] %s %s @ %s, size=%s, totalSize=%s",
                count,
                stopData.getOrDefault("side", "N/A"),
                stopData.getOrDefault("orderID", "N/A"),
                formatNumber(stopData.get("price")),
                formatNumber(stopData.get("size")),
                formatNumber(stopData.get("totalSize"))
            );

            log("STOP", logMsg);
            updateUI();
            exportEventToDb(stopData);

            if (count % 10 == 0) {
                saveToJson();
            }

        } catch (Exception e) {
            log("ERROR", "Error processing StopEvent: " + e.getMessage());
        }
    }

    public void onIcebergEvent(Object event) {
        try {
            // Check if event is within trading window first
            if (event != null) {
                Object timeObj = getFieldValue(event, "time");
                if (timeObj instanceof Long) {
                    long eventTime = (Long) timeObj;
                    if (!isWithinTradingWindow(eventTime)) {
                        log("DEBUG", "IcebergEvent outside trading window, skipping");
                        return;
                    }
                }
            }

            Map<String, Object> icebergData = new HashMap<>();
            icebergData.put("timestamp", dateFormat.format(new Date()));
            icebergData.put("type", "iceberg");

            if (event != null) {
                try {
                    // First time: Log all available fields and methods for debugging
                    if (icebergCount.get() == 0) {
                        logEventStructure("IcebergEvent", event);
                    }

                    // Get the instrument alias for price conversion
                    String instrument = instrumentsInfo.isEmpty() ? "" : instrumentsInfo.keySet().iterator().next();

                    // Get EventType enum and convert to string
                    Object typeObj = getFieldValue(event, "type");
                    String eventType = (typeObj != null) ? typeObj.toString() : "unknown";
                    icebergData.put("eventType", eventType);
                    icebergTypeCounts.merge(eventType, 1, Integer::sum);

                    // Use correct field names from decompiled class
                    icebergData.put("orderID", getFieldValue(event, "orderId"));

                    // Convert integer tick price to actual decimal price (same as Python: price = tick * pips)
                    Object priceObj = getFieldValue(event, "price");
                    if (priceObj instanceof Integer) {
                        int tickPrice = (Integer) priceObj;
                        double actualPrice = convertPrice(tickPrice, instrument);
                        icebergData.put("price", actualPrice);
                    } else {
                        icebergData.put("price", priceObj);
                    }

                    icebergData.put("size", getFieldValue(event, "size"));
                    icebergData.put("time", getFieldValue(event, "time"));
                    icebergData.put("totalSize", getFieldValue(event, "totalSize"));

                    Boolean isBid = (Boolean) getFieldValue(event, "isBid");
                    icebergData.put("isBid", isBid);
                    icebergData.put("side", (isBid != null && isBid) ? "BUY" : "SELL");

                    String typeMsg = getEventTypeMessage(eventType);
                    icebergData.put("typeMessage", typeMsg);

                } catch (Exception e) {
                    log("ERROR", "Failed to extract IcebergEvent fields: " + e.getMessage());
                }
            }

            icebergEvents.add(icebergData);
            int count = icebergCount.incrementAndGet();

            String logMsg = String.format("[ICEBERG #%d] %s %s @ %s %s",
                count,
                icebergData.getOrDefault("typeMessage", ""),
                icebergData.getOrDefault("orderID", "N/A"),
                formatNumber(icebergData.get("price")),
                icebergData.getOrDefault("side", "N/A")
            );

            log("ICEBERG", logMsg);
            updateUI();
            exportEventToDb(icebergData);

            if ((stopCount.get() + icebergCount.get()) % 10 == 0) {
                saveToJson();
            }

        } catch (Exception e) {
            log("ERROR", "Error processing IcebergEvent: " + e.getMessage());
        }
    }

    private String getEventTypeMessage(String eventType) {
        if (eventType == null) return "[UNKNOWN]";
        return switch (eventType.toLowerCase()) {
            case "detection" -> "[DETECTION] New iceberg detected";
            case "trade" -> "[TRADE] Iceberg trade executed";
            case "movement" -> "[MOVEMENT] Iceberg moved to new level";
            case "execution" -> "[EXECUTION] Iceberg fully executed";
            case "cancellation" -> "[CANCELLATION] Iceberg cancelled";
            default -> "[" + eventType.toUpperCase() + "]";
        };
    }

    private Object getFieldValue(Object obj, String fieldName) {
        if (obj == null) return null;
        try {
            java.lang.reflect.Field field = obj.getClass().getDeclaredField(fieldName);
            field.setAccessible(true);
            return field.get(obj);
        } catch (Exception e) {
            try {
                String getter = "get" + Character.toUpperCase(fieldName.charAt(0)) + fieldName.substring(1);
                java.lang.reflect.Method m = obj.getClass().getMethod(getter);
                return m.invoke(obj);
            } catch (Exception e2) {
                try {
                    String getter = "is" + Character.toUpperCase(fieldName.charAt(0)) + fieldName.substring(1);
                    java.lang.reflect.Method m = obj.getClass().getMethod(getter);
                    return m.invoke(obj);
                } catch (Exception e3) {
                    return null;
                }
            }
        }
    }

    /**
     * Convert integer tick price to actual decimal price
     * Same logic as Python: actual_price = tick_price * pips
     */
    private double convertPrice(int tickPrice, String alias) {
        // Get the pip size for this instrument
        Double pips = instrumentPips.get(alias);

        if (pips == null) {
            // Fallback: try to get from first available instrument
            if (!instrumentPips.isEmpty()) {
                pips = instrumentPips.values().iterator().next();
                log("WARN", "No pip size found for " + alias + ", using fallback: " + pips);
            } else {
                // Last resort: assume 0.25 for NQ
                pips = 0.25;
                log("WARN", "No pip size available, using default: " + pips);
            }
        }

        // Convert: actual_price = tick_price * pips
        return tickPrice * pips;
    }

    /**
     * Log the complete structure of an event object to discover available fields and methods
     */
    private void logEventStructure(String eventName, Object event) {
        log("INSPECT", "========================================");
        log("INSPECT", "Inspecting " + eventName + " structure:");
        log("INSPECT", "Class: " + event.getClass().getName());

        // Log all declared fields
        log("INSPECT", "--- Fields ---");
        java.lang.reflect.Field[] fields = event.getClass().getDeclaredFields();
        for (java.lang.reflect.Field field : fields) {
            field.setAccessible(true);
            try {
                Object value = field.get(event);
                log("INSPECT", String.format("  %s (%s) = %s",
                    field.getName(),
                    field.getType().getSimpleName(),
                    value));
            } catch (Exception e) {
                log("INSPECT", String.format("  %s (%s) = <error accessing>",
                    field.getName(),
                    field.getType().getSimpleName()));
            }
        }

        // Log all public methods (getters)
        log("INSPECT", "--- Public Methods ---");
        java.lang.reflect.Method[] methods = event.getClass().getMethods();
        for (java.lang.reflect.Method method : methods) {
            String methodName = method.getName();
            // Only show getters and relevant methods
            if ((methodName.startsWith("get") || methodName.startsWith("is")) &&
                method.getParameterCount() == 0 &&
                !methodName.equals("getClass")) {
                try {
                    Object value = method.invoke(event);
                    log("INSPECT", String.format("  %s() returns %s = %s",
                        methodName,
                        method.getReturnType().getSimpleName(),
                        value));
                } catch (Exception e) {
                    log("INSPECT", String.format("  %s() returns %s = <error invoking>",
                        methodName,
                        method.getReturnType().getSimpleName()));
                }
            }
        }
        log("INSPECT", "========================================");
    }

    private void log(String level, String message) {
        String logLine = String.format("[%s] [%s] %s", dateFormat.format(new Date()), level, message);
        Log.info(logLine);

        try (FileWriter writer = new FileWriter(SI_LOG_PATH, true)) {
            writer.write(logLine + "\n");
        } catch (IOException e) {
            Log.error("Failed to write to log file", e);
        }

        if (logArea != null) {
            SwingUtilities.invokeLater(() -> {
                logArea.append(logLine + "\n");
                logArea.setCaretPosition(logArea.getDocument().getLength());
            });
        }
    }

    private void updateUI() {
        if (statsLabel != null) {
            SwingUtilities.invokeLater(() -> {
                StringBuilder stats = new StringBuilder("<html>");
                stats.append("<b>STATISTICS</b><br>");
                stats.append("Total Stops: ").append(stopCount.get()).append("<br>");
                stats.append("Total Icebergs: ").append(icebergCount.get()).append("<br>");
                if (!icebergTypeCounts.isEmpty()) {
                    stats.append("<br><b>Iceberg Types:</b><br>");
                    icebergTypeCounts.forEach((type, count) ->
                        stats.append("  ").append(type).append(": ").append(count).append("<br>")
                    );
                }
                stats.append("</html>");
                statsLabel.setText(stats.toString());
            });
        }
    }

    private void saveToJson() {
        try (FileWriter writer = new FileWriter(SI_JSON_PATH)) {
            StringBuilder json = new StringBuilder();
            json.append("{\n");
            json.append("  \"timestamp\": \"").append(dateFormat.format(new Date())).append("\",\n");
            json.append("  \"statistics\": {\n");
            json.append("    \"totalStops\": ").append(stopCount.get()).append(",\n");
            json.append("    \"totalIcebergs\": ").append(icebergCount.get()).append(",\n");
            json.append("    \"icebergTypes\": {\n");

            int idx = 0;
            for (Map.Entry<String, Integer> e : icebergTypeCounts.entrySet()) {
                json.append("      \"").append(e.getKey()).append("\": ").append(e.getValue());
                if (++idx < icebergTypeCounts.size()) json.append(",");
                json.append("\n");
            }

            json.append("    }\n");
            json.append("  },\n");
            json.append("  \"stops\": [\n");

            for (int i = 0; i < stopEvents.size(); i++) {
                json.append("    ").append(mapToJson(stopEvents.get(i)));
                if (i < stopEvents.size() - 1) json.append(",");
                json.append("\n");
            }

            json.append("  ],\n");
            json.append("  \"icebergs\": [\n");

            for (int i = 0; i < icebergEvents.size(); i++) {
                json.append("    ").append(mapToJson(icebergEvents.get(i)));
                if (i < icebergEvents.size() - 1) json.append(",");
                json.append("\n");
            }

            json.append("  ]\n");
            json.append("}\n");
            writer.write(json.toString());

            log("INFO", "Saved data to JSON: " + stopCount.get() + " stops, " + icebergCount.get() + " icebergs");
        } catch (IOException e) {
            log("ERROR", "Failed to save JSON: " + e.getMessage());
        }
    }

    private String mapToJson(Map<String, Object> map) {
        StringBuilder s = new StringBuilder();
        s.append("{");
        int i = 0;
        for (Map.Entry<String, Object> e : map.entrySet()) {
            s.append("\"").append(e.getKey()).append("\":");
            Object v = e.getValue();
            if (v == null) {
                s.append("null");
            } else if (v instanceof Number || v instanceof Boolean) {
                s.append(v);
            } else {
                s.append("\"").append(v.toString().replace("\"", "\\\"")).append("\"");
            }
            if (++i < map.size()) s.append(",");
        }
        s.append("}");
        return s.toString();
    }

    private void exportEventToDb(Map<String, Object> event) {
        // Save to CSV file (keep existing functionality)
        try (FileWriter writer = new FileWriter(SI_DB_PATH, true)) {
            String ts = (String) event.getOrDefault("timestamp", dateFormat.format(new Date()));
            String type = (String) event.getOrDefault("type", "unknown");
            String orderId = String.valueOf(event.getOrDefault("orderID", ""));
            String price = String.valueOf(event.getOrDefault("price", ""));
            String size = String.valueOf(event.getOrDefault("size", ""));
            String side = String.valueOf(event.getOrDefault("side", ""));
            String totalSize = String.valueOf(event.getOrDefault("totalSize", ""));

            String line = String.join(",", ts, type, orderId, price, size, side, totalSize);
            writer.write(line + "\n");
        } catch (IOException e) {
            log("ERROR", "Failed to append event to CSV file: " + e.getMessage());
        }

        // Save to SQLite database
        saveEventToSQLite(event);
    }

    /**
     * Save event to SQLite database
     */
    private void saveEventToSQLite(Map<String, Object> event) {
        if (dbConnection == null) {
            log("WARN", "Database connection is null, cannot save event");
            return;
        }

        String insertSQL = """
            INSERT INTO Events (timestamp, event_type, order_id, price, size, side,
                               total_size, is_bid, instrument, sub_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """;

        try (PreparedStatement pstmt = dbConnection.prepareStatement(insertSQL)) {
            // Get values from event map
            String timestamp = (String) event.getOrDefault("timestamp", dateFormat.format(new Date()));
            String eventType = (String) event.getOrDefault("type", "unknown");
            String orderId = String.valueOf(event.getOrDefault("orderID", ""));

            // Handle numeric values safely
            Double price = null;
            Object priceObj = event.get("price");
            if (priceObj instanceof Number) {
                price = ((Number) priceObj).doubleValue();
            }

            Double size = null;
            Object sizeObj = event.get("size");
            if (sizeObj instanceof Number) {
                size = ((Number) sizeObj).doubleValue();
            }

            String side = (String) event.getOrDefault("side", "");

            Double totalSize = null;
            Object totalSizeObj = event.get("totalSize");
            if (totalSizeObj instanceof Number) {
                totalSize = ((Number) totalSizeObj).doubleValue();
            }

            Boolean isBid = (Boolean) event.get("isBid");
            int isBidInt = (isBid != null && isBid) ? 1 : 0;

            // Get instrument from the first entry in instrumentsInfo (assuming single instrument for now)
            String instrument = instrumentsInfo.isEmpty() ? "" : instrumentsInfo.keySet().iterator().next();

            // Get sub_type for iceberg events
            String subType = (String) event.get("eventType");

            // Set parameters
            pstmt.setString(1, timestamp);
            pstmt.setString(2, eventType);
            pstmt.setString(3, orderId);

            if (price != null) {
                pstmt.setDouble(4, price);
            } else {
                pstmt.setNull(4, java.sql.Types.REAL);
            }

            if (size != null) {
                pstmt.setDouble(5, size);
            } else {
                pstmt.setNull(5, java.sql.Types.REAL);
            }

            pstmt.setString(6, side);

            if (totalSize != null) {
                pstmt.setDouble(7, totalSize);
            } else {
                pstmt.setNull(7, java.sql.Types.REAL);
            }

            pstmt.setInt(8, isBidInt);
            pstmt.setString(9, instrument);
            pstmt.setString(10, subType);

            // Execute insert
            pstmt.executeUpdate();

        } catch (SQLException e) {
            log("ERROR", "Failed to save event to SQLite database: " + e.getMessage());
        }
    }

    private String formatNumber(Object o) {
        if (o == null) return "N/A";
        if (o instanceof Number) {
            return String.format("%.2f", ((Number) o).doubleValue());
        }
        return o.toString();
    }

    @Override
    public void finish() {
        try {
            if (broadcaster != null) {
                broadcaster.finish();
            }
        } catch (Exception e) {
            Log.warn("Error finishing broadcaster: " + e.getMessage());
        }

        // Close database connection
        if (dbConnection != null) {
            try {
                dbConnection.close();
                log("INFO", "Database connection closed successfully");
            } catch (SQLException e) {
                log("ERROR", "Error closing database connection: " + e.getMessage());
            }
        }

        saveToJson();
        log("INFO", "Final statistics: " + stopCount.get() + " stops, " + icebergCount.get() + " icebergs");
    }

    @Override
    public void onInstrumentAdded(String alias, InstrumentInfo instrumentInfo) {
        instrumentsInfo.put(alias, instrumentInfo);

        // Store pip size for price conversion (same as Python: price = tick_price * pips)
        double pips = instrumentInfo.pips;
        instrumentPips.put(alias, pips);

        log("INFO", String.format("Instrument added: %s (pips=%.8f, multiplier=%.2f)",
            alias, pips, instrumentInfo.multiplier));
    }

    @Override
    public StrategyPanel[] getCustomGuiFor(String alias, String indicatorName) {
        if (!isWorking.get()) {
            return new StrategyPanel[0];
        }

        StrategyPanel mainPanel = new StrategyPanel("SI Events - " + alias);
        mainPanel.setLayout(new BorderLayout());

        statsLabel = new JLabel("<html><b>Waiting for events...</b></html>");
        JPanel statsPanel = new JPanel(new BorderLayout());
        statsPanel.add(statsLabel, BorderLayout.NORTH);

        logArea = new JTextArea(20, 60);
        logArea.setEditable(false);
        logArea.setBackground(Color.BLACK);
        logArea.setForeground(Color.GREEN);
        JScrollPane scrollPane = new JScrollPane(logArea);

        mainPanel.add(statsPanel, BorderLayout.NORTH);
        mainPanel.add(scrollPane, BorderLayout.CENTER);

        updateUI();

        return new StrategyPanel[]{mainPanel};
    }
}

