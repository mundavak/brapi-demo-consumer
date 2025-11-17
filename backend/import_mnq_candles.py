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
        filename: CSV filename (e.g., 'MNQ_5m_MNQ1!_2025-11-17T12-01-56.csv' or 'CME_MINI_MNQZ2025, 15.csv')

    Returns:
        Timeframe string ('5m' or '15m')
    """
    # TradingView format: MNQ_15m_... (check 15m first since it contains "5")
    if "_15m_" in filename or "15m_MNQ" in filename:
        return "15m"
    elif "_5m_" in filename or "5m_MNQ" in filename:
        return "5m"
    # Old format: ..., 5.csv or ..., 15.csv
    elif ", 15.csv" in filename or "_15.csv" in filename:
        return "15m"
    elif ", 5.csv" in filename or "_5.csv" in filename:
        return "5m"
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
            volume = int(
                float(row.get("Volume", 0) or 0)
            )  # TradingView may have volume

            batch.append(
                (
                    timestamp,
                    "MNQ",  # Symbol (use MNQ to match existing data)
                    timeframe,
                    open_price,
                    high_price,
                    low_price,
                    close_price,
                    volume,
                    f"imported_tradingview_{datetime.now().strftime('%Y%m%d')}",  # session_id
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
    # Try TradingView directory first, then fall back to H:\
    csv_dir = Path("C:/Users/Kudzai/Downloads/TradingView_Data")

    if not csv_dir.exists():
        print(f"❌ Directory not found: {csv_dir}")
        csv_dir = Path("H:/")
        print(f"Trying fallback directory: {csv_dir}")

    # Find all CSV files (TradingView format or old format)
    csv_files = sorted(csv_dir.glob("MNQ_*.csv"))
    if not csv_files:
        csv_files = sorted(csv_dir.glob("CME_MINI_MNQZ2025*.csv"))

    if not csv_files:
        print(f"❌ No CSV files found in {csv_dir}")
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
            WHERE symbol = 'MNQ'
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
