package com.bookmap.demo.consumer.utils;

import com.bookmap.demo.consumer.database.RedisManager;
import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;

import java.io.FileInputStream;
import java.io.FileWriter;
import java.io.IOException;
import java.lang.reflect.Type;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Logger;

/**
 * Dynamic Symbol Selection and Configuration Manager
 * Manages multiple trading symbols (MNQ, BTC, etc.) with persistence
 * Integrates with Redis for real-time state and JSON for configuration
 */
public class SymbolManager {
    private static final Logger LOGGER = Logger.getLogger(SymbolManager.class.getName());
    private static final Gson gson = new Gson();
    private static SymbolManager instance;

    private final Map<String, SymbolConfig> symbolConfigs = new ConcurrentHashMap<>();
    private final Set<String> activeSymbols = ConcurrentHashMap.newKeySet();
    private RedisManager redisManager;
    private String configFilePath = "F:/TradingAgent/Dashboard/symbol_config.json";

    private SymbolManager() {
        this.redisManager = RedisManager.getInstance();
        loadConfiguration();
        syncWithRedis();
    }

    public static synchronized SymbolManager getInstance() {
        if (instance == null) {
            instance = new SymbolManager();
        }
        return instance;
    }

    /**
     * Load symbol configurations from JSON file
     */
    private void loadConfiguration() {
        try (FileInputStream fis = new FileInputStream(configFilePath)) {
            Type listType = new TypeToken<List<SymbolConfig>>() {
            }.getType();
            List<SymbolConfig> configs = gson.fromJson(
                    new java.io.InputStreamReader(fis), listType);

            if (configs != null) {
                for (SymbolConfig config : configs) {
                    symbolConfigs.put(config.symbol, config);
                    if (config.isActive) {
                        activeSymbols.add(config.symbol);
                    }
                }
                LOGGER.info("Loaded " + symbolConfigs.size() + " symbol configurations");
            }
        } catch (IOException e) {
            LOGGER.warning("No symbol config found, creating defaults: " + e.getMessage());
            createDefaultConfiguration();
        }
    }

    /**
     * Create default configuration for initial setup
     */
    private void createDefaultConfiguration() {
        // MNQ (Micro E-mini Nasdaq-100)
        SymbolConfig mnq = new SymbolConfig();
        mnq.symbol = "MNQ";
        mnq.exchange = "CME";
        mnq.description = "Micro E-mini Nasdaq-100 Futures";
        mnq.tickSize = 0.25;
        mnq.tickValue = 0.50; // $0.50 per 0.25 tick
        mnq.contractMultiplier = 2.0;
        mnq.currency = "USD";
        mnq.isActive = true;
        mnq.tradingHours = "23:00 - 22:00 EST (Sun-Fri)";
        mnq.cbdrSupport = true;
        mnq.priority = 1;

        // BTC (Bitcoin Futures) - for future use
        SymbolConfig btc = new SymbolConfig();
        btc.symbol = "BTC";
        btc.exchange = "CME";
        btc.description = "Bitcoin Futures";
        btc.tickSize = 5.0;
        btc.tickValue = 25.0; // $25 per 5 tick
        btc.contractMultiplier = 5.0;
        btc.currency = "USD";
        btc.isActive = false;
        btc.tradingHours = "18:00 - 17:00 EST (Sun-Fri)";
        btc.cbdrSupport = true;
        btc.priority = 2;

        symbolConfigs.put("MNQ", mnq);
        symbolConfigs.put("BTC", btc);
        activeSymbols.add("MNQ");

        saveConfiguration();
        LOGGER.info("Created default symbol configuration");
    }

    /**
     * Save current configuration to JSON file
     */
    public synchronized void saveConfiguration() {
        try (FileWriter writer = new FileWriter(configFilePath)) {
            List<SymbolConfig> configs = new ArrayList<>(symbolConfigs.values());
            gson.toJson(configs, writer);
            LOGGER.info("Symbol configuration saved to " + configFilePath);
        } catch (IOException e) {
            LOGGER.severe("Failed to save symbol configuration: " + e.getMessage());
        }
    }

    /**
     * Sync with Redis on startup
     */
    private void syncWithRedis() {
        // Get active symbols from Redis
        Set<String> redisActiveSymbols = redisManager.getActiveSymbols();

        // Update local state from Redis
        for (String symbol : redisActiveSymbols) {
            if (symbolConfigs.containsKey(symbol)) {
                activeSymbols.add(symbol);
                symbolConfigs.get(symbol).isActive = true;
            }
        }

        // Update Redis with any local active symbols not in Redis
        for (String symbol : activeSymbols) {
            redisManager.setSymbolActive(symbol, true);
            updateRedisConfig(symbol);
        }

        LOGGER.info("Synced with Redis: " + activeSymbols.size() + " active symbols");
    }

    /**
     * Activate a symbol for trading
     */
    public boolean activateSymbol(String symbol) {
        if (!symbolConfigs.containsKey(symbol)) {
            LOGGER.warning("Symbol not found in configuration: " + symbol);
            return false;
        }

        SymbolConfig config = symbolConfigs.get(symbol);
        config.isActive = true;
        activeSymbols.add(symbol);

        // Update Redis
        redisManager.setSymbolActive(symbol, true);
        updateRedisConfig(symbol);

        saveConfiguration();
        LOGGER.info("Activated symbol: " + symbol);
        return true;
    }

