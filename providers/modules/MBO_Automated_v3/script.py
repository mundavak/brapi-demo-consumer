# Enhanced Market Monitor with MBO Support for Bookmap
# v3.0.1 - Fixed Unicode encoding issues for Windows
# Thread-safe version for JAR compilation

import bookmap as bm
import sqlite3
import json
from datetime import datetime, timezone, time as datetime_time
import os
import sys
import pytz
from pathlib import Path

# ✅ FIX ENCODING ISSUES FOR WINDOWS CONSOLE
if sys.platform == "win32":
    try:
        # Try to set UTF-8 encoding
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except:
        # If reconfigure fails, just use ASCII-safe output
        pass


# Safe print function that won't crash on encoding errors
def safe_print(message):
    """Print with encoding error handling"""
    try:
        print(message, flush=True)
    except UnicodeEncodeError:
        # Strip emojis and special characters
        ascii_message = message.encode("ascii", errors="ignore").decode("ascii")
        print(ascii_message, flush=True)
    except Exception as e:
        # Last resort: just print to debug file
        try:
            with open(DEBUG_FILE, "a") as f:
                f.write(str(message) + "\n")
        except:
            pass


# Addon metadata
__title__ = "Enhanced Market Monitor with MBO"
__version__ = "3.0.1"
__desc__ = (
    "Monitors order book updates, trades, and MBO data with real-time price tracking"
)

# Configuration
DB_PATH = r"F:\TradingAgent\enhanced_market_monitor_mbo.db"
DEBUG_FILE = r"F:\TradingAgent\enhanced_monitor_mbo_debug.log"
PRICE_CACHE_FILE = r"F:\TradingAgent\live_prices.json"

# Trading Window Configuration (EST/EDT timezone)
EST = pytz.timezone("US/Eastern")

# CBDR Window 1: PM Session / Asian Open (4:00 PM - 8:00 PM EST)
CBDR_PM_START_HOUR = 16
CBDR_PM_START_MINUTE = 0
CBDR_PM_END_HOUR = 20
CBDR_PM_END_MINUTE = 0

# CBDR Window 2: London Kill Zone (2:00 AM - 5:00 AM EST)
CBDR_LONDON_START_HOUR = 2
CBDR_LONDON_START_MINUTE = 0
CBDR_LONDON_END_HOUR = 5
CBDR_LONDON_END_MINUTE = 0

# Pre-NY Open Window (7:30 AM - 9:30 AM EST)
PRE_NY_START_HOUR = 7
PRE_NY_START_MINUTE = 30
PRE_NY_END_HOUR = 9
PRE_NY_END_MINUTE = 30

# Global state (thread-safe for Bookmap callbacks)
alias_to_order_book = {}
instrument_params = {}
mbo_order_books = {}
mbo_update_sequence = 0

# IN-MEMORY PRICE CACHE (Best Practice)
live_prices = {}
price_update_counter = 0

# Event counters for debugging
event_counts = {"depth": 0, "trades": 0, "mbo": 0}
filtered_counts = {"depth": 0, "trades": 0, "mbo": 0}


