"""
Monitor MBO import progress in real-time
"""

import psycopg2
import time
from datetime import datetime

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)

print("Monitoring MBO Import Progress...")
print("=" * 60)
print("Press Ctrl+C to stop monitoring\n")

last_count = None
last_time = None

try:
    while True:
        cursor = conn.cursor()

        # Get current count
        cursor.execute("SELECT COUNT(*) FROM mbo_data")
        current_count = cursor.fetchone()[0]

        # Get date range
        cursor.execute(
            """
            SELECT 
                DATE(MIN(timestamp)) as first_date,
                DATE(MAX(timestamp)) as last_date,
                COUNT(DISTINCT DATE(timestamp)) as days
            FROM mbo_data
        """
        )
        date_info = cursor.fetchone()

        # Calculate rate if we have previous data
        current_time = time.time()
        rate_info = ""
        if last_count is not None and last_time is not None:
            elapsed = current_time - last_time
            added = current_count - last_count
            if elapsed > 0:
                rate = added / elapsed
                rate_info = f" (+{added:,} in {elapsed:.1f}s = {rate:,.0f}/sec)"

        # Display
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] Total: {current_count:,}{rate_info}")
        print(
            f"          Range: {date_info[0]} to {date_info[1]} ({date_info[2]} days)"
        )
        print()

        last_count = current_count
        last_time = current_time

        cursor.close()
        time.sleep(10)  # Update every 10 seconds

except KeyboardInterrupt:
    print("\nMonitoring stopped")
finally:
    conn.close()
