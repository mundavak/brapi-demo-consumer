import psycopg2
from datetime import datetime, timedelta
import pytz
from collections import defaultdict

# Database connection
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)
cursor = conn.cursor()

one_hour_ago = datetime.now(pytz.UTC) - timedelta(hours=1)
et_tz = pytz.timezone("US/Eastern")

print(f"\n{'='*110}")
print(f"🏦 COMPREHENSIVE INSTITUTIONAL ANALYSIS - Last Hour")
print(f"{'='*110}")
print(
    f"Analysis time: {datetime.now().astimezone(et_tz).strftime('%Y-%m-%d %H:%M:%S ET')}"
)
print(f"Data period: {one_hour_ago.astimezone(et_tz).strftime('%H:%M:%S ET')} to now")
print(f"Filters: MBO size > 15, All absorption events, All icebergs/stops")
print(f"{'='*110}\n")

# ============================================================================
# 1. MBO DATA (Order Flow)
# ============================================================================
mbo_query = """
SELECT timestamp, symbol, price, size, side, action, order_id
FROM mbo_data
WHERE timestamp >= %s AND size > 15 AND action IN ('ADD', 'DELETE', 'MODIFY')
ORDER BY timestamp DESC;
"""
cursor.execute(mbo_query, (one_hour_ago,))
mbo_rows = cursor.fetchall()

# ============================================================================
# 2. ABSORPTION DATA (Aggressive fills)
# ============================================================================
absorption_query = """
SELECT timestamp, symbol, event_type, side, price, absorbed_volume, 
       aggressor_volume, absorption_ratio, significance_score
FROM absorption_events
WHERE timestamp >= %s
ORDER BY timestamp DESC;
"""
cursor.execute(absorption_query, (one_hour_ago,))
absorption_rows = cursor.fetchall()

# ============================================================================
# 3. ICEBERGS & STOPS DATA (Hidden liquidity)
# ============================================================================
icebergs_query = """
SELECT timestamp, symbol, event_type, side, price, detected_size,
       estimated_total_size, confidence_score
FROM stops_icebergs
WHERE timestamp >= %s
ORDER BY timestamp DESC;
"""
cursor.execute(icebergs_query, (one_hour_ago,))
icebergs_rows = cursor.fetchall()

print(f"📊 DATA SUMMARY")
print(f"{'─'*110}")
print(f"  MBO Orders (size > 15):        {len(mbo_rows):5d} orders")
print(f"  Absorption Events:             {len(absorption_rows):5d} events")
print(f"  Icebergs/Stops Detected:       {len(icebergs_rows):5d} events")
print(f"{'─'*110}\n")

# ============================================================================
# ANALYZE MBO DATA
# ============================================================================
if mbo_rows:
    buy_adds = [r for r in mbo_rows if r[4] == "BUY" and r[5] == "ADD"]
    sell_adds = [r for r in mbo_rows if r[4] == "SELL" and r[5] == "ADD"]
    buy_deletes = [r for r in mbo_rows if r[4] == "BUY" and r[5] == "DELETE"]
    sell_deletes = [r for r in mbo_rows if r[4] == "SELL" and r[5] == "DELETE"]

    buy_volume = sum(r[3] for r in buy_adds)
    sell_volume = sum(r[3] for r in sell_adds)
    buy_cancelled = sum(r[3] for r in buy_deletes if r[3] > 0)
    sell_cancelled = sum(r[3] for r in sell_deletes if r[3] > 0)

    net_buy = buy_volume - buy_cancelled
    net_sell = sell_volume - sell_cancelled
    mbo_delta = net_buy - net_sell

    print("📈 MBO ORDER FLOW ANALYSIS")
    print(f"{'─'*110}")
    print(
        f"  🟢 BUY Orders:    {len(buy_adds):4d} placed ({buy_volume:8.1f} contracts)  |  {len(buy_deletes):4d} cancelled ({buy_cancelled:8.1f})"
    )
    print(
        f"  🔴 SELL Orders:   {len(sell_adds):4d} placed ({sell_volume:8.1f} contracts)  |  {len(sell_deletes):4d} cancelled ({sell_cancelled:8.1f})"
    )
    print(f"  {'─'*106}")
    print(f"  Net BUY liquidity:   {net_buy:8.1f} contracts")
    print(f"  Net SELL liquidity:  {net_sell:8.1f} contracts")
    print(f"  MBO DELTA:           {mbo_delta:+8.1f} contracts")
    print(f"{'─'*110}\n")

    # Price level analysis
    buy_levels = defaultdict(lambda: {"volume": 0, "count": 0})
    sell_levels = defaultdict(lambda: {"volume": 0, "count": 0})
    for r in buy_adds:
        price = round(r[2], 2)
        buy_levels[price]["volume"] += r[3]
        buy_levels[price]["count"] += 1
    for r in sell_adds:
        price = round(r[2], 2)
        sell_levels[price]["volume"] += r[3]
        sell_levels[price]["count"] += 1

