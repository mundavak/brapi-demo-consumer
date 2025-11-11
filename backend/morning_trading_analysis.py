"""
Morning Trading Analysis Script
================================
Combines institutional order flow analysis to provide daily trading signals.

Analyzes:
- MBO Data (Market By Order) - Large institutional orders (size > 15)
- Absorption Events - Aggressive buying/selling
- Icebergs & Stops - Hidden institutional orders

Outputs:
- Overall market bias (BULLISH/BEARISH/NEUTRAL)
- Key support/resistance levels
- Reentry zones for pullbacks
- Price targets
- Trading recommendations

Usage:
    python morning_trading_analysis.py [current_price]

Example:
    python morning_trading_analysis.py 25619
    python morning_trading_analysis.py  # Will prompt for price
"""

import psycopg2
import sys
from datetime import datetime, timedelta
import pytz
from collections import defaultdict

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}

# Analysis parameters
LOOKBACK_HOURS = 1  # Analyze last N hours
MBO_SIZE_FILTER = 15  # Minimum order size for institutional detection
HIGH_SIGNIFICANCE_THRESHOLD = 0.7  # For absorption events

# Scoring weights
WEIGHTS = {
    "mbo": 0.4,  # 40% weight
    "absorption": 0.4,  # 40% weight
    "icebergs": 0.2,  # 20% weight
}


def get_current_price():
    """Get current price from user input or command line argument."""
    if len(sys.argv) > 1:
        try:
            return float(sys.argv[1])
        except ValueError:
            print(f"Invalid price: {sys.argv[1]}")
            sys.exit(1)

    while True:
        try:
            price_input = input("\nEnter current price: ")
            return float(price_input)
        except ValueError:
            print("Invalid input. Please enter a number.")


def connect_database():
    """Connect to TimescaleDB."""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)


def fetch_mbo_data(cursor, lookback_time):
    """Fetch MBO data for institutional order flow analysis."""
    query = """
    SELECT timestamp, price, size, side, action
    FROM mbo_data
    WHERE timestamp >= %s 
      AND size > %s
      AND action IN ('ADD', 'DELETE', 'MODIFY')
    ORDER BY timestamp;
    """
    cursor.execute(query, (lookback_time, MBO_SIZE_FILTER))
    return cursor.fetchall()


def fetch_absorption_data(cursor, lookback_time):
    """Fetch absorption events showing aggressive institutional buying/selling."""
    query = """
    SELECT timestamp, price, side, absorbed_volume, aggressor_volume, significance_score
    FROM absorption_events
    WHERE timestamp >= %s
    ORDER BY timestamp;
    """
    cursor.execute(query, (lookback_time,))
    return cursor.fetchall()


def fetch_iceberg_data(cursor, lookback_time):
    """Fetch iceberg and stop cluster detections."""
    query = """
    SELECT timestamp, price, side, detected_size, confidence_score, event_type
    FROM stops_icebergs
    WHERE timestamp >= %s
    ORDER BY timestamp;
    """
    cursor.execute(query, (lookback_time,))
    return cursor.fetchall()


def analyze_mbo_bias(mbo_data):
    """Calculate bias from MBO order flow."""
    buy_volume = sum(r[2] for r in mbo_data if r[3] == "BUY" and r[4] == "ADD")
    sell_volume = sum(r[2] for r in mbo_data if r[3] == "SELL" and r[4] == "ADD")
    cancel_volume = sum(r[2] for r in mbo_data if r[4] == "DELETE")

    delta = buy_volume - sell_volume
    total = buy_volume + sell_volume

    return {
        "buy_volume": buy_volume,
        "sell_volume": sell_volume,
        "cancel_volume": cancel_volume,
        "delta": delta,
        "total": total,
        "score": delta * WEIGHTS["mbo"],
    }


def analyze_absorption_bias(absorption_data):
    """Calculate bias from absorption events."""
    buy_absorption = sum(r[3] for r in absorption_data if r[2] == "BUY")
    sell_absorption = sum(r[3] for r in absorption_data if r[2] == "SELL")
    high_sig_buys = sum(
        1
        for r in absorption_data
        if r[2] == "BUY" and r[5] and r[5] > HIGH_SIGNIFICANCE_THRESHOLD
    )
    high_sig_sells = sum(
        1
        for r in absorption_data
        if r[2] == "SELL" and r[5] and r[5] > HIGH_SIGNIFICANCE_THRESHOLD
    )

    delta = buy_absorption - sell_absorption

    return {
        "buy_volume": buy_absorption,
        "sell_volume": sell_absorption,
        "delta": delta,
        "high_sig_buys": high_sig_buys,
        "high_sig_sells": high_sig_sells,
        "score": delta * WEIGHTS["absorption"],
    }


