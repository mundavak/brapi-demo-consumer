#!/usr/bin/env python3
"""
Import MNQ candle data from CSV files into TimescaleDB.

Handles:
- Timezone conversion (UTC to EST/EDT)
- Price conversion (likely /4 for MNQ micro points)
- 5-minute and 15-minute timeframes
- Batch inserts for performance
"""

import os
import csv
import psycopg2
from datetime import datetime
import pytz
from pathlib import Path

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}

# Price conversion factor
# CSV prices are in index points that need to be multiplied to match actual MNQ prices
# Example: CSV has ~100, actual MNQ is ~26,000, so multiplier ≈ 260
PRICE_MULTIPLIER = 260.0

# Timezone conversion
UTC = pytz.UTC
EST = pytz.timezone("US/Eastern")


def convert_timestamp(utc_str):
    """
    Convert UTC timestamp string to EST datetime.

    Args:
        utc_str: ISO format UTC timestamp (e.g., '2024-09-20T22:15:17.035Z')

    Returns:
        datetime object in EST timezone
    """
    # Parse UTC timestamp
    dt_utc = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))

    # Convert to EST
    dt_est = dt_utc.astimezone(EST)

    return dt_est


def convert_price(price_str):
    """
    Convert MNQ micro price to standard NQ price points.

    Args:
        price_str: Price as string

    Returns:
        Converted price as float
    """
    return float(price_str) * PRICE_MULTIPLIER


def detect_timeframe(filename):
    """
    Detect timeframe from filename.

    Args:
        filename: CSV filename

    Returns:
        Timeframe string ('5m' or '15m')
    """
    if "MNQ1!_CME_5" in filename:
        return "5m"
    elif "MNQ1!_CME_15" in filename:
        return "15m"
    else:
        raise ValueError(f"Cannot detect timeframe from filename: {filename}")


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
    filename = os.path.basename(filepath)
    timeframe = detect_timeframe(filename)

    print(f"\nImporting {filename} (timeframe: {timeframe}m)")

    with open(filepath, "r") as f:
        reader = csv.DictReader(f)

        batch = []
        batch_size = 1000
        row_count = 0

        for row in reader:
            # Convert timestamp
            timestamp_est = convert_timestamp(row["datetime"])

            # Convert prices
            open_price = convert_price(row["open"])
            high_price = convert_price(row["high"])
            low_price = convert_price(row["low"])
            close_price = convert_price(row["close"])
            volume = int(row["volume"])

            batch.append(
                (
                    timestamp_est,
                    "MNQ1!",  # Symbol
                    timeframe,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume,
                    "imported_csv",  # session_id
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
    csv_files_5m = sorted(csv_dir.glob("MNQ1!_CME_5_*.csv"))
    csv_files_15m = sorted(csv_dir.glob("MNQ1!_CME_15_*.csv"))

    all_files = csv_files_5m + csv_files_15m

    if not all_files:
        print("❌ No CSV files found in H:\\")
        return

    print(
        f"Found {len(csv_files_5m)} 5-minute files and {len(csv_files_15m)} 15-minute files"
    )
    print(f"Total: {len(all_files)} files to import\n")

    # Confirm before proceeding
    response = input("Proceed with import? (y/n): ")
    if response.lower() != "y":
        print("Import cancelled.")
        return

    # Connect to database
    print("\nConnecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        total_rows = 0

        for filepath in all_files:
            rows_imported = import_csv_file(filepath, conn, cursor)
            total_rows += rows_imported

        print(f"\n{'='*60}")
        print("✓ Import complete!")
        print(f"  Total files processed: {len(all_files)}")
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
                MAX(timestamp) as latest
            FROM ohlc_candles
            WHERE symbol = 'MNQ1!'
            GROUP BY timeframe
            ORDER BY timeframe
        """
        )

        for row in cursor.fetchall():
            timeframe, count, earliest, latest = row
            print(f"  {timeframe}: {count:,} candles ({earliest} to {latest})")

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
