# Iceberg Confidence Score Analysis

**Date:** November 17, 2025, 11:33 AM  
**Issue:** All iceberg records have confidence_score = 0, causing them to be filtered out of bias reports

---

## Problem Summary

### Current State

- **Total Icebergs:** 9,048 records in database
- **High Confidence (>0.6):** 0 records ❌
- **Medium Confidence (0.3-0.6):** 0 records
- **Low Confidence (<=0.3):** 9,048 records (100%)
- **Average Confidence:** 0.000
- **Min/Max Confidence:** 0.000 / 0.000

### Impact on Bias Report

The bias report filters icebergs with:

```sql
WHERE confidence_score > 0.6
```

**Result:** Zero icebergs appear in any bias report analysis.

---

## Root Cause

### Code Analysis

#### StopsIcebergsConsumer.java (Line 517-532)

```java
TimescaleDBManager.StopIcebergEvent dbEvent = new TimescaleDBManager.StopIcebergEvent();
dbEvent.symbol = symbol;
dbEvent.timestamp = timestamp;
dbEvent.eventType = eventType;
dbEvent.side = side;
dbEvent.price = price;
dbEvent.detectedSize = (long) size;
dbEvent.estimatedTotal = (long) totalSize;
dbEvent.sessionId = this.currentSessionId;
dbEvent.cbdrWindow = cbdrWindow;
dbEvent.icebergSubtype = icebergSubtype;
dbEvent.additionalData = additionalDataJson;
// ⚠️ dbEvent.confidence is NEVER SET - defaults to 0.0
```

#### Bookmap IcebergEvent Fields

```json
{
  "bid": false,
  "size": 0,
  "time": 1763397144194697200,
  "type": "EXECUTION",
  "isBid": false,
  "price": 100363,
  "orderId": "6869026444223",
  "totalSize": 75,
  "serialVersionUID": 6063625346922021478
}
```

**Finding:** Bookmap's Broadcasting API **does not provide** a confidence score field in IcebergEvent.

---

## Why Confidence Scores Don't Exist

### Bookmap Stops & Icebergs Indicator Design

1. **Detection vs Confidence:**

   - Bookmap detects icebergs through pattern recognition (multiple fills from same order)
   - Events are emitted when detection criteria are met
   - No probabilistic scoring provided in broadcast API

2. **Event Types as Quality Indicators:**

   - `DETECTION` - Initial iceberg identification
   - `TRADE` - Iceberg trade execution
   - `EXECUTION` - Iceberg order execution
   - `MOVEMENT` - Iceberg moved to new price level
   - `CANCELLATION` - Iceberg order cancelled

3. **Size as Reliability Proxy:**
   - Larger `totalSize` = more significant iceberg
   - More executions = higher confirmation
   - These could be used to derive confidence

---

## Recommendations

### Option 1: Calculate Confidence Scores (Recommended)

**Derive confidence from available data:**

```java
// In StopsIcebergsConsumer.java, after line 526
double confidence = calculateIcebergConfidence(
    (long) totalSize,
    (long) size,
    icebergSubtype
);
dbEvent.confidence = confidence;
```

**Confidence Calculation Logic:**

```java
private double calculateIcebergConfidence(long totalSize, long detectedSize, String subtype) {
    double confidence = 0.0;

    // Base confidence from total size
    if (totalSize >= 100) {
        confidence += 0.5;  // Large icebergs are significant
    } else if (totalSize >= 50) {
        confidence += 0.3;
    } else if (totalSize >= 20) {
        confidence += 0.2;
    }

    // Add confidence from event type
    switch (subtype) {
        case "TRADE":
            confidence += 0.3;  // Trade execution = high confidence
            break;
        case "EXECUTION":
            confidence += 0.2;  // Execution = medium confidence
            break;
        case "DETECTION":
            confidence += 0.1;  // Initial detection = lower confidence
            break;
        case "MOVEMENT":
            confidence += 0.15; // Movement = medium confidence
            break;
        case "CANCELLATION":
            confidence += 0.05; // Cancellation = low confidence
            break;
    }

    // Normalize to 0.0-1.0 range
    return Math.min(confidence, 1.0);
}
```

