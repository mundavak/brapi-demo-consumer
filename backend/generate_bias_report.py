"""
Trading Bias Report Generator for MNQ
Analyzes overnight structure, absorption, icebergs, and stops to generate trading bias
"""

import psycopg2
from datetime import datetime, timedelta
import pytz
import json
from collections import defaultdict

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}

EST = pytz.timezone("America/New_York")


def get_time_range():
    """Calculate time range from yesterday 20:45 EST to now"""
    now = datetime.now(EST)
    yesterday = now - timedelta(days=1)
    start = yesterday.replace(hour=20, minute=45, second=0, microsecond=0)
    return start, now


def get_nine_thirty_cutoff():
    """Get 9:30 AM EST cutoff for regular session (exclusive)"""
    now = datetime.now(EST)
    nine_thirty = now.replace(hour=9, minute=30, second=0, microsecond=0)
    return nine_thirty


def get_previous_trading_day():
    """Get the previous trading day (skips weekends for futures)"""
    now = datetime.now(EST)
    current_weekday = now.weekday()  # 0=Monday, 6=Sunday

    if current_weekday == 0:  # Monday
        days_back = 3  # Go back to Friday
    elif current_weekday == 6:  # Sunday
        days_back = 2  # Go back to Friday
    else:
        days_back = 1  # Go back one day

    prev_day = now - timedelta(days=days_back)
    return prev_day


def get_ict_kill_zone():
    """
    Identify current ICT Kill Zone for time-based bias weighting
    Returns: (zone_name, weight_multiplier, zone_description)
    """
    now = datetime.now(EST)
    hour = now.hour
    minute = now.minute
    current_time = hour + minute / 60.0

    # Asian Session / Accumulation (20:00 - 02:00 EST)
    if (hour >= 20) or (hour < 2):
        return (
            "ASIAN_ACCUMULATION",
            0.5,
            "Accumulation phase - Low probability setups",
        )

    # London Open / Manipulation (02:00 - 05:00 EST)
    elif 2 <= hour < 5:
        return ("LONDON_OPEN", 1.5, "Manipulation phase - Judas swings likely")

    # London Close / NY Open Overlap (08:30 - 11:00 EST)
    elif (hour == 8 and minute >= 30) or (9 <= hour < 11):
        return ("NY_OPEN", 2.0, "Distribution phase - HIGHEST probability setups")

    # NY Lunch (11:00 - 13:30 EST)
    elif 11 <= hour < 13 or (hour == 13 and minute < 30):
        return ("NY_LUNCH", 0.7, "Lunch consolidation - Lower probability")

    # NY Close (15:00 - 16:00 EST)
    elif 15 <= hour < 16:
        return ("NY_CLOSE", 1.2, "End of day positioning - Moderate probability")

    # After hours (16:00 - 20:00 EST)
    else:
        return ("AFTER_HOURS", 0.3, "After hours - Very low probability")


def get_power_of_three_phase(cursor, start_time, end_time):
    """
    Determine Power of Three phase (Accumulation, Manipulation, Distribution, Expansion)
    Based on price action, volatility, and order flow
    """
    now = datetime.now(EST)
    hour = now.hour

    # Get recent volatility and range data
    cursor.execute(
        """
        SELECT 
            AVG(high - low) as avg_range,
            STDDEV(close) as volatility,
            MAX(high) - MIN(low) as total_range,
            COUNT(*) as candle_count
        FROM ohlc_candles
        WHERE symbol = 'MNQ'
        AND timeframe = '5m'
        AND timestamp >= %s - INTERVAL '2 hours'
        AND timestamp <= %s
    """,
        (end_time, end_time),
    )

    stats = cursor.fetchone()
    if not stats or not stats[0]:
        return ("UNKNOWN", 0, "Insufficient data")

    avg_range, volatility, total_range, candle_count = stats

    # Calculate range efficiency (trending vs ranging)
    range_efficiency = (
        (total_range / (avg_range * candle_count)) if candle_count > 0 else 0
    )

    # ACCUMULATION: Tight range, low volatility
    if range_efficiency < 0.3 and volatility < avg_range * 0.5:
        return ("ACCUMULATION", 50, "Tight range consolidation - Wait for manipulation")

    # MANIPULATION: Sharp move with quick reversal (typically London open)
    elif 2 <= hour < 5 and volatility > avg_range * 1.5:
        return ("MANIPULATION", 75, "Liquidity grab detected - Fade the move")

    # EXPANSION: Large directional move, high volatility
    elif range_efficiency > 0.7 and volatility > avg_range * 2:
        return ("EXPANSION", 85, "Strong trend - Expect retracement soon")

    # DISTRIBUTION: Moderate trending after accumulation
    else:
        return ("DISTRIBUTION", 80, "Directional move in progress - Follow the trend")


def analyze_overnight_structure(cursor, start_time, end_time):
    """Analyze overnight price structure and key levels (excludes regular session 9:30 AM+)"""
    print("\n" + "=" * 80)
    print("OVERNIGHT STRUCTURE ANALYSIS")
    print("=" * 80)

    # Get 9:30 AM cutoff (exclusive of regular session)
    nine_thirty = get_nine_thirty_cutoff()

    # Get OHLC structure (overnight only - before 9:30 AM)
    cursor.execute(
        """
        SELECT 
            MIN(low) as overnight_low, 
            MAX(high) as overnight_high,
            (array_agg(open ORDER BY timestamp))[1] as session_open,
            AVG(close) as avg_price,
            STDDEV(close) as volatility
        FROM ohlc_candles
        WHERE symbol = 'MNQ' 
        AND timeframe = '5m'
        AND timestamp >= %s 
        AND timestamp < %s
    """,
        (start_time, nine_thirty),
    )

    structure = cursor.fetchone()

    # Get most recent 5m close price (actual current price, not limited to overnight)
    cursor.execute(
        """
        SELECT close
        FROM ohlc_candles
        WHERE symbol = 'MNQ'
        AND timeframe = '5m'
        AND timestamp >= %s
        ORDER BY timestamp DESC
        LIMIT 1
    """,
        (start_time,),
    )

    current_price_result = cursor.fetchone()
    current_price = current_price_result[0] if current_price_result else None

    if structure and structure[0] and current_price:
        overnight_low, overnight_high, session_open, avg_price, volatility = structure
        range_size = overnight_high - overnight_low

        # Get previous trading day high/low (9:30 AM to 4:00 PM, skips weekends)
        prev_day = get_previous_trading_day()
        prev_day_start = prev_day.replace(hour=9, minute=30, second=0, microsecond=0)
        prev_day_end = prev_day.replace(hour=16, minute=0, second=0, microsecond=0)

        cursor.execute(
            """
            SELECT 
                MIN(low) as prev_day_low,
                MAX(high) as prev_day_high
            FROM ohlc_candles
            WHERE symbol = 'MNQ'
            AND timeframe = '5m'
            AND timestamp BETWEEN %s AND %s
        """,
            (prev_day_start, prev_day_end),
        )

        prev_day_result = cursor.fetchone()
        prev_day_low = (
            prev_day_result[0] if prev_day_result and prev_day_result[0] else None
        )
        prev_day_high = (
            prev_day_result[1] if prev_day_result and prev_day_result[1] else None
        )

        print(f"\nPrice Structure:")
        print(f"  Overnight Low:    ${overnight_low:,.2f}")
        print(f"  Overnight High:   ${overnight_high:,.2f}")
        print(
            f"  Range:            ${range_size:,.2f} ({(range_size/session_open*100):.2f}%)"
        )
        print(f"  Session Open:     ${session_open:,.2f}")
        print(f"  Current Price:    ${current_price:,.2f}")
        print(f"  Average Price:    ${avg_price:,.2f}")
        print(f"  Volatility:       ${volatility:,.2f}")

        # Determine position in range
        range_position = (current_price - overnight_low) / range_size * 100
        print(f"  Range Position:   {range_position:.1f}% (0=low, 100=high)")

        if prev_day_low and prev_day_high:
            prev_day_name = prev_day.strftime("%A %m/%d")  # e.g., "Friday 11/15"
            print(f"\nPrevious Trading Day Structure ({prev_day_name}):")
            print(f"  Previous Day Low:  ${prev_day_low:,.2f}")
            print(f"  Previous Day High: ${prev_day_high:,.2f}")
            prev_day_range = prev_day_high - prev_day_low
            print(f"  Previous Range:    ${prev_day_range:,.2f}")

            # Analyze current price relative to previous day
            if current_price > prev_day_high:
                print(
                    f"  Status:            ABOVE previous day high (+{current_price - prev_day_high:,.2f})"
                )
            elif current_price < prev_day_low:
                print(
                    f"  Status:            BELOW previous day low ({current_price - prev_day_low:,.2f})"
                )
            else:
                print(f"  Status:            INSIDE previous day range")

        return {
            "overnight_low": float(overnight_low),
            "overnight_high": float(overnight_high),
            "session_open": float(session_open),
            "current_price": float(current_price),
            "avg_price": float(avg_price),
            "range_size": float(range_size),
            "range_position": float(range_position),
            "volatility": float(volatility),
            "prev_day_low": float(prev_day_low) if prev_day_low else None,
            "prev_day_high": float(prev_day_high) if prev_day_high else None,
        }

    return None