def log_debug(message, error=None):
    """Simple logging function with encoding safety"""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    log_message = "[%s] %s" % (timestamp, message)

    if error:
        log_message = "%s: %s" % (log_message, str(error))

    safe_print(log_message)

    try:
        with open(DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(log_message + "\n")
    except:
        pass


def normalize_symbol(alias):
    """
    Normalize symbol by removing exchange prefix and suffix
    Examples:
        CME:MNQZ5@RITHMIC -> MNQZ5
        CME:MNQZ5.CME -> MNQZ5.CME
        MNQZ5.CME@RITHMIC -> MNQZ5.CME
    """
    symbol = alias

    # Remove exchange prefix (e.g., "CME:")
    if ":" in symbol:
        parts = symbol.split(":", 1)
        symbol = parts[1]

    # Remove suffix (e.g., "@RITHMIC")
    if "@" in symbol:
        symbol = symbol.split("@")[0]

    return symbol


def update_price_cache_file():
    """
    Write in-memory prices to JSON file for dashboard access
    Called periodically (not on every tick) to reduce I/O
    """
    global price_update_counter

    try:
        # Only write every 10 updates to reduce I/O overhead
        price_update_counter += 1
        if price_update_counter % 10 != 0:
            return

        with open(PRICE_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(live_prices, f, indent=2)

    except Exception as e:
        log_debug("Failed to update price cache file: %s" % str(e))


def update_live_price(alias, mid_price, best_bid, best_ask, source="depth"):
    """
    Update in-memory live price cache (optimized for speed)
    This is the PRIMARY method for live price tracking
    """
    try:
        normalized_symbol = normalize_symbol(alias)
        timestamp = datetime.now(timezone.utc).isoformat()

        price_data = {
            "mid": round(mid_price, 2),
            "bid": round(best_bid, 2),
            "ask": round(best_ask, 2),
            "spread": round(best_ask - best_bid, 2),
            "timestamp": timestamp,
            "source": source,
            "alias": alias,
        }

        # Store with both full alias and normalized symbol for flexible access
        live_prices[alias] = price_data
        live_prices[normalized_symbol] = price_data

        # Periodically write to shared file for dashboard
        update_price_cache_file()

    except Exception as e:
        log_debug("Failed to update live price: %s" % str(e))


def is_within_trading_window():
    """Check if current time is within allowed trading windows (EST/EDT)"""
    try:
        now_utc = datetime.now(timezone.utc)
        now_est = now_utc.astimezone(EST)
        current_time = now_est.time()

        # CBDR Window 1: PM Session / Asian Open (4:00 PM - 8:00 PM EST)
        cbdr_pm_start = datetime_time(CBDR_PM_START_HOUR, CBDR_PM_START_MINUTE)
        cbdr_pm_end = datetime_time(CBDR_PM_END_HOUR, CBDR_PM_END_MINUTE)

        if cbdr_pm_start <= current_time <= cbdr_pm_end:
            return True, "CBDR_PM_ASIAN"

        # CBDR Window 2: London Kill Zone (2:00 AM - 5:00 AM EST)
        cbdr_london_start = datetime_time(
            CBDR_LONDON_START_HOUR, CBDR_LONDON_START_MINUTE
        )
        cbdr_london_end = datetime_time(CBDR_LONDON_END_HOUR, CBDR_LONDON_END_MINUTE)

        if cbdr_london_start <= current_time <= cbdr_london_end:
            return True, "CBDR_LONDON"

        # Pre-NY Open Window (7:30 AM - 9:30 AM EST)
        pre_ny_start = datetime_time(PRE_NY_START_HOUR, PRE_NY_START_MINUTE)
        pre_ny_end = datetime_time(PRE_NY_END_HOUR, PRE_NY_END_MINUTE)

        if pre_ny_start <= current_time <= pre_ny_end:
            return True, "PRE_NY_OPEN"

        return False, "OUTSIDE_WINDOW"

    except Exception as e:
        log_debug("Error checking trading window: %s" % str(e))
        return False, "ERROR"


def get_db_connection():
    """Create a new database connection for each operation (thread-safe)"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return conn


def init_database():
    """Initialize database with all required tables"""
    try:
        log_debug("Initializing database at %s" % DB_PATH)

        db_dir = os.path.dirname(DB_PATH)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                timestamp TEXT,
                symbol TEXT,
                side TEXT,
                price REAL,
                quantity REAL,
                order_id TEXT PRIMARY KEY,
                exchange TEXT,
                is_bid INTEGER
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                timestamp TEXT,
                symbol TEXT,
                price REAL,
                size REAL,
                is_buy_aggressor INTEGER,
                trade_id TEXT PRIMARY KEY,
                exchange TEXT,
                is_otc INTEGER,
                is_execution_start INTEGER,
                is_execution_end INTEGER,
                aggressor_order_id TEXT,
                passive_order_id TEXT
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS subscription_responses (
                timestamp TEXT,
                req_id INTEGER,
                alias TEXT,
                data_type TEXT,
                success INTEGER,
                response_id TEXT PRIMARY KEY
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS mbo_orders (
                timestamp TEXT,
                symbol TEXT,
                order_id TEXT PRIMARY KEY,
                price REAL,
                size REAL,
                is_bid INTEGER,
                event_type TEXT,
                exchange TEXT,
                update_sequence INTEGER
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS mbo_executions (
                timestamp TEXT,
                symbol TEXT,
                order_id TEXT,
                price REAL,
                executed_size REAL,
                remaining_size REAL,
                is_bid INTEGER,
                exchange TEXT,
                execution_id TEXT PRIMARY KEY
            )
        """
        )

        try:
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_mbo_symbol ON mbo_orders(symbol)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_mbo_timestamp ON mbo_orders(timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_trade_symbol ON trades(symbol)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_order_symbol ON orders(symbol)"
            )
        except:
            pass

        conn.commit()
        conn.close()
        log_debug("Database initialized successfully")

    except Exception as e:
        log_debug("Database initialization failed", e)
        raise


def store_order(timestamp, symbol, side, price, quantity, order_id, exchange, is_bid):
    """Store order data with new connection per call"""
    conn = None
    try:
        symbol = normalize_symbol(symbol) if "@" in symbol or ":" in symbol else symbol

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (timestamp, symbol, side, price, quantity, order_id, exchange, int(is_bid)),
        )
        conn.commit()
    except Exception as e:
        log_debug("Failed to store order", e)
    finally:
        if conn:
            conn.close()


