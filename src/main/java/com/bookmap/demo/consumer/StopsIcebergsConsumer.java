/*
 * Decompiled with CFR 0.152.
 * 
 * Could not load the following classes:
 *  velox.api.layer1.Layer1ApiAdminAdapter
 *  velox.api.layer1.Layer1ApiFinishable
 *  velox.api.layer1.Layer1ApiInstrumentAdapter
 *  velox.api.layer1.Layer1ApiProvider
 *  velox.api.layer1.Layer1CustomPanelsGetter
 *  velox.api.layer1.LayerApiListenable
 *  velox.api.layer1.annotations.Layer1ApiVersion
 *  velox.api.layer1.annotations.Layer1ApiVersionValue
 *  velox.api.layer1.annotations.Layer1Attachable
 *  velox.api.layer1.annotations.Layer1StrategyName
 *  velox.api.layer1.common.ListenableHelper
 *  velox.api.layer1.common.Log
 *  velox.api.layer1.data.InstrumentInfo
 *  velox.api.layer1.messages.Layer1ApiUserMessageReloadStrategyGui
 *  velox.api.layer1.messages.UserMessageLayersChainCreatedTargeted
 *  velox.gui.StrategyPanel
 */
package com.bookmap.demo.consumer;

import com.bookmap.addons.broadcasting.api.view.BroadcasterConsumer;
import com.bookmap.addons.broadcasting.api.view.GeneratorInfo;
import com.bookmap.addons.broadcasting.api.view.listeners.LiveConnectionStatusListener;
import com.bookmap.addons.broadcasting.api.view.listeners.LiveEventListener;
import com.bookmap.addons.broadcasting.api.view.listeners.ProviderStatusListener;
import com.bookmap.addons.broadcasting.implementations.view.BroadcastFactory;
import com.bookmap.demo.consumer.Connector;
import com.bookmap.demo.consumer.ExecutorsUtilities;
import com.bookmap.demo.consumer.database.RedisManager;
import com.bookmap.demo.consumer.database.TimescaleDBManager;
import com.bookmap.demo.consumer.providers.Provider;
import com.bookmap.demo.consumer.utils.SessionManager;
import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Component;
import java.awt.LayoutManager;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.io.StringWriter;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.SQLException;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TimeZone;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;
import javax.swing.SwingUtilities;
import velox.api.layer1.Layer1ApiAdminAdapter;
import velox.api.layer1.Layer1ApiFinishable;
import velox.api.layer1.Layer1ApiInstrumentAdapter;
import velox.api.layer1.Layer1ApiProvider;
import velox.api.layer1.Layer1CustomPanelsGetter;
import velox.api.layer1.LayerApiListenable;
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
import velox.indicators.sionchart.broadcasting.implementations.IcebergEvent;
import velox.indicators.sionchart.broadcasting.implementations.StopEvent;

