"""
Import MBO data from Databento CSV files into TimescaleDB
Focuses on trades (action='T') and adds (action='A')
Uses COPY for fast bulk loading with batch processing
"""

import psycopg2
from psycopg2.extras import execute_batch, Json
from pathlib import Path
from datetime import datetime
import csv
from collections import defaultdict

# Configuration
CSV_DIR = Path(r"H:\missing_mbo_csv_est")
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}

# Symbol mapping (Databento -> Bookmap format)
SYMBOL_MAP = {
    "MNQZ5": "MNQZ5.CME@RITHMIC",
    "MNQ": "MNQZ5.CME@RITHMIC",
}

# Action mappings from Databento to database
ACTION_MAP = {
    "T": "TRADE",  # Trade execution
    "A": "ADD",  # Add order to book
    "C": "CANCEL",  # Cancel order
    "M": "MODIFY",  # Modify order
    "F": "FILL",  # Fill (execution)
    "R": "REPLACE",  # Replace order
}

# Side mappings
SIDE_MAP = {
    "B": "BUY",
    "A": "SELL",  # Ask = Sell
    "N": "NONE",
}

BATCH_SIZE = 50_000  # Insert in batches for performance


def parse_timestamp(ts_str):
    """
    Parse ISO 8601 timestamp string to datetime
    Handles both with and without timezone info
    """
    if not ts_str or ts_str == "":
        return None

    try:
        # Remove timezone offset for parsing (already converted to EST)
        ts_clean = ts_str.split("+")[0].split("-", 3)
        if len(ts_clean) > 3:
            ts_clean = "-".join(ts_clean[:3])
        else:
            ts_clean = ts_str

        # Parse and assume EST timezone
        return datetime.fromisoformat(ts_clean)
    except Exception as e:
        print(f"    Warning: Failed to parse timestamp '{ts_str}': {e}")
        return None


def map_symbol(instrument_id):
    """Map Databento instrument ID to Bookmap symbol format"""
    for key, value in SYMBOL_MAP.items():
        if key in str(instrument_id):
            return value
    return f"{instrument_id}.CME@RITHMIC"


