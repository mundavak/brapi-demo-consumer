"""
Check Redis data structure for Stops & Icebergs Consumer
"""

import redis
import json

# Connect to Redis
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

print("=" * 80)
print("REDIS STOPS & ICEBERGS DATA STRUCTURE INSPECTION")
print("=" * 80)
print()

# 1. Find all stops/icebergs keys
print("1. Finding all stops/icebergs keys in Redis...")
print("-" * 80)

# Pattern: stops:{symbol}:{session_id}
stops_keys = r.keys("stops:*")
iceberg_keys = r.keys("iceberg:*")

print(f"Total 'stops:*' keys: {len(stops_keys)}")
print(f"Total 'iceberg:*' keys: {len(iceberg_keys)}")

if stops_keys:
    print(f"\nFirst 5 stops keys:")
    for key in stops_keys[:5]:
        print(f"  - {key}")

if iceberg_keys:
    print(f"\nFirst 5 iceberg keys:")
    for key in iceberg_keys[:5]:
        print(f"  - {key}")

# 2. Get a sample stops record
print("\n" + "=" * 80)
print("2. SAMPLE STOPS RECORD:")
print("-" * 80)

if stops_keys:
    sample_key = stops_keys[0]
    print(f"Key: {sample_key}")
    print(f"Type: {r.type(sample_key)}")

    if r.type(sample_key) == "zset":
        # Get the first record from the sorted set
        records = r.zrange(sample_key, 0, 0, withscores=True)
        if records:
            value, score = records[0]
            print(f"\nScore (timestamp): {score}")
            print(f"\nValue (JSON):")

            # Parse and pretty-print the JSON
            try:
                data = json.loads(value)
                print(json.dumps(data, indent=2))

                print("\n" + "-" * 80)
                print("FIELD BREAKDOWN:")
                print("-" * 80)
                for key, val in data.items():
                    print(f"  {key:25s} = {val}")

            except json.JSONDecodeError:
                print(value)

    # Get total count in this sorted set
    count = r.zcard(sample_key)
    print(f"\nTotal records in this key: {count}")

# 3. Get a sample iceberg record
print("\n" + "=" * 80)
print("3. SAMPLE ICEBERG RECORD:")
print("-" * 80)

if iceberg_keys:
    sample_key = iceberg_keys[0]
    print(f"Key: {sample_key}")
    print(f"Type: {r.type(sample_key)}")

    if r.type(sample_key) == "zset":
        records = r.zrange(sample_key, 0, 0, withscores=True)
        if records:
            value, score = records[0]
            print(f"\nScore (timestamp): {score}")
            print(f"\nValue (JSON):")

            try:
                data = json.loads(value)
                print(json.dumps(data, indent=2))

                print("\n" + "-" * 80)
                print("FIELD BREAKDOWN:")
                print("-" * 80)
                for key, val in data.items():
                    print(f"  {key:25s} = {val}")

            except json.JSONDecodeError:
                print(value)

    count = r.zcard(sample_key)
    print(f"\nTotal records in this key: {count}")

# 4. Check for different iceberg sub-type keys
print("\n" + "=" * 80)
print("4. ICEBERG SUB-TYPE KEYS:")
print("-" * 80)

subtypes = ["TRADE", "EXECUTION", "DETECTION", "MOVEMENT", "CANCELLATION"]
for subtype in subtypes:
    keys = r.keys(f"iceberg:{subtype}:*")
    print(f"  iceberg:{subtype}:* → {len(keys)} keys")
    if keys:
        sample = keys[0]
        count = r.zcard(sample)
        print(f"    Example: {sample} ({count} records)")

# 5. Get latest stops/icebergs from any active session
print("\n" + "=" * 80)
print("5. LATEST STOPS/ICEBERGS (from most recent key):")
print("-" * 80)

if stops_keys:
    # Sort by key name to get most recent session
    latest_key = sorted(stops_keys)[-1]
    print(f"Key: {latest_key}")

    # Get last 5 records
    records = r.zrevrange(latest_key, 0, 4, withscores=True)
    print(f"\nLast 5 events:")
    for i, (value, score) in enumerate(records, 1):
        data = json.loads(value)
        print(f"\n  [{i}] Timestamp: {score}")
        print(f"      Event: {data.get('eventType')} {data.get('side')}")
        print(f"      Price: ${data.get('price')}")
        print(f"      Size: {data.get('size')} / {data.get('totalSize')}")
        if "icebergSubtype" in data:
            print(f"      Sub-type: {data.get('icebergSubtype')}")

print("\n" + "=" * 80)
print("SUMMARY:")
print("=" * 80)
print("✅ Redis stores stops/icebergs in sorted sets")
print("✅ Key pattern: stops:{symbol}:{session_id}")
print("✅ Score = Unix timestamp (for time-based queries)")
print("✅ Value = JSON with full event data")
print("=" * 80)
