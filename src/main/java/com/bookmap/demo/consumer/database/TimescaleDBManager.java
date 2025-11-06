package com.bookmap.demo.consumer.database;

// HikariCP imports - will be available when JAR is built with dependencies
import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

import java.io.FileInputStream;
import java.io.IOException;
import java.sql.*;
import java.util.*;
import java.util.logging.Logger;

/**
 * TimescaleDB Connection Manager for Historical Trading Data
 * Handles cold storage with connection pooling and batch operations
 */
public class TimescaleDBManager {
    private static final Logger LOGGER = Logger.getLogger(TimescaleDBManager.class.getName());
    private static TimescaleDBManager instance;

    private HikariDataSource dataSource;
    private Properties config;

    private TimescaleDBManager() {
        loadConfiguration();
        initializeConnectionPool();
    }

    public static synchronized TimescaleDBManager getInstance() {
        if (instance == null) {
            instance = new TimescaleDBManager();
        }
        return instance;
    }

    private void loadConfiguration() {
        config = new Properties();
        try {
            FileInputStream fis = new FileInputStream("F:/Databases/database_config.properties");
            config.load(fis);
            fis.close();
            LOGGER.info("TimescaleDB configuration loaded successfully");
        } catch (IOException e) {
            LOGGER.severe("Failed to load configuration: " + e.getMessage());
            setDefaultConfiguration();
        }
    }

    private void setDefaultConfiguration() {
        config.setProperty("timescaledb.host", "localhost");
        config.setProperty("timescaledb.port", "5432");
        config.setProperty("timescaledb.database", "trading_data");
        config.setProperty("timescaledb.user", "postgres");
        config.setProperty("timescaledb.password", "postgres");
        config.setProperty("timescaledb.pool.size", "20");
    }

    private void initializeConnectionPool() {
        // Explicitly load PostgreSQL driver to avoid classloader issues in Bookmap
        try {
            Class.forName("org.postgresql.Driver");
            LOGGER.info("PostgreSQL driver loaded successfully");
        } catch (ClassNotFoundException e) {
            LOGGER.severe("Failed to load PostgreSQL driver: " + e.getMessage());
            throw new RuntimeException("PostgreSQL driver not found", e);
        }

        HikariConfig hikariConfig = new HikariConfig();

        String host = config.getProperty("timescaledb.host", "localhost");
        String port = config.getProperty("timescaledb.port", "5432");
        String database = config.getProperty("timescaledb.database", "trading_data");
        String user = config.getProperty("timescaledb.user", "postgres");
        String password = config.getProperty("timescaledb.password", "postgres");

        String jdbcUrl = "jdbc:postgresql://%s:%s/%s".formatted(host, port, database);
        hikariConfig.setJdbcUrl(jdbcUrl);
        hikariConfig.setUsername(user);
        hikariConfig.setPassword(password);

        // Explicitly set driver class name for HikariCP
        hikariConfig.setDriverClassName("org.postgresql.Driver");

        hikariConfig.setMaximumPoolSize(Integer.parseInt(config.getProperty("timescaledb.pool.size", "20")));
        hikariConfig.setMinimumIdle(Integer.parseInt(config.getProperty("timescaledb.pool.min.idle", "5")));
        hikariConfig.setMaxLifetime(Long.parseLong(config.getProperty("timescaledb.pool.max.lifetime", "1800000")));
        hikariConfig
                .setConnectionTimeout(Long.parseLong(config.getProperty("timescaledb.connection.timeout", "30000")));

        hikariConfig.addDataSourceProperty("cachePrepStmts", "true");
        hikariConfig.addDataSourceProperty("prepStmtCacheSize", "250");
        hikariConfig.addDataSourceProperty("prepStmtCacheSqlLimit", "2048");

        dataSource = new HikariDataSource(hikariConfig);

        // Test connection
        try (Connection conn = dataSource.getConnection()) {
            LOGGER.info("TimescaleDB connection established successfully");
        } catch (SQLException e) {
            LOGGER.severe("Failed to connect to TimescaleDB: " + e.getMessage());
        }
    }

