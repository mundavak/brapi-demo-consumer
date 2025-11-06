# ============================================
# Redis Key Structure Documentation
# Trading Data Architecture Hot Storage
# ============================================

# This document describes all Redis key patterns and data structures
# used in the trading data architecture for real-time access

# ============================================
# MBO DATA (Market By Order)
# ============================================

# Pattern: mbo:{symbol}:{session_id}
# Type: Sorted Set
# Score: timestamp (milliseconds)
# Value: JSON string with MBO event data
# TTL: 86400 seconds (24 hours)
# Example:
#   Key: mbo:MNQ:MNQ_20240115_NEWYORK
#   ZADD mbo:MNQ:MNQ_20240115_NEWYORK 1705334400000 '{"order_id": 12345, "side": "BUY", "price": 17500.25, "size": 10, "action": "ADD"}'
# Queries:
#   ZREVRANGE mbo:MNQ:MNQ_20240115_NEWYORK 0 99  # Get last 100 events
#   ZRANGEBYSCORE mbo:MNQ:session 1705334400000 1705334500000  # Events in time range

# ============================================
# PRICE LADDER
# ============================================

# Pattern: ladder:{symbol}:{side}
# Type: Hash
# Field: price level (as string)
# Value: current size at that price
# TTL: No expiration (updated continuously)
# Example:
#   Key: ladder:MNQ:bid
#   HSET ladder:MNQ:bid 17500.25 150
#   HSET ladder:MNQ:ask 17500.50 200
# Queries:
#   HGETALL ladder:MNQ:bid  # Get entire bid ladder
#   HGET ladder:MNQ:ask 17500.50  # Get size at specific ask price

# ============================================
# OHLC CANDLES
# ============================================

# Pattern: candle:{symbol}:{timeframe}:current
# Type: Hash
# Fields: open, high, low, close, volume, trade_count, vwap, start_time, last_update
# TTL: Based on timeframe (1m = 86400, 5m = 172800)
# Example:
#   Key: candle:MNQ:1m:current
#   HSET candle:MNQ:1m:current open 17500.00 high 17505.25 low 17498.50 close 17503.00 volume 1500
# Queries:
#   HGETALL candle:MNQ:1m:current  # Get current 1m candle

# Pattern: candle:{symbol}:{timeframe}:closed:{timestamp}
# Type: Hash
# Fields: open, high, low, close, volume, trade_count, vwap, timestamp
# TTL: 86400 seconds (24 hours)
# Example:
#   Key: candle:MNQ:1m:closed:1705334400000
#   HSET candle:MNQ:1m:closed:1705334400000 open 17500.00 close 17503.00
# Queries:
#   KEYS candle:MNQ:1m:closed:*  # Get all closed 1m candles (use SCAN in production)

# ============================================
# STOPS & ICEBERGS EVENTS
# ============================================

# Pattern: iceberg:{symbol}:session
# Type: Sorted Set
# Score: timestamp
# Value: JSON event data
# TTL: 86400 seconds (24 hours)
# Example:
#   Key: iceberg:MNQ:session
#   ZADD iceberg:MNQ:session 1705334400000 '{"price": 17500.25, "detected_size": 500, "estimated_total": 1000, "confidence": 0.85}'

# Pattern: stops:{symbol}:session
# Type: Sorted Set
# Score: timestamp
# Value: JSON event data
# TTL: 86400 seconds (24 hours)
# Example:
#   Key: stops:MNQ:session
#   ZADD stops:MNQ:session 1705334400000 '{"price": 17490.00, "detected_size": 350, "fill_count": 8, "confidence": 0.75}'

# Pattern: stream:stops_icebergs:{symbol}
# Type: Stream
# Fields: type, timestamp, data
# MaxLen: ~1000 (approximate trimming)
# Example:
#   XADD stream:stops_icebergs:MNQ * type ICEBERG timestamp 1705334400000 data '{"price": 17500.25}'
# Queries:
#   XREAD COUNT 10 STREAMS stream:stops_icebergs:MNQ 0  # Read last 10 events
#   XREVRANGE stream:stops_icebergs:MNQ + - COUNT 10  # Get 10 most recent