def analyze_iceberg_bias(iceberg_data):
    """Calculate bias from iceberg detections."""
    buy_icebergs = [r for r in iceberg_data if r[2] == "BUY"]
    sell_icebergs = [r for r in iceberg_data if r[2] == "SELL"]

    buy_count = len(buy_icebergs)
    sell_count = len(sell_icebergs)
    delta = buy_count - sell_count

    return {
        "buy_count": buy_count,
        "sell_count": sell_count,
        "delta": delta,
        "score": delta * WEIGHTS["icebergs"] * 100,
    }


def calculate_unified_bias(mbo_analysis, absorption_analysis, iceberg_analysis):
    """Calculate overall market bias from all data sources."""
    total_score = (
        mbo_analysis["score"] + absorption_analysis["score"] + iceberg_analysis["score"]
    )

    # Normalize to -100 to +100 scale
    normalized_score = max(-100, min(100, total_score / 100))

    if normalized_score > 50:
        bias = "STRONGLY BULLISH"
    elif normalized_score > 20:
        bias = "BULLISH"
    elif normalized_score > -20:
        bias = "NEUTRAL"
    elif normalized_score > -50:
        bias = "BEARISH"
    else:
        bias = "STRONGLY BEARISH"

    return {"score": total_score, "normalized": normalized_score, "bias": bias}


def find_support_resistance_levels(
    mbo_data, absorption_data, iceberg_data, current_price
):
    """Find key support and resistance levels with institutional presence."""

    # Support levels (below current price)
    support_levels = defaultdict(
        lambda: {"mbo_volume": 0, "absorption": 0, "icebergs": 0, "score": 0}
    )

    # Resistance levels (above current price)
    resistance_levels = defaultdict(
        lambda: {"mbo_volume": 0, "absorption": 0, "icebergs": 0, "score": 0}
    )

    # Process MBO data
    for r in mbo_data:
        price = round(r[1], 2)
        volume = r[2]
        side = r[3]
        action = r[4]

        if action == "ADD":
            if side == "BUY" and price <= current_price:
                support_levels[price]["mbo_volume"] += volume
                support_levels[price]["score"] += volume / 5
            elif side == "SELL" and price >= current_price:
                resistance_levels[price]["mbo_volume"] += volume
                resistance_levels[price]["score"] += volume / 5

    # Process absorption
    for r in absorption_data:
        price = round(r[1], 2)
        side = r[2]
        volume = r[3]

        if side == "BUY" and price <= current_price:
            support_levels[price]["absorption"] += volume
            support_levels[price]["score"] += volume / 3
        elif side == "SELL" and price >= current_price:
            resistance_levels[price]["absorption"] += volume
            resistance_levels[price]["score"] += volume / 3

    # Process icebergs
    for r in iceberg_data:
        price = round(r[1], 2)
        side = r[2]
        size = r[3]

        if side == "BUY" and price <= current_price:
            support_levels[price]["icebergs"] += size
            support_levels[price]["score"] += 100
        elif side == "SELL" and price >= current_price:
            resistance_levels[price]["icebergs"] += size
            resistance_levels[price]["score"] += 100

    # Sort by score
    sorted_support = sorted(
        support_levels.items(), key=lambda x: x[1]["score"], reverse=True
    )[:10]
    sorted_resistance = sorted(
        resistance_levels.items(), key=lambda x: x[1]["score"], reverse=True
    )[:10]

    return sorted_support, sorted_resistance


def print_header(current_price):
    """Print analysis header."""
    now = datetime.now(pytz.timezone("US/Eastern"))
    print(f"\n{'='*110}")
    print(f"📊 MORNING TRADING ANALYSIS - {now.strftime('%B %d, %Y %I:%M %p ET')}")
    print(f"{'='*110}")
    print(f"Current Price: {current_price:.2f}")
    print(f"Analysis Period: Last {LOOKBACK_HOURS} hour(s)")
    print(f"{'='*110}\n")


def print_data_summary(mbo_count, absorption_count, iceberg_count):
    """Print data availability summary."""
    print("📈 DATA SUMMARY")
    print(f"{'─'*110}")
    print(f"  MBO Orders (size > {MBO_SIZE_FILTER}):  {mbo_count:5d} orders")
    print(f"  Absorption Events:       {absorption_count:5d} events")
    print(f"  Icebergs/Stops:          {iceberg_count:5d} detected")
    print(f"{'─'*110}\n")