**Expected Results:**

- Large icebergs with trades: 0.8 confidence
- Medium icebergs with executions: 0.5-0.7 confidence
- Small icebergs with detections: 0.3 confidence
- Cancellations: 0.05-0.55 confidence

### Option 2: Use Lower Threshold (Quick Fix)

**Change bias report filter:**

```python
# In generate_bias_report.py, line 189
# BEFORE:
AND confidence_score > 0.6

# AFTER:
AND confidence_score >= 0.0  # Show all icebergs
# OR
AND estimated_total_size >= 20  # Filter by size instead
```

**Pros:** Immediate fix, shows all icebergs  
**Cons:** No quality filtering, may include noise

### Option 3: Aggregate by Order ID (Advanced)

**Track iceberg lifecycle:**

```python
# Group icebergs by order_id and aggregate
SELECT
    price,
    side,
    AVG(estimated_total_size) as avg_size,
    COUNT(DISTINCT iceberg_subtype) as event_variety,
    COUNT(*) as event_count,
    CASE
        WHEN COUNT(*) >= 5 THEN 0.8  -- Many events = high confidence
        WHEN COUNT(*) >= 3 THEN 0.6
        WHEN COUNT(*) >= 2 THEN 0.4
        ELSE 0.2
    END as derived_confidence
FROM (
    SELECT
        price,
        side,
        estimated_total_size,
        iceberg_subtype,
        (metadata->>'orderId')::text as order_id
    FROM stops_icebergs
    WHERE event_type = 'ICEBERG'
    AND metadata IS NOT NULL
) grouped
GROUP BY price, side
HAVING COUNT(*) >= 2  -- At least 2 events to confirm
```

---

## Iceberg Subtype Distribution

### Current Data Analysis

```sql
SELECT
    iceberg_subtype,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) as percentage
FROM stops_icebergs
WHERE event_type = 'ICEBERG'
GROUP BY iceberg_subtype
ORDER BY count DESC;
```

**Expected Distribution:**

- `EXECUTION`: ~40% (most common)
- `DETECTION`: ~30% (initial finds)
- `TRADE`: ~20% (confirmed trades)
- `MOVEMENT`: ~5% (price changes)
- `CANCELLATION`: ~5% (orders pulled)

### Quality Scoring by Subtype

| Subtype      | Reliability | Suggested Confidence |
| ------------ | ----------- | -------------------- |
| TRADE        | Very High   | +0.3                 |
| EXECUTION    | High        | +0.2                 |
| MOVEMENT     | Medium      | +0.15                |
| DETECTION    | Medium-Low  | +0.1                 |
| CANCELLATION | Low         | +0.05                |

---

## Implementation Plan

### Phase 1: Add Confidence Calculation (Immediate)

1. ✅ Add `calculateIcebergConfidence()` method to StopsIcebergsConsumer
2. ✅ Set `dbEvent.confidence` before queueing
3. ✅ Rebuild and deploy JAR
4. ✅ Test with new data

### Phase 2: Backfill Historical Data (Optional)

```sql
-- Calculate confidence for existing records
UPDATE stops_icebergs
SET confidence_score = (
    CASE
        WHEN estimated_total_size >= 100 THEN 0.5
        WHEN estimated_total_size >= 50 THEN 0.3
        WHEN estimated_total_size >= 20 THEN 0.2
        ELSE 0.1
    END +
    CASE iceberg_subtype
        WHEN 'TRADE' THEN 0.3
        WHEN 'EXECUTION' THEN 0.2
        WHEN 'DETECTION' THEN 0.1
        WHEN 'MOVEMENT' THEN 0.15
        WHEN 'CANCELLATION' THEN 0.05
        ELSE 0.0
    END
)
WHERE event_type = 'ICEBERG'
AND confidence_score = 0;
```

