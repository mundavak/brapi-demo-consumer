# Automated Daily Candle Import

Automatically imports MNQ candle data from TradingView CSV exports every day at 9:20 AM.

## Features

- ✅ **Auto-detects timeframe** by analyzing timestamp increments (5m, 15m, 1h, etc.)
- ✅ **Duplicate detection** - checks database before importing to skip existing data
- ✅ **Auto-cleanup** - deletes CSV files after successful import
- ✅ **Flexible column detection** - finds time/open/high/low/close columns regardless of case
- ✅ **Batch processing** with conflict prevention (skips duplicate candles)
- ✅ **Comprehensive logging** to `outputs/logs/import_candles.log`
- ✅ **Database validation** - shows summary statistics after import
- ✅ **Error handling** - skips invalid rows, continues processing

## Setup (One-Time)

```powershell
# Run setup script (creates Task Scheduler task)
.\scripts\setup_daily_candle_import.ps1
```

This creates a Windows scheduled task that runs daily at 9:20 AM EST.

## CSV Requirements

**Location:** `C:\Users\Kudzai\Downloads\TradingView_Data\`

**Format:** Any CSV with these columns (case-insensitive):

- `time` or `timestamp` - ISO format timestamps (e.g., `2025-11-17T07:00:00-05:00`)
- `open`, `high`, `low`, `close` - Price values
- `volume` (optional)

**Timeframe Detection:**
The script analyzes the actual time increments between rows to determine timeframe:

- 5-minute intervals → `5m`
- 15-minute intervals → `15m`
- 60-minute intervals → `1h`
- etc.

## Daily Operation

### Automated Run

- **Time:** 9:20 AM EST daily
- **What it does:**
  1. Scans `TradingView_Data` folder for CSV files
  2. Auto-detects timeframe from each file
  3. Imports candles (updates existing if conflicts)
  4. Logs results to `import_candles.log`

### Manual Run

```powershell
# Run import immediately
.\scripts\run_candle_import.ps1

# Or run the Python script directly
cd backend
python auto_import_candles.py
```

## Monitoring

### View Recent Logs

```powershell
# Last 50 lines
Get-Content outputs\logs\import_candles.log -Tail 50

# Live tail (watch in real-time)
Get-Content outputs\logs\import_candles.log -Wait -Tail 20
```

### Check Task Status

```powershell
# View task details
Get-ScheduledTask -TaskName "Bookmap Candle Import" | Format-List *

# View last run result
Get-ScheduledTaskInfo -TaskName "Bookmap Candle Import"

# View task history
Get-WinEvent -LogName "Microsoft-Windows-TaskScheduler/Operational" |
    Where-Object {$_.Message -like "*Bookmap Candle Import*"} |
    Select-Object TimeCreated, Message -First 10
```

## Task Management

```powershell
# Run immediately (test)
Start-ScheduledTask -TaskName "Bookmap Candle Import"

# Disable (stop automatic runs)
Disable-ScheduledTask -TaskName "Bookmap Candle Import"

# Enable (resume automatic runs)
Enable-ScheduledTask -TaskName "Bookmap Candle Import"

# Remove task completely
Unregister-ScheduledTask -TaskName "Bookmap Candle Import" -Confirm:$false
```

## Database Verification

After import, check the database:

```sql
-- View recent imports by timeframe
SELECT
    timeframe,
    COUNT(*) as candle_count,
    MIN(timestamp) as earliest,
    MAX(timestamp) as latest,
    MIN(close) as min_price,
    MAX(close) as max_price
FROM ohlc_candles
WHERE symbol = 'MNQ'
GROUP BY timeframe
ORDER BY timeframe;

-- Check today's imports
SELECT
    timeframe,
    COUNT(*) as count
FROM ohlc_candles
WHERE symbol = 'MNQ'
  AND session_id LIKE 'auto_import_%'
  AND timestamp::date = CURRENT_DATE
GROUP BY timeframe;

-- Check for gaps
SELECT
    timeframe,
    timestamp as gap_start,
    LEAD(timestamp) OVER (PARTITION BY timeframe ORDER BY timestamp) as gap_end,
    EXTRACT(EPOCH FROM (LEAD(timestamp) OVER (PARTITION BY timeframe ORDER BY timestamp) - timestamp))/60 as gap_minutes
FROM ohlc_candles
WHERE symbol = 'MNQ'
  AND timeframe = '5m'