# ============================================
# ABSORPTION EVENTS
# ============================================

# Pattern: absorption:{symbol}:{cbdr_window}
# Type: Sorted Set
# Score: significance (not timestamp!)
# Value: JSON event data
# TTL: 43200 seconds (12 hours)
# Example:
#   Key: absorption:MNQ:PM
#   ZADD absorption:MNQ:PM 0.92 '{"timestamp": 1705334400000, "price": 17500.25, "absorbed_volume": 300, "side": "BUY"}'
# Queries:
#   ZREVRANGE absorption:MNQ:PM 0 19  # Get top 20 significant events
#   ZREVRANGEBYSCORE absorption:MNQ:PM 1.0 0.8  # Events with significance 0.8-1.0

# Pattern: stream:absorption:{symbol}
# Type: Stream
# Fields: window, significance, data
# MaxLen: ~500
# Example:
#   XADD stream:absorption:MNQ * window PM significance 0.92 data '{"price": 17500.25}'

# ============================================
# CBDR WINDOW STATE
# ============================================

# Pattern: cbdr:{symbol}:{window_type}
# Type: Hash
# Fields: status, bias, start_time, end_time, event_count, bullish_events, bearish_events
# TTL: 28800 seconds (8 hours)
# Example:
#   Key: cbdr:MNQ:PM
#   HSET cbdr:MNQ:PM status ACTIVE bias BULLISH start_time 1705334400000 event_count 15
# Queries:
#   HGETALL cbdr:MNQ:PM  # Get PM window status for MNQ

# Valid window_type values: PM, LONDON, PRE_NY

# ============================================
# MARKET BIAS
# ============================================

# Pattern: bias:{symbol}
# Type: Hash
# Fields: direction, confidence, last_update, supporting_factors
# TTL: 3600 seconds (1 hour)
# Example:
#   Key: bias:MNQ
#   HSET bias:MNQ direction BULLISH confidence 0.78 last_update 1705334400000 supporting_factors "PM window absorption: 12 vs 3"
# Queries:
#   HGETALL bias:MNQ  # Get current market bias

# Valid direction values: BULLISH, BEARISH, NEUTRAL

# ============================================
# PUB/SUB CHANNELS
# ============================================

# Pattern: signals:{symbol}
# Type: Pub/Sub Channel
# Message Format: "EVENT_TYPE:SIDE:PRICE:CONFIDENCE:METADATA"
# Example:
#   PUBLISH signals:MNQ "ICEBERG:BUY:17500.25:0.85:1000"
#   PUBLISH signals:MNQ "ABSORPTION:SELL:17500.25:0.92:PM"
#   PUBLISH signals:MNQ "STOP_CLUSTER:BUY:17490.00:0.75:350"
# Subscription:
#   SUBSCRIBE signals:MNQ
#   PSUBSCRIBE signals:*  # Subscribe to all symbols

# ============================================
# SESSION MANAGEMENT
# ============================================

# Pattern: session:{session_id}
# Type: Hash
# Fields: symbol, start_time, status, volume, trades
# TTL: 172800 seconds (48 hours)
# Example:
#   Key: session:MNQ_20240115_NEWYORK
#   HSET session:MNQ_20240115_NEWYORK symbol MNQ start_time 1705334400000 status ACTIVE volume 15000 trades 350
# Queries:
#   HGETALL session:MNQ_20240115_NEWYORK
#   HINCRBY session:MNQ_20240115_NEWYORK volume 100  # Increment volume
#   HINCRBY session:MNQ_20240115_NEWYORK trades 1  # Increment trade count

# Pattern: sessions:active
# Type: Set
# Members: active session IDs
# TTL: None (managed dynamically)
# Example:
#   SADD sessions:active MNQ_20240115_NEWYORK
#   SREM sessions:active MNQ_20240115_NEWYORK
# Queries:
#   SMEMBERS sessions:active  # Get all active sessions
#   SISMEMBER sessions:active MNQ_20240115_NEWYORK  # Check if session is active

