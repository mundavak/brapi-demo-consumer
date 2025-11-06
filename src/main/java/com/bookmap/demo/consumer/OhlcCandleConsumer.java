package com.bookmap.demo.consumer;

import com.bookmap.demo.consumer.database.RedisManager;
import com.bookmap.demo.consumer.database.TimescaleDBManager;
import com.bookmap.demo.consumer.utils.SessionManager;
import com.bookmap.demo.consumer.utils.LoggingConfig;

import com.google.gson.Gson;
import java.util.*;
import java.util.concurrent.*;
import java.util.logging.Logger;
import java.util.logging.Level;

// Bookmap Core API imports
import velox.api.layer1.*;
import velox.api.layer1.annotations.*;
import velox.api.layer1.data.*;
import velox.api.layer1.messages.UserMessageLayersChainCreatedTargeted;

/**
 * OHLC Candle Consumer with Redis (hot) and TimescaleDB (cold) storage
 * Captures candle data from market trades
 * Stores real-time in Redis, historical in TimescaleDB
 */
@Layer1Attachable
@Layer1StrategyName("OHLC Candle Consumer")
@Layer1ApiVersion(Layer1ApiVersionValue.VERSION2)
public class OhlcCandleConsumer implements
        Layer1ApiFinishable,
        Layer1ApiAdminAdapter,
        Layer1ApiInstrumentAdapter,
        Layer1ApiDataListener {

    private static final Logger LOGGER = Logger.getLogger(OhlcCandleConsumer.class.getName());
    private static final Gson gson = new Gson();

    private final Layer1ApiProvider provider;
    private RedisManager redisManager;
    private TimescaleDBManager timescaleDBManager;
    private SessionManager sessionManager;

    // Candle tracking by alias
    private final Map<String, Map<String, CandleBuilder>> candleBuilders = new ConcurrentHashMap<>();
    private final Map<String, String> aliasToSymbol = new ConcurrentHashMap<>();
    private final Map<String, String> sessionIds = new ConcurrentHashMap<>();
    private final Map<String, Double> instrumentPips = new ConcurrentHashMap<>();

    // Batch processing for TimescaleDB
    private final BlockingQueue<TimescaleDBManager.OhlcCandle> batchQueue = new LinkedBlockingQueue<>(10000);
    private final ScheduledExecutorService batchProcessor = Executors.newSingleThreadScheduledExecutor();
    private final ScheduledExecutorService candleCloser = Executors.newSingleThreadScheduledExecutor();

    // Supported timeframes
    private static final String[] TIMEFRAMES = { "1m", "5m", "15m", "1h", "4h" };
    private static final Map<String, Long> TIMEFRAME_MILLIS = new HashMap<>();

    static {
        TIMEFRAME_MILLIS.put("1m", 60_000L);
        TIMEFRAME_MILLIS.put("5m", 300_000L);
        TIMEFRAME_MILLIS.put("15m", 900_000L);
        TIMEFRAME_MILLIS.put("1h", 3_600_000L);
        TIMEFRAME_MILLIS.put("4h", 14_400_000L);
    }

    public OhlcCandleConsumer(Layer1ApiProvider provider) {
        this.provider = provider;
        velox.api.layer1.common.ListenableHelper.addListeners(provider, this);

        // Initialize logging
        LoggingConfig.initializeLogging("OhlcCandleConsumer", Level.INFO);

        // Initialize managers
        redisManager = RedisManager.getInstance();
        timescaleDBManager = TimescaleDBManager.getInstance();
        sessionManager = SessionManager.getInstance();

        // Start batch processor (process every 5 seconds)
        batchProcessor.scheduleAtFixedRate(this::processBatch, 5, 5, TimeUnit.SECONDS);

        // Start candle closer (check every 1 second)
        candleCloser.scheduleAtFixedRate(this::closeCompletedCandles, 1, 1, TimeUnit.SECONDS);
    }

    @Override
    public void onUserMessage(Object data) {
        if (data instanceof UserMessageLayersChainCreatedTargeted) {
            UserMessageLayersChainCreatedTargeted message = (UserMessageLayersChainCreatedTargeted) data;
            if (message.targetClass == getClass()) {
                LOGGER.info("OhlcCandleConsumer: Layers chain created");
            }
        }
    }

    @Override
    public void onInstrumentAdded(String alias, InstrumentInfo info) {
        String symbol = info.symbol;
        aliasToSymbol.put(alias, symbol);
        instrumentPips.put(alias, info.pips);

        // Generate session ID
        String sessionId = sessionManager.generateSessionId(symbol);
        sessionIds.put(alias, sessionId);

        // Initialize candle builders for all timeframes
        Map<String, CandleBuilder> builders = new ConcurrentHashMap<>();
        for (String timeframe : TIMEFRAMES) {
            builders.put(timeframe, new CandleBuilder(symbol, timeframe));
        }
        candleBuilders.put(alias, builders);

        // Set symbol active in Redis
        Map<String, String> symbolConfig = new HashMap<>();
        symbolConfig.put("exchange", info.exchange);
        symbolConfig.put("active", "true");
        symbolConfig.put("last_update", String.valueOf(System.currentTimeMillis()));
        redisManager.updateSymbolConfig(symbol, symbolConfig);
        redisManager.setSymbolActive(symbol, true);

        // Create session in Redis
        redisManager.createSession(sessionId, symbol, System.currentTimeMillis());

        // Create session in TimescaleDB
        String sessionType = sessionManager.getSessionType(System.currentTimeMillis());
        timescaleDBManager.createTradingSession(sessionId, symbol, sessionType, System.currentTimeMillis());

        LOGGER.info("OhlcCandleConsumer initialized for " + symbol + " (alias: " + alias + ")");
    }

    @Override
    public void onInstrumentRemoved(String alias) {
        // Close any remaining candles for this instrument
        Map<String, CandleBuilder> builders = candleBuilders.remove(alias);
        if (builders != null) {
            String symbol = aliasToSymbol.get(alias);
            for (Map.Entry<String, CandleBuilder> entry : builders.entrySet()) {
                closeCandle(alias, entry.getKey(), entry.getValue());
            }
        }
        aliasToSymbol.remove(alias);
        sessionIds.remove(alias);
    }

    @Override
    public void onTrade(String alias, double price, int size, TradeInfo tradeInfo) {
        String symbol = aliasToSymbol.get(alias);
        if (symbol == null)
            return;

        // Convert tick price to actual price using pips
        Double pips = instrumentPips.get(alias);
        if (pips == null)
            return;
        double actualPrice = price * pips;

        long timestamp = System.currentTimeMillis();
        Map<String, CandleBuilder> builders = candleBuilders.get(alias);
        if (builders == null)
            return;

        // Update all timeframe candles
        for (Map.Entry<String, CandleBuilder> entry : builders.entrySet()) {
            String timeframe = entry.getKey();
            CandleBuilder builder = entry.getValue();

            builder.addTrade(timestamp, actualPrice, size);

            // Update current candle in Redis for real-time display
            updateRedisCandle(symbol, timeframe, builder);
        }

        // Update session metrics
        String sessionId = sessionIds.get(alias);
        if (sessionId != null) {
            redisManager.updateSessionMetrics(sessionId, size, 1);
        }
    }

    @Override
    public void onDepth(String alias, boolean isBid, int price, int size) {
        // Not used for candle generation
    }

    @Override
    public void onMarketMode(String alias, MarketMode marketMode) {
        // Not used for candle generation
    }

    /**
     * Check and close completed candles
     */
    private void closeCompletedCandles() {
        long currentTime = System.currentTimeMillis();

        for (Map.Entry<String, Map<String, CandleBuilder>> symbolEntry : candleBuilders.entrySet()) {
            String symbol = symbolEntry.getKey();
            Map<String, CandleBuilder> builders = symbolEntry.getValue();

            for (Map.Entry<String, CandleBuilder> builderEntry : builders.entrySet()) {
                String timeframe = builderEntry.getKey();
                CandleBuilder builder = builderEntry.getValue();

                if (builder.shouldClose(currentTime)) {
                    closeCandle(symbol, timeframe, builder);
                }
            }
        }
    }

    /**
     * Close a completed candle and persist to both Redis and TimescaleDB
     */
    private void closeCandle(String symbol, String timeframe, CandleBuilder builder) {
        if (!builder.hasData())
            return;

        String sessionId = sessionIds.get(symbol);
        String cbdrWindow = sessionManager.getCbdrWindow(builder.startTime);

        // Create OHLC candle object
        TimescaleDBManager.OhlcCandle candle = new TimescaleDBManager.OhlcCandle();
        candle.symbol = symbol;
        candle.timeframe = timeframe;
        candle.timestamp = builder.startTime;
        candle.open = builder.open;
        candle.high = builder.high;
        candle.low = builder.low;
        candle.close = builder.close;
        candle.volume = builder.volume;
        candle.tradeCount = builder.tradeCount;
        candle.vwap = builder.getVwap();
        candle.sessionId = sessionId;
        candle.cbdrWindow = cbdrWindow;

        // Add to batch queue for TimescaleDB
        try {
            batchQueue.put(candle);
        } catch (InterruptedException e) {
            LOGGER.warning("Failed to queue candle for batch processing: " + e.getMessage());
        }

        // Store closed candle in Redis with longer TTL
        String closedKey = String.format("candle:%s:%s:closed:%d", symbol, timeframe, builder.startTime);
        Map<String, String> candleData = new HashMap<>();
        candleData.put("open", String.valueOf(candle.open));
        candleData.put("high", String.valueOf(candle.high));
        candleData.put("low", String.valueOf(candle.low));
        candleData.put("close", String.valueOf(candle.close));
        candleData.put("volume", String.valueOf(candle.volume));
        candleData.put("trade_count", String.valueOf(candle.tradeCount));
        candleData.put("vwap", String.valueOf(candle.vwap));
        candleData.put("timestamp", String.valueOf(candle.timestamp));

        try (var jedis = redisManager.getConnection()) {
            jedis.hset(closedKey, candleData);
            jedis.expire(closedKey, 86400); // Keep for 24 hours
        }

        // Reset builder for next candle
        builder.reset(builder.startTime + TIMEFRAME_MILLIS.get(timeframe));

        LOGGER.fine(String.format("Closed candle: %s %s at %d", symbol, timeframe, candle.timestamp));
    }

    /**
     * Update current candle in Redis for real-time dashboard
     */
    private void updateRedisCandle(String symbol, String timeframe, CandleBuilder builder) {
        if (!builder.hasData())
            return;

        Map<String, String> candleData = new HashMap<>();
        candleData.put("open", String.valueOf(builder.open));
        candleData.put("high", String.valueOf(builder.high));
        candleData.put("low", String.valueOf(builder.low));
        candleData.put("close", String.valueOf(builder.close));
        candleData.put("volume", String.valueOf(builder.volume));
        candleData.put("trade_count", String.valueOf(builder.tradeCount));
        candleData.put("vwap", String.valueOf(builder.getVwap()));
        candleData.put("start_time", String.valueOf(builder.startTime));
        candleData.put("last_update", String.valueOf(System.currentTimeMillis()));

        redisManager.updateCurrentCandle(symbol, timeframe, candleData);
    }

    /**
     * Process batch of candles to TimescaleDB
     */
    private void processBatch() {
        List<TimescaleDBManager.OhlcCandle> batch = new ArrayList<>();
        batchQueue.drainTo(batch, 500); // Process up to 500 at a time

        if (!batch.isEmpty()) {
            timescaleDBManager.batchInsertOhlcCandles(batch);
            LOGGER.info("Processed batch of " + batch.size() + " candles to TimescaleDB");
        }
    }

    @Override
    public void finish() {
        LOGGER.info("Stopping OhlcCandleConsumer...");

        // Close any remaining candles
        for (Map.Entry<String, Map<String, CandleBuilder>> entry : candleBuilders.entrySet()) {
            String alias = entry.getKey();
            for (Map.Entry<String, CandleBuilder> builderEntry : entry.getValue().entrySet()) {
                closeCandle(alias, builderEntry.getKey(), builderEntry.getValue());
            }
        }

        // Process remaining batch
        processBatch();

        // Shutdown executors
        batchProcessor.shutdown();
        candleCloser.shutdown();

        try {
            if (!batchProcessor.awaitTermination(10, TimeUnit.SECONDS)) {
                batchProcessor.shutdownNow();
            }
            if (!candleCloser.awaitTermination(10, TimeUnit.SECONDS)) {
                candleCloser.shutdownNow();
            }
        } catch (InterruptedException e) {
            batchProcessor.shutdownNow();
            candleCloser.shutdownNow();
        }

        LOGGER.info("OhlcCandleConsumer stopped");
    }

    /**
     * Inner class to build candles from trades
     */
    private static class CandleBuilder {
        String symbol;
        String timeframe;
        long startTime;
        double open;
        double high;
        double low;
        double close;
        long volume;
        int tradeCount;
        double volumeWeightedSum;
        boolean hasData;

        CandleBuilder(String symbol, String timeframe) {
            this.symbol = symbol;
            this.timeframe = timeframe;
            long now = System.currentTimeMillis();
            long timeframeMillis = TIMEFRAME_MILLIS.get(timeframe);
            this.startTime = (now / timeframeMillis) * timeframeMillis;
            this.hasData = false;
        }

        void addTrade(long timestamp, double price, int size) {
            // Check if we need to start a new candle
            long timeframeMillis = TIMEFRAME_MILLIS.get(timeframe);
            long expectedStart = (timestamp / timeframeMillis) * timeframeMillis;

            if (expectedStart != startTime) {
                // This trade belongs to a new candle period
                return;
            }

            if (!hasData) {
                // First trade in this candle
                open = price;
                high = price;
                low = price;
                close = price;
                hasData = true;
            } else {
                // Update candle
                if (price > high)
                    high = price;
                if (price < low)
                    low = price;
                close = price;
            }

            volume += size;
            tradeCount++;
            volumeWeightedSum += price * size;
        }

        boolean shouldClose(long currentTime) {
            if (!hasData)
                return false;
            long timeframeMillis = TIMEFRAME_MILLIS.get(timeframe);
            return currentTime >= startTime + timeframeMillis;
        }

        double getVwap() {
            return volume > 0 ? volumeWeightedSum / volume : close;
        }

        void reset(long newStartTime) {
            this.startTime = newStartTime;
            this.hasData = false;
            this.volume = 0;
            this.tradeCount = 0;
            this.volumeWeightedSum = 0;
        }

        boolean hasData() {
            return hasData;
        }
    }
}
