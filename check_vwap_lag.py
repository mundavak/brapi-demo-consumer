import psycopg2
import pytz

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)
cursor = conn.cursor()

cursor.execute("SELECT MAX(timestamp) FROM vwap_levels WHERE symbol = 'MNQ'")
vwap_ts = cursor.fetchone()[0]

cursor.execute(
    "SELECT MAX(timestamp) FROM ohlc_candles WHERE symbol = 'MNQ' AND timeframe = '5m'"
)
candle_ts = cursor.fetchone()[0]

eastern = pytz.timezone("America/New_York")
print(f"Latest VWAP timestamp:   {vwap_ts.astimezone(eastern)}")
print(f"Latest 5m candle timestamp: {candle_ts.astimezone(eastern)}")
print(f"\nVWAP is behind by: {(candle_ts - vwap_ts).total_seconds() / 60:.0f} minutes")

cursor.close()
conn.close()