    /**
     * Deactivate a symbol
     */
    public boolean deactivateSymbol(String symbol) {
        if (!symbolConfigs.containsKey(symbol)) {
            return false;
        }

        SymbolConfig config = symbolConfigs.get(symbol);
        config.isActive = false;
        activeSymbols.remove(symbol);

        // Update Redis
        redisManager.setSymbolActive(symbol, false);

        saveConfiguration();
        LOGGER.info("Deactivated symbol: " + symbol);
        return true;
    }

    /**
     * Get all active symbols
     */
    public Set<String> getActiveSymbols() {
        return new HashSet<>(activeSymbols);
    }

    /**
     * Get symbol configuration
     */
    public SymbolConfig getSymbolConfig(String symbol) {
        return symbolConfigs.get(symbol);
    }

    /**
     * Get all symbol configurations
     */
    public Map<String, SymbolConfig> getAllConfigs() {
        return new HashMap<>(symbolConfigs);
    }

    /**
     * Add or update symbol configuration
     */
    public void updateSymbolConfig(SymbolConfig config) {
        symbolConfigs.put(config.symbol, config);
        if (config.isActive) {
            activeSymbols.add(config.symbol);
            redisManager.setSymbolActive(config.symbol, true);
            updateRedisConfig(config.symbol);
        }
        saveConfiguration();
        LOGGER.info("Updated symbol configuration: " + config.symbol);
    }

    /**
     * Update Redis with symbol configuration
     */
    private void updateRedisConfig(String symbol) {
        SymbolConfig config = symbolConfigs.get(symbol);
        if (config == null)
            return;

        Map<String, String> redisConfig = new HashMap<>();
        redisConfig.put("exchange", config.exchange);
        redisConfig.put("description", config.description);
        redisConfig.put("tick_size", String.valueOf(config.tickSize));
        redisConfig.put("tick_value", String.valueOf(config.tickValue));
        redisConfig.put("contract_multiplier", String.valueOf(config.contractMultiplier));
        redisConfig.put("currency", config.currency);
        redisConfig.put("active", String.valueOf(config.isActive));
        redisConfig.put("trading_hours", config.tradingHours);
        redisConfig.put("cbdr_support", String.valueOf(config.cbdrSupport));
        redisConfig.put("priority", String.valueOf(config.priority));
        redisConfig.put("last_update", String.valueOf(System.currentTimeMillis()));

        redisManager.updateSymbolConfig(symbol, redisConfig);
    }

    /**
     * Get symbols by priority (for dashboard display order)
     */
    public List<String> getSymbolsByPriority() {
        return symbolConfigs.values().stream()
                .sorted(Comparator.comparingInt(c -> c.priority))
                .map(c -> c.symbol)
                .collect(java.util.stream.Collectors.toList());
    }

    /**
     * Check if symbol supports CBDR trading
     */
    public boolean supportsCbdr(String symbol) {
        SymbolConfig config = symbolConfigs.get(symbol);
        return config != null && config.cbdrSupport;
    }

    /**
     * Get primary symbol (lowest priority number)
     */
    public String getPrimarySymbol() {
        return symbolConfigs.values().stream()
                .filter(c -> c.isActive)
                .min(Comparator.comparingInt(c -> c.priority))
                .map(c -> c.symbol)
                .orElse("MNQ");
    }

    /**
     * Calculate tick value in dollars for a given move
     */
    public double calculateTickValue(String symbol, double priceDiff) {
        SymbolConfig config = symbolConfigs.get(symbol);
        if (config == null)
            return 0;

        double ticks = priceDiff / config.tickSize;
        return ticks * config.tickValue;
    }

    /**
     * Get symbol statistics from Redis
     */
    public Map<String, Object> getSymbolStatistics(String symbol) {
        Map<String, Object> stats = new HashMap<>();

        // Get config
        SymbolConfig config = symbolConfigs.get(symbol);
        if (config != null) {
            stats.put("config", config);
        }

        // Get from Redis
        Map<String, String> redisConfig = redisManager.getPriceLadder(symbol, "config");
        stats.put("redis_data", redisConfig);

        // Get current bias
        Map<String, String> bias = redisManager.getMarketBias(symbol);
        stats.put("market_bias", bias);

        // Get active sessions
        Set<String> sessions = redisManager.getActiveSessions();
        long symbolSessions = sessions.stream()
                .filter(s -> s.startsWith(symbol + "_"))
                .count();
        stats.put("active_sessions", symbolSessions);

        return stats;
    }

    /**
     * Symbol configuration data class
     */
    public static class SymbolConfig {
        public String symbol;
        public String exchange;
        public String description;
        public double tickSize;
        public double tickValue;
        public double contractMultiplier;
        public String currency;
        public boolean isActive;
        public String tradingHours;
        public boolean cbdrSupport;
        public int priority; // Lower number = higher priority (1 = primary)
        public long lastTradeTime;
        public double lastPrice;

        @Override
        public String toString() {
            return String.format("%s (%s) - %s [Tick: %.2f = $%.2f]",
                    symbol, exchange, description, tickSize, tickValue);
        }
    }
}
