#!/usr/bin/env python3
"""
Export MBO, Stops/Icebergs, and Absorption data from the last 8 hours
"""

import psycopg2
import csv
from datetime import datetime, timedelta
import os

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}

# Calculate time range (last 8 hours)
end_time = datetime.now()
start_time = end_time - timedelta(hours=8)

# Output directory
OUTPUT_DIR = "F:/TradingAgent/deaProjects/brapi-demo-consumer/outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Timestamp for filenames
timestamp_str = end_time.strftime("%Y%m%d_%H%M%S")

print("=" * 70)
print(f"Exporting data from last 8 hours")
print(f"Start time: {start_time.strftime('%Y-%m-%d %H:%M:%S')} EST")
print(f"End time:   {end_time.strftime('%Y-%m-%d %H:%M:%S')} EST")
print("=" * 70)

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # ============================================
    # 1. Export MBO Data
    # ============================================
    print("\n1. Exporting MBO data...")

    mbo_query = """
        SELECT 
            timestamp AT TIME ZONE 'America/New_York' as est_time,
            symbol,
            order_id,
            side,
            price,
            size,
            order_type,
            action,
            session_id,
            cbdr_window,
            data_type
        FROM mbo_data
        WHERE timestamp >= %s AND timestamp <= %s
        ORDER BY timestamp ASC
    """

    cursor.execute(mbo_query, (start_time, end_time))
    mbo_records = cursor.fetchall()

    mbo_file = os.path.join(OUTPUT_DIR, f"mbo_data_last_8h_{timestamp_str}.csv")
    with open(mbo_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "timestamp",
                "symbol",
                "order_id",
                "side",
                "price",
                "size",
                "order_type",
                "action",
                "session_id",
                "cbdr_window",
                "data_type",
            ]
        )
        writer.writerows(mbo_records)

    print(f"   ✓ Exported {len(mbo_records):,} MBO records")
    print(f"   → {mbo_file}")

    # ============================================
    # 2. Export Stops & Icebergs
    # ============================================
    print("\n2. Exporting Stops & Icebergs data...")

    stops_query = """
        SELECT 
            timestamp AT TIME ZONE 'America/New_York' as est_time,
            symbol,
            event_type,
            side,
            price,
            detected_size,
            estimated_total_size,
            fill_count,
            confidence_score,
            duration_ms,
            session_id,
            cbdr_window,
            iceberg_subtype
        FROM stops_icebergs
        WHERE timestamp >= %s AND timestamp <= %s
        ORDER BY timestamp ASC
    """

    cursor.execute(stops_query, (start_time, end_time))
    stops_records = cursor.fetchall()

    stops_file = os.path.join(OUTPUT_DIR, f"stops_icebergs_last_8h_{timestamp_str}.csv")
    with open(stops_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "timestamp",
                "symbol",
                "event_type",
                "side",
                "price",
                "detected_size",
                "estimated_total_size",
                "fill_count",
                "confidence_score",
                "duration_ms",
                "session_id",
                "cbdr_window",
                "iceberg_subtype",
            ]
        )
        writer.writerows(stops_records)

    print(f"   ✓ Exported {len(stops_records):,} Stops/Icebergs records")
    print(f"   → {stops_file}")

    # ============================================
    # 3. Export Absorption Events
    # ============================================
    print("\n3. Exporting Absorption events...")

    absorption_query = """
        SELECT 
            timestamp AT TIME ZONE 'America/New_York' as est_time,
            symbol,
            event_type,
            side,
            price,
            absorbed_volume,
            aggressor_volume,
            liquidity_removed,
            absorption_ratio,
            imbalance_ratio,
            session_id,
            cbdr_window,
            is_in_cbdr,
            significance_score
        FROM absorption_events
        WHERE timestamp >= %s AND timestamp <= %s
        ORDER BY timestamp ASC
    """

    cursor.execute(absorption_query, (start_time, end_time))
    absorption_records = cursor.fetchall()

    absorption_file = os.path.join(
        OUTPUT_DIR, f"absorption_events_last_8h_{timestamp_str}.csv"
    )
    with open(absorption_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "timestamp",
                "symbol",
                "event_type",
                "side",
                "price",
                "absorbed_volume",
                "aggressor_volume",
                "liquidity_removed",
                "absorption_ratio",
                "imbalance_ratio",
                "session_id",
                "cbdr_window",
                "is_in_cbdr",
                "significance_score",
            ]
        )
        writer.writerows(absorption_records)

    print(f"   ✓ Exported {len(absorption_records):,} Absorption records")
    print(f"   → {absorption_file}")

    # ============================================
    # Summary Statistics
    # ============================================
    print("\n" + "=" * 70)
    print("EXPORT SUMMARY")
    print("=" * 70)

    total_records = len(mbo_records) + len(stops_records) + len(absorption_records)
    print(f"Total records exported: {total_records:,}")
    print(f"  - MBO data:           {len(mbo_records):,}")
    print(f"  - Stops/Icebergs:     {len(stops_records):,}")
    print(f"  - Absorption events:  {len(absorption_records):,}")
    print(f"\nFiles saved to: {OUTPUT_DIR}")

    # Get symbols and session info
    print("\n" + "-" * 70)
    print("DATA BREAKDOWN BY SYMBOL")
    print("-" * 70)

    for table_name, query_name in [
        ("mbo_data", "MBO"),
        ("stops_icebergs", "Stops/Icebergs"),
        ("absorption_events", "Absorption"),
    ]:
        cursor.execute(
            f"""
            SELECT symbol, COUNT(*) as count
            FROM {table_name}
            WHERE timestamp >= %s AND timestamp <= %s
            GROUP BY symbol
            ORDER BY count DESC
        """,
            (start_time, end_time),
        )

        symbol_counts = cursor.fetchall()
        if symbol_counts:
            print(f"\n{query_name}:")
            for symbol, count in symbol_counts:
                print(f"  {symbol}: {count:,} records")
        else:
            print(f"\n{query_name}: No data")

    cursor.close()
    conn.close()

    print("\n" + "=" * 70)
    print("✓ Export completed successfully!")
    print("=" * 70)

except psycopg2.Error as e:
    print(f"\n✗ Database error: {e}")
    exit(1)
except Exception as e:
    print(f"\n✗ Error: {e}")
    exit(1)
