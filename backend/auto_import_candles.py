#!/usr/bin/env python3
"""
Automated daily import of MNQ candle data from TradingView CSV exports.

Features:
- Auto-detects timeframe by analyzing timestamp increments (5m, 15m, 1h, etc.)
- Processes all CSVs in TradingView_Data directory
- Runs daily at 9:20 AM via Task Scheduler
- Logs all operations to import_candles.log
"""

import csv
import psycopg2
from datetime import datetime, timedelta
from pathlib import Path
import logging
from collections import Counter

# Setup logging
LOG_FILE = Path(__file__).parent.parent / "outputs" / "logs" / "import_candles.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}

# CSV source directory
CSV_DIR = Path("C:/Users/Kudzai/Downloads/TradingView_Data")


def detect_timeframe_from_data(csv_path, max_samples=50):
    """
    Detect timeframe by analyzing actual timestamp increments in the CSV.

    Args:
        csv_path: Path to CSV file
        max_samples: Number of rows to sample for analysis

    Returns:
        Timeframe string ('5m', '15m', '1h', '4h', '1d') or None
    """
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Find time column (case-insensitive)
            fieldnames_lower = {name.lower(): name for name in reader.fieldnames}
            time_col = (
                fieldnames_lower.get("time")
                or fieldnames_lower.get("timestamp")
                or fieldnames_lower.get("date")
            )

            if not time_col:
                logger.warning(f"No time column found in {csv_path.name}")
                return None

            # Sample timestamps
            timestamps = []
            for i, row in enumerate(reader):
                if i >= max_samples:
                    break
                try:
                    ts = datetime.fromisoformat(row[time_col])
                    timestamps.append(ts)
                except (ValueError, KeyError) as e:
                    logger.warning(f"Could not parse timestamp in row {i}: {e}")
                    continue

            if len(timestamps) < 2:
                logger.warning(f"Not enough valid timestamps in {csv_path.name}")
                return None

            # Calculate time differences (in minutes)
            diffs = []
            for i in range(1, len(timestamps)):
                diff_minutes = (timestamps[i] - timestamps[i - 1]).total_seconds() / 60
                if diff_minutes > 0:  # Ignore zero or negative diffs
                    diffs.append(diff_minutes)

            if not diffs:
                return None

            # Find most common interval
            counter = Counter(diffs)
            most_common_diff = counter.most_common(1)[0][0]

            # Map to timeframe (only valid database values)
            timeframe_map = {
                1: "1m",
                5: "5m",
                15: "15m",
                60: "1h",
                120: "2h",
                240: "4h",
                1440: "1d",
            }

            # Find closest match
            closest_tf = min(
                timeframe_map.keys(), key=lambda x: abs(x - most_common_diff)
            )

            # Check if interval matches an allowed timeframe (with tolerance)
            if abs(closest_tf - most_common_diff) > 5:  # Tolerance of 5 minutes
                logger.error(
                    f"Unsupported interval detected: {most_common_diff} minutes. "
                    f"Database only allows: 1m, 5m, 15m, 1h (60m), 2h (120m), 4h (240m), 1d (1440m)"
                )
                return None

            timeframe = timeframe_map[closest_tf]
            logger.info(
                f"Detected timeframe: {timeframe} (interval: {most_common_diff} min)"
            )
            return timeframe

    except Exception as e:
        logger.error(f"Error detecting timeframe from {csv_path.name}: {e}")
        return None


def parse_timestamp(time_str):
    """Parse ISO format timestamp to datetime object."""
    return datetime.fromisoformat(time_str)


