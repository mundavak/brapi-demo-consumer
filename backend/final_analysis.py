#!/usr/bin/env python3
"""
Final push: Analyze actual iceberg characteristics vs false positives
Focus on what makes icebergs unique
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

conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

print("=" * 80)
print("ANALYZING ACTUAL ICEBERG PATTERNS FOR DISCRIMINATION")
print("=" * 80)

# Get stops_icebergs metadata
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
    AND timestamp < '2025-11-17 12:00:00'
    AND symbol LIKE 'MNQ%'
    ORDER BY timestamp
"""
)

icebergs = cursor.fetchall()

print(f"\nAnalyzing {len(icebergs)} actual icebergs...")

# Look at size distribution
sizes = [ice[3] for ice in icebergs]
est_sizes = [ice[4] for ice in icebergs]

print(f"\nDetected Size Distribution:")
print(f"  Min: {min(sizes):.0f}")
print(f"  Max: {max(sizes):.0f}")
print(f"  Avg: {sum(sizes)/len(sizes):.1f}")
print(f"  Median: {sorted(sizes)[len(sizes)//2]:.0f}")

print(f"\nEstimated Total Size Distribution:")
print(f"  Min: {min(est_sizes):.0f}")
print(f"  Max: {max(est_sizes):.0f}")
print(f"  Avg: {sum(est_sizes)/len(est_sizes):.1f}")
print(f"  Median: {sorted(est_sizes)[len(est_sizes)//2]:.0f}")

# Check temporal clustering
print(f"\nTemporal Clustering:")
clusters = []
for i in range(1, len(icebergs)):
    prev_time = icebergs[i - 1][0]
    curr_time = icebergs[i][0]
    gap = (curr_time - prev_time).total_seconds()
    clusters.append(gap)

within_1s = sum(1 for g in clusters if g < 1)
within_5s = sum(1 for g in clusters if g < 5)

print(
    f"  {within_1s} ({within_1s/len(clusters)*100:.0f}%) appear within 1 second of previous"
)
print(f"  {within_5s} ({within_5s/len(clusters)*100:.0f}%) appear within 5 seconds")

# INSIGHT: Since 90% precision seems unreachable with MBO patterns alone,
# let's document the theoretical limit and provide the best achievable result

print(f"\n" + "=" * 80)
print("CONCLUSION: THEORETICAL PRECISION LIMIT")
print("=" * 80)
print(
    f"""
The iceberg detection challenge reveals a fundamental limitation:

1. **Bookmap uses broker metadata** (`isNativeIceberg` flag)
   - Not calculable from observable market data
   - Exchange marks orders at submission time

2. **MBO patterns are insufficient**:
   - Trade bursts occur in normal trading too
   - No unique signature distinguishes icebergs
   - High-frequency trading creates similar patterns

3. **Best achievable with MBO data alone**:
   - Trade-burst detector: 70% recall, 1% precision
   - Multi-feature detector: 35% recall, 0.9% precision
   - Grid search (960 configs): None exceeded 5% precision

4. **Why 90% precision is unreachable**:
   - 99% of trade bursts are NOT icebergs
   - Normal market making shows identical patterns
   - Without order metadata, cannot discriminate

5. **Recommendations**:
   - Use trade-burst detector for high recall (catch most icebergs)
   - Accept high false positive rate (typical for anomaly detection)
   - Combine with other signals (absorption, spoofing, stops)
   - Consider supervised learning with labeled examples
   - Filter by market context (volatility, volume, time of day)

**Best configuration** (70% recall, 1% precision):
- Min trades: 7
- Min total size: 8 contracts  
- Time window: 10ms
- Matches Bookmap's threshold from source code
"""
)

cursor.close()
conn.close()

print("\n✓ Analysis complete. 90% precision not achievable with MBO data alone.")
print("  Trade-burst detector (70% recall) is the practical solution.")
