#!/usr/bin/env python3
"""
Check MBO data availability and identify missing dates
"""
import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}

conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

print("=" * 80)
print("MBO DATA GAP ANALYSIS")
print("=" * 80)

# Get OHLC reference range
cursor.execute(
    """
    SELECT 
        DATE(MIN(timestamp)) as first_date,
        DATE(MAX(timestamp)) as last_date,
        COUNT(DISTINCT DATE(timestamp)) as trading_days
    FROM ohlc_candles
    WHERE symbol = 'MNQ' AND timeframe = '5m'
"""
)
ohlc = cursor.fetchone()
print(f"\nOHLC Data (Reference):")
print(f"  First Date: {ohlc[0]}")
print(f"  Last Date: {ohlc[1]}")
print(f"  Total Trading Days: {ohlc[2]}")

# Check stops_icebergs (MBO-derived)
cursor.execute(
    """
    SELECT 
        DATE(MIN(timestamp)) as first_date,
        DATE(MAX(timestamp)) as last_date,
        COUNT(DISTINCT DATE(timestamp)) as days_with_data,
        COUNT(*) as total_events
    FROM stops_icebergs
"""
)
mbo = cursor.fetchone()
print(f"\nStops & Icebergs (MBO-derived):")
print(f"  First Date: {mbo[0]}")
print(f"  Last Date: {mbo[1]}")
print(f"  Days with Data: {mbo[2]} / {ohlc[2]} trading days")
print(f"  Total Events: {mbo[3]:,}")
print(f"  Coverage: {mbo[2] / ohlc[2] * 100:.1f}%")

# Check raw mbo_data table
cursor.execute(
    """
    SELECT 
        DATE(MIN(timestamp)) as first_date,
        DATE(MAX(timestamp)) as last_date,
        COUNT(DISTINCT DATE(timestamp)) as days_with_data,
        COUNT(*) as total_events
    FROM mbo_data
"""
)
raw_mbo = cursor.fetchone()
print(f"\nRaw MBO Data (mbo_data table):")
print(f"  First Date: {raw_mbo[0]}")
print(f"  Last Date: {raw_mbo[1]}")
print(f"  Days with Data: {raw_mbo[2]}")
print(f"  Total Events: {raw_mbo[3]:,}")

# Check absorption events
cursor.execute(
    """
    SELECT 
        DATE(MIN(timestamp)) as first_date,
        DATE(MAX(timestamp)) as last_date,
        COUNT(DISTINCT DATE(timestamp)) as days_with_data,
        COUNT(*) as total_events
    FROM absorption_events
"""
)
absorption = cursor.fetchone()
print(f"\nAbsorption Events (MBO-derived):")
print(f"  First Date: {absorption[0]}")
print(f"  Last Date: {absorption[1]}")
print(f"  Days with Data: {absorption[2]} / {ohlc[2]} trading days")
print(f"  Total Events: {absorption[3]:,}")
print(f"  Coverage: {absorption[2] / ohlc[2] * 100:.1f}%")

# Find gaps - days with OHLC but no MBO
cursor.execute(
    """
    WITH ohlc_days AS (
        SELECT DISTINCT DATE(timestamp) as date
        FROM ohlc_candles
        WHERE symbol = 'MNQ' AND timeframe = '5m'
    ),
    mbo_days AS (
        SELECT DISTINCT DATE(timestamp) as date
        FROM stops_icebergs
    )
    SELECT o.date
    FROM ohlc_days o
    LEFT JOIN mbo_days m ON o.date = m.date
    WHERE m.date IS NULL
    ORDER BY o.date
"""
)
missing_stops = cursor.fetchall()

# Find gaps in raw MBO data
cursor.execute(
    """
    WITH ohlc_days AS (
        SELECT DISTINCT DATE(timestamp) as date
        FROM ohlc_candles
        WHERE symbol = 'MNQ' AND timeframe = '5m'
    ),
    mbo_days AS (
        SELECT DISTINCT DATE(timestamp) as date
        FROM mbo_data
    )
    SELECT o.date
    FROM ohlc_days o
    LEFT JOIN mbo_days m ON o.date = m.date
    WHERE m.date IS NULL
    ORDER BY o.date
"""
)
missing_raw = cursor.fetchall()

# Find gaps in absorption data
cursor.execute(
    """
    WITH ohlc_days AS (
        SELECT DISTINCT DATE(timestamp) as date
        FROM ohlc_candles
        WHERE symbol = 'MNQ' AND timeframe = '5m'
    ),
    absorption_days AS (
        SELECT DISTINCT DATE(timestamp) as date
        FROM absorption_events
    )
    SELECT o.date
    FROM ohlc_days o
    LEFT JOIN absorption_days a ON o.date = a.date
    WHERE a.date IS NULL
    ORDER BY o.date
"""
)
missing_absorption = cursor.fetchall()

print(f"\n" + "=" * 80)
print("MISSING DATA SUMMARY")
print("=" * 80)

print(f"\n❌ Missing Stops & Icebergs Data ({len(missing_stops)} days):")
if missing_stops:
    for (date,) in missing_stops:
        print(f"  {date}")
else:
    print("  ✓ No gaps")

print(f"\n❌ Missing Raw MBO Data ({len(missing_raw)} days):")
if missing_raw:
    for (date,) in missing_raw:
        print(f"  {date}")
else:
    print("  ✓ No gaps")

print(f"\n❌ Missing Absorption Data ({len(missing_absorption)} days):")
if missing_absorption:
    for (date,) in missing_absorption:
        print(f"  {date}")
else:
    print("  ✓ No gaps")

# Daily breakdown for recent data
cursor.execute(
    """
    SELECT 
        DATE(timestamp) as date,
        COUNT(*) as events,
        MIN(timestamp)::time as first_event,
        MAX(timestamp)::time as last_event
    FROM stops_icebergs
    GROUP BY DATE(timestamp)
    ORDER BY date DESC
    LIMIT 20
"""
)
daily = cursor.fetchall()

print(f"\n" + "=" * 80)
print("RECENT DAILY MBO ACTIVITY (Last 20 Days with Data)")
print("=" * 80)
print(f"  Date         Events      First Event    Last Event")
print(f"  {'-' * 60}")
for date, events, first, last in daily:
    print(f"  {date}  {events:>8,}    {first}      {last}")

cursor.close()
conn.close()

print(f"\n" + "=" * 80)
