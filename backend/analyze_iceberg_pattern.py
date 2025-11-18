#!/usr/bin/env python3
"""
Detailed Iceberg Pattern Analysis
Look at individual order lifecycles to understand detection pattern
"""
import psycopg2
from datetime import timedelta

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}


def analyze_single_iceberg():
    """Analyze a specific iceberg detected by Bookmap to understand the pattern"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Get first iceberg
    cursor.execute(
        """
        SELECT 
            timestamp,
            price,
            side,
            detected_size,
            estimated_total_size
        FROM stops_icebergs
        WHERE event_type = 'ICEBERG'
        AND iceberg_subtype = 'DETECTION'
        AND timestamp >= '2025-11-17 09:00:00' 
        AND timestamp < '2025-11-17 10:00:00'
        AND symbol LIKE 'MNQ%'
        ORDER BY timestamp
        LIMIT 1
    """
    )

    iceberg = cursor.fetchone()
    if not iceberg:
        print("No icebergs found")
        return

    ice_time, ice_price, ice_side, ice_det, ice_est = iceberg

    print("=" * 80)
    print("ANALYZING ICEBERG PATTERN")
    print("=" * 80)
    print(f"Time: {ice_time}")
    print(f"Price: ${ice_price:.2f}")
    print(f"Side: {ice_side}")
    print(f"Detected Size: {ice_det:.0f}")
    print(f"Estimated Total: {ice_est:.0f}")

    # Find MBO events near this time/price
    time_before = ice_time - timedelta(seconds=30)
    time_after = ice_time + timedelta(seconds=30)
    price_low = ice_price - 1.0
    price_high = ice_price + 1.0

    print("\nSearching MBO events:")
    print(f"  Time: {time_before} to {time_after}")
    print(f"  Price: ${price_low:.2f} to ${price_high:.2f}")
    print(f"  Side: {ice_side}")

    cursor.execute(
        """
        SELECT 
            timestamp,
            order_id,
            action,
            price,
            size,
            side
        FROM mbo_data
        WHERE timestamp >= %s AND timestamp <= %s
        AND price >= %s AND price <= %s
        AND side = %s
        AND symbol LIKE 'MNQ%%'
        ORDER BY timestamp, order_id
        LIMIT 100
    """,
        (time_before, time_after, price_low, price_high, ice_side),
    )

    events = cursor.fetchall()
    print(f"\nFound {len(events)} MBO events")

    if len(events) > 0:
        print("\nMBO Event Timeline:")

        # Group by order_id
        orders = {}
        for event in events:
            ts, oid, action, price, size, side = event
            if oid not in orders:
                orders[oid] = []
            orders[oid].append(
                {"timestamp": ts, "action": action, "price": price, "size": size}
            )

        print(f"\nTracked {len(orders)} unique orders")

        # Analyze action patterns across all orders
        action_counts = {"ADD": 0, "DELETE": 0, "UPDATE": 0, "TRADE": 0}
        for order_events in orders.values():
            for e in order_events:
                action_counts[e["action"]] = action_counts.get(e["action"], 0) + 1

        print("\nAction Distribution in Window:")
        for action, count in action_counts.items():
            print(f"  {action}: {count}")

        # Show orders with interesting patterns
        interesting_orders = []
        for oid, order_events in orders.items():
            actions = [e["action"] for e in order_events]
            sizes = [e["size"] for e in order_events]

            # Count refills (UPDATE where size increases)
            refills = 0
            for i in range(1, len(order_events)):
                if order_events[i]["action"] == "UPDATE":
                    if order_events[i]["size"] > order_events[i - 1]["size"]:
                        refills += 1

            trades = actions.count("TRADE")
            updates = actions.count("UPDATE")

            # Include all orders with any activity
            if len(order_events) > 1 or trades > 0:
                interesting_orders.append(
                    {
                        "oid": oid,
                        "events": order_events,
                        "actions": actions,
                        "sizes": sizes,
                        "trades": trades,
                        "updates": updates,
                        "refills": refills,
                    }
                )

        # Sort by most interesting (trades first, then updates)
        interesting_orders.sort(
            key=lambda x: (x["trades"], x["updates"], x["refills"]), reverse=True
        )

        print(
            f"\nShowing top 15 orders (out of {len(interesting_orders)} with activity):"
        )
        for order in interesting_orders[:15]:
            print(f"\n  Order {order['oid']}:")
            print(f"    Actions: {' → '.join(order['actions'])}")
            print(f"    Sizes: {order['sizes']}")
            print(
                f"    Trades:{order['trades']} Updates:{order['updates']} Refills:{order['refills']}"
            )

            # Show timeline
            for e in order["events"]:
                print(
                    f"      {e['timestamp'].strftime('%H:%M:%S.%f')[:-3]} "
                    f"{e['action']:6} ${e['price']:.2f} size:{e['size']}"
                )

    cursor.close()
    conn.close()


if __name__ == "__main__":
    analyze_single_iceberg()