def analyze_volume_profile(cursor, start_time, end_time):
    """Analyze volume profile to find high-volume nodes"""
    print("\n" + "=" * 80)
    print("VOLUME PROFILE ANALYSIS")
    print("=" * 80)

    # Using MNQZ5.CME@RITHMIC (most recent MBO data)
    cursor.execute(
        """
        SELECT 
            ROUND(price::numeric, -1)::integer as price_level,
            SUM(size) as total_volume,
            COUNT(*) as touch_count
        FROM mbo_data
        WHERE symbol = 'MNQZ5.CME@RITHMIC'
        AND timestamp BETWEEN %s AND %s
        AND action IN ('ADD', 'MODIFY', 'EXECUTE', 'TRADE')
        GROUP BY price_level
        ORDER BY total_volume DESC
        LIMIT 10
    """,
        (start_time, end_time),
    )

    print(f"\n{'Price Level':<15} {'Volume':<20} {'Touches':<10}")
    print("-" * 50)

    volume_nodes = []
    for price_level, volume, touches in cursor.fetchall():
        print(f"${price_level:<14,.0f} {volume:<20,} {touches:<10,}")
        volume_nodes.append(
            {
                "price": float(price_level),
                "volume": int(volume),
                "touches": int(touches),
            }
        )

    return volume_nodes


def analyze_absorption(cursor, start_time, end_time):
    """Analyze significant absorption events"""
    print("\n" + "=" * 80)
    print("ABSORPTION ANALYSIS (Significance > 0.7)")
    print("=" * 80)

    # Using MNQZ5 and MNQZ5.CME@RITHMIC symbols (absorption data)
    cursor.execute(
        """
        SELECT 
            price,
            side,
            event_type,
            SUM(absorbed_volume) as total_absorbed,
            AVG(significance_score) as avg_significance,
            COUNT(*) as event_count,
            MAX(timestamp) as last_seen
        FROM absorption_events
        WHERE symbol IN ('MNQZ5', 'MNQZ5.CME@RITHMIC')
        AND timestamp BETWEEN %s AND %s
        AND significance_score > 0.7
        GROUP BY price, side, event_type
        ORDER BY total_absorbed DESC
        LIMIT 15
    """,
        (start_time, end_time),
    )

    print(
        f"\n{'Price':<12} {'Side':<6} {'Type':<12} {'Volume':<15} {'Avg Sig':<10} {'Count':<8} {'Last Seen'}"
    )
    print("-" * 95)

    absorption_zones = []
    for price, side, event_type, volume, sig, count, last_seen in cursor.fetchall():
        print(
            f"${price:<11,.2f} {side:<6} {event_type:<12} {volume:<15,} {sig:<10.3f} {count:<8} {last_seen.strftime('%H:%M:%S')}"
        )
        absorption_zones.append(
            {
                "price": float(price),
                "side": side,
                "type": event_type,
                "volume": int(volume),
                "significance": float(sig),
                "count": int(count),
                "last_seen": last_seen.isoformat(),
            }
        )

    return absorption_zones


def analyze_icebergs(cursor, start_time, end_time):
    """Analyze iceberg order positions"""
    print("\n" + "=" * 80)
    print("ICEBERG POSITIONING (Size >= 20 contracts)")
    print("=" * 80)

    # Focus on recent icebergs (last 4 hours)
    recent_start = end_time - timedelta(hours=4)

    # Using MNQZ5.CME@RITHMIC symbol
    # Filter by size instead of confidence (since all confidence scores are 0)
    cursor.execute(
        """
        SELECT 
            price,
            side,
            AVG(estimated_total_size) as avg_size,
            COUNT(*) as detection_count,
            MAX(timestamp) as last_seen,
            STRING_AGG(DISTINCT iceberg_subtype, ', ' ORDER BY iceberg_subtype) as subtypes
        FROM stops_icebergs
        WHERE symbol = 'MNQZ5.CME@RITHMIC'
        AND event_type = 'ICEBERG'
        AND timestamp BETWEEN %s AND %s
        AND estimated_total_size >= 20
        GROUP BY price, side
        HAVING COUNT(*) >= 2
        ORDER BY avg_size DESC, detection_count DESC
        LIMIT 15
    """,
        (recent_start, end_time),
    )

    print(
        f"\n{'Price':<12} {'Side':<6} {'Avg Size':<15} {'Events':<10} {'Types':<30} {'Last Seen'}"
    )
    print("-" * 95)

    iceberg_positions = []
    for price, side, avg_size, count, last_seen, subtypes in cursor.fetchall():
        print(
            f"${price:<11,.2f} {side:<6} {avg_size:<15,.0f} {count:<10} {subtypes:<30} {last_seen.strftime('%H:%M:%S')}"
        )
        iceberg_positions.append(
            {
                "price": float(price),
                "side": side,
                "avg_size": float(avg_size),
                "detections": int(count),
                "subtypes": subtypes,
                "last_seen": last_seen.isoformat(),
            }
        )

    return iceberg_positions


