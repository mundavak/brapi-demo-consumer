import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)
cur = conn.cursor()

print("stops_icebergs columns:")
cur.execute(
    """
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'stops_icebergs' 
    ORDER BY ordinal_position
"""
)
for col in cur.fetchall():
    print(f"  {col[0]:30} {col[1]}")

conn.close()
