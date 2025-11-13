#!/usr/bin/env python3
"""
Export morning session data (7:00 AM - 8:30 AM EST) from TimescaleDB to CSV files.
Exports MBO, stops/icebergs, and absorption/sweeps data for analysis.
"""

import psycopg2
import csv
from datetime import datetime
import os

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}

# Output directory
OUTPUT_DIR = "F:/TradingAgent/deaProjects/brapi-demo-consumer/outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Date and time range
DATE = "2025-11-11"
START_TIME = "07:00:00-05"
END_TIME = "08:30:00-05"


def export_mbo_data(cursor):
    """Export MBO (Market By Order) data."""
    print("Exporting MBO data...")

    sql = """
        SELECT 
            timestamp,
            symbol,
            price,
            side,
            action,
            size,
            order_id
        FROM mbo_data
        WHERE symbol LIKE '%%MNQ%%'
        AND timestamp >= '%s'
        AND timestamp <= '%s'
        ORDER BY timestamp ASC
    """ % (
        f"{DATE} {START_TIME}",
        f"{DATE} {END_TIME}",
    )

    cursor.execute(sql)
    rows = cursor.fetchall()

    filename = os.path.join(OUTPUT_DIR, f"mbo_data_{DATE}_0700-0830.csv")
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["timestamp", "symbol", "price", "side", "action", "size", "order_id"]
        )
        writer.writerows(rows)

    print(f"✓ MBO data exported: {len(rows)} records → {filename}")
    return len(rows)


def export_stops_icebergs(cursor):
    """Export stops and icebergs data."""
    print("Exporting stops/icebergs data...")

    sql = """
        SELECT 
            timestamp,
            symbol,
            price,
            side,
            event_type,
            iceberg_subtype,
            detected_size,
            confidence_score
        FROM stops_icebergs
        WHERE symbol LIKE '%%MNQ%%'
        AND timestamp >= '%s'
        AND timestamp <= '%s'
        ORDER BY timestamp ASC
    """ % (
        f"{DATE} {START_TIME}",
        f"{DATE} {END_TIME}",
    )

    cursor.execute(sql)
    rows = cursor.fetchall()

    filename = os.path.join(OUTPUT_DIR, f"stops_icebergs_{DATE}_0700-0830.csv")
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "timestamp",
                "symbol",
                "price",
                "side",
                "event_type",
                "iceberg_subtype",
                "detected_size",
                "confidence_score",
            ]
        )
        writer.writerows(rows)

    print(f"✓ Stops/Icebergs exported: {len(rows)} records → {filename}")
    return len(rows)


def export_absorption_sweeps(cursor):
    """Export absorption and sweep events."""
    print("Exporting absorption/sweeps data...")

    sql = """
        SELECT 
            timestamp,
            symbol,
            price,
            side,
            event_type,
            absorbed_volume,
            aggressor_volume,
            significance_score,
            cbdr_window
        FROM absorption_events
        WHERE symbol LIKE '%%MNQ%%'
        AND timestamp >= '%s'
        AND timestamp <= '%s'
        ORDER BY timestamp ASC
    """ % (
        f"{DATE} {START_TIME}",
        f"{DATE} {END_TIME}",
    )

    cursor.execute(sql)
    rows = cursor.fetchall()

    filename = os.path.join(OUTPUT_DIR, f"absorption_sweeps_{DATE}_0700-0830.csv")
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "timestamp",
                "symbol",
                "price",
                "side",
                "event_type",
                "absorbed_volume",
                "aggressor_volume",
                "significance_score",
                "cbdr_window",
            ]
        )
        writer.writerows(rows)

    print(f"✓ Absorption/Sweeps exported: {len(rows)} records → {filename}")
    return len(rows)


def export_mbo_summary(cursor):
    """Export aggregated MBO depth by price level."""
    print("Exporting MBO depth summary...")

    sql = """
        SELECT 
            FLOOR(price / 10) * 10 as price_level,
            side,
            action,
            COUNT(*) as order_count,
            SUM(size) as total_size,
            AVG(size) as avg_size,
            MIN(timestamp) as first_seen,
            MAX(timestamp) as last_seen
        FROM mbo_data
        WHERE symbol LIKE '%%MNQ%%'
        AND timestamp >= '%s'
        AND timestamp <= '%s'
        AND price BETWEEN 25400 AND 25700
        GROUP BY price_level, side, action
        ORDER BY price_level DESC, side, action
    """ % (
        f"{DATE} {START_TIME}",
        f"{DATE} {END_TIME}",
    )

    cursor.execute(sql)
    rows = cursor.fetchall()

    filename = os.path.join(OUTPUT_DIR, f"mbo_summary_{DATE}_0700-0830.csv")
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "price_level",
                "side",
                "action",
                "order_count",
                "total_size",
                "avg_size",
                "first_seen",
                "last_seen",
            ]
        )
        writer.writerows(rows)

    print(f"✓ MBO summary exported: {len(rows)} price levels → {filename}")
    return len(rows)


def export_absorption_summary(cursor):
    """Export aggregated absorption/sweep events by price level."""
    print("Exporting absorption/sweep summary...")

    sql = """
        SELECT 
            FLOOR(price / 10) * 10 as price_level,
            event_type,
            side,
            COUNT(*) as event_count,
            SUM(absorbed_volume) as total_volume,
            AVG(significance_score) as avg_significance,
            MIN(timestamp) as first_event,
            MAX(timestamp) as last_event
        FROM absorption_events
        WHERE symbol LIKE '%%MNQ%%'
        AND timestamp >= '%s'
        AND timestamp <= '%s'
        AND price BETWEEN 25400 AND 25700
        GROUP BY price_level, event_type, side
        ORDER BY price_level DESC, event_type, side
    """ % (
        f"{DATE} {START_TIME}",
        f"{DATE} {END_TIME}",
    )

    cursor.execute(sql)
    rows = cursor.fetchall()

    filename = os.path.join(OUTPUT_DIR, f"absorption_summary_{DATE}_0700-0830.csv")
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "price_level",
                "event_type",
                "side",
                "event_count",
                "total_volume",
                "avg_significance",
                "first_event",
                "last_event",
            ]
        )
        writer.writerows(rows)

    print(f"✓ Absorption/Sweep summary exported: {len(rows)} price levels → {filename}")
    return len(rows)


def main():
    print("=" * 80)
    print(f"Exporting Morning Session Data (7:00 AM - 8:30 AM EST)")
    print(f"Date: {DATE}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print("=" * 80)
    print()

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        # Export raw data
        mbo_count = export_mbo_data(cursor)
        stops_count = export_stops_icebergs(cursor)
        absorption_count = export_absorption_sweeps(cursor)

        print()
        print("-" * 80)
        print("Exporting aggregated summaries...")
        print("-" * 80)
        print()

        # Export summaries
        mbo_summary = export_mbo_summary(cursor)
        absorption_summary = export_absorption_summary(cursor)

        print()
        print("=" * 80)
        print("Export Complete!")
        print("=" * 80)
        print(f"Total Records Exported:")
        print(f"  - MBO Orders: {mbo_count:,}")
        print(f"  - Stops/Icebergs: {stops_count:,}")
        print(f"  - Absorption/Sweeps: {absorption_count:,}")
        print(f"  - MBO Summary Levels: {mbo_summary}")
        print(f"  - Absorption Summary Levels: {absorption_summary}")
        print()
        print(f"Files saved to: {OUTPUT_DIR}")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
