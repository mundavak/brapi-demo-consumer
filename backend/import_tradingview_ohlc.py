"""
Import OHLC candle data from TradingView CSV exports into TimescaleDB.

This script:
1. Cleans up all existing OHLC data in TimescaleDB
2. Imports 15m and 5m candle data from TradingView CSV files
3. Handles UTC-5 (EST) timestamps from TradingView
"""

import pandas as pd
import psycopg2
from pathlib import Path
from datetime import datetime
import sys
import json
import os

# Configuration
CSV_DIR = Path("C:/Users/Kudzai/Downloads/TradingView_Data")
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}


def get_db_connection():
    """Create database connection."""
    return psycopg2.connect(**DB_CONFIG)


def get_existing_date_range(conn, symbol, timeframe):
    """Get the existing date range for a symbol/timeframe combination."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*), MIN(timestamp), MAX(timestamp)
            FROM ohlc_candles
            WHERE symbol = %s AND timeframe = %s
        """,
            (symbol, timeframe),
        )

        result = cur.fetchone()
        if result and result[0] > 0:
            return {"count": result[0], "first": result[1], "last": result[2]}
        return None


def create_candle_table(conn):
    """Create or recreate the OHLC candles table."""
    print("Creating/verifying candles table...")

    with conn.cursor() as cur:
        # Create table if not exists (with all columns from existing schema)
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ohlc_candles (
                timestamp TIMESTAMPTZ NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                open NUMERIC NOT NULL,
                high NUMERIC NOT NULL,
                low NUMERIC NOT NULL,
                close NUMERIC NOT NULL,
                volume BIGINT NOT NULL DEFAULT 0,
                trade_count INTEGER NOT NULL DEFAULT 0,
                session_id VARCHAR(100) NOT NULL,
                vwap NUMERIC,
                cbdr_window VARCHAR(50),
                metadata JSONB,
                PRIMARY KEY (timestamp, symbol, timeframe)
            )
        """
        )

        # Create hypertable if not already
        try:
            cur.execute(
                """
                SELECT create_hypertable('ohlc_candles', 'timestamp', 
                    if_not_exists => TRUE,
                    migrate_data => TRUE
                )
            """
            )
            print("✅ Hypertable created/verified")
        except psycopg2.errors.UniqueViolation:
            print("✅ Hypertable already exists")
        except Exception as e:
            print(f"⚠️ Hypertable creation: {e}")

        # Create indexes
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_candles_symbol_timeframe 
            ON ohlc_candles (symbol, timeframe, timestamp DESC)
        """
        )

        conn.commit()
        print("✅ Table and indexes ready")
        print()


def import_csv_file(conn, csv_path):
    """Import a single CSV file into TimescaleDB (new candles only).

    Returns:
        dict: Import statistics including before/after counts and date ranges
    """
    print("=" * 80)
    print(f"IMPORTING: {csv_path.name}")
    print("=" * 80)

    # Parse filename to extract symbol and timeframe
    # Format: MNQ_15m_MNQ1!_2025-11-13T23-12-55.csv
    parts = csv_path.stem.split("_")
    symbol = parts[0]  # MNQ
    timeframe = parts[1]  # 15m or 5m

    print(f"Symbol: {symbol}")
    print(f"Timeframe: {timeframe}")

    # Check what's already in the database
    existing = get_existing_date_range(conn, symbol, timeframe)
    before_count = existing["count"] if existing else 0
    before_last = str(existing["last"]) if existing else None

    if existing:
        print(f"\nExisting data in database:")
        print(f"  Count: {existing['count']:,} candles")
        print(f"  Range: {existing['first']} to {existing['last']}")
    else:
        print(f"\nNo existing data found - will import all candles")
    print()

    # Read CSV
    print(f"Reading CSV file...")
    df = pd.read_csv(csv_path)

    print(f"Total rows: {len(df):,}")
    print(f"Columns: {', '.join(df.columns)}")
    print()

    # Show first few rows
    print("First 3 rows:")
    print(df.head(3))
    print()

    # Parse timestamps - TradingView exports in EST (UTC-5) with timezone info
    print("Parsing timestamps (EST → UTC)...")
    df["timestamp"] = pd.to_datetime(df["time"], utc=True)

    # If timestamps have timezone info, convert to UTC; otherwise assume EST
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = (
            df["timestamp"].dt.tz_localize("US/Eastern").dt.tz_convert("UTC")
        )
    else:
        df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

    print(f"First timestamp: {df['timestamp'].iloc[0]} (UTC)")
    print(f"Last timestamp: {df['timestamp'].iloc[-1]} (UTC)")
    print()

    # Prepare data for insertion
    records = []
    for _, row in df.iterrows():
        # TradingView exports don't include volume, use 0 as placeholder
        volume = int(row.get("Volume", row.get("volume", 0)))

        # Generate session_id from timestamp
        ts = row["timestamp"]
        session_id = f"{symbol}_{ts.strftime('%Y%m%d')}"

        records.append(
            (
                row["timestamp"],
                symbol,
                timeframe,
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                volume,
                0,  # trade_count
                session_id,
            )
        )

    # Batch insert (skip duplicates)
    print(f"Processing {len(records):,} candles from CSV...")

    # Get count before insert
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM ohlc_candles 
            WHERE symbol = %s AND timeframe = %s
        """,
            (symbol, timeframe),
        )
        count_before = cur.fetchone()[0]

    with conn.cursor() as cur:
        # Use ON CONFLICT DO NOTHING to skip duplicates
        cur.executemany(
            """
            INSERT INTO ohlc_candles 
            (timestamp, symbol, timeframe, open, high, low, close, volume, trade_count, session_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (timestamp, symbol, timeframe) DO NOTHING
        """,
            records,
        )

        conn.commit()

    # Get count after insert
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) FROM ohlc_candles 
            WHERE symbol = %s AND timeframe = %s
        """,
            (symbol, timeframe),
        )
        count_after = cur.fetchone()[0]

    new_candles = count_after - count_before
    skipped = len(records) - new_candles

    print(f"✅ Added {new_candles:,} new candles")
    print(f"⏭️  Skipped {skipped:,} duplicate candles")
    print("=" * 80)
    print()

    # Get final state for logging
    final_state = get_existing_date_range(conn, symbol, timeframe)
    after_last = str(final_state["last"]) if final_state else None

    return {
        "filename": csv_path.name,
        "symbol": symbol,
        "timeframe": timeframe,
        "csv_rows": len(records),
        "added": new_candles,
        "skipped": skipped,
        "before": {"count": before_count, "last_timestamp": before_last},
        "after": {"count": count_after, "last_timestamp": after_last},
    }


