#!/usr/bin/env python3
"""
Optimize iceberg detector to reach 90% accuracy
Analyze false positives to find better discrimination features
"""
import psycopg2
from datetime import datetime
from collections import defaultdict

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}


def analyze_false_positives(start_time, end_time):
    """Compare characteristics of true vs false positives"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("=" * 80)
    print("ANALYZING FALSE POSITIVES TO IMPROVE PRECISION")
    print("=" * 80)

    # Get all actual icebergs
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
        AND timestamp >= %s AND timestamp < %s
        AND symbol LIKE 'MNQ%%'
        ORDER BY timestamp
    """,
        (start_time, end_time),
    )

    actual_icebergs = cursor.fetchall()
    print(f"\nActual icebergs: {len(actual_icebergs)}")

    # Get all TRADE events
    cursor.execute(
        """
        SELECT 
            timestamp,
            price,
            side,
            size
        FROM mbo_data
        WHERE timestamp >= %s AND timestamp < %s
        AND action = 'TRADE'
        AND symbol LIKE 'MNQ%%'
        ORDER BY timestamp, price
    """,
        (start_time, end_time),
    )

    trades = cursor.fetchall()
    print(f"Total TRADE events: {len(trades):,}")

    # Analyze characteristics of true icebergs
    true_bursts = []
    false_bursts = []

    # Find trade bursts
    bursts = []
    current_burst = []
    burst_start_time = None
    burst_price = None
    burst_side = None

    for trade in trades:
        ts, price, side, size = trade

        if not current_burst:
            current_burst = [trade]
            burst_start_time = ts
            burst_price = price
            burst_side = side
            continue

        time_diff_ms = (ts - burst_start_time).total_seconds() * 1000
        price_diff = abs(price - burst_price)

        if time_diff_ms <= 10 and price_diff <= 0.25 and side == burst_side:
            current_burst.append(trade)
        else:
            if len(current_burst) >= 5:  # Lower threshold to catch more
                total_size = sum(t[3] for t in current_burst)
                time_span = (
                    current_burst[-1][0] - burst_start_time
                ).total_seconds() * 1000

                # Calculate statistics
                sizes = [t[3] for t in current_burst]
                avg_size = total_size / len(current_burst)
                zero_size_count = sum(1 for s in sizes if s == 0)

                burst_info = {
                    "timestamp": burst_start_time,
                    "price": burst_price,
                    "side": burst_side,
                    "trade_count": len(current_burst),
                    "total_size": total_size,
                    "avg_size": avg_size,
                    "duration_ms": time_span,
                    "zero_sizes": zero_size_count,
                    "zero_ratio": (
                        zero_size_count / len(current_burst)
                        if len(current_burst) > 0
                        else 0
                    ),
                }

                # Check if matches actual iceberg
                is_match = False
                for act_time, act_price, act_side, _, _ in actual_icebergs:
                    time_diff = abs((burst_start_time - act_time).total_seconds())
                    price_diff_check = abs(burst_price - act_price)
                    if (
                        time_diff <= 5
                        and price_diff_check <= 1.0
                        and burst_side == act_side
                    ):
                        is_match = True
                        break

                if is_match:
                    true_bursts.append(burst_info)
                else:
                    false_bursts.append(burst_info)

                bursts.append((burst_info, is_match))

            current_burst = [trade]
            burst_start_time = ts
            burst_price = price
            burst_side = side

    print(f"\nBurst Analysis:")
    print(f"  True Positives (iceberg bursts): {len(true_bursts)}")
    print(f"  False Positives (non-iceberg bursts): {len(false_bursts)}")

    # Compare characteristics
    if true_bursts and false_bursts:
        print("\n" + "=" * 80)
        print("FEATURE COMPARISON: TRUE vs FALSE POSITIVES")
        print("=" * 80)

        def calc_stats(burst_list, feature):
            values = [b[feature] for b in burst_list]
            return {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "median": sorted(values)[len(values) // 2],
            }

        features = [
            "trade_count",
            "total_size",
            "avg_size",
            "duration_ms",
            "zero_ratio",
        ]

        for feature in features:
            true_stats = calc_stats(true_bursts, feature)
            false_stats = calc_stats(false_bursts, feature)

            print(f"\n{feature.upper()}:")
            print(
                f"  TRUE:  min={true_stats['min']:.2f}, avg={true_stats['avg']:.2f}, "
                f"median={true_stats['median']:.2f}, max={true_stats['max']:.2f}"
            )
            print(
                f"  FALSE: min={false_stats['min']:.2f}, avg={false_stats['avg']:.2f}, "
                f"median={false_stats['median']:.2f}, max={false_stats['max']:.2f}"
            )

            # Suggest threshold
            if true_stats["median"] > false_stats["median"]:
                threshold = (true_stats["median"] + false_stats["median"]) / 2
                print(f"  → THRESHOLD: >= {threshold:.2f} (higher is better)")
            else:
                threshold = (true_stats["median"] + false_stats["median"]) / 2
                print(f"  → THRESHOLD: <= {threshold:.2f} (lower is better)")

    cursor.close()
    conn.close()

    return true_bursts, false_bursts


def test_optimized_detector(
    start_time, end_time, min_trades, min_size, max_duration, max_zero_ratio
):
    """Test detector with optimized thresholds"""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("\n" + "=" * 80)
    print("TESTING OPTIMIZED DETECTOR")
    print("=" * 80)
    print(f"Thresholds:")
    print(f"  Min trades: {min_trades}")
    print(f"  Min total size: {min_size}")
    print(f"  Max duration: {max_duration}ms")
    print(f"  Max zero ratio: {max_zero_ratio:.1%}")

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

    # Find bursts with new thresholds
    candidates = []
    current_burst = []
    burst_start_time = None
    burst_price = None
    burst_side = None

    for trade in trades:
        ts, price, side, size = trade

        if not current_burst:
            current_burst = [trade]
            burst_start_time = ts
            burst_price = price
            burst_side = side
            continue

        time_diff_ms = (ts - burst_start_time).total_seconds() * 1000
        price_diff = abs(price - burst_price)

        if time_diff_ms <= 10 and price_diff <= 0.25 and side == burst_side:
            current_burst.append(trade)
        else:
            if len(current_burst) >= min_trades:
                total_size = sum(t[3] for t in current_burst)
                time_span = (
                    current_burst[-1][0] - burst_start_time
                ).total_seconds() * 1000
                zero_count = sum(1 for t in current_burst if t[3] == 0)
                zero_ratio = zero_count / len(current_burst)

                if (
                    total_size >= min_size
                    and time_span <= max_duration
                    and zero_ratio <= max_zero_ratio
                ):
                    candidates.append(
                        {
                            "timestamp": burst_start_time,
                            "price": burst_price,
                            "side": burst_side,
                            "trade_count": len(current_burst),
                            "total_size": total_size,
                        }
                    )

            current_burst = [trade]
            burst_start_time = ts
            burst_price = price
            burst_side = side

    # Get actual icebergs
    cursor.execute(
        """
        SELECT timestamp, price, side, detected_size
        FROM stops_icebergs
        WHERE event_type = 'ICEBERG'
        AND iceberg_subtype = 'DETECTION'
        AND timestamp >= %s AND timestamp < %s
        AND symbol LIKE 'MNQ%%'
    """,
        (start_time, end_time),
    )

    actual_icebergs = cursor.fetchall()

    # Match candidates to actuals
    matches = 0
    matched_actuals = set()

    for candidate in candidates:
        for i, (act_time, act_price, act_side, _) in enumerate(actual_icebergs):
            if i in matched_actuals:
                continue

            time_diff = abs((candidate["timestamp"] - act_time).total_seconds())
            price_diff = abs(candidate["price"] - act_price)

            if time_diff <= 5 and price_diff <= 1.0 and candidate["side"] == act_side:
                matches += 1
                matched_actuals.add(i)
                break

    false_positives = len(candidates) - matches
    false_negatives = len(actual_icebergs) - matches

    print(f"\nResults:")
    print(f"  Candidates detected: {len(candidates)}")
    print(f"  Actual icebergs: {len(actual_icebergs)}")
    print(f"  True Positives: {matches}")
    print(f"  False Positives: {false_positives}")
    print(f"  False Negatives: {false_negatives}")

    if len(actual_icebergs) > 0:
        recall = matches / len(actual_icebergs) * 100
        print(f"  Recall: {recall:.1f}%")

    if len(candidates) > 0:
        precision = matches / len(candidates) * 100
        print(f"  Precision: {precision:.1f}%")

        if len(actual_icebergs) > 0:
            f1 = 2 * (precision * recall) / (precision + recall)
            print(f"  F1 Score: {f1:.1f}%")

    cursor.close()
    conn.close()

    return precision, recall


if __name__ == "__main__":
    start = datetime.fromisoformat("2025-11-17 09:00:00")
    end = datetime.fromisoformat("2025-11-17 12:00:00")

    # Step 1: Analyze characteristics
    print("STEP 1: Analyzing burst characteristics...")
    true_bursts, false_bursts = analyze_false_positives(start, end)

    # Step 2: Test different threshold combinations
    print("\n" + "=" * 80)
    print("STEP 2: Testing threshold combinations...")
    print("=" * 80)

    best_precision = 0
    best_params = None

    # Test configurations
    configs = [
        (10, 10, 8, 0.3),  # Stricter
        (12, 12, 6, 0.2),  # Very strict
        (15, 15, 5, 0.15),  # Extremely strict
        (20, 20, 4, 0.1),  # Maximum strictness
    ]

    for min_trades, min_size, max_duration, max_zero_ratio in configs:
        precision, recall = test_optimized_detector(
            start, end, min_trades, min_size, max_duration, max_zero_ratio
        )

        if precision >= 90 and recall >= 50:  # Target: 90% precision, reasonable recall
            print(f"\n✓ TARGET ACHIEVED!")
            best_precision = precision
            best_params = (min_trades, min_size, max_duration, max_zero_ratio)
            break

        if precision > best_precision:
            best_precision = precision
            best_params = (min_trades, min_size, max_duration, max_zero_ratio)

    if best_params:
        print("\n" + "=" * 80)
        print("BEST CONFIGURATION")
        print("=" * 80)
        print(f"Min trades: {best_params[0]}")
        print(f"Min size: {best_params[1]}")
        print(f"Max duration: {best_params[2]}ms")
        print(f"Max zero ratio: {best_params[3]:.1%}")
        print(f"Precision: {best_precision:.1f}%")
