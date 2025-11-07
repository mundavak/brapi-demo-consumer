"""
Judas Swing Reversal Detection - Nov 6, 2025
Analyzes order flow during the Judas swing reversal (9:30-10:00 AM)
to see if the model can detect the bearish move.
"""

import psycopg2
from datetime import datetime, timedelta
import pytz

# Database connection
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)

# Timezone
est = pytz.timezone("America/New_York")

# Analysis window: 9:30-10:00 AM (Judas swing + reversal)
analysis_date = datetime(2025, 11, 6, 9, 30, 0, tzinfo=est)
end_time = datetime(2025, 11, 6, 10, 0, 0, tzinfo=est)

print("=" * 80)
print("JUDAS SWING REVERSAL DETECTION - Nov 6, 2025")
print("=" * 80)
print(f"Analysis Window: 9:30-10:00 AM EST (30 minutes)")
print(f"Pattern: Judas spike to $25,840 → Reversal to $25,328 (-512 pts)")
print()

# Convert to Unix timestamps
start_ts = analysis_date.timestamp()
end_ts = end_time.timestamp()

# Symbol
symbol = "MNQZ5.CME@RITHMIC"

print("=" * 80)
print("ORDER FLOW ANALYSIS DURING REVERSAL:")
print("-" * 80)

# 1. STOPS ANALYSIS
cur = conn.cursor()
cur.execute(
    """
    SELECT 
        event_type,
        side,
        COUNT(*) as count,
        AVG(price) as avg_price,
        AVG(confidence_score) as avg_confidence
    FROM stops_icebergs
    WHERE symbol = %s
      AND timestamp >= to_timestamp(%s)
      AND timestamp < to_timestamp(%s)
      AND event_type IN ('STOP', 'STOP_CLUSTER')
    GROUP BY event_type, side
    ORDER BY side, event_type
""",
    (symbol, start_ts, end_ts),
)

stops_data = cur.fetchall()

buy_stops = 0
sell_stops = 0
for event_type, side, count, avg_price, avg_conf in stops_data:
    if side == "BUY":
        buy_stops += count
    else:
        sell_stops += count
    print(f"{side} {event_type}: {count} events (avg price: ${avg_price:,.2f})")

# Calculate stops signal
if buy_stops == 0 and sell_stops == 0:
    stops_signal = "NO DATA"
    stops_score = 0
elif buy_stops == 0:
    stops_ratio = 0
    stops_signal = "BEARISH"
    stops_score = -25
elif sell_stops == 0:
    stops_ratio = float("inf")
    stops_signal = "BULLISH"
    stops_score = 25
else:
    stops_ratio = buy_stops / sell_stops
    if stops_ratio > 1.5:
        stops_signal = "BULLISH"
        stops_score = 25
    elif stops_ratio < 0.67:
        stops_signal = "BEARISH"
        stops_score = -25
    else:
        stops_signal = "NEUTRAL"
        stops_score = 0

print(f"\nSTOPS: {stops_signal} ({stops_score:+d} pts)")
print(
    f"  BUY: {buy_stops} | SELL: {sell_stops} | Ratio: {stops_ratio:.2f}x"
    if buy_stops > 0 and sell_stops > 0
    else f"  BUY: {buy_stops} | SELL: {sell_stops}"
)

# 2. ICEBERGS ANALYSIS with sub-type weighting
print("\n" + "-" * 80)

# Sub-type weights
SUBTYPE_WEIGHTS = {
    "TRADE": 1.0,
    "EXECUTION": 0.8,
    "DETECTION": 0.5,
    "MOVEMENT": 0.3,
    "CANCELLATION": 0.2,
    None: 0.5,  # Default for NULL sub-types
}

cur.execute(
    """
    SELECT 
        side,
        iceberg_subtype,
        COUNT(*) as count,
        AVG(price) as avg_price,
        AVG(confidence_score) as avg_confidence
    FROM stops_icebergs
    WHERE symbol = %s
      AND timestamp >= to_timestamp(%s)
      AND timestamp < to_timestamp(%s)
      AND event_type = 'ICEBERG'
    GROUP BY side, iceberg_subtype
    ORDER BY side, iceberg_subtype
""",
    (symbol, start_ts, end_ts),
)

icebergs_data = cur.fetchall()

buy_icebergs_raw = 0
sell_icebergs_raw = 0
buy_icebergs_weighted = 0.0
sell_icebergs_weighted = 0.0

print("ICEBERGS (with sub-type weighting):")
for side, subtype, count, avg_price, avg_conf in icebergs_data:
    weight = SUBTYPE_WEIGHTS.get(subtype, 0.5)
    weighted_count = count * weight

    if side == "BUY":
        buy_icebergs_raw += count
        buy_icebergs_weighted += weighted_count
    else:
        sell_icebergs_raw += count
        sell_icebergs_weighted += weighted_count

    subtype_str = subtype if subtype else "NULL"
    print(
        f"  {side} {subtype_str}: {count} events (weight: {weight}, weighted: {weighted_count:.1f}) @ ${avg_price:,.2f}"
    )

total_icebergs = buy_icebergs_raw + sell_icebergs_raw

# Calculate iceberg signal
if buy_icebergs_weighted == 0 and sell_icebergs_weighted == 0:
    iceberg_signal = "NO DATA"
    iceberg_score = 0
    low_activity_warning = False