    public Connection getConnection() throws SQLException {
        return dataSource.getConnection();
    }

    // ============================================
    // MBO Data Operations
    // ============================================

    public void insertMboData(String symbol, long timestamp, String side, double price, long size,
            String action, String sessionId, String cbdrWindow) {
        String sql = "INSERT INTO mbo_data (timestamp, symbol, side, price, size, action, session_id, cbdr_window) " +
                "VALUES (to_timestamp(?), ?, ?, ?, ?, ?, ?, ?)";

        try (Connection conn = getConnection();
                PreparedStatement pstmt = conn.prepareStatement(sql)) {

            pstmt.setDouble(1, timestamp / 1000.0); // Convert ms to seconds
            pstmt.setString(2, symbol);
            pstmt.setString(3, side);
            pstmt.setDouble(4, price);
            pstmt.setLong(5, size);
            pstmt.setString(6, action);
            pstmt.setString(7, sessionId);
            pstmt.setString(8, cbdrWindow);

            pstmt.executeUpdate();
        } catch (SQLException e) {
            LOGGER.severe("Error inserting MBO data: " + e.getMessage());
        }
    }

    public void batchInsertMboData(List<MboData> mboDataList) {
        String sql = "INSERT INTO mbo_data (timestamp, symbol, order_id, side, price, size, order_type, action, session_id, cbdr_window) "
                +
                "VALUES (to_timestamp(?), ?, ?, ?, ?, ?, ?, ?, ?, ?)";

        try (Connection conn = getConnection();
                PreparedStatement pstmt = conn.prepareStatement(sql)) {

            conn.setAutoCommit(false);
            int batchSize = 0;

            for (MboData data : mboDataList) {
                pstmt.setDouble(1, data.timestamp / 1000.0);
                pstmt.setString(2, data.symbol);
                pstmt.setLong(3, data.orderId);
                pstmt.setString(4, data.side);
                pstmt.setDouble(5, data.price);
                pstmt.setLong(6, data.size);
                pstmt.setString(7, data.orderType);
                pstmt.setString(8, data.action);
                pstmt.setString(9, data.sessionId);
                pstmt.setString(10, data.cbdrWindow);

                pstmt.addBatch();
                batchSize++;

                if (batchSize % 500 == 0) {
                    pstmt.executeBatch();
                    conn.commit();
                    batchSize = 0;
                }
            }

            if (batchSize > 0) {
                pstmt.executeBatch();
                conn.commit();
            }

            conn.setAutoCommit(true);
            LOGGER.info("Batch inserted " + mboDataList.size() + " MBO records");
        } catch (SQLException e) {
            LOGGER.severe("Error batch inserting MBO data: " + e.getMessage());
        }
    }

    // ============================================
    // OHLC Candle Operations
    // ============================================

    public void insertOhlcCandle(String symbol, String timeframe, long timestamp,
            double open, double high, double low, double close,
            long volume, String sessionId, String cbdrWindow) {
        String sql = "INSERT INTO ohlc_candles (timestamp, symbol, timeframe, open, high, low, close, volume, session_id, cbdr_window) "
                +
                "VALUES (to_timestamp(?), ?, ?, ?, ?, ?, ?, ?, ?, ?)";

        try (Connection conn = getConnection();
                PreparedStatement pstmt = conn.prepareStatement(sql)) {

            pstmt.setDouble(1, timestamp / 1000.0);
            pstmt.setString(2, symbol);
            pstmt.setString(3, timeframe);
            pstmt.setDouble(4, open);
            pstmt.setDouble(5, high);
            pstmt.setDouble(6, low);
            pstmt.setDouble(7, close);
            pstmt.setLong(8, volume);
            pstmt.setString(9, sessionId);
            pstmt.setString(10, cbdrWindow);

            pstmt.executeUpdate();
        } catch (SQLException e) {
            LOGGER.severe("Error inserting OHLC candle: " + e.getMessage());
        }
    }

