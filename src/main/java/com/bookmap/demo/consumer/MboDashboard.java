package velox.api.layer1.simplified.mbo;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Dimension;
import java.awt.Font;
import java.awt.GridLayout;
import java.io.FileReader;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.text.SimpleDateFormat;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TimeZone;
import java.util.TreeMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

import javax.swing.BorderFactory;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JProgressBar;
import javax.swing.JScrollPane;
import javax.swing.JTable;
import javax.swing.JTextArea;
import javax.swing.SwingUtilities;
import javax.swing.border.TitledBorder;
import javax.swing.table.DefaultTableModel;

import org.json.JSONArray;
import org.json.JSONObject;

import velox.api.layer1.annotations.Layer1ApiVersion;
import velox.api.layer1.annotations.Layer1ApiVersionValue;
import velox.api.layer1.annotations.Layer1SimpleAttachable;
import velox.api.layer1.annotations.Layer1StrategyName;
import velox.api.layer1.common.Log;
import velox.api.layer1.data.InstrumentInfo;
import velox.api.layer1.simplified.Api;
import velox.api.layer1.simplified.CustomModule;
import velox.api.layer1.simplified.CustomSettingsPanelProvider;
import velox.api.layer1.simplified.InitialState;
import velox.gui.StrategyPanel;

/**
 * MBO Dashboard
 * Java implementation of mbo_dashboard.py
 *
 * Provides a visual dashboard for MBO data analysis and order flow monitoring
 */
@Layer1SimpleAttachable
@Layer1StrategyName("MBO Dashboard")
@Layer1ApiVersion(Layer1ApiVersionValue.VERSION2)
public class MboDashboard implements CustomModule, CustomSettingsPanelProvider {

    // Configuration
    private static final String DB_PATH = "F:/TradingAgent/enhanced_market_monitor_mbo.db";
    private static final String DEBUG_FILE = "F:/TradingAgent/mbo_dashboard_debug.log";
    private static final String PRICE_CACHE_FILE = "F:/TradingAgent/live_prices.json";
    private static final String ANALYTICS_FILE = "F:/TradingAgent/mbo_analytics.json";

    // UI refresh rates
    private static final int FAST_REFRESH_RATE = 1000; // 1 second
    private static final int MED_REFRESH_RATE = 5000;  // 5 seconds
    private static final int SLOW_REFRESH_RATE = 15000; // 15 seconds

    // Database connection
    private Connection dbConnection;

    // API reference
    private Api api;
    private String currentAlias;

    // Scheduled executor for background tasks
    private final ScheduledExecutorService scheduler = Executors.newScheduledThreadPool(3);

    // UI components
    private JPanel mainDashboard;
    private JPanel instrumentPanel;
    private JPanel orderFlowPanel;
    private JPanel alertsPanel;
    private JPanel statsPanel;

    // Data tables
    private JTable priceTable;
    private JTable orderFlowTable;
    private JTable statsTable;

    // Text areas
    private JTextArea alertsTextArea;

    // Status components
    private JLabel statusLabel;
    private JProgressBar progressBar;

    // Data storage
    private final Map<String, Map<String, Object>> instrumentData = new HashMap<>();
    private final Map<String, Map<String, Object>> livePrices = new HashMap<>();
    private final List<Map<String, Object>> recentAlerts = new ArrayList<>();
    private final Map<String, Map<String, Double>> analytics = new HashMap<>();
    private final Map<String, List<Map<String, Object>>> orderFlow = new HashMap<>();

    // Date formatters
    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
    private final DateTimeFormatter isoFormatter = DateTimeFormatter.ISO_OFFSET_DATE_TIME;

