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
cursor = conn.cursor()

# Get data from last hour with institutional size filter (>15 contracts)
one_hour_ago = datetime.now(pytz.UTC) - timedelta(hours=1)

query = """
SELECT 
    timestamp,
    symbol,
    price,
    size,
    side,
    action,
    order_id
FROM mbo_data
WHERE timestamp >= %s
  AND size > 15
ORDER BY timestamp DESC
LIMIT 500;
"""

cursor.execute(query, (one_hour_ago,))
rows = cursor.fetchall()

print(f"\n{'='*80}")
print(f"INSTITUTIONAL MBO ANALYSIS - Last Hour (Size > 15 contracts)")
print(f"{'='*80}")
print(f"Total institutional orders: {len(rows)}")
print(f"Analysis time: {datetime.now()}")
print(f"Data from: {one_hour_ago} to now")
print(f"{'='*80}\n")

if len(rows) == 0:
    print("⚠ No MBO data found in last hour with size > 15")
    print("Possible reasons:")
    print("  1. MBO consumer not running")
    print("  2. Market closed or very quiet")
    print("  3. No institutional-sized orders (>15 contracts)")
    cursor.close()
    conn.close()
    exit()

# Analyze by side and action
buy_adds = [r for r in rows if r[4] == "BUY" and r[5] == "ADD"]
sell_adds = [r for r in rows if r[4] == "SELL" and r[5] == "ADD"]
buy_deletes = [r for r in rows if r[4] == "BUY" and r[5] == "DELETE"]
sell_deletes = [r for r in rows if r[4] == "SELL" and r[5] == "DELETE"]

# Calculate volumes
buy_volume = sum(r[3] for r in buy_adds)
sell_volume = sum(r[3] for r in sell_adds)
buy_pulled = sum(r[3] for r in buy_deletes if r[3] > 0)
sell_pulled = sum(r[3] for r in sell_deletes if r[3] > 0)

print("📊 VOLUME ANALYSIS")
print(f"{'─'*80}")
print(
    f"  Institutional BUY orders placed:   {len(buy_adds):4d} orders | {buy_volume:8.1f} contracts"
)
print(
    f"  Institutional SELL orders placed:  {len(sell_adds):4d} orders | {sell_volume:8.1f} contracts"
)
print(
    f"  BUY orders pulled/cancelled:       {len(buy_deletes):4d} orders | {buy_pulled:8.1f} contracts"
)
print(
    f"  SELL orders pulled/cancelled:      {len(sell_deletes):4d} orders | {sell_pulled:8.1f} contracts"
)
print(f"{'─'*80}")

# Net positioning
net_buy = buy_volume - buy_pulled
net_sell = sell_volume - sell_pulled
net_delta = net_buy - net_sell

print(f"\n💰 NET INSTITUTIONAL POSITIONING")
print(f"{'─'*80}")
print(f"  Net BUY liquidity:   {net_buy:8.1f} contracts")
print(f"  Net SELL liquidity:  {net_sell:8.1f} contracts")
print(f"  NET DELTA:           {net_delta:+8.1f} contracts")
print(f"{'─'*80}")

# Determine bias
if abs(net_delta) < 50:
    bias = "NEUTRAL ⚖️"
    signal = "NO CLEAR DIRECTION - Wait for confirmation"
elif net_delta > 0:
    bias = "BULLISH 🟢"
    signal = "Institutions ACCUMULATING on BID - Look for LONG entries"
else:
    bias = "BEARISH 🔴"
    signal = "Institutions DISTRIBUTING on ASK - Look for SHORT entries"

print(f"\n🎯 TRADING BIAS: {bias}")
print(f"📡 SIGNAL: {signal}")
print(f"{'='*80}\n")

# Find key price levels (top 10 by activity)
print("📍 KEY INSTITUTIONAL PRICE LEVELS")
print(f"{'─'*80}")

