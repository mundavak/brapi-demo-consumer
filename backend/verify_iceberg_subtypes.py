#!/usr/bin/env python3
"""
Verification script for iceberg sub-type capture
Checks both TimescaleDB and Redis for properly captured iceberg sub-types
"""

import psycopg2
import redis
import json
from datetime import datetime, timedelta

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}

REDIS_CONFIG = {"host": "localhost", "port": 6379, "db": 0}


def check_timescaledb():
    """Check TimescaleDB for iceberg sub-types"""
    print("=" * 80)
    print("TIMESCALEDB VERIFICATION")
    print("=" * 80)

    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # 1. Verify column exists
    print("\n1. Column Verification:")
    cur.execute(
        """
        SELECT column_name, data_type, is_nullable, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'stops_icebergs' 
          AND column_name = 'iceberg_subtype'
    """
    )
    result = cur.fetchone()
    if result:
        print(
            f"   ✓ Column exists: {result[0]} ({result[1]}, nullable: {result[2]}, max_length: {result[3]})"
        )
    else:
        print("   ✗ Column NOT found!")
        return

    # 2. Count total icebergs with sub-types
    print("\n2. Overall Statistics:")
    cur.execute(
        """
        SELECT 
            COUNT(*) as total_icebergs,
            COUNT(iceberg_subtype) as with_subtype,
            COUNT(*) - COUNT(iceberg_subtype) as without_subtype
        FROM stops_icebergs
        WHERE event_type = 'ICEBERG'
    """
    )
    total, with_sub, without_sub = cur.fetchone()
    print(f"   Total icebergs: {total:,}")
    print(f"   With sub-type: {with_sub:,} ({with_sub/total*100:.1f}%)")
    print(
        f"   Without sub-type (legacy): {without_sub:,} ({without_sub/total*100:.1f}%)"
    )

    # 3. Recent events (last hour)
    print("\n3. Recent Events (Last Hour):")
    cur.execute(
        """
        SELECT 
            COUNT(*) as count,
            MIN(timestamp) as first_seen,
            MAX(timestamp) as last_seen
        FROM stops_icebergs
        WHERE event_type = 'ICEBERG'
          AND timestamp > NOW() - INTERVAL '1 hour'
    """
    )
    count, first, last = cur.fetchone()
    print(f"   Recent icebergs: {count:,}")
    if count > 0:
        print(f"   First: {first}")
        print(f"   Last: {last}")

    # 4. Sub-type distribution (recent)
    print("\n4. Sub-Type Distribution (Last Hour):")
    cur.execute(
        """
        SELECT 
            COALESCE(iceberg_subtype, 'NULL') as subtype,
            COUNT(*) as count,
            AVG(detected_size) as avg_detected,
            AVG(estimated_total_size) as avg_estimated,
            MIN(timestamp) as first_seen,
            MAX(timestamp) as last_seen
        FROM stops_icebergs
        WHERE event_type = 'ICEBERG'
          AND timestamp > NOW() - INTERVAL '1 hour'
        GROUP BY iceberg_subtype
        ORDER BY count DESC
    """
    )
    results = cur.fetchall()
    if results:
        print(
            f"   {'Sub-Type':<15} {'Count':<8} {'Avg Detected':<15} {'Avg Estimated':<15} {'First Seen':<20} {'Last Seen':<20}"
        )
        print("   " + "-" * 100)
        for row in results:
            subtype, count, avg_det, avg_est, first, last = row
            print(
                f"   {subtype:<15} {count:<8} {avg_det:<15.2f} {avg_est:<15.2f} {str(first):<20} {str(last):<20}"
            )
    else:
        print("   No recent iceberg events found.")

    # 5. Sample TRADE icebergs
    print("\n5. Sample TRADE Icebergs (Most Recent 5):")
    cur.execute(
        """
        SELECT 
            timestamp,
            symbol,
            side,
            iceberg_subtype,
            price,
            detected_size,
            estimated_total_size,
            cbdr_window
        FROM stops_icebergs
        WHERE event_type = 'ICEBERG'
          AND iceberg_subtype = 'TRADE'
        ORDER BY timestamp DESC
        LIMIT 5
    """
    )
    results = cur.fetchall()
    if results:
        for row in results:
            ts, symbol, side, subtype, price, det, est, cbdr = row
            print(
                f"   {ts} | {symbol} | {side} | {subtype} | ${price:.2f} | Detected: {det} | Estimated: {est} | {cbdr}"
            )
    else:
        print("   No TRADE icebergs found yet.")

    # 6. Verify STOP events have NULL sub-type
    print("\n6. STOP Events Verification:")
    cur.execute(
        """
        SELECT 
            COUNT(*) as total_stops,
            COUNT(iceberg_subtype) as stops_with_subtype
        FROM stops_icebergs
        WHERE event_type IN ('STOP', 'STOP_CLUSTER')
          AND timestamp > NOW() - INTERVAL '1 hour'
    """
    )
    total_stops, stops_with_sub = cur.fetchone()
    print(f"   Recent stops: {total_stops:,}")
    print(f"   Stops with sub-type (should be 0): {stops_with_sub}")
    if stops_with_sub > 0:
        print("   ✗ WARNING: STOP events should have NULL iceberg_subtype!")
    else:
        print("   ✓ All STOP events have NULL iceberg_subtype (correct)")

    cur.close()
    conn.close()


