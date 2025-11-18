#!/usr/bin/env python3
"""
Verify Hypothesis: Icebergs appear as rapid bursts of TRADE-only events
"""
import psycopg2
from datetime import timedelta
from collections import defaultdict

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}


def analyze_pattern():
    """Look for pattern: rapid TRADE events at same price/time"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Get all iceberg detections in hour
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
        AND timestamp >= '2025-11-17 09:00:00' 
        AND timestamp < '2025-11-17 10:00:00'
        AND symbol LIKE 'MNQ%'
        ORDER BY timestamp
        LIMIT 10
    """
    )

    icebergs = cursor.fetchall()
    print(f"Analyzing {len(icebergs)} iceberg detections\n")

    for idx, (ice_time, ice_price, ice_side, ice_size) in enumerate(icebergs, 1):
        # Look for MBO pattern within ±2 seconds
        time_before = ice_time - timedelta(seconds=2)
        time_after = ice_time + timedelta(seconds=2)
        price_range = 0.25  # Quarter point

        cursor.execute(
            """
            SELECT 
                timestamp,
                action,
                size,
                price
            FROM mbo_data
            WHERE timestamp >= %s AND timestamp <= %s
            AND price >= %s AND price <= %s
            AND side = %s
            AND symbol LIKE 'MNQ%%'
            AND action = 'TRADE'
            ORDER BY timestamp
        """,
            (
                time_before,
                time_after,
                ice_price - price_range,
                ice_price + price_range,
                ice_side,
            ),
        )

        trades = cursor.fetchall()

        # Group trades by millisecond
        ms_groups = defaultdict(list)
        for ts, action, size, price in trades:
            ms = ts.replace(microsecond=(ts.microsecond // 1000) * 1000)
            ms_groups[ms].append((size, price))

        print(f"\nIceberg #{idx}:")
        print(f"  Time: {ice_time.strftime('%H:%M:%S.%f')[:-3]}")
        print(f"  Price: ${ice_price:.2f}")
        print(f"  Side: {ice_side}")
        print(f"  Detected Size: {ice_size:.0f}")
        print(f"  Found {len(trades)} TRADE events nearby")

        if ms_groups:
            print("\n  Trade bursts (trades within same millisecond):")
            for ms, group in sorted(ms_groups.items())[:5]:
                total_size = sum(s for s, _ in group)
                prices = set(p for _, p in group)
                print(
                    f"    {ms.strftime('%H:%M:%S.%f')[:-3]}: {len(group)} trades, "
                    f"total size: {total_size}, prices: {prices}"
                )

            # Check if there's a burst matching detected size
            max_burst = max(ms_groups.values(), key=len)
            max_burst_size = sum(s for s, _ in max_burst)
            print(f"  Largest burst: {len(max_burst)} trades, total: {max_burst_size}")

            if max_burst_size >= ice_size * 0.8:  # Within 20%
                print(
                    f"  ✓ MATCH: Burst size ({max_burst_size}) ≈ detected size ({ice_size:.0f})"
                )
            else:
                print(
                    f"  ✗ NO MATCH: Burst size ({max_burst_size}) ≠ detected size ({ice_size:.0f})"
                )
        else:
            print("  No TRADE events found in window")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    analyze_pattern()