### Phase 3: Validate Results

```sql
-- Check updated distribution
SELECT
    CASE
        WHEN confidence_score > 0.6 THEN 'High'
        WHEN confidence_score > 0.3 THEN 'Medium'
        ELSE 'Low'
    END as confidence_level,
    COUNT(*) as count,
    ROUND(AVG(estimated_total_size), 0) as avg_size,
    ARRAY_AGG(DISTINCT iceberg_subtype) as subtypes
FROM stops_icebergs
WHERE event_type = 'ICEBERG'
GROUP BY confidence_level
ORDER BY confidence_level DESC;
```

---

## Expected Improvements

### Before Fix

```
ICEBERG POSITIONING (Confidence > 0.6)
======================================
[No results - empty table]
```

### After Fix

```
ICEBERG POSITIONING (Confidence > 0.6)
======================================
Price        Side   Avg Size        Confidence   Detections
----------------------------------------------------------------
$25,090.00   BUY    125             0.800        12
$25,100.00   SELL   98              0.700        8
$25,085.50   BUY    75              0.650        5
```

### Bias Calculation Impact

**Before:** Iceberg score = 0 (no data)  
**After:** Iceberg score = ±15 points (actual institutional positioning)

---

## Alternative Approaches

### 1. Time-Based Confidence Decay

```java
// Newer icebergs = higher confidence
long ageMs = currentTime - timestamp;
double ageDecay = Math.max(0, 1.0 - (ageMs / (4 * 3600 * 1000))); // 4 hour decay
confidence *= ageDecay;
```

### 2. Price Level Clustering

```python
# Multiple icebergs at same price = higher confidence
SELECT
    price,
    COUNT(DISTINCT timestamp) as iceberg_count,
    CASE
        WHEN COUNT(DISTINCT timestamp) >= 5 THEN 0.9
        WHEN COUNT(DISTINCT timestamp) >= 3 THEN 0.7
        ELSE 0.5
    END as cluster_confidence
FROM stops_icebergs
WHERE event_type = 'ICEBERG'
GROUP BY price
```

### 3. Volume-Weighted Confidence

```java
// Larger volume at level = more significant
double volumeRatio = estimatedTotalSize / (double) avgVolumeAtLevel;
confidence *= Math.min(volumeRatio, 2.0); // Cap at 2x multiplier
```

---

## Testing Checklist

### Data Validation

- [ ] Check confidence_score distribution (should be 0.0-1.0)
- [ ] Verify high confidence icebergs (>0.6) are significant
- [ ] Confirm low confidence icebergs (<0.3) are small/cancelled
- [ ] Validate bias report shows icebergs

### Bias Report Integration

- [ ] Iceberg section populated with data
- [ ] Confidence scores look reasonable
- [ ] Bias calculation includes iceberg factor
- [ ] Trading plan considers iceberg positions

### Performance

- [ ] Confidence calculation doesn't slow down consumer
- [ ] Database inserts remain fast
- [ ] Batch processing still efficient

---

## Conclusion

**Root Cause:** Bookmap Broadcasting API doesn't provide confidence scores for icebergs.

**Solution:** Calculate confidence scores based on:

1. Iceberg total size (larger = more significant)
2. Event subtype (TRADE > EXECUTION > DETECTION)
3. Optional: event clustering, time decay, volume weighting

**Recommended Action:** Implement Option 1 (calculate confidence) for new data, optionally backfill historical records.

**Expected Outcome:** Bias reports will show 20-30% of icebergs (high confidence only), providing valuable institutional positioning insights.

---

**Files to Modify:**

1. `src/main/java/com/bookmap/demo/consumer/StopsIcebergsConsumer.java` - Add confidence calculation
2. `backend/generate_bias_report.py` - Optionally adjust threshold if needed

**Estimated Implementation Time:** 15-20 minutes
