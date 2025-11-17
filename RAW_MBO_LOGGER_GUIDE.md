# Raw MBO Data Logger - Usage Guide

## Overview

The **Raw MBO Data Logger** is a diagnostic addon that captures **all** Market-By-Order (MBO) events from Bookmap in real-time and logs them to a text file. This helps you understand what raw data fields are available from the MBO feed.

## Installation

✅ **Already Installed!**

The addon JAR has been copied to: `C:\Users\Kudzai\Bookmap\AddOns\Demo-Consumer-3.0.0.jar`

## How to Use

### 1. Start Bookmap

Launch Bookmap normally and connect to your data feed.

### 2. Enable the Addon

- Right-click on the chart
- Select **"Indicators"** → **"Raw MBO Data Logger"**
- Or go to **Settings** → **"Manage Addons"** and enable "Raw MBO Data Logger"

### 3. Collect Data

- The addon will immediately start logging all MBO events to:
  ```
  F:/TradingAgent/deaProjects/brapi-demo-consumer/outputs/logs/rawmbo.log
  ```
- Let it run for a few minutes to collect sufficient data
- You'll see events logged in real-time as they occur

### 4. Review the Log

Open `rawmbo.log` to see the captured data. Example output:

```
════════════════════════════════════════════════════════════════
RAW MBO DATA LOGGER - CAPTURE STARTED
════════════════════════════════════════════════════════════════
Symbol: MNQ DEC4
Instrument Info:
  - Full Name: E-mini NASDAQ-100 Futures,Dec-2024,ETH
  - Exchange: CME
  - Type: FUTURE
  - Pips: 0.25
  - Size Multiplier: 1.0
  - Multiplier: 2.0
  - Symbol: MNQ DEC4
Timestamp: 2025-11-16 10:18:23.456
════════════════════════════════════════════════════════════════

CAPTURING ALL MBO EVENTS:
  ✓ MBO Send (new orders)
  ✓ MBO Replace (order modifications)
  ✓ MBO Cancel (order deletions)
  ✓ Trades (executions)

────────────────────────────────────────────────────────────────

[1] MBO SEND
    Time:     2025-11-16 10:18:24.123
    OrderID:  ABC123XYZ
    Side:     BUY
    Price:    21345.50 (raw: 85382)
    Size:     5.00 (raw: 5)

[2] MBO REPLACE
    Time:     2025-11-16 10:18:24.456
    OrderID:  ABC123XYZ
    Side:     BUY
    New Price: 21345.75 (raw: 85383)
    New Size:  7.00 (raw: 7)

[3] MBO CANCEL
    Time:     2025-11-16 10:18:25.789
    OrderID:  ABC123XYZ
    Side:     BUY

[4] TRADE
    Time:       2025-11-16 10:18:26.012
    Price:      21346.00 (raw: 21346.00)
    Size:       2.00 (raw: 2)
    Aggressor:  ASK (Buy order filled)
```

## What Data is Captured

### MBO SEND (New Order)

- **OrderID**: Unique identifier for the order
- **Side**: BUY or SELL
- **Price**: Both actual (in dollars) and raw (internal format)
- **Size**: Both actual (contracts) and raw (internal format)
- **Time**: Timestamp when event occurred

### MBO REPLACE (Order Modified)

- **OrderID**: Same ID as original order
- **Side**: Looked up from previous SEND event
- **New Price**: Updated price (both formats)
- **New Size**: Updated size (both formats)
- **Time**: Timestamp

### MBO CANCEL (Order Deleted)

- **OrderID**: Same ID as original order
- **Side**: Looked up from previous SEND event (then removed from tracking)
- **Time**: Timestamp

### TRADE (Execution)

- **Price**: Trade execution price (both formats)
- **Size**: Trade size (both formats)
- **Aggressor**: BID (sell order filled) or ASK (buy order filled)
- **Time**: Timestamp

## Understanding the Data

### Price Formats

