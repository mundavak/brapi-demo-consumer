"""
Convert UTC timestamps in exported CSV files to EST timezone.

This script reads CSV files from the exports directory, converts all timestamp
columns from UTC to EST (UTC-5), and saves them with '_EST' suffix.
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
import pytz

# Configuration
EXPORTS_DIR = Path("./outputs/exports")
TIMESTAMP_COLUMNS = [
    "timestamp",
    "ts_event",
    "event_time",
]  # Common timestamp column names


def convert_csv_to_est(csv_path):
    """Convert UTC timestamps in a CSV file to EST timezone."""
    print("=" * 80)
    print(f"CONVERTING: {csv_path.name}")
    print("=" * 80)

    # Read CSV
    print("Reading CSV file...")
    df = pd.read_csv(csv_path)

    print(f"Total rows: {len(df):,}")
    print(f"Columns: {', '.join(df.columns)}")

    # Find timestamp columns
    timestamp_cols = [
        col for col in df.columns if col in TIMESTAMP_COLUMNS or "time" in col.lower()
    ]

    if not timestamp_cols:
        print("⚠️ No timestamp columns found. Skipping.")
        print("=" * 80)
        print()
        return

    print(f"\nFound timestamp columns: {', '.join(timestamp_cols)}")

    # Convert each timestamp column to EST
    est = pytz.timezone("US/Eastern")

    for col in timestamp_cols:
        print(f"\nProcessing column: {col}")

        # Parse timestamps with mixed format support
        df[col] = pd.to_datetime(df[col], format="mixed", utc=True)

        # Show sample before conversion
        print(f"  Sample UTC: {df[col].iloc[0]}")

        # Convert to EST
        df[col] = df[col].dt.tz_convert(est)

        # Show sample after conversion
        print(f"  Sample EST: {df[col].iloc[0]}")

        # Remove timezone info for cleaner CSV output (optional)
        # df[col] = df[col].dt.tz_localize(None)

    # Create output filename
    output_filename = csv_path.stem + "_EST.csv"
    output_path = csv_path.parent / output_filename

    # Save to new CSV
    print(f"\nSaving to: {output_filename}")
    df.to_csv(output_path, index=False)

    print(f"✅ Successfully converted and saved to {output_filename}")
    print("=" * 80)
    print()

    return output_path


def main():
    """Main conversion process."""
    print("\n")
    print("=" * 80)
    print("UTC TO EST TIMESTAMP CONVERTER")
    print("=" * 80)
    print(f"Exports Directory: {EXPORTS_DIR.resolve()}")
    print()

    # Find CSV files (exclude already converted _EST files)
    csv_files = [f for f in EXPORTS_DIR.glob("*.csv") if not f.stem.endswith("_EST")]

    if not csv_files:
        print("❌ No CSV files found to convert.")
        return

    print(f"Found {len(csv_files)} CSV files to convert:")
    for csv_file in csv_files:
        print(f"  - {csv_file.name}")
    print()

    converted_files = []

    try:
        for csv_file in csv_files:
            output_path = convert_csv_to_est(csv_file)
            if output_path:
                converted_files.append(output_path)

        print("\n" + "=" * 80)
        print(f"✅ Converted {len(converted_files)} files successfully!")
        print("=" * 80)
        print("\nConverted files:")
        for f in converted_files:
            print(f"  - {f.name}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