def analyze_stop_clusters(cursor, start_time, end_time):
    """Analyze stop cluster zones"""
    print("\n" + "=" * 80)
    print("STOP CLUSTER ZONES (Last 6 hours)")
    print("=" * 80)

    # Focus on recent stops (last 6 hours)
    recent_start = end_time - timedelta(hours=6)

    # Using MNQZ5.CME@RITHMIC symbol
    cursor.execute(
        """
        SELECT 
            price,
            side,
            SUM(detected_size) as total_density,
            AVG(confidence_score) as avg_confidence,
            COUNT(*) as cluster_count,
            MAX(timestamp) as last_seen
        FROM stops_icebergs
        WHERE symbol = 'MNQZ5.CME@RITHMIC'
        AND event_type IN ('STOP', 'STOP_CLUSTER')
        AND timestamp BETWEEN %s AND %s
        GROUP BY price, side
        ORDER BY total_density DESC
        LIMIT 10
    """,
        (recent_start, end_time),
    )

    print(
        f"\n{'Price':<12} {'Side':<6} {'Density':<15} {'Confidence':<12} {'Clusters':<10} {'Last Seen'}"
    )
    print("-" * 80)

    stop_zones = []
    for price, side, density, confidence, count, last_seen in cursor.fetchall():
        print(
            f"${price:<11,.2f} {side:<6} {density:<15,} {confidence:<12.3f} {count:<10} {last_seen.strftime('%H:%M:%S')}"
        )
        stop_zones.append(
            {
                "price": float(price),
                "side": side,
                "density": int(density),
                "confidence": float(confidence),
                "clusters": int(count),
                "last_seen": last_seen.isoformat(),
            }
        )

    return stop_zones


def detect_fair_value_gaps(cursor, start_time, end_time):
    """
    Detect Fair Value Gaps (FVG) - 3-candle pattern showing institutional inefficiency
    Bullish FVG: Gap between candle 1 high and candle 3 low
    Bearish FVG: Gap between candle 1 low and candle 3 high

    Detects FVGs across multiple timeframes (5m, 15m, 1h, 2h, 4h)
    Higher timeframes indicate institutional interest
    """
    print("\n" + "=" * 80)
    print("FAIR VALUE GAP (FVG) ANALYSIS - MULTI-TIMEFRAME")
    print("=" * 80)

    all_fvgs = []

    # Check multiple timeframes (ordered by significance: higher TF = more institutional)
    timeframes = [
        ("4h", "4h", 8),  # 4-hour (most significant)
        ("2h", "2h", 6),  # 2-hour
        ("1h", "1h", 4),  # 1-hour
        ("15m", "15m", 2),  # 15-minute
        ("5m", "5m", 1),  # 5-minute (least significant)
    ]

    for tf_db, tf_label, lookback_hours in timeframes:
        cursor.execute(
            """
            SELECT timestamp, open, high, low, close
            FROM ohlc_candles
            WHERE symbol = 'MNQ'
            AND timeframe = %s
            AND timestamp >= %s - INTERVAL '%s hours'
            AND timestamp <= %s
            ORDER BY timestamp DESC
            LIMIT 100
        """,
            (tf_db, end_time, lookback_hours, end_time),
        )

        candles = cursor.fetchall()

        # Check each 3-candle pattern
        for i in range(len(candles) - 2):
            candle_3 = candles[i]  # Most recent
            candle_2 = candles[i + 1]  # Middle
            candle_1 = candles[i + 2]  # Oldest

            # Bullish FVG: Gap UP (candle 1 high < candle 3 low)
            if candle_1[2] < candle_3[3]:  # high[1] < low[3]
                gap_size = candle_3[3] - candle_1[2]
                all_fvgs.append(
                    {
                        "type": "BULLISH_FVG",
                        "timeframe": tf_label,
                        "timestamp": candle_3[0].isoformat(),
                        "gap_low": float(candle_1[2]),
                        "gap_high": float(candle_3[3]),
                        "gap_size": float(gap_size),
                        "age_minutes": int(
                            (end_time - candle_3[0]).total_seconds() / 60
                        ),
                        "tf_priority": 6
                        - lookback_hours,  # Higher TF = higher priority
                    }
                )

            # Bearish FVG: Gap DOWN (candle 1 low > candle 3 high)
            elif candle_1[3] > candle_3[2]:  # low[1] > high[3]
                gap_size = candle_1[3] - candle_3[2]
                all_fvgs.append(
                    {
                        "type": "BEARISH_FVG",
                        "timeframe": tf_label,
                        "timestamp": candle_3[0].isoformat(),
                        "gap_low": float(candle_3[2]),
                        "gap_high": float(candle_1[3]),
                        "gap_size": float(gap_size),
                        "age_minutes": int(
                            (end_time - candle_3[0]).total_seconds() / 60
                        ),
                        "tf_priority": 6
                        - lookback_hours,  # Higher TF = higher priority
                    }
                )

    # Sort by timeframe priority (higher first), then gap size, then recency
    fvgs_sorted = sorted(
        all_fvgs,
        key=lambda x: (x["tf_priority"], x["gap_size"], -x["age_minutes"]),
        reverse=True,
    )[
        :15
    ]  # Show top 15 most significant FVGs

    if fvgs_sorted:
        print(
            f"\n{'Type':<18} {'TF':<6} {'Gap Range':<25} {'Size':<10} {'Age (min)':<10}"
        )
        print("-" * 80)
        for fvg in fvgs_sorted:
            gap_range = f"${fvg['gap_low']:,.2f} - ${fvg['gap_high']:,.2f}"
            fvg_label = f"{fvg['type']} ({fvg['timeframe']})"
            print(
                f"{fvg_label:<18} {fvg['timeframe']:<6} {gap_range:<25} ${fvg['gap_size']:<9.2f} {fvg['age_minutes']:<10}"
            )
    else:
        print("\nNo significant Fair Value Gaps detected")

    return fvgs_sorted


