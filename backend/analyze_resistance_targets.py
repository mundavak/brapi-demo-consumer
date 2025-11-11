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

current_price = 25619
one_hour_ago = datetime.now(pytz.UTC) - timedelta(hours=1)
et_tz = pytz.timezone("US/Eastern")

print(f"\n{'='*110}")
print(f"🎯 RESISTANCE ANALYSIS - Where Will Institutions SELL?")
print(f"{'='*110}")
print(f"Current Price: {current_price:.2f}")
print(f"Analysis: Last Hour | Target: Resistance levels ABOVE current price")
print(f"{'='*110}\n")

# Get MBO SELL orders above current price
mbo_sells_query = """
SELECT timestamp, price, size, side, action
FROM mbo_data
WHERE timestamp >= %s 
  AND side = 'SELL'
  AND action = 'ADD'
  AND price > %s
  AND size > 15
ORDER BY price ASC;
"""
cursor.execute(mbo_sells_query, (one_hour_ago, current_price))
mbo_sells = cursor.fetchall()

# Get SELL absorption above current price
sell_absorption_query = """
SELECT timestamp, price, absorbed_volume, aggressor_volume, significance_score
FROM absorption_events
WHERE timestamp >= %s
  AND side = 'SELL'
  AND price > %s
ORDER BY price ASC;
"""
cursor.execute(sell_absorption_query, (one_hour_ago, current_price))
sell_absorptions = cursor.fetchall()

# Get SELL icebergs above current price
sell_icebergs_query = """
SELECT timestamp, price, detected_size, confidence_score, event_type
FROM stops_icebergs
WHERE timestamp >= %s
  AND side = 'SELL'
  AND price > %s
ORDER BY price ASC;
"""
cursor.execute(sell_icebergs_query, (one_hour_ago, current_price))
sell_icebergs = cursor.fetchall()

print(f"📊 RESISTANCE DATA ABOVE {current_price:.2f}")
print(f"{'─'*110}")
print(f"  SELL Orders (MBO):        {len(mbo_sells):5d} orders")
print(f"  SELL Absorption:          {len(sell_absorptions):5d} events")
print(f"  SELL Icebergs:            {len(sell_icebergs):5d} detected")
print(f"{'─'*110}\n")

# Analyze resistance levels
resistance_levels = defaultdict(
    lambda: {
        "mbo_volume": 0,
        "mbo_count": 0,
        "absorption": 0,
        "abs_count": 0,
        "icebergs": 0,
        "ice_count": 0,
        "score": 0,
    }
)

# Add MBO sells
for r in mbo_sells:
    price = round(r[1], 2)
    resistance_levels[price]["mbo_volume"] += r[2]
    resistance_levels[price]["mbo_count"] += 1
    resistance_levels[price]["score"] += r[2] / 5  # Weight MBO

# Add absorption
for r in sell_absorptions:
    price = round(r[1], 2)
    resistance_levels[price]["absorption"] += r[2]
    resistance_levels[price]["abs_count"] += 1
    resistance_levels[price]["score"] += r[2] / 3  # Weight absorption higher

# Add icebergs
for r in sell_icebergs:
    price = round(r[1], 2)
    resistance_levels[price]["icebergs"] += r[2]
    resistance_levels[price]["ice_count"] += 1
    resistance_levels[price]["score"] += 100  # High weight for icebergs

# Sort by score
sorted_resistance = sorted(
    resistance_levels.items(), key=lambda x: x[1]["score"], reverse=True
)

print("🔴 TOP RESISTANCE LEVELS (Where Institutions Will SELL)")
print(f"{'─'*110}")
print(
    f"{'Price':<10} {'Distance':<10} {'MBO Vol':<12} {'Absorption':<12} {'Icebergs':<10} {'Score':<10} {'Strength':<15}"
)
print(f"{'─'*110}")

key_levels = []
for price, data in sorted_resistance[:20]:
    distance = price - current_price

    # Determine strength
    if data["score"] > 100:
        strength = "🔥 MAJOR"
    elif data["score"] > 50:
        strength = "⚠️  STRONG"
    elif data["score"] > 20:
        strength = "📊 MODERATE"
    else:
        strength = "💨 LIGHT"

    # Track key levels
    if data["score"] > 50:
        key_levels.append((price, data, distance))

    print(
        f"{price:<10.2f} {distance:+9.2f} {data['mbo_volume']:<12.1f} {data['absorption']:<12.1f} {data['icebergs']:<10d} {data['score']:<10.1f} {strength:<15}"
    )

# Find clusters
print(f"\n🎯 KEY RESISTANCE ZONES (Clustered Selling)")
print(f"{'─'*110}")