    public MboDashboard() {
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
        params.put("pointsPerPip", 1.0 / info.pips);
        params.put("symbol", normalizeSymbol(alias));
        instrumentData.put(alias, params);

        // Start background tasks
        startBackgroundTasks();

        logDebug("Initialized MBO Dashboard for: " + alias);
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
        // Create the main dashboard panel
        mainDashboard = new StrategyPanel("MBO Dashboard");
        mainDashboard.setLayout(new BorderLayout(5, 5));

        // Create status panel
        JPanel statusPanel = createStatusPanel();

        // Create instrument panel
        instrumentPanel = new JPanel(new BorderLayout());
        instrumentPanel.setBorder(BorderFactory.createTitledBorder(
                BorderFactory.createEtchedBorder(),
                "Instrument Data",
                TitledBorder.LEFT,
                TitledBorder.TOP));

        // Create price table
        String[] priceColumns = {"Parameter", "Value"};
        DefaultTableModel priceModel = new DefaultTableModel(priceColumns, 0) {
            @Override
            public boolean isCellEditable(int row, int column) {
                return false; // Make all cells non-editable
            }
        };
        priceTable = new JTable(priceModel);
        priceTable.setFont(new Font("Monospaced", Font.PLAIN, 12));
        JScrollPane priceScroll = new JScrollPane(priceTable);
        priceScroll.setPreferredSize(new Dimension(300, 150));
        instrumentPanel.add(priceScroll, BorderLayout.CENTER);

        // Create order flow panel
        orderFlowPanel = new JPanel(new BorderLayout());
        orderFlowPanel.setBorder(BorderFactory.createTitledBorder(
                BorderFactory.createEtchedBorder(),
                "Order Flow",
                TitledBorder.LEFT,
                TitledBorder.TOP));

        // Create order flow table
        String[] orderFlowColumns = {"Time", "Type", "Price", "Size", "Side"};
        DefaultTableModel orderFlowModel = new DefaultTableModel(orderFlowColumns, 0) {
            @Override
            public boolean isCellEditable(int row, int column) {
                return false; // Make all cells non-editable
            }
        };
        orderFlowTable = new JTable(orderFlowModel);
        orderFlowTable.setFont(new Font("Monospaced", Font.PLAIN, 12));
        JScrollPane orderFlowScroll = new JScrollPane(orderFlowTable);
        orderFlowScroll.setPreferredSize(new Dimension(500, 200));
        orderFlowPanel.add(orderFlowScroll, BorderLayout.CENTER);

        // Create alerts panel
        alertsPanel = new JPanel(new BorderLayout());
        alertsPanel.setBorder(BorderFactory.createTitledBorder(
                BorderFactory.createEtchedBorder(),
                "Alerts & Patterns",
                TitledBorder.LEFT,
                TitledBorder.TOP));

        // Create alerts text area
        alertsTextArea = new JTextArea();
        alertsTextArea.setEditable(false);
        alertsTextArea.setFont(new Font("Monospaced", Font.PLAIN, 12));
        alertsTextArea.setBackground(new Color(255, 240, 240));
        JScrollPane alertsScroll = new JScrollPane(alertsTextArea);
        alertsScroll.setPreferredSize(new Dimension(400, 150));
        alertsPanel.add(alertsScroll, BorderLayout.CENTER);

        // Create statistics panel
        statsPanel = new JPanel(new BorderLayout());
        statsPanel.setBorder(BorderFactory.createTitledBorder(
                BorderFactory.createEtchedBorder(),
                "Market Statistics",
                TitledBorder.LEFT,
                TitledBorder.TOP));

        // Create statistics table
        String[] statsColumns = {"Metric", "Value"};
        DefaultTableModel statsModel = new DefaultTableModel(statsColumns, 0) {
            @Override
            public boolean isCellEditable(int row, int column) {
                return false; // Make all cells non-editable
            }
        };
        statsTable = new JTable(statsModel);
        statsTable.setFont(new Font("Monospaced", Font.PLAIN, 12));
        JScrollPane statsScroll = new JScrollPane(statsTable);
        statsScroll.setPreferredSize(new Dimension(300, 200));
        statsPanel.add(statsScroll, BorderLayout.CENTER);

        // Create panels grid
        JPanel upperPanel = new JPanel(new GridLayout(1, 2, 5, 5));
        upperPanel.add(instrumentPanel);
        upperPanel.add(statsPanel);

        JPanel lowerPanel = new JPanel(new GridLayout(1, 2, 5, 5));
        lowerPanel.add(orderFlowPanel);
        lowerPanel.add(alertsPanel);

        // Assemble main dashboard
        mainDashboard.add(statusPanel, BorderLayout.NORTH);
        mainDashboard.add(upperPanel, BorderLayout.CENTER);
        mainDashboard.add(lowerPanel, BorderLayout.SOUTH);

        // Initial UI update
        updateAllPanels();

        return new StrategyPanel[] { mainDashboard };
    }

