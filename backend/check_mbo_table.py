#!/usr/bin/env python3
"""
Check if we have raw MBO data in mbo_data table to work with
"""
import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)
cursor = conn.cursor()

print("Checking mbo_data table structure and content...")

# Check table structure
cursor.execute(
    """
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'mbo_data' 
    ORDER BY ordinal_position
"""
)
print("\nmbo_data columns:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check date range
cursor.execute(
    """
    SELECT 
        DATE(MIN(timestamp)) as first_date,
        DATE(MAX(timestamp)) as last_date,
        COUNT(*) as total_rows,
        COUNT(DISTINCT DATE(timestamp)) as days_with_data
    FROM mbo_data
"""
)
stats = cursor.fetchone()
print(f"\nmbo_data stats:")
print(f"  First Date: {stats[0]}")
print(f"  Last Date: {stats[1]}")
print(f"  Total Rows: {stats[2]:,}")
print(f"  Days with Data: {stats[3]}")

# Sample some rows
cursor.execute(
    """
    SELECT * FROM mbo_data 
    ORDER BY timestamp DESC 
    LIMIT 5
"""
)
print(f"\nSample rows (latest 5):")
for row in cursor.fetchall():
    print(f"  {row}")

cursor.close()
conn.close()
