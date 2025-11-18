import psycopg2
from datetime import datetime, timedelta
import pytz

EST = pytz.timezone("America/New_York")
now = datetime.now(EST)
yesterday = now - timedelta(days=1)
start = yesterday.replace(hour=20, minute=45, second=0, microsecond=0)

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)
cursor = conn.cursor()

print("Overnight Low/High Investigation")
print("=" * 80)
print(f"Current Query Time Range: {start} to {now}")
print()

# Find the actual low candle
cursor.execute(
    """
    SELECT timestamp, open, high, low, close, timeframe
    FROM ohlc_candles
    WHERE symbol = 'MNQ'
    AND timeframe = '5m'
    AND timestamp BETWEEN %s AND %s
    AND low = (
        SELECT MIN(low)
        FROM ohlc_candles
        WHERE symbol = 'MNQ'
        AND timeframe = '5m'
        AND timestamp BETWEEN %s AND %s
    )
""",
    (start, now, start, now),
)

print("Candle with LOWEST price in query range:")
for ts, o, h, l, c, tf in cursor.fetchall():
    print(f"  Time: {ts}")
    print(f"  Open: ${o:,.2f}, High: ${h:,.2f}, Low: ${l:,.2f}, Close: ${c:,.2f}")
    print()

# Find the actual high candle
cursor.execute(
    """
    SELECT timestamp, open, high, low, close, timeframe
    FROM ohlc_candles
    WHERE symbol = 'MNQ'
    AND timeframe = '5m'
    AND timestamp BETWEEN %s AND %s
    AND high = (
        SELECT MAX(high)
        FROM ohlc_candles
        WHERE symbol = 'MNQ'
        AND timeframe = '5m'
        AND timestamp BETWEEN %s AND %s
    )
""",
    (start, now, start, now),
)

print("Candle with HIGHEST price in query range:")
for ts, o, h, l, c, tf in cursor.fetchall():
    print(f"  Time: {ts}")
    print(f"  Open: ${o:,.2f}, High: ${h:,.2f}, Low: ${l:,.2f}, Close: ${c:,.2f}")
    print()

# Show time distribution of candles
cursor.execute(
    """
    SELECT 
        EXTRACT(HOUR FROM timestamp) as hour,
        COUNT(*) as candle_count,
        MIN(low) as low,
        MAX(high) as high
    FROM ohlc_candles
    WHERE symbol = 'MNQ'
    AND timeframe = '5m'
    AND timestamp BETWEEN %s AND %s
    GROUP BY EXTRACT(HOUR FROM timestamp)
    ORDER BY hour
""",
    (start, now),
)

print("Candles by Hour:")
print(f'{"Hour":<6} {"Count":<8} {"Low":<12} {"High":<12}')
print("-" * 50)
for hour, count, low, high in cursor.fetchall():
    print(f"{int(hour):<6} {count:<8} ${low:<11,.2f} ${high:<11,.2f}")

# Check what proper overnight range should be (BEFORE 9:30 AM)
print()
print("=" * 80)
print("PROBLEM IDENTIFIED:")
print("  Current query includes 09:30-10:22 (regular session hours)")
print("  The low at $24,955.25 is from 09:30 AM candle!")
print()
print("Correct Time Ranges Should Be:")
print("  Overnight Session: 20:45 (previous day) to 09:30 (current day) - EXCLUSIVE")
print("  Regular Session: 09:30 to 16:00")
print()

# Now check what overnight should REALLY be (before 9:30)
overnight_end = now.replace(hour=9, minute=30, second=0, microsecond=0)
print(f"Correct Overnight Range: {start} to {overnight_end}")

cursor.execute(
    """
    SELECT 
        MIN(low) as overnight_low,
        MAX(high) as overnight_high,
        (array_agg(open ORDER BY timestamp))[1] as session_open,
        (array_agg(close ORDER BY timestamp DESC))[1] as last_close,
        COUNT(*) as candle_count
    FROM ohlc_candles
    WHERE symbol = 'MNQ'
    AND timeframe = '5m'
    AND timestamp >= %s
    AND timestamp < %s
""",
    (start, overnight_end),
)

result = cursor.fetchone()
if result and result[0]:
    print()
    print("CORRECT Overnight Structure (20:45 to 09:30):")
    print(f"  Candles: {result[4]}")
    print(f"  Low: ${result[0]:,.2f}")
    print(f"  High: ${result[1]:,.2f}")
    print(f"  Open: ${result[2]:,.2f}")
    print(f"  Last Close (before 9:30): ${result[3]:,.2f}")

cursor.close()
conn.close()