    public void batchInsertOhlcCandles(List<OhlcCandle> candles) {
        String sql = "INSERT INTO ohlc_candles (timestamp, symbol, timeframe, open, high, low, close, volume, trade_count, vwap, session_id, cbdr_window) "
                +
                "VALUES (to_timestamp(?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) " +
                "ON CONFLICT (timestamp, symbol, timeframe) DO UPDATE SET " +
                "open = EXCLUDED.open, high = EXCLUDED.high, low = EXCLUDED.low, close = EXCLUDED.close, " +
                "volume = EXCLUDED.volume, trade_count = EXCLUDED.trade_count, vwap = EXCLUDED.vwap";

        try (Connection conn = getConnection();
                PreparedStatement pstmt = conn.prepareStatement(sql)) {

            conn.setAutoCommit(false);

            for (OhlcCandle candle : candles) {
                pstmt.setDouble(1, candle.timestamp / 1000.0);
                pstmt.setString(2, candle.symbol);
                pstmt.setString(3, candle.timeframe);
                pstmt.setDouble(4, candle.open);
                pstmt.setDouble(5, candle.high);
                pstmt.setDouble(6, candle.low);
                pstmt.setDouble(7, candle.close);
                pstmt.setLong(8, candle.volume);
                pstmt.setInt(9, candle.tradeCount);
                pstmt.setDouble(10, candle.vwap);
                pstmt.setString(11, candle.sessionId);
                pstmt.setString(12, candle.cbdrWindow);
                pstmt.addBatch();
            }

            pstmt.executeBatch();
            conn.commit();
            conn.setAutoCommit(true);

            LOGGER.info("Batch inserted " + candles.size() + " OHLC candles");
        } catch (SQLException e) {
            LOGGER.severe("Error batch inserting OHLC candles: " + e.getMessage());
        }
    }

    public List<OhlcCandle> getOhlcCandles(String symbol, String timeframe, long startTime, long endTime) {
        List<OhlcCandle> candles = new ArrayList<>();
        String sql = "SELECT timestamp, open, high, low, close, volume, trade_count, vwap " +
                "FROM ohlc_candles WHERE symbol = ? AND timeframe = ? " +
                "AND timestamp >= to_timestamp(?) AND timestamp <= to_timestamp(?) " +
                "ORDER BY timestamp ASC";

        try (Connection conn = getConnection();
                PreparedStatement pstmt = conn.prepareStatement(sql)) {

            pstmt.setString(1, symbol);
            pstmt.setString(2, timeframe);
            pstmt.setDouble(3, startTime / 1000.0);
            pstmt.setDouble(4, endTime / 1000.0);

            ResultSet rs = pstmt.executeQuery();
            while (rs.next()) {
                OhlcCandle candle = new OhlcCandle();
                candle.symbol = symbol;
                candle.timeframe = timeframe;
                candle.timestamp = rs.getTimestamp("timestamp").getTime();
                candle.open = rs.getDouble("open");
                candle.high = rs.getDouble("high");
                candle.low = rs.getDouble("low");
                candle.close = rs.getDouble("close");
                candle.volume = rs.getLong("volume");
                candle.tradeCount = rs.getInt("trade_count");
                candle.vwap = rs.getDouble("vwap");
                candles.add(candle);
            }
        } catch (SQLException e) {
            LOGGER.severe("Error retrieving OHLC candles: " + e.getMessage());
        }

        return candles;
    }

    // ============================================
    // Stops & Icebergs Operations
    // ============================================

    public void insertStopIcebergEvent(String symbol, String eventType, String side,
            long timestamp, double price, long detectedSize,
            long estimatedTotal, double confidence,
            String sessionId, String cbdrWindow, String metadata) {
        String sql = "INSERT INTO stops_icebergs (timestamp, symbol, event_type, side, price, detected_size, " +
                "estimated_total_size, confidence_score, session_id, cbdr_window, metadata) " +
                "VALUES (to_timestamp(?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb)";

        try (Connection conn = getConnection();
                PreparedStatement pstmt = conn.prepareStatement(sql)) {

            pstmt.setDouble(1, timestamp / 1000.0);
            pstmt.setString(2, symbol);
            pstmt.setString(3, eventType);
            pstmt.setString(4, side);
            pstmt.setDouble(5, price);
            pstmt.setLong(6, detectedSize);
            pstmt.setLong(7, estimatedTotal);
            pstmt.setDouble(8, confidence);
            pstmt.setString(9, sessionId);
            pstmt.setString(10, cbdrWindow);
            pstmt.setString(11, metadata);

            pstmt.executeUpdate();
        } catch (SQLException e) {
            LOGGER.severe("Error inserting stop/iceberg event: " + e.getMessage());
        }
    }

