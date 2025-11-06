package velox.api.layer1.simplified.mbo;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Dimension;
import java.awt.Font;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.text.SimpleDateFormat;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TimeZone;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

import javax.swing.BorderFactory;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;
import javax.swing.SwingUtilities;
import javax.swing.border.TitledBorder;

import org.json.JSONObject;

import velox.api.layer1.annotations.Layer1ApiVersion;
import velox.api.layer1.annotations.Layer1ApiVersionValue;
import velox.api.layer1.annotations.Layer1SimpleAttachable;
import velox.api.layer1.annotations.Layer1StrategyName;
import velox.api.layer1.common.Log;
import velox.api.layer1.data.InstrumentInfo;
import velox.api.layer1.data.TradeInfo;
import velox.api.layer1.simplified.TradeDataListener;
import velox.api.layer1.simplified.Api;
import velox.api.layer1.simplified.CustomModule;
import velox.api.layer1.simplified.CustomSettingsPanelProvider;
import velox.api.layer1.simplified.InitialState;
import velox.gui.StrategyPanel;

/**
 * MBO Flow Analyzer
 * Java implementation of mbo_flow_analyzer.py
 *
 * Analyzes order book and trade data to detect patterns and abnormal activity
 * Provides real-time alerts and statistical analysis
 */
@Layer1SimpleAttachable
@Layer1StrategyName("MBO Flow Analyzer")
@Layer1ApiVersion(Layer1ApiVersionValue.VERSION2)
public class MboFlowAnalyzer implements CustomModule, CustomSettingsPanelProvider, TradeDataListener {

    // Configuration
    private static final String DB_PATH = "F:/TradingAgent/enhanced_market_monitor_mbo.db";
    private static final String DEBUG_FILE = "F:/TradingAgent/mbo_analyzer_debug.log";
    private static final String ANALYTICS_FILE = "F:/TradingAgent/mbo_analytics.json";

    // Trading analysis windows (in seconds)
    private static final int SHORT_WINDOW = 60;  // 1 minute
    private static final int MEDIUM_WINDOW = 300;  // 5 minutes
    private static final int LONG_WINDOW = 900;  // 15 minutes

    // Threshold settings
    private static final double VOLUME_SPIKE_THRESHOLD = 2.5;  // Multiple of average volume
    private static final double PRICE_MOVE_THRESHOLD = 0.5;  // Significant price move (in ticks)
    private static final int MIN_TRADE_COUNT = 10;  // Minimum trades to consider for analysis

    // UI refresh rate (ms)
    private static final int UI_REFRESH_RATE = 1000;

    // Data storage
    private final Map<String, List<Map<String, Object>>> recentTrades = new ConcurrentHashMap<>();
    private final Map<String, Map<String, Object>> instrumentInfo = new ConcurrentHashMap<>();
    private final Map<String, Map<String, Double>> analytics = new ConcurrentHashMap<>();
    private final Map<String, Map<String, Object>> alerts = new ConcurrentHashMap<>();

    // Database connection
    private Connection dbConnection;

    // API reference
    private Api api;
    private String currentAlias;

    // UI components
    private JTextArea analyticsTextArea;
    private JTextArea alertsTextArea;
    private JLabel statusLabel;

    // Scheduled executor for background tasks
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(2);

    // Counters
    private final AtomicInteger tradeCounts = new AtomicInteger(0);
    private final AtomicInteger alertCounts = new AtomicInteger(0);

    // Date formatters
    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
    private final DateTimeFormatter isoFormatter = DateTimeFormatter.ISO_OFFSET_DATE_TIME;

    public MboFlowAnalyzer() {
        // Set timezone for date formatter
        dateFormat.setTimeZone(TimeZone.getTimeZone("UTC"));

        // Initialize database connection
        initializeDatabase();
    }

    @Override
    public void initialize(String alias, InstrumentInfo info, Api api, InitialState initialState) {
        this.api = api;
        this.currentAlias = alias;

        // Store instrument information
        Map<String, Object> params = new HashMap<>();
        params.put("alias", alias);
        params.put("pips", info.pips);
        params.put("tickSize", info.pips);
        params.put("symbol", normalizeSymbol(alias));
        instrumentInfo.put(alias, params);

        // Initialize data structures
        recentTrades.put(alias, new ArrayList<>());
        analytics.put(alias, new HashMap<>());
        alerts.put(alias, new HashMap<>());

        // Start background tasks
        startBackgroundTasks();

        logDebug("Initialized MBO Flow Analyzer for: " + alias);
        logDebug("Instrument parameters: " + params);
    }

