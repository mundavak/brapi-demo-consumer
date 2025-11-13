#!/usr/bin/env python3
"""
Import properly formatted MNQ candle data from CSV files into TimescaleDB.

These CSVs already have:
- EST timestamps (no conversion needed)
- Actual MNQ prices (no conversion needed)
- Proper column names (time, open, high, low, close)
"""

import csv
import psycopg2
from datetime import datetime
from pathlib import Path

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}


def detect_timeframe(filename):
    """
    Detect timeframe from filename.

    Args:
        filename: CSV filename (e.g., 'CME_MINI_MNQZ2025, 15.csv')

    Returns:
        Timeframe string ('5m' or '15m')
    """
    if ", 5.csv" in filename or "_5.csv" in filename:
        return "5m"
    elif ", 15.csv" in filename or "_15.csv" in filename:
        return "15m"
    else:
        raise ValueError(f"Cannot detect timeframe from filename: {filename}")


def parse_timestamp(time_str):
    """
    Parse timestamp string to datetime object.

    Args:
        time_str: ISO format timestamp (e.g., '2025-09-24T12:45:00-04:00')

    Returns:
        datetime object
    """
    return datetime.fromisoformat(time_str)


def import_csv_file(filepath, conn, cursor):
    """
    Import a single CSV file into the database.

    Args:
        filepath: Path to CSV file
        conn: Database connection
        cursor: Database cursor

    Returns:
        Number of rows imported
    """
    filename = filepath.name
    timeframe = detect_timeframe(filename)

    print(f"\nImporting {filename} (timeframe: {timeframe})")

    with open(filepath, "r") as f:
        reader = csv.DictReader(f)

        batch = []
        batch_size = 1000
        row_count = 0

        for row in reader:
            # Parse timestamp (already in EST)
            timestamp = parse_timestamp(row["time"])

            # Prices are already correct
            open_price = float(row["open"])
            high_price = float(row["high"])
            low_price = float(row["low"])
            close_price = float(row["close"])
            volume = 0  # Not provided in CSV

            batch.append(
                (
                    timestamp,
                    "MNQ1!",  # Symbol
                    timeframe,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume,
                    "imported_csv_mnqz2025",  # session_id
                )
            )

            # Insert batch when full
            if len(batch) >= batch_size:
                insert_batch(cursor, batch)
                conn.commit()
                row_count += len(batch)
                print(f"  Inserted {row_count} rows...", end="\r")
                batch = []

        # Insert remaining rows
        if batch:
            insert_batch(cursor, batch)
            conn.commit()
            row_count += len(batch)

        print(f"  ✓ Imported {row_count} rows from {filename}")
        return row_count


def insert_batch(cursor, batch):
    """
    Insert a batch of candle data into the database.

    Args:
        cursor: Database cursor
        batch: List of tuples (timestamp, symbol, timeframe, open, high, low, close, volume, session_id)
    """
    sql = """
        INSERT INTO ohlc_candles 
        (timestamp, symbol, timeframe, open, high, low, close, volume, session_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (timestamp, symbol, timeframe) 
        DO UPDATE SET
            open = EXCLUDED.open,
            high = EXCLUDED.high,
            low = EXCLUDED.low,
            close = EXCLUDED.close,
            volume = EXCLUDED.volume
    """
    cursor.executemany(sql, batch)


def main():
    """Main import process."""
    csv_dir = Path("H:/")

    # Find all CSV files
    csv_files = sorted(csv_dir.glob("CME_MINI_MNQZ2025*.csv"))

    if not csv_files:
        print("❌ No CSV files found in H:\\")
        return

    print(f"Found {len(csv_files)} CSV files to import:")
    for f in csv_files:
        print(f"  - {f.name}")

    # Confirm before proceeding
    response = input("\nProceed with import? (y/n): ")
    if response.lower() != "y":
        print("Import cancelled.")
        return

    # Connect to database
    print("\nConnecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        total_rows = 0

        for filepath in csv_files:
            rows_imported = import_csv_file(filepath, conn, cursor)
            total_rows += rows_imported

        print(f"\n{'='*60}")
        print("✓ Import complete!")
        print(f"  Total files processed: {len(csv_files)}")
        print(f"  Total rows imported: {total_rows:,}")
        print(f"{'='*60}")

        # Show summary statistics
        print("\nDatabase summary:")
        cursor.execute(
            """
            SELECT 
                timeframe,
                COUNT(*) as candle_count,
                MIN(timestamp) as earliest,
                MAX(timestamp) as latest,
                MIN(close) as min_price,
                MAX(close) as max_price
            FROM ohlc_candles
            WHERE symbol = 'MNQ1!'
            GROUP BY timeframe
            ORDER BY timeframe
        """
        )

        for row in cursor.fetchall():
            timeframe, count, earliest, latest, min_price, max_price = row
            print(f"  {timeframe}: {count:,} candles")
            print(f"    Date range: {earliest} to {latest}")
            print(f"    Price range: {min_price:.2f} to {max_price:.2f}")

    except Exception as e:
        print(f"\n❌ Error during import: {e}")
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    main()
