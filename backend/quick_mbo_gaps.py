#!/usr/bin/env python3
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)
cursor = conn.cursor()

# Get missing dates
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
missing = cursor.fetchall()

print(f"Missing MBO Dates ({len(missing)} days):")
for (date,) in missing:
    print(f"  {date}")

# Check if raw MBO data exists for these dates
print("\nChecking raw mbo_data table...")
cursor.execute(
    """
    SELECT 
        DATE(MIN(timestamp)), 
        DATE(MAX(timestamp)),
        COUNT(DISTINCT DATE(timestamp))
    FROM mbo_data
"""
)
raw = cursor.fetchone()
print(f"Raw MBO Range: {raw[0]} to {raw[1]} ({raw[2]} days)")

cursor.close()
conn.close()
