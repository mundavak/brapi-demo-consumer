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

print("OHLC Candle Data Analysis")
print("=" * 80)

# Check total candles
cursor.execute(
    "SELECT symbol, timeframe, COUNT(*) FROM ohlc_candles GROUP BY symbol, timeframe ORDER BY symbol, timeframe"
)
print("\nCandle Inventory:")
for symbol, tf, count in cursor.fetchall():
    print(f"  {symbol} {tf}: {count:,} candles")

# Check date range
cursor.execute(
    "SELECT MIN(timestamp), MAX(timestamp), COUNT(*) FROM ohlc_candles WHERE symbol = 'MNQ'"
)
result = cursor.fetchone()
print(f"\nMNQ Date Range:")
print(f"  First: {result[0]}")
print(f"  Last:  {result[1]}")
print(f"  Total: {result[2]:,}")

# Check overnight session data
print(f"\nOvernight Session Analysis (for bias report):")
print(f"  Time Range: {start} to {now}")

cursor.execute(
    """
    SELECT 
        timeframe,
        COUNT(*) as candle_count,
        MIN(low) as session_low,
        MAX(high) as session_high,
        (array_agg(open ORDER BY timestamp))[1] as session_open,
        (array_agg(close ORDER BY timestamp DESC))[1] as current_close,
        MIN(timestamp) as first_candle,
        MAX(timestamp) as last_candle
    FROM ohlc_candles
    WHERE symbol = 'MNQ'
    AND timestamp BETWEEN %s AND %s
    GROUP BY timeframe
    ORDER BY timeframe
""",
    (start, now),
)

results = cursor.fetchall()
if results:
    for tf, count, low, high, open_price, close, first, last in results:
        print(f"\n  {tf} Timeframe:")
        print(f"    Candles: {count}")
        print(f"    Low: ${low:,.2f}")
        print(f"    High: ${high:,.2f}")
        print(f"    Open: ${open_price:,.2f}")
        print(f"    Close: ${close:,.2f}")
        print(f"    Range: ${high-low:,.2f} ({(high-low)/open_price*100:.2f}%)")
        print(f"    Position in Range: {(close-low)/(high-low)*100:.1f}%")
        print(f"    First: {first}")
        print(f"    Last: {last}")
else:
    print("  No candles found in overnight session!")

# Check most recent 10 candles for 5m timeframe
print("\n" + "=" * 80)
print("Most Recent 5m Candles:")
cursor.execute(
    """
    SELECT timestamp, open, high, low, close, volume
    FROM ohlc_candles
    WHERE symbol = 'MNQ' AND timeframe = '5m'
    ORDER BY timestamp DESC
    LIMIT 10
"""
)
for ts, o, h, l, c, v in cursor.fetchall():
    print(f"  {ts}: O:${o:,.2f} H:${h:,.2f} L:${l:,.2f} C:${c:,.2f} V:{v:,}")

# Compare with what bias report is using
print("\n" + "=" * 80)
print("Bias Report Query Simulation (5m candles only):")
cursor.execute(
    """
    SELECT 
        MIN(low) as overnight_low, 
        MAX(high) as overnight_high,
        (array_agg(open ORDER BY timestamp))[1] as session_open,
        (array_agg(close ORDER BY timestamp DESC))[1] as current_price,
        AVG(close) as avg_price,
        STDDEV(close) as volatility,
        COUNT(*) as candle_count
    FROM ohlc_candles
    WHERE symbol = 'MNQ' 
    AND timeframe = '5m'
    AND timestamp BETWEEN %s AND %s
""",
    (start, now),
)

result = cursor.fetchone()
if result and result[0]:
    low, high, open_p, close, avg, vol, count = result
    range_size = high - low
    range_pos = (close - low) / range_size * 100
    print(f"  Candles Used: {count}")
    print(f"  Overnight Low: ${low:,.2f}")
    print(f"  Overnight High: ${high:,.2f}")
    print(f"  Session Open: ${open_p:,.2f}")
    print(f"  Current Price: ${close:,.2f}")
    print(f"  Range: ${range_size:,.2f}")
    print(f"  Range Position: {range_pos:.1f}%")
    print(f"  Avg Price: ${avg:,.2f}")
    print(f"  Volatility: ${vol:,.2f}")
else:
    print("  No data returned!")

cursor.close()
conn.close()