    private JPanel createStatusPanel() {
        JPanel panel = new JPanel(new BorderLayout(5, 5));
        panel.setBorder(BorderFactory.createEmptyBorder(5, 5, 5, 5));

        // Status label
        statusLabel = new JLabel("Initializing MBO Dashboard...");
        statusLabel.setFont(new Font("SansSerif", Font.BOLD, 12));

        // Progress bar
        progressBar = new JProgressBar(0, 100);
        progressBar.setIndeterminate(true);
        progressBar.setPreferredSize(new Dimension(200, 20));

        panel.add(statusLabel, BorderLayout.CENTER);
        panel.add(progressBar, BorderLayout.EAST);

        return panel;
    }

    private void initializeDatabase() {
        try {
            // Load SQLite JDBC driver
            Class.forName("org.sqlite.JDBC");

            // Create connection
            dbConnection = DriverManager.getConnection("jdbc:sqlite:" + DB_PATH);

            // Create new table for dashboard statistics if it doesn't exist
            try (Statement stmt = dbConnection.createStatement()) {
                stmt.execute("CREATE TABLE IF NOT EXISTS dashboard_stats (" +
                        "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                        "timestamp TEXT NOT NULL," +
                        "symbol TEXT NOT NULL," +
                        "metric TEXT NOT NULL," +
                        "value REAL NOT NULL," +
                        "window TEXT" +
                        ")");

                // Create index
                stmt.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_stats_symbol ON dashboard_stats (symbol)");
                stmt.execute("CREATE INDEX IF NOT EXISTS idx_dashboard_stats_metric ON dashboard_stats (metric)");
            }

            logDebug("Connected to database: " + DB_PATH);
        } catch (ClassNotFoundException | SQLException e) {
            logDebug("Error initializing database", e);
        }
    }

    private void startBackgroundTasks() {
        // Fast refresh tasks (1 second)
        scheduler.scheduleAtFixedRate(this::updatePriceData, 0, FAST_REFRESH_RATE, TimeUnit.MILLISECONDS);
        scheduler.scheduleAtFixedRate(this::updateOrderFlow, 0, FAST_REFRESH_RATE, TimeUnit.MILLISECONDS);

        // Medium refresh tasks (5 seconds)
        scheduler.scheduleAtFixedRate(this::updateAlerts, 0, MED_REFRESH_RATE, TimeUnit.MILLISECONDS);
        scheduler.scheduleAtFixedRate(this::updateStatistics, 0, MED_REFRESH_RATE, TimeUnit.MILLISECONDS);

        // Slow refresh tasks (15 seconds)
        scheduler.scheduleAtFixedRate(this::updateDatabaseStats, 0, SLOW_REFRESH_RATE, TimeUnit.MILLISECONDS);

        // UI refresh
        scheduler.scheduleAtFixedRate(this::updateAllPanels, 1, FAST_REFRESH_RATE, TimeUnit.MILLISECONDS);

        logDebug("Background tasks started");
    }

    private void updatePriceData() {
        try {
            // Read live prices from cache file
            if (Files.exists(Path.of(PRICE_CACHE_FILE))) {
                try (FileReader reader = new FileReader(PRICE_CACHE_FILE)) {
                    StringBuilder content = new StringBuilder();
                    char[] buffer = new char[1024];
                    int bytesRead;
                    while ((bytesRead = reader.read(buffer)) != -1) {
                        content.append(buffer, 0, bytesRead);
                    }

                    JSONObject json = new JSONObject(content.toString());

                    // Process each instrument's price data
                    for (String key : json.keySet()) {
                        JSONObject priceData = json.getJSONObject(key);

                        Map<String, Object> price = new HashMap<>();
                        price.put("symbol", key);
                        price.put("mid", priceData.optDouble("mid", 0.0));
                        price.put("bid", priceData.optDouble("bid", 0.0));
                        price.put("ask", priceData.optDouble("ask", 0.0));
                        price.put("spread", priceData.optDouble("spread", 0.0));
                        price.put("timestamp", priceData.optString("timestamp", ""));
                        price.put("source", priceData.optString("source", ""));

                        livePrices.put(key, price);
                    }
                }
            }
        } catch (IOException e) {
            logDebug("Error reading price cache file", e);
        } catch (Exception e) {
            logDebug("Error updating price data", e);
        }
    }