    public void batchInsertStopIcebergEvents(List<StopIcebergEvent> events) {
        String sql = "INSERT INTO stops_icebergs (timestamp, symbol, event_type, side, price, detected_size, " +
                "estimated_total_size, fill_count, confidence_score, duration_ms, session_id, cbdr_window, metadata) " +
                "VALUES (to_timestamp(?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb)";

        try (Connection conn = getConnection();
                PreparedStatement pstmt = conn.prepareStatement(sql)) {

            conn.setAutoCommit(false);

            for (StopIcebergEvent event : events) {
                pstmt.setDouble(1, event.timestamp / 1_000_000_000.0); // Convert nanoseconds to seconds
                pstmt.setString(2, event.symbol);
                pstmt.setString(3, event.eventType);
                pstmt.setString(4, event.side);
                pstmt.setDouble(5, event.price);
                pstmt.setLong(6, event.detectedSize);

                // Handle nullable estimated_total_size
                if (event.estimatedTotal > 0) {
                    pstmt.setLong(7, event.estimatedTotal);
                } else {
                    pstmt.setNull(7, java.sql.Types.BIGINT);
                }

                pstmt.setInt(8, event.fillCount);
                pstmt.setDouble(9, event.confidence);

                // Handle nullable duration_ms
                if (event.durationMs > 0) {
                    pstmt.setLong(10, event.durationMs);
                } else {
                    pstmt.setNull(10, java.sql.Types.BIGINT);
                }

                pstmt.setString(11, event.sessionId);
                pstmt.setString(12, event.cbdrWindow);

                // Handle nullable metadata JSONB field
                if (event.metadata != null && !event.metadata.isEmpty()) {
                    pstmt.setString(13, event.metadata);
                } else {
                    pstmt.setNull(13, java.sql.Types.OTHER);
                }

                pstmt.addBatch();
            }

            pstmt.executeBatch();
            conn.commit();
            conn.setAutoCommit(true);

            LOGGER.info("Batch inserted " + events.size() + " stop/iceberg events");
        } catch (SQLException e) {
            LOGGER.severe("Error batch inserting stop/iceberg events: " + e.getMessage());
        }
    }

    // ============================================
    // Absorption Events Operations
    // ============================================

    public void insertAbsorptionEvent(String symbol, String eventType, String side,
            long timestamp, double price, long absorbedVolume,
            long aggressorVolume, double absorptionRatio,
            String sessionId, String cbdrWindow, boolean isInCbdr,
            double significance, String metadata) {
        String sql = "INSERT INTO absorption_events (timestamp, symbol, event_type, side, price, " +
                "absorbed_volume, aggressor_volume, absorption_ratio, session_id, cbdr_window, " +
                "is_in_cbdr, significance_score, metadata) " +
                "VALUES (to_timestamp(?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb)";

        try (Connection conn = getConnection();
                PreparedStatement pstmt = conn.prepareStatement(sql)) {

            pstmt.setDouble(1, timestamp / 1000.0);
            pstmt.setString(2, symbol);
            pstmt.setString(3, eventType);
            pstmt.setString(4, side);
            pstmt.setDouble(5, price);
            pstmt.setLong(6, absorbedVolume);
            pstmt.setLong(7, aggressorVolume);
            pstmt.setDouble(8, absorptionRatio);
            pstmt.setString(9, sessionId);
            pstmt.setString(10, cbdrWindow);
            pstmt.setBoolean(11, isInCbdr);
            pstmt.setDouble(12, significance);
            pstmt.setString(13, metadata);

            pstmt.executeUpdate();
        } catch (SQLException e) {
            LOGGER.severe("Error inserting absorption event: " + e.getMessage());
        }
    }

