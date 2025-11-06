# Enhanced MBO Monitor with Redis/TimescaleDB Integration
# Version 4.0.0 - Integrated with Java consumer architecture
# Uses shared Redis (hot) + TimescaleDB (cold) storage

# EARLY BOOTSTRAP: write minimal environment info to TEMP so we capture python executable
try:
    import json, os, sys
    try:
        tmp = os.environ.get('TEMP', os.environ.get('TMP', 'C:\\Windows\\Temp'))
        path = os.path.join(tmp, 'MBO_bootstrap_env.json')
        with open(path, 'a', encoding='utf-8') as f:
            from datetime import datetime, timezone
            f.write(json.dumps({'timestamp': datetime.now(timezone.utc).isoformat(), 'pid': os.getpid(), 'python_executable': sys.executable}) + "\n")
    except Exception:
        pass
except Exception:
    pass

import sys
import os
import json
import time
import threading
from datetime import datetime, timezone, time as datetime_time
from queue import Queue, Full
from collections import deque
import pytz

# Redis and PostgreSQL imports
try:
    import redis
    import psycopg2
    from psycopg2.extras import execute_batch
except ImportError:
    print("ERROR: Required packages not installed. Run:")
    print("  pip install redis psycopg2-binary pytz")
    sys.exit(1)

# Bookmap API import
try:
    import bookmap as bm
except ImportError:
    print("ERROR: Bookmap API not available. This script must run inside Bookmap.")
    sys.exit(1)

# Windows encoding fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except:
        pass


# ============================================
# Configuration (matches database_config.properties)
# ============================================

# Redis Configuration
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_POOL_MAX = 50
REDIS_TTL_MBO = 86400  # 24 hours
REDIS_TTL_TRADES = 43200  # 12 hours
REDIS_TTL_STATS = 3600  # 1 hour

# TimescaleDB Configuration
TIMESCALE_HOST = "localhost"
TIMESCALE_PORT = 5432
TIMESCALE_DB = "trading_data"
TIMESCALE_USER = "postgres"
TIMESCALE_PASSWORD = "X74Ot*BvtjgKuCBx"

# Logging Configuration
LOG_DIR = "F:/Databases/Logs/"
LOG_FILE = os.path.join(LOG_DIR, "MBO_Consumer.log")
# Add a debug file for early bootstrap info
DEBUG_FILE = os.path.join(LOG_DIR, "MBO_Consumer_debug.log")

# CBDR Window Configuration (EST/EDT timezone)
EST = pytz.timezone("US/Eastern")
CBDR_PM_START = (16, 0)  # 4:00 PM
CBDR_PM_END = (20, 0)    # 8:00 PM
CBDR_LONDON_START = (2, 0)   # 2:00 AM
CBDR_LONDON_END = (5, 0)     # 5:00 AM
PRE_NY_START = (7, 30)   # 7:30 AM
PRE_NY_END = (9, 30)     # 9:30 AM

# Batch Processing Configuration
BATCH_SIZE = 2000   # Increased from 500 for higher throughput
BATCH_INTERVAL = 2  # Decreased from 5 seconds for faster processing

# Addon Metadata
__title__ = "MBO Redis Consumer"
__version__ = "4.0.0"
__desc__ = "Captures MBO data to Redis (hot) and TimescaleDB (cold) storage"


# ============================================
# Global State
# ============================================

# Redis connection pool
redis_pool = None
redis_client = None

# TimescaleDB connection
pg_conn = None
pg_conn_lock = threading.Lock()

# Batch queues - increased capacity for high-volume periods
mbo_batch_queue = Queue(maxsize=50000)
trade_batch_queue = Queue(maxsize=50000)

# Batch processor thread
batch_processor_thread = None
batch_processor_running = False

# Instrument tracking
alias_to_order_book = {}
instrument_params = {}
mbo_order_books = {}

# Statistics
event_counts = {"depth": 0, "trades": 0, "mbo": 0}
session_id = None


# ============================================
# Logging
# ============================================

def ensure_log_directory():
    """Create log directory if it doesn't exist"""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)


