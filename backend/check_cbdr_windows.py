import psycopg2
from datetime import datetime

conn = psycopg2.connect(
    host='localhost',
    database='trading_data',
    user='postgres',
    password='X74Ot*BvtjgKuCBx'
)

cur = conn.cursor()

# Check CBDR windows
print("=== CBDR Windows in stops_icebergs ===")
cur.execute("""
    SELECT DISTINCT cbdr_window, COUNT(*) as count
    FROM stops_icebergs 
    WHERE symbol LIKE 'MNQ%'
    GROUP BY cbdr_window
    ORDER BY count DESC
""")
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]:,} events")

# Check absorption cbdr_window
print("\n=== CBDR Windows in absorption_events ===")
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'absorption_events'
    ORDER BY ordinal_position
""")
print("Columns:", [r[0] for r in cur.fetchall()])

# Check for Nov 5 pre-market data (before 9:30 AM EST)
print("\n=== Nov 5, 2025 Pre-Market Data (before 9:30 AM EST) ===")
cur.execute("""
    SELECT 
        cbdr_window,
        COUNT(*) as events,
        MIN(timestamp AT TIME ZONE 'America/New_York') as first_event,
        MAX(timestamp AT TIME ZONE 'America/New_York') as last_event
    FROM stops_icebergs
    WHERE symbol LIKE 'MNQ%'
    AND DATE(timestamp AT TIME ZONE 'America/New_York') = '2025-11-05'
    AND EXTRACT(HOUR FROM (timestamp AT TIME ZONE 'America/New_York')) < 9
    GROUP BY cbdr_window
    ORDER BY events DESC
""")
print("Pre-market (before 9:30 AM):")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]:,} events ({row[2]} to {row[3]})")

# Check MBO data availability
print("\n=== MBO Data Structure ===")
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns 
    WHERE table_name = 'mbo_data'
    ORDER BY ordinal_position
""")
print("MBO Columns:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check Nov 5 MBO data
cur.execute("""
    SELECT 
        COUNT(*) as total_orders,
        COUNT(DISTINCT order_id) as unique_orders,
        MIN(timestamp AT TIME ZONE 'America/New_York') as first_order,
        MAX(timestamp AT TIME ZONE 'America/New_York') as last_order
    FROM mbo_data
    WHERE symbol LIKE 'MNQ%'
    AND DATE(timestamp AT TIME ZONE 'America/New_York') = '2025-11-05'
    AND EXTRACT(HOUR FROM (timestamp AT TIME ZONE 'America/New_York')) < 9
""")
row = cur.fetchone()
print(f"\nNov 5 Pre-Market MBO: {row[0]:,} order events, {row[1]:,} unique orders")
print(f"Time range: {row[2]} to {row[3]}")

cur.close()
conn.close()