    @Override
    public void stop() {
        // Shutdown background tasks
        scheduler.shutdown();
        try {
            if (!scheduler.awaitTermination(5, TimeUnit.SECONDS)) {
                scheduler.shutdownNow();
            }
        } catch (InterruptedException e) {
            scheduler.shutdownNow();
            Thread.currentThread().interrupt();
        }

        // Close database connection
        try {
            if (dbConnection != null && !dbConnection.isClosed()) {
                dbConnection.close();
                logDebug("Database connection closed");
            }
        } catch (SQLException e) {
            logDebug("Error closing database connection", e);
        }
    }

    @Override
    public StrategyPanel[] getCustomSettingsPanels() {
        // Create the main panel
        StrategyPanel mainPanel = new StrategyPanel("MBO Flow Analyzer");
        mainPanel.setLayout(new BorderLayout(5, 5));

        // Create status panel
        JPanel statusPanel = new JPanel(new BorderLayout());
        statusPanel.setBorder(BorderFactory.createEmptyBorder(5, 5, 5, 5));
        statusLabel = new JLabel("Initializing...");
        statusLabel.setFont(new Font("SansSerif", Font.BOLD, 12));
        statusPanel.add(statusLabel, BorderLayout.CENTER);

        // Create analytics panel
        JPanel analyticsPanel = new JPanel(new BorderLayout());
        analyticsPanel.setBorder(BorderFactory.createTitledBorder(
                BorderFactory.createEtchedBorder(),
                "Market Analytics",
                TitledBorder.LEFT,
                TitledBorder.TOP));

        analyticsTextArea = new JTextArea();
        analyticsTextArea.setEditable(false);
        analyticsTextArea.setFont(new Font("Monospaced", Font.PLAIN, 12));
        analyticsTextArea.setBackground(new Color(240, 240, 240));
        JScrollPane analyticsScrollPane = new JScrollPane(analyticsTextArea);
        analyticsScrollPane.setPreferredSize(new Dimension(300, 200));
        analyticsPanel.add(analyticsScrollPane, BorderLayout.CENTER);

        // Create alerts panel
        JPanel alertsPanel = new JPanel(new BorderLayout());
        alertsPanel.setBorder(BorderFactory.createTitledBorder(
                BorderFactory.createEtchedBorder(),
                "Alerts & Patterns",
                TitledBorder.LEFT,
                TitledBorder.TOP));

        alertsTextArea = new JTextArea();
        alertsTextArea.setEditable(false);
        alertsTextArea.setFont(new Font("Monospaced", Font.PLAIN, 12));
        alertsTextArea.setBackground(new Color(255, 240, 240));
        JScrollPane alertsScrollPane = new JScrollPane(alertsTextArea);
        alertsScrollPane.setPreferredSize(new Dimension(300, 200));
        alertsPanel.add(alertsScrollPane, BorderLayout.CENTER);

        // Add panels to main panel
        mainPanel.add(statusPanel, BorderLayout.NORTH);
        mainPanel.add(analyticsPanel, BorderLayout.CENTER);
        mainPanel.add(alertsPanel, BorderLayout.SOUTH);

        return new StrategyPanel[] { mainPanel };
    }

    @Override
    public void onTrade(double price, int size, TradeInfo tradeInfo) {
        try {
            String alias = currentAlias; // Using stored instrument alias
            // In Bookmap simplified API, TradeInfo doesn't have isBid field directly
            // Using tradeInfo.aggressor == TradeInfo.AGGRESSOR_BUY to determine side
            boolean isBid = tradeInfo.aggressor == TradeInfo.AGGRESSOR_BUY;

            // Create trade record
            Map<String, Object> trade = new HashMap<>();
            trade.put("price", price);
            trade.put("size", size);
            trade.put("isBid", isBid);
            trade.put("timestamp", ZonedDateTime.now(ZoneId.of("UTC")).format(isoFormatter));
            // TradeInfo doesn't have a getTradeId method, so generating a unique ID based on timestamp and price
            trade.put("tradeId", System.currentTimeMillis() + "-" + Double.toString(price).replace('.', '-'));
            trade.put("aggressor", isBid ? "buyer" : "seller");

            // Add to recent trades
            List<Map<String, Object>> trades = recentTrades.get(alias);
            if (trades != null) {
                trades.add(trade);
                // Keep only last 1000 trades
                while (trades.size() > 1000) {
                    trades.remove(0);
                }
            }

            tradeCounts.incrementAndGet();

            // Real-time analysis
            analyzeTradeImpact(alias, trade);

        } catch (Exception e) {
            logDebug("Error in onTrade", e);
        }
    }

    private void initializeDatabase() {
        try {
            // Load SQLite JDBC driver
            Class.forName("org.sqlite.JDBC");

            // Create connection
            dbConnection = DriverManager.getConnection("jdbc:sqlite:" + DB_PATH);
            logDebug("Connected to database: " + DB_PATH);
        } catch (ClassNotFoundException | SQLException e) {
            logDebug("Error initializing database", e);
        }
    }