def print_bias_analysis(
    mbo_analysis, absorption_analysis, iceberg_analysis, unified_bias
):
    """Print detailed bias analysis."""
    print("🎯 INSTITUTIONAL BIAS ANALYSIS")
    print(f"{'─'*110}")

    # MBO
    print(f"\n1. MBO Order Flow (Weight: {WEIGHTS['mbo']*100:.0f}%)")
    print(f"   Buy Volume:   {mbo_analysis['buy_volume']:8.0f} contracts")
    print(f"   Sell Volume:  {mbo_analysis['sell_volume']:8.0f} contracts")
    print(f"   Delta:        {mbo_analysis['delta']:+8.0f} contracts")
    print(f"   Score:        {mbo_analysis['score']:+8.1f}")

    # Absorption
    print(f"\n2. Absorption Analysis (Weight: {WEIGHTS['absorption']*100:.0f}%)")
    print(f"   Buy Absorption:   {absorption_analysis['buy_volume']:8.0f} volume")
    print(f"   Sell Absorption:  {absorption_analysis['sell_volume']:8.0f} volume")
    print(f"   Delta:            {absorption_analysis['delta']:+8.0f} volume")
    print(f"   High-Sig Buys:    {absorption_analysis['high_sig_buys']:8d} events")
    print(f"   High-Sig Sells:   {absorption_analysis['high_sig_sells']:8d} events")
    print(f"   Score:            {absorption_analysis['score']:+8.1f}")

    # Icebergs
    print(f"\n3. Icebergs & Stops (Weight: {WEIGHTS['icebergs']*100:.0f}%)")
    print(f"   Buy Icebergs:   {iceberg_analysis['buy_count']:5d} detected")
    print(f"   Sell Icebergs:  {iceberg_analysis['sell_count']:5d} detected")
    print(f"   Delta:          {iceberg_analysis['delta']:+5d}")
    print(f"   Score:          {iceberg_analysis['score']:+8.1f}")

    # Unified
    print(f"\n{'─'*110}")
    print(f"🎯 UNIFIED INSTITUTIONAL BIAS: {unified_bias['bias']}")
    print(f"   Total Score:      {unified_bias['score']:+8.1f}")
    print(f"   Normalized:       {unified_bias['normalized']:+8.1f}/100")
    print(f"{'─'*110}\n")


def print_support_resistance(support_levels, resistance_levels, current_price):
    """Print support and resistance levels."""
    print("🟢 KEY SUPPORT LEVELS (Below Current Price)")
    print(f"{'─'*110}")
    print(
        f"{'Price':<10} {'Distance':<12} {'MBO Vol':<12} {'Absorption':<12} {'Icebergs':<10} {'Score':<10}"
    )
    print(f"{'─'*110}")

    for price, data in support_levels[:5]:
        distance = current_price - price
        print(
            f"{price:<10.2f} -{distance:>6.2f} pts   {data['mbo_volume']:<12.0f} {data['absorption']:<12.0f} {data['icebergs']:<10.0f} {data['score']:<10.0f}"
        )

    print(f"\n🔴 KEY RESISTANCE LEVELS (Above Current Price)")
    print(f"{'─'*110}")
    print(
        f"{'Price':<10} {'Distance':<12} {'MBO Vol':<12} {'Absorption':<12} {'Icebergs':<10} {'Score':<10}"
    )
    print(f"{'─'*110}")

    if resistance_levels:
        for price, data in resistance_levels[:5]:
            distance = price - current_price
            print(
                f"{price:<10.2f} +{distance:>6.2f} pts   {data['mbo_volume']:<12.0f} {data['absorption']:<12.0f} {data['icebergs']:<10.0f} {data['score']:<10.0f}"
            )
    else:
        print(
            "   ⚠️  No significant resistance detected - Path of least resistance is UP!"
        )

    print(f"{'─'*110}\n")