    private void updateOrderFlow() {
        try {
            String alias = currentAlias;
            if (alias == null) return;

            String symbol = normalizeSymbol(alias);

            // Query recent trades from database
            ZonedDateTime cutoff = ZonedDateTime.now().minusMinutes(5);
            String cutoffStr = cutoff.format(isoFormatter);

            String sql = "SELECT * FROM trades WHERE symbol = ? AND timestamp > ? ORDER BY timestamp DESC LIMIT 100";

            try (PreparedStatement pstmt = dbConnection.prepareStatement(sql)) {
                pstmt.setString(1, symbol);
                pstmt.setString(2, cutoffStr);

                ResultSet rs = pstmt.executeQuery();

                List<Map<String, Object>> trades = new ArrayList<>();

                while (rs.next()) {
                    Map<String, Object> trade = new HashMap<>();
                    trade.put("type", "Trade");
                    trade.put("timestamp", rs.getString("timestamp"));
                    trade.put("price", rs.getDouble("price"));
                    trade.put("size", rs.getInt("size"));
                    trade.put("isBid", rs.getInt("is_bid") == 1);
                    trade.put("side", rs.getInt("is_bid") == 1 ? "Buy" : "Sell");
                    trade.put("aggressor", rs.getString("aggressor"));

                    trades.add(trade);
                }

                // Query recent MBO updates
                sql = "SELECT * FROM mbo_updates WHERE symbol = ? AND timestamp > ? ORDER BY timestamp DESC LIMIT 100";

                try (PreparedStatement pstmt2 = dbConnection.prepareStatement(sql)) {
                    pstmt2.setString(1, symbol);
                    pstmt2.setString(2, cutoffStr);

                    rs = pstmt2.executeQuery();

                    while (rs.next()) {
                        Map<String, Object> mbo = new HashMap<>();
                        mbo.put("type", "MBO");
                        mbo.put("timestamp", rs.getString("timestamp"));
                        mbo.put("price", rs.getDouble("price"));
                        mbo.put("size", rs.getInt("size"));
                        mbo.put("isBid", rs.getInt("is_bid") == 1);
                        mbo.put("side", rs.getInt("is_bid") == 1 ? "Bid" : "Ask");
                        mbo.put("orderId", rs.getString("order_id"));

                        trades.add(mbo);
                    }
                }

                // Sort by timestamp (most recent first)
                trades.sort((t1, t2) -> {
                    String ts1 = (String) t1.get("timestamp");
                    String ts2 = (String) t2.get("timestamp");
                    return ts2.compareTo(ts1);
                });

                // Store order flow
                orderFlow.put(alias, trades);
            }
        } catch (SQLException e) {
            logDebug("Error querying database for order flow", e);
        } catch (Exception e) {
            logDebug("Error updating order flow", e);
        }
    }

    private void updateAlerts() {
        try {
            // Read alerts from analytics file
            if (Files.exists(Path.of(ANALYTICS_FILE))) {
                try (FileReader reader = new FileReader(ANALYTICS_FILE)) {
                    StringBuilder content = new StringBuilder();
                    char[] buffer = new char[1024];
                    int bytesRead;
                    while ((bytesRead = reader.read(buffer)) != -1) {
                        content.append(buffer, 0, bytesRead);
                    }

                    JSONObject json = new JSONObject(content.toString());

                    if (json.has("alerts")) {
                        JSONArray alertsArray = json.getJSONArray("alerts");

                        // Clear previous alerts
                        recentAlerts.clear();

                        for (int i = 0; i < alertsArray.length(); i++) {
                            JSONObject alertJson = alertsArray.getJSONObject(i);

                            Map<String, Object> alert = new HashMap<>();
                            alert.put("id", alertJson.optString("id", ""));
                            alert.put("type", alertJson.optString("type", ""));
                            alert.put("message", alertJson.optString("message", ""));
                            alert.put("timestamp", alertJson.optString("timestamp", ""));
                            alert.put("priority", alertJson.optString("priority", "medium"));

                            recentAlerts.add(alert);
                        }
                    }

                    // Get analytics
                    if (json.has("analytics")) {
                        JSONObject analyticsJson = json.getJSONObject("analytics");
                        Map<String, Double> stats = new HashMap<>();

                        for (String key : analyticsJson.keySet()) {
                            stats.put(key, analyticsJson.getDouble(key));
                        }

                        String instrument = json.optString("instrument", "");
                        if (!instrument.isEmpty()) {
                            analytics.put(instrument, stats);
                        }

                        String symbol = json.optString("symbol", "");
                        if (!symbol.isEmpty()) {
                            analytics.put(symbol, stats);
                        }
                    }
                }
            }
        } catch (IOException e) {
            logDebug("Error reading analytics file", e);
        } catch (Exception e) {
            logDebug("Error updating alerts", e);
        }
    }