    private void startBackgroundTasks() {
        // Task to perform detailed analysis every 5 seconds
        scheduler.scheduleAtFixedRate(this::performDetailedAnalysis, 5, 5, TimeUnit.SECONDS);

        // Task to check MBO patterns every 2 seconds
        scheduler.scheduleAtFixedRate(this::analyzeMboPatterns, 2, 2, TimeUnit.SECONDS);

        // Task to refresh UI every second
        scheduler.scheduleAtFixedRate(this::refreshUI, 1, 1, TimeUnit.SECONDS);

        // Task to save analytics to file every 10 seconds
        scheduler.scheduleAtFixedRate(this::saveAnalyticsToFile, 10, 10, TimeUnit.SECONDS);

        logDebug("Background tasks started");
    }

    private void performDetailedAnalysis() {
        try {
            String alias = currentAlias;
            if (alias == null) return;

            // Get recent trades for this instrument
            List<Map<String, Object>> trades = recentTrades.get(alias);
            if (trades == null || trades.isEmpty()) return;

            // Calculate analytics
            Map<String, Double> stats = calculateTradeStats(trades);

            // Update analytics
            analytics.put(alias, stats);

            // Detect patterns and generate alerts
            detectPatterns(alias, trades, stats);

        } catch (Exception e) {
            logDebug("Error in performDetailedAnalysis", e);
        }
    }

    private Map<String, Double> calculateTradeStats(List<Map<String, Object>> trades) {
        Map<String, Double> stats = new HashMap<>();

        if (trades.isEmpty()) {
            return stats;
        }

        try {
            // Calculate basic statistics
            double totalVolume = 0;
            double buyVolume = 0;
            double sellVolume = 0;
            double vwap = 0;
            double highPrice = Double.NEGATIVE_INFINITY;
            double lowPrice = Double.POSITIVE_INFINITY;

            for (Map<String, Object> trade : trades) {
                double price = (double) trade.get("price");
                int size = (int) trade.get("size");
                boolean isBid = (boolean) trade.get("isBid");

                totalVolume += size;
                vwap += price * size;

                if (isBid) {
                    buyVolume += size;
                } else {
                    sellVolume += size;
                }

                highPrice = Math.max(highPrice, price);
                lowPrice = Math.min(lowPrice, price);
            }

            if (totalVolume > 0) {
                vwap /= totalVolume;
            }

            // Calculate delta and ratio
            double delta = buyVolume - sellVolume;
            double ratio = totalVolume > 0 ? buyVolume / totalVolume : 0.5;

            // Store results
            stats.put("tradeCount", (double) trades.size());
            stats.put("totalVolume", totalVolume);
            stats.put("buyVolume", buyVolume);
            stats.put("sellVolume", sellVolume);
            stats.put("vwap", vwap);
            stats.put("highPrice", highPrice);
            stats.put("lowPrice", lowPrice);
            stats.put("delta", delta);
            stats.put("deltaRatio", ratio);
            stats.put("range", highPrice - lowPrice);

            // Calculate time-based metrics
            calculateTimeBasedMetrics(trades, stats);

        } catch (Exception e) {
            logDebug("Error calculating trade stats", e);
        }

        return stats;
    }

    private void calculateTimeBasedMetrics(List<Map<String, Object>> trades, Map<String, Double> stats) {
        try {
            ZonedDateTime now = ZonedDateTime.now(ZoneId.of("UTC"));

            // Time windows in seconds
            int[] windows = { SHORT_WINDOW, MEDIUM_WINDOW, LONG_WINDOW };
            String[] windowNames = { "short", "medium", "long" };

            for (int i = 0; i < windows.length; i++) {
                int window = windows[i];
                String name = windowNames[i];

                ZonedDateTime cutoff = now.minusSeconds(window);

                // Filter trades in this window
                List<Map<String, Object>> windowTrades = trades.stream()
                        .filter(trade -> {
                            String timestamp = (String) trade.get("timestamp");
                            ZonedDateTime tradeTime = ZonedDateTime.parse(timestamp, isoFormatter);
                            return !tradeTime.isBefore(cutoff);
                        })
                        .toList();

                // Calculate window metrics
                double windowVolume = 0;
                double windowBuyVolume = 0;
                double windowSellVolume = 0;
                double firstPrice = windowTrades.isEmpty() ? 0 : (double) windowTrades.get(0).get("price");
                double lastPrice = windowTrades.isEmpty() ? 0 : (double) windowTrades.get(windowTrades.size() - 1).get("price");

                for (Map<String, Object> trade : windowTrades) {
                    int size = (int) trade.get("size");
                    boolean isBid = (boolean) trade.get("isBid");

                    windowVolume += size;
                    if (isBid) {
                        windowBuyVolume += size;
                    } else {
                        windowSellVolume += size;
                    }
                }

                // Store window metrics
                stats.put(name + "WindowVolume", windowVolume);
                stats.put(name + "WindowBuyVolume", windowBuyVolume);
                stats.put(name + "WindowSellVolume", windowSellVolume);
                stats.put(name + "WindowDelta", windowBuyVolume - windowSellVolume);
                stats.put(name + "WindowPriceChange", lastPrice - firstPrice);
                stats.put(name + "WindowTradeCount", (double) windowTrades.size());
            }

        } catch (Exception e) {
            logDebug("Error calculating time-based metrics", e);
        }
    }