# ============================================
# SYMBOL MANAGEMENT
# ============================================

# Pattern: symbol:{symbol}:config
# Type: Hash
# Fields: exchange, description, tick_size, tick_value, contract_multiplier, currency, active, trading_hours, cbdr_support, priority, last_update
# TTL: None (persistent configuration)
# Example:
#   Key: symbol:MNQ:config
#   HSET symbol:MNQ:config exchange CME tick_size 0.25 tick_value 0.50 contract_multiplier 2.0 active true cbdr_support true priority 1
# Queries:
#   HGETALL symbol:MNQ:config

# Pattern: symbols:active
# Type: Set
# Members: active symbol names
# TTL: None
# Example:
#   SADD symbols:active MNQ
#   SADD symbols:active BTC
#   SREM symbols:active BTC  # Deactivate BTC
# Queries:
#   SMEMBERS symbols:active  # Get all active symbols
#   SCARD symbols:active  # Count active symbols

# ============================================
# DASHBOARD CACHE
# ============================================

# Pattern: dashboard:{symbol}:summary
# Type: String (JSON)
# Value: Complete dashboard summary JSON
# TTL: 30 seconds (real-time updates)
# Example:
#   Key: dashboard:MNQ:summary
#   SET dashboard:MNQ:summary '{"symbol": "MNQ", "last_price": 17503.00, "bias": "BULLISH", "active_cbdr": "PM", "recent_events": [...]}'
# Queries:
#   GET dashboard:MNQ:summary

# ============================================
# CLEANUP & MAINTENANCE
# ============================================

# Pattern: cleanup:last_run
# Type: String (timestamp)
# Value: Last cleanup timestamp
# TTL: None
# Example:
#   SET cleanup:last_run 1705334400000

# ============================================
# KEY NAMING CONVENTIONS
# ============================================

# 1. Use lowercase for key types (mbo, candle, session, etc.)
# 2. Use colon (:) as separator
# 3. Include symbol in most keys for multi-symbol support
# 4. Use session_id for time-series grouping
# 5. Use cbdr_window for CBDR-specific data
# 6. Timestamps always in milliseconds since epoch
# 7. Prices as doubles (e.g., 17500.25)
# 8. Sides as uppercase (BUY, SELL)
# 9. Event types as uppercase (ICEBERG, ABSORPTION, etc.)

# ============================================
# PERFORMANCE TIPS
# ============================================

# 1. Use pipelining for batch operations:
#    MULTI
#    ZADD mbo:MNQ:session 1705334400000 '...'
#    ZADD mbo:MNQ:session 1705334401000 '...'
#    EXEC

# 2. Use SCAN instead of KEYS in production:
#    SCAN 0 MATCH candle:MNQ:1m:closed:* COUNT 100

# 3. Monitor memory usage:
#    INFO memory
#    MEMORY USAGE candle:MNQ:1m:current

# 4. Check key expiration:
#    TTL session:MNQ_20240115_NEWYORK

# 5. Monitor slow queries:
#    SLOWLOG GET 10

# ============================================
# BACKUP & PERSISTENCE
# ============================================

# Redis persistence configuration (redis.conf):
# save 900 1      # Save after 900 seconds if at least 1 key changed
# save 300 10     # Save after 300 seconds if at least 10 keys changed
# save 60 10000   # Save after 60 seconds if at least 10000 keys changed

# AOF (Append Only File) for durability:
# appendonly yes
# appendfsync everysec

# ============================================
# MONITORING COMMANDS
# ============================================

# Check connection:
# PING

# Get all keys matching pattern (development only):
# KEYS mbo:MNQ:*

# Count keys:
# DBSIZE

# Get Redis info:
# INFO
# INFO stats
# INFO memory
# INFO replication

# Monitor commands in real-time:
# MONITOR

# Get key type:
# TYPE mbo:MNQ:session

# Check key existence:
# EXISTS mbo:MNQ:session

# Get all field names in hash:
# HKEYS symbol:MNQ:config