def store_trade(
    timestamp,
    symbol,
    price,
    size,
    is_buy_aggressor,
    trade_id,
    exchange,
    is_otc,
    is_execution_start,
    is_execution_end,
    aggressor_order_id,
    passive_order_id,
):
    """Store trade data with new connection per call"""
    conn = None
    try:
        symbol = normalize_symbol(symbol) if "@" in symbol or ":" in symbol else symbol

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO trades VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                timestamp,
                symbol,
                price,
                size,
                int(is_buy_aggressor),
                trade_id,
                exchange,
                int(is_otc),
                int(is_execution_start),
                int(is_execution_end),
                aggressor_order_id,
                passive_order_id,
            ),
        )
        conn.commit()
    except Exception as e:
        log_debug("Failed to store trade", e)
    finally:
        if conn:
            conn.close()


def store_mbo_event(event_data):
    """Store MBO event with new connection per call"""
    global mbo_update_sequence
    conn = None

    try:
        symbol = event_data.get("symbol", "")
        symbol = normalize_symbol(symbol) if "@" in symbol or ":" in symbol else symbol

        conn = get_db_connection()
        cursor = conn.cursor()
        event_type = event_data.get("type")

        if event_type in ["add", "update", "delete"]:
            mbo_update_sequence += 1
            cursor.execute(
                "INSERT OR REPLACE INTO mbo_orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_data["timestamp"],
                    symbol,
                    str(event_data["order_id"]),
                    event_data["price"],
                    event_data["size"],
                    int(event_data["is_bid"]),
                    event_type,
                    event_data["exchange"],
                    mbo_update_sequence,
                ),
            )

        elif event_type == "execution":
            execution_id = "%s_%s_%d" % (
                event_data["order_id"],
                event_data["timestamp"].replace(":", "").replace(".", ""),
                mbo_update_sequence,
            )
            cursor.execute(
                "INSERT INTO mbo_executions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    event_data["timestamp"],
                    symbol,
                    str(event_data["order_id"]),
                    event_data["price"],
                    event_data["executed_size"],
                    event_data["remaining_size"],
                    int(event_data["is_bid"]),
                    event_data["exchange"],
                    execution_id,
                ),
            )

        conn.commit()

    except Exception as e:
        log_debug("Failed to store MBO event", e)
    finally:
        if conn:
            conn.close()