    private void detectPatterns(String alias, List<Map<String, Object>> trades, Map<String, Double> stats) {
        try {
            // Skip if not enough data
            if (trades.size() < MIN_TRADE_COUNT) {
                return;
            }

            Map<String, Object> instrumentData = instrumentInfo.get(alias);
            if (instrumentData == null) return;

            double tickSize = (double) instrumentData.get("tickSize");

            // Check for volume spikes
            double shortVolume = stats.getOrDefault("shortWindowVolume", 0.0);
            double mediumVolume = stats.getOrDefault("mediumWindowVolume", 0.0);
            double longVolume = stats.getOrDefault("longWindowVolume", 0.0);

            double shortAvgVolume = shortVolume / SHORT_WINDOW;
            double mediumAvgVolume = mediumVolume / MEDIUM_WINDOW;
            double longAvgVolume = longVolume / LONG_WINDOW;

            // Short-term volume spike
            if (shortAvgVolume > mediumAvgVolume * VOLUME_SPIKE_THRESHOLD) {
                createAlert(alias, "SHORT_VOLUME_SPIKE",
                        "Short-term volume spike: " + Math.round(shortAvgVolume) + " vs avg " + Math.round(mediumAvgVolume),
                        "high");
            }

            // Medium-term volume spike
            if (mediumAvgVolume > longAvgVolume * VOLUME_SPIKE_THRESHOLD) {
                createAlert(alias, "MEDIUM_VOLUME_SPIKE",
                        "Medium-term volume spike: " + Math.round(mediumAvgVolume) + " vs avg " + Math.round(longAvgVolume),
                        "medium");
            }

            // Price move patterns
            double shortPriceChange = stats.getOrDefault("shortWindowPriceChange", 0.0);
            // We'll use short-term price changes for alerts
            // Medium-term price changes are tracked in analytics but not used for immediate alerts

            // Significant short-term price move
            if (Math.abs(shortPriceChange) > PRICE_MOVE_THRESHOLD * tickSize) {
                String direction = shortPriceChange > 0 ? "up" : "down";
                createAlert(alias, "SHORT_PRICE_MOVE_" + direction.toUpperCase(),
                        "Short-term price move " + direction + ": " + round(shortPriceChange, 2) + " points",
                        "high");
            }

            // Buying/selling pressure
            double shortDelta = stats.getOrDefault("shortWindowDelta", 0.0);
            double shortVol = stats.getOrDefault("shortWindowVolume", 1.0); // Avoid division by zero
            double deltaRatio = shortDelta / shortVol;

            if (Math.abs(deltaRatio) > 0.6) { // Strong imbalance
                String pressure = deltaRatio > 0 ? "buying" : "selling";
                createAlert(alias, pressure.toUpperCase() + "_PRESSURE",
                        "Strong " + pressure + " pressure: " + Math.round(Math.abs(deltaRatio) * 100) + "%",
                        "medium");
            }

        } catch (Exception e) {
            logDebug("Error detecting patterns", e);
        }
    }

