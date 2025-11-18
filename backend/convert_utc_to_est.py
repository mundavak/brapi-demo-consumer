#!/usr/bin/env python3
"""
Convert UTC timestamps in Databento MBO CSV files to EST/EDT
- Before Nov 2, 2025: UTC-4 (EDT - Daylight Saving Time)
- Nov 2, 2025 and after: UTC-5 (EST - Standard Time)
"""
import csv
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Directories
INPUT_DIR = r"H:\missing_mbo_csv"
OUTPUT_DIR = r"H:\missing_mbo_csv_est"

# DST transition: Nov 2, 2025 at 2:00 AM EST (6:00 AM UTC)
DST_END = datetime(2025, 11, 2, 6, 0, 0, tzinfo=timezone.utc)


def convert_timestamp_to_est(ts_utc_str, dst_transition=DST_END):
    """
    Convert UTC timestamp to EST/EDT

    Args:
        ts_utc_str: UTC timestamp string (ISO 8601 or nanoseconds)
        dst_transition: DST end datetime (UTC)

    Returns:
        EST/EDT timestamp string
    """
    if not ts_utc_str or ts_utc_str == "":
        return ts_utc_str

    try:
        # Try parsing as ISO 8601
        if "T" in ts_utc_str or "-" in ts_utc_str:
            # ISO 8601 format - remove timezone if present
            ts_str_clean = ts_utc_str.replace("Z", "").split("+")[0].split("-", 3)
            if len(ts_str_clean) > 3:
                ts_str_clean = "-".join(ts_str_clean[:3])
            else:
                ts_str_clean = ts_utc_str.replace("Z", "+00:00")

            ts_utc = datetime.fromisoformat(ts_str_clean)
            if ts_utc.tzinfo is None:
                ts_utc = ts_utc.replace(tzinfo=timezone.utc)
        else:
            # Nanoseconds since epoch
            ts_ns = int(ts_utc_str)
            ts_utc = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc)

        # Determine offset based on date
        if ts_utc < dst_transition:
            # EDT: UTC-4
            offset_hours = -4
        else:
            # EST: UTC-5
            offset_hours = -5

        ts_local = ts_utc + timedelta(hours=offset_hours)

        # Return in ISO 8601 format
        return ts_local.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]

    except (ValueError, TypeError, AttributeError):
        # If conversion fails, return original
        return ts_utc_str


def process_csv_file(input_path, output_path, dst_transition=DST_END):
    """
    Process a single CSV file, converting UTC timestamps to EST/EDT
    """
    print(f"Processing: {os.path.basename(input_path)}")

    rows_processed = 0
    timestamp_fields = set()

    with open(input_path, "r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)

        # Identify timestamp fields (ts_event, ts_recv, etc.)
        fieldnames = reader.fieldnames
        for field in fieldnames:
            if field.startswith("ts_"):
                timestamp_fields.add(field)

        print(f"  Timestamp fields: {', '.join(timestamp_fields)}")

        with open(output_path, "w", newline="", encoding="utf-8") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                # Convert all timestamp fields
                for ts_field in timestamp_fields:
                    if ts_field in row and row[ts_field]:
                        row[ts_field] = convert_timestamp_to_est(
                            row[ts_field], dst_transition
                        )

                writer.writerow(row)
                rows_processed += 1

                if rows_processed % 1000000 == 0:
                    print(f"    {rows_processed:,} rows processed...")

    print(f"  ✓ Completed: {rows_processed:,} rows")
    return rows_processed


def main():
    """Process all CSV files in input directory"""

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output directory: {OUTPUT_DIR}\n")

    # Get all CSV files
    input_dir = Path(INPUT_DIR)
    csv_files = sorted(input_dir.glob("*.csv"))

    if not csv_files:
        print(f"No CSV files found in {INPUT_DIR}")
        return

    print("=" * 80)
    print("TIMEZONE CONVERSION: UTC → EST/EDT")
    print("=" * 80)
    print(f"Files to process: {len(csv_files)}")
    print(f"DST transition: {DST_END.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Before: UTC-4 (EDT)")
    print(f"  After:  UTC-5 (EST)")
    print()

    total_rows = 0
    processed_files = 0

    for csv_file in csv_files:
        output_file = Path(OUTPUT_DIR) / csv_file.name

        try:
            rows = process_csv_file(str(csv_file), str(output_file))
            total_rows += rows
            processed_files += 1
        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            continue

        print()

    print("=" * 80)
    print("CONVERSION COMPLETE")
    print("=" * 80)
    print(f"Files processed: {processed_files}/{len(csv_files)}")
    print(f"Total rows: {total_rows:,}")
    print(f"Output location: {OUTPUT_DIR}")
    print()
    print("✓ All timestamps converted to EST/EDT")


if __name__ == "__main__":
    main()