def store_response(timestamp, req_id, alias, data_type, success):
    """Store subscription response with new connection per call"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        response_id = "%s_%d_%s" % (data_type, req_id, timestamp.replace(":", ""))
        cursor.execute(
            "INSERT OR REPLACE INTO subscription_responses VALUES (?, ?, ?, ?, ?, ?)",
            (timestamp, req_id, alias, data_type, int(success), response_id),
        )
        conn.commit()
    except Exception as e:
        log_debug("Failed to store response", e)
    finally:
        if conn:
            conn.close()


def handle_subscribe_instrument(
    addon,
    alias,
    full_name,
    is_crypto,
    pips,
    size_multiplier,
    instrument_multiplier,
    supported_features,
):
    """Handle instrument subscription"""
    try:
        log_debug(
            "Subscribing to: %s (pips=%f, size_mult=%f)"
            % (alias, pips, size_multiplier)
        )

        instrument_params[alias] = {
            "pips": pips,
            "size_multiplier": size_multiplier,
            "instrument_multiplier": instrument_multiplier,
            "supported_features": supported_features,
        }

        alias_to_order_book[alias] = bm.create_order_book()
        mbo_order_books[alias] = {}

        bm.subscribe_to_depth(addon, alias, 1)
        log_debug("Depth subscription requested")

        bm.subscribe_to_trades(addon, alias, 2)
        log_debug("Trades subscription requested")

        if supported_features:
            mbo_supported = False
            if isinstance(supported_features, dict):
                mbo_supported = supported_features.get("mbo", False)
            elif isinstance(supported_features, str):
                mbo_supported = "mbo" in supported_features.lower()

            if mbo_supported:
                bm.subscribe_to_mbo(addon, alias, 3)
                log_debug("MBO subscription requested")
            else:
                log_debug("MBO not supported for this instrument")

    except Exception as e:
        log_debug("Subscription failed", e)


def handle_unsubscribe_instrument(addon, alias):
    """Handle instrument unsubscription"""
    try:
        log_debug("Unsubscribing from: %s" % alias)

        if alias in alias_to_order_book:
            del alias_to_order_book[alias]
        if alias in instrument_params:
            del instrument_params[alias]
        if alias in mbo_order_books:
            del mbo_order_books[alias]
        # DISABLED: No longer tracking live prices
        # if alias in live_prices:
        #     del live_prices[alias]

    except Exception as e:
        log_debug("Unsubscribe failed", e)


def handle_depth_info(addon, alias, is_bid, price_level, size_level):
    """
    Handle aggregated depth updates with optimized price tracking
    BEST PRACTICE: Use bm.get_bbo() for live price access
    """
    try:
        is_allowed, window_name = is_within_trading_window()
        event_counts["depth"] += 1

        if event_counts["depth"] <= 5:
            log_debug(
                "Depth event #%d [%s]: alias=%s, is_bid=%s, price=%s, size=%s"
                % (
                    event_counts["depth"],
                    window_name,
                    alias,
                    is_bid,
                    price_level,
                    size_level,
                )
            )

        # Update order book
        if alias not in alias_to_order_book:
            alias_to_order_book[alias] = bm.create_order_book()

        order_book = alias_to_order_book[alias]
        bm.on_depth(order_book, is_bid, price_level, size_level)

        params = instrument_params.get(alias, {"pips": 1.0, "size_multiplier": 1.0})

        # OPTIMIZED: Get BBO directly from order book (fastest method)
        try:
            bbos = bm.get_bbo(order_book)
            if bbos and bbos[0] and bbos[1]:
                (best_bid_level, _), (best_ask_level, _) = bbos

                # Convert to actual prices
                best_bid = float(best_bid_level) * float(params["pips"])
                best_ask = float(best_ask_level) * float(params["pips"])
                mid_price = (best_bid + best_ask) / 2

                # Update in-memory cache (no database I/O)
                # update_live_price(alias, mid_price, best_bid, best_ask, "depth")  # DISABLED: No longer pulling current price

                # Log every 100 updates for monitoring
                if event_counts["depth"] % 100 == 0:
                    log_debug(
                        "[PRICE] Live Price #%d: %s = $%.2f (bid: $%.2f, ask: $%.2f, spread: $%.2f)"
                        % (
                            event_counts["depth"],
                            normalize_symbol(alias),
                            mid_price,
                            best_bid,
                            best_ask,
                            best_ask - best_bid,
                        )
                    )
        except Exception as e:
            log_debug("Error getting BBO: %s" % str(e))

        # Skip database storage if outside trading window
        if not is_allowed:
            filtered_counts["depth"] += 1
            if filtered_counts["depth"] % 1000 == 0:
                log_debug(
                    "Filtered %d depth events (outside trading window)"
                    % filtered_counts["depth"]
                )
            return

        # Store orders to database (only during trading windows)
        actual_price = float(price_level) * float(params["pips"])
        actual_size = (
            abs(float(size_level)) / float(params["size_multiplier"])
            if params["size_multiplier"] > 0
            else abs(size_level)
        )

        if ":" in alias:
            parts = alias.split(":", 1)
            exchange = parts[0]
            symbol = parts[1]
        else:
            exchange = ""
            symbol = alias

        timestamp = datetime.now(timezone.utc).isoformat()
        order_id = "%s_%s_%f_%s" % (
            exchange,
            symbol,
            actual_price,
            timestamp.replace(":", ""),
        )
        side = "BUY" if is_bid else "SELL"

        store_order(
            timestamp,
            symbol,
            side,
            actual_price,
            actual_size,
            order_id,
            exchange,
            is_bid,
        )

    except Exception as e:
        log_debug("Depth handling failed", e)


def handle_mbo_info(addon, alias, event_type, order_id, price_level, size_level):
    """Handle MBO updates with time filtering"""
    try:
        is_allowed, window_name = is_within_trading_window()

        if not is_allowed:
            filtered_counts["mbo"] += 1
            if filtered_counts["mbo"] % 1000 == 0:
                log_debug(
                    "Filtered %d MBO events (outside trading window)"
                    % filtered_counts["mbo"]
                )
            return

        event_counts["mbo"] = event_counts.get("mbo", 0) + 1

        if alias not in mbo_order_books:
            mbo_order_books[alias] = {}

        is_bid = "BID" in event_type.upper()

        if ":" in alias:
            parts = alias.split(":", 1)
            exchange = parts[0]
            symbol = parts[1]
        else:
            exchange = ""
            symbol = alias

        timestamp = datetime.now(timezone.utc).isoformat()

        if event_type == "CANCEL":
            old_price = 0.0
            old_size = 0.0

            if order_id in mbo_order_books[alias]:
                old_order = mbo_order_books[alias][order_id]
                old_price = old_order.get("price", 0.0)
                old_size = old_order.get("size", 0.0)
                del mbo_order_books[alias][order_id]

            store_mbo_event(
                {
                    "type": "delete",
                    "timestamp": timestamp,
                    "symbol": symbol,
                    "order_id": order_id,
                    "price": old_price,
                    "size": old_size,
                    "is_bid": is_bid,
                    "exchange": exchange,
                }
            )
            return

        params = instrument_params.get(alias, {"pips": 1.0, "size_multiplier": 1.0})

        if event_counts["mbo"] <= 10:
            log_debug(
                "MBO RAW #%d [%s]: event=%s oid=%s price_lvl=%s size_lvl=%s"
                % (
                    event_counts["mbo"],
                    window_name,
                    event_type,
                    order_id,
                    price_level,
                    size_level,
                )
            )

        if not isinstance(price_level, (int, float)):
            log_debug(
                "ERROR: price_level is not numeric! type=%s value=%s"
                % (type(price_level), price_level)
            )
            return

        if not isinstance(size_level, (int, float)):
            log_debug(
                "ERROR: size_level is not numeric! type=%s value=%s"
                % (type(size_level), size_level)
            )
            return

        actual_price = float(price_level) * float(params["pips"])
        actual_size = (
            float(size_level) / float(params["size_multiplier"])
            if params["size_multiplier"] > 0
            else float(size_level)
        )

        if event_type in ("BID_NEW", "ASK_NEW"):
            action = "add"
            mbo_order_books[alias][order_id] = {
                "price": actual_price,
                "size": actual_size,
                "is_bid": is_bid,
                "event_type": event_type,
                "price_level": price_level,
            }

        elif event_type == "REPLACE":
            action = "update"
            if order_id in mbo_order_books[alias]:
                old_order = mbo_order_books[alias][order_id]
                old_size = old_order.get("size", 0)

                if actual_size < old_size:
                    executed_size = old_size - actual_size
                    store_mbo_event(
                        {
                            "type": "execution",
                            "timestamp": timestamp,
                            "symbol": symbol,
                            "order_id": order_id,
                            "price": actual_price,
                            "executed_size": executed_size,
                            "remaining_size": actual_size,
                            "is_bid": is_bid,
                            "exchange": exchange,
                        }
                    )

                mbo_order_books[alias][order_id] = {
                    "price": actual_price,
                    "size": actual_size,
                    "is_bid": is_bid,
                    "event_type": event_type,
                    "price_level": price_level,
                }
            else:
                action = "add"
                mbo_order_books[alias][order_id] = {
                    "price": actual_price,
                    "size": actual_size,
                    "is_bid": is_bid,
                    "event_type": event_type,
                    "price_level": price_level,
                }
        else:
            action = "unknown"
            log_debug("Unknown MBO event type: %s" % event_type)
            return

        store_mbo_event(
            {
                "type": action,
                "timestamp": timestamp,
                "symbol": symbol,
                "order_id": order_id,
                "price": actual_price,
                "size": actual_size,
                "is_bid": is_bid,
                "exchange": exchange,
            }
        )

    except Exception as e:
        log_debug("MBO handling failed: %s" % str(e))


def handle_trade_info(
    addon,
    alias,
    price_level,
    size_level,
    is_otc,
    is_bid,
    is_execution_start,
    is_execution_end,
    aggressor_order_id,
    passive_order_id,
):
    """Handle trade events with time filtering and price tracking"""
    try:
        is_allowed, window_name = is_within_trading_window()

        # Update live price from trades (secondary source)
        params = instrument_params.get(alias, {"pips": 1.0, "size_multiplier": 1.0})
        actual_price = float(price_level) * float(params["pips"])

        # DISABLED: No longer pulling current price to database/file
        # Get current BBO for context
        # if alias in alias_to_order_book:
        #     try:
        #         bbos = bm.get_bbo(alias_to_order_book[alias])
        #         if bbos and bbos[0] and bbos[1]:
        #             (best_bid_level, _), (best_ask_level, _) = bbos
        #             best_bid = float(best_bid_level) * float(params["pips"])
        #             best_ask = float(best_ask_level) * float(params["pips"])
        #
        #             # Use trade price as mid if it's between bid/ask
        #             if best_bid <= actual_price <= best_ask:
        #                 update_live_price(
        #                     alias, actual_price, best_bid, best_ask, "trade"
        #                 )
        #     except:
        #         pass

        if not is_allowed:
            filtered_counts["trades"] += 1
            if filtered_counts["trades"] % 1000 == 0:
                log_debug(
                    "Filtered %d trade events (outside trading window)"
                    % filtered_counts["trades"]
                )
            return

        event_counts["trades"] += 1

        if event_counts["trades"] <= 5:
            log_debug(
                "Trade event #%d [%s]: alias=%s, price=%s, size=%s, is_bid=%s"
                % (
                    event_counts["trades"],
                    window_name,
                    alias,
                    price_level,
                    size_level,
                    is_bid,
                )
            )

        actual_size = (
            abs(float(size_level)) / float(params["size_multiplier"])
            if params["size_multiplier"] > 0
            else abs(size_level)
        )

        if ":" in alias:
            parts = alias.split(":", 1)
            exchange = parts[0]
            symbol = parts[1]
        else:
            exchange = ""
            symbol = alias

        timestamp = datetime.now(timezone.utc).isoformat()
        trade_id = "%s_%s_%f_%s_%d" % (
            exchange,
            symbol,
            actual_price,
            timestamp.replace(":", ""),
            size_level,
        )

        is_buy_aggressor = is_bid

        aggressor_id_str = str(aggressor_order_id) if aggressor_order_id else None
        passive_id_str = str(passive_order_id) if passive_order_id else None

        store_trade(
            timestamp,
            symbol,
            actual_price,
            actual_size,
            is_buy_aggressor,
            trade_id,
            exchange,
            is_otc,
            is_execution_start,
            is_execution_end,
            aggressor_id_str,
            passive_id_str,
        )

        if actual_size >= 100:
            side = "BUY" if is_buy_aggressor else "SELL"
            log_debug(
                "Large Trade [%s]: %s %s @ $%.2f x %.0f"
                % (
                    window_name,
                    normalize_symbol(symbol),
                    side,
                    actual_price,
                    actual_size,
                )
            )

    except Exception as e:
        log_debug("Trade handling failed", e)


def handle_subscription_response(addon, req_id):
    """Handle subscription confirmation"""
    try:
        data_types = {1: "depth", 2: "trades", 3: "mbo"}
        data_type = data_types.get(req_id, "unknown")

        log_debug("Subscription confirmed: %s (req_id=%d)" % (data_type, req_id))

        timestamp = datetime.now(timezone.utc).isoformat()
        store_response(timestamp, req_id, "current", data_type, True)

    except Exception as e:
        log_debug("Response handling failed", e)


def get_statistics():
    """Get statistics from database"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM trades")
        trade_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM mbo_orders")
        mbo_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM mbo_executions")
        exec_count = cursor.fetchone()[0]

        log_debug(
            "Statistics - DB: Orders=%d, Trades=%d, MBO=%d, Executions=%d | Filtered: Depth=%d, Trades=%d, MBO=%d | Live Prices: %d"
            % (
                order_count,
                trade_count,
                mbo_count,
                exec_count,
                filtered_counts.get("depth", 0),
                filtered_counts.get("trades", 0),
                filtered_counts.get("mbo", 0),
                len(live_prices),
            )
        )

        return {
            "orders": order_count,
            "trades": trade_count,
            "mbo_orders": mbo_count,
            "mbo_executions": exec_count,
            "live_events": event_counts,
            "filtered_events": filtered_counts,
            "live_prices_count": len(live_prices),
        }
    except Exception as e:
        log_debug("Failed to get statistics", e)
        return None
    finally:
        if conn:
            conn.close()


