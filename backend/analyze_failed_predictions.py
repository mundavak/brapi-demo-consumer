#!/usr/bin/env python3
"""
Analyze failed bias predictions in detail
Shows what factors led to incorrect bearish calls
"""

import psycopg2
from datetime import datetime, timedelta
import pytz

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}

EST = pytz.timezone("America/New_York")

# Failed predictions from backtest (UPDATED after logic fixes)
# Oct 31, Nov 4, Nov 7, Nov 11, Nov 13 - NOW CORRECT (flipped to bullish)
# Nov 14, Nov 17 - STILL WRONG (need more analysis)
FAILED_DAYS = [
    # ("2025-10-31", "BULLISH", 62.5, 100, +1014.94, 4.07),  # FIXED
    # ("2025-11-04", "BULLISH", 63.5, 65, +611.06, 2.45),    # FIXED
    # ("2025-11-07", "BULLISH", 60.5, 55, +213.00, 0.85),    # FIXED
    # ("2025-11-11", "NEUTRAL", 45.0, 35, +708.25, 2.84),    # FIXED
    # ("2025-11-13", "BEARISH", 33.0, 80, +188.75, 0.76),    # IMPROVED but still wrong
    ("2025-11-14", "BEARISH", 41.0, 95, +244.50, 0.99),  # STILL WRONG
    ("2025-11-17", "BEARISH", 30.0, 100, 0.0, 0.0),  # STILL WRONG
]