    private void analyzeMboPatterns() {
        try {
            String alias = currentAlias;
            if (alias == null || dbConnection == null || dbConnection.isClosed()) return;

            String symbol = normalizeSymbol(alias);

            // Get recent MBO updates from database
            ZonedDateTime cutoff = ZonedDateTime.now(ZoneId.of("UTC")).minusMinutes(5);
            String cutoffStr = cutoff.format(isoFormatter);

            String sql = "SELECT * FROM mbo_updates WHERE symbol = ? AND timestamp > ? ORDER BY timestamp DESC LIMIT 1000";

            try (PreparedStatement pstmt = dbConnection.prepareStatement(sql)) {
                pstmt.setString(1, symbol);
                pstmt.setString(2, cutoffStr);

                ResultSet rs = pstmt.executeQuery();

                // Process MBO updates
                Map<String, Map<String, Object>> orders = new HashMap<>();
                Map<Double, Integer> priceMap = new TreeMap<>();

                while (rs.next()) {
                    String orderId = rs.getString("order_id");
                    double price = rs.getDouble("price");
                    int size = rs.getInt("size");
                    boolean isBid = rs.getInt("is_bid") == 1;
                    String timestamp = rs.getString("timestamp");

                    Map<String, Object> order = new HashMap<>();
                    order.put("orderId", orderId);
                    order.put("price", price);
                    order.put("size", size);
                    order.put("isBid", isBid);
                    order.put("timestamp", timestamp);

                    orders.put(orderId, order);

                    // Track price levels
                    if (size > 0) {
                        priceMap.put(price, priceMap.getOrDefault(price, 0) + size);
                    }
                }

                // Detect iceberg orders
                detectIcebergOrders(alias, orders);

                // Detect spoofing patterns
                detectSpoofingPatterns(alias, orders, priceMap);

                // Detect stop runs
                detectStopRuns(alias, orders, priceMap);

            }
        } catch (SQLException e) {
            logDebug("Error analyzing MBO patterns", e);
        }
    }

    private void detectIcebergOrders(String alias, Map<String, Map<String, Object>> orders) {
        try {
            // Group orders by price level
            Map<Double, List<Map<String, Object>>> priceOrders = new HashMap<>();

            for (Map<String, Object> order : orders.values()) {
                double price = (double) order.get("price");

                List<Map<String, Object>> ordersAtPrice = priceOrders.computeIfAbsent(price, k -> new ArrayList<>());
                ordersAtPrice.add(order);
            }

            // Look for replenishment patterns at each price level
            for (Map.Entry<Double, List<Map<String, Object>>> entry : priceOrders.entrySet()) {
                double price = entry.getKey();
                List<Map<String, Object>> ordersAtPrice = entry.getValue();

                if (ordersAtPrice.size() < 5) continue; // Need multiple orders to detect pattern

                // Count number of new orders at this level
                int newOrderCount = 0;
                int totalSize = 0;

                for (Map<String, Object> order : ordersAtPrice) {
                    int size = (int) order.get("size");
                    totalSize += size;

                    if (size > 0) {
                        newOrderCount++;
                    }
                }

                // Potential iceberg if many new orders at same price level
                if (newOrderCount >= 5) {
                    boolean isBid = (boolean) ordersAtPrice.get(0).get("isBid");
                    String side = isBid ? "BID" : "ASK";

                    createAlert(alias, "ICEBERG_" + side,
                            "Potential iceberg at " + price + " (" + side + "): " + newOrderCount + " refreshes, " + totalSize + " total",
                            "high");
                }
            }
        } catch (Exception e) {
            logDebug("Error detecting iceberg orders", e);
        }
    }

    private void detectSpoofingPatterns(String alias, Map<String, Map<String, Object>> orders, Map<Double, Integer> priceMap) {
        // Note: priceMap parameter is kept for future enhancements but not currently used
        try {
            // Look for large orders that appear and disappear quickly
            Map<String, Integer> orderChanges = new HashMap<>();

            for (Map<String, Object> order : orders.values()) {
                String orderId = (String) order.get("orderId");
                int size = (int) order.get("size");

                orderChanges.put(orderId, orderChanges.getOrDefault(orderId, 0) + 1);
            }

            // Identify orders with multiple updates
            for (Map.Entry<String, Integer> entry : orderChanges.entrySet()) {
                String orderId = entry.getKey();
                int changes = entry.getValue();

                if (changes >= 3) { // Order modified multiple times
                    Map<String, Object> order = orders.get(orderId);
                    if (order != null) {
                        double price = (double) order.get("price");
                        int size = (int) order.get("size");
                        boolean isBid = (boolean) order.get("isBid");
                        String side = isBid ? "BID" : "ASK";

                        // Potential spoofing if large order with many changes
                        if (size > 50) { // Arbitrary threshold for "large" order
                            createAlert(alias, "SPOOFING_" + side,
                                    "Potential spoofing at " + price + " (" + side + "): OrderID " + orderId + " changed " + changes + " times",
                                    "medium");
                        }
                    }
                }
            }
        } catch (Exception e) {
            logDebug("Error detecting spoofing patterns", e);
        }
    }