def detect_market_structure_shift(cursor, start_time, end_time):
    """
    Detect Market Structure Shifts (MSS)
    Bullish MSS: Lower Low → Higher Low (break of structure to upside)
    Bearish MSS: Higher High → Lower High (break of structure to downside)
    """
    print("\n" + "=" * 80)
    print("MARKET STRUCTURE SHIFT (MSS) DETECTION")
    print("=" * 80)

    # Get swing highs and lows from 5m candles
    cursor.execute(
        """
        WITH swing_points AS (
            SELECT 
                timestamp,
                high,
                low,
                LAG(high, 1) OVER (ORDER BY timestamp) as prev_high,
                LAG(low, 1) OVER (ORDER BY timestamp) as prev_low,
                LAG(high, 2) OVER (ORDER BY timestamp) as prev2_high,
                LAG(low, 2) OVER (ORDER BY timestamp) as prev2_low,
                LEAD(high, 1) OVER (ORDER BY timestamp) as next_high,
                LEAD(low, 1) OVER (ORDER BY timestamp) as next_low
            FROM ohlc_candles
            WHERE symbol = 'MNQ'
            AND timeframe = '5m'
            AND timestamp >= %s - INTERVAL '4 hours'
            AND timestamp <= %s
        )
        SELECT timestamp, high, low, prev_high, prev_low, prev2_high, prev2_low
        FROM swing_points
        WHERE prev_high IS NOT NULL 
        AND prev2_high IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 50
    """,
        (end_time, end_time),
    )

    swings = cursor.fetchall()
    mss_events = []

    for i in range(len(swings) - 2):
        current = swings[i]
        prev = swings[i + 1]
        prev2 = swings[i + 2]

        # Bullish MSS: Lower Low → Higher Low
        if prev2[2] > prev[2] and current[2] > prev[2]:  # LL → HL
            mss_events.append(
                {
                    "type": "BULLISH_MSS",
                    "timestamp": current[0].isoformat(),
                    "price": float(current[2]),
                    "description": "Break of Structure to upside",
                }
            )

        # Bearish MSS: Higher High → Lower High
        elif prev2[1] < prev[1] and current[1] < prev[1]:  # HH → LH
            mss_events.append(
                {
                    "type": "BEARISH_MSS",
                    "timestamp": current[0].isoformat(),
                    "price": float(current[1]),
                    "description": "Break of Structure to downside",
                }
            )

    # Show most recent MSS events
    recent_mss = mss_events[:5]

    if recent_mss:
        print(f"\n{'Type':<15} {'Price':<12} {'Time':<20} {'Description'}")
        print("-" * 80)
        for mss in recent_mss:
            timestamp = datetime.fromisoformat(mss["timestamp"]).strftime("%H:%M:%S")
            print(
                f"{mss['type']:<15} ${mss['price']:<11,.2f} {timestamp:<20} {mss['description']}"
            )
    else:
        print("\nNo recent Market Structure Shifts detected")

    return recent_mss


def calculate_ipda_ranges(cursor, end_time):
    """
    Calculate IPDA Lookback Ranges (20, 40, 60 day)
    Track Internal Range Liquidity (FVGs) vs External Range Liquidity (Highs/Lows)
    """
    print("\n" + "=" * 80)
    print("IPDA LOOKBACK RANGES")
    print("=" * 80)

    ranges = {}

    for days in [20, 40, 60]:
        lookback_start = end_time - timedelta(days=days)

        cursor.execute(
            """
            SELECT 
                MIN(low) as range_low,
                MAX(high) as range_high
            FROM ohlc_candles
            WHERE symbol = 'MNQ'
            AND timeframe = '5m'
            AND timestamp >= %s
            AND timestamp <= %s
        """,
            (lookback_start, end_time),
        )

        result = cursor.fetchone()
        if result and result[0]:
            range_low, range_high = result
            range_size = range_high - range_low

            ranges[f"{days}day"] = {
                "low": float(range_low),
                "high": float(range_high),
                "size": float(range_size),
                "midpoint": float((range_high + range_low) / 2),
            }

            print(f"\n{days}-Day Range:")
            print(f"  Low:      ${range_low:,.2f}")
            print(f"  High:     ${range_high:,.2f}")
            print(f"  Midpoint: ${(range_high + range_low) / 2:,.2f}")
            print(f"  Size:     ${range_size:,.2f}")

    return ranges


def calculate_vwap_standard_deviations(cursor, end_time, vwap_value):
    """
    Calculate VWAP Standard Deviation bands (1, 2, 3 SD)
    Used for mean reversion and target projection
    """
    cursor.execute(
        """
        SELECT STDDEV(close) as std_dev
        FROM ohlc_candles
        WHERE symbol = 'MNQ'
        AND timeframe = '5m'
        AND timestamp >= %s - INTERVAL '1 day'
        AND timestamp <= %s
    """,
        (end_time, end_time),
    )

    result = cursor.fetchone()
    std_dev = result[0] if result and result[0] else 50.0  # Default fallback

    return {
        "vwap": float(vwap_value),
        "std_dev": float(std_dev),
        "+1sd": float(vwap_value + std_dev),
        "+2sd": float(vwap_value + 2 * std_dev),
        "+3sd": float(vwap_value + 3 * std_dev),
        "-1sd": float(vwap_value - std_dev),
        "-2sd": float(vwap_value - 2 * std_dev),
        "-3sd": float(vwap_value - 3 * std_dev),
    }


def analyze_vwap(cursor, start_time, end_time):
    """Analyze VWAP levels for Judas swing detection and daily bias"""
    print("\n" + "=" * 80)
    print("VWAP ANALYSIS (Judas Swing & Daily Bias)")
    print("=" * 80)

    # Get latest VWAP data
    cursor.execute(
        """
        SELECT 
            v.timestamp,
            v.vwap_930am,
            v.vwap_daily,
            c.close as current_price,
            c.high as candle_high,
            c.low as candle_low
        FROM vwap_levels v
        JOIN ohlc_candles c ON 
            v.timestamp = c.timestamp 
            AND v.symbol = c.symbol 
            AND v.timeframe = c.timeframe
        WHERE v.symbol = 'MNQ'
        AND v.timeframe = '5m'
        AND v.timestamp BETWEEN %s AND %s
        ORDER BY v.timestamp DESC
        LIMIT 1
    """,
        (start_time, end_time),
    )

    vwap_data = cursor.fetchone()
    if not vwap_data:
        print("  ⚠️  No VWAP data available for this period")
        return None

    timestamp, vwap_930, vwap_daily, current_price, candle_high, candle_low = vwap_data

    # Convert to float for calculations
    vwap_930 = float(vwap_930)
    vwap_daily = float(vwap_daily)
    current_price = float(current_price)

    # Calculate distances
    diff_930 = current_price - vwap_930
    diff_daily = current_price - vwap_daily
    pct_930 = (diff_930 / vwap_930) * 100
    pct_daily = (diff_daily / vwap_daily) * 100

    print(f"\nLatest VWAP Data ({timestamp.strftime('%Y-%m-%d %H:%M')}):")
    print(f"  Current Price:     ${current_price:,.2f}")
    print(
        f"  9:30 AM VWAP:      ${vwap_930:,.2f} (diff: {diff_930:+.2f}, {pct_930:+.2f}%)"
    )
    print(
        f"  Daily VWAP:        ${vwap_daily:,.2f} (diff: {diff_daily:+.2f}, {pct_daily:+.2f}%)"
    )

    # Determine bias from Daily VWAP
    if current_price > vwap_daily:
        vwap_bias = "BULLISH"
        print(f"  📈 Daily Bias:     BULLISH (above Daily VWAP)")
    elif current_price < vwap_daily:
        vwap_bias = "BEARISH"
        print(f"  📉 Daily Bias:     BEARISH (below Daily VWAP)")
    else:
        vwap_bias = "NEUTRAL"
        print(f"  ➡️  Daily Bias:     NEUTRAL (at Daily VWAP)")

    # Detect recent VWAP crosses (Judas swing detection)
    cursor.execute(
        """
        WITH vwap_with_lag AS (
            SELECT 
                v.timestamp,
                c.close,
                v.vwap_930am,
                LAG(c.close) OVER (ORDER BY v.timestamp) as prev_close,
                CASE 
                    WHEN LAG(c.close) OVER (ORDER BY v.timestamp) < v.vwap_930am 
                         AND c.close > v.vwap_930am THEN 'BULLISH_CROSS'
                    WHEN LAG(c.close) OVER (ORDER BY v.timestamp) > v.vwap_930am 
                         AND c.close < v.vwap_930am THEN 'BEARISH_CROSS'
                    ELSE NULL
                END as cross_type
            FROM vwap_levels v
            JOIN ohlc_candles c ON 
                v.timestamp = c.timestamp 
                AND v.symbol = c.symbol 
                AND v.timeframe = c.timeframe
            WHERE v.symbol = 'MNQ'
            AND v.timeframe = '5m'
            AND v.timestamp >= %s - INTERVAL '2 hours'
            AND v.timestamp <= %s
        )
        SELECT timestamp, close, vwap_930am, cross_type
        FROM vwap_with_lag
        WHERE cross_type IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 5
    """,
        (end_time, end_time),
    )

    crosses = cursor.fetchall()
    if crosses:
        print(f"\n  ⚡ Recent 9:30 AM VWAP Crosses (Judas Swings):")
        for cross_time, cross_price, cross_vwap, cross_type in crosses:
            direction = "📈" if cross_type == "BULLISH_CROSS" else "📉"
            print(
                f"     {direction} {cross_time.strftime('%H:%M')} - ${cross_price:,.2f} crossed ${cross_vwap:,.2f} ({cross_type.replace('_', ' ')})"
            )
    else:
        print(f"\n  ⚡ No 9:30 AM VWAP crosses in last 2 hours")

    return {
        "timestamp": timestamp.isoformat(),
        "current_price": float(current_price),
        "vwap_930am": float(vwap_930),
        "vwap_daily": float(vwap_daily),
        "diff_930am": float(diff_930),
        "diff_daily": float(diff_daily),
        "pct_930am": float(pct_930),
        "pct_daily": float(pct_daily),
        "daily_bias": vwap_bias,
        "recent_crosses": [
            {
                "timestamp": cross[0].isoformat(),
                "price": float(cross[1]),
                "vwap": float(cross[2]),
                "type": cross[3],
            }
            for cross in crosses
        ],
    }


