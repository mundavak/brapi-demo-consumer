#!/usr/bin/env python3
"""
Iceberg Order Detection using Raw MBO Data

This script implements the classic iceberg detection algorithm:
1. Track order_id at each price level
2. Detect when same order_id refills at same price after partial fills
3. Calculate hidden size from refill pattern
4. Validate against Bookmap's detected icebergs

Key MBO Patterns for Icebergs:
- Add (A): Order placed on book
- Fill/Trade (F/T): Order executed
- Cancel (C): Order canceled
- Modify (M): Order size changed

Iceberg Pattern:
- Order added with size X
- Fills occur (size decreases)
- Order "refills" back to size X or Y (hidden liquidity revealed)
- This repeats multiple times at same price
"""
import psycopg2
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Tuple
import json

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}


@dataclass
class IcebergDetection:
    """Detected iceberg order"""

    order_id: int
    price: float
    side: str
    first_seen: datetime
    last_seen: datetime
    refill_count: int  # How many times order refilled
    total_filled: int  # Total contracts filled
    peak_visible_size: int  # Largest visible size
    estimated_total_size: int  # Estimated hidden + visible
    confidence: float
    evidence: List[str]

    def matches_actual(
        self,
        actual_timestamp: datetime,
        actual_price: float,
        actual_side: str,
        tolerance_seconds: int = 300,
        tolerance_ticks: float = 0.25,
    ) -> bool:
        """Check if this detection matches an actual iceberg"""
        # Time match
        time_diff = abs((self.first_seen - actual_timestamp).total_seconds())
        if time_diff > tolerance_seconds:
            return False

        # Price match
        price_diff = abs(self.price - actual_price)
        if price_diff > tolerance_ticks:
            return False

        # Side match
        if self.side != actual_side:
            return False

        return True


