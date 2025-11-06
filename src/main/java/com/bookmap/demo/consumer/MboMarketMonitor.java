package velox.api.layer1.simplified.mbo;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.sql.Statement;
import java.text.SimpleDateFormat;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;
import java.util.TimeZone;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

// Using manual JSON generation since external JSON libraries aren't available

import velox.api.layer1.annotations.Layer1ApiVersion;
import velox.api.layer1.annotations.Layer1ApiVersionValue;
import velox.api.layer1.annotations.Layer1SimpleAttachable;
import velox.api.layer1.annotations.Layer1StrategyName;
import velox.api.layer1.common.Log;
import velox.api.layer1.data.InstrumentInfo;
import velox.api.layer1.data.TradeInfo;
import velox.api.layer1.simplified.Api;
import velox.api.layer1.simplified.CustomModule;
import velox.api.layer1.simplified.CustomSettingsPanelProvider;
import velox.api.layer1.simplified.DepthDataListener;
import velox.api.layer1.simplified.InitialState;
import velox.api.layer1.simplified.TradeDataListener;
import velox.api.layer1.simplified.Api;
import velox.api.layer1.simplified.CustomModule;
import velox.api.layer1.simplified.CustomSettingsPanelProvider;
import velox.api.layer1.simplified.InitialState;
import velox.gui.StrategyPanel;

/**
 * Enhanced Market Monitor with MBO Support for Bookmap
 * Java implementation of MBO_Automated_v3.py
 *
 * Monitors order book updates, trades, and MBO data with real-time price tracking
 */