def calculate_bias(
    structure,
    absorption_zones,
    iceberg_positions,
    stop_zones,
    vwap_analysis,
    fvgs=None,
    mss_events=None,
    ipda_ranges=None,
    po3_phase=None,
    kill_zone=None,
):
    """
    Calculate overall trading bias based on multiple ICT factors
    Enhanced with: Kill Zones, FVGs, MSS, IPDA Ranges, Power of Three phases
    """
    print("\n" + "=" * 80)
    print("BIAS CALCULATION")
    print("=" * 80)

    bias_score = 50  # Start neutral
    confidence = 0
    factors = []

    if not structure:
        print("Insufficient data for bias calculation")
        return None

    current_price = structure["current_price"]
    range_position = structure["range_position"]
    prev_day_low = structure.get("prev_day_low")
    prev_day_high = structure.get("prev_day_high")

    # Factor 1: Range position - ICT REVERSAL logic (20 points max)
    # LOW range = expect bounce (BULLISH), HIGH range = expect reversion (BEARISH)
    if range_position > 65:
        bias_score -= 15  # CHANGED: High in range = bearish (reversion expected)
        confidence += 15
        factors.append(f"Price in upper 35% of range (-15) - Expect reversion")
    elif range_position < 35:
        bias_score += 15  # CHANGED: Low in range = bullish (bounce expected)
        confidence += 15
        factors.append(f"Price in lower 35% of range (+15) - Expect bounce")

    # Factor 1.5: Previous day structure (20 points max)
    if prev_day_low and prev_day_high:
        if current_price > prev_day_high:
            bias_score += 20
            confidence += 20
            factors.append(f"Price ABOVE previous day high (+20) - Bullish breakout")
        elif current_price < prev_day_low:
            bias_score -= 20
            confidence += 20
            factors.append(f"Price BELOW previous day low (-20) - Bearish breakdown")
        elif current_price > (prev_day_low + (prev_day_high - prev_day_low) * 0.7):
            bias_score += 10
            confidence += 10
            factors.append(f"Price in upper 30% of previous day range (+10)")
        elif current_price < (prev_day_low + (prev_day_high - prev_day_low) * 0.3):
            bias_score -= 10
            confidence += 10
            factors.append(f"Price in lower 30% of previous day range (-10)")

    # Factor 2: Absorption analysis (25 points max)
    bullish_absorption = sum(
        1
        for a in absorption_zones
        if a["side"] in ("BUY", "BID") and a["price"] < current_price
    )
    bearish_absorption = sum(
        1
        for a in absorption_zones
        if a["side"] in ("SELL", "ASK") and a["price"] > current_price
    )

    absorption_diff = bullish_absorption - bearish_absorption
    if absorption_diff > 3:
        bias_score += 20
        confidence += 20
        factors.append(
            f"Strong bullish absorption below ({bullish_absorption} zones) (+20)"
        )
    elif absorption_diff < -3:
        # Context-aware: At low range, absorption above = stop hunt targets (reduce bearish weight)
        if range_position < 35:
            bias_score -= 10  # REDUCED: Stop hunt setup, not distribution
            confidence += 20
            factors.append(
                f"Bearish absorption above at LOW range ({bearish_absorption} zones) (-10) - Stop hunt targets"
            )
        else:
            bias_score -= 20  # FULL: Mid/high range = distribution
            confidence += 20
            factors.append(
                f"Strong bearish absorption above ({bearish_absorption} zones) (-20)"
            )
    elif absorption_diff > 0:
        bias_score += 10
        confidence += 10
        factors.append(f"Moderate bullish absorption (+10)")
    elif absorption_diff < 0:
        bias_score -= 10
        confidence += 10
        factors.append(f"Moderate bearish absorption (-10)")

    # Factor 3: Iceberg positioning (20 points max)
    buy_icebergs_below = sum(
        1
        for i in iceberg_positions
        if i["side"] == "BUY" and i["price"] < current_price
    )
    sell_icebergs_above = sum(
        1
        for i in iceberg_positions
        if i["side"] == "SELL" and i["price"] > current_price
    )

    if buy_icebergs_below > sell_icebergs_above + 2:
        bias_score += 15
        confidence += 15
        factors.append(f"Buy icebergs supporting below ({buy_icebergs_below}) (+15)")
    elif sell_icebergs_above > buy_icebergs_below + 2:
        bias_score -= 15
        confidence += 15
        factors.append(f"Sell icebergs capping above ({sell_icebergs_above}) (-15)")

    # Factor 4: VWAP Analysis - CONTEXT-AWARE (30 points max)
    if vwap_analysis:
        if vwap_analysis["daily_bias"] == "BULLISH":
            bias_score += 25
            confidence += 20
            factors.append(
                f"Price above Daily VWAP (+25) - Institutional bullish intent"
            )
        elif vwap_analysis["daily_bias"] == "BEARISH":
            # CHANGED: Reduce bearish weight if at low range (accumulation zone)
            if range_position < 35:
                bias_score -= 10  # Reduced from -25 (accumulation, not distribution)
                confidence += 10
                factors.append(
                    "Price below VWAP at LOW range (-10) - Potential accumulation zone"
                )
            else:
                bias_score -= 25
                confidence += 20
                factors.append(
                    f"Price below Daily VWAP (-25) - Institutional bearish intent"
                )

        # Add Judas swing detection
        if vwap_analysis.get("recent_crosses"):
            latest_cross = vwap_analysis["recent_crosses"][0]
            if latest_cross["type"] == "BULLISH_CROSS":
                bias_score += 5
                factors.append(
                    f"Recent bullish VWAP cross (+5) - Judas swing completion"
                )
            elif latest_cross["type"] == "BEARISH_CROSS":
                bias_score -= 5
                factors.append(
                    f"Recent bearish VWAP cross (-5) - Judas swing completion"
                )

    # Factor 5: Stop cluster vulnerability (15 points max)
    buy_stops_below = sum(
        1 for s in stop_zones if s["side"] == "SELL" and s["price"] < current_price
    )
    sell_stops_above = sum(
        1 for s in stop_zones if s["side"] == "BUY" and s["price"] > current_price
    )

    if sell_stops_above > buy_stops_below + 1:
        bias_score += 10
        confidence += 10
        factors.append(
            f"Sell stops above vulnerable to hunt ({sell_stops_above} zones) (+10)"
        )
    elif buy_stops_below > sell_stops_above + 1:
        bias_score -= 10
        confidence += 10
        factors.append(
            f"Buy stops below vulnerable to hunt ({buy_stops_below} zones) (-10)"
        )

    # Factor 6: ICT Kill Zone weighting (up to 2x multiplier)
    if kill_zone:
        zone_name, multiplier, description = kill_zone
        if multiplier > 1.0:
            # Amplify bias during high-probability zones
            bias_adjustment = (bias_score - 50) * (multiplier - 1.0)
            bias_score += bias_adjustment
            confidence += int(multiplier * 10)
            factors.append(
                f"Kill Zone: {zone_name} ({multiplier}x multiplier) - {description}"
            )
        elif multiplier < 1.0:
            # Reduce bias during low-probability zones
            bias_adjustment = (bias_score - 50) * (1.0 - multiplier)
            bias_score -= bias_adjustment
            factors.append(
                f"Kill Zone: {zone_name} ({multiplier}x) - Low probability time"
            )

    # Factor 7: Fair Value Gaps - CONTEXT-AWARE (20 points max)
    if fvgs:
        bullish_fvgs = [
            f for f in fvgs if f["type"] == "BULLISH_FVG" and f["age_minutes"] < 120
        ]
        bearish_fvgs = [
            f for f in fvgs if f["type"] == "BEARISH_FVG" and f["age_minutes"] < 120
        ]

        if bullish_fvgs and len(bullish_fvgs) > len(bearish_fvgs):
            bias_score += 15
            confidence += 15
            largest_fvg = max(bullish_fvgs, key=lambda x: x["gap_size"])
            factors.append(
                f"Unfilled Bullish FVG at ${largest_fvg['gap_low']:.2f}-${largest_fvg['gap_high']:.2f} (+15)"
            )
        elif bearish_fvgs and len(bearish_fvgs) > len(bullish_fvgs):
            # Context-aware: At low range, bearish FVG above = liquidity target (reduce bearish weight)
            if range_position < 35:
                bias_score -= 5  # REDUCED: FVG above = target to fill (bullish draw)
                confidence += 10
                largest_fvg = max(bearish_fvgs, key=lambda x: x["gap_size"])
                factors.append(
                    f"Bearish FVG above at LOW range ${largest_fvg['gap_low']:.2f}-${largest_fvg['gap_high']:.2f} (-5) - Liquidity target"
                )
            else:
                bias_score -= 15  # FULL: Mid/high range = bearish imbalance
                confidence += 15
                largest_fvg = max(bearish_fvgs, key=lambda x: x["gap_size"])
                factors.append(
                    f"Unfilled Bearish FVG at ${largest_fvg['gap_low']:.2f}-${largest_fvg['gap_high']:.2f} (-15)"
                )

    # Factor 8: Market Structure Shift - CONTEXT-AWARE (25 points max)
    if mss_events:
        latest_mss = mss_events[0]
        if latest_mss["type"] == "BULLISH_MSS":
            bias_score += 25
            confidence += 20
            factors.append(
                f"Recent Bullish MSS at ${latest_mss['price']:.2f} (+25) - Upside break of structure"
            )
        elif latest_mss["type"] == "BEARISH_MSS":
            # CHANGED: Reduce bearish MSS weight at low range (likely stop hunt before reversal)
            if range_position < 35:
                bias_score -= 15  # Reduced from -25 (potential liquidity grab)
                confidence += 10
                factors.append(
                    f"Bearish MSS at LOW range ${latest_mss['price']:.2f} (-15) - Potential stop hunt"
                )
            else:
                bias_score -= 25
                confidence += 20
                factors.append(
                    f"Recent Bearish MSS at ${latest_mss['price']:.2f} (-25) - Downside break of structure"
                )

    # Factor 9: Power of Three Phase (confidence modifier)
    if po3_phase:
        phase_name, phase_confidence, phase_desc = po3_phase
        if phase_name == "MANIPULATION":
            # Fade the current move during manipulation
            bias_score = 100 - bias_score  # Invert bias
            factors.append(f"P03 Phase: {phase_name} - FADE THE MOVE ({phase_desc})")
        elif phase_name == "DISTRIBUTION":
            # High confidence in directional move
            confidence = min(confidence + 20, 100)
            factors.append(f"P03 Phase: {phase_name} - Follow trend ({phase_desc})")
        elif phase_name == "ACCUMULATION":
            # Reduce confidence, wait for manipulation
            confidence = max(confidence - 20, 20)
            factors.append(f"P03 Phase: {phase_name} - Wait for setup ({phase_desc})")
        elif phase_name == "EXPANSION":
            # Expect retracement
            factors.append(f"P03 Phase: {phase_name} - Expect pullback ({phase_desc})")

    # Factor 10: IPDA Range Position (10 points max)
    if ipda_ranges and "20day" in ipda_ranges:
        ipda_20 = ipda_ranges["20day"]
        range_position = ((current_price - ipda_20["low"]) / ipda_20["size"]) * 100

        if range_position > 70:
            bias_score -= 10
            factors.append(
                f"IPDA 20D: Price in upper range ({range_position:.0f}%) - Expect reversion (-10)"
            )
        elif range_position < 30:
            bias_score += 10
            factors.append(
                f"IPDA 20D: Price in lower range ({range_position:.0f}%) - Expect bounce (+10)"
            )

    # Normalize confidence (max 100)
    confidence = min(confidence, 100)

    # Determine bias category
    if bias_score >= 70:
        bias_category = "STRONG_BULLISH"
    elif bias_score >= 55:
        bias_category = "BULLISH"
    elif bias_score >= 45:
        bias_category = "NEUTRAL"
    elif bias_score >= 30:
        bias_category = "BEARISH"
    else:
        bias_category = "STRONG_BEARISH"

    print(f"\nBias Score: {bias_score}/100")
    print(f"Confidence: {confidence}%")
    print(f"Category: {bias_category}")
    print(f"\nFactors contributing to bias:")
    for factor in factors:
        print(f"  • {factor}")

    return {
        "bias_score": bias_score,
        "confidence_score": confidence,
        "bias_category": bias_category,
        "factors": factors,
    }


