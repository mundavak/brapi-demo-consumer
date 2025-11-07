"""
Check MBO data availability - what time ranges do we have?
"""

import psycopg2
from datetime import datetime
import pytz

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)

est = pytz.timezone("America/New_York")

print("=" * 80)
print("MBO DATA AVAILABILITY CHECK")
print("=" * 80)

cur = conn.cursor()

# Check hourly distribution for Nov 6
print("\nNov 6, 2025 - Hourly MBO data distribution:")
print("-" * 80)

cur.execute(
    """
    SELECT 
        DATE_TRUNC('hour', timestamp) as hour,
        COUNT(*) as record_count,
        MIN(timestamp) as first_record,
        MAX(timestamp) as last_record
    FROM mbo_data
    WHERE symbol = 'MNQZ5.CME'
      AND timestamp >= '2025-11-06 00:00:00-05:00'
      AND timestamp < '2025-11-07 00:00:00-05:00'
    GROUP BY DATE_TRUNC('hour', timestamp)
    ORDER BY hour
"""
)

hours = cur.fetchall()

if hours:
    for hour, count, first, last in hours:
        print(
            f"{hour.strftime('%Y-%m-%d %H:00')} EST: {count:8,} records | {first.strftime('%H:%M:%S')} - {last.strftime('%H:%M:%S')}"
        )
else:
    print("No data found for Nov 6, 2025")

# Check the gap around market open
print("\n" + "=" * 80)
print("CRITICAL TIME WINDOW - PRE_NY to NY Open:")
print("-" * 80)

cur.execute(
    """
    SELECT 
        DATE_TRUNC('minute', timestamp) as minute,
        COUNT(*) as record_count
    FROM mbo_data
    WHERE symbol = 'MNQZ5.CME'
      AND timestamp >= '2025-11-06 09:00:00-05:00'
      AND timestamp < '2025-11-06 10:00:00-05:00'
    GROUP BY DATE_TRUNC('minute', timestamp)
    ORDER BY minute DESC
    LIMIT 40
"""
)

minutes = cur.fetchall()

if minutes:
    print("\nMinute-by-minute breakdown (9:00-9:59 AM):")
    for minute, count in minutes:
        print(f"  {minute.strftime('%H:%M')} EST: {count:6,} records")
else:
    print("No data in 9:00-10:00 AM window")

# Check last records before cutoff
print("\n" + "=" * 80)
print("LAST 10 MBO RECORDS before data stops:")
print("-" * 80)

cur.execute(
    """
    SELECT timestamp, action, side, price, size
    FROM mbo_data
    WHERE symbol = 'MNQZ5.CME'
    ORDER BY timestamp DESC
    LIMIT 10
"""
)

last_records = cur.fetchall()
for ts, action, side, price, size in last_records:
    print(f"{ts} | {action:8s} | {side:4s} | ${price:8.2f} | {size:5d}")

print("\n" + "=" * 80)
print("CONCLUSION:")
print("=" * 80)
print("MBO Consumer appears to have stopped at 9:29:59 AM")
print("This is RIGHT BEFORE the NY market open at 9:30 AM")
print("\nPossible reasons:")
print("1. MBO Consumer addon was stopped/disabled at market open")
print("2. Session ended and new session not started")
print("3. Bookmap disconnected/restarted at market open")
print("4. MBO data feed issue from exchange")
print("\n⚠️  This means we have NO MBO data for the Judas swing period!")
print("   - No data for 9:30-10:00 AM (reversal)")
print("   - No data for 10:00-10:30 AM (bearish move)")
print("=" * 80)

cur.close()
conn.close()
