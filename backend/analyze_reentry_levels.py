import psycopg2
from datetime import datetime, timedelta
import pytz
from collections import defaultdict

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)
cursor = conn.cursor()

current_high = 25647
original_entry = 25538
one_hour_ago = datetime.now(pytz.UTC) - timedelta(hours=1)
et_tz = pytz.timezone("US/Eastern")

print(f"\n{'='*110}")
print("🔄 REENTRY ANALYSIS - Finding Pullback Support Zones")
print(f"{'='*110}")
print(f"Session High: {current_high:.2f}")
print(f"Original Entry: {original_entry:.2f}")
print(
    f"Move Size: +{current_high - original_entry:.2f} points (+{(current_high - original_entry)/original_entry*100:.2f}%)"
)
print(f"Analysis: Last Hour | Target: Support levels for reentry")
print(f"{'='*110}\n")

# Define pullback range: between original entry and current high
pullback_low = original_entry
pullback_high = current_high

# Get BUY orders in pullback zone
mbo_buys_query = """
SELECT timestamp, price, size, side, action
FROM mbo_data
WHERE timestamp >= %s 
  AND side = 'BUY'
  AND action = 'ADD'
  AND price BETWEEN %s AND %s
  AND size > 15
ORDER BY price DESC;
"""
cursor.execute(mbo_buys_query, (one_hour_ago, pullback_low, pullback_high))
mbo_buys = cursor.fetchall()

# Get BUY absorption in pullback zone
buy_absorption_query = """
SELECT timestamp, price, absorbed_volume, aggressor_volume, significance_score
FROM absorption_events
WHERE timestamp >= %s
  AND side = 'BUY'
  AND price BETWEEN %s AND %s
ORDER BY price DESC;
"""
cursor.execute(buy_absorption_query, (one_hour_ago, pullback_low, pullback_high))
buy_absorptions = cursor.fetchall()

# Get BUY icebergs in pullback zone
buy_icebergs_query = """
SELECT timestamp, price, detected_size, confidence_score, event_type
FROM stops_icebergs
WHERE timestamp >= %s
  AND side = 'BUY'
  AND price BETWEEN %s AND %s
ORDER BY price DESC;
"""
cursor.execute(buy_icebergs_query, (one_hour_ago, pullback_low, pullback_high))
buy_icebergs = cursor.fetchall()

print(f"📊 SUPPORT DATA IN PULLBACK ZONE ({pullback_low:.2f} - {pullback_high:.2f})")
print(f"{'─'*110}")
print(f"  BUY Orders (MBO):         {len(mbo_buys):5d} orders")
print(f"  BUY Absorption:           {len(buy_absorptions):5d} events")
print(f"  BUY Icebergs:             {len(buy_icebergs):5d} detected")
print(f"{'─'*110}\n")

# Build support levels
support_levels = defaultdict(
    lambda: {
        "mbo_volume": 0,
        "mbo_count": 0,
        "absorption": 0,
        "abs_count": 0,
        "high_sig_abs": 0,
        "icebergs": 0,
        "ice_count": 0,
        "score": 0,
        "distance_from_high": 0,
    }
)

# Add MBO buys
for r in mbo_buys:
    price = round(r[1], 2)
    support_levels[price]["mbo_volume"] += r[2]
    support_levels[price]["mbo_count"] += 1
    support_levels[price]["score"] += r[2] / 5  # Weight MBO

# Add absorption
for r in buy_absorptions:
    price = round(r[1], 2)
    support_levels[price]["absorption"] += r[2]
    support_levels[price]["abs_count"] += 1
    if r[4] and r[4] > 0.7:  # High significance
        support_levels[price]["high_sig_abs"] += 1
        support_levels[price]["score"] += (
            r[2] / 2
        )  # Higher weight for significant absorption
    else:
        support_levels[price]["score"] += r[2] / 3

# Add icebergs
for r in buy_icebergs:
    price = round(r[1], 2)
    support_levels[price]["icebergs"] += r[2]
    support_levels[price]["ice_count"] += 1
    support_levels[price]["score"] += 100  # High weight for icebergs

# Calculate distance from high
for price in support_levels:
    support_levels[price]["distance_from_high"] = current_high - price

# Sort by score
sorted_support = sorted(
    support_levels.items(), key=lambda x: x[1]["score"], reverse=True
)

print("🟢 TOP SUPPORT LEVELS FOR REENTRY (Sorted by Strength)")
print(f"{'─'*110}")
print(
    f"{'Price':<10} {'From High':<12} {'MBO Vol':<12} {'Absorption':<12} {'Icebergs':<10} {'Score':<10} {'Strength':<15}"
)
print(f"{'─'*110}")

key_support_levels = []
for price, data in sorted_support[:25]:
    distance = data["distance_from_high"]
    pullback_pct = (distance / current_high) * 100

    # Determine strength
    if data["score"] > 100:
        strength = "🔥 STRONG"
    elif data["score"] > 50:
        strength = "⚠️  MODERATE"
    elif data["score"] > 20:
        strength = "📊 DECENT"
    else:
        strength = "💨 LIGHT"

    # Track good reentry levels (score > 30)
    if data["score"] > 30:
        key_support_levels.append((price, data, distance, pullback_pct))

    print(
        f"{price:<10.2f} -{distance:>6.2f} ({pullback_pct:>4.2f}%) {data['mbo_volume']:<12.1f} {data['absorption']:<12.1f} {data['icebergs']:<10d} {data['score']:<10.1f} {strength:<15}"
    )