def identify_key_levels(
    structure, absorption_zones, iceberg_positions, stop_zones, volume_nodes
):
    """Identify key support and resistance levels"""
    print("\n" + "=" * 80)
    print("KEY LEVELS IDENTIFICATION")
    print("=" * 80)

    if not structure:
        return None

    current_price = structure["current_price"]

    # Support levels
    support_candidates = []

    # Overnight low
    support_candidates.append(
        {"price": structure["overnight_low"], "type": "Overnight Low", "strength": 80}
    )

    # Buy-side absorption below current
    for zone in absorption_zones:
        if zone["side"] in ("BUY", "BID") and zone["price"] < current_price:
            support_candidates.append(
                {
                    "price": zone["price"],
                    "type": "Absorption Support",
                    "strength": int(zone["significance"] * 100),
                }
            )

    # Buy icebergs below
    for iceberg in iceberg_positions:
        if iceberg["side"] == "BUY" and iceberg["price"] < current_price:
            # Use size-based strength (20-100+ contracts mapped to 60-90 strength)
            size_strength = min(60 + int(iceberg["avg_size"] / 5), 90)
            support_candidates.append(
                {
                    "price": iceberg["price"],
                    "type": "Iceberg Support",
                    "strength": size_strength,
                }
            )

    # High volume nodes below
    for node in volume_nodes[:5]:
        if node["price"] < current_price:
            support_candidates.append(
                {"price": node["price"], "type": "Volume Node", "strength": 60}
            )

    # Sort and deduplicate supports
    support_candidates.sort(key=lambda x: (x["price"], -x["strength"]), reverse=True)
    supports = []
    seen_prices = set()
    for s in support_candidates:
        price_rounded = round(s["price"], -1)
        if price_rounded not in seen_prices:
            supports.append(s)
            seen_prices.add(price_rounded)

    supports = supports[:5]

    # Resistance levels
    resistance_candidates = []

    # Overnight high
    resistance_candidates.append(
        {"price": structure["overnight_high"], "type": "Overnight High", "strength": 80}
    )

    # Sell-side absorption above current
    for zone in absorption_zones:
        if zone["side"] in ("SELL", "ASK") and zone["price"] > current_price:
            resistance_candidates.append(
                {
                    "price": zone["price"],
                    "type": "Absorption Resistance",
                    "strength": int(zone["significance"] * 100),
                }
            )

    # Sell icebergs above
    for iceberg in iceberg_positions:
        if iceberg["side"] == "SELL" and iceberg["price"] > current_price:
            # Use size-based strength (20-100+ contracts mapped to 60-90 strength)
            size_strength = min(60 + int(iceberg["avg_size"] / 5), 90)
            resistance_candidates.append(
                {
                    "price": iceberg["price"],
                    "type": "Iceberg Resistance",
                    "strength": size_strength,
                }
            )

    # High volume nodes above
    for node in volume_nodes[:5]:
        if node["price"] > current_price:
            resistance_candidates.append(
                {"price": node["price"], "type": "Volume Node", "strength": 60}
            )

    # Sort and deduplicate resistances
    resistance_candidates.sort(key=lambda x: (x["price"], -x["strength"]))
    resistances = []
    seen_prices = set()
    for r in resistance_candidates:
        price_rounded = round(r["price"], -1)
        if price_rounded not in seen_prices:
            resistances.append(r)
            seen_prices.add(price_rounded)

    resistances = resistances[:5]

    print(f"\nSupport Levels (below ${current_price:,.2f}):")
    for s in supports:
        print(f"  ${s['price']:,.2f} - {s['type']} (Strength: {s['strength']}%)")

    print(f"\nResistance Levels (above ${current_price:,.2f}):")
    for r in resistances:
        print(f"  ${r['price']:,.2f} - {r['type']} (Strength: {r['strength']}%)")

    return {"support_levels": supports, "resistance_levels": resistances}


