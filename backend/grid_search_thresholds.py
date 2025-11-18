#!/usr/bin/env python3
"""
Aggressive threshold tuning to reach 90% precision
Focus on most distinctive iceberg characteristics
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


def test_detector(
    start_time, end_time, min_trades, min_size, max_duration, min_avg_size
):
    """Test detector with specific thresholds"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Get trades
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

    trades = cursor.fetchall()

    # Find bursts
    candidates = []
    current_burst = []
    burst_start = None
    burst_price = None
    burst_side = None

    for ts, price, side, size in trades:
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

    # Get actual icebergs
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

    actuals = cursor.fetchall()

    # Match with tighter window (1 second, $0.50)
    matches = 0
    matched = set()

    for cand_time, cand_price, cand_side in candidates:
        for i, (act_time, act_price, act_side) in enumerate(actuals):
            if i in matched:
                continue

            time_diff = abs((cand_time - act_time).total_seconds())
            price_diff = abs(cand_price - act_price)

            if time_diff <= 1 and price_diff <= 0.5 and cand_side == act_side:
                matches += 1
                matched.add(i)
                break

    precision = (matches / len(candidates) * 100) if candidates else 0
    recall = (matches / len(actuals) * 100) if actuals else 0

    cursor.close()
    conn.close()

    return len(candidates), len(actuals), matches, precision, recall


def grid_search():
    """Grid search for optimal parameters"""
    start = datetime.fromisoformat("2025-11-17 09:00:00")
    end = datetime.fromisoformat("2025-11-17 12:00:00")

    print("=" * 80)
    print("GRID SEARCH FOR 90% PRECISION")
    print("=" * 80)

    best_results = []

    # More aggressive parameter ranges
    for min_trades in [10, 12, 15, 18, 20, 25, 30]:
        for min_size in [10, 15, 20, 25, 30, 40, 50]:
            for max_duration in [3, 4, 5, 6]:
                for min_avg_size in [0.8, 1.0, 1.2, 1.5, 2.0]:

                    cand, act, matches, prec, rec = test_detector(
                        start, end, min_trades, min_size, max_duration, min_avg_size
                    )

                    # Target: 90%+ precision with reasonable recall (>20%)
                    if prec >= 90 and rec >= 20:
                        print(f"\n✓ TARGET ACHIEVED!")
                        print(
                            f"  trades>={min_trades}, size>={min_size}, "
                            f"duration<={max_duration}ms, avg_size>={min_avg_size}"
                        )
                        print(f"  Candidates: {cand}, Matches: {matches}")
                        print(f"  Precision: {prec:.1f}%, Recall: {rec:.1f}%")
                        best_results.append(
                            {
                                "params": (
                                    min_trades,
                                    min_size,
                                    max_duration,
                                    min_avg_size,
                                ),
                                "precision": prec,
                                "recall": rec,
                                "matches": matches,
                                "candidates": cand,
                            }
                        )

                    # Also track high precision results
                    elif prec >= 85 and rec >= 15:
                        best_results.append(
                            {
                                "params": (
                                    min_trades,
                                    min_size,
                                    max_duration,
                                    min_avg_size,
                                ),
                                "precision": prec,
                                "recall": rec,
                                "matches": matches,
                                "candidates": cand,
                            }
                        )

    # Show top results
    if best_results:
        best_results.sort(key=lambda x: (x["precision"], x["recall"]), reverse=True)

        print("\n" + "=" * 80)
        print("TOP 10 CONFIGURATIONS")
        print("=" * 80)

        for i, result in enumerate(best_results[:10], 1):
            params = result["params"]
            print(
                f"\n#{i}: Precision {result['precision']:.1f}%, Recall {result['recall']:.1f}%"
            )
            print(
                f"     trades>={params[0]}, size>={params[1]}, "
                f"dur<={params[2]}ms, avg>={params[3]}"
            )
            print(
                f"     {result['matches']} matches from {result['candidates']} candidates"
            )
    else:
        print("\nNo configuration achieved 85%+ precision with 15%+ recall")
        print("May need different approach or features")


if __name__ == "__main__":
    grid_search()