    public void batchInsertAbsorptionEvents(List<AbsorptionEvent> events) {
        String sql = "INSERT INTO absorption_events (timestamp, symbol, event_type, side, price, " +
                "absorbed_volume, aggressor_volume, liquidity_removed, absorption_ratio, imbalance_ratio, " +
                "session_id, cbdr_window, is_in_cbdr, significance_score, metadata) " +
                "VALUES (to_timestamp(?), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?::jsonb)";

        try (Connection conn = getConnection();
                PreparedStatement pstmt = conn.prepareStatement(sql)) {

            conn.setAutoCommit(false);

            for (AbsorptionEvent event : events) {
                pstmt.setDouble(1, event.timestamp / 1_000_000_000.0); // nanoseconds to seconds
                pstmt.setString(2, event.symbol);
                pstmt.setString(3, event.eventType);
                pstmt.setString(4, event.side);
                pstmt.setDouble(5, event.price);
                pstmt.setLong(6, event.absorbedVolume);
                pstmt.setLong(7, event.aggressorVolume);
                pstmt.setLong(8, event.liquidityRemoved);
                pstmt.setDouble(9, event.absorptionRatio);
                pstmt.setDouble(10, event.imbalanceRatio);
                pstmt.setString(11, event.sessionId);
                pstmt.setString(12, event.cbdrWindow);
                pstmt.setBoolean(13, event.isInCbdr);
                pstmt.setDouble(14, event.significance);
                pstmt.setString(15, event.metadata);
                pstmt.addBatch();
            }

            pstmt.executeBatch();
            conn.commit();
            conn.setAutoCommit(true);

            LOGGER.info("Batch inserted " + events.size() + " absorption events");
        } catch (SQLException e) {
            LOGGER.severe("Error batch inserting absorption events: " + e.getMessage());
        }
    }

    // ============================================
    // Query Operations for Analysis
    // ============================================

    public List<AbsorptionEvent> getAbsorptionEventsDuringCbdr(String symbol, String cbdrWindow,
            long startTime, long endTime) {
        List<AbsorptionEvent> events = new ArrayList<>();
        String sql = "SELECT * FROM absorption_events WHERE symbol = ? AND cbdr_window = ? " +
                "AND timestamp >= to_timestamp(?) AND timestamp <= to_timestamp(?) " +
                "ORDER BY significance_score DESC LIMIT 100";

        try (Connection conn = getConnection();
                PreparedStatement pstmt = conn.prepareStatement(sql)) {

            pstmt.setString(1, symbol);
            pstmt.setString(2, cbdrWindow);
            pstmt.setDouble(3, startTime / 1_000_000_000.0); // nanoseconds to seconds
            pstmt.setDouble(4, endTime / 1_000_000_000.0); // nanoseconds to seconds

            ResultSet rs = pstmt.executeQuery();
            while (rs.next()) {
                AbsorptionEvent event = new AbsorptionEvent();
                event.symbol = symbol;
                event.timestamp = rs.getTimestamp("timestamp").getTime();
                event.eventType = rs.getString("event_type");
                event.side = rs.getString("side");
                event.price = rs.getDouble("price");
                event.absorbedVolume = rs.getLong("absorbed_volume");
                event.aggressorVolume = rs.getLong("aggressor_volume");
                event.absorptionRatio = rs.getDouble("absorption_ratio");
                event.significance = rs.getDouble("significance_score");
                event.cbdrWindow = cbdrWindow;
                events.add(event);
            }
        } catch (SQLException e) {
            LOGGER.severe("Error retrieving absorption events: " + e.getMessage());
        }

        return events;
    }