def generate_trading_plan(bias, key_levels, structure, vwap_bands=None):
    """Generate actionable trading plan with VWAP SD targets"""
    print("\n" + "=" * 80)
    print("TRADING PLAN")
    print("=" * 80)

    if not bias or not key_levels or not structure:
        print("Insufficient data for trading plan")
        return None

    current_price = structure["current_price"]
    bias_category = bias["bias_category"]

    plan = {
        "bias": bias_category,
        "confidence": bias["confidence_score"],
        "current_price": current_price,
        "recommendations": [],
    }

    if bias_category in ("STRONG_BULLISH", "BULLISH"):
        plan["primary_direction"] = "LONG"
        plan["recommendations"].append("Look for long opportunities on pullbacks")

        if key_levels["support_levels"]:
            nearest_support = key_levels["support_levels"][0]
            plan["entry_zone"] = (
                f"${nearest_support['price']:,.2f} - ${current_price:,.2f}"
            )
            plan["recommendations"].append(
                f"Entry on dip to ${nearest_support['price']:,.2f} support"
            )

        # Use VWAP Standard Deviation bands for institutional targets
        if vwap_bands:
            t1 = vwap_bands["+1sd"]
            t2 = vwap_bands["+2sd"]
            t3 = vwap_bands["+3sd"]

            ticks_t1 = (t1 - current_price) * 4
            ticks_t2 = (t2 - current_price) * 4
            ticks_t3 = (t3 - current_price) * 4

            plan["targets"] = {
                "T1": {"price": t1, "ticks": ticks_t1, "label": "+1 SD"},
                "T2": {"price": t2, "ticks": ticks_t2, "label": "+2 SD"},
                "T3": {"price": t3, "ticks": ticks_t3, "label": "+3 SD"},
            }
            plan["recommendations"].append(
                f"T1: ${t1:,.2f} ({ticks_t1:.0f} ticks) +1 SD - First target"
            )
            plan["recommendations"].append(
                f"T2: ${t2:,.2f} ({ticks_t2:.0f} ticks) +2 SD - Extended target"
            )
            plan["recommendations"].append(
                f"T3: ${t3:,.2f} ({ticks_t3:.0f} ticks) +3 SD - Extreme target"
            )
        else:
            # Fallback to resistance levels if VWAP bands not available
            if key_levels["resistance_levels"]:
                target_price = key_levels["resistance_levels"][0]["price"]
                ticks = (target_price - current_price) * 4
                plan["target"] = f"${target_price:,.2f}"
                plan["recommendations"].append(
                    f"Target: ${target_price:,.2f} ({ticks:.0f} ticks, ${target_price - current_price:,.2f})"
                )

        if key_levels["support_levels"]:
            plan["stop"] = f"Below ${key_levels['support_levels'][0]['price']:,.2f}"
            plan["recommendations"].append(
                f"Stop loss below ${key_levels['support_levels'][0]['price']:,.2f}"
            )

    elif bias_category in ("STRONG_BEARISH", "BEARISH"):
        plan["primary_direction"] = "SHORT"
        plan["recommendations"].append("Look for short opportunities on rallies")

        if key_levels["resistance_levels"]:
            nearest_resistance = key_levels["resistance_levels"][0]
            plan["entry_zone"] = (
                f"${current_price:,.2f} - ${nearest_resistance['price']:,.2f}"
            )
            plan["recommendations"].append(
                f"Entry on rally to ${nearest_resistance['price']:,.2f} resistance"
            )

        # Use VWAP Standard Deviation bands for institutional targets
        if vwap_bands:
            t1 = vwap_bands["-1sd"]
            t2 = vwap_bands["-2sd"]
            t3 = vwap_bands["-3sd"]

            ticks_t1 = (current_price - t1) * 4
            ticks_t2 = (current_price - t2) * 4
            ticks_t3 = (current_price - t3) * 4

            plan["targets"] = {
                "T1": {"price": t1, "ticks": ticks_t1, "label": "-1 SD"},
                "T2": {"price": t2, "ticks": ticks_t2, "label": "-2 SD"},
                "T3": {"price": t3, "ticks": ticks_t3, "label": "-3 SD"},
            }
            plan["recommendations"].append(
                f"T1: ${t1:,.2f} ({ticks_t1:.0f} ticks) -1 SD - First target"
            )
            plan["recommendations"].append(
                f"T2: ${t2:,.2f} ({ticks_t2:.0f} ticks) -2 SD - Extended target"
            )
            plan["recommendations"].append(
                f"T3: ${t3:,.2f} ({ticks_t3:.0f} ticks) -3 SD - Extreme target"
            )
        else:
            # Fallback to support levels if VWAP bands not available
            if key_levels["support_levels"]:
                target_price = key_levels["support_levels"][0]["price"]
                ticks = (current_price - target_price) * 4
                plan["target"] = f"${target_price:,.2f}"
                plan["recommendations"].append(
                    f"Target: ${target_price:,.2f} ({ticks:.0f} ticks, ${current_price - target_price:,.2f})"
                )

        if key_levels["resistance_levels"]:
            plan["stop"] = f"Above ${key_levels['resistance_levels'][0]['price']:,.2f}"
            plan["recommendations"].append(
                f"Stop loss above ${key_levels['resistance_levels'][0]['price']:,.2f}"
            )

    else:  # NEUTRAL
        plan["primary_direction"] = "RANGE"
        plan["recommendations"].append("Range-bound market - trade both directions")
        plan["recommendations"].append(
            f"Sell resistance around ${key_levels['resistance_levels'][0]['price']:,.2f}"
        )
        plan["recommendations"].append(
            f"Buy support around ${key_levels['support_levels'][0]['price']:,.2f}"
        )
        plan["recommendations"].append("Use tight stops in both directions")

    print(f"\nPrimary Direction: {plan['primary_direction']}")
    print(f"Confidence: {plan['confidence']}%")
    print(f"\nRecommendations:")
    for rec in plan["recommendations"]:
        print(f"  • {rec}")

    return plan