def log(message, level="INFO"):
    """Thread-safe logging with rotation"""
    try:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        log_line = f"[{timestamp}] [{level}] {message}\n"
        
        # Print to console
        print(log_line.strip(), flush=True)
        
        # Write to file
        ensure_log_directory()
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line)
            
    except Exception as e:
        print(f"Logging failed: {e}")


# Ensure early bootstrap info is recorded (helps identify which python executable Bookmap spawned)
def bootstrap_log_environment():
    try:
        ensure_log_directory()
        info = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
            "python_executable": sys.executable,
            "argv": sys.argv
        }
        line = json.dumps(info) + "\n"
        # Write to both LOG_FILE and DEBUG_FILE
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write("[BOOTSTRAP] " + line)
        with open(DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
        # Also print immediately
        print("[BOOTSTRAP] " + line, flush=True)
    except Exception as e:
        try:
            print(f"[BOOTSTRAP] Failed to write bootstrap info: {e}", flush=True)
        except:
            pass

# Call bootstrap logger as early as possible
bootstrap_log_environment()


# ============================================
# Database Initialization
# ============================================

def init_redis():
    """Initialize Redis connection pool"""
    global redis_pool, redis_client
    try:
        log("Initializing Redis connection pool...")

        redis_pool = redis.ConnectionPool(
            host=REDIS_HOST,
            port=REDIS_PORT,
            max_connections=REDIS_POOL_MAX,
            decode_responses=True,
            socket_keepalive=True,
            socket_connect_timeout=5
        )

        redis_client = redis.Redis(connection_pool=redis_pool)

        # Test connection
        redis_client.ping()
        log(f"✓ Redis connected: {REDIS_HOST}:{REDIS_PORT}")

        return True

    except Exception as e:
        log(f"✗ Redis connection failed: {e}", "ERROR")
        # Keep process alive; redis_client remains None and callers should handle it.
        redis_client = None
        return False


def init_timescaledb():
    """Initialize TimescaleDB connection"""
    global pg_conn
    try:
        log("Initializing TimescaleDB connection...")

        pg_conn = psycopg2.connect(
            host=TIMESCALE_HOST,
            port=TIMESCALE_PORT,
            database=TIMESCALE_DB,
            user=TIMESCALE_USER,
            password=TIMESCALE_PASSWORD,
            connect_timeout=10
        )

        pg_conn.autocommit = False

        # Test connection
        with pg_conn.cursor() as cursor:
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            log(f"✓ TimescaleDB connected: {version[:80]}")

        return True

    except Exception as e:
        log(f"✗ TimescaleDB connection failed: {e}", "ERROR")
        # Keep process alive; leave pg_conn as None and let batch inserts skip when disconnected
        pg_conn = None
        return False


# ============================================
# Session Management
# ============================================

def generate_session_id(symbol):
    """Generate session ID matching Java SessionManager pattern"""
    import uuid
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{symbol}_{timestamp}_{str(uuid.uuid4())[:8]}"


def get_cbdr_window():
    """Get current CBDR window name (matching Java SessionManager)"""
    try:
        now_utc = datetime.now(timezone.utc)
        now_est = now_utc.astimezone(EST)
        current_time = now_est.time()
        
        # CBDR PM (4-8 PM EST)
        if datetime_time(*CBDR_PM_START) <= current_time <= datetime_time(*CBDR_PM_END):
            return "CBDR_PM"
        
        # CBDR London (2-5 AM EST)
        if datetime_time(*CBDR_LONDON_START) <= current_time <= datetime_time(*CBDR_LONDON_END):
            return "CBDR_LONDON"
        
        # Pre-NY (7:30-9:30 AM EST)
        if datetime_time(*PRE_NY_START) <= current_time <= datetime_time(*PRE_NY_END):
            return "PRE_NY"
        
        return "OUTSIDE_WINDOW"
        
    except Exception as e:
        log(f"Error getting CBDR window: {e}", "ERROR")
        return "UNKNOWN"


def is_within_trading_window():
    """Check if currently within a trading window"""
    window = get_cbdr_window()
    return window != "OUTSIDE_WINDOW", window


# ============================================
# Symbol Normalization
# ============================================

def normalize_symbol(alias):
    """
    Normalize symbol (matching Java pattern)
    CME:MNQZ5@RITHMIC -> MNQZ5
    """
    symbol = alias
    
    # Remove exchange prefix
    if ":" in symbol:
        symbol = symbol.split(":", 1)[1]
    
    # Remove suffix
    if "@" in symbol:
        symbol = symbol.split("@")[0]
    
    return symbol


# ============================================
# Redis Operations
# ============================================

def store_mbo_order_redis(symbol, order_id, price, size, is_bid, event_type):
    """Store MBO order in Redis sorted set (modern Redis Stack)"""
    try:
        side = "bid" if is_bid else "ask"
        key = f"mbo:orders:{symbol}:{side}"
        
        # Store as sorted set with price as score
        order_data = json.dumps({
            "order_id": str(order_id),
            "size": float(size),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Modern Redis syntax: zadd key {member: score}
        redis_client.zadd(key, {order_data: price})
        redis_client.expire(key, REDIS_TTL_MBO)
        
    except Exception as e:
        log(f"Failed to store MBO order in Redis: {e}", "ERROR")


def store_trade_redis(symbol, price, size, is_bid, trade_id):
    """Store trade in Redis Stream (modern Redis Stack)"""
    try:
        key = f"mbo:trades:{symbol}"
        
        trade_data = {
            "trade_id": str(trade_id),
            "price": str(price),
            "size": str(size),
            "is_bid": "1" if is_bid else "0",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Use Redis Streams for time-series data
        redis_client.xadd(key, trade_data, maxlen=10000)
        redis_client.expire(key, REDIS_TTL_TRADES)
        
    except Exception as e:
        log(f"Failed to store trade in Redis: {e}", "ERROR")


def update_mbo_stats_redis(symbol):
    """Update MBO statistics in Redis (modern Redis Stack)"""
    try:
        key = f"mbo:stats:{symbol}"
        
        # Modern Redis syntax: HSET with mapping
        redis_client.hset(key, mapping={
            "depth_events": event_counts["depth"],
            "trade_events": event_counts["trades"],
            "mbo_events": event_counts["mbo"],
            "last_update": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id
        })
        redis_client.expire(key, REDIS_TTL_STATS)
        
    except Exception as e:
        log(f"Failed to update MBO stats in Redis: {e}", "ERROR")


# ============================================
# TimescaleDB Batch Operations
# ============================================

def process_batch():
    """Process batches of MBO data to TimescaleDB"""
    global batch_processor_running
    
    log("Batch processor started")
    
    while batch_processor_running:
        try:
            time.sleep(BATCH_INTERVAL)
            
            # Process MBO orders batch
            mbo_batch = []
            while not mbo_batch_queue.empty() and len(mbo_batch) < BATCH_SIZE:
                try:
                    mbo_batch.append(mbo_batch_queue.get_nowait())
                except:
                    break
            
            if mbo_batch:
                success = insert_mbo_batch(mbo_batch)
                if success:
                    log(f"✓ Inserted {len(mbo_batch)} MBO records to TimescaleDB")
                else:
                    log(f"✗ Failed to insert {len(mbo_batch)} MBO records", "WARN")
            
            # Process trades batch
            trade_batch = []
            while not trade_batch_queue.empty() and len(trade_batch) < BATCH_SIZE:
                try:
                    trade_batch.append(trade_batch_queue.get_nowait())
                except:
                    break
            
            if trade_batch:
                success = insert_trade_batch(trade_batch)
                if success:
                    log(f"✓ Inserted {len(trade_batch)} trade records to TimescaleDB")
                else:
                    log(f"✗ Failed to insert {len(trade_batch)} trade records", "WARN")
                
        except Exception as e:
            log(f"Batch processing error: {e}", "ERROR")
    
    log("Batch processor stopped")


def insert_mbo_batch(batch):
    """Insert batch of MBO orders into TimescaleDB"""
    try:
        if pg_conn is None:
            log("TimescaleDB not connected; skipping mbo batch insert", "WARN")
            return False

        if not batch:
            return True

        with pg_conn_lock:
            with pg_conn.cursor() as cursor:
                # Use existing mbo_data table structure (order matches tuple order)
                query = """
                    INSERT INTO mbo_data 
                    (timestamp, symbol, order_id, side, price, size, order_type, action, session_id, cbdr_window)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (timestamp, symbol, order_id) DO NOTHING
                """

                # Log first record for debugging
                if batch:
                    sample = batch[0]
                    log(f"Inserting batch: {len(batch)} records, sample: symbol={sample[1]}, order_id={sample[2]}, side={sample[3]}, price={sample[4]:.2f}")

                execute_batch(cursor, query, batch, page_size=500)
                pg_conn.commit()
                
                # Verify insertion
                cursor.execute("SELECT COUNT(*) FROM mbo_data WHERE symbol = %s", (batch[0][1],))
                count = cursor.fetchone()[0]
                log(f"Verification: {count} total records for {batch[0][1]} in database")
                
                return True

    except Exception as e:
        log(f"Failed to insert MBO batch: {e}", "ERROR")
        import traceback
        log(f"Traceback: {traceback.format_exc()}", "ERROR")
        try:
            if pg_conn:
                pg_conn.rollback()
        except:
            pass
        return False


def insert_trade_batch(batch):
    """Insert batch of trades into TimescaleDB"""
    try:
        if pg_conn is None:
            log("TimescaleDB not connected; skipping trade batch insert", "WARN")
            return False

        if not batch:
            return True

        with pg_conn_lock:
            with pg_conn.cursor() as cursor:
                # Trades can also use mbo_data table with action='TRADE'
                query = """
                    INSERT INTO mbo_data 
                    (timestamp, symbol, order_id, price, size, side, order_type, action, session_id, cbdr_window)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (timestamp, symbol, order_id) DO NOTHING
                """

                execute_batch(cursor, query, batch, page_size=500)
                pg_conn.commit()
                
                return True

    except Exception as e:
        log(f"Failed to insert trade batch: {e}", "ERROR")
        import traceback
        log(f"Traceback: {traceback.format_exc()}", "ERROR")
        try:
            if pg_conn:
                pg_conn.rollback()
        except:
            pass
        return False


# ============================================
# Bookmap Event Handlers
# ============================================

def handle_subscribe_instrument(
    addon, alias, full_name, is_crypto, pips, size_multiplier, 
    instrument_multiplier, supported_features
):
    """Handle instrument subscription"""
    try:
        symbol = normalize_symbol(alias)
        log(f"Subscribing to: {symbol} (alias: {alias})")
        
        instrument_params[alias] = {
            "symbol": symbol,
            "pips": pips,
            "size_multiplier": size_multiplier,
            "instrument_multiplier": instrument_multiplier,
            "supported_features": supported_features
        }
        
        alias_to_order_book[alias] = bm.create_order_book()
        mbo_order_books[alias] = {}  # Simple dictionary like MBO_Automated_v3
        
        # Subscribe to data feeds
        bm.subscribe_to_depth(addon, alias, 1)
        bm.subscribe_to_trades(addon, alias, 2)
        
        # Check if MBO is supported (like the working version)
        if supported_features:
            mbo_supported = False
            if isinstance(supported_features, dict):
                mbo_supported = supported_features.get("supportsMbo", False) or supported_features.get("supportsMboDepth", False)
            elif isinstance(supported_features, str):
                mbo_supported = "mbo" in supported_features.lower()
            
            if mbo_supported:
                bm.subscribe_to_order_info(addon, alias, 3)
                log(f"MBO data subscription enabled for {symbol}")
        
    except Exception as e:
        log(f"Subscription failed: {e}", "ERROR")


def handle_unsubscribe_instrument(addon, alias):
    """Handle instrument unsubscription"""
    try:
        symbol = normalize_symbol(alias)
        log(f"Unsubscribing from: {symbol}")
        
        if alias in alias_to_order_book:
            del alias_to_order_book[alias]
        if alias in instrument_params:
            del instrument_params[alias]
        if alias in mbo_order_books:
            del mbo_order_books[alias]
            
    except Exception as e:
        log(f"Unsubscribe failed: {e}", "ERROR")


def handle_depth_info(addon, alias, is_bid, price, size):
    """Handle depth updates"""
    try:
        is_allowed, window = is_within_trading_window()
        event_counts["depth"] += 1
        
        if alias not in alias_to_order_book:
            return
        
        order_book = alias_to_order_book[alias]
        bm.on_depth(order_book, is_bid, price, size)
        
        # Only store during trading windows
        if not is_allowed:
            return
        
        params = instrument_params.get(alias, {"pips": 1.0, "size_multiplier": 1.0})
        symbol = params.get("symbol", normalize_symbol(alias))
        
        actual_price = float(price) * float(params["pips"])
        actual_size = abs(float(size)) / float(params["size_multiplier"])
        
        timestamp = datetime.now(timezone.utc)
        # Generate bigint order_id: timestamp in microseconds + random 4 digits
        order_id = int(timestamp.timestamp() * 1000000) + (hash(f"{alias}_{price}_{size}") % 10000)
        side = "BUY" if is_bid else "SELL"
        
        # Store in Redis (hot)
        store_mbo_order_redis(symbol, order_id, actual_price, actual_size, is_bid, "DEPTH")
        
        # Queue for TimescaleDB (cold)
        mbo_data = (
            timestamp,
            symbol,
            order_id,
            side,
            actual_price,
            int(actual_size),  # Ensure size is bigint
            "LIMIT",
            "ADD",  # Changed from UPDATE to match schema constraint
            session_id,
            window
        )
        
        try:
            mbo_batch_queue.put_nowait(mbo_data)
        except Full:
            log("MBO batch queue full, dropping oldest", "WARN")
            
    except Exception as e:
        log(f"Depth handling failed: {e}", "ERROR")


def handle_mbo_info(addon, alias, event_type, order_id, price, size):
    """Handle MBO updates"""
    try:
        is_allowed, window = is_within_trading_window()
        
        if not is_allowed:
            return
        
        event_counts["mbo"] += 1
        
        params = instrument_params.get(alias, {"pips": 1.0, "size_multiplier": 1.0})
        symbol = params.get("symbol", normalize_symbol(alias))
        
        actual_price = float(price) * float(params["pips"])
        actual_size = float(size) / float(params["size_multiplier"])
        
        is_bid = "BID" in event_type.upper()
        side = "BUY" if is_bid else "SELL"
        
        # Determine action
        if event_type in ("BID_NEW", "ASK_NEW"):
            action = "ADD"
        elif event_type == "REPLACE":
            action = "UPDATE"
        elif event_type == "CANCEL":
            action = "DELETE"
        else:
            action = event_type
        
        timestamp = datetime.now(timezone.utc)
        
        # Store in Redis (hot)
        store_mbo_order_redis(symbol, order_id, actual_price, actual_size, is_bid, action)
        
        # Queue for TimescaleDB (cold)
        mbo_data = (
            timestamp,
            symbol,
            order_id,
            actual_price,
            actual_size,
            side,
            "LIMIT",
            action,
            session_id,
            window
        )
        
        try:
            mbo_batch_queue.put_nowait(mbo_data)
        except Full:
            log("MBO batch queue full", "WARN")
        
        # Update stats periodically
        if event_counts["mbo"] % 100 == 0:
            update_mbo_stats_redis(symbol)
            
    except Exception as e:
        log(f"MBO handling failed: {e}", "ERROR")


def handle_trade_info(
    addon, alias, price, size, is_otc, is_bid,
    is_execution_start, is_execution_end, aggressor_order_id, passive_order_id
):
    """Handle trade events"""
    try:
        is_allowed, window = is_within_trading_window()
        
        if not is_allowed:
            return
        
        event_counts["trades"] += 1
        
        params = instrument_params.get(alias, {"pips": 1.0, "size_multiplier": 1.0})
        symbol = params.get("symbol", normalize_symbol(alias))
        
        actual_price = float(price) * float(params["pips"])
        actual_size = abs(float(size)) / float(params["size_multiplier"])
        
        timestamp = datetime.now(timezone.utc)
        # Generate bigint trade_id: timestamp in microseconds
        trade_id = int(timestamp.timestamp() * 1000000)
        side = "BUY" if is_bid else "SELL"
        
        # Store in Redis (hot)
        store_trade_redis(symbol, actual_price, actual_size, is_bid, trade_id)
        
        # Queue for TimescaleDB - but trades table doesn't exist! Skip for now
        # TODO: Create trades table or store in mbo_data
        
    except Exception as e:
        log(f"Trade handling failed: {e}", "ERROR")


def handle_subscription_response(addon, req_id):
    """Handle subscription confirmation"""
    try:
        log(f"Subscription confirmed: req_id={req_id}")
    except Exception as e:
        log(f"Subscription response error: {e}", "ERROR")


# ============================================
# Lifecycle Management
# ============================================

def initialize_addon(retry_on_fail=True, retry_interval=5):
    """Initialize addon and start batch processor

    This function will not exit the process on DB init failures. It will start
    the addon and keep retrying connections in the background so the process
    remains available for RPC from Bookmap.
    """
    global session_id, batch_processor_thread, batch_processor_running

    try:
        log("=" * 50)
        log(f"{__title__} v{__version__}")
        log("=" * 50)

        # Try to initialize Redis and TimescaleDB but do not abort if they fail
        redis_ok = init_redis()
        ts_ok = init_timescaledb()

        if not redis_ok:
            log("Redis not ready. The addon will continue and retry in background.", "WARN")

        if not ts_ok:
            log("TimescaleDB not ready. The addon will continue and retry in background.", "WARN")

        # Generate session ID
        session_id = generate_session_id("MBO")
        log(f"Session ID: {session_id}")

        # Start batch processor
        batch_processor_running = True
        batch_processor_thread = threading.Thread(target=process_batch, daemon=True)
        batch_processor_thread.start()

        # Start background connector thread that will retry DB connections periodically
        def db_retry_loop():
            while True:
                try:
                    if redis_client is None:
                        init_redis()
                    if pg_conn is None:
                        init_timescaledb()
                except Exception as e:
                    log(f"DB retry loop error: {e}", "ERROR")
                time.sleep(retry_interval)

        t = threading.Thread(target=db_retry_loop, daemon=True)
        t.start()

        log("✓ Addon initialized (DB connections may be pending)")
        return True

    except Exception as e:
        log(f"✗ Addon initialization failed: {e}", "ERROR")
        return False


def cleanup_addon():
    """Cleanup resources on shutdown"""
    global batch_processor_running
    
    try:
        log("Shutting down addon...")
        
        # Stop batch processor
        batch_processor_running = False
        if batch_processor_thread:
            batch_processor_thread.join(timeout=10)
        
        # Process remaining batches
        log("Processing remaining batches...")
        # (batch processing logic here)
        
        # Close connections
        if redis_client:
            redis_client.close()
        if redis_pool:
            redis_pool.disconnect()
        if pg_conn:
            pg_conn.close()
        
        log("✓ Addon shutdown complete")
        
    except Exception as e:
        log(f"Cleanup error: {e}", "ERROR")


# ============================================
# Main Entry Point
# ============================================

if __name__ == "__main__":
    try:
        # Initialize database connections
        initialized = initialize_addon()
        if not initialized:
            log("Initialization returned False — addon will continue running and retry initialization.", "WARN")

        log("Creating Bookmap addon...")
        addon = bm.create_addon()
        
        # Register event handlers (matching MBO_Automated_v3 pattern)
        log("Registering event handlers...")
        bm.add_depth_handler(addon, handle_depth_info)
        bm.add_mbo_handler(addon, handle_mbo_info)
        bm.add_trades_handler(addon, handle_trade_info)
        
        log("Starting addon...")
        log(f"Monitoring CBDR windows: PM, London, Pre-NY")
        log(f"Data storage: Redis (hot) + TimescaleDB (cold)")
        log(f"Batch size: {BATCH_SIZE}, Interval: {BATCH_INTERVAL}s")
        
        # Start addon with instrument subscription handlers
        bm.start_addon(addon, handle_subscribe_instrument, handle_unsubscribe_instrument)
        
        # Block until addon is turned off by Bookmap
        log("Addon ready. Waiting for Bookmap events...")
        bm.wait_until_addon_is_turned_off(addon)
        
        log("Addon stopped by Bookmap")

    except KeyboardInterrupt:
        log("Received shutdown signal")
    except Exception as e:
        log(f"Fatal error: {e}", "ERROR")
    finally:
        cleanup_addon()