    public Map<String, Object> getMarketBiasFromHistory(String symbol, int lookbackMinutes) {
        Map<String, Object> bias = new HashMap<>();
        String sql = "SELECT side, SUM(absorbed_volume) as total_volume, AVG(significance_score) as avg_significance " +
                "FROM absorption_events WHERE symbol = ? " +
                "AND timestamp > NOW() - INTERVAL '" + lookbackMinutes + " minutes' " +
                "GROUP BY side";

        try (Connection conn = getConnection();
                PreparedStatement pstmt = conn.prepareStatement(sql)) {

            pstmt.setString(1, symbol);
            ResultSet rs = pstmt.executeQuery();

            long buyVolume = 0;
            long sellVolume = 0;
            double avgSignificance = 0;

            while (rs.next()) {
                String side = rs.getString("side");
                long volume = rs.getLong("total_volume");
                if ("BUY".equals(side)) {
                    buyVolume = volume;
                } else if ("SELL".equals(side)) {
                    sellVolume = volume;
                }
                avgSignificance = Math.max(avgSignificance, rs.getDouble("avg_significance"));
            }

            String direction = "NEUTRAL";
            if (buyVolume > sellVolume * 1.2) {
                direction = "BULLISH";
            } else if (sellVolume > buyVolume * 1.2) {
                direction = "BEARISH";
            }

            bias.put("direction", direction);
            bias.put("confidence", avgSignificance);
            bias.put("buy_volume", buyVolume);
            bias.put("sell_volume", sellVolume);

        } catch (SQLException e) {
            LOGGER.severe("Error calculating market bias: " + e.getMessage());
        }

        return bias;
    }

    // ============================================
    // Session Management
    // ============================================

    public void createTradingSession(String sessionId, String symbol, String sessionType, long startTime) {
        String sql = "INSERT INTO trading_sessions (session_id, symbol, session_type, start_time, total_volume, total_trades) "
                +
                "VALUES (?, ?, ?, to_timestamp(?), 0, 0)";

        try (Connection conn = getConnection();
                PreparedStatement pstmt = conn.prepareStatement(sql)) {

            pstmt.setString(1, sessionId);
            pstmt.setString(2, symbol);
            pstmt.setString(3, sessionType);
            pstmt.setDouble(4, startTime / 1000.0);
            pstmt.executeUpdate();

            LOGGER.info("Created trading session: " + sessionId);
        } catch (SQLException e) {
            LOGGER.severe("Error creating trading session: " + e.getMessage());
        }
    }

    // ============================================
    // Utility Methods
    // ============================================

    public boolean healthCheck() {
        try (Connection conn = getConnection();
                Statement stmt = conn.createStatement()) {
            ResultSet rs = stmt.executeQuery("SELECT 1");
            return rs.next();
        } catch (SQLException e) {
            LOGGER.severe("TimescaleDB health check failed: " + e.getMessage());
            return false;
        }
    }

    public void close() {
        if (dataSource != null && !dataSource.isClosed()) {
            dataSource.close();
            LOGGER.info("TimescaleDB connection pool closed");
        }
    }

    // ============================================
    // Data Classes
    // ============================================

    public static class MboData {
        public String symbol;
        public long timestamp;
        public long orderId;
        public String side;
        public double price;
        public long size;
        public String orderType;
        public String action;
        public String sessionId;
        public String cbdrWindow;
    }

    public static class OhlcCandle {
        public String symbol;
        public String timeframe;
        public long timestamp;
        public double open;
        public double high;
        public double low;
        public double close;
        public long volume;
        public int tradeCount;
        public double vwap;
        public String sessionId;
        public String cbdrWindow;
    }

    public static class StopIcebergEvent {
        public String symbol;
        public long timestamp;
        public String eventType;
        public String side;
        public double price;
        public long detectedSize;
        public long estimatedTotal;
        public int fillCount;
        public double confidence;
        public long durationMs;
        public String sessionId;
        public String cbdrWindow;
        public String metadata;
    }

    public static class AbsorptionEvent {
        public String symbol;
        public long timestamp;
        public String eventType;
        public String side;
        public double price;
        public long absorbedVolume;
        public long aggressorVolume;
        public long liquidityRemoved;
        public double absorptionRatio;
        public double imbalanceRatio;
        public String sessionId;
        public String cbdrWindow;
        public boolean isInCbdr;
        public double significance;
        public String metadata;
    }
}
