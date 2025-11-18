#!/usr/bin/env python3
"""
Trade-Burst Iceberg Detector
Detects icebergs by finding rapid bursts of TRADE events (multiple trades within milliseconds)
"""
import psycopg2
from datetime import datetime, timedelta
from collections import defaultdict

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}

# Detection thresholds (based on Bookmap analysis)
MIN_TRADES_IN_BURST = 7  # At least 7 trades
BURST_WINDOW_MS = 10  # Within 10 milliseconds (Bookmap threshold)
MIN_BURST_SIZE = 8  # Total size >= 8 contracts


def detect_trade_bursts(start_time, end_time, symbol="MNQ"):
    """
    Detect iceberg candidates by finding bursts of trades

    Pattern: Multiple TRADE events at same/similar price within milliseconds
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print(f"{'=' * 80}")
    print(f"TRADE-BURST ICEBERG DETECTION")
    print(f"{'=' * 80}")
    print(f"Period: {start_time} to {end_time}")
    print(f"Thresholds:")
    print(f"  Min trades per burst: {MIN_TRADES_IN_BURST}")
    print(f"  Time window: {BURST_WINDOW_MS}ms")
    print(f"  Min total size: {MIN_BURST_SIZE}")
    print()

    # Get all TRADE events for the period
    cursor.execute(
        """
        SELECT 
            timestamp,
            price,
            side,
            size
        FROM mbo_data
        WHERE timestamp >= %s AND timestamp < %s
        AND action = 'TRADE'
        AND symbol LIKE %s
        ORDER BY timestamp, price
    """,
        (start_time, end_time, f"{symbol}%"),
    )

    trades = cursor.fetchall()
    print(f"Loaded {len(trades):,} TRADE events")

    if not trades:
        print("No trades found")
        return []

    # Group trades into bursts
    # A burst = multiple trades at same price within BURST_WINDOW_MS
    bursts = []
    current_burst = []
    burst_start_time = None
    burst_price = None
    burst_side = None

    for trade in trades:
        ts, price, side, size = trade

        # Start new burst?
        if not current_burst:
            current_burst = [trade]
            burst_start_time = ts
            burst_price = price
            burst_side = side
            continue

        # Check if this trade belongs to current burst
        time_diff_ms = (ts - burst_start_time).total_seconds() * 1000
        price_diff = abs(price - burst_price)

        if (
            time_diff_ms <= BURST_WINDOW_MS
            and price_diff <= 0.25  # Within quarter point
            and side == burst_side
        ):
            # Add to current burst
            current_burst.append(trade)
        else:
            # Check if current burst qualifies as iceberg
            if len(current_burst) >= MIN_TRADES_IN_BURST:
                total_size = sum(t[3] for t in current_burst)
                if total_size >= MIN_BURST_SIZE:
                    bursts.append(
                        {
                            "timestamp": burst_start_time,
                            "price": burst_price,
                            "side": burst_side,
                            "trade_count": len(current_burst),
                            "total_size": total_size,
                            "duration_ms": time_diff_ms,
                        }
                    )

            # Start new burst
            current_burst = [trade]
            burst_start_time = ts
            burst_price = price
            burst_side = side

    # Check final burst
    if len(current_burst) >= MIN_TRADES_IN_BURST:
        total_size = sum(t[3] for t in current_burst)
        if total_size >= MIN_BURST_SIZE:
            time_diff_ms = (
                current_burst[-1][0] - burst_start_time
            ).total_seconds() * 1000
            bursts.append(
                {
                    "timestamp": burst_start_time,
                    "price": burst_price,
                    "side": burst_side,
                    "trade_count": len(current_burst),
                    "total_size": total_size,
                    "duration_ms": time_diff_ms,
                }
            )

    print(f"\nDetected {len(bursts)} iceberg candidates")

    # Now compare with actual icebergs
    cursor.execute(
        """
        SELECT 
            timestamp,
            price,
            side,
            detected_size
        FROM stops_icebergs
        WHERE event_type = 'ICEBERG'
        AND iceberg_subtype = 'DETECTION'
        AND timestamp >= %s AND timestamp < %s
        AND symbol LIKE %s
        ORDER BY timestamp
    """,
        (start_time, end_time, f"{symbol}%"),
    )

    actual_icebergs = cursor.fetchall()
    print(f"Actual icebergs from Bookmap: {len(actual_icebergs)}")

    # Match candidates to actuals (within 5 seconds and $1)
    matches = 0
    false_positives = 0
    false_negatives = 0

    matched_actuals = set()
    matched_candidates = set()

    for i, candidate in enumerate(bursts):
        cand_time = candidate["timestamp"]
        cand_price = candidate["price"]
        cand_side = candidate["side"]

        # Find matching actual
        for j, (act_time, act_price, act_side, act_size) in enumerate(actual_icebergs):
            if j in matched_actuals:
                continue

            time_diff = abs((cand_time - act_time).total_seconds())
            price_diff = abs(cand_price - act_price)

            if time_diff <= 5 and price_diff <= 1.0 and cand_side == act_side:
                matches += 1
                matched_actuals.add(j)
                matched_candidates.add(i)
                break

    false_positives = len(bursts) - matches
    false_negatives = len(actual_icebergs) - matches

    print(f"\n{'=' * 80}")
    print("VALIDATION RESULTS")
    print(f"{'=' * 80}")
    print(f"True Positives (matches):     {matches}")
    print(f"False Positives (extra):      {false_positives}")
    print(f"False Negatives (missed):     {false_negatives}")

    if len(actual_icebergs) > 0:
        recall = matches / len(actual_icebergs) * 100
        print(f"\nRecall (detection rate):      {recall:.1f}%")

    if len(bursts) > 0:
        precision = matches / len(bursts) * 100
        print(f"Precision (accuracy):         {precision:.1f}%")

    # Show sample matches
    print(f"\nSample matches (first 5):")
    match_count = 0
    for i, candidate in enumerate(bursts):
        if i in matched_candidates:
            match_count += 1
            if match_count <= 5:
                print(
                    f"  {candidate['timestamp'].strftime('%H:%M:%S.%f')[:-3]} "
                    f"{candidate['side']:4} ${candidate['price']:.2f} "
                    f"[{candidate['trade_count']} trades, {candidate['total_size']:.0f} contracts, "
                    f"{candidate['duration_ms']:.1f}ms]"
                )

    # Show sample misses
    print(f"\nSample misses (first 5):")
    miss_count = 0
    for j, (act_time, act_price, act_side, act_size) in enumerate(actual_icebergs):
        if j not in matched_actuals:
            miss_count += 1
            if miss_count <= 5:
                print(
                    f"  {act_time.strftime('%H:%M:%S.%f')[:-3]} "
                    f"{act_side:4} ${act_price:.2f} "
                    f"[size: {act_size:.0f}] - NO BURST DETECTED"
                )

    cursor.close()
    conn.close()

    return bursts


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 4:
        date_str = sys.argv[1]
        start_hour = int(sys.argv[2])
        end_hour = int(sys.argv[3])
    else:
        # Default: Nov 17, 9am-10am
        date_str = "2025-11-17"
        start_hour = 9
        end_hour = 10

    start_time = datetime.fromisoformat(f"{date_str} {start_hour:02d}:00:00")
    end_time = datetime.fromisoformat(f"{date_str} {end_hour:02d}:00:00")

    detect_trade_bursts(start_time, end_time)