# Identify key zones
print(f"\n{'='*110}")
print("🎯 RECOMMENDED REENTRY ZONES")
print(f"{'='*110}\n")

if key_support_levels:
    for i, (price, data, distance, pct) in enumerate(key_support_levels[:5], 1):
        print(
            f"Zone {i}: {price:.2f} (-{distance:.2f} points / -{pct:.2f}% pullback from high)"
        )
        print(f"  Strength Score: {data['score']:.0f}")

        # Show what makes this level strong
        components = []
        if data["mbo_volume"] > 0:
            components.append(
                f"{data['mbo_count']} MBO orders ({data['mbo_volume']:.0f} contracts)"
            )
        if data["absorption"] > 0:
            abs_str = f"{data['abs_count']} absorption events ({data['absorption']:.0f} volume)"
            if data["high_sig_abs"] > 0:
                abs_str += f" [{data['high_sig_abs']} high-significance]"
            components.append(abs_str)
        if data["icebergs"] > 0:
            components.append(
                f"{data['ice_count']} icebergs ({data['icebergs']:.0f} size)"
            )

        for comp in components:
            print(f"    • {comp}")
        print()
else:
    print("⚠️  No strong support levels found in pullback zone")
    print(
        "   → May need to wait for deeper pullback or new institutional positioning\n"
    )

# Fibonacci retracement levels
print(f"\n{'─'*110}")
print("📐 FIBONACCI RETRACEMENT LEVELS (Technical Reference)")
print(f"{'─'*110}")

move_size = current_high - original_entry
fib_levels = {
    "23.6%": current_high - (move_size * 0.236),
    "38.2%": current_high - (move_size * 0.382),
    "50.0%": current_high - (move_size * 0.500),
    "61.8%": current_high - (move_size * 0.618),
    "78.6%": current_high - (move_size * 0.786),
}

for level_name, fib_price in fib_levels.items():
    # Find if there's institutional support near this fib level
    nearby_support = [s for s in sorted_support if abs(s[0] - fib_price) < 10]
    confluence = ""
    if nearby_support:
        total_score = sum(s[1]["score"] for s in nearby_support[:3])
        if total_score > 50:
            confluence = " ✓ CONFLUENCE with institutional support"

    print(f"  {level_name}: {fib_price:>8.2f}{confluence}")

# Trading recommendations
print(f"\n\n{'='*110}")
print("💡 REENTRY STRATEGY")
print(f"{'='*110}\n")

if key_support_levels:
    # Best reentry
    best = key_support_levels[0]
    print(f"🎯 PRIMARY REENTRY TARGET: {best[0]:.2f}")
    print(f"   Distance from high: -{best[2]:.2f} points (-{best[3]:.2f}%)")
    print(f"   Strength: {best[1]['score']:.0f} (Strong institutional support)")

    # Check if it's close to original entry
    if abs(best[0] - original_entry) < 20:
        print(
            f"   ⚠️  This is near your original entry zone - institutions still defending"
        )

    # Alternative entries
    if len(key_support_levels) >= 2:
        alt = key_support_levels[1]
        print(f"\n🎯 ALTERNATIVE REENTRY: {alt[0]:.2f}")
        print(f"   Distance from high: -{alt[2]:.2f} points (-{alt[3]:.2f}%)")
        print(f"   Strength: {alt[1]['score']:.0f}")

    print(f"\n📋 EXECUTION PLAN:")
    print(f"   1. Set alerts at top 3 support levels")
    print(f"   2. Wait for price to pull back to these zones")
    print(f"   3. Look for bullish price action (rejection wick, volume spike)")
    print(f"   4. Enter with tight stop below support level")
    print(f"   5. Target: Retest of {current_high:.2f} and higher")

    # Risk assessment
    print(f"\n⚠️  RISK ASSESSMENT:")
    strongest_support_price = key_support_levels[0][0]
    risk_from_high = current_high - strongest_support_price
    print(
        f"   • Pullback to strongest support: -{risk_from_high:.2f} points (-{(risk_from_high/current_high)*100:.2f}%)"
    )

    if strongest_support_price > original_entry + 20:
        print(f"   • Good: Reentry still above original entry zone (more cushion)")
    elif strongest_support_price > original_entry:
        print(f"   • Moderate: Reentry near original entry (less cushion)")
    else:
        print(f"   • Caution: Reentry below original entry (trend may be weakening)")

else:
    print("⚠️  NO STRONG REENTRY LEVELS IDENTIFIED")
    print("\nOPTIONS:")
    print("   1. Wait for price to pull back to original entry zone (25538-25545)")
    print("   2. Wait for new institutional positioning to form")
    print("   3. Look for intraday support formation at lower timeframes")
    print("   4. Consider this move complete and wait for next setup")

print(f"\n{'='*110}\n")

cursor.close()
conn.close()
