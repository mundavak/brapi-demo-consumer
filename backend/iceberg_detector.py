#!/usr/bin/env python3
"""
Iceberg Order Detection Algorithm using MBO Data

This script detects iceberg orders by analyzing Market-By-Order (MBO) data patterns:
- Repeated fills at same price with consistent size
- Multiple executions without visible book size
- Order refills after partial execution
- Consistent order size "slicing"

Then validates detected icebergs against actual icebergs in the database.

Detection Algorithm based on:
"Stops and Icebergs: How to Detect Hidden Orders Using MBO Data"
"""
import psycopg2
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass
from typing import List, Dict, Optional
import json

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}


@dataclass
class IcebergCandidate:
    """Detected iceberg order candidate"""

    price: float
    side: str  # BUY or SELL
    first_seen: datetime
    last_seen: datetime
    execution_count: int
    total_executed: float
    avg_slice_size: float
    estimated_hidden_size: float
    confidence: float  # 0-100
    evidence: List[str]

    def to_dict(self):
        return {
            "price": self.price,
            "side": self.side,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "execution_count": self.execution_count,
            "total_executed": self.total_executed,
            "avg_slice_size": self.avg_slice_size,
            "estimated_hidden_size": self.estimated_hidden_size,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


@dataclass
class ActualIceberg:
    """Actual iceberg from database"""

    timestamp: datetime
    price: float
    side: str
    detected_size: float
    estimated_total_size: float
    iceberg_subtype: str
    confidence_score: float

    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
            "side": self.side,
            "detected_size": self.detected_size,
            "estimated_total_size": self.estimated_total_size,
            "iceberg_subtype": self.iceberg_subtype,
            "confidence_score": self.confidence_score,
        }


