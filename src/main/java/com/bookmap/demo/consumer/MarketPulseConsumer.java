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

import javax.swing.*;
import java.awt.*;
import java.io.FileWriter;
import java.io.IOException;
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
 * Consumer for Market Pulse broadcasting events
 * Receives and logs market pulse events with trading window filtering
 */
@Layer1Attachable
@Layer1StrategyName("Market Pulse Broadcasting Consumer")
@Layer1ApiVersion(Layer1ApiVersionValue.VERSION2)
public class MarketPulseConsumer implements
        Layer1ApiFinishable,
        Layer1ApiAdminAdapter,
        Layer1ApiInstrumentAdapter,
        Layer1CustomPanelsGetter {

    private static final String LOG_PATH = "F:/TradingAgent/market_pulse_events.log";
    private static final String JSON_PATH = "F:/TradingAgent/market_pulse_data.json";
    private static final String SQLITE_DB_PATH = "F:/TradingAgent/enhanced_market_monitor_mbo.db";

    // Trading windows in EST (Bookmap times are in UTC-4)
    private static final int[][] TRADING_WINDOWS_EST = {
        {16, 0, 20, 0},  // CBDR PM/Asian: 16:00-20:00 EST
        {2, 0, 5, 0},    // CBDR London: 02:00-05:00 EST
        {7, 30, 9, 30}   // Pre-NY: 07:30-09:30 EST
    };

    private JTextArea logArea;
    private JLabel statsLabel;

    private final List<Map<String, Object>> pulseEvents = new ArrayList<>();
    private final AtomicInteger totalCount = new AtomicInteger(0);
    private final Map<String, Integer> typeCounts = new HashMap<>();

    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
    private final Map<String, InstrumentInfo> instrumentsInfo = new ConcurrentHashMap<>();
    private final Map<String, Double> instrumentPips = new ConcurrentHashMap<>();

    private final Layer1ApiProvider provider;
    private final BroadcasterConsumer broadcaster;
    private Connection dbConnection;
    private final AtomicBoolean isWorking = new AtomicBoolean(false);
    private final Connector connector;

    public MarketPulseConsumer(Layer1ApiProvider provider) {
        dateFormat.setTimeZone(TimeZone.getTimeZone("UTC"));
        ListenableHelper.addListeners(provider, this);
        this.provider = provider;

        Log.info("========================================");
        Log.info("Market Pulse Broadcasting Consumer: STARTING UP");
        Log.info("========================================");

        initializeDatabase();

        this.broadcaster = BroadcastFactory.getBroadcasterConsumer(provider, "Market Pulse Broadcasting Consumer", this.getClass());
        this.connector = new Connector(provider, broadcaster, com.bookmap.demo.consumer.providers.Provider.MARKET_PULSE);

        broadcaster.setProviderStatusListener(new ProviderStatusListener() {
            @Override
            public void providerUpdateGenerator(String providerName, String providerId, GeneratorInfo generator, boolean isOnline) {
                log("INFO", String.format("Provider update: %s, generator: %s, online: %s",
                    providerName, generator != null ? generator.getGeneratorName() : "null", isOnline));

                if (isWorking.get()) {
                    ExecutorsUtilities.getExecutor().submit(() -> {
                        MarketPulseConsumer.this.provider.sendUserMessage(new Layer1ApiUserMessageReloadStrategyGui());
                    });
                }
            }
        });

        Log.info("MarketPulseConsumer: Broadcaster created");
        Log.info("Log file: " + LOG_PATH);
        Log.info("SQLite DB: " + SQLITE_DB_PATH);
    }

    private void initializeDatabase() {
        try {
            Class.forName("org.sqlite.JDBC");
            String url = "jdbc:sqlite:" + SQLITE_DB_PATH;
            dbConnection = DriverManager.getConnection(url);

            String createTableSQL = """
                CREATE TABLE IF NOT EXISTS MarketPulseEvents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    price REAL,
                    volume REAL,
                    delta REAL,
                    side TEXT,
                    is_bid INTEGER,
                    instrument TEXT,
                    event_type TEXT,
                    intensity REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """;

            try (Statement stmt = dbConnection.createStatement()) {
                stmt.execute(createTableSQL);
                log("INFO", "SQLite database initialized - MarketPulseEvents table ready");
            }

            String createIndexSQL = "CREATE INDEX IF NOT EXISTS idx_pulse_timestamp ON MarketPulseEvents(timestamp)";
            try (Statement stmt = dbConnection.createStatement()) {
                stmt.execute(createIndexSQL);
            }

        } catch (ClassNotFoundException e) {
            log("ERROR", "SQLite JDBC driver not found: " + e.getMessage());
        } catch (SQLException e) {
            log("ERROR", "Failed to initialize database: " + e.getMessage());
        }
    }

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

    private void connectToProvider() {
        log("INFO", "Connecting to Market Pulse provider...");

        try {
            connector.connect();

            ExecutorsUtilities.getExecutor().submit(() -> {
                try {
                    Thread.sleep(1000);

                    if (connector.isConnected()) {
                        log("INFO", "✓ Successfully connected to Market Pulse");

                        List<String> generators = connector.getGeneratorsNames();
                        log("INFO", "Found " + generators.size() + " generator(s)");

                        for (String generatorName : generators) {
                            log("INFO", "Subscribing to generator: " + generatorName);
                            subscribeToGenerator(generatorName);
                        }
                    } else {
                        log("WARN", "Connection not established, retrying...");
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

    private void subscribeToGenerator(String generatorName) {
        try {
            if (!connector.isConnected()) {
                log("WARN", "Not connected, cannot subscribe to " + generatorName);
                return;
            }

            LiveEventListener eventListener = event -> {
                if (event != null) {
                    processMarketPulseEvent(event);
                }
            };

            LiveConnectionStatusListener connectionListener = isSubscribed -> {
                if (isSubscribed) {
                    log("INFO", "✓ Successfully subscribed to: " + generatorName);
                } else {
                    log("WARN", "✗ Unsubscribed from: " + generatorName);
                }
            };

            broadcaster.subscribeToLiveData(
                com.bookmap.demo.consumer.providers.Provider.MARKET_PULSE.getFullName(),
                generatorName,
                eventListener,
                connectionListener
            );

        } catch (Exception e) {
            log("ERROR", "Failed to subscribe to generator: " + e.getMessage());
        }
    }

    private void processMarketPulseEvent(Object event) {
        try {
            // Check time window first
            Object timeObj = getFieldValue(event, "time");
            if (timeObj instanceof Long) {
                long eventTime = (Long) timeObj;
                if (!isWithinTradingWindow(eventTime)) {
                    log("DEBUG", "MarketPulseEvent outside trading window, skipping");
                    return;
                }
            }

            Map<String, Object> pulseData = new HashMap<>();
            pulseData.put("timestamp", dateFormat.format(new Date()));

            if (totalCount.get() == 0) {
                logEventStructure("MarketPulseEvent", event);
            }

            String instrument = instrumentsInfo.isEmpty() ? "" : instrumentsInfo.keySet().iterator().next();

            // Extract price and convert
            Object priceObj = getFieldValue(event, "price");
            if (priceObj instanceof Integer) {
                int tickPrice = (Integer) priceObj;
                double actualPrice = convertPrice(tickPrice, instrument);
                pulseData.put("price", actualPrice);
            } else {
                pulseData.put("price", priceObj);
            }

            pulseData.put("volume", getFieldValue(event, "volume"));
            pulseData.put("delta", getFieldValue(event, "delta"));

            Boolean isBid = (Boolean) getFieldValue(event, "isBid");
            pulseData.put("isBid", isBid);
            pulseData.put("side", (isBid != null && isBid) ? "BUY" : "SELL");

            Object typeObj = getFieldValue(event, "type");
            String eventType = (typeObj != null) ? typeObj.toString() : "PULSE";
            pulseData.put("eventType", eventType);
            typeCounts.merge(eventType, 1, Integer::sum);

            pulseData.put("intensity", getFieldValue(event, "intensity"));
            pulseData.put("instrument", instrument);

            pulseEvents.add(pulseData);
            int count = totalCount.incrementAndGet();

            String logMsg = String.format("[PULSE #%d] %s @ %s, volume=%s, delta=%s, intensity=%s",
                count,
                pulseData.getOrDefault("side", "N/A"),
                formatNumber(pulseData.get("price")),
                formatNumber(pulseData.get("volume")),
                formatNumber(pulseData.get("delta")),
                formatNumber(pulseData.get("intensity"))
            );

            log("PULSE", logMsg);
            updateUI();
            saveEventToDatabase(pulseData);

            if (count % 10 == 0) {
                saveToJson();
            }

        } catch (Exception e) {
            log("ERROR", "Error processing MarketPulseEvent: " + e.getMessage());
        }
    }

    private void saveEventToDatabase(Map<String, Object> event) {
        if (dbConnection == null) {
            return;
        }

        String insertSQL = """
            INSERT INTO MarketPulseEvents (timestamp, price, volume, delta, side,
                                          is_bid, instrument, event_type, intensity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """;

        try (PreparedStatement pstmt = dbConnection.prepareStatement(insertSQL)) {
            pstmt.setString(1, (String) event.get("timestamp"));

            setDoubleOrNull(pstmt, 2, event.get("price"));
            setDoubleOrNull(pstmt, 3, event.get("volume"));
            setDoubleOrNull(pstmt, 4, event.get("delta"));

            pstmt.setString(5, (String) event.get("side"));

            Boolean isBid = (Boolean) event.get("isBid");
            pstmt.setInt(6, (isBid != null && isBid) ? 1 : 0);

            pstmt.setString(7, (String) event.get("instrument"));
            pstmt.setString(8, (String) event.get("eventType"));

            setDoubleOrNull(pstmt, 9, event.get("intensity"));

            pstmt.executeUpdate();

        } catch (SQLException e) {
            log("ERROR", "Failed to save to database: " + e.getMessage());
        }
    }

    private void setDoubleOrNull(PreparedStatement pstmt, int index, Object value) throws SQLException {
        if (value instanceof Number) {
            pstmt.setDouble(index, ((Number) value).doubleValue());
        } else {
            pstmt.setNull(index, java.sql.Types.REAL);
        }
    }

    private double convertPrice(int tickPrice, String alias) {
        Double pips = instrumentPips.get(alias);
        if (pips == null && !instrumentPips.isEmpty()) {
            pips = instrumentPips.values().iterator().next();
        }
        if (pips == null) {
            pips = 0.25;
        }
        return tickPrice * pips;
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
                return obj.getClass().getMethod(getter).invoke(obj);
            } catch (Exception e2) {
                try {
                    String getter = "is" + Character.toUpperCase(fieldName.charAt(0)) + fieldName.substring(1);
                    return obj.getClass().getMethod(getter).invoke(obj);
                } catch (Exception e3) {
                    return null;
                }
            }
        }
    }

    private void logEventStructure(String eventName, Object event) {
        log("INSPECT", "========================================");
        log("INSPECT", "Inspecting " + eventName);
        log("INSPECT", "Class: " + event.getClass().getName());

        java.lang.reflect.Field[] fields = event.getClass().getDeclaredFields();
        for (java.lang.reflect.Field field : fields) {
            field.setAccessible(true);
            try {
                Object value = field.get(event);
                log("INSPECT", String.format("  %s = %s", field.getName(), value));
            } catch (Exception e) {
                // Ignore
            }
        }
        log("INSPECT", "========================================");
    }

    private void saveToJson() {
        try (FileWriter writer = new FileWriter(JSON_PATH)) {
            StringBuilder json = new StringBuilder();
            json.append("{\n");
            json.append("  \"timestamp\": \"").append(dateFormat.format(new Date())).append("\",\n");
            json.append("  \"statistics\": {\n");
            json.append("    \"total\": ").append(totalCount.get()).append(",\n");
            json.append("    \"types\": {\n");

            int idx = 0;
            for (Map.Entry<String, Integer> e : typeCounts.entrySet()) {
                json.append("      \"").append(e.getKey()).append("\": ").append(e.getValue());
                if (++idx < typeCounts.size()) json.append(",");
                json.append("\n");
            }

            json.append("    }\n");
            json.append("  },\n");
            json.append("  \"events\": [\n");

            for (int i = 0; i < pulseEvents.size(); i++) {
                json.append("    ").append(mapToJson(pulseEvents.get(i)));
                if (i < pulseEvents.size() - 1) json.append(",");
                json.append("\n");
            }

            json.append("  ]\n");
            json.append("}\n");
            writer.write(json.toString());

        } catch (IOException e) {
            log("ERROR", "Failed to save JSON: " + e.getMessage());
        }
    }

    private String mapToJson(Map<String, Object> map) {
        StringBuilder s = new StringBuilder("{");
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

    private void log(String level, String message) {
        String logLine = String.format("[%s] [%s] %s", dateFormat.format(new Date()), level, message);
        Log.info(logLine);

        try (FileWriter writer = new FileWriter(LOG_PATH, true)) {
            writer.write(logLine + "\n");
        } catch (IOException e) {
            Log.error("Failed to write to log", e);
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
                StringBuilder stats = new StringBuilder("<html><b>MARKET PULSE STATISTICS</b><br>");
                stats.append("Total Events: ").append(totalCount.get()).append("<br>");
                if (!typeCounts.isEmpty()) {
                    stats.append("<br><b>Event Types:</b><br>");
                    typeCounts.forEach((type, count) ->
                        stats.append("  ").append(type).append(": ").append(count).append("<br>")
                    );
                }
                stats.append("</html>");
                statsLabel.setText(stats.toString());
            });
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
    public void onUserMessage(Object data) {
        if (data == null) return;

        if (data.getClass() == UserMessageLayersChainCreatedTargeted.class) {
            UserMessageLayersChainCreatedTargeted message = (UserMessageLayersChainCreatedTargeted) data;
            if (message.targetClass == getClass()) {
                isWorking.set(true);
                broadcaster.start();
                log("INFO", "========================================");
                log("INFO", "Broadcaster STARTED - Listening for Market Pulse events");
                log("INFO", "========================================");
                connectToProvider();
                ExecutorsUtilities.getExecutor().submit(() -> {
                    provider.sendUserMessage(new Layer1ApiUserMessageReloadStrategyGui());
                });
            }
        }
    }

    @Override
    public void onInstrumentAdded(String alias, InstrumentInfo instrumentInfo) {
        instrumentsInfo.put(alias, instrumentInfo);
        instrumentPips.put(alias, instrumentInfo.pips);
        log("INFO", String.format("Instrument added: %s (pips=%.8f)", alias, instrumentInfo.pips));
    }

    @Override
    public void finish() {
        if (broadcaster != null) {
            broadcaster.finish();
        }
        if (dbConnection != null) {
            try {
                dbConnection.close();
                log("INFO", "Database connection closed");
            } catch (SQLException e) {
                log("ERROR", "Error closing database: " + e.getMessage());
            }
        }
        saveToJson();
    }

    @Override
    public StrategyPanel[] getCustomGuiFor(String alias, String indicatorName) {
        if (!isWorking.get()) {
            return new StrategyPanel[0];
        }

        StrategyPanel mainPanel = new StrategyPanel("Market Pulse Events - " + alias);
        mainPanel.setLayout(new BorderLayout());

        statsLabel = new JLabel("<html><b>Waiting for events...</b></html>");
        JPanel statsPanel = new JPanel(new BorderLayout());
        statsPanel.add(statsLabel, BorderLayout.NORTH);

        logArea = new JTextArea(20, 60);
        logArea.setEditable(false);
        logArea.setBackground(Color.BLACK);
        logArea.setForeground(Color.CYAN);
        JScrollPane scrollPane = new JScrollPane(logArea);

        mainPanel.add(statsPanel, BorderLayout.NORTH);
        mainPanel.add(scrollPane, BorderLayout.CENTER);

        updateUI();

        return new StrategyPanel[]{mainPanel};
    }
}

