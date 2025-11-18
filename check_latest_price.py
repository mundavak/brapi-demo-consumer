import psycopg2
from datetime import datetime
import pytz

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)
cursor = conn.cursor()

# Get current time in EST
eastern = pytz.timezone("America/New_York")
now = datetime.now(eastern)
print(f'Current Time: {now.strftime("%Y-%m-%d %H:%M:%S %Z")}')
print("=" * 80)

# Get latest 5m candles
cursor.execute(
    """
    SELECT timestamp, open, high, low, close, volume
    FROM ohlc_candles
    WHERE symbol = 'MNQ'
    AND timeframe = '5m'
    ORDER BY timestamp DESC
    LIMIT 10
"""
)

print(f"\nLatest 10 5m Candles:")
print(
    f'{"Timestamp":<25} {"Open":<12} {"High":<12} {"Low":<12} {"Close":<12} {"Volume":<12}'
)
print("-" * 100)
for row in cursor.fetchall():
    ts, o, h, l, c, v = row
    # Convert to EST
    ts_est = ts.astimezone(eastern)
    print(
        f'{ts_est.strftime("%Y-%m-%d %H:%M:%S %Z"):<25} ${o:<11,.2f} ${h:<11,.2f} ${l:<11,.2f} ${c:<11,.2f} {v:<12,}'
    )

cursor.close()
conn.close()