def process_csv_file(filepath, cursor, session_id):
    """
    Process a single CSV file and insert into database

    Args:
        filepath: Path to CSV file
        cursor: Database cursor
        session_id: Session identifier for this import

    Returns:
        Dictionary with import statistics
    """
    stats = defaultdict(int)
    batch = []

    print(f"\n  Processing: {filepath.name}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, 1):
                stats["total_rows"] += 1

                # Filter: Only process trades and adds
                action = row.get("action", "")
                if action not in ["T", "A"]:
                    stats["skipped_actions"] += 1
                    continue

                # Parse timestamp
                ts_event = parse_timestamp(row.get("ts_event", ""))
                if not ts_event:
                    stats["invalid_timestamp"] += 1
                    continue

                # Extract fields
                symbol = map_symbol(row.get("instrument_id", ""))
                order_id = int(row.get("order_id", 0)) if row.get("order_id") else 0
                side = SIDE_MAP.get(row.get("side", "N"), "NONE")
                price = (
                    float(row.get("price", 0)) / 1e9
                )  # Price is in 1e-9 fixed precision
                size = int(row.get("size", 0)) if row.get("size") else 0
                action_mapped = ACTION_MAP.get(action, action)

                # Build record tuple for batch insert
                record = (
                    ts_event,  # timestamp
                    symbol,  # symbol
                    order_id,  # order_id
                    side,  # side
                    price,  # price
                    size,  # size
                    "LIMIT",  # order_type (default to LIMIT)
                    action_mapped,  # action
                    session_id,  # session_id
                    "NONE",  # cbdr_window
                    None,  # metadata
                    Json({}),  # additional_data (wrap dict in Json)
                    "MBO",  # data_type
                )

                batch.append(record)
                stats["valid_records"] += 1

                # Insert batch when full
                if len(batch) >= BATCH_SIZE:
                    insert_batch(cursor, batch)
                    stats["batches_inserted"] += 1
                    batch = []

                # Progress update
                if row_num % 500_000 == 0:
                    print(
                        f"    {row_num:,} rows processed, {stats['valid_records']:,} valid records..."
                    )

        # Insert remaining records
        if batch:
            insert_batch(cursor, batch)
            stats["batches_inserted"] += 1

        print(f"    Complete: {stats['valid_records']:,} records inserted")

    except Exception as e:
        print(f"    ERROR: {e}")
        stats["errors"] = 1

    return dict(stats)


def insert_batch(cursor, batch):
    """
    Insert a batch of records using execute_batch for performance
    """
    insert_sql = """
        INSERT INTO mbo_data (
            timestamp, symbol, order_id, side, price, size,
            order_type, action, session_id, cbdr_window,
            metadata, additional_data, data_type
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (timestamp, symbol, order_id) DO NOTHING
    """

    execute_batch(cursor, insert_sql, batch, page_size=5000)


def main():
    """
    Main import function
    Processes all CSV files and imports to database
    """
    # Get list of CSV files
    csv_files = sorted(CSV_DIR.glob("*.csv"))

    if not csv_files:
        print(f"No CSV files found in {CSV_DIR}")
        return

    print("=" * 80)
    print("MBO Data Import - Trades and Adds Only")
    print("=" * 80)
    print(f"Source directory: {CSV_DIR}")
    print(f"Files to process: {len(csv_files)}")
    print(f"Target table:     mbo_data")
    print(f"Actions:          T (Trade), A (Add)")
    print(f"Batch size:       {BATCH_SIZE:,}")
    print("=" * 80)

    # Connect to database
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Generate session ID for this import
    session_id = f"IMPORT_MBO_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    print(f"\nSession ID: {session_id}\n")

    # Check initial row count
    cursor.execute("SELECT COUNT(*) FROM mbo_data")
    initial_count = cursor.fetchone()[0]
    print(f"Initial row count: {initial_count:,}\n")

    # Process each file
    total_stats = defaultdict(int)
    start_time = datetime.now()

    for file_num, csv_file in enumerate(csv_files, 1):
        print(f"[{file_num}/{len(csv_files)}] {csv_file.name}")
        print(f"  Size: {csv_file.stat().st_size / (1024**3):.2f} GB")

        file_start = datetime.now()
        stats = process_csv_file(csv_file, cursor, session_id)
        file_elapsed = (datetime.now() - file_start).total_seconds()

        # Commit after each file
        conn.commit()

        # Aggregate stats
        for key, value in stats.items():
            total_stats[key] += value

        # Show file summary
        if stats.get("valid_records", 0) > 0:
            records_per_sec = stats["valid_records"] / file_elapsed
            print(f"    Speed: {records_per_sec:,.0f} records/sec")
            print(f"    Time: {file_elapsed:.1f} seconds")

    # Check final row count
    cursor.execute("SELECT COUNT(*) FROM mbo_data")
    final_count = cursor.fetchone()[0]
    rows_added = final_count - initial_count

    # Summary
    total_elapsed = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 80)
    print("IMPORT COMPLETE")
    print("=" * 80)
    print(f"Files processed:      {len(csv_files)}")
    print(f"Total rows scanned:   {total_stats['total_rows']:,}")
    print(f"Valid records:        {total_stats['valid_records']:,}")
    print(f"Rows added to DB:     {rows_added:,}")
    print(f"Skipped (actions):    {total_stats['skipped_actions']:,}")
    print(f"Invalid timestamps:   {total_stats['invalid_timestamp']:,}")
    print(f"Batches inserted:     {total_stats['batches_inserted']:,}")
    print(f"\nDatabase counts:")
    print(f"  Before: {initial_count:,}")
    print(f"  After:  {final_count:,}")
    print(f"  Added:  {rows_added:,}")
    print(
        f"\nTotal time:          {total_elapsed:.1f} seconds ({total_elapsed/60:.1f} minutes)"
    )
    if total_stats["valid_records"] > 0:
        print(
            f"Average speed:       {total_stats['valid_records']/total_elapsed:,.0f} records/sec"
        )
    print("=" * 80)

    # Show date range of imported data
    cursor.execute(
        """
        SELECT 
            DATE(MIN(timestamp)) as first_date,
            DATE(MAX(timestamp)) as last_date,
            COUNT(DISTINCT DATE(timestamp)) as days_with_data
        FROM mbo_data
        WHERE session_id = %s
    """,
        (session_id,),
    )

    date_stats = cursor.fetchone()
    if date_stats[0]:
        print(f"\nImported data range:")
        print(f"  First date: {date_stats[0]}")
        print(f"  Last date:  {date_stats[1]}")
        print(f"  Days:       {date_stats[2]}")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nImport interrupted by user")
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback

        traceback.print_exc()
