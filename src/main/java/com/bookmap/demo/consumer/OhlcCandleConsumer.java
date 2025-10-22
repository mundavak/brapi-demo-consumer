package com.bookmap.demo.consumer;

import velox.api.layer1.Layer1ApiAdminAdapter;
import velox.api.layer1.Layer1ApiDataAdapter;
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
import velox.api.layer1.data.TradeInfo;
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
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * OHLC Candle Consumer - Builds candles from trade data
 * Aggregates trades into time-based candles (1m, 5m, 15m, 1h)
 * Saves OHLC data to SQLite database
 */
@Layer1Attachable
@Layer1StrategyName("OHLC Candle Consumer")
@Layer1ApiVersion(Layer1ApiVersionValue.VERSION2)
public class OhlcCandleConsumer implements
        Layer1ApiFinishable,
        Layer1ApiAdminAdapter,
        Layer1ApiInstrumentAdapter,
        Layer1CustomPanelsGetter,
        Layer1ApiDataAdapter {

    // Configuration
    private static final String OHLC_LOG_PATH = "F:/TradingAgent/ohlc_candles.log";
    private static final String SQLITE_DB_PATH = "F:/TradingAgent/enhanced_market_monitor_mbo.db";

    // Timeframes in milliseconds
    private static final long[] TIMEFRAMES_MS = {
        60_000L,      // 1 minute
        300_000L,     // 5 minutes
        900_000L,     // 15 minutes
        3600_000L     // 1 hour
    };

    private final Layer1ApiProvider provider;
    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
    private final Map<String, InstrumentInfo> instrumentsInfo = new ConcurrentHashMap<>();
    private final Map<String, Double> instrumentPips = new ConcurrentHashMap<>();
    private Connection dbConnection;
    private final AtomicBoolean isWorking = new AtomicBoolean(false);
    private final AtomicInteger candleCount = new AtomicInteger(0);

    // Candle builders for each timeframe
    private final Map<String, Map<Long, CandleBuilder>> candleBuilders = new ConcurrentHashMap<>();

    // UI components
    private JTextArea logArea;
    private JLabel statsLabel;

    // Scheduler for closing candles
    private ScheduledExecutorService scheduler;

    /**
     * Inner class to build candles from trades
     */
    private class CandleBuilder {
        String instrument;
        long timeframe;
        long periodStart;
        long periodEnd;
        double open = 0;
        double high = Double.MIN_VALUE;
        double low = Double.MAX_VALUE;
        double close = 0;
        double volume = 0;
        boolean hasData = false;

        CandleBuilder(String instrument, long timeframe, long timestamp) {
            this.instrument = instrument;
            this.timeframe = timeframe;
            this.periodStart = (timestamp / timeframe) * timeframe;
            this.periodEnd = periodStart + timeframe;
        }

        synchronized void addTrade(double price, int size, long timestamp) {
            if (!hasData) {
                open = price;
                hasData = true;
            }

            high = Math.max(high, price);
            low = Math.min(low, price);
            close = price;
            volume += size;
        }

        synchronized Map<String, Object> toMap() {
            if (!hasData) {
                return null;
            }

            Map<String, Object> candle = new HashMap<>();
            candle.put("timestamp", dateFormat.format(new Date(periodEnd)));
            candle.put("instrument", instrument);
            candle.put("timeframe", formatTimeframe(timeframe));
            candle.put("open", open);
            candle.put("high", high);
            candle.put("low", low);
            candle.put("close", close);
            candle.put("volume", volume);
            candle.put("bar_start_time", periodStart);
            candle.put("bar_end_time", periodEnd);
            return candle;
        }
    }

    public OhlcCandleConsumer(Layer1ApiProvider provider) {
        dateFormat.setTimeZone(TimeZone.getTimeZone("UTC"));
        ListenableHelper.addListeners(provider, this);
        this.provider = provider;

        Log.info("========================================");
        Log.info("OHLC Candle Consumer: STARTING UP");
        Log.info("========================================");

        initializeDatabase();
        startCandleCloser();

        log("INFO", "OHLC Candle Consumer initialized");
        log("INFO", "Log file: " + OHLC_LOG_PATH);
        log("INFO", "SQLite DB: " + SQLITE_DB_PATH);
        log("INFO", "Timeframes: 1m, 5m, 15m, 1h");
    }

    private void initializeDatabase() {
        try {
            Class.forName("org.sqlite.JDBC");
            String url = "jdbc:sqlite:" + SQLITE_DB_PATH;
            dbConnection = DriverManager.getConnection(url);

            String createTableSQL = """
                CREATE TABLE IF NOT EXISTS candles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    instrument TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL,
                    bar_start_time INTEGER,
                    bar_end_time INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """;

            try (Statement stmt = dbConnection.createStatement()) {
                stmt.execute(createTableSQL);
                log("INFO", "Candles table created or already exists");
            }

            // Create indexes
            try (Statement stmt = dbConnection.createStatement()) {
                stmt.execute("CREATE INDEX IF NOT EXISTS idx_candles_instrument_time ON candles(instrument, timeframe, timestamp)");
            }

        } catch (Exception e) {
            log("ERROR", "Database initialization failed: " + e.getMessage());
        }
    }

    /**
     * Start scheduler to periodically close completed candles
     */
    private void startCandleCloser() {
        scheduler = Executors.newScheduledThreadPool(1);
        scheduler.scheduleAtFixedRate(() -> {
            try {
                closeCompletedCandles();
            } catch (Exception e) {
                log("ERROR", "Error closing candles: " + e.getMessage());
            }
        }, 1, 1, TimeUnit.SECONDS);
    }

    /**
     * Close and save completed candles
     */
    private void closeCompletedCandles() {
        long now = System.currentTimeMillis();

        for (Map.Entry<String, Map<Long, CandleBuilder>> entry : candleBuilders.entrySet()) {
            String instrument = entry.getKey();
            Map<Long, CandleBuilder> timeframes = entry.getValue();

            List<Long> toRemove = new ArrayList<>();

            for (Map.Entry<Long, CandleBuilder> tfEntry : timeframes.entrySet()) {
                Long timeframe = tfEntry.getKey();
                CandleBuilder builder = tfEntry.getValue();

                // Close candle if period has ended
                if (now >= builder.periodEnd) {
                    Map<String, Object> candleData = builder.toMap();
                    if (candleData != null) {
                        saveCandleToDatabase(candleData);
                        int count = candleCount.incrementAndGet();

                        if (count % 10 == 0) {
                            log("CANDLE", String.format("[CANDLE #%d] %s %s: O=%.2f H=%.2f L=%.2f C=%.2f V=%.0f",
                                count, candleData.get("instrument"), candleData.get("timeframe"),
                                candleData.get("open"), candleData.get("high"),
                                candleData.get("low"), candleData.get("close"),
                                candleData.get("volume")));
                        }
                    }
                    toRemove.add(timeframe);
                }
            }

            // Remove closed candles
            toRemove.forEach(timeframes::remove);
        }

        updateUI();
    }

    @Override
    public void onInstrumentAdded(String alias, InstrumentInfo instrumentInfo) {
        instrumentsInfo.put(alias, instrumentInfo);
        instrumentPips.put(alias, instrumentInfo.pips);
        candleBuilders.put(alias, new ConcurrentHashMap<>());

        log("INFO", String.format("Instrument added: %s (pips=%.8f)", alias, instrumentInfo.pips));
    }

    @Override
    public void onInstrumentRemoved(String alias) {
        instrumentsInfo.remove(alias);
        instrumentPips.remove(alias);
        candleBuilders.remove(alias);
        log("INFO", "Instrument removed: " + alias);
    }

    @Override
    public void onTrade(String alias, double price, int size, TradeInfo tradeInfo) {
        if (!isWorking.get()) {
            return;
        }

        try {
            long timestamp = System.currentTimeMillis();

            // Convert price from ticks to actual price (same logic as Stop/Iceberg events)
            // Bookmap's onTrade provides prices in the same format as depth data
            Double pips = instrumentPips.get(alias);
            double actualPrice = price;

            if (pips != null) {
                // Convert: actual_price = tick_price * pips
                actualPrice = price * pips;
            } else {
                log("WARN", "No pip size found for " + alias + ", using raw price");
            }

            // Get or create candle builders for this instrument
            Map<Long, CandleBuilder> timeframes = candleBuilders.get(alias);
            if (timeframes == null) {
                return;
            }

            // Add trade to each timeframe
            for (long timeframe : TIMEFRAMES_MS) {
                CandleBuilder builder = timeframes.computeIfAbsent(timeframe,
                    tf -> new CandleBuilder(alias, tf, timestamp));

                // Check if we need a new candle builder for this period
                if (timestamp >= builder.periodEnd) {
                    // Close the old candle
                    Map<String, Object> candleData = builder.toMap();
                    if (candleData != null) {
                        saveCandleToDatabase(candleData);
                        int count = candleCount.incrementAndGet();

                        log("CANDLE", String.format("[CANDLE #%d] %s %s: O=%.2f H=%.2f L=%.2f C=%.2f V=%.0f",
                            count, candleData.get("instrument"), candleData.get("timeframe"),
                            candleData.get("open"), candleData.get("high"),
                            candleData.get("low"), candleData.get("close"),
                            candleData.get("volume")));
                    }

                    // Create new builder for the new period
                    builder = new CandleBuilder(alias, timeframe, timestamp);
                    timeframes.put(timeframe, builder);
                }

                // Add the converted price to the candle
                builder.addTrade(actualPrice, size, timestamp);
            }

        } catch (Exception e) {
            log("ERROR", "Error processing trade: " + e.getMessage());
        }
    }

    private void saveCandleToDatabase(Map<String, Object> candle) {
        if (dbConnection == null) {
            return;
        }

        String insertSQL = """
            INSERT INTO candles (timestamp, instrument, timeframe, open, high, low, close, volume, bar_start_time, bar_end_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """;

        try (PreparedStatement pstmt = dbConnection.prepareStatement(insertSQL)) {
            pstmt.setString(1, (String) candle.get("timestamp"));
            pstmt.setString(2, (String) candle.get("instrument"));
            pstmt.setString(3, (String) candle.get("timeframe"));
            pstmt.setDouble(4, (Double) candle.get("open"));
            pstmt.setDouble(5, (Double) candle.get("high"));
            pstmt.setDouble(6, (Double) candle.get("low"));
            pstmt.setDouble(7, (Double) candle.get("close"));
            pstmt.setDouble(8, (Double) candle.get("volume"));
            pstmt.setLong(9, (Long) candle.get("bar_start_time"));
            pstmt.setLong(10, (Long) candle.get("bar_end_time"));

            pstmt.executeUpdate();

        } catch (SQLException e) {
            log("ERROR", "Failed to save candle: " + e.getMessage());
        }
    }

    private String formatTimeframe(long milliseconds) {
        if (milliseconds < 60_000) {
            return (milliseconds / 1000) + "s";
        } else if (milliseconds < 3600_000) {
            return (milliseconds / 60_000) + "m";
        } else if (milliseconds < 86400_000) {
            return (milliseconds / 3600_000) + "h";
        } else {
            return (milliseconds / 86400_000) + "d";
        }
    }

    private void log(String level, String message) {
        String logLine = String.format("[%s] [%s] %s", dateFormat.format(new Date()), level, message);
        Log.info(logLine);

        try (FileWriter writer = new FileWriter(OHLC_LOG_PATH, true)) {
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
                stats.append("<b>OHLC CANDLE STATISTICS</b><br>");
                stats.append("Total Candles: ").append(candleCount.get()).append("<br>");
                stats.append("Instruments: ").append(instrumentsInfo.size()).append("<br>");
                stats.append("Timeframes: 1m, 5m, 15m, 1h<br>");
                stats.append("</html>");
                statsLabel.setText(stats.toString());
            });
        }
    }

    @Override
    public void finish() {
        if (scheduler != null) {
            scheduler.shutdown();
        }

        // Close remaining candles
        closeCompletedCandles();

        if (dbConnection != null) {
            try {
                dbConnection.close();
                log("INFO", "Database connection closed");
            } catch (SQLException e) {
                log("ERROR", "Error closing database: " + e.getMessage());
            }
        }

        log("INFO", "Final: " + candleCount.get() + " candles saved");
    }

    @Override
    public StrategyPanel[] getCustomGuiFor(String alias, String indicatorName) {
        isWorking.set(true);

        StrategyPanel mainPanel = new StrategyPanel("OHLC Candles - " + alias);
        mainPanel.setLayout(new BorderLayout());

        statsLabel = new JLabel("<html><b>Building candles from trades...</b></html>");
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

