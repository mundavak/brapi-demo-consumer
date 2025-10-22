# StopsIcebergsConsumer Verification Guide

## How to Confirm It's Working

I've added enhanced logging to help you verify the addon is working correctly.

### Step 1: Build the Project

Set JAVA_HOME first (adjust path to your Java installation):
```cmd
set JAVA_HOME=C:\Program Files\Java\jdk-17
```

Then build:
```cmd
cd F:\TradingAgent\deaProjects\brapi-demo-consumer
gradlew clean build
```

The JAR will be created in: `build\libs\brapi-demo-consumer-1.0-SNAPSHOT.jar`

### Step 2: Install in Bookmap

1. **Copy the JAR** from `build\libs\` to your Bookmap addons folder:
   - Usually: `C:\Users\<YourUser>\Bookmap\AddOns\` 
   - Or: `C:\Program Files\Bookmap\addons\`

2. **Restart Bookmap**

### Step 3: Enable the Addon

1. In Bookmap, go to **Settings → Manage Addons**
2. Look for **"SI Broadcasting Consumer"**
3. Enable it by checking the box
4. Click OK

### Step 4: Verify Startup (Check Logs)

Open Bookmap's log file (usually at `C:\Users\<YourUser>\Bookmap\logs\`)

Look for these startup messages:
```
========================================
SI Broadcasting Consumer: STARTING UP
========================================
StopsIcebergsConsumer: Broadcaster created and started successfully
Waiting for Stops & Icebergs events...
Log file: F:/TradingAgent/si_events.log
JSON file: F:/TradingAgent/si_data.json
DB file: F:/TradingAgent/si_events_db.csv
```

If you see these, **the addon loaded successfully!**

### Step 5: Verify UI Panel

1. Open a chart in Bookmap
2. Right-click on the chart → **Indicators**
3. Look for **"SI Broadcasting Consumer"** in the list
4. Add it to the chart
5. You should see a panel with:
   - **Statistics** showing "Waiting for events..."
   - A **black console** with green text for live event logs

### Step 6: Check for Events

The addon will log **ALL** incoming messages to help debug. Check:

**Bookmap Console/Logs:**
```
SI Consumer received message: <ClassName>
```

You'll see many messages. When Stop/Iceberg events arrive, you'll see:
```
[FOUND] Detected StopEvent: <ClassName>
[STOP #1] BUY ORDER123 @ 4500.00, size=10, totalSize=100
```

**Your Log Files:**
- `F:\TradingAgent\si_events.log` - Detailed event log
- `F:\TradingAgent\si_events_db.csv` - CSV export for database
- `F:\TradingAgent\si_data.json` - JSON summary (saved every 10 events)

### Step 7: Enable the Stops & Icebergs Provider

**IMPORTANT:** For this consumer to receive events, you need:

1. **The "Stops & Icebergs On-Chart" addon** to be installed and enabled
2. That addon must be **active on the same instrument** you're watching
3. The provider JAR must be in the classpath

If you don't have the Stops & Icebergs provider:
- Install it from Bookmap Marketplace
- Or add its JAR to `providers/modules/` folder
- The JAR name might be similar to: `StopsIcebergs-X.X.X.jar`

### Troubleshooting

#### No startup messages in logs
- Addon didn't load - check for compilation errors
- Wrong JAR location - verify Bookmap addons path
- Conflicting addon name - check for duplicates

#### Addon loads but no events received
- Check if Stops & Icebergs On-Chart provider is enabled
- Verify the provider is active on the instrument
- Check Bookmap logs for provider connection messages
- The provider JAR might not be on the classpath

#### See "SI Consumer received message: ..." but no events
The logging shows what messages the addon receives. If you see:
- `UserMessageLayersChainCreatedTargeted` - Normal startup message
- `CurrentTimeUserMessage` - Clock ticks (normal)
- Messages with "stop" or "iceberg" in the name - These should trigger events!

If you see stop/iceberg messages but they're not being processed:
- The class name detection might not match
- Check the exact class name in logs
- Update the detection logic if needed

### Expected Behavior When Working

1. **On Bookmap startup:**
   - Logs show "SI Broadcasting Consumer: STARTING UP"
   - Broadcaster starts successfully

2. **When chart opens:**
   - UI panel appears
   - Shows "Waiting for events..."

3. **When Stop event detected:**
   - Console logs: `[STOP #X] BUY/SELL ...`
   - UI updates with count
   - Entry added to CSV file
   - Every 10 events: JSON file updated

4. **When Iceberg event detected:**
   - Console logs: `[ICEBERG #X] [DETECTION/TRADE/...] ...`
   - UI updates with count
   - Entry added to CSV file
   - Every 10 events: JSON file updated

### Quick Test Without Provider

To test the addon is receiving messages (even without the Stops & Icebergs provider):

1. Enable the addon
2. Open a chart
3. Check Bookmap logs

You should see:
```
SI Consumer received message: velox.api.layer1.messages.CurrentTimeUserMessage
SI Consumer received message: velox.api.layer1.messages.UserMessageLayersChainCreatedTargeted
... (various other messages)
```

This confirms the addon is **loaded and listening**. It just needs the Stops & Icebergs provider to send the actual events.

### Files to Monitor

Watch these files to confirm events are being captured:

```cmd
# Watch the log file (auto-refreshes)
Get-Content F:\TradingAgent\si_events.log -Wait

# Check if CSV is being written
Get-Content F:\TradingAgent\si_events_db.csv | Select-Object -Last 10

# View JSON summary
Get-Content F:\TradingAgent\si_data.json
```

## Summary

✅ **Addon is working if:**
- Startup logs appear
- UI panel loads
- "SI Consumer received message" logs appear
- Files are created in F:\TradingAgent\

✅ **Events are being captured if:**
- "[STOP #X]" or "[ICEBERG #X]" logs appear
- Statistics in UI panel update
- CSV file contains event data
- JSON file shows event counts

❌ **Not working if:**
- No startup logs
- UI panel doesn't appear
- No messages logged at all
- Exception errors in Bookmap logs