def main():
    """Main execution"""
    print("\n" + "=" * 80)
    print("MNQ TRADING BIAS REPORT")
    print("=" * 80)

    # Get time range
    start_time, end_time = get_time_range()
    print(f"\nAnalysis Period:")
    print(f"  Start: {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"  End:   {end_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    # Connect to database
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        # Get ICT Kill Zone and Power of Three phase
        kill_zone = get_ict_kill_zone()
        po3_phase = get_power_of_three_phase(cursor, start_time, end_time)

        print("\n" + "=" * 80)
        print(f"ICT KILL ZONE: {kill_zone[0]} ({kill_zone[1]}x)")
        print(f"  {kill_zone[2]}")
        print(f"\nPOWER OF THREE PHASE: {po3_phase[0]} ({po3_phase[1]}% confidence)")
        print(f"  {po3_phase[2]}")
        print("=" * 80)

        # Run all analyses
        structure = analyze_overnight_structure(cursor, start_time, end_time)
        volume_nodes = analyze_volume_profile(cursor, start_time, end_time)
        absorption_zones = analyze_absorption(cursor, start_time, end_time)
        iceberg_positions = analyze_icebergs(cursor, start_time, end_time)
        stop_zones = analyze_stop_clusters(cursor, start_time, end_time)

        # NEW ICT Analysis
        fvgs = detect_fair_value_gaps(cursor, start_time, end_time)
        mss_events = detect_market_structure_shift(cursor, start_time, end_time)
        ipda_ranges = calculate_ipda_ranges(cursor, end_time)

        # VWAP with Standard Deviation bands
        vwap_analysis = analyze_vwap(cursor, start_time, end_time)
        vwap_bands = None
        if vwap_analysis and "vwap_daily" in vwap_analysis:
            vwap_bands = calculate_vwap_standard_deviations(
                cursor, end_time, vwap_analysis["vwap_daily"]
            )
            print("\n" + "=" * 80)
            print("VWAP STANDARD DEVIATION BANDS")
            print("=" * 80)
            print(f"\nVWAP: ${vwap_bands['vwap']:,.2f}")
            print(f"  +1 SD: ${vwap_bands['+1sd']:,.2f} (First target)")
            print(f"  +2 SD: ${vwap_bands['+2sd']:,.2f} (Extended target)")
            print(f"  +3 SD: ${vwap_bands['+3sd']:,.2f} (Extreme target)")
            print(f"  -1 SD: ${vwap_bands['-1sd']:,.2f} (First target)")
            print(f"  -2 SD: ${vwap_bands['-2sd']:,.2f} (Extended target)")
            print(f"  -3 SD: ${vwap_bands['-3sd']:,.2f} (Extreme target)")

        # Calculate bias with all ICT factors
        bias = calculate_bias(
            structure,
            absorption_zones,
            iceberg_positions,
            stop_zones,
            vwap_analysis,
            fvgs,
            mss_events,
            ipda_ranges,
            po3_phase,
            kill_zone,
        )

        # Identify key levels
        key_levels = identify_key_levels(
            structure, absorption_zones, iceberg_positions, stop_zones, volume_nodes
        )

        # Generate trading plan with VWAP SD targets
        trading_plan = generate_trading_plan(bias, key_levels, structure, vwap_bands)

        # Generate final report
        report = {
            "timestamp": end_time.isoformat(),
            "analysis_period": {
                "start": start_time.isoformat(),
                "end": end_time.isoformat(),
                "nine_thirty_cutoff": get_nine_thirty_cutoff().isoformat(),
            },
            "ict_context": {
                "kill_zone": {
                    "name": kill_zone[0],
                    "multiplier": kill_zone[1],
                    "description": kill_zone[2],
                },
                "power_of_three_phase": {
                    "phase": po3_phase[0],
                    "confidence": po3_phase[1],
                    "description": po3_phase[2],
                },
            },
            "overnight_structure": structure,
            "vwap_analysis": vwap_analysis,
            "vwap_bands": vwap_bands,
            "volume_profile": volume_nodes[:5],
            "absorption_zones": absorption_zones[:10],
            "iceberg_positions": iceberg_positions[:5],
            "stop_clusters": stop_zones[:5],
            "fair_value_gaps": fvgs,
            "market_structure_shifts": mss_events,
            "ipda_ranges": ipda_ranges,
            "bias_assessment": bias,
            "key_levels": key_levels,
            "trading_plan": trading_plan,
        }

        # Save report
        report_file = f"outputs/bias_report_{end_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)

        print("\n" + "=" * 80)
        print(f"Report saved to: {report_file}")
        print("=" * 80 + "\n")

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    main()
