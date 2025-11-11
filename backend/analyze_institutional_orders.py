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

# Get TRUE MBO data (ADD/DELETE only, not DEPTH aggregations)
one_hour_ago = datetime.now(pytz.UTC) - timedelta(hours=1)

query = """
SELECT 
    timestamp,
    symbol,
    price,
    size,
    side,
    action,
    order_id,
    metadata
FROM mbo_data
WHERE timestamp >= %s
  AND size > 15
  AND action IN ('ADD', 'DELETE', 'MODIFY')
ORDER BY timestamp DESC
LIMIT 1000;
"""

cursor.execute(query, (one_hour_ago,))
rows = cursor.fetchall()

print(f"\n{'='*100}")
print(f"🏦 INSTITUTIONAL ORDER FLOW ANALYSIS - Last Hour (Size > 15 contracts)")
print(f"{'='*100}")
print(f"Total institutional orders: {len(rows)}")
print(f"Analysis time: {datetime.now()}")
print(
    f"Data period: {one_hour_ago.astimezone(pytz.timezone('US/Eastern')).strftime('%H:%M:%S ET')} to now"
)
print(f"{'='*100}\n")

if len(rows) == 0:
    print("⚠️  NO TRUE MBO DATA FOUND")
    print("\nThis could mean:")
    print("  1. MBO Consumer not running or just started")
    print("  2. No institutional-sized orders (>15 contracts) in last hour")
    print("  3. Market is closed or extremely quiet")
    print("  4. Only receiving aggregated depth data (not true order-by-order)")
    print("\n💡 Check log: F:/Databases/Logs/mbo_consumer.log")
    print("   Look for: '✓ TRUE MBO DATA CONFIRMED'")
    cursor.close()
    conn.close()
    exit()

# Separate by action type
adds = [r for r in rows if r[5] == "ADD"]
deletes = [r for r in rows if r[5] == "DELETE"]
modifies = [r for r in rows if r[5] == "MODIFY"]

# Analyze buy vs sell
buy_adds = [r for r in adds if r[4] == "BUY"]
sell_adds = [r for r in adds if r[4] == "SELL"]
buy_deletes = [r for r in deletes if r[4] == "BUY"]
sell_deletes = [r for r in deletes if r[4] == "SELL"]

# Calculate volumes
buy_placed_vol = sum(r[3] for r in buy_adds)
sell_placed_vol = sum(r[3] for r in sell_adds)
buy_cancelled_vol = sum(r[3] for r in buy_deletes if r[3] > 0)
sell_cancelled_vol = sum(r[3] for r in sell_deletes if r[3] > 0)

print("📊 ORDER FLOW BREAKDOWN")
print(f"{'─'*100}")
print(f"  {'Type':<30} {'Count':<10} {'Volume':<15} {'Avg Size':<12}")
print(f"{'─'*100}")
print(
    f"  {'🟢 BUY Orders Placed (ADD)':<30} {len(buy_adds):<10} {buy_placed_vol:<15.1f} {buy_placed_vol/len(buy_adds) if buy_adds else 0:<12.1f}"
)
print(
    f"  {'🔴 SELL Orders Placed (ADD)':<30} {len(sell_adds):<10} {sell_placed_vol:<15.1f} {sell_placed_vol/len(sell_adds) if sell_adds else 0:<12.1f}"
)
print(
    f"  {'❌ BUY Orders Pulled (DELETE)':<30} {len(buy_deletes):<10} {buy_cancelled_vol:<15.1f} {buy_cancelled_vol/len(buy_deletes) if buy_deletes else 0:<12.1f}"
)
print(
    f"  {'❌ SELL Orders Pulled (DELETE)':<30} {len(sell_deletes):<10} {sell_cancelled_vol:<15.1f} {sell_cancelled_vol/len(sell_deletes) if sell_deletes else 0:<12.1f}"
)
print(
    f"  {'🔄 Modified Orders':<30} {len(modifies):<10} {sum(r[3] for r in modifies):<15.1f} {sum(r[3] for r in modifies)/len(modifies) if modifies else 0:<12.1f}"
)
print(f"{'─'*100}\n")

# Net positioning (shows institutional intent)
net_buy_liquidity = buy_placed_vol - buy_cancelled_vol
net_sell_liquidity = sell_placed_vol - sell_cancelled_vol
delta = net_buy_liquidity - net_sell_liquidity