def analyze_day(cursor, date_str):
    """Run detailed bias analysis for a specific day"""
    trade_date = datetime.strptime(date_str, "%Y-%m-%d").date()

    # Trading day range (8:45 PM prev day to 5:00 PM current day)
    prev_day = trade_date - timedelta(days=1)
    start_time = EST.localize(
        datetime.combine(prev_day, datetime.min.time().replace(hour=20, minute=45))
    )
    analysis_time = EST.localize(
        datetime.combine(trade_date, datetime.min.time().replace(hour=9, minute=30))
    )
    end_time = EST.localize(
        datetime.combine(trade_date, datetime.min.time().replace(hour=17, minute=0))
    )

    print("\n" + "=" * 100)
    print(f"DETAILED ANALYSIS: {date_str}")
    print("=" * 100)

    # Import analysis functions
    import sys
    from pathlib import Path

    sys.path.append(str(Path(__file__).parent))

    from generate_bias_report import (
        analyze_overnight_structure,
        analyze_absorption,
        analyze_icebergs,
        analyze_stop_clusters,
        detect_fair_value_gaps,
        detect_market_structure_shift,
        calculate_ipda_ranges,
        analyze_vwap,
        calculate_bias,
        get_ict_kill_zone,
        get_power_of_three_phase,
    )

    # Run analyses
    print("\n[1/10] Overnight Structure...")
    structure = analyze_overnight_structure(cursor, start_time, analysis_time)

    print("\n[2/10] Absorption Zones...")
    absorption_zones = analyze_absorption(cursor, start_time, analysis_time)

    print("\n[3/10] Iceberg Positions...")
    iceberg_positions = analyze_icebergs(cursor, start_time, analysis_time)

    print("\n[4/10] Stop Clusters...")
    stop_zones = analyze_stop_clusters(cursor, start_time, analysis_time)

    print("\n[5/10] Fair Value Gaps...")
    fvgs = detect_fair_value_gaps(cursor, start_time, analysis_time)

    print("\n[6/10] Market Structure Shifts...")
    mss_events = detect_market_structure_shift(cursor, start_time, analysis_time)

    print("\n[7/10] IPDA Ranges...")
    ipda_ranges = calculate_ipda_ranges(cursor, analysis_time)

    print("\n[8/10] VWAP Analysis...")
    vwap_analysis = analyze_vwap(cursor, start_time, analysis_time)

    print("\n[9/10] ICT Context...")
    kill_zone = get_ict_kill_zone()
    po3_phase = get_power_of_three_phase(cursor, start_time, analysis_time)

    print("\n[10/10] Calculating Bias...")
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

    # Show actual outcome
    cursor.execute(
        """
        SELECT MIN(low), MAX(high), 
               (SELECT close FROM ohlc_candles 
                WHERE symbol = 'MNQ' AND timeframe = '5m'
                AND timestamp >= %s AND timestamp <= %s
                ORDER BY timestamp DESC LIMIT 1)
        FROM ohlc_candles
        WHERE symbol = 'MNQ' 
        AND timeframe = '5m'
        AND timestamp >= %s 
        AND timestamp <= %s
    """,
        (analysis_time, end_time, analysis_time, end_time),
    )

    day_low, day_high, day_close = cursor.fetchone()
    start_price = structure["current_price"]
    price_change = day_close - start_price if day_close else 0

    print("\n" + "=" * 100)
    print("OUTCOME vs PREDICTION")
    print("=" * 100)
    print(
        f"\nPrediction: {bias['bias_category']} (Score: {bias['bias_score']}/100, Confidence: {bias['confidence_score']}%)"
    )
    print(f"Start Price: ${start_price:,.2f}")
    print(f"End Price:   ${day_close:,.2f}")
    print(f"Change:      ${price_change:+,.2f} ({price_change/start_price*100:+.2f}%)")
    print(f"Day Range:   ${day_low:,.2f} - ${day_high:,.2f}")

    if price_change > 50:
        print(f"\n⚠️  RESULT: BULLISH (went UP) - PREDICTION WAS WRONG")
    elif price_change < -50:
        print(f"\n✓ RESULT: BEARISH (went DOWN) - PREDICTION WAS CORRECT")
    else:
        print(f"\n○ RESULT: NEUTRAL (choppy)")

    # Key factors analysis
    print("\n" + "=" * 100)
    print("KEY FACTORS BREAKDOWN")
    print("=" * 100)

    bullish_factors = [f for f in bias["factors"] if "+" in f and not f.startswith("•")]
    bearish_factors = [f for f in bias["factors"] if "-" in f and not f.startswith("•")]

    print(f"\n📈 BULLISH FACTORS ({len(bullish_factors)}):")
    for factor in bullish_factors:
        print(f"  {factor}")

    print(f"\n📉 BEARISH FACTORS ({len(bearish_factors)}):")
    for factor in bearish_factors:
        print(f"  {factor}")

    # Count absorption zones
    bullish_absorption = len(
        [
            a
            for a in absorption_zones
            if a["side"] in ("BUY", "BID") and a["price"] < start_price
        ]
    )
    bearish_absorption = len(
        [
            a
            for a in absorption_zones
            if a["side"] in ("SELL", "ASK") and a["price"] > start_price
        ]
    )

    print(f"\n💧 ABSORPTION SUMMARY:")
    print(f"  Bullish zones below: {bullish_absorption}")
    print(f"  Bearish zones above: {bearish_absorption}")

    # FVG summary
    if fvgs:
        bullish_fvgs = len([f for f in fvgs if f["type"] == "BULLISH_FVG"])
        bearish_fvgs = len([f for f in fvgs if f["type"] == "BEARISH_FVG"])
        print(f"\n📊 FVG SUMMARY:")
        print(f"  Bullish FVGs: {bullish_fvgs}")
        print(f"  Bearish FVGs: {bearish_fvgs}")

    # MSS summary
    if mss_events:
        latest_mss = mss_events[0]
        print(f"\n🔀 LATEST MSS: {latest_mss['type']} at ${latest_mss['price']:,.2f}")

    print("\n" + "=" * 100)
    input("\nPress Enter to continue to next day...")


def main():
    """Analyze each failed prediction"""
    print("\n" + "=" * 100)
    print("FAILED BEARISH PREDICTIONS ANALYSIS")
    print("=" * 100)
    print(f"\nAnalyzing {len(FAILED_DAYS)} incorrect predictions...")
    print("Each day will show full bias calculation and outcome")

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        for i, (date, bias_cat, score, conf, change, pct) in enumerate(FAILED_DAYS, 1):
            print(
                f"\n[Day {i}/{len(FAILED_DAYS)}] {date} - Predicted {bias_cat}, Actually went UP ${change:+,.2f} ({pct:+.2f}%)"
            )
            input("Press Enter to analyze...")

            analyze_day(cursor, date)

    finally:
        cursor.close()
        conn.close()

    print("\n" + "=" * 100)
    print("ANALYSIS COMPLETE")
    print("=" * 100)


if __name__ == "__main__":
    main()
