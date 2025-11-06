import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)

cur = conn.cursor()

print("=== MBO Actions in PRE_NY window (Nov 5) ===")
cur.execute(
    """
    SELECT DISTINCT action, COUNT(*) as cnt
    FROM mbo_data 
    WHERE symbol LIKE 'MNQ%' 
    AND cbdr_window = 'PRE_NY'
    AND DATE(timestamp AT TIME ZONE 'America/New_York') = '2025-11-05'
    GROUP BY action
    ORDER BY cnt DESC
"""
)
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]:,}")

print("\n=== Sample MBO records ===")
cur.execute(
    """
    SELECT action, side, price, size
    FROM mbo_data 
    WHERE symbol LIKE 'MNQ%' 
    AND cbdr_window = 'PRE_NY'
    AND DATE(timestamp AT TIME ZONE 'America/New_York') = '2025-11-05'
    LIMIT 10
"""
)
for row in cur.fetchall():
    print(f"{row[0]:<15} {row[1]:<10} Price: {row[2]:<10} Size: {row[3]}")

cur.close()
conn.close()
