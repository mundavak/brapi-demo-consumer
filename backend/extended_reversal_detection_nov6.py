"""
Extended Reversal Detection - Nov 6, 2025
Analyzes order flow 10:00-10:30 AM when the bearish move is well established
"""

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

est = pytz.timezone("America/New_York")

# Analysis window: 10:00-10:30 AM (bearish move underway)
analysis_date = datetime(2025, 11, 6, 10, 0, 0, tzinfo=est)
end_time = datetime(2025, 11, 6, 10, 30, 0, tzinfo=est)

print("=" * 80)
print("BEARISH MOVE CONFIRMATION - Nov 6, 2025")
print("=" * 80)
print("Analysis Window: 10:00-10:30 AM EST (30 minutes)")
print("Context: Judas swing complete, bearish move underway")
print()

start_ts = analysis_date.timestamp()
end_ts = end_time.timestamp()
symbol = "MNQZ5.CME@RITHMIC"

SUBTYPE_WEIGHTS = {
    "TRADE": 1.0,
    "EXECUTION": 0.8,
    "DETECTION": 0.5,
    "MOVEMENT": 0.3,
    "CANCELLATION": 0.2,
    None: 0.5,
}

print("=" * 80)
print("ORDER FLOW ANALYSIS:")
print("-" * 80)

# STOPS
cur = conn.cursor()
cur.execute(
    """
    SELECT event_type, side, COUNT(*) as count, AVG(price) as avg_price
    FROM stops_icebergs
    WHERE symbol = %s AND timestamp >= to_timestamp(%s) AND timestamp < to_timestamp(%s)
      AND event_type IN ('STOP', 'STOP_CLUSTER')
    GROUP BY event_type, side ORDER BY side, event_type
""",
    (symbol, start_ts, end_ts),
)

stops_data = cur.fetchall()
buy_stops = sum(count for _, side, count, _ in stops_data if side == "BUY")
sell_stops = sum(count for _, side, count, _ in stops_data if side == "SELL")

if buy_stops > 0 and sell_stops > 0:
    stops_ratio = buy_stops / sell_stops
    if stops_ratio < 0.67:
        stops_signal, stops_score = "BEARISH", -25
    elif stops_ratio > 1.5:
        stops_signal, stops_score = "BULLISH", 25
    else:
        stops_signal, stops_score = "NEUTRAL", 0
else:
    stops_signal, stops_score = "NO DATA", 0
    stops_ratio = 0

print(f"STOPS: {stops_signal} ({stops_score:+d} pts)")
print(
    f"  BUY: {buy_stops} | SELL: {sell_stops}"
    + (f" | Ratio: {stops_ratio:.2f}x" if stops_ratio > 0 else "")
)

# ICEBERGS
print()
cur.execute(
    """
    SELECT side, iceberg_subtype, COUNT(*) as count, AVG(price) as avg_price
    FROM stops_icebergs
    WHERE symbol = %s AND timestamp >= to_timestamp(%s) AND timestamp < to_timestamp(%s)
      AND event_type = 'ICEBERG'
    GROUP BY side, iceberg_subtype ORDER BY side, iceberg_subtype
""",
    (symbol, start_ts, end_ts),
)

icebergs_data = cur.fetchall()
buy_weighted = sum(
    count * SUBTYPE_WEIGHTS.get(subtype, 0.5)
    for side, subtype, count, _ in icebergs_data
    if side == "BUY"
)
sell_weighted = sum(
    count * SUBTYPE_WEIGHTS.get(subtype, 0.5)
    for side, subtype, count, _ in icebergs_data
    if side == "SELL"
)
total_icebergs = sum(count for _, _, count, _ in icebergs_data)

if sell_weighted > buy_weighted * 2:
    iceberg_signal, iceberg_score = "BEARISH", -20
elif buy_weighted > sell_weighted * 2:
    iceberg_signal, iceberg_score = "BULLISH", 20
else:
    iceberg_signal, iceberg_score = "NEUTRAL", 0

print(f"ICEBERGS: {iceberg_signal} ({iceberg_score:+d} pts)")
print(f"  Total: {total_icebergs} events")
print(f"  BUY weighted: {buy_weighted:.1f}")
print(f"  SELL weighted: {sell_weighted:.1f}")

# MBO
print()
cur.execute(
    """
    SELECT side, COUNT(*) as order_count, SUM(size) as total_volume
    FROM mbo_data
    WHERE symbol = %s AND timestamp >= to_timestamp(%s) AND timestamp < to_timestamp(%s)
      AND action IN ('ADD', 'EXECUTE')
    GROUP BY side
""",
    (symbol, start_ts, end_ts),
)

mbo_data = cur.fetchall()
buy_orders = sum(count for side, count, _ in mbo_data if side == "BUY")
sell_orders = sum(count for side, count, _ in mbo_data if side == "SELL")
buy_volume = sum(vol for side, _, vol in mbo_data if side == "BUY")
sell_volume = sum(vol for side, _, vol in mbo_data if side == "SELL")

if buy_orders > 0 and sell_orders > 0:
    order_ratio = buy_orders / sell_orders
    volume_ratio = buy_volume / sell_volume
    if order_ratio < 0.83 and volume_ratio < 0.83:
        mbo_signal, mbo_score = "BEARISH", -15
    elif order_ratio > 1.2 and volume_ratio > 1.2:
        mbo_signal, mbo_score = "BULLISH", 15
    else:
        mbo_signal, mbo_score = "NEUTRAL", 0
else:
    mbo_signal, mbo_score = "NO DATA", 0
    order_ratio = volume_ratio = 0

print(f"MBO FLOW: {mbo_signal} ({mbo_score:+d} pts)")
if order_ratio > 0:
    print(f"  Orders: {order_ratio:.2f}x | Volume: {volume_ratio:.2f}x")

# FINAL
total_score = stops_score + iceberg_score + mbo_score
confidence = abs(total_score) / 75 * 100 if total_score != 0 else 0

print("\n" + "=" * 80)
print(f"TOTAL SCORE: {total_score:+d} / ±75")
print(f"CONFIDENCE: {confidence:.1f}%")
print("=" * 80)

if confidence < 30:
    signal = "WAIT"
elif total_score < 0:
    signal = "SHORT"
else:
    signal = "LONG"

print(f"SIGNAL: {signal}")
print()
print("Actual: Bearish move from $25,840 → $25,328 (-512 pts)")
print(
    f"Result: {'✅ CORRECT' if signal == 'SHORT' else '❌ MISSED' if signal == 'WAIT' else '❌ WRONG'}"
)
print("=" * 80)

cur.close()
conn.close()