def verify_import(conn):
    """Verify the imported data."""
    print("=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    with conn.cursor() as cur:
        # Count by symbol and timeframe
        cur.execute(
            """
            SELECT symbol, timeframe, COUNT(*), MIN(timestamp), MAX(timestamp)
            FROM ohlc_candles
            GROUP BY symbol, timeframe
            ORDER BY symbol, timeframe
        """
        )

        results = cur.fetchall()

        print(f"\nImported data summary:")
        print(
            f"{'Symbol':<10} {'Timeframe':<12} {'Count':<12} {'First':<25} {'Last':<25}"
        )
        print("-" * 80)

        for symbol, timeframe, count, first_ts, last_ts in results:
            print(
                f"{symbol:<10} {timeframe:<12} {count:<12,} {str(first_ts):<25} {str(last_ts):<25}"
            )

        print()

        # Show sample data
        print("Sample candles (first 5):")
        cur.execute(
            """
            SELECT timestamp, symbol, timeframe, open, high, low, close, volume
            FROM ohlc_candles
            ORDER BY timestamp DESC
            LIMIT 5
        """
        )

        samples = cur.fetchall()
        for ts, sym, tf, o, h, l, c, v in samples:
            print(f"  {ts} | {sym} {tf} | O:{o} H:{h} L:{l} C:{c} V:{v}")

    print()
    print("=" * 80)
    print("✅ Import completed successfully!")
    print("=" * 80)


def main():
    """Main import process."""
    print("\n")
    print("=" * 80)
    print("TRADINGVIEW OHLC DATA IMPORT")
    print("=" * 80)
    print(f"CSV Directory: {CSV_DIR}")
    print(f"Database: {DB_CONFIG['database']}@{DB_CONFIG['host']}")
    print()

    # Find CSV files
    csv_files = list(CSV_DIR.glob("*.csv"))

    if not csv_files:
        print(f"❌ No CSV files found in {CSV_DIR}")
        sys.exit(1)

    print(f"Found {len(csv_files)} CSV files:")
    for csv_file in csv_files:
        print(f"  - {csv_file.name}")
    print()

    # Connect to database
    print("Connecting to TimescaleDB...")
    conn = get_db_connection()
    print("✅ Connected!")
    print()

    import_results = []

    try:
        # Step 1: Create/verify table
        create_candle_table(conn)

        # Step 2: Import each CSV file (new candles only)
        for csv_file in csv_files:
            result = import_csv_file(conn, csv_file)
            import_results.append(result)

        # Step 3: Verify import
        verify_import(conn)

        # Step 4: Log results to JSON file
        log_file = (
            CSV_DIR / f"import_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_files": len(csv_files),
                "total_added": sum(r["added"] for r in import_results),
                "total_skipped": sum(r["skipped"] for r in import_results),
            },
            "files": import_results,
        }

        with open(log_file, "w") as f:
            json.dump(log_data, f, indent=2)

        print("\n" + "=" * 80)
        print(f"📄 Import log saved to: {log_file.name}")
        print("=" * 80)

        # Step 5: Delete processed CSV files
        print("\n🗑️  Deleting processed CSV files...")
        for csv_file in csv_files:
            try:
                os.remove(csv_file)
                print(f"  ✅ Deleted: {csv_file.name}")
            except Exception as e:
                print(f"  ❌ Failed to delete {csv_file.name}: {e}")

        print("\n" + "=" * 80)
        print("✅ All CSV files processed and deleted")
        print("=" * 80)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()
        conn.rollback()
    finally:
        conn.close()
        print("\n✅ Database connection closed")


if __name__ == "__main__":
    main()