ORDER BY gap_minutes DESC NULLS LAST
LIMIT 20;
```

## Troubleshooting

### Import Fails

1. Check log file: `outputs\logs\import_candles.log`
2. Verify CSV files exist in `C:\Users\Kudzai\Downloads\TradingView_Data\`
3. Test database connection: `psql -U postgres -d trading_data`

### No CSVs Found

- Ensure TradingView exports to the correct directory
- Check filename patterns (script processes all `.csv` files)

### Wrong Timeframe Detected

- Check the `time` column increments
- Verify timestamps are in ISO format with timezone
- Look for irregular intervals (market close gaps are normal)

### Task Doesn't Run

```powershell
# Check task status
Get-ScheduledTask -TaskName "Bookmap Candle Import"

# View task history/errors
Get-ScheduledTaskInfo -TaskName "Bookmap Candle Import"

# Ensure task is enabled
Enable-ScheduledTask -TaskName "Bookmap Candle Import"

# Test manually
Start-ScheduledTask -TaskName "Bookmap Candle Import"
```

## Workflow Integration

This automated import integrates with the daily data pipeline:

```
9:05 AM  → Bookmap Morning Session Export (run_daily_pipeline.py)
         → Exports 6-9 AM trading data to n8n
         → n8n triggers Gemini AI analysis

9:20 AM  → Automated Candle Import (auto_import_candles.py)
         → Imports TradingView historical candles
         → Updates TimescaleDB with latest data
```

Both processes run independently and log to separate files:

- Bookmap export: `export_daily_session.log`
- Candle import: `import_candles.log`

## Timeframe Detection Logic

The script samples the first 50 rows and calculates time differences:

```python
# Example: 5-minute candles
07:00:00 → 07:05:00 = 5 minutes
07:05:00 → 07:10:00 = 5 minutes
07:10:00 → 07:15:00 = 5 minutes
Most common interval: 5 minutes → Timeframe: 5m

# Example: 15-minute candles
07:00:00 → 07:15:00 = 15 minutes
07:15:00 → 07:30:00 = 15 minutes
Most common interval: 15 minutes → Timeframe: 15m
```

Supported timeframes:

- `1m` - 1 minute
- `5m` - 5 minutes
- `15m` - 15 minutes
- `30m` - 30 minutes
- `1h` - 1 hour (60 minutes)
- `4h` - 4 hours (240 minutes)
- `1d` - 1 day (1440 minutes)

## Files Structure

```
brapi-demo-consumer/
├── backend/
│   ├── auto_import_candles.py        # Main import script
│   └── import_mnq_candles.py         # Legacy manual import
├── scripts/
│   ├── setup_daily_candle_import.ps1 # Task Scheduler setup
│   └── run_candle_import.ps1         # Manual trigger
├── docs/
│   └── AUTOMATED_CANDLE_IMPORT.md    # This file
└── outputs/
    └── logs/
        └── import_candles.log        # Operation logs
```

## Example Log Output

```
2025-11-17 09:20:01 - INFO - ============================================================
2025-11-17 09:20:01 - INFO - Starting automated candle import
2025-11-17 09:20:01 - INFO - ============================================================
2025-11-17 09:20:01 - INFO - Found 2 CSV files
2025-11-17 09:20:01 - INFO - Connected to database
2025-11-17 09:20:01 - INFO - Detected timeframe: 5m (interval: 5.0 min)
2025-11-17 09:20:01 - INFO - Importing MNQ_5m_MNQ1!_2025-11-17T12-01-56.csv (timeframe: 5m)
2025-11-17 09:20:02 - INFO - ✓ Imported 300 rows from MNQ_5m_MNQ1!_2025-11-17T12-01-56.csv
2025-11-17 09:20:02 - INFO - Detected timeframe: 15m (interval: 15.0 min)
2025-11-17 09:20:02 - INFO - Importing MNQ_15m_MNQ1!_2025-11-17T12-01-17.csv (timeframe: 15m)
2025-11-17 09:20:03 - INFO - ✓ Imported 461 rows from MNQ_15m_MNQ1!_2025-11-17T12-01-17.csv
2025-11-17 09:20:03 - INFO - ============================================================
2025-11-17 09:20:03 - INFO - Import complete!
2025-11-17 09:20:03 - INFO -   Files processed: 2
2025-11-17 09:20:03 - INFO -   Successful imports: 2
2025-11-17 09:20:03 - INFO -   Total rows imported: 761
2025-11-17 09:20:03 - INFO -   Timeframes: 15m, 5m
2025-11-17 09:20:03 - INFO - ============================================================
```

## Support

For issues or questions:

1. Check the log file first: `outputs/logs/import_candles.log`
2. Verify CSV format matches requirements
3. Test database connection manually
4. Run import manually to see errors: `.\scripts\run_candle_import.ps1`
