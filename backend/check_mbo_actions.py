import psycopg2

conn = psycopg2.connect(
    host="localhost",
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)

cur = conn.cursor()

print("=== MBO Actions on Nov 17 ===")
cur.execute(
    """
    SELECT DISTINCT action, COUNT(*) as cnt
    FROM mbo_data 
    WHERE timestamp >= '2025-11-17' AND timestamp < '2025-11-18'
    GROUP BY action
    ORDER BY cnt DESC
"""
)
for row in cur.fetchall():
    print(f"{row[0]}: {row[1]:,}")

print(f"\n=== Total events ===")
cur.execute(
    "SELECT COUNT(*) FROM mbo_data WHERE timestamp >= '2025-11-17' AND timestamp < '2025-11-18'"
)
print(f"Total: {cur.fetchone()[0]:,}")

print("\n=== Sample MBO records ===")
cur.execute(
    """
    SELECT timestamp, action, side, price, size, order_id
    FROM mbo_data 
    WHERE timestamp >= '2025-11-17' AND timestamp < '2025-11-18'
    ORDER BY timestamp
    LIMIT 10
"""
)
for row in cur.fetchall():
    print(
        f"{row[0]} {row[1]:<5} {row[2]:<5} ${row[3]:<10.2f} size:{row[4]} id:{row[5]}"
    )

cur.close()
conn.close()
