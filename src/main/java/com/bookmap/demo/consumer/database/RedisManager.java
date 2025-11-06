package com.bookmap.demo.consumer.database;

import java.io.FileInputStream;
import java.io.IOException;
import java.util.*;
import java.util.logging.Logger;

// Redis Jedis imports - will be available when JAR is built with dependencies
import redis.clients.jedis.Jedis;
import redis.clients.jedis.JedisPool;
import redis.clients.jedis.JedisPoolConfig;
import redis.clients.jedis.params.SetParams;
import redis.clients.jedis.resps.StreamEntry;

/**
 * Redis Connection Manager for Real-Time Trading Data
 * Handles hot storage with automatic connection pooling and failover
 */
public class RedisManager {
    private static final Logger LOGGER = Logger.getLogger(RedisManager.class.getName());
    private static RedisManager instance;

    private JedisPool jedisPool;
    private Properties config;
    private final Map<String, Integer> ttlCache;

    private RedisManager() {
        this.ttlCache = new HashMap<>();
        loadConfiguration();
        initializePool();
    }

    public static synchronized RedisManager getInstance() {
        if (instance == null) {
            instance = new RedisManager();
        }
        return instance;
    }

    private void loadConfiguration() {
        config = new Properties();
        try {
            FileInputStream fis = new FileInputStream("F:/Databases/database_config.properties");
            config.load(fis);
            fis.close();

            // Cache TTL values
            ttlCache.put("mbo", Integer.parseInt(config.getProperty("redis.ttl.mbo", "86400")));
            ttlCache.put("ohlc_1m", Integer.parseInt(config.getProperty("redis.ttl.ohlc.1m", "86400")));
            ttlCache.put("stops_icebergs", Integer.parseInt(config.getProperty("redis.ttl.stops.icebergs", "86400")));
            ttlCache.put("absorption", Integer.parseInt(config.getProperty("redis.ttl.absorption", "43200")));
            ttlCache.put("cbdr", Integer.parseInt(config.getProperty("redis.ttl.cbdr", "28800")));
            ttlCache.put("bias", Integer.parseInt(config.getProperty("redis.ttl.bias", "3600")));
            ttlCache.put("dashboard", Integer.parseInt(config.getProperty("redis.ttl.dashboard", "30")));

            LOGGER.info("Redis configuration loaded successfully");
        } catch (IOException e) {
            LOGGER.severe("Failed to load configuration: " + e.getMessage());
            setDefaultConfiguration();
        }
    }

    private void setDefaultConfiguration() {
        config.setProperty("redis.host", "localhost");
        config.setProperty("redis.port", "6379");
        config.setProperty("redis.timeout", "5000");
        config.setProperty("redis.max.connections", "50");
        config.setProperty("redis.min.idle", "10");
        config.setProperty("redis.max.idle", "30");
    }

    private void initializePool() {
        String host = config.getProperty("redis.host", "localhost");
        int port = Integer.parseInt(config.getProperty("redis.port", "6379"));
        int timeout = Integer.parseInt(config.getProperty("redis.timeout", "5000"));
        String password = config.getProperty("redis.password", "");

        JedisPoolConfig poolConfig = new JedisPoolConfig();
        poolConfig.setMaxTotal(Integer.parseInt(config.getProperty("redis.max.connections", "50")));
        poolConfig.setMaxIdle(Integer.parseInt(config.getProperty("redis.max.idle", "30")));
        poolConfig.setMinIdle(Integer.parseInt(config.getProperty("redis.min.idle", "10")));
        poolConfig.setTestOnBorrow(Boolean.parseBoolean(config.getProperty("redis.test.on.borrow", "true")));
        poolConfig.setTestOnReturn(true);
        poolConfig.setTestWhileIdle(true);
        poolConfig.setMinEvictableIdleTimeMillis(60000);
        poolConfig.setTimeBetweenEvictionRunsMillis(30000);

        if (password != null && !password.isEmpty()) {
            jedisPool = new JedisPool(poolConfig, host, port, timeout, password);
        } else {
            jedisPool = new JedisPool(poolConfig, host, port, timeout);
        }

        // Test connection
        try (Jedis jedis = jedisPool.getResource()) {
            String pong = jedis.ping();
            LOGGER.info("Redis connection established: " + pong);
        } catch (Exception e) {
            LOGGER.severe("Failed to connect to Redis: " + e.getMessage());
        }
    }

