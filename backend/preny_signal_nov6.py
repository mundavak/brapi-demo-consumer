#!/usr/bin/env python3
"""
PRE_NY Order Flow Analysis for 9:30 AM Trading Signal
Using: MBO, Stops, Icebergs (with sub-types), and Absorption data
Date: Nov 6, 2025
Starting Price: 25,802 at 8:44 AM EST
"""

import psycopg2
from datetime import datetime, timedelta
import pytz

# Database config
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}


def analyze_preny_order_flow():
    """Analyze PRE_NY window (7:30-9:00 AM) for 9:30 signal"""

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Nov 6, 2025 PRE_NY window: 7:30 AM - 9:00 AM EST
    # Convert to timestamps (EST is UTC-5)
    date_str = "2025-11-06"
    start_time = datetime.strptime(f"{date_str} 07:30:00", "%Y-%m-%d %H:%M:%S")
    end_time = datetime.strptime(f"{date_str} 09:00:00", "%Y-%m-%d %H:%M:%S")

    # Convert to UTC for database query
    eastern = pytz.timezone("America/New_York")
    start_time = eastern.localize(start_time)
    end_time = eastern.localize(end_time)

    print("=" * 80)
    print("PRE_NY ORDER FLOW ANALYSIS FOR 9:30 AM SIGNAL")
    print("=" * 80)
    print(f"Date: {date_str}")
    print(f"PRE_NY Window: 7:30 AM - 9:00 AM EST")
    print(f"Starting Price: $25,802 (8:44 AM)")
    print()

    # === STOPS ANALYSIS (ICT Stop Hunt Concept) ===
    print("=" * 80)
    print("1. STOP HUNT ANALYSIS")
    print("=" * 80)

    # Query all stops in the time window (cbdr_window may not be set)
    cur.execute(
        """
        SELECT 
            side,
            COUNT(*) as count,
            SUM(detected_size) as total_detected,
            SUM(estimated_total_size) as total_estimated
        FROM stops_icebergs
        WHERE symbol LIKE 'MNQ%%'
          AND event_type IN ('STOP', 'STOP_CLUSTER')
          AND timestamp >= to_timestamp(%s)
          AND timestamp < to_timestamp(%s)
        GROUP BY side
    """,
        (start_time.timestamp(), end_time.timestamp()),
    )

    stops_data = cur.fetchall()

    buy_stops = sell_stops = 0
    buy_stops_vol = sell_stops_vol = 0

    if stops_data:
        for side, count, detected, estimated in stops_data:
            if side == "BUY":
                buy_stops = count
                buy_stops_vol = estimated if estimated else detected
            else:
                sell_stops = count
                sell_stops_vol = estimated if estimated else detected

        print(f"BUY Stops:  {buy_stops:,} events | Vol: {buy_stops_vol:,.0f}")
        print(f"SELL Stops: {sell_stops:,} events | Vol: {sell_stops_vol:,.0f}")

        if buy_stops + sell_stops > 0:
            ratio = buy_stops / sell_stops if sell_stops > 0 else 999
            print(f"Ratio: {ratio:.2f}x")
            print()

            # ICT Stop Hunt Logic: BUY stops = price swept down = bullish reversal expected
            if ratio > 1.2:
                stops_signal = "BULLISH"
                stops_score = min((ratio - 1) * 25, 30)
                print(f"Signal: {stops_signal} (BUY stops dominant)")
                print(
                    f"Interpretation: Price swept DOWN through stops → Expect BULLISH reversal"
                )
            elif ratio < 0.8:
                stops_signal = "BEARISH"
                stops_score = min((1 / ratio - 1) * 25, 30)
                print(f"Signal: {stops_signal} (SELL stops dominant)")
                print(
                    f"Interpretation: Price swept UP through stops → Expect BEARISH reversal"
                )
            else:
                stops_signal = "NEUTRAL"
                stops_score = 0
                print(f"Signal: {stops_signal} (balanced)")
        else:
            stops_signal = "NEUTRAL"
            stops_score = 0
    else:
        print("No stop data in PRE_NY window")
        stops_signal = "NEUTRAL"
        stops_score = 0
    print()

    # === ICEBERGS ANALYSIS (with sub-types) ===
    print("=" * 80)
    print("2. ICEBERG ANALYSIS (Institutional Positioning)")
    print("=" * 80)

    # High-confidence icebergs only (TRADE, EXECUTION)
    cur.execute(
        """
        SELECT 
            side,
            iceberg_subtype,
            COUNT(*) as count,
            SUM(detected_size) as total_detected,
            SUM(estimated_total_size) as total_estimated
        FROM stops_icebergs
        WHERE symbol LIKE 'MNQ%%'
          AND event_type = 'ICEBERG'
          AND timestamp >= to_timestamp(%s)
          AND timestamp < to_timestamp(%s)
        GROUP BY side, iceberg_subtype
        ORDER BY side, count DESC
    """,
        (start_time.timestamp(), end_time.timestamp()),
    )

    iceberg_data = cur.fetchall()

    buy_icebergs = sell_icebergs = 0
    buy_ice_vol = sell_ice_vol = 0

    # Weight by sub-type reliability
    subtype_weights = {
        "TRADE": 1.0,
        "EXECUTION": 0.8,
        "DETECTION": 0.5,
        "MOVEMENT": 0.3,
        "CANCELLATION": 0.2,
    }

    buy_weighted = sell_weighted = 0

    if iceberg_data:
        print("By Sub-Type:")
        for side, subtype, count, detected, estimated in iceberg_data:
            weight = subtype_weights.get(subtype, 0.5) if subtype else 0.5
            weighted_count = count * weight

            print(
                f"  {side:4} {subtype or 'NULL':12} - {count:3} events (weighted: {weighted_count:.1f})"
            )

            if side == "BUY":
                buy_icebergs += count
                buy_ice_vol += estimated if estimated else detected
                buy_weighted += weighted_count
            else:
                sell_icebergs += count
                sell_ice_vol += estimated if estimated else detected
                sell_weighted += weighted_count

        print()
        print(
            f"BUY Icebergs:  {buy_icebergs} events (weighted: {buy_weighted:.1f}) | Vol: {buy_ice_vol:.0f}"
        )
        print(
            f"SELL Icebergs: {sell_icebergs} events (weighted: {sell_weighted:.1f}) | Vol: {sell_ice_vol:.0f}"
        )

        # Use weighted counts for signal
        if buy_weighted + sell_weighted > 0:
            ratio = buy_weighted / sell_weighted if sell_weighted > 0 else 999
            print(f"Weighted Ratio: {ratio:.2f}x")
            print()

            # BUY icebergs = support, SELL icebergs = resistance
            if ratio > 1.3:
                ice_signal = "BULLISH"
                ice_score = min((ratio - 1) * 15, 20)
                print(f"Signal: {ice_signal} (BUY icebergs = institutional support)")
            elif ratio < 0.7:
                ice_signal = "BEARISH"
                ice_score = min((1 / ratio - 1) * 15, 20)
                print(
                    f"Signal: {ice_signal} (SELL icebergs = institutional resistance)"
                )
            else:
                ice_signal = "NEUTRAL"
                ice_score = 0
                print(f"Signal: {ice_signal}")
        else:
            ice_signal = "NEUTRAL"
            ice_score = 0
    else:
        print("No iceberg data in PRE_NY window")
        ice_signal = "NEUTRAL"
        ice_score = 0
    print()

    # === MBO FLOW ANALYSIS ===
    print("=" * 80)
    print("3. MBO ORDER FLOW")
    print("=" * 80)

    cur.execute(
        """
        SELECT 
            side,
            COUNT(*) as order_count,
            SUM(size) as total_volume
        FROM mbo_data
        WHERE symbol LIKE 'MNQ%%'
          AND action = 'ADD'
          AND timestamp >= to_timestamp(%s)
          AND timestamp < to_timestamp(%s)
        GROUP BY side
    """,
        (start_time.timestamp(), end_time.timestamp()),
    )

    mbo_data = cur.fetchall()

    if mbo_data:
        buy_orders = sell_orders = 0
        buy_vol = sell_vol = 0

        for side, count, vol in mbo_data:
            if side == "BUY":
                buy_orders = count
                buy_vol = vol
            else:
                sell_orders = count
                sell_vol = vol

        print(f"BUY Orders:  {buy_orders:,} | Volume: {buy_vol:,.0f}")
        print(f"SELL Orders: {sell_orders:,} | Volume: {sell_vol:,.0f}")

        if buy_orders + sell_orders > 0:
            order_ratio = buy_orders / sell_orders if sell_orders > 0 else 999
            vol_ratio = buy_vol / sell_vol if sell_vol > 0 else 999

            print(f"Order Ratio: {order_ratio:.2f}x")
            print(f"Volume Ratio: {vol_ratio:.2f}x")
            print()

            # MBO flow direction
            if order_ratio > 1.1 and vol_ratio > 1.1:
                mbo_signal = "BULLISH"
                mbo_score = min((order_ratio - 1) * 20, 25)
                print(f"Signal: {mbo_signal} (BUY-side aggression)")
            elif order_ratio < 0.9 and vol_ratio < 0.9:
                mbo_signal = "BEARISH"
                mbo_score = min((1 / order_ratio - 1) * 20, 25)
                print(f"Signal: {mbo_signal} (SELL-side aggression)")
            else:
                mbo_signal = "NEUTRAL"
                mbo_score = 0
                print(f"Signal: {mbo_signal} (balanced flow)")
        else:
            mbo_signal = "NEUTRAL"
            mbo_score = 0
    else:
        print("No MBO data in PRE_NY window")
        mbo_signal = "NEUTRAL"
        mbo_score = 0
    print()

    # === COMPREHENSIVE BIAS ===
    print("=" * 80)
    print("9:30 AM TRADING SIGNAL")
    print("=" * 80)

    # Calculate bias score (negative for bearish)
    if stops_signal == "BEARISH":
        stops_score = -stops_score
    if ice_signal == "BEARISH":
        ice_score = -ice_score
    if mbo_signal == "BEARISH":
        mbo_score = -mbo_score

    total_score = stops_score + ice_score + mbo_score

    print("Signal Components:")
    print(f"  Stops:    {stops_signal:8} ({stops_score:+.1f} points)")
    print(f"  Icebergs: {ice_signal:8} ({ice_score:+.1f} points)")
    print(f"  MBO Flow: {mbo_signal:8} ({mbo_score:+.1f} points)")
    print()
    print(f"Total Score: {total_score:+.1f} / ±75")
    print()

    # Final recommendation
    if total_score >= 15:
        final_signal = "LONG"
        confidence = min(abs(total_score) / 75 * 100, 95)
    elif total_score <= -15:
        final_signal = "SHORT"
        confidence = min(abs(total_score) / 75 * 100, 95)
    else:
        final_signal = "WAIT"
        confidence = 100 - min(abs(total_score) / 75 * 100, 95)

    print("=" * 80)
    print(f"FINAL SIGNAL: {final_signal}")
    print(f"Confidence: {confidence:.1f}%")
    print("=" * 80)
    print()

    # Trading plan
    if final_signal == "LONG":
        print("LONG Setup:")
        print(f"  Entry: $25,802 (or pullback to $25,777 London high)")
        print(f"  Stop:  $25,628 (London low)")
        print(f"  Target 1: $25,878 (PDH)")
        print(f"  Target 2: $25,928 (extension)")
        print(
            f"  Risk: {25802 - 25628:.0f} points | Reward: {25878 - 25802:.0f} points (R:R = {(25878-25802)/(25802-25628):.2f}:1)"
        )
    elif final_signal == "SHORT":
        print("SHORT Setup:")
        print(f"  Entry: $25,802 (or retest of $25,777 London high)")
        print(f"  Stop:  $25,878 (PDH)")
        print(f"  Target 1: $25,628 (London low)")
        print(f"  Target 2: $25,403 (PDL)")
        print(
            f"  Risk: {25878 - 25802:.0f} points | Reward: {25802 - 25628:.0f} points (R:R = {(25802-25628)/(25878-25802):.2f}:1)"
        )
    else:
        print("WAIT for clearer setup. Conflicting signals.")

    print()

    cur.close()
    conn.close()

    return final_signal, confidence


if __name__ == "__main__":
    analyze_preny_order_flow()
