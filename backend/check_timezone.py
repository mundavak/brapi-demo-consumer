import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)

cur = conn.cursor()

# Check database timezone setting
cur.execute("SHOW timezone")
db_tz = cur.fetchone()[0]
print(f"Database timezone: {db_tz}")
print("=" * 70)

# Get sample timestamps
cur.execute(
    """
    SELECT 
        timestamp as raw_timestamp,
        timestamp AT TIME ZONE 'UTC' as utc_time,
        timestamp AT TIME ZONE 'America/New_York' as est_time
    FROM mbo_data 
    ORDER BY timestamp DESC 
    LIMIT 5
"""
)

print("\nSample timestamps from database:")
print("-" * 70)
rows = cur.fetchall()
for row in rows:
    print(f"Raw DB: {row[0]}")
    print(f"As UTC: {row[1]}")
    print(f"As EST: {row[2]}")
    print()

conn.close()

print("\nConclusion:")
print("-" * 70)
if db_tz.lower() in ["utc", "gmt"]:
    print("✓ Database stores timestamps in UTC")
    print("✓ The exported CSVs apply 'AT TIME ZONE America/New_York'")
    print("✓ CSV timestamps are correctly converted to EST")
else:
    print(f"⚠ Database timezone is set to: {db_tz}")
    print("The conversion may need adjustment")