def import_csv_file(filepath, conn, cursor):
    """
    Import a single CSV file into the database.

    Returns:
        Tuple of (rows_imported, timeframe) or (0, None) on failure
    """
    filename = filepath.name

    # Auto-detect timeframe from data
    timeframe = detect_timeframe_from_data(filepath)

    if not timeframe:
        logger.error(f"Could not detect timeframe for {filename}, skipping")
        return 0, None

    logger.info(f"Importing {filename} (timeframe: {timeframe})")

    # Check for duplicate data before importing
    try:
        import pandas as pd

        df = pd.read_csv(filepath)

        # Find time column (case-insensitive)
        columns = {col.lower(): col for col in df.columns}
        time_col = None
        for possible_name in ["time", "timestamp", "datetime", "date"]:
            if possible_name in columns:
                time_col = columns[possible_name]
                break

        if time_col and len(df) > 0:
            first_timestamp = pd.to_datetime(df[time_col].iloc[0])
            last_timestamp = pd.to_datetime(df[time_col].iloc[-1])
            total_rows = len(df)

            # Explicitly delete DataFrame to free file handle
            del df
            import gc

            gc.collect()

            cursor.execute(
                """
                SELECT COUNT(*) FROM ohlc_candles 
                WHERE symbol = 'MNQ' 
                AND timeframe = %s 
                AND timestamp >= %s 
                AND timestamp <= %s
            """,
                (timeframe, first_timestamp, last_timestamp),
            )

            existing_count = cursor.fetchone()[0]

            if existing_count >= total_rows:
                logger.info(
                    f"○ Skipping {filename}: All {total_rows} candles already exist in database"
                )
                return 0, timeframe
    except Exception as e:
        logger.warning(f"Could not check for duplicates in {filename}: {e}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Find column names (case-insensitive)
            fieldnames_lower = {name.lower(): name for name in reader.fieldnames}
            time_col = fieldnames_lower.get("time") or fieldnames_lower.get("timestamp")
            open_col = fieldnames_lower.get("open")
            high_col = fieldnames_lower.get("high")
            low_col = fieldnames_lower.get("low")
            close_col = fieldnames_lower.get("close")
            volume_col = fieldnames_lower.get("volume")

            # Check for VWAP columns (with exact match for special naming)
            vwap_930_col = None
            vwap_daily_col = None
            for col_name in reader.fieldnames:
                if "9:30" in col_name and "VWAP" in col_name.upper():
                    vwap_930_col = col_name
                elif "Daily" in col_name and "VWAP" in col_name.upper():
                    vwap_daily_col = col_name

            has_vwap = vwap_930_col or vwap_daily_col
            if has_vwap:
                logger.info(
                    f"VWAP columns found: 9:30={vwap_930_col}, Daily={vwap_daily_col}"
                )

            if not all([time_col, open_col, high_col, low_col, close_col]):
                logger.error(f"Missing required columns in {filename}")
                return 0, None

            batch = []
            vwap_batch = []
            batch_size = 1000
            row_count = 0
            vwap_count = 0
            session_id = f"auto_import_{datetime.now().strftime('%Y%m%d_%H%M')}"

            for row in reader:
                try:
                    # Parse timestamp
                    timestamp = parse_timestamp(row[time_col])

                    # Parse prices
                    open_price = float(row[open_col])
                    high_price = float(row[high_col])
                    low_price = float(row[low_col])
                    close_price = float(row[close_col])
                    volume = int(float(row.get(volume_col, 0) or 0))

                    batch.append(
                        (
                            timestamp,
                            "MNQ",
                            timeframe,
                            open_price,
                            high_price,
                            low_price,
                            close_price,
                            volume,
                            session_id,
                        )
                    )

                    # Parse VWAP values if columns exist
                    if has_vwap:
                        vwap_930 = None
                        vwap_daily = None

                        if vwap_930_col:
                            val = row.get(vwap_930_col, "").strip()
                            if val and val.lower() not in ["", "nan", "null"]:
                                try:
                                    vwap_930 = float(val)
                                except ValueError:
                                    pass

                        if vwap_daily_col:
                            val = row.get(vwap_daily_col, "").strip()
                            if val and val.lower() not in ["", "nan", "null"]:
                                try:
                                    vwap_daily = float(val)
                                except ValueError:
                                    pass

                        # Only insert if at least one VWAP value exists
                        if vwap_930 is not None or vwap_daily is not None:
                            vwap_batch.append(
                                (
                                    timestamp,
                                    "MNQ",
                                    timeframe,
                                    vwap_930,
                                    vwap_daily,
                                    session_id,
                                )
                            )

                    # Insert batch when full
                    if len(batch) >= batch_size:
                        insert_batch(cursor, batch)
                        affected_rows = cursor.rowcount
                        conn.commit()
                        row_count += affected_rows
                        batch = []

                        # Insert VWAP batch if exists
                        if vwap_batch:
                            insert_vwap_batch(cursor, vwap_batch)
                            vwap_affected = cursor.rowcount
                            conn.commit()
                            vwap_count += vwap_affected
                            vwap_batch = []

                except (ValueError, KeyError) as e:
                    logger.warning(f"Skipping invalid row in {filename}: {e}")
                    continue

            # Insert remaining rows
            if batch:
                insert_batch(cursor, batch)
                affected_rows = cursor.rowcount
                conn.commit()
                row_count += affected_rows

            # Insert remaining VWAP rows
            if vwap_batch:
                insert_vwap_batch(cursor, vwap_batch)
                vwap_affected = cursor.rowcount
                conn.commit()
                vwap_count += vwap_affected

            if row_count > 0:
                logger.info(f"✓ Imported {row_count} new candles from {filename}")
                if vwap_count > 0:
                    logger.info(f"✓ Imported {vwap_count} VWAP records from {filename}")
            else:
                logger.info(f"○ No new data in {filename} (all candles already exist)")
            return row_count, timeframe

    except Exception as e:
        logger.error(f"Error importing {filename}: {e}")
        return 0, None


def insert_batch(cursor, batch):
    """Insert batch of candles with conflict resolution."""
    sql = """
        INSERT INTO ohlc_candles 
        (timestamp, symbol, timeframe, open, high, low, close, volume, session_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (timestamp, symbol, timeframe) 
        DO NOTHING
    """
    cursor.executemany(sql, batch)


def insert_vwap_batch(cursor, batch):
    """Insert batch of VWAP records with conflict resolution."""
    sql = """
        INSERT INTO vwap_levels 
        (timestamp, symbol, timeframe, vwap_930am, vwap_daily, session_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (timestamp, symbol, timeframe) 
        DO UPDATE SET
            vwap_930am = COALESCE(EXCLUDED.vwap_930am, vwap_levels.vwap_930am),
            vwap_daily = COALESCE(EXCLUDED.vwap_daily, vwap_levels.vwap_daily),
            session_id = EXCLUDED.session_id
    """
    cursor.executemany(sql, batch)


def get_database_summary(cursor):
    """Get summary statistics from database."""
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
    return cursor.fetchall()


def main():
    """Main automated import process."""
    logger.info("=" * 60)
    logger.info("Starting automated candle import")
    logger.info("=" * 60)

    # Check if CSV directory exists
    if not CSV_DIR.exists():
        logger.error(f"CSV directory not found: {CSV_DIR}")
        return

    # Find all CSV files
    csv_files = sorted(CSV_DIR.glob("*.csv"))

    if not csv_files:
        logger.warning(f"No CSV files found in {CSV_DIR}")
        return

    logger.info(f"Found {len(csv_files)} CSV files")

    # Track files to delete after successful import
    files_to_delete = []

    # Connect to database
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        logger.info("Connected to database")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return

    try:
        total_rows = 0
        successful_imports = 0
        timeframes_imported = set()

        for filepath in csv_files:
            try:
                rows, timeframe = import_csv_file(filepath, conn, cursor)

                # Track for deletion if import was attempted (even if 0 new rows)
                if timeframe:
                    files_to_delete.append(filepath)
                    timeframes_imported.add(timeframe)

                if rows > 0:
                    total_rows += rows
                    successful_imports += 1
            except Exception as e:
                logger.error(f"Failed to import {filepath.name}: {e}")
                # Rollback transaction to recover from error
                conn.rollback()
                continue

        # Delete successfully processed CSV files
        deleted_count = 0
        for filepath in files_to_delete:
            try:
                # Small delay to ensure file handles are closed
                import time

                time.sleep(0.1)
                filepath.unlink()
                deleted_count += 1
                logger.info(f"🗑 Deleted {filepath.name}")
            except Exception as e:
                logger.warning(f"Could not delete {filepath.name}: {e}")

        logger.info("=" * 60)
        logger.info("Import complete!")
        logger.info(f"  Files processed: {len(csv_files)}")
        logger.info(f"  Successful imports: {successful_imports}")
        logger.info(f"  Total rows imported: {total_rows:,}")
        logger.info(f"  Files deleted: {deleted_count}")
        logger.info(f"  Timeframes: {', '.join(sorted(timeframes_imported))}")
        logger.info("=" * 60)

        # Show database summary
        logger.info("\nDatabase summary:")
        for row in get_database_summary(cursor):
            timeframe, count, earliest, latest, min_price, max_price = row
            logger.info(f"  {timeframe}: {count:,} candles")
            logger.info(f"    Range: {earliest} to {latest}")
            logger.info(f"    Price: ${min_price:.2f} - ${max_price:.2f}")

    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        conn.rollback()

    finally:
        cursor.close()
        conn.close()
        logger.info("Database connection closed")


if __name__ == "__main__":
    main()
