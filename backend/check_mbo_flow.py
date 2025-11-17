"""
Check MBO data flow: Redis (hot) -> TimescaleDB (cold)
Verifies async Redis writer is working and data flows to TimescaleDB
"""

import redis
import psycopg2
from datetime import datetime, timedelta, timezone
import json

# Redis connection
redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)

# PostgreSQL connection
pg_conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="trading_data",
    user="postgres",
    password="X74Ot*BvtjgKuCBx",
)


def check_redis_mbo():
    """Check Redis for recent MBO data"""
    print("\n=== REDIS MBO DATA CHECK ===")

    # Check MBO orders (bid/ask sorted sets)
    symbols = ["MNQZ4", "MNQ"]  # Common symbols

    for symbol in symbols:
        bid_key = f"mbo:orders:{symbol}:bid"
        ask_key = f"mbo:orders:{symbol}:ask"

        bid_count = redis_client.zcard(bid_key)
        ask_count = redis_client.zcard(ask_key)

        if bid_count > 0 or ask_count > 0:
            print(f"\n✓ Symbol: {symbol}")
            print(f"  Bid orders: {bid_count}")
            print(f"  Ask orders: {ask_count}")

            # Sample a few orders from each side
            if bid_count > 0:
                sample_bids = redis_client.zrange(bid_key, 0, 2, withscores=True)
                print(f"  Sample bid orders (price: order):")
                for order_json, price in sample_bids:
                    order = json.loads(order_json)
                    print(
                        f"    ${price:.2f}: {order['order_id']} | size={order['size']:.2f} | {order['event_type']}"
                    )

            if ask_count > 0:
                sample_asks = redis_client.zrange(ask_key, 0, 2, withscores=True)
                print(f"  Sample ask orders (price: order):")
                for order_json, price in sample_asks:
                    order = json.loads(order_json)
                    print(
                        f"    ${price:.2f}: {order['order_id']} | size={order['size']:.2f} | {order['event_type']}"
                    )

    # Check MBO trades stream
    for symbol in symbols:
        trade_key = f"mbo:trades:{symbol}"
        trade_count = redis_client.xlen(trade_key)

        if trade_count > 0:
            print(f"\n✓ Trade stream: {trade_key}")
            print(f"  Total trades: {trade_count}")

            # Get last 3 trades
            trades = redis_client.xrevrange(trade_key, count=3)
            print(f"  Last 3 trades:")
            for trade_id, trade_data in trades:
                print(
                    f"    {trade_id}: price=${trade_data.get('price', 'N/A')} | size={trade_data.get('size', 'N/A')} | aggressor={trade_data.get('is_bid_aggressor', 'N/A')}"
                )

    # Check MBO stats
    for symbol in symbols:
        stats_key = f"mbo:stats:{symbol}"
        if redis_client.exists(stats_key):
            stats = redis_client.hgetall(stats_key)
            if stats:
                print(f"\n✓ MBO Stats: {symbol}")
                print(f"  Session: {stats.get('session_id', 'N/A')}")
                print(f"  MBO events: {stats.get('mbo_count', 0)}")
                print(f"  Trades: {stats.get('trade_count', 0)}")
                print(
                    f"  Depth: {stats.get('depth_count', 0)} (should be 0 - disabled for performance)"
                )
                print(f"  Last update: {stats.get('last_update', 'N/A')}")


def check_timescale_mbo():
    """Check TimescaleDB for recent MBO data"""
    print("\n\n=== TIMESCALEDB MBO DATA CHECK ===")

    cursor = pg_conn.cursor()

    # Check last 5 minutes of MBO data
    five_min_ago = datetime.now() - timedelta(minutes=5)

    # Count by action type
    cursor.execute(
        """
        SELECT action, data_type, COUNT(*) as count
        FROM mbo_data
        WHERE timestamp >= %s
        GROUP BY action, data_type
        ORDER BY count DESC
    """,
        (five_min_ago,),
    )

    results = cursor.fetchall()

    if results:
        print(f"\n✓ MBO data in last 5 minutes:")
        total = 0
        for action, data_type, count in results:
            print(f"  {data_type}/{action}: {count:,} events")
            total += count
        print(f"  TOTAL: {total:,} events")
    else:
        print("\n⚠ NO MBO data found in last 5 minutes")

    # Get most recent events
    cursor.execute(
        """
        SELECT timestamp, symbol, action, data_type, side, price, size
        FROM mbo_data
        ORDER BY timestamp DESC
        LIMIT 10
    """
    )

    recent = cursor.fetchall()

    if recent:
        print(f"\n✓ Most recent 10 MBO events:")
        for ts, symbol, action, dtype, side, price, size in recent:
            print(
                f"  {ts} | {symbol} | {dtype}/{action} | {side} | ${price:.2f} x {size:.2f}"
            )

    # Check time since last event
    cursor.execute("SELECT MAX(timestamp) FROM mbo_data")
    last_ts = cursor.fetchone()[0]

    if last_ts:
        time_diff = datetime.now(timezone.utc) - last_ts
        seconds_ago = time_diff.total_seconds()
        print(f"\n⏱ Last MBO event: {seconds_ago:.1f} seconds ago")

        if seconds_ago < 60:
            print("  ✓ Data is FLOWING (within last minute)")
        elif seconds_ago < 300:
            print("  ⚠ Data may be stale (over 1 minute old)")
        else:
            print("  ❌ Data is NOT flowing (over 5 minutes old)")

    cursor.close()


def check_redis_queue_health():
    """Check if Redis async writer is keeping up"""
    print("\n\n=== REDIS ASYNC WRITER HEALTH ===")

    # Check all MBO-related keys
    pattern = "mbo:*"
    keys = redis_client.keys(pattern)

    print(f"✓ Total Redis MBO keys: {len(keys)}")

    # Group by type
    key_types = {}
    for key in keys:
        key_type = key.split(":")[1] if ":" in key else "unknown"
        key_types[key_type] = key_types.get(key_type, 0) + 1

    print(f"  Key types:")
    for ktype, count in key_types.items():
        print(f"    {ktype}: {count}")

    # Check memory usage
    info = redis_client.info("memory")
    used_memory_mb = info["used_memory"] / (1024 * 1024)
    print(f"\n✓ Redis memory usage: {used_memory_mb:.2f} MB")


if __name__ == "__main__":
    try:
        print("=" * 60)
        print("MBO DATA FLOW VERIFICATION")
        print("Checking Redis (hot) -> TimescaleDB (cold) pipeline")
        print("=" * 60)

        check_redis_mbo()
        check_timescale_mbo()
        check_redis_queue_health()

        print("\n" + "=" * 60)
        print("CHECK COMPLETE")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
    finally:
        redis_client.close()
        pg_conn.close()
