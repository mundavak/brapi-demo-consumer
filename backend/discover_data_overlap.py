import os
from datetime import datetime

# Define paths from the user request
OHLC_DATA_PATH = "C:\\Users\\Kudzai\\Downloads\\TradingView_Data"
MBO_DATA_PATH = "H:\\mbo_csv"
OUTPUT_DIR = "f:\\TradingAgent\\deaProjects\\brapi-demo-consumer\\backend"


def get_dates_from_filenames(path, prefix, date_format, is_mbo=False):
    """
    Extracts dates from filenames in a given directory.

    Args:
        path (str): The directory path to scan.
        prefix (str): The filename prefix to look for.
        date_format (str): The format of the date in the filename.
        is_mbo (bool): Flag to handle the specific MBO filename format.

    Returns:
        set: A set of dates found in the filenames.
    """
    dates = set()
    if not os.path.exists(path):
        print(f"Warning: Directory not found at {path}")
        return dates

    for filename in os.listdir(path):
        if filename.startswith(prefix) and filename.endswith(".csv"):
            try:
                date_found = False
                if is_mbo:
                    # Handles 'glbx-mdp3-YYYYMMDD.mbo.csv'
                    date_str = filename.replace(prefix, "").split(".")[0]
                    try:
                        dt = datetime.strptime(date_str, date_format)
                        dates.add(dt.date())
                        date_found = True
                    except ValueError:
                        pass  # Continue if format doesn't match
                else:
                    # Handles 'MNQ_..._YYYY-MM-DDTHH-MM-SS.csv'
                    parts = (
                        filename.replace(prefix, "")
                        .replace(".csv", "")
                        .strip("_")
                        .split("_")
                    )
                    for part in parts:
                        try:
                            date_str = part.split("T")[0]
                            dt = datetime.strptime(date_str, date_format)
                            dates.add(dt.date())
                            date_found = True
                            break
                        except ValueError:
                            continue

                if not date_found:
                    print(
                        f"Could not parse date from filename: {filename} with format {date_format}"
                    )

            except Exception as e:
                print(f"Error processing filename: {filename}. Error: {e}")
    return dates


def find_overlapping_dates():
    """
    Finds the overlapping dates for which both OHLC and MBO data exist and saves them.
    """
    print("Starting data overlap discovery...")
    print(f"OHLC Path: {OHLC_DATA_PATH}")
    print(f"MBO Path: {MBO_DATA_PATH}")

    # Ensure output directory exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

    # Extract dates from OHLC filenames (e.g., MNQ_..._2025-11-14T....csv)
    ohlc_dates = get_dates_from_filenames(OHLC_DATA_PATH, "MNQ", "%Y-%m-%d")
    if not ohlc_dates:
        print(
            "No OHLC dates found. Please check the path and file naming convention (expected: MNQ_*YYYY-MM-DD*.csv)."
        )
    else:
        print(f"Found {len(ohlc_dates)} unique dates in OHLC data.")

    # Extract dates from MBO filenames (e.g., glbx-mdp3-20250828.mbo.csv)
    mbo_dates = get_dates_from_filenames(
        MBO_DATA_PATH, "glbx-mdp3-", "%Y%m%d", is_mbo=True
    )
    if not mbo_dates:
        print(
            "No MBO dates found. Please check the path and file naming convention (expected: glbx-mdp3-YYYYMMDD.mbo.csv)."
        )
    else:
        print(f"Found {len(mbo_dates)} unique dates in MBO data.")

    # Find the intersection of the two sets of dates
    overlapping_dates = ohlc_dates.intersection(mbo_dates)

    if overlapping_dates:
        sorted_dates = sorted(list(overlapping_dates))
        print(f"\nFound {len(overlapping_dates)} overlapping dates for analysis.")
        if sorted_dates:
            print(f"Overlapping date range: {sorted_dates[0]} to {sorted_dates[-1]}")

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
        print("\nNo overlapping dates found between OHLC and MBO data sources.")
        print(
            "Please verify the data paths and that the files follow the expected naming convention."
        )

    return overlapping_dates


if __name__ == "__main__":
    find_overlapping_dates()
