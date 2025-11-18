#!/usr/bin/env python3
"""
Fast grid search with cached trade data
"""
import psycopg2
from datetime import datetime

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}

# Cache trade data globally
TRADES_CACHE = None
ACTUALS_CACHE = None


def load_data(start_time, end_time):
    """Load data once"""
    global TRADES_CACHE, ACTUALS_CACHE

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("Loading data...")
    cursor.execute(
        """
        SELECT timestamp, price, side, size
        FROM mbo_data
        WHERE timestamp >= %s AND timestamp < %s
        AND action = 'TRADE'
        AND symbol LIKE 'MNQ%%'
        ORDER BY timestamp, price
    """,
        (start_time, end_time),
    )
    TRADES_CACHE = cursor.fetchall()
    print(f"Loaded {len(TRADES_CACHE):,} trades")

    cursor.execute(
        """
        SELECT timestamp, price, side
        FROM stops_icebergs
        WHERE event_type = 'ICEBERG'
        AND iceberg_subtype = 'DETECTION'
        AND timestamp >= %s AND timestamp < %s
        AND symbol LIKE 'MNQ%%'
    """,
        (start_time, end_time),
    )
    ACTUALS_CACHE = cursor.fetchall()
    print(f"Loaded {len(ACTUALS_CACHE)} actual icebergs\n")

    cursor.close()
    conn.close()


def test_params(min_trades, min_size, max_duration, min_avg_size):
    """Test parameters on cached data"""
    candidates = []
    current_burst = []
    burst_start = None
    burst_price = None
    burst_side = None

    for ts, price, side, size in TRADES_CACHE:
        if not current_burst:
            current_burst = [(ts, size)]
            burst_start = ts
            burst_price = price
            burst_side = side
            continue

        time_diff_ms = (ts - burst_start).total_seconds() * 1000
        price_diff = abs(price - burst_price)

        if time_diff_ms <= 10 and price_diff <= 0.25 and side == burst_side:
            current_burst.append((ts, size))
        else:
            if len(current_burst) >= min_trades:
                total_size = sum(s for _, s in current_burst)
                duration = (current_burst[-1][0] - burst_start).total_seconds() * 1000
                avg_size = total_size / len(current_burst)

                if (
                    total_size >= min_size
                    and duration <= max_duration
                    and avg_size >= min_avg_size
                ):
                    candidates.append((burst_start, burst_price, burst_side))

            current_burst = [(ts, size)]
            burst_start = ts
            burst_price = price
            burst_side = side

    # Match candidates to actuals
    matches = 0
    matched = set()

    for cand_time, cand_price, cand_side in candidates:
        for i, (act_time, act_price, act_side) in enumerate(ACTUALS_CACHE):
            if i in matched:
                continue

            time_diff = abs((cand_time - act_time).total_seconds())
            price_diff = abs(cand_price - act_price)

            if time_diff <= 1 and price_diff <= 0.5 and cand_side == act_side:
                matches += 1
                matched.add(i)
                break

    precision = (matches / len(candidates) * 100) if candidates else 0
    recall = (matches / len(ACTUALS_CACHE) * 100) if ACTUALS_CACHE else 0

    return len(candidates), matches, precision, recall


def main():
    start = datetime.fromisoformat("2025-11-17 09:00:00")
    end = datetime.fromisoformat("2025-11-17 12:00:00")

    load_data(start, end)

    print("=" * 80)
    print("SEARCHING FOR 90% PRECISION")
    print("=" * 80)

    results = []
    test_count = 0

    # Test configurations
    for min_trades in [15, 18, 20, 25, 30, 35, 40, 50]:
        for min_size in [20, 25, 30, 40, 50, 60, 80, 100]:
            for max_duration in [3, 4, 5]:
                for min_avg_size in [1.0, 1.2, 1.5, 2.0, 2.5]:

                    test_count += 1
                    if test_count % 50 == 0:
                        print(f"Tested {test_count} configurations...")

                    cand, matches, prec, rec = test_params(
                        min_trades, min_size, max_duration, min_avg_size
                    )

                    if prec >= 85:  # High precision
                        results.append(
                            {
                                "trades": min_trades,
                                "size": min_size,
                                "duration": max_duration,
                                "avg_size": min_avg_size,
                                "precision": prec,
                                "recall": rec,
                                "matches": matches,
                                "candidates": cand,
                            }
                        )

                        if prec >= 90 and rec >= 15:
                            print(
                                f"\n✓ TARGET: trades≥{min_trades}, size≥{min_size}, "
                                f"dur≤{max_duration}ms, avg≥{min_avg_size}"
                            )
                            print(f"  Precision: {prec:.1f}%, Recall: {rec:.1f}%")
                            print(f"  {matches} matches from {cand} candidates")

    print(f"\nTotal configurations tested: {test_count}")

    if results:
        results.sort(key=lambda x: (x["precision"], x["recall"]), reverse=True)

        print("\n" + "=" * 80)
        print("TOP 15 RESULTS")
        print("=" * 80)

        for i, r in enumerate(results[:15], 1):
            print(f"\n#{i}: {r['precision']:.1f}% precision, {r['recall']:.1f}% recall")
            print(
                f"    trades≥{r['trades']}, size≥{r['size']}, "
                f"dur≤{r['duration']}ms, avg≥{r['avg_size']}"
            )
            print(f"    {r['matches']} matches / {r['candidates']} candidates")
    else:
        print("\nNo configurations achieved 85%+ precision")


if __name__ == "__main__":
    main()