class MBOIcebergDetector:
    """Detect icebergs from raw MBO data"""

    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)

        # Detection thresholds
        self.MIN_REFILLS = 2  # Minimum refills to be considered iceberg
        self.MIN_TOTAL_FILLED = 5  # Minimum total contracts filled
        self.REFILL_THRESHOLD = 0.5  # Size must increase by 50%+ to be "refill"
        self.TIME_WINDOW = 600  # Max seconds between events for same iceberg

    def detect_icebergs(self, date: str, symbol: str = "MNQ") -> List[IcebergDetection]:
        """
        Detect icebergs from MBO data for a specific date

        Algorithm:
        1. Get all MBO events for the date, ordered by time
        2. Track each order_id's size changes
        3. Detect "refill" pattern: size increases after fills
        4. Count refills and total filled size
        5. Classify as iceberg if meets thresholds
        """
        print(f"\n{'=' * 80}")
        print(f"DETECTING ICEBERGS FROM RAW MBO DATA")
        print(f"{'=' * 80}")
        print(f"Date: {date}")
        print(f"Symbol: {symbol}")

        cursor = self.conn.cursor()

        # Query raw MBO data for the date
        # Focus on limit orders (ADD/UPDATE/DELETE/TRADE) at price levels
        query = """
            SELECT 
                timestamp,
                order_id,
                side,
                price,
                size,
                action
            FROM mbo_data
            WHERE timestamp >= %s::date AND timestamp < %s::date + INTERVAL '1 day'
            AND symbol LIKE %s
            AND action IN ('ADD', 'UPDATE', 'DELETE', 'TRADE')
            ORDER BY timestamp
            LIMIT 5000000
        """

        print(f"Querying MBO data (limit 5M events)...")
        cursor.execute(query, (date, date, f"{symbol}%"))

        # Process events to track order lifecycles
        order_states = (
            {}
        )  # order_id -> {current_size, fills, refills, price, side, timestamps}
        detections = []

        print(f"Processing MBO events...")
        row_count = 0

        for row in cursor:
            row_count += 1
            if row_count % 100000 == 0:
                print(
                    f"  Processed {row_count:,} events, detected {len(detections)} icebergs..."
                )

            timestamp, order_id, side, price, size, action = row

            # Skip invalid data
            if order_id is None or price is None or size is None:
                continue

            # Initialize order tracking
            if order_id not in order_states:
                order_states[order_id] = {
                    "price": price,
                    "side": side,
                    "current_size": 0,
                    "peak_size": 0,
                    "total_filled": 0,
                    "refill_count": 0,
                    "first_seen": timestamp,
                    "last_seen": timestamp,
                    "events": [],
                }

            state = order_states[order_id]
            state["last_seen"] = timestamp

            # Track event
            state["events"].append(
                {
                    "timestamp": timestamp,
                    "action": action,
                    "size": size,
                    "prev_size": state["current_size"],
                }
            )

            # Process action
            if action == "ADD":  # Add - new order on book
                state["current_size"] = size
                state["peak_size"] = max(state["peak_size"], size)

            elif action == "UPDATE":  # Modify - size change
                prev_size = state["current_size"]
                state["current_size"] = size

                # Detect refill: size increased significantly
                if size > prev_size * (1 + self.REFILL_THRESHOLD):
                    state["refill_count"] += 1

                state["peak_size"] = max(state["peak_size"], size)

            elif action == "TRADE":  # Trade - order executed
                filled_size = min(size, state["current_size"])
                state["total_filled"] += filled_size
                state["current_size"] = max(0, state["current_size"] - filled_size)

            elif action == "DELETE":  # Delete - order removed
                state["current_size"] = 0

        print(f"✓ Processed {row_count:,} MBO events")
        print(f"  Tracked {len(order_states):,} unique orders")

        # Analyze order states to find icebergs
        print(f"\nAnalyzing order patterns...")

        for order_id, state in order_states.items():
            # Check iceberg criteria
            if state["refill_count"] < self.MIN_REFILLS:
                continue

            if state["total_filled"] < self.MIN_TOTAL_FILLED:
                continue

            # Check time window
            duration = (state["last_seen"] - state["first_seen"]).total_seconds()
            if duration > self.TIME_WINDOW:
                # Check if refills were clustered
                refill_times = [
                    e["timestamp"]
                    for e in state["events"]
                    if e["action"] == "UPDATE" and e["size"] > e["prev_size"] * 1.5
                ]
                if len(refill_times) >= 2:
                    max_gap = max(
                        (refill_times[i] - refill_times[i - 1]).total_seconds()
                        for i in range(1, len(refill_times))
                    )
                    if max_gap > self.TIME_WINDOW:
                        continue  # Refills too spread out

            # Estimate total hidden size
            # Formula: peak_visible + (refill_count * avg_refill_size)
            avg_refill = state["peak_size"] / 2  # Conservative estimate
            estimated_total = state["peak_size"] + (state["refill_count"] * avg_refill)

            # Calculate confidence
            confidence = self._calculate_confidence(
                state["refill_count"],
                state["total_filled"],
                duration,
                len(state["events"]),
            )

            # Build evidence
            evidence = [
                f"{state['refill_count']} refills detected",
                f"{state['total_filled']} contracts filled",
                f"Peak visible: {state['peak_size']}",
                f"Duration: {duration:.1f}s",
                f"{len(state['events'])} total events",
            ]

            detection = IcebergDetection(
                order_id=order_id,
                price=state["price"],
                side=state["side"],
                first_seen=state["first_seen"],
                last_seen=state["last_seen"],
                refill_count=state["refill_count"],
                total_filled=state["total_filled"],
                peak_visible_size=state["peak_size"],
                estimated_total_size=int(estimated_total),
                confidence=confidence,
                evidence=evidence,
            )

            detections.append(detection)

        cursor.close()

        # Sort by confidence
        detections.sort(key=lambda x: x.confidence, reverse=True)

        print(f"✓ Detected {len(detections)} iceberg orders")
        return detections

    def _calculate_confidence(
        self, refill_count: int, total_filled: int, duration: float, event_count: int
    ) -> float:
        """Calculate detection confidence (0-100)"""
        # More refills = higher confidence
        refill_score = min(refill_count * 15, 40)

        # More fills = higher confidence
        fill_score = min(total_filled / 2, 30)

        # More events = more activity = higher confidence
        event_score = min(event_count / 5, 20)

        # Shorter duration = more aggressive = higher confidence
        if duration < 60:
            duration_score = 10
        elif duration < 300:
            duration_score = 5
        else:
            duration_score = 2

        total = refill_score + fill_score + event_score + duration_score
        return min(total, 100)

    def get_actual_icebergs(self, date: str, symbol: str = "MNQ") -> List[Dict]:
        """Get actual icebergs from database"""
        print(f"\n{'=' * 80}")
        print(f"LOADING ACTUAL ICEBERGS FROM DATABASE")
        print(f"{'=' * 80}")

        cursor = self.conn.cursor()

        query = """
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
            AND DATE(timestamp) = %s
            AND symbol LIKE %s
            AND iceberg_subtype = 'DETECTION'
            ORDER BY timestamp
        """

        cursor.execute(query, (date, f"{symbol}%"))
        rows = cursor.fetchall()

        icebergs = []
        for row in rows:
            timestamp, price, side, detected_size, est_total, subtype, confidence = row
            icebergs.append(
                {
                    "timestamp": timestamp,
                    "price": price,
                    "side": side,
                    "detected_size": detected_size,
                    "estimated_total_size": est_total,
                    "iceberg_subtype": subtype,
                    "confidence_score": confidence,
                }
            )

        cursor.close()

        print(f"✓ Loaded {len(icebergs)} actual iceberg DETECTION events")
        return icebergs

    def validate(self, detected: List[IcebergDetection], actual: List[Dict]) -> Dict:
        """Validate detections against actual"""
        print(f"\n{'=' * 80}")
        print(f"VALIDATION")
        print(f"{'=' * 80}")
        print(f"Detected: {len(detected)}")
        print(f"Actual: {len(actual)}")

        true_positives = 0
        false_positives = 0
        matched_actuals = set()
        matches = []

        for detection in detected:
            matched = False

            for i, actual_iceberg in enumerate(actual):
                if i in matched_actuals:
                    continue

                if detection.matches_actual(
                    actual_iceberg["timestamp"],
                    actual_iceberg["price"],
                    actual_iceberg["side"],
                ):
                    true_positives += 1
                    matched_actuals.add(i)
                    matched = True
                    matches.append((detection, actual_iceberg))
                    break

            if not matched:
                false_positives += 1

        false_negatives = len(actual) - true_positives

        precision = true_positives / len(detected) if detected else 0
        recall = true_positives / len(actual) if actual else 0
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        print(f"\nResults:")
        print(f"  True Positives: {true_positives}")
        print(f"  False Positives: {false_positives}")
        print(f"  False Negatives: {false_negatives}")
        print(f"\n  Precision: {precision*100:.1f}%")
        print(f"  Recall: {recall*100:.1f}%")
        print(f"  F1 Score: {f1*100:.1f}%")

        if matches:
            print(f"\n✓ Sample Matches:")
            for i, (det, act) in enumerate(matches[:3], 1):
                time_diff = abs((det.first_seen - act["timestamp"]).total_seconds())
                price_diff = abs(det.price - act["price"])
                print(f"\n  Match #{i}:")
                print(f"    Order ID: {det.order_id}")
                print(f"    Price: ${det.price:.2f} (diff: ${price_diff:.2f})")
                print(f"    Side: {det.side}")
                print(f"    Refills: {det.refill_count}")
                print(f"    Total Filled: {det.total_filled}")
                print(f"    Confidence: {det.confidence:.1f}")
                print(f"    Time diff: {time_diff:.1f}s")

        return {
            "true_positives": true_positives,
            "false_positives": false_positives,
            "false_negatives": false_negatives,
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "matches": matches,
        }

    def close(self):
        self.conn.close()


