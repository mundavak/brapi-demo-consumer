"""
Find ALL Redis keys to understand the exact key patterns
"""

import redis
import json
from datetime import datetime

# Connect to Redis
r = redis.Redis(host="localhost", port=6379, decode_responses=True)

print("=" * 80)
print("ALL REDIS KEYS INSPECTION")
print("=" * 80)
print()

# Get ALL keys
all_keys = r.keys("*")
print(f"Total keys in Redis: {len(all_keys)}")
print()

# Group by pattern
patterns = {}
for key in all_keys:
    # Extract pattern (e.g., "iceberg" from "iceberg:MNQZ5.CME@RITHMIC:session")
    prefix = key.split(":")[0] if ":" in key else key
    if prefix not in patterns:
        patterns[prefix] = []
    patterns[prefix].append(key)

print("=" * 80)
print("KEYS GROUPED BY PREFIX:")
print("-" * 80)
for prefix, keys in sorted(patterns.items()):
    print(f"\n{prefix}:* → {len(keys)} keys")
    for key in sorted(keys)[:5]:  # Show first 5
        key_type = r.type(key)
        if key_type == "zset":
            count = r.zcard(key)
            print(f"  - {key} (sorted set, {count} records)")
        elif key_type == "string":
            print(f"  - {key} (string)")
        elif key_type == "hash":
            count = r.hlen(key)
            print(f"  - {key} (hash, {count} fields)")
        elif key_type == "list":
            count = r.llen(key)
            print(f"  - {key} (list, {count} items)")
        elif key_type == "set":
            count = r.scard(key)
            print(f"  - {key} (set, {count} members)")

    if len(keys) > 5:
        print(f"  ... and {len(keys) - 5} more")

# Now let's get detailed data from each type
print("\n" + "=" * 80)
print("DETAILED DATA INSPECTION:")
print("=" * 80)

for prefix in sorted(patterns.keys()):
    print(f"\n{'=' * 80}")
    print(f"PREFIX: {prefix}")
    print("=" * 80)

    sample_key = patterns[prefix][0]
    key_type = r.type(sample_key)

    print(f"Sample key: {sample_key}")
    print(f"Type: {key_type}")
    print()

    if key_type == "zset":
        # Get first and last record
        first = r.zrange(sample_key, 0, 0, withscores=True)
        last = r.zrevrange(sample_key, 0, 0, withscores=True)
        count = r.zcard(sample_key)

        print(f"Total records: {count}")
        print()

        if first:
            value, score = first[0]
            # Convert score to timestamp
            ts = (
                datetime.fromtimestamp(score / 1e9)
                if score > 1e12
                else datetime.fromtimestamp(score)
            )
            print(f"FIRST RECORD (timestamp: {ts}):")
            try:
                data = json.loads(value)
                print(json.dumps(data, indent=2))
            except:
                print(value)

        print()

        if last:
            value, score = last[0]
            ts = (
                datetime.fromtimestamp(score / 1e9)
                if score > 1e12
                else datetime.fromtimestamp(score)
            )
            print(f"LAST RECORD (timestamp: {ts}):")
            try:
                data = json.loads(value)
                print(json.dumps(data, indent=2))
            except:
                print(value)

    elif key_type == "string":
        value = r.get(sample_key)
        try:
            data = json.loads(value)
            print(json.dumps(data, indent=2))
        except:
            print(value[:500])  # First 500 chars

    elif key_type == "hash":
        # Get all fields
        data = r.hgetall(sample_key)
        print(json.dumps(data, indent=2))

    elif key_type == "list":
        # Get first 3 items
        items = r.lrange(sample_key, 0, 2)
        for i, item in enumerate(items):
            print(f"[{i}] {item}")

print("\n" + "=" * 80)
print("SUMMARY:")
print("=" * 80)
print(f"Total unique prefixes: {len(patterns)}")
for prefix, keys in sorted(patterns.items()):
    print(f"  {prefix:20s} → {len(keys):5d} keys")
print("=" * 80)