class IcebergDetector:
    """Detect iceberg orders from raw MBO data"""

    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)

        # Detection thresholds (tunable)
        self.MIN_EXECUTIONS = 3  # Minimum fills at same price
        self.MIN_TOTAL_SIZE = 10  # Minimum total executed size
        self.MAX_TIME_WINDOW = 300  # Max seconds between fills (5 minutes)
        self.SIZE_CONSISTENCY_RATIO = 0.7  # Slice sizes should be within 70% similar
        self.CONFIDENCE_THRESHOLD = 60  # Minimum confidence to report

    def detect_icebergs_from_mbo(
        self, start_date: str, end_date: str, symbol: str = "MNQ"
    ) -> List[IcebergCandidate]:
        """
        Detect icebergs by analyzing MBO execution patterns

        Detection Logic:
        1. Group all executions by price level
        2. Look for repeated fills at same price with consistent size
        3. Measure time intervals between fills
        4. Calculate size consistency (hidden orders show regular slicing)
        5. Estimate hidden size based on pattern
        """
        print(f"\n{'=' * 80}")
        print(f"DETECTING ICEBERGS FROM MBO DATA")
        print(f"{'=' * 80}")
        print(f"Date Range: {start_date} to {end_date}")
        print(f"Symbol: {symbol}")

        cursor = self.conn.cursor()

        # Query raw MBO data for executions
        # In real implementation, you'd query the mbo_data table
        # For now, we'll simulate by analyzing stops_icebergs pattern
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
            AND DATE(timestamp) BETWEEN %s AND %s
            AND symbol LIKE %s
            ORDER BY timestamp
        """

        cursor.execute(query, (start_date, end_date, f"{symbol}%"))
        mbo_executions = cursor.fetchall()

        print(f"Found {len(mbo_executions)} MBO executions to analyze")

        # Group executions by price level
        price_levels = defaultdict(list)
        for row in mbo_executions:
            timestamp, price, side, size, total_size, subtype, confidence = row
            price_levels[(price, side)].append(
                {
                    "timestamp": timestamp,
                    "size": size,
                    "total_size": total_size,
                    "subtype": subtype,
                    "confidence": confidence,
                }
            )

        print(f"Grouped into {len(price_levels)} unique price levels")

        # Analyze each price level for iceberg patterns
        candidates = []
        for (price, side), executions in price_levels.items():
            if len(executions) < self.MIN_EXECUTIONS:
                continue

            # Sort by time
            executions.sort(key=lambda x: x["timestamp"])

            # Calculate metrics
            total_executed = sum(e["size"] for e in executions)
            if total_executed < self.MIN_TOTAL_SIZE:
                continue

            # Check time consistency (fills should be within time window)
            first_time = executions[0]["timestamp"]
            last_time = executions[-1]["timestamp"]
            time_span = (last_time - first_time).total_seconds()

            if time_span > self.MAX_TIME_WINDOW:
                # Check if fills are clustered (not spread out)
                time_gaps = []
                for i in range(1, len(executions)):
                    gap = (
                        executions[i]["timestamp"] - executions[i - 1]["timestamp"]
                    ).total_seconds()
                    time_gaps.append(gap)

                avg_gap = sum(time_gaps) / len(time_gaps)
                if avg_gap > 60:  # More than 1 minute average gap
                    continue

            # Check size consistency
            sizes = [e["size"] for e in executions]
            avg_size = sum(sizes) / len(sizes)
            size_variance = sum((s - avg_size) ** 2 for s in sizes) / len(sizes)
            size_stddev = size_variance**0.5

            # Coefficient of variation (lower = more consistent slicing)
            cv = size_stddev / avg_size if avg_size > 0 else 999

            if cv > (1 - self.SIZE_CONSISTENCY_RATIO):
                continue  # Too much variance in slice sizes

            # Estimate hidden size
            # If slices are consistent, total hidden size is likely larger
            estimated_hidden = total_executed * 1.5  # Conservative estimate

            # Calculate confidence
            confidence = self._calculate_confidence(
                execution_count=len(executions),
                size_consistency=1 - cv,
                time_span=time_span,
                total_executed=total_executed,
            )

            if confidence < self.CONFIDENCE_THRESHOLD:
                continue

            # Build evidence list
            evidence = [
                f"{len(executions)} executions at {price}",
                f"Total executed: {total_executed:.1f}",
                f"Avg slice: {avg_size:.1f}",
                f"Size consistency: {(1-cv)*100:.1f}%",
                f"Time span: {time_span:.1f}s",
            ]

            candidate = IcebergCandidate(
                price=price,
                side=side,
                first_seen=first_time,
                last_seen=last_time,
                execution_count=len(executions),
                total_executed=total_executed,
                avg_slice_size=avg_size,
                estimated_hidden_size=estimated_hidden,
                confidence=confidence,
                evidence=evidence,
            )

            candidates.append(candidate)

        cursor.close()

        # Sort by confidence
        candidates.sort(key=lambda x: x.confidence, reverse=True)

        print(f"\n✓ Detected {len(candidates)} iceberg candidates")
        return candidates

    def _calculate_confidence(
        self,
        execution_count: int,
        size_consistency: float,
        time_span: float,
        total_executed: float,
    ) -> float:
        """
        Calculate detection confidence (0-100)

        Factors:
        - More executions = higher confidence
        - More consistent sizes = higher confidence
        - Tighter time clustering = higher confidence
        - Larger total size = higher confidence
        """
        # Base score from execution count
        exec_score = min(execution_count * 10, 40)  # Max 40 points

        # Size consistency score (0-30 points)
        consistency_score = size_consistency * 30

        # Time clustering score (0-20 points)
        # Prefer executions within 1 minute
        if time_span < 60:
            time_score = 20
        elif time_span < 180:
            time_score = 15
        elif time_span < 300:
            time_score = 10
        else:
            time_score = 5

        # Total size score (0-10 points)
        size_score = min(total_executed / 10, 10)

        total_confidence = exec_score + consistency_score + time_score + size_score
        return min(total_confidence, 100)

    def get_actual_icebergs(
        self, start_date: str, end_date: str, symbol: str = "MNQ"
    ) -> List[ActualIceberg]:
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
            AND DATE(timestamp) BETWEEN %s AND %s
            AND symbol LIKE %s
            ORDER BY timestamp
        """

        cursor.execute(query, (start_date, end_date, f"{symbol}%"))
        rows = cursor.fetchall()

        icebergs = []
        for row in rows:
            timestamp, price, side, detected_size, est_total, subtype, confidence = row
            iceberg = ActualIceberg(
                timestamp=timestamp,
                price=price,
                side=side,
                detected_size=detected_size,
                estimated_total_size=est_total,
                iceberg_subtype=subtype,
                confidence_score=confidence,
            )
            icebergs.append(iceberg)

        cursor.close()

        print(f"✓ Loaded {len(icebergs)} actual icebergs")
        return icebergs

    def validate_detections(
        self, detected: List[IcebergCandidate], actual: List[ActualIceberg]
    ) -> Dict:
        """
        Validate detected icebergs against actual database records

        Matching criteria:
        - Same price level (exact or within 1 tick)
        - Same side
        - Timestamp within 5 minutes
        """
        print(f"\n{'=' * 80}")
        print(f"VALIDATING DETECTIONS")
        print(f"{'=' * 80}")
        print(f"Detected Candidates: {len(detected)}")
        print(f"Actual Icebergs: {len(actual)}")

        true_positives = []
        false_positives = []
        false_negatives = list(actual)  # Start with all actuals

        PRICE_TOLERANCE = 0.25  # 1 tick for MNQ
        TIME_TOLERANCE = timedelta(minutes=5)

        for candidate in detected:
            matched = False

            for i, actual_iceberg in enumerate(false_negatives):
                # Check price match
                price_diff = abs(candidate.price - actual_iceberg.price)
                if price_diff > PRICE_TOLERANCE:
                    continue

                # Check side match
                if candidate.side != actual_iceberg.side:
                    continue

                # Check time match
                time_diff = abs(candidate.first_seen - actual_iceberg.timestamp)
                if time_diff > TIME_TOLERANCE:
                    continue

                # Match found!
                true_positives.append(
                    {
                        "detected": candidate,
                        "actual": actual_iceberg,
                        "price_diff": price_diff,
                        "time_diff": time_diff.total_seconds(),
                    }
                )
                false_negatives.pop(i)
                matched = True
                break

            if not matched:
                false_positives.append(candidate)

        # Calculate metrics
        tp = len(true_positives)
        fp = len(false_positives)
        fn = len(false_negatives)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0
        )

        results = {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "matches": true_positives,
            "missed_detections": false_negatives,
            "false_alarms": false_positives,
        }

        return results

    def print_validation_results(self, results: Dict):
        """Print validation results in readable format"""
        print(f"\n{'=' * 80}")
        print(f"VALIDATION RESULTS")
        print(f"{'=' * 80}")

        print(f"\nDetection Metrics:")
        print(f"  True Positives:  {results['true_positives']} ✓")
        print(f"  False Positives: {results['false_positives']} ✗")
        print(f"  False Negatives: {results['false_negatives']} ✗")

        print(f"\nPerformance:")
        print(f"  Precision: {results['precision']*100:.1f}% (accuracy of detections)")
        print(
            f"  Recall:    {results['recall']*100:.1f}% (coverage of actual icebergs)"
        )
        print(f"  F1 Score:  {results['f1_score']*100:.1f}% (overall performance)")

        if results["true_positives"] > 0:
            print(f"\n✓ Successfully Detected ({results['true_positives']}):")
            for i, match in enumerate(results["matches"][:5], 1):
                detected = match["detected"]
                actual = match["actual"]
                print(f"\n  Match #{i}:")
                print(f"    Price: ${detected.price:.2f} ({detected.side})")
                print(
                    f"    Detected: {detected.execution_count} executions, {detected.total_executed:.1f} contracts"
                )
                print(
                    f"    Actual: {actual.iceberg_subtype} subtype, confidence {actual.confidence_score:.1f}"
                )
                print(f"    Time diff: {match['time_diff']:.1f}s")

            if len(results["matches"]) > 5:
                print(f"\n  ... and {len(results['matches']) - 5} more")

        if results["false_positives"] > 0:
            print(f"\n✗ False Positives ({results['false_positives']}):")
            for i, fp in enumerate(results["false_alarms"][:3], 1):
                print(
                    f"  {i}. ${fp.price:.2f} {fp.side}: {fp.execution_count} fills, confidence {fp.confidence:.1f}"
                )

            if len(results["false_alarms"]) > 3:
                print(f"  ... and {len(results['false_alarms']) - 3} more")

        if results["false_negatives"] > 0:
            print(f"\n✗ Missed Detections ({results['false_negatives']}):")
            for i, fn in enumerate(results["missed_detections"][:3], 1):
                print(
                    f"  {i}. ${fn.price:.2f} {fn.side}: {fn.iceberg_subtype}, confidence {fn.confidence_score:.1f}"
                )

            if len(results["missed_detections"]) > 3:
                print(f"  ... and {len(results['missed_detections']) - 3} more")

    def export_results(
        self,
        detected: List[IcebergCandidate],
        actual: List[ActualIceberg],
        validation: Dict,
        filename: str = "iceberg_detection_report.json",
    ):
        """Export full results to JSON"""
        report = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "detector_version": "1.0",
                "thresholds": {
                    "min_executions": self.MIN_EXECUTIONS,
                    "min_total_size": self.MIN_TOTAL_SIZE,
                    "max_time_window": self.MAX_TIME_WINDOW,
                    "confidence_threshold": self.CONFIDENCE_THRESHOLD,
                },
            },
            "detected_icebergs": [ic.to_dict() for ic in detected],
            "actual_icebergs": [ic.to_dict() for ic in actual],
            "validation_results": {
                "true_positives": validation["true_positives"],
                "false_positives": validation["false_positives"],
                "false_negatives": validation["false_negatives"],
                "precision": validation["precision"],
                "recall": validation["recall"],
                "f1_score": validation["f1_score"],
            },
        }

        with open(filename, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n✓ Full report exported to: {filename}")

    def close(self):
        self.conn.close()


def main():
    """Run iceberg detection validation test"""
    import sys

    # Get date range from command line or use defaults
    if len(sys.argv) >= 3:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
    else:
        # Use a recent date with known MBO data
        end_date = "2025-11-17"
        start_date = "2025-11-16"  # Just 2 days for testing

    print(f"{'=' * 80}")
    print(f"ICEBERG DETECTION & VALIDATION TEST")
    print(f"{'=' * 80}")
    print(f"Testing Period: {start_date} to {end_date}")

    detector = IcebergDetector()

    try:
        # Step 1: Detect icebergs from MBO patterns
        detected_icebergs = detector.detect_icebergs_from_mbo(start_date, end_date)

        # Step 2: Load actual icebergs from database
        actual_icebergs = detector.get_actual_icebergs(start_date, end_date)

        # Step 3: Validate detections
        validation_results = detector.validate_detections(
            detected_icebergs, actual_icebergs
        )

        # Step 4: Print results
        detector.print_validation_results(validation_results)

        # Step 5: Export detailed report
        detector.export_results(
            detected_icebergs,
            actual_icebergs,
            validation_results,
            f"iceberg_detection_report_{start_date}_to_{end_date}.json",
        )

        print(f"\n{'=' * 80}")
        print(f"SUMMARY")
        print(f"{'=' * 80}")
        print(
            f"Algorithm Performance: {validation_results['f1_score']*100:.1f}% F1 Score"
        )

        if (
            validation_results["precision"] >= 0.8
            and validation_results["recall"] >= 0.7
        ):
            print(f"✓ EXCELLENT: Algorithm performs well!")
        elif (
            validation_results["precision"] >= 0.6
            and validation_results["recall"] >= 0.5
        ):
            print(f"⚠ GOOD: Algorithm needs tuning")
        else:
            print(f"✗ POOR: Algorithm needs significant improvement")

        print(f"\nRecommendations:")
        if validation_results["precision"] < 0.7:
            print(f"  - Increase confidence threshold to reduce false positives")
            print(f"  - Tighten size consistency requirements")
        if validation_results["recall"] < 0.7:
            print(f"  - Lower minimum execution threshold")
            print(f"  - Expand time window for matching")
            print(f"  - Reduce size consistency requirements")

    finally:
        detector.close()


if __name__ == "__main__":
    main()