    private void updateStatistics() {
        try {
            String alias = currentAlias;
            if (alias == null) return;

            String symbol = normalizeSymbol(alias);

            // Get volume statistics from database
            Map<String, Double> volumeStats = getVolumeStats(symbol);

            // Get tick statistics
            Map<String, Double> tickStats = getTickStats(symbol);

            // Merge statistics
            Map<String, Double> allStats = new HashMap<>();
            allStats.putAll(volumeStats);
            allStats.putAll(tickStats);

            // Add analytics data
            Map<String, Double> analyticsData = analytics.get(alias);
            if (analyticsData != null) {
                allStats.putAll(analyticsData);
            }

            analyticsData = analytics.get(symbol);
            if (analyticsData != null) {
                allStats.putAll(analyticsData);
            }

            // Update stats in database
            updateDatabaseStats(symbol, allStats);

        } catch (Exception e) {
            logDebug("Error updating statistics", e);
        }
    }

    private Map<String, Double> getVolumeStats(String symbol) {
        Map<String, Double> stats = new HashMap<>();

        try {
            // Define time windows (in minutes)
            int[] windows = {1, 5, 15, 60};
            String[] windowNames = {"1min", "5min", "15min", "60min"};

            for (int i = 0; i < windows.length; i++) {
                int minutes = windows[i];
                String windowName = windowNames[i];

                ZonedDateTime cutoff = ZonedDateTime.now().minusMinutes(minutes);
                String cutoffStr = cutoff.format(isoFormatter);

                // Get total volume
                String sql = "SELECT SUM(size) AS total_volume FROM trades WHERE symbol = ? AND timestamp > ?";

                try (PreparedStatement pstmt = dbConnection.prepareStatement(sql)) {
                    pstmt.setString(1, symbol);
                    pstmt.setString(2, cutoffStr);

                    ResultSet rs = pstmt.executeQuery();

                    if (rs.next()) {
                        double volume = rs.getDouble("total_volume");
                        stats.put(windowName + "_volume", volume);
                    }
                }

                // Get buy/sell volumes
                sql = "SELECT SUM(CASE WHEN is_bid = 1 THEN size ELSE 0 END) AS buy_volume, " +
                      "SUM(CASE WHEN is_bid = 0 THEN size ELSE 0 END) AS sell_volume " +
                      "FROM trades WHERE symbol = ? AND timestamp > ?";

                try (PreparedStatement pstmt = dbConnection.prepareStatement(sql)) {
                    pstmt.setString(1, symbol);
                    pstmt.setString(2, cutoffStr);

                    ResultSet rs = pstmt.executeQuery();

                    if (rs.next()) {
                        double buyVolume = rs.getDouble("buy_volume");
                        double sellVolume = rs.getDouble("sell_volume");
                        double delta = buyVolume - sellVolume;

                        stats.put(windowName + "_buy_volume", buyVolume);
                        stats.put(windowName + "_sell_volume", sellVolume);
                        stats.put(windowName + "_delta", delta);
                    }
                }
            }
        } catch (SQLException e) {
            logDebug("Error getting volume statistics", e);
        }

        return stats;
    }