@Layer1Attachable
@Layer1StrategyName(value = "SI Broadcasting Consumer")
@Layer1ApiVersion(value = Layer1ApiVersionValue.VERSION2)
public class StopsIcebergsConsumer
        implements Layer1ApiFinishable,
        Layer1ApiAdminAdapter,
        Layer1ApiInstrumentAdapter,
        Layer1CustomPanelsGetter {
    private static final String SI_LOG_PATH = "F:/TradingAgent/si_events.log";
    private static final String SI_JSON_PATH = "F:/TradingAgent/si_data.json";
    private static final String SI_DB_PATH = "F:/TradingAgent/si_events_db.csv";
    private static final int[][] TRADING_WINDOWS_EST = new int[][] { { 16, 0, 20, 0 }, { 2, 0, 5, 0 },
            { 7, 30, 9, 30 } };
    private final RedisManager redisManager;
    private final TimescaleDBManager dbManager;
    private final BlockingQueue<TimescaleDBManager.StopIcebergEvent> batchQueue;
    private final ScheduledExecutorService batchProcessor;
    private String currentSessionId;
    private JTextArea logArea;
    private JLabel statsLabel;
    private final List<Map<String, Object>> stopEvents = new ArrayList<Map<String, Object>>();
    private final List<Map<String, Object>> icebergEvents = new ArrayList<Map<String, Object>>();
    private final AtomicInteger stopCount = new AtomicInteger(0);
    private final AtomicInteger icebergCount = new AtomicInteger(0);
    private final Map<String, Integer> icebergTypeCounts = new HashMap<String, Integer>();
    private final SimpleDateFormat dateFormat = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss.SSS");
    private final Map<String, InstrumentInfo> instrumentsInfo = new ConcurrentHashMap<String, InstrumentInfo>();
    private final Map<String, Double> instrumentPips = new ConcurrentHashMap<String, Double>();
    private final Layer1ApiProvider provider;
    private final BroadcasterConsumer broadcaster;
    private final AtomicBoolean isWorking = new AtomicBoolean(false);
    private final Connector connector;
    private Connection dbConnection;

    public StopsIcebergsConsumer(Layer1ApiProvider provider) {
        this.dateFormat.setTimeZone(TimeZone.getTimeZone("UTC"));
        ListenableHelper.addListeners((LayerApiListenable) provider, (Object) this);
        this.provider = provider;
        Log.info((String) "========================================");
        Log.info((String) "SI Broadcasting Consumer: STARTING UP");
        Log.info((String) "========================================");
        this.redisManager = RedisManager.getInstance();
        this.dbManager = TimescaleDBManager.getInstance();
        this.batchQueue = new LinkedBlockingQueue<TimescaleDBManager.StopIcebergEvent>(5000);
        this.batchProcessor = Executors.newSingleThreadScheduledExecutor();
        this.batchProcessor.scheduleAtFixedRate(this::processBatch, 5L, 5L, TimeUnit.SECONDS);
        this.broadcaster = BroadcastFactory.getBroadcasterConsumer(provider, "SI Broadcasting Consumer",
                this.getClass());
        this.connector = new Connector(provider, this.broadcaster, Provider.SIT_INDICATOR);
        this.broadcaster.setProviderStatusListener(new ProviderStatusListener() {

            @Override
            public void providerUpdateGenerator(String providerName, String providerId, GeneratorInfo generator,
                    boolean isOnline) {
                StopsIcebergsConsumer.this.log("INFO", "Provider update: %s, generator: %s, online: %s".formatted(
                        providerName, generator != null ? generator.getGeneratorName() : "null", isOnline));
                if (StopsIcebergsConsumer.this.isWorking.get()) {
                    ExecutorsUtilities.getExecutor().submit(() -> StopsIcebergsConsumer.this.provider
                            .sendUserMessage((Object) new Layer1ApiUserMessageReloadStrategyGui()));
                }
            }
        });
        Log.info((String) "StopsIcebergsConsumer: Broadcaster created (waiting for chain creation)");
        Log.info((String) "Log file: F:/TradingAgent/si_events.log");
        Log.info((String) "JSON file: F:/TradingAgent/si_data.json");
        Log.info((String) "Redis: Hot storage enabled");
        Log.info((String) "TimescaleDB: Cold storage enabled (batch writes every 5 seconds)");
    }

    private boolean isWithinTradingWindow(long timestampNanos) {
        long timestampMillis = timestampNanos / 1000000L;
        Calendar cal = Calendar.getInstance(TimeZone.getTimeZone("America/New_York"));
        cal.setTimeInMillis(timestampMillis);
        int hour = cal.get(11);
        int minute = cal.get(12);
        int currentMinutes = hour * 60 + minute;
        for (int[] window : TRADING_WINDOWS_EST) {
            int startMinutes = window[0] * 60 + window[1];
            int endMinutes = window[2] * 60 + window[3];
            if (currentMinutes < startMinutes || currentMinutes > endMinutes)
                continue;
            return true;
        }
        return false;
    }

    private void processBatch() {
        try {
            ArrayList<TimescaleDBManager.StopIcebergEvent> batch = new ArrayList<TimescaleDBManager.StopIcebergEvent>();
            this.batchQueue.drainTo(batch, 500);
            if (!batch.isEmpty()) {
                this.dbManager.batchInsertStopIcebergEvents(batch);
                this.log("INFO", "[BATCH] Wrote %d events to TimescaleDB".formatted(batch.size()));
            }
        } catch (Exception e) {
            this.log("ERROR", "[BATCH] Error processing batch: " + e.getMessage());
        }
    }

    private void connectToProvider() {
        this.log("INFO", "Connecting to Stops & Icebergs On-Chart provider...");
        try {
            this.connector.connect();
            ExecutorsUtilities.getExecutor().submit(() -> {
                try {
                    Thread.sleep(1000L);
                    if (this.connector.isConnected()) {
                        this.log("INFO", "\u00e2\u0153\u201c Successfully connected to Stops & Icebergs On-Chart");
                        List<String> generators = this.connector.getGeneratorsNames();
                        this.log("INFO", "Found " + generators.size() + " generator(s)");
                        for (String generatorName : generators) {
                            this.log("INFO", "Subscribing to generator: " + generatorName);
                            this.subscribeToGenerator(generatorName);
                        }
                    } else {
                        this.log("WARN", "Connection not yet established, will retry in 2 seconds...");
                        Thread.sleep(2000L);
                        this.connectToProvider();
                    }
                } catch (Exception e) {
                    this.log("ERROR", "Error during connection setup: " + e.getMessage());
                }
            });
        } catch (Exception e) {
            this.log("ERROR", "Failed to connect to provider: " + e.getMessage());
        }
    }

    private void subscribeToGenerator(String generatorName) {
        try {
            if (!this.connector.isConnected()) {
                this.log("WARN", "Not connected, cannot subscribe to " + generatorName);
                return;
            }
            LiveEventListener eventListener = event -> {
                if (event != null) {
                    this.processIncomingEvent(event);
                }
            };
            LiveConnectionStatusListener connectionListener = isSubscribed -> {
                if (isSubscribed) {
                    this.log("INFO", "\u00e2\u0153\u201c Successfully subscribed to live data: " + generatorName);
                } else {
                    this.log("WARN", "\u00e2\u0153\u2014 Unsubscribed from: " + generatorName);
                }
            };
            this.broadcaster.subscribeToLiveData(Provider.SIT_INDICATOR.getFullName(), generatorName, eventListener,
                    connectionListener);
        } catch (Exception e) {
            this.log("ERROR", "Failed to subscribe to generator " + generatorName + ": " + e.getMessage());
        }
    }

    private void processIncomingEvent(Object event) {
        try {
            String className = event.getClass().getName();
            if (this.icebergCount.get() == 0 && this.stopCount.get() % 100 == 0) {
                this.log("INFO", "Still receiving events - Class: " + className);
            }
            if (event instanceof StopEvent) {
                this.log("DEBUG", "Received StopEvent (direct type)");
                this.onStopEvent(event);
                return;
            }
            if (event instanceof IcebergEvent) {
                this.log("INFO",
                        "\u00e2\u0153\u201c\u00e2\u0153\u201c\u00e2\u0153\u201c Received IcebergEvent (direct type) \u00e2\u0153\u201c\u00e2\u0153\u201c\u00e2\u0153\u201c");
                this.onIcebergEvent(event);
                return;
            }
            if (className.toLowerCase().contains("stop") && className.toLowerCase().contains("event")) {
                this.log("DEBUG", "Received StopEvent (by name): " + className);
                this.onStopEvent(event);
            } else if (className.toLowerCase().contains("iceberg") && className.toLowerCase().contains("event")) {
                this.log("INFO",
                        "\u00e2\u0153\u201c\u00e2\u0153\u201c\u00e2\u0153\u201c Received IcebergEvent (by name): "
                                + className + " \u00e2\u0153\u201c\u00e2\u0153\u201c\u00e2\u0153\u201c");
                this.onIcebergEvent(event);
            } else if (this.stopCount.get() % 50 == 0) {
                this.log("WARN", "Received unknown event type: " + className);
            }
        } catch (Exception e) {
            this.log("ERROR", "Error processing incoming event: " + e.getMessage());
        }
    }

    public void onUserMessage(Object data) {
        try {
            boolean isIcebergEvent;
            if (data == null) {
                return;
            }
            if (data.getClass() == UserMessageLayersChainCreatedTargeted.class) {
                UserMessageLayersChainCreatedTargeted message = (UserMessageLayersChainCreatedTargeted) data;
                if (message.targetClass == this.getClass()) {
                    this.isWorking.set(true);
                    this.broadcaster.start();
                    this.log("INFO", "========================================");
                    this.log("INFO", "Broadcaster STARTED - Now listening for Stop/Iceberg events");
                    this.log("INFO", "========================================");
                    this.connectToProvider();
                    ExecutorsUtilities.getExecutor().submit(
                            () -> this.provider.sendUserMessage((Object) new Layer1ApiUserMessageReloadStrategyGui()));
                }
                return;
            }
            if (!this.isWorking.get()) {
                return;
            }
            String className = data.getClass().getName();
            Log.info((String) ("SI Consumer received message: " + className));
            if (data instanceof StopEvent) {
                this.log("FOUND", "Detected StopEvent (direct type): " + className);
                this.onStopEvent(data);
                return;
            }
            if (data instanceof IcebergEvent) {
                this.log("FOUND", "Detected IcebergEvent (direct type): " + className);
                this.onIcebergEvent(data);
                return;
            }
            boolean isStopEvent = className.toLowerCase().contains("stop") && className.toLowerCase().contains("event");
            boolean bl = isIcebergEvent = className.toLowerCase().contains("iceberg")
                    && className.toLowerCase().contains("event");
            if (isStopEvent) {
                this.log("FOUND", "Detected StopEvent (by name): " + className);
                this.onStopEvent(data);
            } else if (isIcebergEvent) {
                this.log("FOUND", "Detected IcebergEvent (by name): " + className);
                this.onIcebergEvent(data);
            }
        } catch (Exception e) {
            StringWriter sw = new StringWriter();
            e.printStackTrace(new PrintWriter(sw));
            this.log("ERROR", "Error in onUserMessage: " + e.getMessage());
        }
    }

    public void onStopEvent(Object event) {
        try {
            HashMap<String, Object> stopData = new HashMap<String, Object>();
            stopData.put("timestamp", this.dateFormat.format(new Date()));
            stopData.put("type", "stop");
            if (event != null) {
                try {
                    if (this.stopCount.get() == 0) {
                        this.logEventStructure("StopEvent", event);
                    }
                    String instrument = this.instrumentsInfo.isEmpty() ? ""
                            : this.instrumentsInfo.keySet().iterator().next();
                    stopData.put("orderID", this.getFieldValue(event, "orderId"));
                    Object priceObj = this.getFieldValue(event, "price");
                    if (priceObj instanceof Integer tickPrice) {
                        double actualPrice = this.convertPrice(tickPrice, instrument);
                        stopData.put("price", actualPrice);
                    } else {
                        stopData.put("price", priceObj);
                    }
                    stopData.put("size", this.getFieldValue(event, "size"));
                    stopData.put("time", this.getFieldValue(event, "time"));
                    stopData.put("totalSize", this.getFieldValue(event, "totalSize"));
                    Boolean isBid = (Boolean) this.getFieldValue(event, "isBid");
                    stopData.put("isBid", isBid);
                    stopData.put("side", isBid != null && isBid != false ? "BUY" : "SELL");
                    Object typeObj = this.getFieldValue(event, "type");
                    if (typeObj != null) {
                        stopData.put("eventType", typeObj.toString());
                    }
                } catch (Exception e) {
                    this.log("ERROR", "Failed to extract StopEvent fields: " + e.getMessage());
                }
            }
            this.stopEvents.add(stopData);
            int count = this.stopCount.incrementAndGet();
            String logMsg = "[STOP #%d] %s %s @ %s, size=%s, totalSize=%s".formatted(count,
                    stopData.getOrDefault("side", "N/A"), stopData.getOrDefault("orderID", "N/A"),
                    this.formatNumber(stopData.get("price")), this.formatNumber(stopData.get("size")),
                    this.formatNumber(stopData.get("totalSize")));
            this.log("STOP", logMsg);
            this.updateUI();
            try {
                String symbol;
                String string = symbol = this.instrumentsInfo.isEmpty() ? "UNKNOWN"
                        : this.instrumentsInfo.keySet().iterator().next();
                if (this.currentSessionId == null) {
                    this.currentSessionId = SessionManager.getInstance().generateSessionId(symbol);
                }
                long timestamp = stopData.get("time") != null ? ((Number) stopData.get("time")).longValue()
                        : System.nanoTime();
                String eventType = (String) stopData.getOrDefault("eventType", "STOP");
                String side = (String) stopData.getOrDefault("side", "UNKNOWN");
                double price = stopData.get("price") != null ? ((Number) stopData.get("price")).doubleValue() : 0.0;
                double size = stopData.get("size") != null ? ((Number) stopData.get("size")).doubleValue() : 0.0;
                double totalSize = stopData.get("totalSize") != null
                        ? ((Number) stopData.get("totalSize")).doubleValue()
                        : 0.0;
                String cbdrWindow = SessionManager.getInstance().getCbdrWindow(timestamp / 1_000_000L);
                if (cbdrWindow == null) {
                    cbdrWindow = "OUTSIDE_CBDR";
                    this.log("DEBUG", "[STOP] Event outside CBDR windows - still recording");
                } else {
                    this.log("INFO", "[STOP] Event in CBDR window: %s".formatted(cbdrWindow));
                }
                String eventJson = "{\"symbol\":\"%s\",\"timestamp\":%d,\"eventType\":\"%s\",\"side\":\"%s\",\"price\":%.2f,\"size\":%.2f,\"totalSize\":%.2f,\"sessionId\":\"%s\",\"cbdrWindow\":\"%s\"}".formatted(
                        symbol, timestamp, eventType, side, price, size, totalSize, this.currentSessionId, cbdrWindow);
                this.redisManager.addStopIcebergEvent(symbol, eventType, timestamp, eventJson);
                TimescaleDBManager.StopIcebergEvent dbEvent = new TimescaleDBManager.StopIcebergEvent();
                dbEvent.symbol = symbol;
                dbEvent.timestamp = timestamp;
                dbEvent.eventType = eventType;
                dbEvent.side = side;
                dbEvent.price = price;
                dbEvent.detectedSize = (long) size;
                dbEvent.estimatedTotal = (long) totalSize;
                dbEvent.sessionId = this.currentSessionId;
                dbEvent.cbdrWindow = cbdrWindow;
                if (!this.batchQueue.offer(dbEvent)) {
                    this.log("WARN", "Batch queue full, event dropped");
                }
            } catch (Exception e) {
                this.log("ERROR", "Failed to write to databases: " + e.getMessage());
            }
            if (count % 10 == 0) {
                this.saveToJson();
            }
        } catch (Exception e) {
            this.log("ERROR", "Error processing StopEvent: " + e.getMessage());
        }
    }

    public void onIcebergEvent(Object event) {
        try {
            HashMap<String, Object> icebergData = new HashMap<String, Object>();
            icebergData.put("timestamp", this.dateFormat.format(new Date()));
            icebergData.put("type", "iceberg");
            if (event != null) {
                try {
                    if (this.icebergCount.get() == 0) {
                        this.logEventStructure("IcebergEvent", event);
                    }
                    String instrument = this.instrumentsInfo.isEmpty() ? ""
                            : this.instrumentsInfo.keySet().iterator().next();
                    Object typeObj = this.getFieldValue(event, "type");
                    String eventType = typeObj != null ? typeObj.toString() : "unknown";
                    icebergData.put("eventType", eventType);
                    this.icebergTypeCounts.merge(eventType, 1, Integer::sum);
                    icebergData.put("orderID", this.getFieldValue(event, "orderId"));
                    Object priceObj = this.getFieldValue(event, "price");
                    if (priceObj instanceof Integer tickPrice) {
                        double actualPrice = this.convertPrice(tickPrice, instrument);
                        icebergData.put("price", actualPrice);
                    } else {
                        icebergData.put("price", priceObj);
                    }
                    icebergData.put("size", this.getFieldValue(event, "size"));
                    icebergData.put("time", this.getFieldValue(event, "time"));
                    icebergData.put("totalSize", this.getFieldValue(event, "totalSize"));
                    Boolean isBid = (Boolean) this.getFieldValue(event, "isBid");
                    icebergData.put("isBid", isBid);
                    icebergData.put("side", isBid != null && isBid != false ? "BUY" : "SELL");
                    String typeMsg = this.getEventTypeMessage(eventType);
                    icebergData.put("typeMessage", typeMsg);
                } catch (Exception e) {
                    this.log("ERROR", "Failed to extract IcebergEvent fields: " + e.getMessage());
                }
            }
            this.icebergEvents.add(icebergData);
            int count = this.icebergCount.incrementAndGet();
            String logMsg = "[ICEBERG #%d] %s %s @ %s %s".formatted(count,
                    icebergData.getOrDefault("typeMessage", ""), icebergData.getOrDefault("orderID", "N/A"),
                    this.formatNumber(icebergData.get("price")), icebergData.getOrDefault("side", "N/A"));
            this.log("ICEBERG", logMsg);
            this.updateUI();
            try {
                String symbol;
                String string = symbol = this.instrumentsInfo.isEmpty() ? "UNKNOWN"
                        : this.instrumentsInfo.keySet().iterator().next();
                if (this.currentSessionId == null) {
                    this.currentSessionId = SessionManager.getInstance().generateSessionId(symbol);
                }
                long timestamp = icebergData.get("time") != null ? ((Number) icebergData.get("time")).longValue()
                        : System.nanoTime();
                String eventType = "ICEBERG";
                String side = (String) icebergData.getOrDefault("side", "UNKNOWN");
                double price = icebergData.get("price") != null ? ((Number) icebergData.get("price")).doubleValue()
                        : 0.0;
                double size = icebergData.get("size") != null ? ((Number) icebergData.get("size")).doubleValue() : 0.0;
                double totalSize = icebergData.get("totalSize") != null
                        ? ((Number) icebergData.get("totalSize")).doubleValue()
                        : 0.0;
                String cbdrWindow = SessionManager.getInstance().getCbdrWindow(timestamp / 1_000_000L);
                if (cbdrWindow == null) {
                    cbdrWindow = "OUTSIDE_CBDR";
                    this.log("DEBUG", "[ICEBERG] Event outside CBDR windows - still recording");
                } else {
                    this.log("INFO", "[ICEBERG] Event in CBDR window: %s".formatted(cbdrWindow));
                }
                String eventJson = "{\"symbol\":\"%s\",\"timestamp\":%d,\"eventType\":\"%s\",\"side\":\"%s\",\"price\":%.2f,\"size\":%.2f,\"totalSize\":%.2f,\"sessionId\":\"%s\",\"cbdrWindow\":\"%s\"}".formatted(
                        symbol, timestamp, eventType, side, price, size, totalSize, this.currentSessionId, cbdrWindow);
                this.redisManager.addStopIcebergEvent(symbol, eventType, timestamp, eventJson);
                TimescaleDBManager.StopIcebergEvent dbEvent = new TimescaleDBManager.StopIcebergEvent();
                dbEvent.symbol = symbol;
                dbEvent.timestamp = timestamp;
                dbEvent.eventType = eventType;
                dbEvent.side = side;
                dbEvent.price = price;
                dbEvent.detectedSize = (long) size;
                dbEvent.estimatedTotal = (long) totalSize;
                dbEvent.sessionId = this.currentSessionId;
                dbEvent.cbdrWindow = cbdrWindow;
                if (!this.batchQueue.offer(dbEvent)) {
                    this.log("WARN", "Batch queue full, event dropped");
                }
            } catch (Exception e) {
                this.log("ERROR", "Failed to write to databases: " + e.getMessage());
            }
            if ((this.stopCount.get() + this.icebergCount.get()) % 10 == 0) {
                this.saveToJson();
            }
        } catch (Exception e) {
            this.log("ERROR", "Error processing IcebergEvent: " + e.getMessage());
        }
    }

    private String getEventTypeMessage(String eventType) {
        if (eventType == null) {
            return "[UNKNOWN]";
        }
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
        if (obj == null) {
            return null;
        }
        try {
            Field field = obj.getClass().getDeclaredField(fieldName);
            field.setAccessible(true);
            return field.get(obj);
        } catch (Exception e) {
            try {
                String getter = "get" + Character.toUpperCase(fieldName.charAt(0)) + fieldName.substring(1);
                Method m = obj.getClass().getMethod(getter, new Class[0]);
                return m.invoke(obj, new Object[0]);
            } catch (Exception e2) {
                try {
                    String getter = "is" + Character.toUpperCase(fieldName.charAt(0)) + fieldName.substring(1);
                    Method m = obj.getClass().getMethod(getter, new Class[0]);
                    return m.invoke(obj, new Object[0]);
                } catch (Exception e3) {
                    return null;
                }
            }
        }
    }

    private double convertPrice(int tickPrice, String alias) {
        Double pips = this.instrumentPips.get(alias);
        if (pips == null) {
            if (!this.instrumentPips.isEmpty()) {
                pips = this.instrumentPips.values().iterator().next();
                this.log("WARN", "No pip size found for " + alias + ", using fallback: " + pips);
            } else {
                pips = 0.25;
                this.log("WARN", "No pip size available, using default: " + pips);
            }
        }
        return (double) tickPrice * pips;
    }

    private void logEventStructure(String eventName, Object event) {
        Method[] methods;
        Field[] fields;
        this.log("INSPECT", "========================================");
        this.log("INSPECT", "Inspecting " + eventName + " structure:");
        this.log("INSPECT", "Class: " + event.getClass().getName());
        this.log("INSPECT", "--- Fields ---");
        for (Field field : fields = event.getClass().getDeclaredFields()) {
            field.setAccessible(true);
            try {
                Object value = field.get(event);
                this.log("INSPECT",
                        "  %s (%s) = %s".formatted(field.getName(), field.getType().getSimpleName(), value));
            } catch (Exception e) {
                this.log("INSPECT", "  %s (%s) = <error accessing>".formatted(field.getName(),
                        field.getType().getSimpleName()));
            }
        }
        this.log("INSPECT", "--- Public Methods ---");
        for (Method method : methods = event.getClass().getMethods()) {
            String methodName = method.getName();
            if (!methodName.startsWith("get") && !methodName.startsWith("is") || method.getParameterCount() != 0
                    || methodName.equals("getClass"))
                continue;
            try {
                Object value = method.invoke(event, new Object[0]);
                this.log("INSPECT", "  %s() returns %s = %s".formatted(methodName,
                        method.getReturnType().getSimpleName(), value));
            } catch (Exception e) {
                this.log("INSPECT", "  %s() returns %s = <error invoking>".formatted(methodName,
                        method.getReturnType().getSimpleName()));
            }
        }
        this.log("INSPECT", "========================================");
    }

    private void log(String level, String message) {
        String logLine = "[%s] [%s] %s".formatted(this.dateFormat.format(new Date()), level, message);
        Log.info((String) logLine);
        try (FileWriter writer = new FileWriter(SI_LOG_PATH, true);) {
            writer.write(logLine + "\n");
        } catch (IOException e) {
            Log.error((String) "Failed to write to log file", (Throwable) e);
        }
        if (this.logArea != null) {
            SwingUtilities.invokeLater(() -> {
                this.logArea.append(logLine + "\n");
                this.logArea.setCaretPosition(this.logArea.getDocument().getLength());
            });
        }
    }

    private void updateUI() {
        if (this.statsLabel != null) {
            SwingUtilities.invokeLater(() -> {
                StringBuilder stats = new StringBuilder("<html>");
                stats.append("<b>STATISTICS</b><br>");
                stats.append("Total Stops: ").append(this.stopCount.get()).append("<br>");
                stats.append("Total Icebergs: ").append(this.icebergCount.get()).append("<br>");
                if (!this.icebergTypeCounts.isEmpty()) {
                    stats.append("<br><b>Iceberg Types:</b><br>");
                    this.icebergTypeCounts.forEach((type, count) -> stats.append("  ").append((String) type)
                            .append(": ").append(count).append("<br>"));
                }
                stats.append("</html>");
                this.statsLabel.setText(stats.toString());
            });
        }
    }

    private void saveToJson() {
        try (FileWriter writer = new FileWriter(SI_JSON_PATH);) {
            int i;
            StringBuilder json = new StringBuilder();
            json.append("{\n");
            json.append("  \"timestamp\": \"").append(this.dateFormat.format(new Date())).append("\",\n");
            json.append("  \"statistics\": {\n");
            json.append("    \"totalStops\": ").append(this.stopCount.get()).append(",\n");
            json.append("    \"totalIcebergs\": ").append(this.icebergCount.get()).append(",\n");
            json.append("    \"icebergTypes\": {\n");
            int idx = 0;
            for (Map.Entry<String, Integer> e : this.icebergTypeCounts.entrySet()) {
                json.append("      \"").append(e.getKey()).append("\": ").append(e.getValue());
                if (++idx < this.icebergTypeCounts.size()) {
                    json.append(",");
                }
                json.append("\n");
            }
            json.append("    }\n");
            json.append("  },\n");
            json.append("  \"stops\": [\n");
            for (i = 0; i < this.stopEvents.size(); ++i) {
                json.append("    ").append(this.mapToJson(this.stopEvents.get(i)));
                if (i < this.stopEvents.size() - 1) {
                    json.append(",");
                }
                json.append("\n");
            }
            json.append("  ],\n");
            json.append("  \"icebergs\": [\n");
            for (i = 0; i < this.icebergEvents.size(); ++i) {
                json.append("    ").append(this.mapToJson(this.icebergEvents.get(i)));
                if (i < this.icebergEvents.size() - 1) {
                    json.append(",");
                }
                json.append("\n");
            }
            json.append("  ]\n");
            json.append("}\n");
            writer.write(json.toString());
            this.log("INFO",
                    "Saved data to JSON: " + this.stopCount.get() + " stops, " + this.icebergCount.get() + " icebergs");
        } catch (IOException e) {
            this.log("ERROR", "Failed to save JSON: " + e.getMessage());
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
            if (++i >= map.size())
                continue;
            s.append(",");
        }
        s.append("}");
        return s.toString();
    }

    private void exportEventToDb(Map<String, Object> event) {
        try (FileWriter writer = new FileWriter(SI_DB_PATH, true);) {
            String ts = (String) event.getOrDefault("timestamp", this.dateFormat.format(new Date()));
            String type = (String) event.getOrDefault("type", "unknown");
            String orderId = String.valueOf(event.getOrDefault("orderID", ""));
            String price = String.valueOf(event.getOrDefault("price", ""));
            String size = String.valueOf(event.getOrDefault("size", ""));
            String side = String.valueOf(event.getOrDefault("side", ""));
            String totalSize = String.valueOf(event.getOrDefault("totalSize", ""));
            String line = String.join((CharSequence) ",", ts, type, orderId, price, size, side, totalSize);
            writer.write(line + "\n");
        } catch (IOException e) {
            this.log("ERROR", "Failed to append event to CSV file: " + e.getMessage());
        }
        this.saveEventToSQLite(event);
    }

    private void saveEventToSQLite(Map<String, Object> event) {
        if (this.dbConnection == null) {
            this.log("WARN", "Database connection is null, cannot save event");
            return;
        }
        String insertSQL = "INSERT INTO Events (timestamp, event_type, order_id, price, size, side,\n                   total_size, is_bid, instrument, sub_type)\nVALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)\n";
        try (PreparedStatement pstmt = this.dbConnection.prepareStatement(insertSQL);) {
            Boolean isBid;
            String timestamp = (String) event.getOrDefault("timestamp", this.dateFormat.format(new Date()));
            String eventType = (String) event.getOrDefault("type", "unknown");
            String orderId = String.valueOf(event.getOrDefault("orderID", ""));
            Double price = null;
            Object priceObj = event.get("price");
            if (priceObj instanceof Number number) {
                price = number.doubleValue();
            }
            Double size = null;
            Object sizeObj = event.get("size");
            if (sizeObj instanceof Number number) {
                size = number.doubleValue();
            }
            String side = (String) event.getOrDefault("side", "");
            Double totalSize = null;
            Object totalSizeObj = event.get("totalSize");
            if (totalSizeObj instanceof Number number) {
                totalSize = number.doubleValue();
            }
            int isBidInt = (isBid = (Boolean) event.get("isBid")) != null && isBid != false ? 1 : 0;
            String instrument = this.instrumentsInfo.isEmpty() ? "" : this.instrumentsInfo.keySet().iterator().next();
            String subType = (String) event.get("eventType");
            pstmt.setString(1, timestamp);
            pstmt.setString(2, eventType);
            pstmt.setString(3, orderId);
            if (price != null) {
                pstmt.setDouble(4, price);
            } else {
                pstmt.setNull(4, 7);
            }
            if (size != null) {
                pstmt.setDouble(5, size);
            } else {
                pstmt.setNull(5, 7);
            }
            pstmt.setString(6, side);
            if (totalSize != null) {
                pstmt.setDouble(7, totalSize);
            } else {
                pstmt.setNull(7, 7);
            }
            pstmt.setInt(8, isBidInt);
            pstmt.setString(9, instrument);
            pstmt.setString(10, subType);
            pstmt.executeUpdate();
        } catch (SQLException e) {
            this.log("ERROR", "Failed to save event to SQLite database: " + e.getMessage());
        }
    }

    private String formatNumber(Object o) {
        if (o == null) {
            return "N/A";
        }
        if (o instanceof Number number) {
            return "%.2f".formatted(number.doubleValue());
        }
        return o.toString();
    }

    public void finish() {
        try {
            if (this.broadcaster != null) {
                this.broadcaster.finish();
            }
        } catch (Exception e) {
            Log.warn((String) ("Error finishing broadcaster: " + e.getMessage()));
        }
        if (this.batchProcessor != null) {
            try {
                this.log("INFO", "Shutting down batch processor...");
                this.batchProcessor.shutdown();
                if (!this.batchProcessor.awaitTermination(10L, TimeUnit.SECONDS)) {
                    this.batchProcessor.shutdownNow();
                }
                this.processBatch();
                this.log("INFO", "Batch processor shutdown complete");
            } catch (InterruptedException e) {
                this.batchProcessor.shutdownNow();
                Thread.currentThread().interrupt();
            }
        }
        this.saveToJson();
        this.log("INFO",
                "Final statistics: " + this.stopCount.get() + " stops, " + this.icebergCount.get() + " icebergs");
    }

    public void onInstrumentAdded(String alias, InstrumentInfo instrumentInfo) {
        this.instrumentsInfo.put(alias, instrumentInfo);
        double pips = instrumentInfo.pips;
        this.instrumentPips.put(alias, pips);
        this.log("INFO", "Instrument added: %s (pips=%.8f, multiplier=%.2f)".formatted(alias, pips,
                instrumentInfo.multiplier));
    }

    public StrategyPanel[] getCustomGuiFor(String alias, String indicatorName) {
        if (!this.isWorking.get()) {
            return new StrategyPanel[0];
        }
        StrategyPanel mainPanel = new StrategyPanel("SI Events - " + alias);
        mainPanel.setLayout((LayoutManager) new BorderLayout());
        this.statsLabel = new JLabel("<html><b>Waiting for events...</b></html>");
        JPanel statsPanel = new JPanel(new BorderLayout());
        statsPanel.add((Component) this.statsLabel, "North");
        this.logArea = new JTextArea(20, 60);
        this.logArea.setEditable(false);
        this.logArea.setBackground(Color.BLACK);
        this.logArea.setForeground(Color.GREEN);
        JScrollPane scrollPane = new JScrollPane(this.logArea);
        mainPanel.add((Component) statsPanel, (Object) "North");
        mainPanel.add((Component) scrollPane, (Object) "Center");
        this.updateUI();
        return new StrategyPanel[] { mainPanel };
    }
}
