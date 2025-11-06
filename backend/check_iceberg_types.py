import psycopg2
import redis
import json

# Check TimescaleDB
print("=" * 80)
print("CHECKING ICEBERG TYPES IN TIMESCALEDB")
print("=" * 80)

conn = psycopg2.connect(
    host="localhost",
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)

cur = conn.cursor()

# Check if we have iceberg_type column
cur.execute(
    """
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'stops_icebergs' 
    ORDER BY ordinal_position
"""
)
print("\nstops_icebergs columns:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check metadata field for iceberg type info
print("\n\nChecking metadata field for iceberg type information...")
cur.execute(
    """
    SELECT 
        metadata,
        COUNT(*) as cnt
    FROM stops_icebergs
    WHERE event_type = 'ICEBERG'
    AND metadata IS NOT NULL
    GROUP BY metadata
    LIMIT 5
"""
)
print("\nSample metadata values:")
for row in cur.fetchall():
    print(f"  {row[0]} (count: {row[1]})")

# Check if there's any variation in event_type for icebergs
cur.execute(
    """
    SELECT DISTINCT event_type
    FROM stops_icebergs
    ORDER BY event_type
"""
)
print("\n\nDistinct event_type values:")
for row in cur.fetchall():
    print(f"  {row[0]}")

# Check sample iceberg records
print("\n\nSample ICEBERG records (showing all fields):")
cur.execute(
    """
    SELECT *
    FROM stops_icebergs
    WHERE event_type = 'ICEBERG'
    LIMIT 3
"""
)
cols = [desc[0] for desc in cur.description]
for i, row in enumerate(cur.fetchall(), 1):
    print(f"\nRecord {i}:")
    for col, val in zip(cols, row):
        print(f"  {col}: {val}")

cur.close()
conn.close()

# Check Redis
print("\n\n" + "=" * 80)
print("CHECKING ICEBERG TYPES IN REDIS")
print("=" * 80)

r = redis.Redis(host="localhost", port=6379, decode_responses=True)

# Get iceberg keys
iceberg_keys = r.keys("iceberg:*")
print(f"\nFound {len(iceberg_keys)} iceberg keys")

if iceberg_keys:
    print("\nSample iceberg key structure:")
    for key in iceberg_keys[:3]:
        print(f"\nKey: {key}")
        key_type = r.type(key)
        print(f"Type: {key_type}")

        if key_type == "zset":
            # Get a few members
            members = r.zrange(key, 0, 2, withscores=True)
            print(f"Sample members (first 3):")
            for member, score in members:
                print(f"  Score: {score}")
                print(f"  Value: {member[:200]}...")  # Truncate long values
                # Try to parse as JSON
                try:
                    data = json.loads(member)
                    if "iceberg_type" in data or "type" in data:
                        print(
                            f"    Contains type field: {data.get('iceberg_type') or data.get('type')}"
                        )
                except:
                    pass

r.close()

print("\n" + "=" * 80)
print("ANALYSIS COMPLETE")
print("=" * 80)