# Aggression metrics (cancellations show spoofing/hesitation)
buy_pull_ratio = (buy_cancelled_vol / buy_placed_vol * 100) if buy_placed_vol > 0 else 0
sell_pull_ratio = (
    (sell_cancelled_vol / sell_placed_vol * 100) if sell_placed_vol > 0 else 0
)

print("💰 NET INSTITUTIONAL POSITIONING")
print(f"{'─'*100}")
print(
    f"  Net BUY liquidity:        {net_buy_liquidity:8.1f} contracts  (placed - pulled)"
)
print(
    f"  Net SELL liquidity:       {net_sell_liquidity:8.1f} contracts  (placed - pulled)"
)
print(f"  NET DELTA:                {delta:+8.1f} contracts")
print(f"{'─'*100}")
print(
    f"  BUY pull ratio:           {buy_pull_ratio:6.1f}%  (higher = more spoofing/hesitation)"
)
print(
    f"  SELL pull ratio:          {sell_pull_ratio:6.1f}%  (higher = more spoofing/hesitation)"
)
print(f"{'─'*100}\n")

# Determine bias
if abs(delta) < 30:
    bias = "⚖️  NEUTRAL"
    strength = "MIXED"
    signal = "NO CLEAR DIRECTION - Wait for clearer positioning"
elif delta > 100:
    bias = "🟢 STRONGLY BULLISH"
    strength = "STRONG"
    signal = "Institutions AGGRESSIVELY BUYING - Look for LONG entries"
elif delta > 30:
    bias = "🟢 BULLISH"
    strength = "MODERATE"
    signal = "Institutions accumulating BID - Look for LONG on pullbacks"
elif delta < -100:
    bias = "🔴 STRONGLY BEARISH"
    strength = "STRONG"
    signal = "Institutions AGGRESSIVELY SELLING - Look for SHORT entries"
else:
    bias = "🔴 BEARISH"
    strength = "MODERATE"
    signal = "Institutions distributing ASK - Look for SHORT on rallies"

print(f"🎯 TRADING BIAS: {bias}")
print(f"📊 Signal Strength: {strength}")
print(f"📡 SIGNAL: {signal}")
print(f"{'='*100}\n")

# Price level analysis
buy_price_levels = defaultdict(lambda: {"count": 0, "volume": 0, "cancelled": 0})
sell_price_levels = defaultdict(lambda: {"count": 0, "volume": 0, "cancelled": 0})

for r in buy_adds:
    price = round(r[2], 2)
    buy_price_levels[price]["count"] += 1
    buy_price_levels[price]["volume"] += r[3]

for r in buy_deletes:
    price = round(r[2], 2) if r[2] > 0 else 0
    buy_price_levels[price]["cancelled"] += r[3] if r[3] > 0 else 0

for r in sell_adds:
    price = round(r[2], 2)
    sell_price_levels[price]["count"] += 1
    sell_price_levels[price]["volume"] += r[3]

for r in sell_deletes:
    price = round(r[2], 2) if r[2] > 0 else 0
    sell_price_levels[price]["cancelled"] += r[3] if r[3] > 0 else 0

# Find key price levels
print("📍 KEY INSTITUTIONAL PRICE LEVELS")
print(f"{'─'*100}\n")

print("🟢 TOP INSTITUTIONAL BID ZONES (Where big players are BUYING)")
print(
    f"{'Price':<12} {'Orders':<10} {'Volume':<12} {'Cancelled':<12} {'Net':<12} {'Conviction':<15}"
)
print(f"{'─'*100}")
top_buys = sorted(
    [(p, d) for p, d in buy_price_levels.items() if d["volume"] > 0],
    key=lambda x: x[1]["volume"] - x[1]["cancelled"],
    reverse=True,
)[:10]

for price, data in top_buys:
    net = data["volume"] - data["cancelled"]
    conviction = (
        "🔥 STRONG"
        if data["cancelled"] / data["volume"] < 0.2
        else ("⚠️  WEAK" if data["cancelled"] / data["volume"] > 0.5 else "📊 MODERATE")
    )
    print(
        f"{price:<12.2f} {data['count']:<10} {data['volume']:<12.1f} {data['cancelled']:<12.1f} {net:<12.1f} {conviction:<15}"
    )

