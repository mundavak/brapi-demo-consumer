# MNQ Bias Generator - Interactive Backtesting

## Overview

Interactive backtesting tool for validating MNQ bias generator accuracy using historical data.

## Features

- ✅ **Interactive date selection** - Choose from presets or custom ranges
- ✅ **Data availability check** - Shows available data ranges before backtesting
- ✅ **Day-by-day analysis** - Calculates bias and compares with actual outcomes
- ✅ **Performance metrics** - Win rate, accuracy by bias type, target hit rates
- ✅ **CSV export** - Export detailed results for further analysis
- ✅ **P/L analysis** - Simulated profit/loss based on VWAP SD targets

## Usage

### Run Interactive Backtest

```powershell
python backend/backtest_bias_generator.py
```

### Date Range Options

1. **Last 7 days** - Quick recent performance check
2. **Last 30 days** - Monthly performance analysis
3. **Last 90 days** - Quarterly trend analysis
4. **Full range** - All available data (limited by MBO data availability)
5. **Custom range** - Specify exact start/end dates

### Example Session

```
================================================================================
MNQ BIAS GENERATOR - INTERACTIVE BACKTESTING
================================================================================

AVAILABLE DATA RANGES
================================================================================

5m OHLC Candles:
  Range: 2025-10-07 to 2025-11-17
  Count: 8,160 candles

Absorption Data:
  Range: 2025-11-11 to 2025-11-12
  Count: 215,678 events

Common Data Range (all sources available):
  Start: 2025-11-11
  End:   2025-11-12
  Days:  1

SELECT BACKTEST DATE RANGE
================================================================================

Select option (1-5): 4
Backtesting from 2025-11-11 to 2025-11-12
Proceed? (y/n): y

BACKTESTING BIAS GENERATOR
Date Range: 2025-11-11 to 2025-11-12
================================================================================

[1/2] Analyzing 2025-11-11... ✓ STRONG_BEARISH → BEARISH (-15.25)
[2/2] Analyzing 2025-11-12... ✓ BULLISH → BULLISH (+22.50)

BACKTEST RESULTS SUMMARY
================================================================================

Overall Performance:
  Total Days:     2
  Correct:        2 (100.0%)
  Wrong:          0 (0.0%)
  Win Rate:       100.0%

By Bias Type:
  Bullish:  1/1 (100.0%)
  Bearish:  1/1 (100.0%)

VWAP SD Target Hit Rates:
  +1 SD: 1/2 (50.0%)
  +2 SD: 0/2 (0.0%)
  -1 SD: 1/2 (50.0%)
  -2 SD: 1/2 (50.0%)
```

## Output Files

### CSV Export Location

`outputs/backtests/backtest_YYYYMMDD_YYYYMMDD_HHMMSS.csv`

### CSV Columns

- `date` - Trading day
- `bias_category` - Predicted bias (STRONG_BULLISH, BULLISH, NEUTRAL, BEARISH, STRONG_BEARISH)
- `bias_score` - Numerical bias score (0-100)
- `confidence` - Prediction confidence (%)
- `start_price` - Price at analysis time (9:30 AM)
- `end_price` - Price at market close (4:00 PM)
- `price_change` - Dollar change
- `price_change_pct` - Percentage change
- `actual_direction` - Actual market direction
- `accuracy` - CORRECT/WRONG/PARTIAL
- `day_low` - Session low
- `day_high` - Session high
- `hit_plus_1sd` - Did price reach +1 SD?
- `hit_plus_2sd` - Did price reach +2 SD?
- `hit_plus_3sd` - Did price reach +3 SD?
- `hit_minus_1sd` - Did price reach -1 SD?
- `hit_minus_2sd` - Did price reach -2 SD?
- `hit_minus_3sd` - Did price reach -3 SD?

## Data Requirements

### Minimum Required Data

- ✅ **OHLC Candles** (5m timeframe) - Price action data
- ✅ **VWAP Levels** - Daily and 9:30 AM VWAP
- ✅ **Absorption Events** - Buy/sell absorption detection
- ✅ **Stops & Icebergs** - Hidden order detection

### Current Data Availability

Your system has:

- **5m Candles**: Oct 7 - Nov 17 (8,160 candles)
- **VWAP**: Sep 10, 2024 - Nov 17, 2025 (1,847 records)
- **Absorption**: Nov 11-12 (215k events) ⚠️ **LIMITED**
- **Stops/Icebergs**: Oct 29 - Nov 17 (753k events)

**Note**: Absorption data is currently the limiting factor. Common range is Nov 11-12 only.

## Extending Data Range

To backtest further back, you need more absorption and MBO data. Options:

1. **Capture live data** - Run Bookmap consumers longer to build historical data
2. **Import historical MBO** - If you have historical MBO data archives
3. **Use OHLC-only mode** - Modify backtest to work without absorption (reduced accuracy)

## Performance Metrics Explained

### Win Rate

- Percentage of days where bias correctly predicted market direction
- **Target**: 60%+ for profitable trading

### By Bias Type

- Separate accuracy for BULLISH vs BEARISH predictions
- Helps identify if system has directional bias

### VWAP SD Target Hit Rates

- How often each standard deviation level is reached
- **+1/-1 SD**: Should hit 60-70% (institutional first target)
- **+2/-2 SD**: Should hit 30-40% (extended move)
- **+3/-3 SD**: Should hit 10-20% (extreme outlier)

### P/L Analysis

- Simulates 1 contract trades
- Assumes entry at start price, exit at +/-1 SD target
- Stop loss at 100 ticks (25 points) for wrong predictions

## Tips for Analysis

1. **Look for patterns** - Do certain ICT phases have higher accuracy?
2. **Check Kill Zones** - Are certain time periods more reliable?
3. **FVG confluence** - Do days with multiple FVGs perform better?
4. **Market Structure** - Does recent MSS improve prediction?
5. **VWAP position** - Is accuracy better when price is near VWAP?

## Next Steps

After backtesting:

1. Review CSV export for patterns
2. Adjust bias calculation weights based on results
3. Add more data sources for longer backtests
4. Consider machine learning on backtest features

## Troubleshooting

### "No trading days found"

- Check date range is within available data
- Ensure OHLC candles exist for selected period

### "Insufficient data for bias calculation"

- MBO data (absorption/stops) may be missing for some days
- System skips days without required data

### ImportError

- Ensure you're running from `backend/` directory
- Check `generate_bias_report.py` is in same folder

## Example: Analyzing Results in Excel

1. Open exported CSV in Excel
2. Create pivot table:
   - Rows: `bias_category`
   - Values: Count of `accuracy` (filter to "CORRECT")
3. Calculate win rate per bias type
4. Create scatter plot: `bias_score` vs `price_change`
5. Analyze which factors correlate with accuracy