    public Jedis getConnection() {
        return jedisPool.getResource();
    }

    // ============================================
    // MBO Data Operations
    // ============================================

    public void addMboData(String symbol, String sessionId, long timestamp, String mboJson) {
        String key = String.format("mbo:%s:%s", symbol, sessionId);
        try (Jedis jedis = getConnection()) {
            jedis.zadd(key, timestamp, mboJson);
            jedis.expire(key, ttlCache.get("mbo"));
        } catch (Exception e) {
            LOGGER.severe("Error adding MBO data: " + e.getMessage());
        }
    }

    public List<String> getRecentMboData(String symbol, String sessionId, int count) {
        String key = String.format("mbo:%s:%s", symbol, sessionId);
        try (Jedis jedis = getConnection()) {
            return jedis.zrevrange(key, 0, count - 1);
        } catch (Exception e) {
            LOGGER.severe("Error retrieving MBO data: " + e.getMessage());
            return Collections.emptyList();
        }
    }

    // ============================================
    // Price Ladder Operations
    // ============================================

    public void updatePriceLadder(String symbol, String side, double price, long size) {
        String key = String.format("ladder:%s:%s", symbol, side.toLowerCase());
        try (Jedis jedis = getConnection()) {
            jedis.hset(key, String.valueOf(price), String.valueOf(size));
        } catch (Exception e) {
            LOGGER.severe("Error updating price ladder: " + e.getMessage());
        }
    }

    public Map<String, String> getPriceLadder(String symbol, String side) {
        String key = String.format("ladder:%s:%s", symbol, side.toLowerCase());
        try (Jedis jedis = getConnection()) {
            return jedis.hgetAll(key);
        } catch (Exception e) {
            LOGGER.severe("Error retrieving price ladder: " + e.getMessage());
            return Collections.emptyMap();
        }
    }

    // ============================================
    // OHLC Candle Operations
    // ============================================

    public void updateCurrentCandle(String symbol, String timeframe, Map<String, String> candleData) {
        String key = String.format("candle:%s:%s:current", symbol, timeframe);
        try (Jedis jedis = getConnection()) {
            jedis.hset(key, candleData);
            int ttl = timeframe.equals("1m") ? ttlCache.get("ohlc_1m") : ttlCache.get("ohlc_1m") * 2;
            jedis.expire(key, ttl);
        } catch (Exception e) {
            LOGGER.severe("Error updating current candle: " + e.getMessage());
        }
    }

    public Map<String, String> getCurrentCandle(String symbol, String timeframe) {
        String key = String.format("candle:%s:%s:current", symbol, timeframe);
        try (Jedis jedis = getConnection()) {
            return jedis.hgetAll(key);
        } catch (Exception e) {
            LOGGER.severe("Error retrieving current candle: " + e.getMessage());
            return Collections.emptyMap();
        }
    }

    // ============================================
    // Stops & Icebergs Operations
    // ============================================

    public void addStopIcebergEvent(String symbol, String eventType, long timestamp, String eventJson) {
        String key = String.format("%s:%s:session", eventType.toLowerCase(), symbol);
        try (Jedis jedis = getConnection()) {
            jedis.zadd(key, timestamp, eventJson);
            jedis.expire(key, ttlCache.get("stops_icebergs"));

            // Also add to stream for real-time notifications
            String streamKey = String.format("stream:stops_icebergs:%s", symbol);
            Map<String, String> streamData = new HashMap<>();
            streamData.put("type", eventType);
            streamData.put("timestamp", String.valueOf(timestamp));
            streamData.put("data", eventJson);
            // XADD with MAXLEN approximation
            jedis.xadd(streamKey, streamData, redis.clients.jedis.params.XAddParams.xAddParams().maxLen(1000).approximateTrimming());
        } catch (Exception e) {
            LOGGER.severe("Error adding stop/iceberg event: " + e.getMessage());
        }
    }

    public List<String> getRecentStopIcebergEvents(String symbol, String eventType, int count) {
        String key = String.format("%s:%s:session", eventType.toLowerCase(), symbol);
        try (Jedis jedis = getConnection()) {
            return jedis.zrevrange(key, 0, count - 1);
        } catch (Exception e) {
            LOGGER.severe("Error retrieving stop/iceberg events: " + e.getMessage());
            return Collections.emptyList();
        }
    }

    // ============================================
    // Absorption Events Operations
    // ============================================