def main():
    import sys

    # Get date from command line or use default
    if len(sys.argv) >= 2:
        test_date = sys.argv[1]
    else:
        test_date = "2025-11-17"  # Recent date with MBO data

    print(f"{'=' * 80}")
    print(f"MBO ICEBERG DETECTION & VALIDATION")
    print(f"{'=' * 80}")
    print(f"Test Date: {test_date}")

    detector = MBOIcebergDetector()

    try:
        # Detect icebergs from raw MBO
        detected = detector.detect_icebergs(test_date)

        # Get actual icebergs
        actual = detector.get_actual_icebergs(test_date)

        # Validate
        results = detector.validate(detected, actual)

        # Summary
        print(f"\n{'=' * 80}")
        print(f"SUMMARY")
        print(f"{'=' * 80}")

        if results["f1_score"] >= 0.7:
            print(f"✓ EXCELLENT: F1 Score {results['f1_score']*100:.1f}%")
        elif results["f1_score"] >= 0.5:
            print(f"⚠ GOOD: F1 Score {results['f1_score']*100:.1f}%")
        else:
            print(f"✗ NEEDS WORK: F1 Score {results['f1_score']*100:.1f}%")

        if results["precision"] < 0.8:
            print(
                f"\nTip: Increase MIN_REFILLS or MIN_TOTAL_FILLED to reduce false positives"
            )
        if results["recall"] < 0.7:
            print(
                f"Tip: Decrease MIN_REFILLS or increase TIME_WINDOW to catch more icebergs"
            )

    finally:
        detector.close()


if __name__ == "__main__":
    main()
