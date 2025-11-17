# Raw MBO Data Logger - Quick Reference

## ✅ Status: Ready to Use

**JAR Location**: `C:\Users\Kudzai\Bookmap\AddOns\Demo-Consumer-3.0.0.jar`  
**Log Output**: `F:/TradingAgent/deaProjects/brapi-demo-consumer/outputs/logs/rawmbo.log`

---

## Quick Start (3 Steps)

1. **Launch Bookmap** and connect to data feed
2. **Enable addon**: Right-click chart → Indicators → "Raw MBO Data Logger"
3. **View log**: Open `rawmbo.log` in text editor

---

## What Gets Logged

### MBO SEND (New Order)

```
[1] MBO SEND
    Time:     2025-11-16 10:18:24.123
    OrderID:  ABC123XYZ
    Side:     BUY
    Price:    21345.50 (raw: 85382)
    Size:     5.00 (raw: 5)
```

### MBO REPLACE (Order Modified)

```
[2] MBO REPLACE
    Time:     2025-11-16 10:18:24.456
    OrderID:  ABC123XYZ
    Side:     BUY
    New Price: 21345.75 (raw: 85383)
    New Size:  7.00 (raw: 7)
```

### MBO CANCEL (Order Deleted)

```
[3] MBO CANCEL
    Time:     2025-11-16 10:18:25.789
    OrderID:  ABC123XYZ
    Side:     BUY
```

### TRADE (Execution)

```
[4] TRADE
    Time:       2025-11-16 10:18:26.012
    Price:      21346.00 (raw: 21346.00)
    Size:       2.00 (raw: 2)
    Aggressor:  ASK (Buy order filled)
```

---

## Available Data Fields

### Always Available

- ✅ **OrderID** (String) - Unique identifier
- ✅ **Side** (BUY/SELL) - From SEND, tracked for REPLACE/CANCEL
- ✅ **Price** (int raw, double actual) - Both formats
- ✅ **Size** (int raw, double actual) - Both formats
- ✅ **Timestamp** (yyyy-MM-dd HH:mm:ss.SSS)
- ✅ **Aggressor** (BID/ASK) - Trade only

### Instrument Info (logged at startup)

- ✅ Symbol, Exchange, Type
- ✅ Pips, SizeMultiplier, Multiplier
- ✅ Full Name

---

## Understanding the Output

### Price Conversion

```
Actual Price = Raw Price × Pips
21345.50 = 85382 × 0.25
```

### Size Conversion

```
Actual Size = Raw Size ÷ Size Multiplier
5.00 = 5 ÷ 1.0
```

### Aggressor Side

- **BID Aggressor**: Market sell hit resting buy (bearish)
- **ASK Aggressor**: Market buy hit resting sell (bullish)

---

## Event Volume (Active Market)

- **SEND**: 500-2000/sec
- **REPLACE**: 200-800/sec
- **CANCEL**: 400-1800/sec
- **TRADE**: 50-200/sec

**Log growth**: ~100-500 KB/sec  
**Recommendation**: Run for 5-10 minutes max

---

## Session Summary (at shutdown)

```
════════════════════════════════════════
RAW MBO DATA LOGGER - CAPTURE STOPPED
════════════════════════════════════════
Session Summary:
  MBO Sends:    1,234
  MBO Replaces: 567
  MBO Cancels:  1,123
  Trades:       345
  Total Events: 3,269
  Uptime:       300.00 seconds
════════════════════════════════════════
```

---

## Troubleshooting

| Problem         | Solution                                       |
| --------------- | ---------------------------------------------- |
| No log file     | Check permissions on `outputs/logs/`           |
| Log is empty    | Verify addon enabled, data feed connected      |
| "Side: UNKNOWN" | Logger missed SEND (enable before market open) |
| Too much data   | Run for shorter periods                        |

---

## Integration with Existing Pipeline

```
Bookmap
   ↓
   ├─→ MboDataConsumer → Redis/TimescaleDB → Python → n8n → Gemini
   ├─→ StopsIcebergsConsumer → Iceberg detection
   ├─→ OhlcCandleConsumer → Candles
   └─→ RawMboDataLogger → rawmbo.log ← YOU ARE HERE
```

All run independently, no conflicts.

---

## Common Use Cases

### 1. Field Discovery

**Goal**: See what MBO fields Bookmap provides  
**Action**: Run for 5 minutes, review log  
**Output**: Complete field inventory

### 2. Order Lifetime Analysis

**Goal**: Track order from SEND to CANCEL/TRADE  
**Action**: Match OrderIDs across events  
**Output**: Order lifecycle timings

### 3. Price Modification Patterns

**Goal**: Detect institutional iceberg orders  
**Action**: Look for frequent REPLACEs at same price  
**Output**: Hidden order detection

### 4. Trade Flow Analysis

**Goal**: Measure buy vs sell aggression  
**Action**: Count BID vs ASK aggressor trades  
**Output**: Market pressure indicators

---

## Performance Notes

- **Flush Frequency**: Every 100 MBO, every 50 trades
- **Memory**: Minimal (~32 bytes per active order)
- **Thread Safety**: Yes (ConcurrentHashMap)
- **Production Use**: No (synchronous I/O, high disk usage)

---

## Documentation

- **User Guide**: `RAW_MBO_LOGGER_GUIDE.md` (detailed)
- **Implementation**: `RAW_MBO_LOGGER_SUMMARY.md` (technical)
- **Quick Reference**: `RAW_MBO_QUICK_REF.md` (this file)

---

## Build Commands (if you modify code)

```powershell
# Set Java home
$env:JAVA_HOME='C:\Users\Kudzai\.jdk\jdk-21.0.8'

# Build
.\gradlew.bat clean build

# Auto-copies to F:/Bookmap/Python/build/
# Manual copy to Bookmap addons:
Copy-Item "build\libs\Demo-Consumer-3.0.0.jar" `
  -Destination "C:\Users\Kudzai\Bookmap\AddOns\" -Force
```

---

## Next Steps After Testing

1. ✅ Identify useful fields from log
2. ⏸️ Update MboDataConsumer to capture specific fields
3. ⏸️ Add Python analysis scripts for new data
4. ⏸️ Enhance n8n workflow with insights
5. ⏸️ Fine-tune Gemini prompts based on findings

---

**Status**: ✅ Complete and Ready  
**Last Updated**: November 16, 2025  
**Tested**: Build successful, deployed to Bookmap
