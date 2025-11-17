"""
Export MBO, Absorption, and Icebergs/Stops data from Wednesday 6AM-9AM EST to CSV files.
"""

import psycopg2
import pandas as pd
from datetime import datetime, timedelta
import pytz

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}


def get_last_wednesday_morning():
    """Get the last Wednesday 6AM-9AM EST time range."""
    est = pytz.timezone("US/Eastern")
    now = datetime.now(est)

    # Find last Wednesday (0=Monday, 2=Wednesday)
    days_since_wednesday = (now.weekday() - 2) % 7
    if days_since_wednesday == 0 and now.hour < 9:
        # If today is Wednesday but before 9AM, go back to last week
        days_since_wednesday = 7

    last_wednesday = now - timedelta(days=days_since_wednesday)

    # Set to 6AM-9AM EST
    start_time = last_wednesday.replace(hour=6, minute=0, second=0, microsecond=0)
    end_time = last_wednesday.replace(hour=9, minute=0, second=0, microsecond=0)

    return start_time, end_time


def export_mbo_data(conn, start_time, end_time, output_file):
    """Export MBO data to CSV (only orders with size >= 20)."""
    query = """
        SELECT 
            timestamp AT TIME ZONE 'America/New_York' as timestamp_est,
            symbol,
            order_id,
            side,
            price,
            size,
            order_type,
            action,
            session_id,
            data_type,
            cbdr_window
        FROM mbo_data
        WHERE timestamp >= %s AND timestamp < %s
            AND size >= 20
        ORDER BY timestamp
    """

    print(f"\nExporting MBO data from {start_time} to {end_time}...")
    df = pd.read_sql_query(query, conn, params=(start_time, end_time))
    df.to_csv(output_file, index=False)
    print(f"✓ Exported {len(df):,} MBO records to {output_file}")
    return len(df)


def export_absorption_data(conn, start_time, end_time, output_file):
    """Export Absorption events to CSV."""
    query = """
        SELECT 
            timestamp AT TIME ZONE 'America/New_York' as timestamp_est,
            symbol,
            event_type,
            price,
            absorbed_volume,
            aggressor_volume,
            imbalance_ratio,
            session_id,
            cbdr_window,
            is_in_cbdr,
            significance_score
        FROM absorption_events
        WHERE timestamp >= %s AND timestamp < %s
        ORDER BY timestamp
    """

    print(f"\nExporting Absorption data from {start_time} to {end_time}...")
    df = pd.read_sql_query(query, conn, params=(start_time, end_time))
    df.to_csv(output_file, index=False)
    print(f"✓ Exported {len(df):,} Absorption records to {output_file}")
    return len(df)


def export_stops_icebergs_data(conn, start_time, end_time, output_file):
    """Export Stops & Icebergs events to CSV."""
    query = """
        SELECT 
            timestamp AT TIME ZONE 'America/New_York' as timestamp_est,
            symbol,
            event_type,
            price,
            detected_size,
            estimated_total_size,
            confidence_score,
            session_id,
            cbdr_window,
            iceberg_subtype
        FROM stops_icebergs
        WHERE timestamp >= %s AND timestamp < %s
        ORDER BY timestamp
    """

    print(f"\nExporting Stops & Icebergs data from {start_time} to {end_time}...")
    df = pd.read_sql_query(query, conn, params=(start_time, end_time))
    df.to_csv(output_file, index=False)
    print(f"✓ Exported {len(df):,} Stops/Icebergs records to {output_file}")
    return len(df)


def main():
    """Export all data types for Wednesday morning session."""
    try:
        # Get last Wednesday 6AM-9AM EST
        start_time, end_time = get_last_wednesday_morning()

        print("=" * 70)
        print("EXPORTING WEDNESDAY MORNING DATA (6AM-9AM EST)")
        print("=" * 70)
        print(f"Date: {start_time.strftime('%Y-%m-%d')}")
        print(
            f"Time Range: {start_time.strftime('%H:%M:%S')} - {end_time.strftime('%H:%M:%S')} EST"
        )

        # Create output directory
        output_dir = "outputs/exports"
        import os

        os.makedirs(output_dir, exist_ok=True)

        # Generate filenames with date
        date_str = start_time.strftime("%Y%m%d")
        mbo_file = f"{output_dir}/mbo_data_wed_{date_str}_6am_9am.csv"
        absorption_file = f"{output_dir}/absorption_data_wed_{date_str}_6am_9am.csv"
        stops_file = f"{output_dir}/stops_icebergs_data_wed_{date_str}_6am_9am.csv"

        # Connect to database
        print("\nConnecting to PostgreSQL...")
        conn = psycopg2.connect(**DB_CONFIG)

        # Export each data type
        total_records = 0
        total_records += export_mbo_data(conn, start_time, end_time, mbo_file)
        total_records += export_absorption_data(
            conn, start_time, end_time, absorption_file
        )
        total_records += export_stops_icebergs_data(
            conn, start_time, end_time, stops_file
        )

        conn.close()

        print("\n" + "=" * 70)
        print(f"✓ EXPORT COMPLETE - Total records: {total_records:,}")
        print("=" * 70)
        print("\nOutput files:")
        print(f"  • MBO Data: {mbo_file}")
        print(f"  • Absorption: {absorption_file}")
        print(f"  • Stops/Icebergs: {stops_file}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
