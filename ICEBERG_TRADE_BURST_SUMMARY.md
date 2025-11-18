# Iceberg Detection via Trade-Burst Pattern Analysis

## Discovery Summary

**Date**: Nov 17, 2025  
**Method**: MBO data analysis + Bookmap source code review  
**Breakthrough**: Icebergs appear as rapid bursts of TRADE events, not as "refill" patterns

---

## Key Findings

### 1. Bookmap's Detection Mechanism

From source code analysis (`sit-icebergs.js`, `sit-alert.js`):

```javascript
// Bookmap checks broker-provided flag
if (pa.isNativeIceberg || pa.isCustomIceberg) {
    var orderSize = pa.lifetimeTradedSize + pa.remainedSize;
}

// Alert threshold
threshold: 50,
icebergs: new Aggregator(1e7), // 10 milliseconds
```

**Critical insight**: Bookmap receives `isNativeIceberg` flag from broker/exchange. They don't algorithmically detect icebergs - they visualize already-flagged orders.

### 2. MBO Data Pattern

Analysis of 111 actual iceberg detections revealed:

**Pattern**: Rapid bursts of TRADE-only events

- No visible ADD/UPDATE/DELETE sequence
- Just multiple TRADE actions clustered in time
- All trades at same/similar price level
- Burst duration: 0-10 milliseconds

**Example**:

```
Time: 09:10:47.502
Price: $25039.75
Side: SELL
Detected Size: 1

MBO Pattern:
  09:10:47.502: 10 TRADE events, total size: 13 contracts
  09:10:47.505: 5 TRADE events, total size: 6 contracts
  09:10:47.506: 16 TRADE events, total size: 20 contracts
```

**Key Observation**:

- Detected size (1-2) << actual burst size (10-20)
- Bookmap's "detected_size" represents something other than total traded volume
- Bursts contain 5-20+ individual TRADE events within milliseconds

### 3. Detection Algorithm

**Approach**: Identify trade bursts instead of order refills

```python
# Thresholds
MIN_TRADES_IN_BURST = 7      # At least 7 trades
BURST_WINDOW_MS = 10         # Within 10 milliseconds
MIN_BURST_SIZE = 8           # Total size >= 8 contracts

# Algorithm
1. Sort all TRADE events by timestamp
2. Group trades within 10ms window at same price
3. Count trades and total size in each group
4. Flag groups exceeding thresholds as iceberg candidates
```

---

## Test Results

### Validation (Nov 17, 2025, 9am-12pm)

**Dataset**:

- 563,752 TRADE events
- 111 actual iceberg detections (from Bookmap)

**Results**:

```
True Positives:     78  (70.3% recall)
False Positives:    7,436  (1.0% precision)
False Negatives:    33  (29.7% missed)
```

### Performance by Hour

| Hour | Actual | Detected | Recall |
| ---- | ------ | -------- | ------ |
| 9am  | 29     | 27       | 93.1%  |
| 10am | 44     | 30       | 68.2%  |
| 11am | 38     | 21       | 55.3%  |

### Missed Icebergs Analysis

All missed icebergs have characteristics:

- Small detected size (1-5 contracts)
- Weak burst pattern (< 7 trades)
- Longer duration (> 10ms spread)

**Example misses**:

```
09:10:47.897 SELL $25037.75 [size: 1] - only 3 trades in burst
10:03:23.392 BUY  $25165.00 [size: 5] - trades spread over 50ms
```

---

## Conclusions

### What We Learned

1. **Original hypothesis wrong**: Icebergs don't show "refill" pattern (UPDATE increasing size) in MBO data

2. **Actual pattern**: Rapid trade bursts

   - Multiple executions hitting iceberg order
   - Clustered in time (< 10ms)
   - Visible as burst of TRADE events

3. **Bookmap doesn't calculate**: They use broker-provided `isNativeIceberg` flag

   - Exchange marks orders as icebergs at submission time
   - Based on order metadata (hidden size, iceberg flag in order entry)
   - Not detectable from observable behavior alone