    private void detectStopRuns(String alias, Map<String, Map<String, Object>> orders, Map<Double, Integer> priceMap) {
        // Note: orders and priceMap parameters are kept for future algorithmic enhancements
        // Currently using direct database queries for stop run detection
        try {
            // Get recent trades from database
            ZonedDateTime cutoff = ZonedDateTime.now(ZoneId.of("UTC")).minusMinutes(2);
            String cutoffStr = cutoff.format(isoFormatter);
            String symbol = normalizeSymbol(alias);

            String sql = "SELECT * FROM trades WHERE symbol = ? AND timestamp > ? ORDER BY timestamp";

            try (PreparedStatement pstmt = dbConnection.prepareStatement(sql)) {
                pstmt.setString(1, symbol);
                pstmt.setString(2, cutoffStr);

                ResultSet rs = pstmt.executeQuery();

                List<Map<String, Object>> trades = new ArrayList<>();

                while (rs.next()) {
                    Map<String, Object> trade = new HashMap<>();
                    trade.put("price", rs.getDouble("price"));
                    trade.put("size", rs.getInt("size"));
                    trade.put("isBid", rs.getInt("is_bid") == 1);
                    trade.put("timestamp", rs.getString("timestamp"));
                    trades.add(trade);
                }

                if (trades.isEmpty()) return;

                // Analyze trade sequence for stop runs
                // A stop run typically involves a rapid sequence of trades in one direction,
                // often accompanied by a quick reversal

                double firstPrice = (double) trades.get(0).get("price");
                double lastPrice = (double) trades.get(trades.size() - 1).get("price");
                double maxMove = 0;
                double currentMove = 0;
                double prevPrice = firstPrice;

                for (Map<String, Object> trade : trades) {
                    double price = (double) trade.get("price");
                    double move = price - prevPrice;

                    currentMove += move;
                    maxMove = Math.max(maxMove, Math.abs(currentMove));

                    prevPrice = price;
                }

                // Check for significant move followed by reversal
                Map<String, Object> instrumentData = instrumentInfo.get(alias);
                if (instrumentData == null) return;

                double tickSize = (double) instrumentData.get("tickSize");

                if (maxMove > 5 * tickSize && Math.abs(lastPrice - firstPrice) < 2 * tickSize) {
                    String direction = currentMove > 0 ? "upward" : "downward";
                    createAlert(alias, "STOP_RUN_" + direction.toUpperCase(),
                            "Potential stop run " + direction + ": " + round(maxMove, 2) + " points move with reversal",
                            "high");
                }

            }
        } catch (SQLException e) {
            logDebug("Error detecting stop runs", e);
        } catch (Exception e) {
            logDebug("Error in stop run detection", e);
        }
    }

    private void createAlert(String alias, String type, String message, String priority) {
        try {
            String id = type + "_" + System.currentTimeMillis();
            String timestamp = ZonedDateTime.now(ZoneId.of("UTC")).format(isoFormatter);

            Map<String, Object> alert = new HashMap<>();
            alert.put("id", id);
            alert.put("type", type);
            alert.put("message", message);
            alert.put("timestamp", timestamp);
            alert.put("priority", priority);
            alert.put("alias", alias);

            // Add to alerts map
            alerts.put(id, alert);

            // Increment alert count
            alertCounts.incrementAndGet();

            // Log the alert
            logDebug("ALERT [" + priority.toUpperCase() + "]: " + message);

        } catch (Exception e) {
            logDebug("Error creating alert", e);
        }
    }

    private void analyzeTradeImpact(String alias, Map<String, Object> trade) {
        try {
            double price = (double) trade.get("price");
            int size = (int) trade.get("size");
            boolean isBid = (boolean) trade.get("isBid");

            // Get recent trades for this instrument
            List<Map<String, Object>> trades = recentTrades.get(alias);
            if (trades == null || trades.size() < 2) return;

            // Get previous trade
            Map<String, Object> prevTrade = trades.get(trades.size() - 2);
            double prevPrice = (double) prevTrade.get("price");

            // Check for price impact
            double priceChange = price - prevPrice;

            Map<String, Object> instrumentData = instrumentInfo.get(alias);
            if (instrumentData == null) return;

            double tickSize = (double) instrumentData.get("tickSize");

            // Significant price impact from single trade
            if (Math.abs(priceChange) > tickSize && size > 10) { // Arbitrary thresholds
                String direction = priceChange > 0 ? "up" : "down";

                createAlert(alias, "PRICE_IMPACT_" + direction.toUpperCase(),
                        "Significant price impact: " + round(priceChange, 2) + " points " + direction + " on " + size + " lot trade",
                        "medium");
            }

        } catch (Exception e) {
            logDebug("Error analyzing trade impact", e);
        }
    }

    private void refreshUI() {
        try {
            if (analyticsTextArea == null || alertsTextArea == null || statusLabel == null) {
                return;
            }

            SwingUtilities.invokeLater(() -> {
                try {
                    updateAnalyticsDisplay();
                    updateAlertsDisplay();
                    updateStatusDisplay();
                } catch (Exception e) {
                    logDebug("Error updating UI", e);
                }
            });
        } catch (Exception e) {
            logDebug("Error in refreshUI", e);
        }
    }