# ============================================================================
# ANALYZE ABSORPTION DATA
# ============================================================================
if absorption_rows:
    buy_absorptions = [r for r in absorption_rows if r[3] == "BUY"]
    sell_absorptions = [r for r in absorption_rows if r[3] == "SELL"]

    buy_abs_volume = sum(r[5] for r in buy_absorptions)
    sell_abs_volume = sum(r[5] for r in sell_absorptions)

    # High significance absorption (>0.7)
    significant_buy = [r for r in buy_absorptions if r[8] > 0.7]
    significant_sell = [r for r in sell_absorptions if r[8] > 0.7]

    print("💥 ABSORPTION ANALYSIS (Aggressive Fills)")
    print(f"{'─'*110}")
    print(
        f"  🟢 BUY Absorption:    {len(buy_absorptions):4d} events  |  {buy_abs_volume:10.1f} contracts absorbed"
    )
    print(
        f"  🔴 SELL Absorption:   {len(sell_absorptions):4d} events  |  {sell_abs_volume:10.1f} contracts absorbed"
    )
    print(f"  {'─'*106}")
    print(
        f"  High-significance BUY absorption (>0.7):   {len(significant_buy):4d} events"
    )
    print(
        f"  High-significance SELL absorption (>0.7):  {len(significant_sell):4d} events"
    )

    absorption_delta = buy_abs_volume - sell_abs_volume
    print(
        f"  ABSORPTION DELTA:    {absorption_delta:+8.1f} contracts (positive = buying pressure)"
    )
    print(f"{'─'*110}\n")

    # Top absorption price levels
    abs_buy_levels = defaultdict(lambda: {"volume": 0, "count": 0, "avg_score": 0})
    abs_sell_levels = defaultdict(lambda: {"volume": 0, "count": 0, "avg_score": 0})

    for r in buy_absorptions:
        price = round(r[4], 2)
        abs_buy_levels[price]["volume"] += r[5]
        abs_buy_levels[price]["count"] += 1
        abs_buy_levels[price]["avg_score"] += r[8]

    for r in sell_absorptions:
        price = round(r[4], 2)
        abs_sell_levels[price]["volume"] += r[5]
        abs_sell_levels[price]["count"] += 1
        abs_sell_levels[price]["avg_score"] += r[8]

    # Calculate averages
    for level in abs_buy_levels.values():
        level["avg_score"] /= level["count"]
    for level in abs_sell_levels.values():
        level["avg_score"] /= level["count"]

# ============================================================================
# ANALYZE ICEBERGS & STOPS
# ============================================================================
if icebergs_rows:
    icebergs = [r for r in icebergs_rows if r[2] == "ICEBERG"]
    stops = [r for r in icebergs_rows if r[2] == "STOP_CLUSTER"]

    buy_icebergs = [r for r in icebergs if r[3] == "BUY"]
    sell_icebergs = [r for r in icebergs if r[3] == "SELL"]
    buy_stops = [r for r in stops if r[3] == "BUY"]
    sell_stops = [r for r in stops if r[3] == "SELL"]

    print("🧊 ICEBERGS & STOPS ANALYSIS (Hidden Liquidity)")
    print(f"{'─'*110}")
    print(f"  🟢 BUY Icebergs:   {len(buy_icebergs):4d} detected")
    print(f"  🔴 SELL Icebergs:  {len(sell_icebergs):4d} detected")
    print(f"  🟢 BUY Stops:      {len(buy_stops):4d} clusters")
    print(f"  🔴 SELL Stops:     {len(sell_stops):4d} clusters")
    print(f"{'─'*110}\n")

    # Iceberg price levels
    iceberg_buy_levels = defaultdict(
        lambda: {"count": 0, "total_size": 0, "confidence": 0}
    )
    iceberg_sell_levels = defaultdict(
        lambda: {"count": 0, "total_size": 0, "confidence": 0}
    )

    for r in buy_icebergs:
        price = round(r[4], 2)
        iceberg_buy_levels[price]["count"] += 1
        iceberg_buy_levels[price]["total_size"] += r[5]
        iceberg_buy_levels[price]["confidence"] += r[7]

    for r in sell_icebergs:
        price = round(r[4], 2)
        iceberg_sell_levels[price]["count"] += 1
        iceberg_sell_levels[price]["total_size"] += r[5]
        iceberg_sell_levels[price]["confidence"] += r[7]

