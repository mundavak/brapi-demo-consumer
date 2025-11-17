import psycopg2
from datetime import datetime, timedelta

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)

cursor = conn.cursor()

# Check most recent records
cursor.execute(
    """
    SELECT timestamp, symbol, action, order_id, side
    FROM mbo_data 
    ORDER BY timestamp DESC 
    LIMIT 20
"""
)

print(f"Current time: {datetime.now()}")
print("\nMost recent 20 MBO records:")
for ts, sym, act, oid, side in cursor.fetchall():
    print(f"{ts} | {sym} | {act:8s} | {oid} | {side}")

# Check last 30 seconds
cursor.execute(
    """
    SELECT COUNT(*), MIN(timestamp), MAX(timestamp) 
    FROM mbo_data 
    WHERE timestamp >= %s
""",
    (datetime.now() - timedelta(seconds=30),),
)

count, first, last = cursor.fetchone()
print(f"\nLast 30 seconds: {count:,} MBO events")
if first:
    print(f"First event: {first}")
    print(f"Last event:  {last}")

# Breakdown by action
cursor.execute(
    """
    SELECT action, COUNT(*) 
    FROM mbo_data 
    WHERE timestamp >= %s 
    GROUP BY action
""",
    (datetime.now() - timedelta(seconds=30),),
)

print("\nBreakdown by action:")
for action, cnt in cursor.fetchall():
    print(f"  {action}: {cnt:,}")

# Check last minute
cursor.execute(
    """
    SELECT COUNT(*) 
    FROM mbo_data 
    WHERE timestamp >= %s
""",
    (datetime.now() - timedelta(minutes=1),),
)

count_1m = cursor.fetchone()[0]
print(f"\nLast 1 minute: {count_1m:,} MBO events")

# Check current session
cursor.execute(
    """
    SELECT session_id, COUNT(*), MIN(timestamp), MAX(timestamp)
    FROM mbo_data
    WHERE session_id LIKE 'MNQZ5.CME@RITHMIC_20251114_12%'
    GROUP BY session_id
    ORDER BY session_id DESC
    LIMIT 3
"""
)

print("\nCurrent session(s):")
for session_id, cnt, first, last in cursor.fetchall():
    print(f"  {session_id}: {cnt:,} events ({first} to {last})")

cursor.close()
conn.close()
