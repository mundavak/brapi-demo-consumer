#!/usr/bin/env python3
"""
Session Analysis for Trading Bias
Analyzes previous day high/low and Asia/London session data to provide today's bias
"""

import pandas as pd
from datetime import datetime, timezone, timedelta
import pytz

# File path
CSV_FILE = "../KnowledgeBase/CME_MINI_MNQ1!, 60.csv"


def timestamp_to_et(ts):
    """Convert Unix timestamp to ET timezone"""
    return datetime.fromtimestamp(ts, tz=timezone.utc).astimezone(
        pytz.timezone("America/New_York")
    )


def analyze_sessions():
    """Analyze previous day and session highs/lows for bias"""

    print("=" * 80)
    print("SESSION ANALYSIS FOR TRADING BIAS")
    print("=" * 80)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}")
    print()

    # Load CSV
    df = pd.read_csv(CSV_FILE)
    df["datetime"] = df["time"].apply(timestamp_to_et)
    df["date"] = df["datetime"].dt.date
    df["hour"] = df["datetime"].dt.hour

    print(f"Data loaded: {len(df)} 60-minute candles")
    print(f"Date range: {df['datetime'].min()} to {df['datetime'].max()}")
    print()

    # Get unique dates
    dates = sorted(df["date"].unique())
    print(f"Available dates: {len(dates)} days")

    # Today and yesterday
    today = datetime.now(pytz.timezone("America/New_York")).date()
    yesterday = today - timedelta(days=1)

    print(f"Today: {today}")
    print(f"Yesterday: {yesterday}")
    print()

    # Find yesterday in data
    if yesterday not in dates:
        print(f"⚠️  WARNING: Yesterday ({yesterday}) not found in data!")
        print(f"Using most recent complete day: {dates[-1]}")
        yesterday = dates[-1]
        print()

    # === PREVIOUS DAY ANALYSIS ===
    print("=" * 80)
    print("PREVIOUS DAY (D1) ANALYSIS")
    print("=" * 80)

    prev_day_data = df[df["date"] == yesterday]

    if len(prev_day_data) == 0:
        print(f"No data found for {yesterday}")
        return

    d1_high = prev_day_data["high"].max()
    d1_low = prev_day_data["low"].min()
    d1_open = prev_day_data.iloc[0]["open"]
    d1_close = prev_day_data.iloc[-1]["close"]
    d1_range = d1_high - d1_low

    print(f"Date: {yesterday}")
    print(f"Open:  ${d1_open:,.2f}")
    print(f"High:  ${d1_high:,.2f}")
    print(f"Low:   ${d1_low:,.2f}")
    print(f"Close: ${d1_close:,.2f}")
    print(f"Range: {d1_range:.2f} points")
    print(
        f"Move:  {d1_close - d1_open:+.2f} points ({((d1_close - d1_open) / d1_open * 100):+.2f}%)"
    )
    print()

    # Daily bias
    if d1_close > d1_open:
        d1_bias = "BULLISH"
        print(f"D1 Bias: {d1_bias} ✓ (Close > Open)")
    else:
        d1_bias = "BEARISH"
        print(f"D1 Bias: {d1_bias} ✗ (Close < Open)")
    print()

    # === ASIA SESSION ANALYSIS ===
    print("=" * 80)
    print("ASIA SESSION ANALYSIS (6 PM - 2 AM ET)")
    print("=" * 80)

    # Asia: 18:00 - 02:00 ET (next day)
    asia_data = prev_day_data[prev_day_data["hour"].isin([18, 19, 20, 21, 22, 23])]
    next_day = yesterday + timedelta(days=1)
    if next_day in dates:
        next_day_early = df[(df["date"] == next_day) & (df["hour"].isin([0, 1, 2]))]
        asia_data = pd.concat([asia_data, next_day_early])

    if len(asia_data) > 0:
        asia_high = asia_data["high"].max()
        asia_low = asia_data["low"].min()
        asia_open = asia_data.iloc[0]["open"]
        asia_close = asia_data.iloc[-1]["close"]
        asia_range = asia_high - asia_low

        print(f"High:  ${asia_high:,.2f}")
        print(f"Low:   ${asia_low:,.2f}")
        print(f"Range: {asia_range:.2f} points")
        print(f"Move:  {asia_close - asia_open:+.2f} points")

        if asia_close > asia_open:
            asia_bias = "BULLISH"
            print(f"Asia Bias: {asia_bias} ✓")
        else:
            asia_bias = "BEARISH"
            print(f"Asia Bias: {asia_bias} ✗")
    else:
        print("No Asia session data found")
        asia_bias = "UNKNOWN"
        asia_high = None
        asia_low = None
    print()

    # === LONDON SESSION ANALYSIS ===
    print("=" * 80)
    print("LONDON SESSION ANALYSIS (3 AM - 8 AM ET)")
    print("=" * 80)

    # London: 03:00 - 08:00 ET
    if next_day in dates:
        london_data = df[
            (df["date"] == next_day) & (df["hour"].isin([3, 4, 5, 6, 7, 8]))
        ]

        if len(london_data) > 0:
            london_high = london_data["high"].max()
            london_low = london_data["low"].min()
            london_open = london_data.iloc[0]["open"]
            london_close = london_data.iloc[-1]["close"]
            london_range = london_high - london_low

            print(f"High:  ${london_high:,.2f}")
            print(f"Low:   ${london_low:,.2f}")
            print(f"Range: {london_range:.2f} points")
            print(f"Move:  {london_close - london_open:+.2f} points")

            if london_close > london_open:
                london_bias = "BULLISH"
                print(f"London Bias: {london_bias} ✓")
            else:
                london_bias = "BEARISH"
                print(f"London Bias: {london_bias} ✗")
        else:
            print("No London session data found")
            london_bias = "UNKNOWN"
            london_high = None
            london_low = None
    else:
        print(f"Next day ({next_day}) not in data")
        london_bias = "UNKNOWN"
        london_high = None
        london_low = None
    print()

    # === KEY LEVELS ===
    print("=" * 80)
    print("KEY LEVELS FOR TODAY")
    print("=" * 80)

    print(f"D1 High:     ${d1_high:,.2f} - Major resistance")
    print(f"D1 Low:      ${d1_low:,.2f} - Major support")

    if asia_high is not None:
        print(f"Asia High:   ${asia_high:,.2f} - Overnight resistance")
        print(f"Asia Low:    ${asia_low:,.2f} - Overnight support")

    if london_high is not None:
        print(f"London High: ${london_high:,.2f} - Recent resistance")
        print(f"London Low:  ${london_low:,.2f} - Recent support")
    print()

    # === BIAS CALCULATION ===
    print("=" * 80)
    print("TODAY'S TRADING BIAS")
    print("=" * 80)

    bias_score = 0
    reasons = []

    # D1 bias (weight: 2)
    if d1_bias == "BULLISH":
        bias_score += 2
        reasons.append(f"✓ D1 closed BULLISH (+{d1_close - d1_open:.2f} pts)")
    else:
        bias_score -= 2
        reasons.append(f"✗ D1 closed BEARISH ({d1_close - d1_open:.2f} pts)")

    # Asia bias (weight: 1)
    if asia_bias == "BULLISH":
        bias_score += 1
        reasons.append("✓ Asia session BULLISH")
    elif asia_bias == "BEARISH":
        bias_score -= 1
        reasons.append("✗ Asia session BEARISH")

    # London bias (weight: 1.5)
    if london_bias == "BULLISH":
        bias_score += 1.5
        reasons.append("✓ London session BULLISH")
    elif london_bias == "BEARISH":
        bias_score -= 1.5
        reasons.append("✗ London session BEARISH")

    # Price position relative to D1 range (weight: 1)
    if london_high is not None and london_low is not None:
        current_price = london_close
        d1_mid = (d1_high + d1_low) / 2

        if current_price > d1_mid:
            bias_score += 1
            reasons.append(f"✓ Price above D1 midpoint (${d1_mid:.2f})")
        else:
            bias_score -= 1
            reasons.append(f"✗ Price below D1 midpoint (${d1_mid:.2f})")

    print("Bias Factors:")
    for i, reason in enumerate(reasons, 1):
        print(f"  {i}. {reason}")
    print()

    print(f"Bias Score: {bias_score:+.1f}")
    print()

    # Final bias
    if bias_score >= 2:
        final_bias = "BULLISH"
        confidence = min(abs(bias_score) / 5.5 * 100, 100)
        direction = "LONG"
    elif bias_score <= -2:
        final_bias = "BEARISH"
        confidence = min(abs(bias_score) / 5.5 * 100, 100)
        direction = "SHORT"
    else:
        final_bias = "NEUTRAL"
        confidence = 100 - min(abs(bias_score) / 5.5 * 100, 100)
        direction = "WAIT"

    print("=" * 80)
    print(f"FINAL BIAS: {final_bias}")
    print(f"Confidence: {confidence:.1f}%")
    print(f"Direction:  {direction}")
    print("=" * 80)
    print()

    # Trading plan
    print("TRADING PLAN:")
    print("-" * 80)

    if direction == "LONG":
        print(f"Entry Zone:  ${london_low:.2f} - ${london_low + 20:.2f}")
        print(f"Stop Loss:   ${asia_low:.2f} (risk: {london_low - asia_low:.2f} pts)")
        print(f"Target 1:    ${d1_high:.2f} (reward: {d1_high - london_low:.2f} pts)")
        print(f"Target 2:    ${d1_high + 50:.2f} (extension)")

    elif direction == "SHORT":
        print(f"Entry Zone:  ${london_high:.2f} - ${london_high - 20:.2f}")
        print(
            f"Stop Loss:   ${asia_high:.2f} (risk: {asia_high - london_high:.2f} pts)"
        )
        print(f"Target 1:    ${d1_low:.2f} (reward: {london_high - d1_low:.2f} pts)")
        print(f"Target 2:    ${d1_low - 50:.2f} (extension)")

    else:
        print("Wait for clearer setup. Mixed signals from D1/Asia/London sessions.")
        print("Look for breakout above recent highs or breakdown below recent lows.")

    print()


if __name__ == "__main__":
    analyze_sessions()