@Layer1SimpleAttachable
@Layer1StrategyName("MBO Market Monitor")
@Layer1ApiVersion(Layer1ApiVersionValue.VERSION2)
public class MboMarketMonitor implements CustomModule, CustomSettingsPanelProvider,
    DepthDataListener, TradeDataListener {

    // Configuration
    private static final String DB_PATH = "F:/TradingAgent/enhanced_market_monitor_mbo.db";
    private static final String DEBUG_FILE = "F:/TradingAgent/enhanced_monitor_mbo_debug.log";
    private static final String PRICE_CACHE_FILE = "F:/TradingAgent/live_prices.json";

    // Trading Window Configuration (EST/EDT timezone)
    private static final ZoneId EST = ZoneId.of("America/New_York");

    // CBDR Window 1: PM Session / Asian Open (4:00 PM - 8:00 PM EST)
    private static final int CBDR_PM_START_HOUR = 16;
    private static final int CBDR_PM_START_MINUTE = 0;
    private static final int CBDR_PM_END_HOUR = 20;
    private static final int CBDR_PM_END_MINUTE = 0;

    // CBDR Window 2: London Kill Zone (2:00 AM - 5:00 AM EST)
    private static final int CBDR_LONDON_START_HOUR = 2;
    private static final int CBDR_LONDON_START_MINUTE = 0;
    private static final int CBDR_LONDON_END_HOUR = 5;
    private static final int CBDR_LONDON_END_MINUTE = 0;

    // Pre-NY Open Window (7:30 AM - 9:30 AM EST)
    private static final int PRE_NY_START_HOUR = 7;
    private static final int PRE_NY_START_MINUTE = 30;
    private static final int PRE_NY_END_HOUR = 9;
    private static final int PRE_NY_END_MINUTE = 30;

    // Global state
    private final Map<String, Map<Double, Integer>> aliasToOrderBook = new ConcurrentHashMap<>();
    private final Map<String, Map<String, Object>> instrumentParams = new ConcurrentHashMap<>();
    private final Map<String, Map<String, Map<String, Object>>> mboOrderBooks = new ConcurrentHashMap<>();
    private final AtomicInteger mboUpdateSequence = new AtomicInteger(0);

    // IN-MEMORY PRICE CACHE
    private final Map<String, Map<String, Object>> livePrices = new ConcurrentHashMap<>();
    private final AtomicInteger priceUpdateCounter = new AtomicInteger(0);

    // Event counters for debugging
    private final Map<String, AtomicInteger> eventCounts = new ConcurrentHashMap<>();
    private final Map<String, AtomicInteger> filteredCounts = new ConcurrentHashMap<>();

    // Database connection
    private Connection dbConnection;

    // API reference
    private Api api;
    private String currentAlias; // Added to store the current instrument alias

    // Date formatters
    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
    private final DateTimeFormatter isoFormatter = DateTimeFormatter.ISO_OFFSET_DATE_TIME;

    public MboMarketMonitor() {
        // Initialize counters
        eventCounts.put("depth", new AtomicInteger(0));
        eventCounts.put("trades", new AtomicInteger(0));
        eventCounts.put("mbo", new AtomicInteger(0));

        filteredCounts.put("depth", new AtomicInteger(0));
        filteredCounts.put("trades", new AtomicInteger(0));
        filteredCounts.put("mbo", new AtomicInteger(0));

        // Set timezone for date formatter
        dateFormat.setTimeZone(TimeZone.getTimeZone("UTC"));

        // Initialize database
        initializeDatabase();
    }

    @Override
    public void initialize(String alias, InstrumentInfo info, Api api, InitialState initialState) {
        this.api = api;
        this.currentAlias = alias;  // Store the current instrument alias

        // Initialize empty order book for this instrument
        aliasToOrderBook.put(alias, new ConcurrentHashMap<>());

        // Initialize empty MBO order book for this instrument
        mboOrderBooks.put(alias, new ConcurrentHashMap<>());

        // Store instrument parameters
        Map<String, Object> params = new HashMap<>();
        params.put("alias", alias);
        params.put("pips", info.pips);
        params.put("pointsPerPip", 1.0 / info.pips);
        params.put("symbol", normalizeSymbol(alias));
        instrumentParams.put(alias, params);

        logDebug("Initialized MBO Market Monitor for: " + alias);
        logDebug("Instrument parameters: " + params);
    }

    @Override
    public void stop() {
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
        // No custom settings panel for now
        return new StrategyPanel[0];
    }

    @Override
    public void onDepth(boolean isBid, int price, int size) {
        try {
            // Convert price from int to double (Bookmap uses integer prices internally)
            double doublePrice = price / (double) 100;

            // Use the stored currentAlias instead of api.getInstrument() which doesn't exist
            String alias = currentAlias;
            Map<Double, Integer> orderBook = aliasToOrderBook.get(alias);

            // Update order book
            if (orderBook != null) {
                if (size > 0) {
                    orderBook.put(doublePrice, size);
                } else {
                    orderBook.remove(doublePrice);
                }
            }

            // Update counters
            eventCounts.get("depth").incrementAndGet();

            // Check if within trading window
            Map.Entry<Boolean, String> tradingWindow = isWithinTradingWindow();
            if (tradingWindow.getKey()) {
                // Within trading window, record depth update
                recordDepthUpdate(alias, isBid, doublePrice, size, tradingWindow.getValue());
                filteredCounts.get("depth").incrementAndGet();
            }

            // Update price cache if bid and ask are available
            updatePriceFromOrderBook(alias, orderBook);

        } catch (Exception e) {
            logDebug("Error in onDepth", e);
        }
    }

    @Override
    public void onTrade(double price, int size, TradeInfo tradeInfo) {
        try {
            // Use the stored currentAlias instead of api.getInstrument()
            String alias = currentAlias;
            // Checking if it's a buy using available TradeInfo API
            // In the simplified API, we can determine buy/sell differently
            boolean isBid = true; // Default to buy
            try {
                // Different ways to determine trade direction based on what's available in the API
                if (tradeInfo != null) {
                    // Use reflection to try to access fields that may be available
                    try {
                        java.lang.reflect.Field field = TradeInfo.class.getDeclaredField("aggressor");
                        field.setAccessible(true);
                        int aggressor = (int)field.get(tradeInfo);
                        // Typically AGGRESSOR_BUY = 1
                        isBid = (aggressor == 1);
                    } catch (Exception e) {
                        // Field not available, try other approaches
                        // Inferring from price movement or other trade info
                        isBid = (size > 0); // Simple heuristic - positive size often means buy
                    }
                }
            } catch (Exception e) {
                logDebug("Error determining trade direction", e);
            }

            // Update counters
            eventCounts.get("trades").incrementAndGet();

            // Check if within trading window
            Map.Entry<Boolean, String> tradingWindow = isWithinTradingWindow();
            if (tradingWindow.getKey()) {
                // Within trading window, record trade
                recordTrade(alias, price, size, isBid, tradeInfo, tradingWindow.getValue());
                filteredCounts.get("trades").incrementAndGet();
            }
        } catch (Exception e) {
            logDebug("Error in onTrade", e);
        }
    }

    @Override
    public void onMboDepth(String orderId, boolean isBid, int price, int size) {
        try {
            // Convert price from int to double
            double doublePrice = price / (double) 100;

            // Use the stored currentAlias instead of api.getInstrument()
            String alias = currentAlias;

            // Update counters
            eventCounts.get("mbo").incrementAndGet();

            // Get side-specific order book
            String side = isBid ? "bids" : "asks";
            Map<String, Map<String, Object>> sideOrderBook = mboOrderBooks.computeIfAbsent(alias, k -> new ConcurrentHashMap<>())
                    .computeIfAbsent(side, k -> new ConcurrentHashMap<>());

            // Update or remove order
            if (size > 0) {
                // Add or update order
                Map<String, Object> order = new HashMap<>();
                order.put("orderId", orderId);
                order.put("price", doublePrice);
                order.put("size", size);
                order.put("isBid", isBid);
                order.put("timestamp", ZonedDateTime.now(ZoneId.of("UTC")).format(isoFormatter));

                sideOrderBook.put(orderId, order);
            } else {
                // Remove order
                sideOrderBook.remove(orderId);
            }

            // Check if within trading window
            Map.Entry<Boolean, String> tradingWindow = isWithinTradingWindow();
            if (tradingWindow.getKey()) {
                // Within trading window, record MBO update
                recordMboUpdate(alias, orderId, isBid, doublePrice, size, tradingWindow.getValue());
                filteredCounts.get("mbo").incrementAndGet();
            }
        } catch (Exception e) {
            logDebug("Error in onMboDepth", e);
        }
    }

    private void initializeDatabase() {
        try {
            // Ensure directory exists
            File dbFile = new File(DB_PATH);
            dbFile.getParentFile().mkdirs();

            // Load SQLite JDBC driver
            Class.forName("org.sqlite.JDBC");

            // Create connection
            dbConnection = DriverManager.getConnection("jdbc:sqlite:" + DB_PATH);

            // Create tables if they don't exist
            try (Statement stmt = dbConnection.createStatement()) {
                // Depth updates table
                stmt.execute("CREATE TABLE IF NOT EXISTS depth_updates (" +
                        "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                        "timestamp TEXT NOT NULL," +
                        "symbol TEXT NOT NULL," +
                        "price REAL NOT NULL," +
                        "size INTEGER NOT NULL," +
                        "is_bid INTEGER NOT NULL," +
                        "trading_window TEXT" +
                        ")");

                // Trades table
                stmt.execute("CREATE TABLE IF NOT EXISTS trades (" +
                        "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                        "timestamp TEXT NOT NULL," +
                        "symbol TEXT NOT NULL," +
                        "price REAL NOT NULL," +
                        "size INTEGER NOT NULL," +
                        "is_bid INTEGER NOT NULL," +
                        "aggressor TEXT," +
                        "trade_id TEXT," +
                        "trading_window TEXT" +
                        ")");

                // MBO updates table
                stmt.execute("CREATE TABLE IF NOT EXISTS mbo_updates (" +
                        "id INTEGER PRIMARY KEY AUTOINCREMENT," +
                        "timestamp TEXT NOT NULL," +
                        "symbol TEXT NOT NULL," +
                        "order_id TEXT NOT NULL," +
                        "price REAL NOT NULL," +
                        "size INTEGER NOT NULL," +
                        "is_bid INTEGER NOT NULL," +
                        "sequence INTEGER NOT NULL," +
                        "trading_window TEXT" +
                        ")");

                // Create indexes
                stmt.execute("CREATE INDEX IF NOT EXISTS idx_depth_timestamp ON depth_updates (timestamp)");
                stmt.execute("CREATE INDEX IF NOT EXISTS idx_depth_symbol ON depth_updates (symbol)");
                stmt.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades (timestamp)");
                stmt.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades (symbol)");
                stmt.execute("CREATE INDEX IF NOT EXISTS idx_mbo_timestamp ON mbo_updates (timestamp)");
                stmt.execute("CREATE INDEX IF NOT EXISTS idx_mbo_symbol ON mbo_updates (symbol)");
                stmt.execute("CREATE INDEX IF NOT EXISTS idx_mbo_order_id ON mbo_updates (order_id)");
            }

            logDebug("Database initialized: " + DB_PATH);
        } catch (ClassNotFoundException | SQLException e) {
            logDebug("Error initializing database", e);
        }
    }

    private void recordDepthUpdate(String alias, boolean isBid, double price, int size, String tradingWindow) {
        try {
            if (dbConnection == null || dbConnection.isClosed()) {
                return;
            }

            String normalized = normalizeSymbol(alias);
            String timestamp = ZonedDateTime.now(ZoneId.of("UTC")).format(isoFormatter);

            String sql = "INSERT INTO depth_updates (timestamp, symbol, price, size, is_bid, trading_window) " +
                    "VALUES (?, ?, ?, ?, ?, ?)";

            try (PreparedStatement pstmt = dbConnection.prepareStatement(sql)) {
                pstmt.setString(1, timestamp);
                pstmt.setString(2, normalized);
                pstmt.setDouble(3, price);
                pstmt.setInt(4, size);
                pstmt.setInt(5, isBid ? 1 : 0);
                pstmt.setString(6, tradingWindow);

                pstmt.executeUpdate();
            }
        } catch (SQLException e) {
            logDebug("Error recording depth update", e);
        }
    }

    private void recordTrade(String alias, double price, int size, boolean isBid, TradeInfo tradeInfo, String tradingWindow) {
        try {
            if (dbConnection == null || dbConnection.isClosed()) {
                return;
            }

            String normalized = normalizeSymbol(alias);
            String timestamp = ZonedDateTime.now(ZoneId.of("UTC")).format(isoFormatter);
            String aggressor = isBid ? "buyer" : "seller";
            // Using timestamp + price as ID since TradeInfo doesn't have an accessible id field
            String tradeId = System.currentTimeMillis() + "-" + price;

            String sql = "INSERT INTO trades (timestamp, symbol, price, size, is_bid, aggressor, trade_id, trading_window) " +
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)";

            try (PreparedStatement pstmt = dbConnection.prepareStatement(sql)) {
                pstmt.setString(1, timestamp);
                pstmt.setString(2, normalized);
                pstmt.setDouble(3, price);
                pstmt.setInt(4, size);
                pstmt.setInt(5, isBid ? 1 : 0);
                pstmt.setString(6, aggressor);
                pstmt.setString(7, tradeId);
                pstmt.setString(8, tradingWindow);

                pstmt.executeUpdate();
            }
        } catch (SQLException e) {
            logDebug("Error recording trade", e);
        }
    }

    private void recordMboUpdate(String alias, String orderId, boolean isBid, double price, int size, String tradingWindow) {
        try {
            if (dbConnection == null || dbConnection.isClosed()) {
                return;
            }

            String normalized = normalizeSymbol(alias);
            String timestamp = ZonedDateTime.now(ZoneId.of("UTC")).format(isoFormatter);
            int sequence = mboUpdateSequence.incrementAndGet();

            String sql = "INSERT INTO mbo_updates (timestamp, symbol, order_id, price, size, is_bid, sequence, trading_window) " +
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)";

            try (PreparedStatement pstmt = dbConnection.prepareStatement(sql)) {
                pstmt.setString(1, timestamp);
                pstmt.setString(2, normalized);
                pstmt.setString(3, orderId);
                pstmt.setDouble(4, price);
                pstmt.setInt(5, size);
                pstmt.setInt(6, isBid ? 1 : 0);
                pstmt.setInt(7, sequence);
                pstmt.setString(8, tradingWindow);

                pstmt.executeUpdate();
            }
        } catch (SQLException e) {
            logDebug("Error recording MBO update", e);
        }
    }

    private Map.Entry<Boolean, String> isWithinTradingWindow() {
        try {
            LocalDateTime nowUtc = LocalDateTime.now(ZoneId.of("UTC"));
            LocalDateTime nowEst = nowUtc.atZone(ZoneId.of("UTC"))
                    .withZoneSameInstant(EST)
                    .toLocalDateTime();
            LocalTime currentTime = nowEst.toLocalTime();

            // CBDR Window 1: PM Session / Asian Open (4:00 PM - 8:00 PM EST)
            LocalTime cbdrPmStart = LocalTime.of(CBDR_PM_START_HOUR, CBDR_PM_START_MINUTE);
            LocalTime cbdrPmEnd = LocalTime.of(CBDR_PM_END_HOUR, CBDR_PM_END_MINUTE);

            if (!currentTime.isBefore(cbdrPmStart) && !currentTime.isAfter(cbdrPmEnd)) {
                return Map.entry(true, "CBDR_PM_ASIAN");
            }

            // CBDR Window 2: London Kill Zone (2:00 AM - 5:00 AM EST)
            LocalTime cbdrLondonStart = LocalTime.of(CBDR_LONDON_START_HOUR, CBDR_LONDON_START_MINUTE);
            LocalTime cbdrLondonEnd = LocalTime.of(CBDR_LONDON_END_HOUR, CBDR_LONDON_END_MINUTE);

            if (!currentTime.isBefore(cbdrLondonStart) && !currentTime.isAfter(cbdrLondonEnd)) {
                return Map.entry(true, "CBDR_LONDON");
            }

            // Pre-NY Open Window (7:30 AM - 9:30 AM EST)
            LocalTime preNyStart = LocalTime.of(PRE_NY_START_HOUR, PRE_NY_START_MINUTE);
            LocalTime preNyEnd = LocalTime.of(PRE_NY_END_HOUR, PRE_NY_END_MINUTE);

            if (!currentTime.isBefore(preNyStart) && !currentTime.isAfter(preNyEnd)) {
                return Map.entry(true, "PRE_NY_OPEN");
            }

            // Not in any trading window
            return Map.entry(false, "OUTSIDE_WINDOW");
        } catch (Exception e) {
            logDebug("Error checking trading window", e);
            return Map.entry(false, "ERROR");
        }
    }

    private void updatePriceFromOrderBook(String alias, Map<Double, Integer> orderBook) {
        try {
            // Find best bid and best ask
            double bestBid = Double.NEGATIVE_INFINITY;
            double bestAsk = Double.POSITIVE_INFINITY;

            for (Map.Entry<Double, Integer> entry : orderBook.entrySet()) {
                double price = entry.getKey();
                int size = entry.getValue();

                // Skip entries with zero size
                if (size <= 0) {
                    continue;
                }

                // Update best bid (highest price)
                if (price > bestBid && isBidPrice(price, alias)) {
                    bestBid = price;
                }

                // Update best ask (lowest price)
                if (price < bestAsk && !isBidPrice(price, alias)) {
                    bestAsk = price;
                }
            }

            // Only update if we have both bid and ask
            if (bestBid > 0 && bestAsk < Double.POSITIVE_INFINITY) {
                double midPrice = (bestBid + bestAsk) / 2.0;
                updateLivePrice(alias, midPrice, bestBid, bestAsk, "depth");
            }
        } catch (Exception e) {
            logDebug("Error updating price from order book", e);
        }
    }

    private boolean isBidPrice(double price, String alias) {
        // This is a simplification - in reality, we need to determine if a price
        // belongs to the bid or ask side. In Bookmap, this is typically handled
        // differently. This is just a placeholder implementation.
        // For a real implementation, you would use the API to determine this.
        return price < getMarketPrice(alias);
    }

    private double getMarketPrice(String alias) {
        // Simplified implementation - in reality, you would use the API
        // to get the current market price.
        // For now, we'll just return a price from our live prices map if available.
        Map<String, Object> priceData = livePrices.get(alias);
        if (priceData != null && priceData.containsKey("mid")) {
            return (double) priceData.get("mid");
        }
        // Default fallback price - this should never be used in practice
        return 0.0;
    }

    private void updateLivePrice(String alias, double midPrice, double bestBid, double bestAsk, String source) {
        try {
            String normalizedSymbol = normalizeSymbol(alias);
            String timestamp = ZonedDateTime.now(ZoneId.of("UTC")).format(isoFormatter);

            Map<String, Object> priceData = new HashMap<>();
            priceData.put("mid", round(midPrice, 2));
            priceData.put("bid", round(bestBid, 2));
            priceData.put("ask", round(bestAsk, 2));
            priceData.put("spread", round(bestAsk - bestBid, 2));
            priceData.put("timestamp", timestamp);
            priceData.put("source", source);
            priceData.put("alias", alias);

            // Store with both full alias and normalized symbol for flexible access
            livePrices.put(alias, priceData);
            livePrices.put(normalizedSymbol, priceData);

            // Periodically write to shared file for dashboard
            updatePriceCacheFile();
        } catch (Exception e) {
            logDebug("Error updating live price", e);
        }
    }

    private void updatePriceCacheFile() {
        try {
            // Only write every 10 updates to reduce I/O overhead
            int count = priceUpdateCounter.incrementAndGet();
            if (count % 10 != 0) {
                return;
            }

            // Using Gson instead of JSONObject for better compatibility
            Gson gson = new GsonBuilder().setPrettyPrinting().create();
            String jsonStr = gson.toJson(livePrices);
            try (FileWriter writer = new FileWriter(PRICE_CACHE_FILE)) {
                writer.write(jsonStr);
            }
        } catch (IOException e) {
            logDebug("Failed to update price cache file", e);
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

    private static double round(double value, int places) {
        if (places < 0) throw new IllegalArgumentException();

        long factor = (long) Math.pow(10, places);
        value = value * factor;
        long tmp = Math.round(value);
        return (double) tmp / factor;
    }
}