    private Map<String, Double> getTickStats(String symbol) {
        Map<String, Double> stats = new HashMap<>();

        try {
            // Define time windows (in minutes)
            int[] windows = {1, 5, 15, 60};
            String[] windowNames = {"1min", "5min", "15min", "60min"};

            for (int i = 0; i < windows.length; i++) {
                int minutes = windows[i];
                String windowName = windowNames[i];

                ZonedDateTime cutoff = ZonedDateTime.now().minusMinutes(minutes);
                String cutoffStr = cutoff.format(isoFormatter);

                // Get price range
                String sql = "SELECT MIN(price) AS min_price, MAX(price) AS max_price FROM trades " +
                             "WHERE symbol = ? AND timestamp > ?";

                try (PreparedStatement pstmt = dbConnection.prepareStatement(sql)) {
                    pstmt.setString(1, symbol);
                    pstmt.setString(2, cutoffStr);

                    ResultSet rs = pstmt.executeQuery();

                    if (rs.next()) {
                        double minPrice = rs.getDouble("min_price");
                        double maxPrice = rs.getDouble("max_price");
                        double range = maxPrice - minPrice;

                        stats.put(windowName + "_min_price", minPrice);
                        stats.put(windowName + "_max_price", maxPrice);
                        stats.put(windowName + "_range", range);
                    }
                }

                // Get trade count
                sql = "SELECT COUNT(*) AS trade_count FROM trades WHERE symbol = ? AND timestamp > ?";

                try (PreparedStatement pstmt = dbConnection.prepareStatement(sql)) {
                    pstmt.setString(1, symbol);
                    pstmt.setString(2, cutoffStr);

                    ResultSet rs = pstmt.executeQuery();

                    if (rs.next()) {
                        double tradeCount = rs.getDouble("trade_count");
                        stats.put(windowName + "_trade_count", tradeCount);
                    }
                }
            }
        } catch (SQLException e) {
            logDebug("Error getting tick statistics", e);
        }

        return stats;
    }

    private void updateDatabaseStats(String symbol, Map<String, Double> stats) {
        try {
            if (dbConnection == null || dbConnection.isClosed()) {
                return;
            }

            String timestamp = ZonedDateTime.now().format(isoFormatter);

            // Insert each statistic into dashboard_stats table
            String sql = "INSERT INTO dashboard_stats (timestamp, symbol, metric, value, window) VALUES (?, ?, ?, ?, ?)";

            for (Map.Entry<String, Double> entry : stats.entrySet()) {
                String metric = entry.getKey();
                Double value = entry.getValue();

                // Skip null or NaN values
                if (value == null || value.isNaN()) {
                    continue;
                }

                // Determine window
                String window = "unknown";
                if (metric.startsWith("1min_")) {
                    window = "1min";
                } else if (metric.startsWith("5min_")) {
                    window = "5min";
                } else if (metric.startsWith("15min_")) {
                    window = "15min";
                } else if (metric.startsWith("60min_")) {
                    window = "60min";
                }

                try (PreparedStatement pstmt = dbConnection.prepareStatement(sql)) {
                    pstmt.setString(1, timestamp);
                    pstmt.setString(2, symbol);
                    pstmt.setString(3, metric);
                    pstmt.setDouble(4, value);
                    pstmt.setString(5, window);

                    pstmt.executeUpdate();
                }
            }
        } catch (SQLException e) {
            logDebug("Error updating database statistics", e);
        }
    }

    private void updateDatabaseStats() {
        try {
            String alias = currentAlias;
            if (alias == null) return;

            String symbol = normalizeSymbol(alias);

            // Clean up old stats
            String sql = "DELETE FROM dashboard_stats WHERE timestamp < ?";

            ZonedDateTime cutoff = ZonedDateTime.now().minusDays(1);
            String cutoffStr = cutoff.format(isoFormatter);

            try (PreparedStatement pstmt = dbConnection.prepareStatement(sql)) {
                pstmt.setString(1, cutoffStr);
                int deleted = pstmt.executeUpdate();

                if (deleted > 0) {
                    logDebug("Cleaned up " + deleted + " old dashboard stats");
                }
            }
        } catch (SQLException e) {
            logDebug("Error cleaning up old stats", e);
        }
    }

    private void updateAllPanels() {
        try {
            SwingUtilities.invokeLater(() -> {
                try {
                    updatePricePanel();
                    updateOrderFlowPanel();
                    updateAlertsPanel();
                    updateStatsPanel();
                    updateStatusPanel();
                } catch (Exception e) {
                    logDebug("Error updating UI panels", e);
                }
            });
        } catch (Exception e) {
            logDebug("Error in updateAllPanels", e);
        }
    }

