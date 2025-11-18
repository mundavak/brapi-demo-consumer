"""
Fast timezone conversion for MBO CSV files using chunked processing
Converts UTC timestamps to EST/EDT with DST handling
Uses pandas for vectorized operations - 10-100x faster than row-by-row
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

# Configuration
INPUT_DIR = Path(r"H:\missing_mbo_csv")
OUTPUT_DIR = Path(r"H:\missing_mbo_csv_est")
DST_TRANSITION = pd.Timestamp("2025-11-02 06:00:00", tz="UTC")  # Nov 2, 2025 at 6am UTC
CHUNK_SIZE = 500_000  # Process 500k rows at a time (balance memory vs speed)

# Timestamp fields to convert
TIMESTAMP_FIELDS = ["ts_event", "ts_recv", "ts_in_delta"]


def convert_chunk_timestamps(chunk, timestamp_cols):
    """
    Convert UTC timestamps to EST/EDT for a DataFrame chunk
    Uses vectorized operations for maximum speed
    """
    for col in timestamp_cols:
        if col not in chunk.columns:
            continue

        # Parse as UTC timestamps
        chunk[col] = pd.to_datetime(chunk[col], utc=True, errors="coerce")

        # Apply timezone conversion
        # pandas automatically handles DST when converting to US/Eastern
        chunk[col] = chunk[col].dt.tz_convert("US/Eastern")

        # Format as ISO 8601 string without timezone suffix (just the local time)
        chunk[col] = chunk[col].dt.strftime("%Y-%m-%dT%H:%M:%S.%f").str[:-3]

    return chunk


def process_csv_file(input_path, output_path):
    """
    Process a single CSV file with chunked reading and writing

    Args:
        input_path: Path to input CSV file (UTC timestamps)
        output_path: Path to output CSV file (EST/EDT timestamps)

    Returns:
        Total rows processed
    """
    print(f"\nProcessing: {input_path.name}")
    print(f"  Output: {output_path.name}")

    total_rows = 0
    first_chunk = True

    try:
        # Read and process in chunks
        for chunk_num, chunk in enumerate(
            pd.read_csv(input_path, chunksize=CHUNK_SIZE), 1
        ):
            # Identify which timestamp fields exist in this file
            ts_cols = [col for col in TIMESTAMP_FIELDS if col in chunk.columns]

            if chunk_num == 1:
                print(f"  Timestamp fields: {', '.join(ts_cols)}")

            # Convert timestamps in this chunk
            chunk = convert_chunk_timestamps(chunk, ts_cols)

            # Write chunk to output file
            chunk.to_csv(
                output_path,
                mode="w" if first_chunk else "a",
                header=first_chunk,
                index=False,
            )

            first_chunk = False
            total_rows += len(chunk)

            # Progress update every 5 chunks
            if chunk_num % 5 == 0:
                print(f"  {total_rows:,} rows processed...")

        print(f"  Completed: {total_rows:,} rows")
        return total_rows

    except Exception as e:
        print(f"  ERROR: {e}")
        return total_rows


def main():
    """
    Main processing function
    Processes all CSV files in input directory
    """
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Get list of CSV files
    csv_files = sorted(INPUT_DIR.glob("*.csv"))

    if not csv_files:
        print(f"No CSV files found in {INPUT_DIR}")
        return

    print("=" * 80)
    print("Fast Timezone Conversion - MBO Data")
    print("=" * 80)
    print(f"Input directory:  {INPUT_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Files to process: {len(csv_files)}")
    print(f"Chunk size:       {CHUNK_SIZE:,} rows")
    print(f"\nDST transition:   {DST_TRANSITION.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("  Before: UTC-4 (EDT)")
    print("  After:  UTC-5 (EST)")
    print("=" * 80)

    # Process each file
    total_files = len(csv_files)
    grand_total_rows = 0
    start_time = datetime.now()

    for file_num, input_file in enumerate(csv_files, 1):
        output_file = OUTPUT_DIR / input_file.name

        print(f"\n[{file_num}/{total_files}] Processing {input_file.name}")
        print(f"  Size: {input_file.stat().st_size / (1024**3):.2f} GB")

        file_start = datetime.now()
        rows_processed = process_csv_file(input_file, output_file)
        file_elapsed = (datetime.now() - file_start).total_seconds()

        grand_total_rows += rows_processed

        if rows_processed > 0:
            rows_per_sec = rows_processed / file_elapsed
            print(f"  Speed: {rows_per_sec:,.0f} rows/sec")
            print(f"  Time: {file_elapsed:.1f} seconds")

    # Summary
    total_elapsed = (datetime.now() - start_time).total_seconds()
    print("\n" + "=" * 80)
    print("CONVERSION COMPLETE")
    print("=" * 80)
    print(f"Files processed:  {total_files}")
    print(f"Total rows:       {grand_total_rows:,}")
    print(
        f"Total time:       {total_elapsed:.1f} seconds ({total_elapsed/60:.1f} minutes)"
    )
    if grand_total_rows > 0:
        print(f"Average speed:    {grand_total_rows/total_elapsed:,.0f} rows/sec")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nConversion interrupted by user")
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}")
        import traceback

        traceback.print_exc()