def print_trading_recommendations(
    unified_bias, support_levels, resistance_levels, current_price
):
    """Print actionable trading recommendations."""
    print(f"{'='*110}")
    print("💡 TRADING RECOMMENDATIONS")
    print(f"{'='*110}\n")

    bias = unified_bias["bias"]

    if "BULLISH" in bias:
        print(f"📈 BULLISH SETUP DETECTED")
        print(f"   Market Bias: {bias} ({unified_bias['normalized']:+.1f}/100)")

        if support_levels:
            top_support = support_levels[0]
            print(f"\n🎯 KEY LEVELS:")
            print(
                f"   Primary Support:  {top_support[0]:.2f} (Score: {top_support[1]['score']:.0f})"
            )

            if len(support_levels) >= 2:
                second_support = support_levels[1]
                print(
                    f"   Secondary Support: {second_support[0]:.2f} (Score: {second_support[1]['score']:.0f})"
                )

        if resistance_levels:
            top_resistance = resistance_levels[0]
            print(
                f"   First Resistance: {top_resistance[0]:.2f} (Score: {top_resistance[1]['score']:.0f})"
            )
        else:
            print(f"   First Resistance: MINIMAL - Price may run freely")

        print(f"\n📋 STRATEGY:")
        if support_levels:
            print(
                f"   • LONG on pullbacks to support zones: {support_levels[0][0]:.2f}"
            )
            if len(support_levels) >= 2:
                print(f"   • Alternative entry: {support_levels[1][0]:.2f}")
        print(f"   • Watch for bullish price action (rejection wicks, volume spikes)")
        print(f"   • Set stops below support levels")
        if resistance_levels:
            print(f"   • Take profits at resistance: {resistance_levels[0][0]:.2f}")
            print(f"   • Trail stops as price moves higher")
        else:
            print(f"   • Use trailing stops (minimal resistance above)")

    elif "BEARISH" in bias:
        print(f"📉 BEARISH SETUP DETECTED")
        print(f"   Market Bias: {bias} ({unified_bias['normalized']:+.1f}/100)")

        if resistance_levels:
            top_resistance = resistance_levels[0]
            print(f"\n🎯 KEY LEVELS:")
            print(
                f"   Primary Resistance: {top_resistance[0]:.2f} (Score: {top_resistance[1]['score']:.0f})"
            )

            if len(resistance_levels) >= 2:
                second_resistance = resistance_levels[1]
                print(
                    f"   Secondary Resistance: {second_resistance[0]:.2f} (Score: {second_resistance[1]['score']:.0f})"
                )

        if support_levels:
            top_support = support_levels[0]
            print(
                f"   First Support: {top_support[0]:.2f} (Score: {top_support[1]['score']:.0f})"
            )

        print(f"\n📋 STRATEGY:")
        if resistance_levels:
            print(
                f"   • SHORT on rallies to resistance zones: {resistance_levels[0][0]:.2f}"
            )
            if len(resistance_levels) >= 2:
                print(f"   • Alternative entry: {resistance_levels[1][0]:.2f}")
        print(f"   • Watch for bearish price action (rejection wicks, volume spikes)")
        print(f"   • Set stops above resistance levels")
        if support_levels:
            print(f"   • Take profits at support: {support_levels[0][0]:.2f}")

    else:  # NEUTRAL
        print(f"⚖️  NEUTRAL BIAS")
        print(f"   Market Bias: {bias} ({unified_bias['normalized']:+.1f}/100)")
        print(f"\n📋 STRATEGY:")
        print(f"   • Range-bound trading likely")
        if support_levels and resistance_levels:
            print(f"   • Buy near support: {support_levels[0][0]:.2f}")
            print(f"   • Sell near resistance: {resistance_levels[0][0]:.2f}")
        print(f"   • Wait for clearer directional bias to develop")
        print(f"   • Reduce position sizes in choppy conditions")

    print(f"\n{'='*110}\n")


def main():
    """Main analysis routine."""
    # Get current price
    current_price = get_current_price()

    # Print header
    print_header(current_price)

    # Connect to database
    conn = connect_database()
    cursor = conn.cursor()

    # Calculate lookback time
    lookback_time = datetime.now(pytz.UTC) - timedelta(hours=LOOKBACK_HOURS)

    # Fetch data
    print("⏳ Fetching market data...")
    mbo_data = fetch_mbo_data(cursor, lookback_time)
    absorption_data = fetch_absorption_data(cursor, lookback_time)
    iceberg_data = fetch_iceberg_data(cursor, lookback_time)

    # Print data summary
    print_data_summary(len(mbo_data), len(absorption_data), len(iceberg_data))

    # Analyze bias
    mbo_analysis = analyze_mbo_bias(mbo_data)
    absorption_analysis = analyze_absorption_bias(absorption_data)
    iceberg_analysis = analyze_iceberg_bias(iceberg_data)
    unified_bias = calculate_unified_bias(
        mbo_analysis, absorption_analysis, iceberg_analysis
    )

    # Print bias analysis
    print_bias_analysis(
        mbo_analysis, absorption_analysis, iceberg_analysis, unified_bias
    )

    # Find support/resistance
    support_levels, resistance_levels = find_support_resistance_levels(
        mbo_data, absorption_data, iceberg_data, current_price
    )

    # Print levels
    print_support_resistance(support_levels, resistance_levels, current_price)

    # Print recommendations
    print_trading_recommendations(
        unified_bias, support_levels, resistance_levels, current_price
    )

    # Cleanup
    cursor.close()
    conn.close()

    print("✅ Analysis complete!\n")


if __name__ == "__main__":
    main()