    private void updatePricePanel() {
        try {
            DefaultTableModel model = (DefaultTableModel) priceTable.getModel();
            model.setRowCount(0);

            String alias = currentAlias;
            if (alias == null) return;

            // Get normalized symbol
            String symbol = normalizeSymbol(alias);

            // Get price data
            Map<String, Object> price = livePrices.get(alias);
            if (price == null) {
                price = livePrices.get(symbol);
            }

            if (price != null) {
                model.addRow(new Object[]{"Symbol", symbol});
                model.addRow(new Object[]{"Bid", price.get("bid")});
                model.addRow(new Object[]{"Ask", price.get("ask")});
                model.addRow(new Object[]{"Mid", price.get("mid")});
                model.addRow(new Object[]{"Spread", price.get("spread")});

                // Format timestamp for display
                String timestamp = (String) price.get("timestamp");
                if (timestamp != null && !timestamp.isEmpty()) {
                    try {
                        ZonedDateTime zdt = ZonedDateTime.parse(timestamp, isoFormatter);
                        String localTime = zdt.withZoneSameInstant(ZoneId.systemDefault())
                                .format(DateTimeFormatter.ofPattern("HH:mm:ss.SSS"));
                        model.addRow(new Object[]{"Updated", localTime});
                    } catch (Exception e) {
                        model.addRow(new Object[]{"Updated", timestamp});
                    }
                }

                model.addRow(new Object[]{"Source", price.get("source")});
            } else {
                model.addRow(new Object[]{"Status", "No price data available"});
            }
        } catch (Exception e) {
            logDebug("Error updating price panel", e);
        }
    }

    private void updateOrderFlowPanel() {
        try {
            DefaultTableModel model = (DefaultTableModel) orderFlowTable.getModel();
            model.setRowCount(0);

            String alias = currentAlias;
            if (alias == null) return;

            // Get order flow data
            List<Map<String, Object>> flows = orderFlow.get(alias);
            if (flows == null || flows.isEmpty()) {
                return;
            }

            // Add rows to table (limited to 50)
            int count = 0;
            for (Map<String, Object> flow : flows) {
                if (count++ >= 50) break;

                String timestamp = (String) flow.get("timestamp");
                String localTime = "";

                try {
                    ZonedDateTime zdt = ZonedDateTime.parse(timestamp, isoFormatter);
                    localTime = zdt.withZoneSameInstant(ZoneId.systemDefault())
                            .format(DateTimeFormatter.ofPattern("HH:mm:ss"));
                } catch (Exception e) {
                    localTime = timestamp;
                }

                String type = (String) flow.get("type");
                double price = (double) flow.get("price");
                int size = (int) flow.get("size");
                String side = (String) flow.get("side");

                model.addRow(new Object[]{localTime, type, price, size, side});
            }
        } catch (Exception e) {
            logDebug("Error updating order flow panel", e);
        }
    }

