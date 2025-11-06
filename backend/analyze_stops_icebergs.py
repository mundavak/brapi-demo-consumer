import psycopg2
from datetime import datetime
import pytz

conn = psycopg2.connect(
    host="localhost",
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)

cur = conn.cursor()
est = pytz.timezone("America/New_York")

print("=" * 80)
print("STOPS & ICEBERGS DATA ANALYSIS")
print("=" * 80)

# 1. Event Type Breakdown
print("\n1. EVENT TYPE BREAKDOWN")
cur.execute(
    """
    SELECT 
        event_type,
        COUNT(*) as total_events,
        COUNT(DISTINCT DATE(timestamp AT TIME ZONE 'America/New_York')) as days,
        AVG(detected_size) as avg_detected_size,
        AVG(estimated_total_size) as avg_estimated_total,
        AVG(confidence_score) as avg_confidence
    FROM stops_icebergs
    WHERE symbol LIKE 'MNQ%'
    GROUP BY event_type
"""
)
print(
    f"\n{'Event Type':<15} {'Total':<12} {'Days':<8} {'Avg Detected':<15} {'Avg Estimated':<15} {'Avg Confidence':<15}"
)
print("-" * 80)
for row in cur.fetchall():
    print(
        f"{row[0]:<15} {row[1]:>11,} {row[2]:>7} {row[3]:>14.2f} {row[4]:>14.2f} {row[5]:>14.2f}"
    )

# 2. Side Breakdown by Event Type
print("\n2. SIDE BREAKDOWN BY EVENT TYPE")
cur.execute(
    """
    SELECT 
        event_type,
        side,
        COUNT(*) as events,
        SUM(detected_size) as total_detected,
        SUM(estimated_total_size) as total_estimated,
        AVG(confidence_score) as avg_confidence
    FROM stops_icebergs
    WHERE symbol LIKE 'MNQ%'
    GROUP BY event_type, side
    ORDER BY event_type, side
"""
)
print(
    f"\n{'Type':<12} {'Side':<8} {'Events':<12} {'Total Detected':<18} {'Total Estimated':<18} {'Avg Confidence':<15}"
)
print("-" * 80)
for row in cur.fetchall():
    print(
        f"{row[0]:<12} {row[1]:<8} {row[2]:>11,} {row[3]:>17,} {row[4]:>17,} {row[5]:>14.2f}"
    )

# 3. CBDR Window Analysis
print("\n3. CBDR WINDOW DISTRIBUTION")
cur.execute(
    """
    SELECT 
        cbdr_window,
        event_type,
        COUNT(*) as events,
        AVG(detected_size) as avg_size,
        AVG(confidence_score) as avg_conf
    FROM stops_icebergs
    WHERE symbol LIKE 'MNQ%'
    GROUP BY cbdr_window, event_type
    ORDER BY cbdr_window, event_type
"""
)
print(
    f"\n{'CBDR Window':<20} {'Type':<12} {'Events':<12} {'Avg Size':<12} {'Avg Conf':<12}"
)
print("-" * 80)
for row in cur.fetchall():
    window = row[0] if row[0] else "NULL"
    print(f"{window:<20} {row[1]:<12} {row[2]:>11,} {row[3]:>11.2f} {row[4]:>11.2f}")

# 4. Nov 5, 2025 PRE_NY Window Analysis (7:30-9:00 AM)
print("\n4. NOV 5, 2025 - PRE_NY WINDOW (7:30-9:00 AM EST)")
cur.execute(
    """
    SELECT 
        event_type,
        side,
        COUNT(*) as events,
        SUM(detected_size) as detected,
        SUM(estimated_total_size) as estimated,
        AVG(confidence_score) as conf
    FROM stops_icebergs
    WHERE symbol LIKE 'MNQ%'
    AND timestamp AT TIME ZONE 'America/New_York' >= '2025-11-05 07:30:00'
    AND timestamp AT TIME ZONE 'America/New_York' <= '2025-11-05 09:00:00'
    AND cbdr_window = 'PRE_NY'
    GROUP BY event_type, side
    ORDER BY event_type, side
"""
)
print(
    f"\n{'Type':<12} {'Side':<8} {'Events':<10} {'Detected':<12} {'Estimated':<12} {'Confidence':<12}"
)
print("-" * 80)
for row in cur.fetchall():
    print(
        f"{row[0]:<12} {row[1]:<8} {row[2]:>9} {row[3]:>11} {row[4]:>11} {row[5]:>11.2f}"
    )