    public void addAbsorptionEvent(String symbol, String cbdrWindow, double significance, String eventJson) {
        String key = String.format("absorption:%s:%s", symbol, cbdrWindow);
        try (Jedis jedis = getConnection()) {
            jedis.zadd(key, significance, eventJson);
            jedis.expire(key, ttlCache.get("absorption"));

            // Stream for real-time notifications
            String streamKey = String.format("stream:absorption:%s", symbol);
            Map<String, String> streamData = new HashMap<>();
            streamData.put("window", cbdrWindow);
            streamData.put("significance", String.valueOf(significance));
            streamData.put("data", eventJson);
            // XADD with MAXLEN approximation
            jedis.xadd(streamKey, streamData, redis.clients.jedis.params.XAddParams.xAddParams().maxLen(500).approximateTrimming());
        } catch (Exception e) {
            LOGGER.severe("Error adding absorption event: " + e.getMessage());
        }
    }

    public List<String> getTopAbsorptionEvents(String symbol, String cbdrWindow, int count) {
        String key = String.format("absorption:%s:%s", symbol, cbdrWindow);
        try (Jedis jedis = getConnection()) {
            return jedis.zrevrange(key, 0, count - 1);
        } catch (Exception e) {
            LOGGER.severe("Error retrieving absorption events: " + e.getMessage());
            return Collections.emptyList();
        }
    }

    // ============================================
    // CBDR Window Operations
    // ============================================

    public void updateCbdrWindow(String symbol, String windowType, Map<String, String> windowData) {
        String key = String.format("cbdr:%s:%s", symbol, windowType);
        try (Jedis jedis = getConnection()) {
            jedis.hset(key, windowData);
            jedis.expire(key, ttlCache.get("cbdr"));
        } catch (Exception e) {
            LOGGER.severe("Error updating CBDR window: " + e.getMessage());
        }
    }

    public Map<String, String> getCbdrWindow(String symbol, String windowType) {
        String key = String.format("cbdr:%s:%s", symbol, windowType);
        try (Jedis jedis = getConnection()) {
            return jedis.hgetAll(key);
        } catch (Exception e) {
            LOGGER.severe("Error retrieving CBDR window: " + e.getMessage());
            return Collections.emptyMap();
        }
    }

    // ============================================
    // Market Bias Operations
    // ============================================

    public void updateMarketBias(String symbol, String direction, double confidence, String supportingFactors) {
        String key = String.format("bias:%s", symbol);
        try (Jedis jedis = getConnection()) {
            Map<String, String> biasData = new HashMap<>();
            biasData.put("direction", direction);
            biasData.put("confidence", String.valueOf(confidence));
            biasData.put("last_update", String.valueOf(System.currentTimeMillis()));
            biasData.put("supporting_factors", supportingFactors);
            jedis.hset(key, biasData);
            jedis.expire(key, ttlCache.get("bias"));
        } catch (Exception e) {
            LOGGER.severe("Error updating market bias: " + e.getMessage());
        }
    }

    public Map<String, String> getMarketBias(String symbol) {
        String key = String.format("bias:%s", symbol);
        try (Jedis jedis = getConnection()) {
            return jedis.hgetAll(key);
        } catch (Exception e) {
            LOGGER.severe("Error retrieving market bias: " + e.getMessage());
            return Collections.emptyMap();
        }
    }

    // ============================================
    // Pub/Sub Operations
    // ============================================

    public void publishSignal(String symbol, String signal) {
        String channel = String.format("signals:%s", symbol);
        try (Jedis jedis = getConnection()) {
            jedis.publish(channel, signal);
        } catch (Exception e) {
            LOGGER.severe("Error publishing signal: " + e.getMessage());
        }
    }

    // ============================================
    // Session Management
    // ============================================

    public void createSession(String sessionId, String symbol, long startTime) {
        String key = String.format("session:%s", sessionId);
        try (Jedis jedis = getConnection()) {
            Map<String, String> sessionData = new HashMap<>();
            sessionData.put("symbol", symbol);
            sessionData.put("start_time", String.valueOf(startTime));
            sessionData.put("status", "ACTIVE");
            sessionData.put("volume", "0");
            sessionData.put("trades", "0");
            jedis.hset(key, sessionData);
            jedis.expire(key, 172800); // 48 hours

            jedis.sadd("sessions:active", sessionId);
        } catch (Exception e) {
            LOGGER.severe("Error creating session: " + e.getMessage());
        }
    }

