import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)

cur = conn.cursor()

print("=== Absorption Events - Nov 5 PRE_NY Window (7:30-9:00 AM) ===")
cur.execute(
    """
    SELECT 
        cbdr_window,
        is_in_cbdr,
        COUNT(*) as cnt,
        MIN(timestamp AT TIME ZONE 'America/New_York') as first_ts,
        MAX(timestamp AT TIME ZONE 'America/New_York') as last_ts
    FROM absorption_events 
    WHERE symbol LIKE 'MNQ%'
    AND DATE(timestamp AT TIME ZONE 'America/New_York') = '2025-11-05'
    AND EXTRACT(HOUR FROM (timestamp AT TIME ZONE 'America/New_York')) BETWEEN 7 AND 8
    GROUP BY cbdr_window, is_in_cbdr
"""
)
for row in cur.fetchall():
    print(
        f"{row[0] if row[0] else 'NULL':<15} | in_cbdr={row[1]:<5} | {row[2]:,} events | {row[3]} to {row[4]}"
    )

print("\n=== All absorption cbdr_window values ===")
cur.execute(
    """
    SELECT DISTINCT cbdr_window, COUNT(*) 
    FROM absorption_events 
    WHERE symbol LIKE 'MNQ%'
    GROUP BY cbdr_window
    ORDER BY COUNT(*) DESC
"""
)
for row in cur.fetchall():
    print(f"{row[0] if row[0] else 'NULL'}: {row[1]:,}")

cur.close()
conn.close()
