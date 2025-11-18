import psycopg2
from datetime import datetime, timedelta
import pytz

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)
cursor = conn.cursor()

eastern = pytz.timezone("America/New_York")
now = datetime.now(eastern)

# Yesterday (Saturday) 9:30 AM to 4:00 PM
yesterday_start = (now - timedelta(days=1)).replace(
    hour=9, minute=30, second=0, microsecond=0
)
yesterday_end = (now - timedelta(days=1)).replace(
    hour=16, minute=0, second=0, microsecond=0
)

print(f"Searching for data between:")
print(f"  Start: {yesterday_start}")
print(f"  End:   {yesterday_end}")

cursor.execute(
    """
    SELECT COUNT(*), MIN(low), MAX(high), MIN(timestamp), MAX(timestamp)
    FROM ohlc_candles
    WHERE symbol = 'MNQ'
    AND timeframe = '5m'
    AND timestamp BETWEEN %s AND %s
""",
    (yesterday_start, yesterday_end),
)

result = cursor.fetchone()
print(f"\nResults:")
print(f"  Candles found: {result[0]}")
print(f"  Low: ${result[1]:,.2f}" if result[1] else "  Low: None")
print(f"  High: ${result[2]:,.2f}" if result[2] else "  High: None")
if result[3]:
    print(f"  First candle: {result[3].astimezone(eastern)}")
    print(f"  Last candle: {result[4].astimezone(eastern)}")

# Try last Friday instead (2 days ago)
friday_start = (now - timedelta(days=3)).replace(
    hour=9, minute=30, second=0, microsecond=0
)
friday_end = (now - timedelta(days=3)).replace(
    hour=16, minute=0, second=0, microsecond=0
)

print(f"\nLast Friday (3 days ago):")
print(f"  Start: {friday_start}")
print(f"  End:   {friday_end}")

cursor.execute(
    """
    SELECT COUNT(*), MIN(low), MAX(high)
    FROM ohlc_candles
    WHERE symbol = 'MNQ'
    AND timeframe = '5m'
    AND timestamp BETWEEN %s AND %s
""",
    (friday_start, friday_end),
)

result = cursor.fetchone()
print(f"\nResults:")
print(f"  Candles found: {result[0]}")
print(f"  Low: ${result[1]:,.2f}" if result[1] else "  Low: None")
print(f"  High: ${result[2]:,.2f}" if result[2] else "  High: None")

cursor.close()
conn.close()