    public void updateSessionMetrics(String sessionId, long volumeDelta, int tradesDelta) {
        String key = String.format("session:%s", sessionId);
        try (Jedis jedis = getConnection()) {
            jedis.hincrBy(key, "volume", volumeDelta);
            jedis.hincrBy(key, "trades", tradesDelta);
        } catch (Exception e) {
            LOGGER.severe("Error updating session metrics: " + e.getMessage());
        }
    }

    public Set<String> getActiveSessions() {
        try (Jedis jedis = getConnection()) {
            return jedis.smembers("sessions:active");
        } catch (Exception e) {
            LOGGER.severe("Error retrieving active sessions: " + e.getMessage());
            return Collections.emptySet();
        }
    }

    // ============================================
    // Symbol Management
    // ============================================

    public void updateSymbolConfig(String symbol, Map<String, String> config) {
        String key = String.format("symbol:%s:config", symbol);
        try (Jedis jedis = getConnection()) {
            jedis.hset(key, config);
        } catch (Exception e) {
            LOGGER.severe("Error updating symbol config: " + e.getMessage());
        }
    }

    public void setSymbolActive(String symbol, boolean active) {
        try (Jedis jedis = getConnection()) {
            if (active) {
                jedis.sadd("symbols:active", symbol);
            } else {
                jedis.srem("symbols:active", symbol);
            }
        } catch (Exception e) {
            LOGGER.severe("Error setting symbol active status: " + e.getMessage());
        }
    }

    public Set<String> getActiveSymbols() {
        try (Jedis jedis = getConnection()) {
            return jedis.smembers("symbols:active");
        } catch (Exception e) {
            LOGGER.severe("Error retrieving active symbols: " + e.getMessage());
            return Collections.emptySet();
        }
    }

    // ============================================
    // Dashboard Cache Operations (requires RedisJSON)
    // ============================================

    public void updateDashboardSummary(String symbol, String jsonSummary) {
        String key = String.format("dashboard:%s:summary", symbol);
        try (Jedis jedis = getConnection()) {
            jedis.set(key, jsonSummary);
            jedis.expire(key, ttlCache.get("dashboard"));
        } catch (Exception e) {
            LOGGER.severe("Error updating dashboard summary: " + e.getMessage());
        }
    }

    public String getDashboardSummary(String symbol) {
        String key = String.format("dashboard:%s:summary", symbol);
        try (Jedis jedis = getConnection()) {
            return jedis.get(key);
        } catch (Exception e) {
            LOGGER.severe("Error retrieving dashboard summary: " + e.getMessage());
            return null;
        }
    }

    // ============================================
    // Utility Methods
    // ============================================

    public boolean healthCheck() {
        try (Jedis jedis = getConnection()) {
            String pong = jedis.ping();
            return "PONG".equals(pong);
        } catch (Exception e) {
            LOGGER.severe("Redis health check failed: " + e.getMessage());
            return false;
        }
    }

    public void flushSymbolData(String symbol) {
        try (Jedis jedis = getConnection()) {
            String pattern = String.format("*:%s:*", symbol);
            jedis.keys(pattern).forEach(jedis::del);
            LOGGER.info("Flushed all data for symbol: " + symbol);
        } catch (Exception e) {
            LOGGER.severe("Error flushing symbol data: " + e.getMessage());
        }
    }

    public void cleanup(long olderThanTimestamp) {
        try (Jedis jedis = getConnection()) {
            Set<String> activeSymbols = getActiveSymbols();
            for (String symbol : activeSymbols) {
                // Clean old MBO data
                Set<String> sessions = jedis.keys(String.format("mbo:%s:*", symbol));
                for (String key : sessions) {
                    jedis.zremrangeByScore(key, 0, olderThanTimestamp);
                }

                // Clean old events
                jedis.zremrangeByScore(String.format("stops:%s:session", symbol), 0, olderThanTimestamp);
                jedis.zremrangeByScore(String.format("icebergs:%s:session", symbol), 0, olderThanTimestamp);
            }
            LOGGER.info("Cleanup completed for data older than: " + olderThanTimestamp);
        } catch (Exception e) {
            LOGGER.severe("Error during cleanup: " + e.getMessage());
        }
    }

    public void close() {
        if (jedisPool != null && !jedisPool.isClosed()) {
            jedisPool.close();
            LOGGER.info("Redis connection pool closed");
        }
    }
}

