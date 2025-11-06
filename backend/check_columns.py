import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='trading_data',
    user='postgres',
    password='X74Ot*BvtjgKuCBx'
)

cur = conn.cursor()
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_name = 'stops_icebergs' 
    ORDER BY ordinal_position
""")

print("stops_icebergs columns:")
for row in cur.fetchall():
    print(f"  - {row[0]}")

# Also get a sample row to see the structure
cur.execute("SELECT * FROM stops_icebergs WHERE event_type = 'ICEBERG' LIMIT 1")
sample = cur.fetchone()
if sample:
    print("\nSample ICEBERG row:")
    cur.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'stops_icebergs' 
        ORDER BY ordinal_position
    """)
    columns = [row[0] for row in cur.fetchall()]
    for col, val in zip(columns, sample):
        print(f"  {col}: {val}")

cur.close()
conn.close()