# Group by price for BUY side
buy_prices = {}
for r in buy_adds:
    price = round(r[2], 2)
    if price not in buy_prices:
        buy_prices[price] = {"count": 0, "volume": 0}
    buy_prices[price]["count"] += 1
    buy_prices[price]["volume"] += r[3]

# Group by price for SELL side
sell_prices = {}
for r in sell_adds:
    price = round(r[2], 2)
    if price not in sell_prices:
        sell_prices[price] = {"count": 0, "volume": 0}
    sell_prices[price]["count"] += 1
    sell_prices[price]["volume"] += r[3]

print("\n🟢 TOP INSTITUTIONAL BUY ZONES (Size > 15)")
print(f"{'Price':<12} {'Orders':<10} {'Volume':<12} {'Avg Size':<10}")
print(f"{'─'*50}")
top_buys = sorted(buy_prices.items(), key=lambda x: x[1]["volume"], reverse=True)[:10]
for price, data in top_buys:
    avg_size = data["volume"] / data["count"]
    print(
        f"{price:<12.2f} {data['count']:<10d} {data['volume']:<12.1f} {avg_size:<10.1f}"
    )

print(f"\n🔴 TOP INSTITUTIONAL SELL ZONES (Size > 15)")
print(f"{'Price':<12} {'Orders':<10} {'Volume':<12} {'Avg Size':<10}")
print(f"{'─'*50}")
top_sells = sorted(sell_prices.items(), key=lambda x: x[1]["volume"], reverse=True)[:10]
for price, data in top_sells:
    avg_size = data["volume"] / data["count"]
    print(
        f"{price:<12.2f} {data['count']:<10d} {data['volume']:<12.1f} {avg_size:<10.1f}"
    )

# Find largest single orders (whales)
print(f"\n🐋 LARGEST INSTITUTIONAL ORDERS (Whales)")
print(f"{'─'*80}")
print(f"{'Time':<20} {'Side':<6} {'Action':<8} {'Price':<12} {'Size':<10}")
print(f"{'─'*80}")
largest = sorted(rows, key=lambda x: x[3], reverse=True)[:15]
for r in largest:
    time_str = r[0].strftime("%H:%M:%S") if r[0] else "N/A"
    side = r[4]
    action = r[5]
    price = r[2]
    size = r[3]
    emoji = "🟢" if side == "BUY" else "🔴"
    print(f"{time_str:<20} {emoji} {side:<6} {action:<8} {price:<12.2f} {size:<10.1f}")

print(f"\n{'='*80}")
print("📌 TRADING RECOMMENDATIONS:")
print(f"{'='*80}")

if net_delta > 100:
    print("✅ STRONG BULLISH SETUP")
    if top_buys:
        print(
            f"   → Watch for price to return to {top_buys[0][0]:.2f} (highest bid activity)"
        )
        print(
            f"   → Support zone: {min(p for p, _ in top_buys[:3]):.2f} - {max(p for p, _ in top_buys[:3]):.2f}"
        )
    print("   → Strategy: Look for LONG entries on pullbacks to institutional bids")
    print("   → Stop: Below lowest institutional buy zone")
elif net_delta < -100:
    print("✅ STRONG BEARISH SETUP")
    if top_sells:
        print(
            f"   → Watch for price to rally to {top_sells[0][0]:.2f} (highest ask activity)"
        )
        print(
            f"   → Resistance zone: {min(p for p, _ in top_sells[:3]):.2f} - {max(p for p, _ in top_sells[:3]):.2f}"
        )
    print("   → Strategy: Look for SHORT entries on rallies to institutional offers")
    print("   → Stop: Above highest institutional sell zone")
else:
    print("⚠️ MIXED SIGNALS - NO CLEAR INSTITUTIONAL BIAS")
    print("   → Wait for clearer positioning before entering")
    print("   → Monitor for order flow imbalances at key levels")

cursor.close()
conn.close()