# ============================================================================
# UNIFIED BIAS CALCULATION
# ============================================================================
print(f"\n{'='*110}")
print("🎯 UNIFIED INSTITUTIONAL BIAS")
print(f"{'='*110}\n")

total_score = 0
bias_components = []

# MBO contribution (40% weight)
if mbo_rows:
    mbo_bias_score = (mbo_delta / 1000) * 40  # Normalize to -40 to +40
    total_score += mbo_bias_score
    bias_components.append(f"MBO: {mbo_bias_score:+.1f}")
    print(
        f"  MBO Order Flow:        {mbo_delta:+8.1f} contracts  →  Score: {mbo_bias_score:+6.1f}/40"
    )

# Absorption contribution (40% weight)
if absorption_rows:
    absorption_bias_score = (absorption_delta / 1000) * 40
    total_score += absorption_bias_score
    bias_components.append(f"Absorption: {absorption_bias_score:+.1f}")
    print(
        f"  Absorption:            {absorption_delta:+8.1f} contracts  →  Score: {absorption_bias_score:+6.1f}/40"
    )

# Icebergs contribution (20% weight)
if icebergs_rows:
    iceberg_delta = len(buy_icebergs) - len(sell_icebergs)
    iceberg_bias_score = (iceberg_delta / 10) * 20  # Normalize to -20 to +20
    total_score += iceberg_bias_score
    bias_components.append(f"Icebergs: {iceberg_bias_score:+.1f}")
    print(
        f"  Iceberg Imbalance:     {iceberg_delta:+3d} (buy-sell)    →  Score: {iceberg_bias_score:+6.1f}/20"
    )

print(f"  {'─'*106}")
print(f"  TOTAL BIAS SCORE:      {total_score:+6.1f}/100")
print(f"{'─'*110}\n")

# Determine overall bias
if total_score > 30:
    bias = "🟢 STRONGLY BULLISH"
    signal = "Institutions AGGRESSIVELY ACCUMULATING - Look for LONG entries"
elif total_score > 10:
    bias = "🟢 BULLISH"
    signal = "Institutions accumulating - Look for LONG on pullbacks"
elif total_score < -30:
    bias = "🔴 STRONGLY BEARISH"
    signal = "Institutions AGGRESSIVELY DISTRIBUTING - Look for SHORT entries"
elif total_score < -10:
    bias = "🔴 BEARISH"
    signal = "Institutions distributing - Look for SHORT on rallies"
else:
    bias = "⚖️  NEUTRAL"
    signal = "MIXED SIGNALS - Wait for confirmation"

print(f"🎯 OVERALL BIAS: {bias}")
print(f"📡 SIGNAL: {signal}")
print(f"{'='*110}\n")

# ============================================================================
# KEY PRICE LEVELS WITH CONFLUENCE
# ============================================================================
print("📍 KEY INSTITUTIONAL PRICE LEVELS (Multi-Factor Confluence)")
print(f"{'─'*110}\n")

# Combine all levels for BUY side
all_buy_levels = defaultdict(
    lambda: {"mbo": 0, "absorption": 0, "icebergs": 0, "score": 0}
)
if mbo_rows:
    for price, data in buy_levels.items():
        all_buy_levels[price]["mbo"] = data["volume"]
        all_buy_levels[price]["score"] += data["volume"] / 10
if absorption_rows:
    for price, data in abs_buy_levels.items():
        all_buy_levels[price]["absorption"] = data["volume"]
        all_buy_levels[price]["score"] += data["volume"] / 5
if icebergs_rows:
    for price, data in iceberg_buy_levels.items():
        all_buy_levels[price]["icebergs"] = data["count"]
        all_buy_levels[price]["score"] += data["count"] * 50

# Combine all levels for SELL side
all_sell_levels = defaultdict(
    lambda: {"mbo": 0, "absorption": 0, "icebergs": 0, "score": 0}
)
if mbo_rows:
    for price, data in sell_levels.items():
        all_sell_levels[price]["mbo"] = data["volume"]
        all_sell_levels[price]["score"] += data["volume"] / 10