    private void updateAlertsPanel() {
        try {
            StringBuilder sb = new StringBuilder();

            if (recentAlerts.isEmpty()) {
                sb.append("No recent alerts detected...");
            } else {
                // Sort alerts by timestamp (most recent first)
                recentAlerts.sort((a1, a2) -> {
                    String ts1 = (String) a1.get("timestamp");
                    String ts2 = (String) a2.get("timestamp");
                    return ts2.compareTo(ts1);
                });

                // Add header
                sb.append("Recent Alerts and Patterns:\n\n");

                // Add alerts (limited to 10)
                int count = 0;
                for (Map<String, Object> alert : recentAlerts) {
                    if (count++ >= 10) break;

                    String timestamp = (String) alert.get("timestamp");
                    String localTime = "";

                    try {
                        ZonedDateTime zdt = ZonedDateTime.parse(timestamp, isoFormatter);
                        localTime = zdt.withZoneSameInstant(ZoneId.systemDefault())
                                .format(DateTimeFormatter.ofPattern("HH:mm:ss"));
                    } catch (Exception e) {
                        localTime = timestamp;
                    }

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
            }

            alertsTextArea.setText(sb.toString());
            alertsTextArea.setCaretPosition(0);

        } catch (Exception e) {
            logDebug("Error updating alerts panel", e);
        }
    }

    private void updateStatsPanel() {
        try {
            DefaultTableModel model = (DefaultTableModel) statsTable.getModel();
            model.setRowCount(0);

            String alias = currentAlias;
            if (alias == null) return;

            String symbol = normalizeSymbol(alias);

            // Try to get analytics data
            Map<String, Double> stats = analytics.get(alias);
            if (stats == null) {
                stats = analytics.get(symbol);
            }

            if (stats != null && !stats.isEmpty()) {
                // Add volume metrics
                model.addRow(new Object[]{"Total Volume", formatValue(stats.get("totalVolume"))});
                model.addRow(new Object[]{"Buy Volume", formatValue(stats.get("buyVolume"))});
                model.addRow(new Object[]{"Sell Volume", formatValue(stats.get("sellVolume"))});
                model.addRow(new Object[]{"Delta", formatValue(stats.get("delta"))});
                model.addRow(new Object[]{"Delta %", formatPercent(stats.get("deltaRatio"))});

                // Add price metrics
                model.addRow(new Object[]{"VWAP", formatValue(stats.get("vwap"))});
                model.addRow(new Object[]{"Range", formatValue(stats.get("range"))});
                model.addRow(new Object[]{"Trade Count", formatValue(stats.get("tradeCount"))});

                // Add window stats
                model.addRow(new Object[]{"1min Volume", formatValue(stats.get("shortWindowVolume"))});
                model.addRow(new Object[]{"5min Volume", formatValue(stats.get("mediumWindowVolume"))});
                model.addRow(new Object[]{"1min Delta", formatValue(stats.get("shortWindowDelta"))});
                model.addRow(new Object[]{"1min Price Chg", formatValue(stats.get("shortWindowPriceChange"))});
                model.addRow(new Object[]{"5min Price Chg", formatValue(stats.get("mediumWindowPriceChange"))});
            } else {
                model.addRow(new Object[]{"Status", "No analytics data available"});
            }
        } catch (Exception e) {
            logDebug("Error updating stats panel", e);
        }
    }

    private void updateStatusPanel() {
        try {
            String alias = currentAlias;
            if (alias == null) {
                statusLabel.setText("No instrument selected");
                return;
            }

            String symbol = normalizeSymbol(alias);

            // Get number of trades in last hour
            int tradeCount = 0;
            int mboUpdateCount = 0;

            ZonedDateTime cutoff = ZonedDateTime.now().minusHours(1);
            String cutoffStr = cutoff.format(isoFormatter);

            String sql = "SELECT COUNT(*) AS count FROM trades WHERE symbol = ? AND timestamp > ?";

            try (PreparedStatement pstmt = dbConnection.prepareStatement(sql)) {
                pstmt.setString(1, symbol);
                pstmt.setString(2, cutoffStr);

                ResultSet rs = pstmt.executeQuery();

                if (rs.next()) {
                    tradeCount = rs.getInt("count");
                }
            }

            sql = "SELECT COUNT(*) AS count FROM mbo_updates WHERE symbol = ? AND timestamp > ?";

            try (PreparedStatement pstmt = dbConnection.prepareStatement(sql)) {
                pstmt.setString(1, symbol);
                pstmt.setString(2, cutoffStr);

                ResultSet rs = pstmt.executeQuery();

                if (rs.next()) {
                    mboUpdateCount = rs.getInt("count");
                }
            }

            // Get alerts count
            int alertCount = recentAlerts.size();

            // Update status
            StringBuilder sb = new StringBuilder();
            sb.append("Monitoring: ").append(symbol);
            sb.append(" | 1h Trades: ").append(tradeCount);
            sb.append(" | 1h MBO Updates: ").append(mboUpdateCount);
            sb.append(" | Alerts: ").append(alertCount);

            statusLabel.setText(sb.toString());
            progressBar.setIndeterminate(false);
            progressBar.setValue(100);

        } catch (SQLException e) {
            logDebug("Error querying database for status update", e);
            statusLabel.setText("Error querying database: " + e.getMessage());
        } catch (Exception e) {
            logDebug("Error updating status panel", e);
            statusLabel.setText("Error updating status: " + e.getMessage());
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

    private String formatValue(Double value) {
        if (value == null) return "N/A";
        if (value.isNaN()) return "N/A";

        if (Math.abs(value) < 0.001) {
            return "%.6f".formatted(value);
        } else if (Math.abs(value) < 1) {
            return "%.4f".formatted(value);
        } else if (Math.abs(value) < 10) {
            return "%.2f".formatted(value);
        } else {
            return "%.0f".formatted(value);
        }
    }

    private String formatPercent(Double value) {
        if (value == null) return "N/A";
        if (value.isNaN()) return "N/A";

        return "%.1f%%".formatted(value * 100);
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
                Files.createDirectories(Path.of(DEBUG_FILE).getParent());
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
}
