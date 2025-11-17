"""Quick check for data flow issues."""

import psycopg2
from datetime import datetime, timedelta

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

print("=" * 80)
print("DATA FLOW CHECK")
print("=" * 80)

# Check last 10 minutes
cur.execute(
    "SELECT COUNT(*) FROM mbo_data WHERE timestamp > NOW() - INTERVAL '10 minutes'"
)
recent = cur.fetchone()[0]
print(f"\nMBO rows (last 10 min): {recent:,}")

# Check last hour
cur.execute("SELECT COUNT(*) FROM mbo_data WHERE timestamp > NOW() - INTERVAL '1 hour'")
hour = cur.fetchone()[0]
print(f"MBO rows (last 1 hour): {hour:,}")

# Get last timestamp
cur.execute("SELECT MAX(timestamp) FROM mbo_data")
last = cur.fetchone()[0]
print(f"\nLast MBO timestamp: {last}")
if last:
    time_ago = datetime.now(last.tzinfo) - last
    print(f"Time since last: {time_ago}")

# Check absorption
cur.execute(
    "SELECT COUNT(*) FROM absorption_events WHERE timestamp > NOW() - INTERVAL '10 minutes'"
)
abs_recent = cur.fetchone()[0]
print(f"\nAbsorption rows (last 10 min): {abs_recent:,}")

# Check stops/icebergs
cur.execute(
    "SELECT COUNT(*) FROM stops_icebergs WHERE timestamp > NOW() - INTERVAL '10 minutes'"
)
stops_recent = cur.fetchone()[0]
print(f"Stops/Icebergs rows (last 10 min): {stops_recent:,}")

print("\n" + "=" * 80)
if recent == 0 and hour == 0:
    print("❌ NO NEW DATA - Data flow stopped!")
    print("\nPossible issues:")
    print("1. Bookmap not connected to data feed")
    print("2. No active instrument on chart")
    print("3. Consumer addons not enabled")
    print("4. Session ended or instrument not trading")
else:
    print("✅ Data is flowing normally")

conn.close()
