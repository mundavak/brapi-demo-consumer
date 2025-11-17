import os
import pandas as pd
import pytz

# Define paths from the user request
OHLC_DATA_PATH = "C:\\Users\\Kudzai\\Downloads\\TradingView_Data"
MBO_DATA_PATH = "H:\\mbo_csv"
OUTPUT_DIR = "f:\\TradingAgent\\deaProjects\\brapi-demo-consumer\\backend"
EST = pytz.timezone("America/New_York")


def get_unique_dates_from_csv_content(
    directory, file_prefix, timestamp_col, is_unix=False, date_format=None
):
    """
    Reads CSV files in a directory to extract unique dates from a timestamp column.

    Args:
        directory (str): The path to the directory containing CSV files.
        file_prefix (str): The prefix of the files to process.
        timestamp_col (str): The name of the column containing the timestamp.
        is_unix (bool): True if the timestamp is in UNIX format.
        date_format (str): The string format for non-UNIX timestamps.

    Returns:
        set: A set of unique dates found across all processed files.
    """
    unique_dates = set()
    if not os.path.exists(directory):
        print(f"Warning: Directory not found at {directory}")
        return unique_dates

    print(f"Scanning directory: {directory}")
    for filename in os.listdir(directory):
        if filename.startswith(file_prefix) and filename.endswith(".csv"):
            file_path = os.path.join(directory, filename)
            print(f"  Processing file: {filename}...")
            try:
                # Read only the timestamp column to save memory
                df = pd.read_csv(file_path, usecols=[timestamp_col])

                if is_unix:
                    # Convert UNIX timestamp to datetime objects
                    # unit='ns' for nanoseconds
                    timestamps = pd.to_datetime(
                        df[timestamp_col], unit="ns", errors="coerce"
                    )
                else:
                    # Convert string timestamps to datetime objects
                    # Pandas can often infer the format automatically for ISO-like strings
                    timestamps = pd.to_datetime(df[timestamp_col], errors="coerce")

                # Drop any rows where conversion failed
                timestamps = timestamps.dropna()

                # Convert to EST dates.
                # If the timestamp is naive (like UNIX time), localize to UTC first.
                # If it's already aware (like the ISO strings with offsets), just convert.
                if timestamps.dt.tz is None:
                    dates_in_file = (
                        timestamps.dt.tz_localize("UTC").dt.tz_convert(EST).dt.date
                    )
                else:
                    dates_in_file = timestamps.dt.tz_convert(EST).dt.date

                unique_dates.update(dates_in_file.unique())
                print(
                    f"    Found {len(dates_in_file.unique())} unique dates in this file."
                )

            except ValueError:
                print(
                    f"    Could not find column '{timestamp_col}' in {filename}. Skipping."
                )
            except Exception as e:
                print(f"    An error occurred while processing {filename}: {e}")

    return unique_dates


def find_overlapping_dates_from_content():
    """
    Finds overlapping dates by reading the content of the CSV files.
    """
    print("\nStarting data overlap discovery by reading file contents...")

    # --- Process OHLC Data ---
    # TradingView exports often use a 'time' column for the timestamp.
    # User specified "ISO UTC-5", but TradingView often exports UNIX time. Let's try UNIX first.
    print("\n--- Processing OHLC Data (TradingView) ---")
    ohlc_dates = get_unique_dates_from_csv_content(
        directory=OHLC_DATA_PATH,
        file_prefix="MNQ",
        timestamp_col="time",  # Correct column name
        is_unix=False,  # It's an ISO string, not UNIX
    )
    if not ohlc_dates:
        print("No dates found in OHLC data files.")
    else:
        print(f"Found {len(ohlc_dates)} total unique dates in OHLC data.")

    # --- Process MBO Data ---
    print("\n--- Processing MBO Data ---")
    mbo_dates = get_unique_dates_from_csv_content(
        directory=MBO_DATA_PATH,
        file_prefix="glbx-mdp3-",
        timestamp_col="ts_event",  # Correct column name based on new info
        is_unix=True,  # It's a UNIX timestamp in nanoseconds
    )
    if not mbo_dates:
        print(
            "No dates found in MBO data files. Check if 'ts_event' is the correct column name."
        )
    else:
        print(f"Found {len(mbo_dates)} total unique dates in MBO data.")

    # --- Find and Report Overlap ---
    print("\n--- Analysis Complete ---")
    overlapping_dates = ohlc_dates.intersection(mbo_dates)

    if overlapping_dates:
        sorted_dates = sorted(list(overlapping_dates))
        print(
            f"\nSuccess! Found {len(overlapping_dates)} overlapping dates for analysis."
        )
        if sorted_dates:
            print(
                f"Overlapping date range (EST): {sorted_dates[0]} to {sorted_dates[-1]}"
            )

        # Save the list of overlapping dates to a file for the next step
        overlap_file_path = os.path.join(OUTPUT_DIR, "overlapping_dates.txt")
        try:
            with open(overlap_file_path, "w") as f:
                for date in sorted_dates:
                    f.write(f"{date.strftime('%Y-%m-%d')}\n")
            print(f"List of overlapping dates saved to: {overlap_file_path}")
        except IOError as e:
            print(f"Error saving overlapping dates file: {e}")

    else:
        print("\nNo overlapping dates found between the data sources.")
        print("Please check the following:")
        print(
            "1. The timestamp column names ('time' for OHLC, 'timestamp' for MBO) are correct."
        )
        print(
            "2. The timestamp formats are correct (both assumed to be UNIX timestamps)."
        )
        print("3. The data files for the two sources actually cover the same days.")

    return overlapping_dates


if __name__ == "__main__":
    # Ensure output directory exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    find_overlapping_dates_from_content()
