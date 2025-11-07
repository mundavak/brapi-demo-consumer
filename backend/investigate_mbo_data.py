"""
MBO Data Investigation - Check what's actually in the database
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

# Check 9:30-10:00 AM window
analysis_date = datetime(2025, 11, 6, 9, 30, 0, tzinfo=est)
end_time = datetime(2025, 11, 6, 10, 0, 0, tzinfo=est)

start_ts = analysis_date.timestamp()
end_ts = end_time.timestamp()
symbol = "MNQZ5.CME@RITHMIC"

print("=" * 80)
print("MBO DATA INVESTIGATION - Nov 6, 2025")
print("=" * 80)
print("Checking 9:30-10:00 AM window")
print()

cur = conn.cursor()

# 1. Check if there's ANY MBO data for this symbol and time
print("1. Checking for ANY MBO data in this window...")
cur.execute(
    """
    SELECT COUNT(*) 
    FROM mbo_data
    WHERE symbol = %s
      AND timestamp >= to_timestamp(%s)
      AND timestamp < to_timestamp(%s)
""",
    (symbol, start_ts, end_ts),
)

total_count = cur.fetchone()[0]
print(f"   Total MBO records: {total_count:,}")

if total_count == 0:
    print("\n   ❌ NO MBO DATA FOUND for this time window!")
    print("   Possible reasons:")
    print("   - MBO Consumer addon not running during this time")
    print("   - Data not captured for this symbol")
    print("   - Time window mismatch")

    # Check what symbols we DO have
    print("\n2. Checking what symbols ARE in mbo_data table...")
    cur.execute(
        """
        SELECT DISTINCT symbol, COUNT(*) as count
        FROM mbo_data
        GROUP BY symbol
        ORDER BY count DESC
        LIMIT 10
    """
    )
    symbols = cur.fetchall()
    if symbols:
        print("   Symbols with MBO data:")
        for sym, count in symbols:
            print(f"   - {sym}: {count:,} records")
    else:
        print("   ❌ NO MBO DATA AT ALL in table!")

    # Check date range
    print("\n3. Checking date range of MBO data...")
    cur.execute(
        """
        SELECT 
            MIN(timestamp) as earliest,
            MAX(timestamp) as latest,
            COUNT(*) as total
        FROM mbo_data
    """
    )
    result = cur.fetchone()
    if result and result[2] > 0:
        print(f"   Earliest: {result[0]}")
        print(f"   Latest: {result[1]}")
        print(f"   Total: {result[2]:,} records")

else:
    print(f"   ✅ Found {total_count:,} MBO records\n")

    # 2. Check what ACTION types exist
    print("2. Checking ACTION types in this window...")
    cur.execute(
        """
        SELECT action, COUNT(*) as count
        FROM mbo_data
        WHERE symbol = %s
          AND timestamp >= to_timestamp(%s)
          AND timestamp < to_timestamp(%s)
        GROUP BY action
        ORDER BY count DESC
    """,
        (symbol, start_ts, end_ts),
    )

    actions = cur.fetchall()
    print("   Action types found:")
    for action, count in actions:
        print(f"   - {action}: {count:,} records")

    # 3. Check SIDE distribution
    print("\n3. Checking SIDE distribution...")
    cur.execute(
        """
        SELECT side, COUNT(*) as count, SUM(size) as total_volume
        FROM mbo_data
        WHERE symbol = %s
          AND timestamp >= to_timestamp(%s)
          AND timestamp < to_timestamp(%s)
        GROUP BY side
        ORDER BY count DESC
    """,
        (symbol, start_ts, end_ts),
    )

    sides = cur.fetchall()
    print("   Side distribution:")
    for side, count, volume in sides:
        print(f"   - {side}: {count:,} orders, {volume:,} volume")

    # 4. Check by ACTION and SIDE together
    print("\n4. Full breakdown by ACTION and SIDE...")
    cur.execute(
        """
        SELECT action, side, COUNT(*) as count, SUM(size) as total_volume
        FROM mbo_data
        WHERE symbol = %s
          AND timestamp >= to_timestamp(%s)
          AND timestamp < to_timestamp(%s)
        GROUP BY action, side
        ORDER BY action, side
    """,
        (symbol, start_ts, end_ts),
    )

    breakdown = cur.fetchall()
    print("   Action x Side breakdown:")
    for action, side, count, volume in breakdown:
        print(f"   - {action} {side}: {count:,} orders, {volume:,} volume")

    # 5. Sample a few records
    print("\n5. Sample MBO records (first 5)...")
    cur.execute(
        """
        SELECT timestamp, action, side, price, size, order_id
        FROM mbo_data
        WHERE symbol = %s
          AND timestamp >= to_timestamp(%s)
          AND timestamp < to_timestamp(%s)
        ORDER BY timestamp
        LIMIT 5
    """,
        (symbol, start_ts, end_ts),
    )

    samples = cur.fetchall()
    print("   Sample records:")
    for ts, action, side, price, size, order_id in samples:
        print(
            f"   {ts} | {action:8s} | {side:4s} | ${price:,.2f} | {size:5d} | {order_id}"
        )

print("\n" + "=" * 80)

cur.close()
conn.close()
