#!/usr/bin/env python3
"""
Real-time monitoring for MNQ re-entry after stop loss.
Watches for bullish reversal signals at new session lows.
"""

import psycopg2
import time
from datetime import datetime, timedelta
import pytz

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}

EST = pytz.timezone("US/Eastern")

# Critical levels
SESSION_LOW = 25545  # New low hit
RECLAIM_LEVEL = 25570  # Old session low - must reclaim
ENTRY_ZONE_LOW = 25575
ENTRY_ZONE_HIGH = 25585
STOP_LOSS = 25540
TARGET_1 = 25620
TARGET_2 = 25670
TARGET_3 = 25730


def get_latest_candles(cursor, limit=10):
    """Get latest 5-minute candles from database."""
    sql = """
        SELECT timestamp, open, high, low, close, timeframe
        FROM ohlc_candles
        WHERE symbol = 'MNQ1!' 
        AND timeframe = '5m'
        AND timestamp >= NOW() - INTERVAL '2 hours'
        ORDER BY timestamp DESC
        LIMIT %s
    """
    cursor.execute(sql, (limit,))
    return cursor.fetchall()


def get_mbo_depth_at_level(cursor, price_low, price_high):
    """Get MBO depth in specific price range since Asian KZ."""
    sql = """
        SELECT 
            side,
            SUM(CASE WHEN action = 'DEPTH' THEN size ELSE 0 END) as depth_size,
            COUNT(*) as order_count
        FROM mbo_data
        WHERE symbol LIKE '%MNQ%'
        AND timestamp >= '2025-11-10 20:00:00-05'
        AND price BETWEEN %s AND %s
        AND size >= 10
        GROUP BY side
    """
    cursor.execute(sql, (price_low, price_high))
    return cursor.fetchall()


def get_recent_absorption_sweeps(cursor, price_low, price_high, minutes=30):
    """Get recent absorption and sweep activity."""
    sql = """
        SELECT 
            event_type,
            side,
            COUNT(*) as event_count,
            AVG(significance_score) as avg_significance
        FROM absorption_events
        WHERE symbol LIKE '%MNQ%'
        AND timestamp >= NOW() - INTERVAL '%s minutes'
        AND price BETWEEN %s AND %s
        GROUP BY event_type, side
        ORDER BY event_count DESC
    """
    cursor.execute(sql, (minutes, price_low, price_high))
    return cursor.fetchall()


def check_bullish_structure_break(candles):
    """
    Check if price has made a higher low and is breaking structure.
    Returns (is_bullish, details)
    """
    if len(candles) < 3:
        return False, "Not enough candles"

    # Sort by time ascending
    candles_asc = sorted(candles, key=lambda x: x[0])

    latest = candles_asc[-1]
    prev_1 = candles_asc[-2]
    prev_2 = candles_asc[-3]

    latest_low = latest[3]
    prev_1_low = prev_1[3]
    prev_2_low = prev_2[3]
    latest_close = latest[4]

    # Check for higher low
    if latest_low > prev_1_low and prev_1_low <= prev_2_low:
        # Check if breaking above previous high
        prev_high = max(prev_1[2], prev_2[2])
        if latest_close > prev_high:
            return True, f"Higher low at {latest_low:.2f}, broke above {prev_high:.2f}"

    return False, f"Current low: {latest_low:.2f}, Previous: {prev_1_low:.2f}"


def print_separator():
    print("\n" + "=" * 80)


