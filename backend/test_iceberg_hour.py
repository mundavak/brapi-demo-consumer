#!/usr/bin/env python3
"""
Optimized Iceberg Detection Test
Focus on 1-hour window with tuned thresholds based on Bookmap's approach
"""
import psycopg2
from datetime import datetime, timedelta
import sys

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}


def test_hour_window(date: str, start_hour: int = 9, end_hour: int = 10):
    """
    Test detection on a specific hour window

    Bookmap Insights from code review:
    - They use isNativeIceberg flag from broker (we must infer it)
    - Alert threshold: 50 contracts within 10ms
    - Track: lifetimeTradedSize + remainedSize for total order size
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    start_time = f"{date} {start_hour:02d}:00:00"
    end_time = f"{date} {end_hour:02d}:00:00"

    print(f"{'=' * 80}")
    print(f"ANALYZING {start_time} to {end_time}")
    print(f"{'=' * 80}")

    # Get actual icebergs in this window
    cursor.execute(
        """
        SELECT 
            timestamp,
            price,
            side,
            detected_size,
            estimated_total_size,
            iceberg_subtype,
            confidence_score
        FROM stops_icebergs
        WHERE event_type = 'ICEBERG'
        AND iceberg_subtype = 'DETECTION'
        AND timestamp >= %s AND timestamp < %s
        AND symbol LIKE 'MNQ%%'
        ORDER BY timestamp
    """,
        (start_time, end_time),
    )

    actuals = cursor.fetchall()
    print(f"\nActual Icebergs Detected by Bookmap: {len(actuals)}")

    if len(actuals) > 0:
        print(f"\nSample Actual Icebergs:")
        for i, row in enumerate(actuals[:5], 1):
            timestamp, price, side, det_size, est_total, subtype, conf = row
            print(
                f"  {i}. {timestamp} | ${price:.2f} {side:4} | "
                f"detected:{det_size:.0f} estimated:{est_total:.0f} conf:{conf:.0f}"
            )

    # Analyze MBO patterns in this window
    print(f"\nAnalyzing MBO Data Patterns...")

    # Get order statistics
    cursor.execute(
        """
        SELECT 
            action,
            COUNT(*) as cnt,
            AVG(size) as avg_size,
            MAX(size) as max_size
        FROM mbo_data
        WHERE timestamp >= %s AND timestamp < %s
        AND symbol LIKE 'MNQ%%'
        GROUP BY action
        ORDER BY cnt DESC
    """,
        (start_time, end_time),
    )

    print(f"\nMBO Action Distribution:")
    for action, cnt, avg_size, max_size in cursor.fetchall():
        print(
            f"  {action:10} {cnt:8,} events | avg size:{avg_size:6.1f} max:{max_size:,.0f}"
        )

    # Find orders with multiple UPDATEs (potential refills)
    cursor.execute(
        """
        WITH order_updates AS (
            SELECT 
                order_id,
                COUNT(*) FILTER (WHERE action = 'UPDATE') as update_count,
                COUNT(*) FILTER (WHERE action = 'TRADE') as trade_count,
                MIN(timestamp) as first_seen,
                MAX(timestamp) as last_seen,
                AVG(price) as avg_price,
                MAX(size) as max_size,
                SUM(CASE WHEN action = 'TRADE' THEN size ELSE 0 END) as total_traded
            FROM mbo_data
            WHERE timestamp >= %s AND timestamp < %s
            AND symbol LIKE 'MNQ%%'
            GROUP BY order_id
            HAVING COUNT(*) FILTER (WHERE action = 'UPDATE') >= 2
            AND COUNT(*) FILTER (WHERE action = 'TRADE') >= 1
        )
        SELECT 
            order_id,
            update_count,
            trade_count,
            first_seen,
            last_seen,
            EXTRACT(EPOCH FROM (last_seen - first_seen)) as duration_sec,
            avg_price,
            max_size,
            total_traded
        FROM order_updates
        WHERE total_traded >= 5
        ORDER BY update_count DESC, trade_count DESC
        LIMIT 20
    """,
        (start_time, end_time),
    )

    iceberg_candidates = cursor.fetchall()
    print(f"\nPotential Iceberg Candidates (orders with 2+ UPDATEs + trades):")
    print(f"Found {len(iceberg_candidates)} candidates")

    if len(iceberg_candidates) > 0:
        print(f"\nTop Candidates:")
        for i, row in enumerate(iceberg_candidates[:10], 1):
            order_id, upd_cnt, trade_cnt, first, last, dur, price, max_sz, total = row
            print(f"  {i}. Order {order_id}")
            print(f"      Updates:{upd_cnt} Trades:{trade_cnt} Duration:{dur:.1f}s")
            print(
                f"      Price:${price:.2f} MaxSize:{max_sz:.0f} TotalTraded:{total:.0f}"
            )

    # Check if any candidates match actual icebergs
    print(f"\n{'=' * 80}")
    print(f"VALIDATION")
    print(f"{'=' * 80}")

    if len(actuals) > 0 and len(iceberg_candidates) > 0:
        print(f"\nMatching candidates to actual icebergs...")

        matches = 0
        for actual in actuals:
            act_time, act_price, act_side, *_ = actual

            for candidate in iceberg_candidates:
                _, _, _, cand_first, _, _, cand_price, *_ = candidate

                # Check time and price match
                time_diff = abs((act_time - cand_first).total_seconds())
                price_diff = abs(act_price - cand_price)

                if time_diff < 60 and price_diff < 0.5:
                    matches += 1
                    print(
                        f"  ✓ Match: Actual @ {act_time} ${act_price:.2f} ~ "
                        f"Candidate order @ ${cand_price:.2f}"
                    )
                    break

        print(f"\nMatched {matches} / {len(actuals)} actual icebergs")
        print(f"Detection Rate: {matches / len(actuals) * 100:.1f}%")

    cursor.close()
    conn.close()

    return len(actuals), len(iceberg_candidates)


def main():
    if len(sys.argv) >= 2:
        date = sys.argv[1]
    else:
        date = "2025-11-17"

    if len(sys.argv) >= 4:
        start_hour = int(sys.argv[2])
        end_hour = int(sys.argv[3])
    else:
        # Test morning session (9-12 ET)
        start_hour = 9
        end_hour = 12

    print(f"{'=' * 80}")
    print(f"ICEBERG DETECTION TEST - HOUR WINDOW ANALYSIS")
    print(f"{'=' * 80}")
    print(f"Date: {date}")
    print(f"Time Window: {start_hour}:00 - {end_hour}:00")
    print(f"\nBookmap Threshold (from code review): 50 contracts in 10ms")
    print(f"Our Strategy: Find orders with multiple UPDATEs + TRADEs")

    actuals, candidates = test_hour_window(date, start_hour, end_hour)

    print(f"\n{'=' * 80}")
    print(f"SUMMARY")
    print(f"{'=' * 80}")
    print(f"Bookmap Detected: {actuals} icebergs")
    print(f"Our Candidates: {candidates} orders")

    if candidates == 0 and actuals > 0:
        print(f"\n⚠ No candidates found - thresholds may be too strict")
        print(f"Try lowering threshold: 2+ UPDATEs → 1+ UPDATE")
    elif candidates > actuals * 2:
        print(f"\n⚠ Too many candidates - thresholds may be too loose")
        print(f"Try increasing threshold or add time window filter")
    else:
        print(f"\n✓ Reasonable detection ratio")


if __name__ == "__main__":
    main()