    private void updateAnalyticsDisplay() {
        try {
            String alias = currentAlias;
            if (alias == null) return;

            Map<String, Double> stats = analytics.get(alias);
            if (stats == null || stats.isEmpty()) {
                analyticsTextArea.setText("Waiting for data...");
                return;
            }

            StringBuilder sb = new StringBuilder();
            sb.append("Analytics for ").append(normalizeSymbol(alias)).append("\n\n");

            sb.append("Trades: ").append(stats.getOrDefault("tradeCount", 0.0).intValue()).append("\n");
            sb.append("Volume: ").append(stats.getOrDefault("totalVolume", 0.0).intValue()).append(" lots\n");
            sb.append("Buy Vol: ").append(stats.getOrDefault("buyVolume", 0.0).intValue()).append(" lots\n");
            sb.append("Sell Vol: ").append(stats.getOrDefault("sellVolume", 0.0).intValue()).append(" lots\n");
            sb.append("Delta: ").append(stats.getOrDefault("delta", 0.0).intValue()).append(" lots\n");
            sb.append("Delta Ratio: ").append(Math.round(stats.getOrDefault("deltaRatio", 0.5) * 100)).append("%\n");
            sb.append("VWAP: ").append(round(stats.getOrDefault("vwap", 0.0), 2)).append("\n");
            sb.append("Range: ").append(round(stats.getOrDefault("range", 0.0), 2)).append("\n\n");

            sb.append("1min Volume: ").append(stats.getOrDefault("shortWindowVolume", 0.0).intValue()).append(" lots\n");
            sb.append("5min Volume: ").append(stats.getOrDefault("mediumWindowVolume", 0.0).intValue()).append(" lots\n");
            sb.append("15min Volume: ").append(stats.getOrDefault("longWindowVolume", 0.0).intValue()).append(" lots\n\n");

            sb.append("1min Price Change: ").append(round(stats.getOrDefault("shortWindowPriceChange", 0.0), 2)).append("\n");
            sb.append("5min Price Change: ").append(round(stats.getOrDefault("mediumWindowPriceChange", 0.0), 2)).append("\n");

            analyticsTextArea.setText(sb.toString());
            analyticsTextArea.setCaretPosition(0);

        } catch (Exception e) {
            logDebug("Error updating analytics display", e);
        }
    }

    private void updateAlertsDisplay() {
        try {
            if (alerts.isEmpty()) {
                alertsTextArea.setText("No alerts detected yet...");
                return;
            }

            StringBuilder sb = new StringBuilder();
            sb.append("Recent Alerts:\n\n");

            // Sort alerts by timestamp (most recent first)
            List<Map<String, Object>> sortedAlerts = new ArrayList<>(alerts.values());
            sortedAlerts.sort((a1, a2) -> {
                String ts1 = (String) a1.get("timestamp");
                String ts2 = (String) a2.get("timestamp");
                return ts2.compareTo(ts1); // Reverse order
            });

            // Take only most recent 10 alerts
            int count = 0;
            for (Map<String, Object> alert : sortedAlerts) {
                if (count++ >= 10) break;

                String timestamp = (String) alert.get("timestamp");
                String localTime = ZonedDateTime.parse(timestamp, isoFormatter)
                        .withZoneSameInstant(ZoneId.systemDefault())
                        .format(DateTimeFormatter.ofPattern("HH:mm:ss"));

                String priority = (String) alert.get("priority");
                String message = (String) alert.get("message");

                sb.append("[").append(localTime).append("] ");
                if ("high".equals(priority)) {
                    sb.append("❗ ");
                } else if ("medium".equals(priority)) {
                    sb.append("⚠ ");
                }
                sb.append(message).append("\n\n");
            }

            alertsTextArea.setText(sb.toString());
            alertsTextArea.setCaretPosition(0);

        } catch (Exception e) {
            logDebug("Error updating alerts display", e);
        }
    }

    private void updateStatusDisplay() {
        try {
            String alias = currentAlias;
            if (alias == null) {
                statusLabel.setText("No instrument selected");
                return;
            }

            int trades = tradeCounts.get();
            int alerts = alertCounts.get();

            StringBuilder sb = new StringBuilder();
            sb.append("Monitoring: ").append(normalizeSymbol(alias));
            sb.append(" | Trades: ").append(trades);
            sb.append(" | Alerts: ").append(alerts);

            statusLabel.setText(sb.toString());

        } catch (Exception e) {
            logDebug("Error updating status display", e);
        }
    }

