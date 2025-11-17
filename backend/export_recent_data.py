"""
Exports the last 12 hours of trading data from TimescaleDB to CSV files.

This script connects to the trading_data database and exports data from:
- mbo_data
- absorption_events
- stops_icebergs
"""

import pandas as pd
import psycopg2
from pathlib import Path
from datetime import datetime, timedelta
import sys

# Configuration
OUTPUT_DIR = Path("./outputs/exports")
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}
TABLES_TO_EXPORT = ["mbo_data", "absorption_events", "stops_icebergs"]


def get_db_connection():
    """Create database connection."""
    return psycopg2.connect(**DB_CONFIG)


def export_table_to_csv(conn, table_name):
    """Exports the last 12 hours of data from a table to a CSV file."""
    print("=" * 80)
    print(f"EXPORTING: {table_name}")
    print("=" * 80)

    # Calculate the time 12 hours ago
    twelve_hours_ago = datetime.utcnow() - timedelta(hours=12)

    # Check if table has a timestamp column
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = %s 
            AND (column_name = 'timestamp' OR column_name = 'ts_event')
        """,
            (table_name,),
        )

        timestamp_col = cur.fetchone()
        if not timestamp_col:
            print(
                f"❌ Skipping table '{table_name}': No 'timestamp' or 'ts_event' column found."
            )
            return

        timestamp_col = timestamp_col[0]
        print(f"Using timestamp column: '{timestamp_col}'")

    # Construct the query
    query = f"""
        SELECT * 
        FROM {table_name} 
        WHERE {timestamp_col} >= %s
    """

    # Add specific filter for mbo_data
    if table_name == "mbo_data":
        query += " AND size >= 20"
        print("Applying filter: size >= 20")

    query += f" ORDER BY {timestamp_col} DESC"

    print(f"Querying data since: {twelve_hours_ago.isoformat()} UTC")

    # Execute query and fetch into a pandas DataFrame
    df = pd.read_sql_query(query, conn, params=(twelve_hours_ago,))

    if df.empty:
        print("No data found in the last 12 hours.")
        print("=" * 80)
        print()
        return

    print(f"Found {len(df):,} rows.")

    # Create filename
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{table_name}_export_{timestamp_str}.csv"
    output_path = OUTPUT_DIR / filename

    # Create output directory if it doesn't exist
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Save to CSV
    print(f"Saving to: {output_path}")
    df.to_csv(output_path, index=False)

    print(f"✅ Successfully exported to {filename}")
    print("=" * 80)
    print()


def main():
    """Main export process."""
    print("\n")
    print("=" * 80)
    print("DATABASE EXPORT SCRIPT")
    print("=" * 80)
    print(f"Output Directory: {OUTPUT_DIR.resolve()}")
    print(f"Database: {DB_CONFIG['database']}@{DB_CONFIG['host']}")
    print()

    # Connect to database
    print("Connecting to TimescaleDB...")
    conn = get_db_connection()
    print("✅ Connected!")
    print()

    try:
        for table in TABLES_TO_EXPORT:
            export_table_to_csv(conn, table)

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        import traceback

        traceback.print_exc()
    finally:
        conn.close()
        print("\n✅ Database connection closed")


if __name__ == "__main__":
    main()
