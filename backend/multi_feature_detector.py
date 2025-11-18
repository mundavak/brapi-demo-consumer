#!/usr/bin/env python3
"""
Multi-feature iceberg detector
Combines trade bursts with price level analysis and order book features
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


def detect_with_features(start_time, end_time):
    """
    Enhanced detection using multiple features:
    1. Trade burst (rapid trades)
    2. Price level persistence (same price appears repeatedly)
    3. Order size consistency (similar sizes)
    4. Time clustering (multiple bursts at same price)
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("=" * 80)
    print("MULTI-FEATURE ICEBERG DETECTION")
    print("=" * 80)

    # Load all MBO events (not just trades)
    cursor.execute(
        """
        SELECT timestamp, action, price, side, size, order_id
        FROM mbo_data
        WHERE timestamp >= %s AND timestamp < %s
        AND symbol LIKE 'MNQ%%'
        ORDER BY timestamp
    """,
        (start_time, end_time),
    )

    events = cursor.fetchall()
    print(f"Loaded {len(events):,} MBO events")

    # Feature 1: Find trade bursts
    trade_bursts = []
    current_burst = []
    burst_start = None
    burst_price = None
    burst_side = None

    for ts, action, price, side, size, oid in events:
        if action != "TRADE":
            continue

        if not current_burst:
            current_burst = [(ts, size)]
            burst_start = ts
            burst_price = price
            burst_side = side
            continue

        time_diff_ms = (ts - burst_start).total_seconds() * 1000
        price_diff = abs(price - burst_price)

        if time_diff_ms <= 10 and price_diff <= 0.25 and side == burst_side:
            current_burst.append((ts, size))
        else:
            if len(current_burst) >= 10:  # Minimum burst size
                total_size = sum(s for _, s in current_burst)
                if total_size >= 10:
                    trade_bursts.append(
                        {
                            "time": burst_start,
                            "price": burst_price,
                            "side": burst_side,
                            "count": len(current_burst),
                            "total": total_size,
                        }
                    )

            current_burst = [(ts, size)]
            burst_start = ts
            burst_price = price
            burst_side = side

    print(f"Found {len(trade_bursts)} trade bursts")

    # Feature 2: Price level persistence (orders repeatedly at same price)
    price_levels = defaultdict(lambda: {"count": 0, "times": [], "side": None})

    for ts, action, price, side, size, oid in events:
        if action == "ADD":
            key = (round(price * 4) / 4, side)  # Round to quarter point
            price_levels[key]["count"] += 1
            price_levels[key]["times"].append(ts)
            price_levels[key]["side"] = side

    # Find persistent levels (many ADDs at same price over time)
    persistent_levels = []
    for (price, side), data in price_levels.items():
        if data["count"] >= 20:  # 20+ orders at same price
            time_span = (max(data["times"]) - min(data["times"])).total_seconds()
            if time_span >= 10:  # Over at least 10 seconds
                persistent_levels.append(
                    {
                        "price": price,
                        "side": side,
                        "count": data["count"],
                        "start": min(data["times"]),
                        "end": max(data["times"]),
                    }
                )

    print(f"Found {len(persistent_levels)} persistent price levels")

    # Feature 3: Combine features - burst + persistent level
    candidates = []

    for burst in trade_bursts:
        # Check if burst is near a persistent level
        for level in persistent_levels:
            price_diff = abs(burst["price"] - level["price"])
            time_overlap = burst["time"] >= level["start"] and burst["time"] <= level[
                "end"
            ] + timedelta(seconds=30)
            side_match = burst["side"] == level["side"]

            if price_diff <= 0.5 and time_overlap and side_match:
                # This burst is hitting a persistent level!
                candidates.append(
                    {
                        "time": burst["time"],
                        "price": burst["price"],
                        "side": burst["side"],
                        "burst_count": burst["count"],
                        "burst_size": burst["total"],
                        "level_orders": level["count"],
                    }
                )
                break  # Only count once

    print(f"Found {len(candidates)} candidates (burst + persistent level)")

    # Get actual icebergs
    cursor.execute(
        """
        SELECT timestamp, price, side
        FROM stops_icebergs
        WHERE event_type = 'ICEBERG'
        AND iceberg_subtype = 'DETECTION'
        AND timestamp >= %s AND timestamp < %s
        AND symbol LIKE 'MNQ%%'
    """,
        (start_time, end_time),
    )

    actuals = cursor.fetchall()
    print(f"Actual icebergs: {len(actuals)}")

    # Match candidates to actuals
    matches = 0
    matched = set()
    matched_candidates = []
    unmatched_candidates = []

    for cand in candidates:
        is_match = False
        for i, (act_time, act_price, act_side) in enumerate(actuals):
            if i in matched:
                continue

            time_diff = abs((cand["time"] - act_time).total_seconds())
            price_diff = abs(cand["price"] - act_price)

            if time_diff <= 2 and price_diff <= 0.5 and cand["side"] == act_side:
                matches += 1
                matched.add(i)
                matched_candidates.append(cand)
                is_match = True
                break

        if not is_match:
            unmatched_candidates.append(cand)

    precision = (matches / len(candidates) * 100) if candidates else 0
    recall = (matches / len(actuals) * 100) if actuals else 0

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"Candidates: {len(candidates)}")
    print(f"True Positives: {matches}")
    print(f"False Positives: {len(candidates) - matches}")
    print(f"False Negatives: {len(actuals) - matches}")
    print(f"\nPrecision: {precision:.1f}%")
    print(f"Recall: {recall:.1f}%")

    if precision > 0 and recall > 0:
        f1 = 2 * (precision * recall) / (precision + recall)
        print(f"F1 Score: {f1:.1f}%")

    # Show sample matches
    if matched_candidates:
        print(f"\nSample TRUE POSITIVES (first 5):")
        for cand in matched_candidates[:5]:
            print(
                f"  {cand['time'].strftime('%H:%M:%S')} {cand['side']:4} ${cand['price']:.2f} "
                f"[{cand['burst_count']} trades, {cand['burst_size']:.0f} size, "
                f"{cand['level_orders']} level orders]"
            )

    # Show sample false positives
    if unmatched_candidates:
        print(f"\nSample FALSE POSITIVES (first 5):")
        for cand in unmatched_candidates[:5]:
            print(
                f"  {cand['time'].strftime('%H:%M:%S')} {cand['side']:4} ${cand['price']:.2f} "
                f"[{cand['burst_count']} trades, {cand['burst_size']:.0f} size, "
                f"{cand['level_orders']} level orders]"
            )

    cursor.close()
    conn.close()

    return precision, recall


if __name__ == "__main__":
    start = datetime.fromisoformat("2025-11-17 09:00:00")
    end = datetime.fromisoformat("2025-11-17 12:00:00")

    detect_with_features(start, end)