    private void saveAnalyticsToFile() {
        try {
            String alias = currentAlias;
            if (alias == null) return;

            Map<String, Double> stats = analytics.get(alias);
            if (stats == null || stats.isEmpty()) return;

            // Prepare JSON data
            Map<String, Object> jsonData = new HashMap<>();
            jsonData.put("timestamp", ZonedDateTime.now(ZoneId.of("UTC")).format(isoFormatter));
            jsonData.put("instrument", alias);
            jsonData.put("symbol", normalizeSymbol(alias));
            jsonData.put("analytics", new HashMap<>(stats));

            // Add alerts
            List<Map<String, Object>> recentAlerts = new ArrayList<>();
            for (Map<String, Object> alert : alerts.values()) {
                recentAlerts.add(new HashMap<>(alert));
                if (recentAlerts.size() >= 20) break; // Limit to 20 most recent alerts
            }
            jsonData.put("alerts", recentAlerts);

            // Write to file
            // Create formatted JSON string directly
            StringBuilder jsonStr = new StringBuilder("{\n");
            jsonStr.append("  \"timestamp\": \"").append(ZonedDateTime.now(ZoneId.of("UTC")).format(isoFormatter)).append("\",\n");
            jsonStr.append("  \"instrument\": \"").append(alias).append("\",\n");
            jsonStr.append("  \"symbol\": \"").append(normalizeSymbol(alias)).append("\",\n");
            jsonStr.append("  \"analytics\": {\n");

            int statCount = 0;
            for (Map.Entry<String, Object> entry : jsonData.entrySet()) {
                if (statCount++ > 0) jsonStr.append(",\n");
                jsonStr.append("    \"").append(entry.getKey()).append("\": ");
                Object value = entry.getValue();
                if (value instanceof String) {
                    jsonStr.append("\"").append(value).append("\"");
                } else {
                    jsonStr.append(value);
                }
            }

            jsonStr.append("\n  },\n");
            jsonStr.append("  \"alerts\": [\n");

            // Add alert data
            int alertCount = 0;
            for (Map.Entry<String, Object> alert : alerts.entrySet()) {
                if (alertCount++ > 0) jsonStr.append(",\n");
                jsonStr.append("    {\n");
                jsonStr.append("      \"id\": \"").append(alert.getKey()).append("\",\n");
                Map<String, Object> alertData = (Map<String, Object>)alert.getValue();
                for (Map.Entry<String, Object> field : alertData.entrySet()) {
                    jsonStr.append("      \"").append(field.getKey()).append("\": ");
                    Object value = field.getValue();
                    if (value instanceof String) {
                        jsonStr.append("\"").append(value).append("\"");
                    } else {
                        jsonStr.append(value);
                    }
                    jsonStr.append(",\n");
                }
                jsonStr.append("    }");
            }

            jsonStr.append("\n  ]\n");
            jsonStr.append("}\n");

            try (FileWriter writer = new FileWriter(ANALYTICS_FILE)) {
                writer.write(jsonStr.toString());
            }

        } catch (IOException e) {
            logDebug("Error saving analytics to file", e);
        } catch (Exception e) {
            logDebug("Error in saveAnalyticsToFile", e);
        }
    }

    private String normalizeSymbol(String alias) {
        String symbol = alias;

        // Remove exchange prefix (e.g., "CME:")
        if (symbol.contains(":")) {
            String[] parts = symbol.split(":", 2);
            symbol = parts[1];
        }

        // Remove suffix (e.g., "@RITHMIC")
        if (symbol.contains("@")) {
            symbol = symbol.split("@")[0];
        }

        return symbol;
    }

    private void logDebug(String message) {
        logDebug(message, null);
    }

    private void logDebug(String message, Exception error) {
        try {
            String timestamp = dateFormat.format(new Date());
            String logMessage = "[" + timestamp + "] " + message;

            if (error != null) {
                logMessage = logMessage + ": " + error.getMessage();
            }

            // Log to console
            Log.info(logMessage);

            // Log to file
            try {
                Files.createDirectories(Paths.get(DEBUG_FILE).getParent());
                try (FileWriter writer = new FileWriter(DEBUG_FILE, true)) {
                    writer.write(logMessage + "\n");

                    if (error != null) {
                        writer.write("[" + timestamp + "] Stack trace: ");
                        for (StackTraceElement element : error.getStackTrace()) {
                            writer.write("\n    " + element.toString());
                        }
                        writer.write("\n");
                    }
                }
            } catch (IOException e) {
                Log.error("Failed to write to debug file", e);
            }
        } catch (Exception e) {
            Log.error("Error in logDebug", e);
        }
    }

    private static double round(double value, int places) {
        if (places < 0) throw new IllegalArgumentException();

        long factor = (long) Math.pow(10, places);
        value = value * factor;
        long tmp = Math.round(value);
        return (double) tmp / factor;
    }
}