print(f"\n🔴 TOP INSTITUTIONAL ASK ZONES (Where big players are SELLING)")
print(
    f"{'Price':<12} {'Orders':<10} {'Volume':<12} {'Cancelled':<12} {'Net':<12} {'Conviction':<15}"
)
print(f"{'─'*100}")
top_sells = sorted(
    [(p, d) for p, d in sell_price_levels.items() if d["volume"] > 0],
    key=lambda x: x[1]["volume"] - x[1]["cancelled"],
    reverse=True,
)[:10]

for price, data in top_sells:
    net = data["volume"] - data["cancelled"]
    conviction = (
        "🔥 STRONG"
        if data["cancelled"] / data["volume"] < 0.2
        else ("⚠️  WEAK" if data["cancelled"] / data["volume"] > 0.5 else "📊 MODERATE")
    )
    print(
        f"{price:<12.2f} {data['count']:<10} {data['volume']:<12.1f} {data['cancelled']:<12.1f} {net:<12.1f} {conviction:<15}"
    )

# Find whale orders
print(f"\n🐋 LARGEST INDIVIDUAL ORDERS (Institutional Whales)")
print(f"{'─'*100}")
print(
    f"{'Time (ET)':<12} {'Side':<6} {'Action':<10} {'Price':<12} {'Size':<10} {'Symbol':<15}"
)
print(f"{'─'*100}")
largest = sorted(
    [r for r in rows if r[5] in ("ADD", "MODIFY")], key=lambda x: x[3], reverse=True
)[:20]
for r in largest:
    time_et = (
        r[0].astimezone(pytz.timezone("US/Eastern")).strftime("%H:%M:%S")
        if r[0]
        else "N/A"
    )
    emoji = "🟢" if r[4] == "BUY" else "🔴"
    side = f"{emoji} {r[4]}"
    print(f"{time_et:<12} {side:<6} {r[5]:<10} {r[2]:<12.2f} {r[3]:<10.1f} {r[1]:<15}")

# Trading recommendations
print(f"\n{'='*100}")
print("📌 TRADING RECOMMENDATIONS")
print(f"{'='*100}\n")

if abs(delta) < 30:
    print("⚠️  MIXED SIGNALS - NO CLEAR INSTITUTIONAL DIRECTION")
    print("   → Wait for clearer order flow before entering")
    print("   → Watch for order flow imbalances at key levels")
    print("   → Monitor pull ratios - high cancellations = indecision/spoofing")

elif delta > 50:
    print("✅ BULLISH SETUP - INSTITUTIONS ACCUMULATING")
    if top_buys:
        strongest_bid = max(top_buys, key=lambda x: x[1]["volume"] - x[1]["cancelled"])
        print(
            f"   → Primary support: {strongest_bid[0]:.2f} ({strongest_bid[1]['volume']:.0f} contracts)"
        )
        if len(top_buys) >= 3:
            support_zone_low = min(p for p, _ in top_buys[:3])
            support_zone_high = max(p for p, _ in top_buys[:3])
            print(
                f"   → Support zone: {support_zone_low:.2f} - {support_zone_high:.2f}"
            )
    print("   → Strategy: Look for LONG entries on pullbacks to institutional bids")
    print("   → Entry: Near high-conviction bid zones (low cancellation ratio)")
    print("   → Stop: Below lowest significant bid level")
    if buy_pull_ratio > 40:
        print(
            f"   ⚠️  WARNING: High BUY cancellation rate ({buy_pull_ratio:.0f}%) - may indicate spoofing"
        )

else:  # Bearish
    print("✅ BEARISH SETUP - INSTITUTIONS DISTRIBUTING")
    if top_sells:
        strongest_ask = max(top_sells, key=lambda x: x[1]["volume"] - x[1]["cancelled"])
        print(
            f"   → Primary resistance: {strongest_ask[0]:.2f} ({strongest_ask[1]['volume']:.0f} contracts)"
        )
        if len(top_sells) >= 3:
            resistance_zone_low = min(p for p, _ in top_sells[:3])
            resistance_zone_high = max(p for p, _ in top_sells[:3])
            print(
                f"   → Resistance zone: {resistance_zone_low:.2f} - {resistance_zone_high:.2f}"
            )
    print("   → Strategy: Look for SHORT entries on rallies to institutional offers")
    print("   → Entry: Near high-conviction ask zones (low cancellation ratio)")
    print("   → Stop: Above highest significant ask level")
    if sell_pull_ratio > 40:
        print(
            f"   ⚠️  WARNING: High SELL cancellation rate ({sell_pull_ratio:.0f}%) - may indicate spoofing"
        )

print(f"\n{'='*100}")

cursor.close()
conn.close()