if key_levels:
    # Group nearby levels into zones
    zones = []
    current_zone = [key_levels[0]]

    for i in range(1, len(key_levels)):
        if key_levels[i][2] - current_zone[-1][2] < 20:  # Within 20 points
            current_zone.append(key_levels[i])
        else:
            zones.append(current_zone)
            current_zone = [key_levels[i]]
    zones.append(current_zone)

    for i, zone in enumerate(zones[:5], 1):
        zone_low = min(lvl[0] for lvl in zone)
        zone_high = max(lvl[0] for lvl in zone)
        zone_score = sum(lvl[1]["score"] for lvl in zone)
        zone_distance = zone_low - current_price

        print(
            f"\n  Zone {i}: {zone_low:.2f} - {zone_high:.2f} (+{zone_distance:.0f} to +{zone_high-current_price:.0f} points)"
        )
        print(f"    Total Score: {zone_score:.0f}")
        print(f"    Levels: {len(zone)}")

        # Show components
        total_mbo = sum(lvl[1]["mbo_volume"] for lvl in zone)
        total_abs = sum(lvl[1]["absorption"] for lvl in zone)
        total_ice = sum(lvl[1]["icebergs"] for lvl in zone)

        components = []
        if total_mbo > 0:
            components.append(f"MBO: {total_mbo:.0f} contracts")
        if total_abs > 0:
            components.append(f"Absorption: {total_abs:.0f}")
        if total_ice > 0:
            components.append(f"Icebergs: {total_ice:.0f}")

        if components:
            print(f"    {' | '.join(components)}")

# Target analysis
print(f"\n\n{'='*110}")
print("📈 PRICE TARGET ANALYSIS")
print(f"{'='*110}\n")

if key_levels:
    nearest = key_levels[0]
    print(f"🎯 NEAREST MAJOR RESISTANCE: {nearest[0]:.2f} (+{nearest[2]:.2f} points)")
    print(f"   Score: {nearest[1]['score']:.0f}")
    print(f"   This is where institutions have the MOST sell orders waiting")

    if len(key_levels) >= 2:
        second = key_levels[1]
        print(f"\n🎯 SECONDARY RESISTANCE: {second[0]:.2f} (+{second[2]:.2f} points)")
        print(f"   Score: {second[1]['score']:.0f}")

    if len(key_levels) >= 3:
        third = key_levels[2]
        print(f"\n🎯 TERTIARY RESISTANCE: {third[0]:.2f} (+{third[2]:.2f} points)")
        print(f"   Score: {third[1]['score']:.0f}")

    # Upside potential
    highest_significant = max(lvl[0] for lvl in key_levels[:5])
    total_upside = highest_significant - current_price

    print(f"\n📊 UPSIDE POTENTIAL")
    print(f"{'─'*110}")
    print(
        f"   Max realistic target: {highest_significant:.2f} (+{total_upside:.2f} points / +{total_upside/current_price*100:.2f}%)"
    )
    print(f"   Based on: Top 5 resistance zones")
else:
    print("⚠️  NO MAJOR RESISTANCE FOUND ABOVE CURRENT PRICE")
    print("   → Very bullish - minimal institutional selling pressure")
    print("   → Price may continue higher with less resistance")

# Trading recommendation
print(f"\n\n{'='*110}")
print("📌 TRADING RECOMMENDATIONS")
print(f"{'='*110}\n")

if key_levels:
    nearest = key_levels[0]
    print(f"✅ CURRENT POSITION: Price at {current_price:.2f}")
    print(f"\n🎯 TARGET PROGRESSION:")
    print(
        f"   T1: {nearest[0]:.2f} (+{nearest[2]:.2f} pts) - Take partial profits, expect resistance"
    )

    if len(key_levels) >= 2:
        second = key_levels[1]
        print(f"   T2: {second[0]:.2f} (+{second[2]:.2f} pts) - Major resistance zone")

    if len(key_levels) >= 3:
        third = key_levels[2]
        print(
            f"   T3: {third[0]:.2f} (+{third[2]:.2f} pts) - Extended target if momentum continues"
        )

    print(f"\n💡 STRATEGY:")
    print(f"   → Scale out as price approaches each target")
    print(f"   → Watch for rejection at {nearest[0]:.2f} (strongest resistance)")
    if len(key_levels) >= 2:
        print(
            f"   → If price breaks {nearest[0]:.2f} with volume, next target is {key_levels[1][0]:.2f}"
        )
    print(f"   → Trail stop to protect profits as targets are hit")
else:
    print("🚀 BULLISH SCENARIO - LIMITED RESISTANCE")
    print("   → No major institutional sell walls detected")
    print("   → Price may run freely until next data point")
    print("   → Use momentum indicators and trailing stops")

print(f"\n{'='*110}\n")

cursor.close()
conn.close()