4. **Detection challenge**: Reverse-engineering without metadata
   - Can detect ~70% using trade-burst pattern
   - Small icebergs (1-5 contracts) create weak signatures
   - High false positive rate (99% of bursts aren't icebergs)

### Why Refill Detection Failed

Original algorithm looked for:

```python
if action == 'UPDATE' and size > prev_size * 1.5:
    refill_count += 1
```

**Problem**:

- Icebergs don't refill their visible size in MBO data
- Hidden size is... hidden (not visible in market-by-order feed)
- Only see rapid fills as separate TRADE events
- No UPDATE showing size increase

### Trade-Burst vs Refill

| Pattern        | Refill (Expected)           | Trade-Burst (Actual)        |
| -------------- | --------------------------- | --------------------------- |
| Signature      | ADD → TRADE → UPDATE(size↑) | TRADE TRADE TRADE...        |
| Timing         | Seconds between refills     | Milliseconds between trades |
| Size changes   | Visible in UPDATE action    | Not visible (hidden size)   |
| Detection rate | 0% (pattern doesn't exist)  | 70% (pattern exists)        |

---

## Recommendations

### For Production Use

1. **Accept trade-burst detection** with caveats:

   - 70% recall (will miss 30% of small icebergs)
   - 1% precision (99% false positives)
   - Best for detecting significant icebergs (>5 contracts)

2. **Threshold tuning**:

   - Increase for fewer false positives (lower recall)
   - Decrease for higher recall (more false positives)
   - Current: 7 trades, 8 contracts, 10ms

3. **Complementary approach**:
   - Use trade-burst for real-time detection
   - Combine with other signals (spoofing, absorption)
   - Filter by market context (high volume periods)

### Alternative Approaches

Since we can't access broker metadata, consider:

1. **Statistical analysis**:

   - Model typical fill patterns
   - Flag anomalous fill sequences
   - Machine learning on labeled data

2. **Indirect indicators**:

   - Repeated fills at exact same price
   - Unusually persistent liquidity
   - Price rejections with no visible size

3. **Multi-signal fusion**:
   - Combine with absorption indicator
   - Look for sweeps through iceberg levels
   - Track stops triggered near icebergs

---

## Files

- `mbo_iceberg_detector.py` - Original refill-based detector (0% recall)
- `trade_burst_detector.py` - Trade-burst detector (70% recall)
- `analyze_iceberg_pattern.py` - Single iceberg MBO analysis
- `verify_iceberg_hypothesis.py` - Pattern verification across 10 samples
- `test_iceberg_hour.py` - Hour-window testing framework

---

## Next Steps

1. ✅ Understand why refill detection failed
2. ✅ Find actual MBO pattern for icebergs
3. ✅ Build trade-burst detector
4. ✅ Validate on multi-hour dataset
5. ⏳ Integrate into real-time consumer
6. ⏳ Combine with other institutional order detection
7. ⏳ Build machine learning classifier for better precision

---

## Database Queries

### Get actual icebergs

```sql
SELECT timestamp, price, side, detected_size, estimated_total_size
FROM stops_icebergs
WHERE event_type = 'ICEBERG'
AND iceberg_subtype = 'DETECTION'
AND symbol LIKE 'MNQ%'
ORDER BY timestamp;
```

### Find trade bursts

```sql
WITH burst_candidates AS (
    SELECT
        timestamp,
        price,
        side,
        COUNT(*) FILTER (WHERE action = 'TRADE') as trade_count,
        SUM(size) FILTER (WHERE action = 'TRADE') as total_size
    FROM mbo_data
    WHERE symbol LIKE 'MNQ%'
    AND timestamp >= '2025-11-17 09:00:00'
    GROUP BY
        DATE_TRUNC('millisecond', timestamp),
        price,
        side
)
SELECT *
FROM burst_candidates
WHERE trade_count >= 7
AND total_size >= 8
ORDER BY timestamp;
```

### Match candidates to actuals

```sql
-- Find MBO events near iceberg detection
SELECT m.*
FROM mbo_data m
INNER JOIN stops_icebergs s
    ON m.symbol LIKE LEFT(s.symbol, 3) || '%'
    AND m.side = s.side
    AND ABS(EXTRACT(EPOCH FROM (m.timestamp - s.timestamp))) <= 5
    AND ABS(m.price - s.price) <= 1.0
WHERE s.event_type = 'ICEBERG'
AND s.iceberg_subtype = 'DETECTION'
AND m.action = 'TRADE'
ORDER BY m.timestamp;
```