- **Raw**: Internal Bookmap representation (integer)
- **Actual**: Real dollar/point value (raw × pips)
- Example: raw=85382, pips=0.25 → actual=21345.50

### Size Formats

- **Raw**: Internal Bookmap representation
- **Actual**: Real contract count (raw ÷ sizeMultiplier)
- Example: raw=5, sizeMultiplier=1.0 → actual=5.00

### Order Side Tracking

- SEND events provide the side (BUY/SELL)
- REPLACE and CANCEL events only provide OrderID
- The logger tracks sides internally to display them for REPLACE/CANCEL

### Aggressor Side

- **BID Aggressor**: A market sell order hit a resting buy limit order
- **ASK Aggressor**: A market buy order hit a resting sell limit order

## Session Summary

When you disable the addon or close Bookmap, a summary is written to the log:

```
════════════════════════════════════════════════════════════════
RAW MBO DATA LOGGER - CAPTURE STOPPED
════════════════════════════════════════════════════════════════
Session Summary:
  MBO Sends:    1,234
  MBO Replaces: 567
  MBO Cancels:  1,123
  Trades:       345
  Total Events: 3,269
  Uptime:       300,000 ms (300.00 seconds)
════════════════════════════════════════════════════════════════
```

## Performance Notes

- The logger **flushes to disk**:
  - Every 100 MBO events (send/replace/cancel)
  - Every 50 trade events
- This ensures data is saved even if Bookmap crashes
- High-frequency markets may generate **thousands of events per second**
- The log file will grow quickly during active market hours

## Troubleshooting

### No log file created

- Check that Bookmap has write permissions to `F:/TradingAgent/deaProjects/brapi-demo-consumer/outputs/logs/`
- The directory is automatically created if it doesn't exist
- Look for errors in Bookmap's log files

### Log file is empty

- Make sure the addon is enabled on the chart
- Verify you're connected to a data feed that provides MBO data
- Some data feeds only provide aggregated depth, not MBO

### "Side: UNKNOWN" in REPLACE/CANCEL events

- This happens if the logger missed the original SEND event
- Can occur if you enable the addon after the market opens (snapshot doesn't include SEND events)
- Will resolve as new orders are placed

### Too much data

- The logger captures **everything** - it's intentionally verbose
- For production use, consider adding filters in the code
- Or collect data for short periods (5-10 minutes) then stop

## Next Steps

After reviewing the raw data:

1. **Identify Key Fields**: Determine which fields are most useful for your analysis
2. **Optimize Storage**: Modify `MboDataConsumer.java` to store only needed fields
3. **Add Calculations**: Use OrderID tracking to calculate:
   - Order lifetime (SEND to CANCEL time)
   - Price improvement (REPLACE price changes)
   - Fill rates (CANCEL before TRADE)
4. **Pattern Detection**: Look for institutional order patterns:
   - Large iceberg orders (frequent REPLACEs at same price)
   - Spoofing (rapid SEND then CANCEL)
   - Layering (multiple orders stacked at similar prices)

## Technical Details

- **API Version**: Layer1ApiVersion.VERSION2
- **Interfaces**: CustomModule, MarketByOrderDepthDataListener, TradeDataListener
- **Thread Safety**: Uses ConcurrentHashMap for order tracking
- **Memory Usage**: Minimal (only tracks active order IDs)
- **Disk Usage**: Grows ~100 bytes per event (depends on OrderID length)

## Related Addons

- **MboDataConsumer**: Production consumer that writes MBO data to Redis/TimescaleDB
- **StopsIcebergsConsumer**: Detects iceberg orders from MBO patterns
- **OhlcCandleConsumer**: Generates OHLC candles from trade data

## Support

For questions or issues:

- Check `KnowledgeBase/BookmapAPIREADME.md` for API details
- Review `VERIFICATION_GUIDE.md` for troubleshooting steps
- Examine Bookmap logs in `C:\Users\Kudzai\Bookmap\Logs\`