# Main execution
if __name__ == "__main__":
    try:
        log_debug("=" * 70)
        log_debug("Enhanced Market Monitor with MBO Support v%s" % __version__)
        log_debug("Python: %s" % sys.version)
        log_debug("[OK] Optimized In-Memory Price Tracking Enabled")
        log_debug("[FILE] Price Cache: %s" % PRICE_CACHE_FILE)
        log_debug("Trading Windows (EST):")
        log_debug(
            "  CBDR PM/Asian: %02d:%02d - %02d:%02d"
            % (
                CBDR_PM_START_HOUR,
                CBDR_PM_START_MINUTE,
                CBDR_PM_END_HOUR,
                CBDR_PM_END_MINUTE,
            )
        )
        log_debug(
            "  CBDR London:   %02d:%02d - %02d:%02d"
            % (
                CBDR_LONDON_START_HOUR,
                CBDR_LONDON_START_MINUTE,
                CBDR_LONDON_END_HOUR,
                CBDR_LONDON_END_MINUTE,
            )
        )
        log_debug(
            "  Pre-NY:        %02d:%02d - %02d:%02d"
            % (
                PRE_NY_START_HOUR,
                PRE_NY_START_MINUTE,
                PRE_NY_END_HOUR,
                PRE_NY_END_MINUTE,
            )
        )
        log_debug("=" * 70)

        init_database()

        addon = bm.create_addon()
        log_debug("Addon created successfully")

        bm.add_depth_handler(addon, handle_depth_info)
        bm.add_mbo_handler(addon, handle_mbo_info)
        bm.add_trades_handler(addon, handle_trade_info)
        bm.add_response_data_handler(addon, handle_subscription_response)
        log_debug("All handlers registered")

        bm.start_addon(
            addon, handle_subscribe_instrument, handle_unsubscribe_instrument
        )
        log_debug(
            "Addon started - monitoring market data with optimized real-time price tracking"
        )

        import time as time_module

        last_status = time_module.time()
        last_window_status = None

        while True:
            try:
                current_time = time_module.time()

                is_allowed, window_name = is_within_trading_window()

                if window_name != last_window_status:
                    if is_allowed:
                        log_debug("[+] ENTERING TRADING WINDOW: %s" % window_name)
                    else:
                        log_debug("[-] OUTSIDE TRADING WINDOW")
                    last_window_status = window_name

                if current_time - last_status > 60:
                    log_debug(
                        "Status [%s] - Instruments: %s"
                        % (window_name, list(instrument_params.keys()))
                    )

                    # Display live prices
                    for symbol, price_data in live_prices.items():
                        if (
                            "@" not in symbol and ":" not in symbol
                        ):  # Only show normalized symbols
                            log_debug(
                                "[PRICE] Live Price [%s]: $%.2f (bid: $%.2f, ask: $%.2f, spread: $%.2f) [%s]"
                                % (
                                    symbol,
                                    price_data["mid"],
                                    price_data["bid"],
                                    price_data["ask"],
                                    price_data["spread"],
                                    price_data["source"],
                                )
                            )

                    get_statistics()
                    last_status = current_time

                if bm.is_addon_turned_off(addon):
                    break

                time_module.sleep(1)
            except:
                bm.wait_until_addon_is_turned_off(addon)
                break

    except Exception as e:
        log_debug("Critical error: %s" % str(e))

    finally:
        log_debug("Final Statistics:")
        get_statistics()

        log_debug("Enhanced Market Monitor shutdown complete")