def monitor_reentry():
    """Main monitoring loop."""
    print("🔍 MNQ Re-Entry Monitor Started")
    print(f"Time: {datetime.now(EST).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print_separator()
    print(f"Session Low (Stop Hit): {SESSION_LOW}")
    print(f"Reclaim Level Required: {RECLAIM_LEVEL}")
    print(f"Entry Zone: {ENTRY_ZONE_LOW}-{ENTRY_ZONE_HIGH}")
    print(f"Stop Loss: {STOP_LOSS}")
    print(f"Targets: {TARGET_1} → {TARGET_2} → {TARGET_3}")
    print_separator()

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    signal_count = 0
    last_alert_time = None

    try:
        while True:
            current_time = datetime.now(EST)

            # Only monitor during NY Kill Zone (8:30 AM - 11:00 AM EST)
            hour = current_time.hour
            minute = current_time.minute

            if hour < 8 or (hour == 8 and minute < 30) or hour >= 11:
                print(
                    f"\r⏸️  Outside NY Kill Zone (Current: {current_time.strftime('%H:%M')}) - Paused",
                    end="",
                    flush=True,
                )
                time.sleep(60)
                continue

            # Get latest data
            candles = get_latest_candles(cursor, 10)

            if not candles:
                print("\r⚠️  No recent candle data available", end="", flush=True)
                time.sleep(10)
                continue

            latest_candle = candles[0]
            timestamp, open_price, high, low, close, timeframe = latest_candle

            # Check structure
            is_bullish, structure_detail = check_bullish_structure_break(candles)

            # Get MBO depth around current price
            mbo_data = get_mbo_depth_at_level(cursor, close - 10, close + 20)
            buy_depth_above = 0
            sell_depth_below = 0

            for row in mbo_data:
                side, depth, count = row
                if side == "BUY":
                    buy_depth_above += depth
                elif side == "SELL":
                    sell_depth_below += depth

            # Get recent order flow
            order_flow = get_recent_absorption_sweeps(
                cursor, close - 20, close + 20, 15
            )
            buy_absorption = 0
            sell_absorption = 0
            buy_sweeps = 0
            sell_sweeps = 0

            for row in order_flow:
                event_type, side, count, avg_sig = row
                if event_type == "ABSORPTION":
                    if side in ("BUY", "BID"):
                        buy_absorption += count
                    else:
                        sell_absorption += count
                elif event_type == "SWEEP":
                    if side in ("BUY", "BID"):
                        buy_sweeps += count
                    else:
                        sell_sweeps += count

            # Status display
            status = f"\r🕐 {current_time.strftime('%H:%M:%S')} | "
            status += f"Price: {close:.2f} | "
            status += f"Low: {low:.2f} | "

            # Check re-entry conditions
            signals = []

            # Signal 1: Price reclaimed old session low
            if close > RECLAIM_LEVEL:
                signals.append("✅ RECLAIM")
            else:
                signals.append(f"⏳ Need {RECLAIM_LEVEL:.2f}")

            # Signal 2: Bullish structure break
            if is_bullish:
                signals.append("✅ STRUCTURE")
            else:
                signals.append("⏳ No break")

            # Signal 3: MBO favors upside
            if buy_depth_above > sell_depth_below * 1.5:
                signals.append("✅ MBO")
            else:
                signals.append("⏳ MBO weak")

            # Signal 4: Order flow bullish
            total_buy = buy_absorption + buy_sweeps
            total_sell = sell_absorption + sell_sweeps
            if total_buy > 0 and total_buy > total_sell * 1.2:
                signals.append("✅ FLOW")
            else:
                signals.append("⏳ Flow weak")

            status += " | ".join(signals)
            print(status, end="", flush=True)

            # Check if all conditions met
            conditions_met = all("✅" in s for s in signals)

            if conditions_met:
                signal_count += 1
                if (
                    last_alert_time is None
                    or (current_time - last_alert_time).seconds > 300
                ):
                    print_separator()
                    print("🚨 RE-ENTRY SIGNAL DETECTED!")
                    print(f"Time: {current_time.strftime('%H:%M:%S')}")
                    print(f"Current Price: {close:.2f}")
                    print(f"Entry Zone: {ENTRY_ZONE_LOW}-{ENTRY_ZONE_HIGH}")
                    print(
                        f"Stop Loss: {STOP_LOSS} ({close - STOP_LOSS:.1f} points risk)"
                    )
                    print(f"\nStructure: {structure_detail}")
                    print(
                        f"MBO: {buy_depth_above:,.0f} buy depth above vs {sell_depth_below:,.0f} sell below"
                    )
                    print(f"Order Flow (15min): {total_buy} buy vs {total_sell} sell")
                    print(f"\nTargets:")
                    print(
                        f"  TP1: {TARGET_1} (+{TARGET_1-close:.1f} pts, 1:{(TARGET_1-close)/(close-STOP_LOSS):.1f} R/R)"
                    )
                    print(
                        f"  TP2: {TARGET_2} (+{TARGET_2-close:.1f} pts, 1:{(TARGET_2-close)/(close-STOP_LOSS):.1f} R/R)"
                    )
                    print(
                        f"  TP3: {TARGET_3} (+{TARGET_3-close:.1f} pts, 1:{(TARGET_3-close)/(close-STOP_LOSS):.1f} R/R)"
                    )
                    print_separator()
                    last_alert_time = current_time

            # Sleep before next check
            time.sleep(10)  # Check every 10 seconds

    except KeyboardInterrupt:
        print("\n\n🛑 Monitor stopped by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()
        print("\n✅ Database connection closed")


if __name__ == "__main__":
    monitor_reentry()