def check_redis():
    """Check Redis for iceberg sub-types in JSON"""
    print("\n" + "=" * 80)
    print("REDIS VERIFICATION")
    print("=" * 80)

    r = redis.Redis(**REDIS_CONFIG, decode_responses=True)

    # Find iceberg keys
    print("\n1. Finding Iceberg Keys:")
    keys = r.keys("iceberg:*")
    print(f"   Found {len(keys)} iceberg keys")

    if not keys:
        print("   No iceberg keys found in Redis.")
        return

    # Check first 5 keys
    print("\n2. Sample Iceberg Events:")
    for i, key in enumerate(keys[:5]):
        print(f"\n   Key: {key}")
        events = r.zrevrange(key, 0, 2, withscores=False)  # Get latest 3 events
        if events:
            print(f"   Latest {len(events)} events:")
            for j, event_json in enumerate(events):
                try:
                    event = json.loads(event_json)
                    print(f"      Event {j+1}:")
                    print(f"         symbol: {event.get('symbol')}")
                    print(f"         eventType: {event.get('eventType')}")
                    print(
                        f"         icebergSubtype: {event.get('icebergSubtype', 'NOT FOUND')}"
                    )
                    print(f"         side: {event.get('side')}")
                    print(f"         price: {event.get('price')}")
                    print(
                        f"         size: {event.get('size')} / totalSize: {event.get('totalSize')}"
                    )
                    print(f"         cbdrWindow: {event.get('cbdrWindow')}")

                    if "icebergSubtype" not in event:
                        print(f"         ✗ WARNING: icebergSubtype field missing!")
                    elif event.get("icebergSubtype") in [
                        "TRADE",
                        "EXECUTION",
                        "DETECTION",
                        "CANCELLATION",
                        "MOVEMENT",
                    ]:
                        print(f"         ✓ Valid iceberg sub-type")
                except json.JSONDecodeError:
                    print(f"      ✗ Failed to parse JSON: {event_json[:100]}...")


def main():
    print("ICEBERG SUB-TYPE CAPTURE VERIFICATION")
    print("=" * 80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("This script verifies that iceberg sub-types (TRADE, EXECUTION, DETECTION,")
    print("CANCELLATION, MOVEMENT) are being captured correctly in both TimescaleDB")
    print("and Redis storage systems.")
    print()

    try:
        check_timescaledb()
    except Exception as e:
        print(f"\n✗ TimescaleDB check failed: {e}")

    try:
        check_redis()
    except Exception as e:
        print(f"\n✗ Redis check failed: {e}")

    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)
    print("\nNext Steps:")
    print("1. If no recent events found, wait for icebergs to occur in Bookmap")
    print("2. Verify 'icebergSubtype' field is populated with TRADE, EXECUTION, etc.")
    print("3. Verify STOP events have NULL iceberg_subtype")
    print("4. Update comprehensive_backtest.py to filter/weight by sub-type")
    print()


if __name__ == "__main__":
    main()