elif sell_icebergs_weighted > buy_icebergs_weighted * 2:
    iceberg_signal = "BEARISH"
    iceberg_score = -20
    low_activity_warning = total_icebergs < 20
elif buy_icebergs_weighted > sell_icebergs_weighted * 2:
    iceberg_signal = "BULLISH"
    iceberg_score = 20
    low_activity_warning = total_icebergs < 20
else:
    iceberg_signal = "NEUTRAL"
    iceberg_score = 0
    low_activity_warning = total_icebergs < 20

print(f"\nICEBERGS: {iceberg_signal} ({iceberg_score:+d} pts)")
print(f"  Total: {total_icebergs} events")
print(f"  BUY: {buy_icebergs_raw} (weighted: {buy_icebergs_weighted:.1f})")
print(f"  SELL: {sell_icebergs_raw} (weighted: {sell_icebergs_weighted:.1f})")
if low_activity_warning:
    print(f"  ⚠️  WARNING: Low institutional activity (< 20 icebergs)")
    print(f"  → Signal confidence reduced by 50%")

# 3. MBO ANALYSIS
print("\n" + "-" * 80)

cur.execute(
    """
    SELECT 
        side,
        action,
        COUNT(*) as order_count,
        SUM(size) as total_volume
    FROM mbo_data
    WHERE symbol = %s
      AND timestamp >= to_timestamp(%s)
      AND timestamp < to_timestamp(%s)
      AND action IN ('ADD', 'EXECUTE')
    GROUP BY side, action
    ORDER BY side, action
""",
    (symbol, start_ts, end_ts),
)

mbo_data = cur.fetchall()

buy_orders = 0
sell_orders = 0
buy_volume = 0
sell_volume = 0

for side, action, order_count, total_vol in mbo_data:
    if side == "BUY":
        buy_orders += order_count
        buy_volume += total_vol
    else:
        sell_orders += order_count
        sell_volume += total_vol

# Calculate MBO signal
if buy_orders > 0 and sell_orders > 0:
    order_ratio = buy_orders / sell_orders
    volume_ratio = buy_volume / sell_volume

    if order_ratio > 1.2 and volume_ratio > 1.2:
        mbo_signal = "BULLISH"
        mbo_score = 15
    elif order_ratio < 0.83 and volume_ratio < 0.83:
        mbo_signal = "BEARISH"
        mbo_score = -15
    else:
        mbo_signal = "NEUTRAL"
        mbo_score = 0
else:
    mbo_signal = "NO DATA"
    mbo_score = 0
    order_ratio = 0
    volume_ratio = 0

print(f"MBO FLOW: {mbo_signal} ({mbo_score:+d} pts)")
if buy_orders > 0 and sell_orders > 0:
    print(f"  Orders: {order_ratio:.2f}x | Volume: {volume_ratio:.2f}x")
print(f"  BUY: {buy_orders:,} orders, {buy_volume:,} volume")
print(f"  SELL: {sell_orders:,} orders, {sell_volume:,} volume")

# CALCULATE FINAL SIGNAL
print("\n" + "=" * 80)
total_score = stops_score + iceberg_score + mbo_score
max_score = 75

if total_score == 0:
    raw_confidence = 0
else:
    raw_confidence = abs(total_score) / max_score * 100

# Apply low activity penalty
if low_activity_warning and iceberg_score != 0:
    final_confidence = raw_confidence * 0.5
    print(f"TOTAL SCORE: {total_score:+d} / ±{max_score}")
    print(f"RAW CONFIDENCE: {raw_confidence:.1f}%")
    print(f"AFTER PENALTY: {final_confidence:.1f}% (50% reduction due to low icebergs)")
else:
    final_confidence = raw_confidence
    print(f"TOTAL SCORE: {total_score:+d} / ±{max_score}")
    print(f"CONFIDENCE: {final_confidence:.1f}%")

print("=" * 80)

# Determine signal
if final_confidence < 30:
    signal = "WAIT"
    reason = f"Insufficient confidence ({final_confidence:.1f}% < 30%)"
elif total_score > 0:
    signal = "LONG"
    reason = f"Bullish order flow ({final_confidence:.1f}% confidence)"
elif total_score < 0:
    signal = "SHORT"
    reason = f"Bearish order flow ({final_confidence:.1f}% confidence)"
else:
    signal = "WAIT"
    reason = "Neutral order flow"

print(f"SIGNAL: {signal}")
print(f"REASON: {reason}")

# Show actual outcome
print("\n" + "=" * 80)
print("OUTCOME ANALYSIS")
print("=" * 80)
print("What Actually Happened:")
print("  9:30 AM: Judas swing to $25,840")
print("  9:30-10:00: Reversal begins")
print("  Eventual move: -512 points to $25,328")
print("  Pattern: Bearish reversal after false spike")
print()

if signal == "SHORT":
    print("Model Performance:")
    print("  ✅ CORRECT: Model detected BEARISH move during reversal")
elif signal == "WAIT":
    print("Model Performance:")
    print("  ⚠️  PARTIAL: Model said WAIT (missed the short opportunity)")
    print(f"  Issue: {reason}")
elif signal == "LONG":
    print("Model Performance:")
    print("  ❌ INCORRECT: Model said LONG (would have lost money)")

print("=" * 80)

cur.close()
conn.close()