# 5. Temporal Distribution - Nov 5 PRE_NY
print("\n5. TEMPORAL DISTRIBUTION - NOV 5 PRE_NY (10-min buckets)")
cur.execute(
    """
    SELECT 
        DATE_TRUNC('minute', timestamp AT TIME ZONE 'America/New_York') 
            - INTERVAL '1 minute' * (EXTRACT(MINUTE FROM timestamp AT TIME ZONE 'America/New_York')::int % 10) as time_bucket,
        event_type,
        COUNT(*) as events,
        SUM(CASE WHEN side = 'BUY' THEN detected_size ELSE 0 END) as buy_detected,
        SUM(CASE WHEN side = 'SELL' THEN detected_size ELSE 0 END) as sell_detected
    FROM stops_icebergs
    WHERE symbol LIKE 'MNQ%'
    AND timestamp AT TIME ZONE 'America/New_York' >= '2025-11-05 07:30:00'
    AND timestamp AT TIME ZONE 'America/New_York' <= '2025-11-05 09:00:00'
    AND cbdr_window = 'PRE_NY'
    GROUP BY time_bucket, event_type
    ORDER BY time_bucket, event_type
    LIMIT 20
"""
)
print(f"\n{'Time':<20} {'Type':<12} {'Events':<10} {'Buy Size':<12} {'Sell Size':<12}")
print("-" * 80)
for row in cur.fetchall():
    print(f"{str(row[0])[:-6]:<20} {row[1]:<12} {row[2]:>9} {row[3]:>11} {row[4]:>11}")

# 6. Confidence Score Distribution
print("\n6. CONFIDENCE SCORE DISTRIBUTION")
cur.execute(
    """
    SELECT 
        event_type,
        CASE 
            WHEN confidence_score = 0 THEN '0 (No Confidence)'
            WHEN confidence_score <= 0.3 THEN '0.01-0.30 (Low)'
            WHEN confidence_score <= 0.6 THEN '0.31-0.60 (Medium)'
            WHEN confidence_score <= 0.8 THEN '0.61-0.80 (High)'
            ELSE '0.81-1.00 (Very High)'
        END as conf_range,
        COUNT(*) as events
    FROM stops_icebergs
    WHERE symbol LIKE 'MNQ%'
    GROUP BY event_type, conf_range
    ORDER BY event_type, conf_range
"""
)
print(f"\n{'Type':<12} {'Confidence Range':<25} {'Events':<12}")
print("-" * 80)
for row in cur.fetchall():
    print(f"{row[0]:<12} {row[1]:<25} {row[2]:>11,}")

# 7. Sample High-Confidence Events from Nov 5 PRE_NY
print("\n7. SAMPLE HIGH-CONFIDENCE EVENTS (Nov 5 PRE_NY, confidence > 0.5)")
cur.execute(
    """
    SELECT 
        timestamp AT TIME ZONE 'America/New_York' as ts,
        event_type,
        side,
        price,
        detected_size,
        estimated_total_size,
        confidence_score
    FROM stops_icebergs
    WHERE symbol LIKE 'MNQ%'
    AND timestamp AT TIME ZONE 'America/New_York' >= '2025-11-05 07:30:00'
    AND timestamp AT TIME ZONE 'America/New_York' <= '2025-11-05 09:00:00'
    AND cbdr_window = 'PRE_NY'
    AND confidence_score > 0.5
    ORDER BY confidence_score DESC, timestamp
    LIMIT 10
"""
)
print(
    f"\n{'Time':<20} {'Type':<10} {'Side':<6} {'Price':<12} {'Detected':<10} {'Estimated':<10} {'Conf':<8}"
)
print("-" * 80)
rows = cur.fetchall()
if rows:
    for row in rows:
        print(
            f"{str(row[0])[:-6]:<20} {row[1]:<10} {row[2]:<6} {row[3]:>11.2f} {row[4]:>9} {row[5]:>9} {row[6]:>7.2f}"
        )
else:
    print("No high-confidence events found in this window")

print("\n" + "=" * 80)
print("KEY INSIGHTS FOR TRADING ALGORITHM:")
print("=" * 80)
print(
    """
STOPS:
- Represent stop-loss orders being triggered (liquidity grabs)
- BUY stops = buyers' stops hit = price moved DOWN (bearish move)
- SELL stops = sellers' stops hit = price moved UP (bullish move)
- High BUY stops → expect BULLISH reversal (ICT concept: grab liquidity below, then up)
- High SELL stops → expect BEARISH reversal (grab liquidity above, then down)

ICEBERGS:
- Hidden institutional orders (large orders split into small visible pieces)
- BUY icebergs = hidden BID support (institutions accumulating)
- SELL icebergs = hidden ASK resistance (institutions distributing)
- Higher confidence_score = more reliable detection
- estimated_total_size shows the true institutional interest

USAGE FOR BIAS:
1. Stop imbalance (BUY/SELL ratio) predicts reversal direction
2. Iceberg imbalance shows institutional positioning
3. Combine both: stops show where price went, icebergs show where institutions are positioned
4. CBDR windows isolate setup periods before main trading sessions
"""
)

cur.close()
conn.close()