if absorption_rows:
    for price, data in abs_sell_levels.items():
        all_sell_levels[price]["absorption"] = data["volume"]
        all_sell_levels[price]["score"] += data["volume"] / 5
if icebergs_rows:
    for price, data in iceberg_sell_levels.items():
        all_sell_levels[price]["icebergs"] = data["count"]
        all_sell_levels[price]["score"] += data["count"] * 50

print("🟢 TOP SUPPORT ZONES (BUY Confluence)")
print(
    f"{'Price':<12} {'MBO Vol':<12} {'Absorption':<12} {'Icebergs':<12} {'Score':<10}"
)
print(f"{'─'*110}")
top_support = sorted(all_buy_levels.items(), key=lambda x: x[1]["score"], reverse=True)[
    :10
]
for price, data in top_support:
    print(
        f"{price:<12.2f} {data['mbo']:<12.1f} {data['absorption']:<12.1f} {data['icebergs']:<12d} {data['score']:<10.1f}"
    )

print(f"\n🔴 TOP RESISTANCE ZONES (SELL Confluence)")
print(
    f"{'Price':<12} {'MBO Vol':<12} {'Absorption':<12} {'Icebergs':<12} {'Score':<10}"
)
print(f"{'─'*110}")
top_resistance = sorted(
    all_sell_levels.items(), key=lambda x: x[1]["score"], reverse=True
)[:10]
for price, data in top_resistance:
    print(
        f"{price:<12.2f} {data['mbo']:<12.1f} {data['absorption']:<12.1f} {data['icebergs']:<12d} {data['score']:<10.1f}"
    )

# ============================================================================
# TRADING RECOMMENDATIONS
# ============================================================================
print(f"\n{'='*110}")
print("📌 TRADING RECOMMENDATIONS")
print(f"{'='*110}\n")

if total_score > 10:
    print("✅ BULLISH SETUP - INSTITUTIONS ACCUMULATING")
    if top_support:
        strongest = top_support[0]
        print(
            f"   → Primary support: {strongest[0]:.2f} (Score: {strongest[1]['score']:.0f})"
        )
        components = []
        if strongest[1]["mbo"] > 0:
            components.append(f"MBO: {strongest[1]['mbo']:.0f}")
        if strongest[1]["absorption"] > 0:
            components.append(f"Absorption: {strongest[1]['absorption']:.0f}")
        if strongest[1]["icebergs"] > 0:
            components.append(f"Icebergs: {strongest[1]['icebergs']}")
        print(f"      Components: {', '.join(components)}")

        if len(top_support) >= 3:
            zone_low = min(p for p, _ in top_support[:3])
            zone_high = max(p for p, _ in top_support[:3])
            print(f"   → Support zone: {zone_low:.2f} - {zone_high:.2f}")
    print("   → Strategy: LONG on pullbacks to support zones")
    print("   → Entry: Near multi-factor confluence levels")
    print("   → Stop: Below lowest support with iceberg/absorption confirmation")

elif total_score < -10:
    print("✅ BEARISH SETUP - INSTITUTIONS DISTRIBUTING")
    if top_resistance:
        strongest = top_resistance[0]
        print(
            f"   → Primary resistance: {strongest[0]:.2f} (Score: {strongest[1]['score']:.0f})"
        )
        components = []
        if strongest[1]["mbo"] > 0:
            components.append(f"MBO: {strongest[1]['mbo']:.0f}")
        if strongest[1]["absorption"] > 0:
            components.append(f"Absorption: {strongest[1]['absorption']:.0f}")
        if strongest[1]["icebergs"] > 0:
            components.append(f"Icebergs: {strongest[1]['icebergs']}")
        print(f"      Components: {', '.join(components)}")

        if len(top_resistance) >= 3:
            zone_low = min(p for p, _ in top_resistance[:3])
            zone_high = max(p for p, _ in top_resistance[:3])
            print(f"   → Resistance zone: {zone_low:.2f} - {zone_high:.2f}")
    print("   → Strategy: SHORT on rallies to resistance zones")
    print("   → Entry: Near multi-factor confluence levels")
    print("   → Stop: Above highest resistance with iceberg/absorption confirmation")
else:
    print("⚠️  NEUTRAL - MIXED INSTITUTIONAL SIGNALS")
    print("   → Wait for clearer directional bias")
    print("   → Monitor for breakouts from consolidation")
    print("   → Watch for absorption clusters at key levels")

print(f"\n{'='*110}\n")

cursor.close()
conn.close()
