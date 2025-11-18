#!/usr/bin/env python3
"""
Interactive Backtesting for MNQ Bias Generator

Features:
- Backtest bias accuracy against historical data
- Interactive date range selection based on available MBO data
- Performance metrics: win rate, average profit/loss, Sharpe ratio
- Day-by-day bias reports with actual outcomes
- Export results to CSV for analysis

Usage:
  python backtest_bias_generator.py              # Interactive mode
  python backtest_bias_generator.py --auto       # Auto mode (full range, auto-export)
  python backtest_bias_generator.py --days 30    # Auto mode (last 30 days)
"""

import psycopg2
from datetime import datetime, timedelta
import pytz
import json
from pathlib import Path
import csv
from collections import defaultdict
import argparse

# Import bias calculation functions from main generator
import sys

sys.path.append(str(Path(__file__).parent))

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}

# Import timezone
EST = pytz.timezone("America/New_York")


def get_available_data_range(cursor):
    """Get the earliest and latest dates for all required data sources"""
    print("\n" + "=" * 80)
    print("AVAILABLE DATA RANGES")
    print("=" * 80)

    ranges = {}

    # Check OHLC candles (5m)
    cursor.execute(
        """
        SELECT MIN(timestamp), MAX(timestamp), COUNT(*)
        FROM ohlc_candles
        WHERE symbol = 'MNQ' AND timeframe = '5m'
    """
    )
    min_ohlc, max_ohlc, count_ohlc = cursor.fetchone()
    ranges["ohlc_5m"] = (min_ohlc, max_ohlc, count_ohlc)
    print(f"\n5m OHLC Candles:")
    print(f"  Range: {min_ohlc} to {max_ohlc}")
    print(f"  Count: {count_ohlc:,} candles")

    # Check VWAP data
    cursor.execute(
        """
        SELECT MIN(timestamp), MAX(timestamp), COUNT(*)
        FROM vwap_levels
        WHERE symbol = 'MNQ'
    """
    )
    min_vwap, max_vwap, count_vwap = cursor.fetchone()
    ranges["vwap"] = (min_vwap, max_vwap, count_vwap)
    print(f"\nVWAP Levels:")
    print(f"  Range: {min_vwap} to {max_vwap}")
    print(f"  Count: {count_vwap:,} records")

    # Check absorption data (all symbols)
    cursor.execute(
        """
        SELECT MIN(timestamp), MAX(timestamp), COUNT(*)
        FROM absorption_events
    """
    )
    result = cursor.fetchone()
    if result and result[0]:
        min_abs, max_abs, count_abs = result
        ranges["absorption"] = (min_abs, max_abs, count_abs)
        print(f"\nAbsorption Data:")
        print(f"  Range: {min_abs} to {max_abs}")
        print(f"  Count: {count_abs:,} events")

    # Check stops/icebergs data (all symbols)
    cursor.execute(
        """
        SELECT MIN(timestamp), MAX(timestamp), COUNT(*)
        FROM stops_icebergs
    """
    )
    result = cursor.fetchone()
    if result and result[0]:
        min_stops, max_stops, count_stops = result
        ranges["stops_icebergs"] = (min_stops, max_stops, count_stops)
        print(f"\nStops & Icebergs Data:")
        print(f"  Range: {min_stops} to {max_stops}")
        print(f"  Count: {count_stops:,} events")

    # Determine the common date range (intersection of all data sources)
    earliest_start = max([r[0] for r in ranges.values() if r[0]])
    latest_end = min([r[1] for r in ranges.values() if r[1]])

    print("\n" + "-" * 80)
    print(f"\nCommon Data Range (all sources available):")
    print(f"  Start: {earliest_start}")
    print(f"  End:   {latest_end}")
    print(f"  Days:  {(latest_end - earliest_start).days}")

    return earliest_start, latest_end, ranges


def get_trading_days(cursor, start_date, end_date):
    """Get list of trading days with sufficient data"""
    cursor.execute(
        """
        SELECT DISTINCT DATE(timestamp) as trade_date
        FROM ohlc_candles
        WHERE symbol = 'MNQ' 
        AND timeframe = '5m'
        AND timestamp >= %s
        AND timestamp <= %s
        AND EXTRACT(DOW FROM timestamp) NOT IN (0, 6)  -- Exclude weekends
        ORDER BY trade_date
    """,
        (start_date, end_date),
    )

    trading_days = [row[0] for row in cursor.fetchall()]
    return trading_days


def get_day_range(trade_date):
    """Get start/end timestamps for a trading day (8:45 PM prev day to 5:00 PM current day EST)"""
    # Start at 8:45 PM previous day (overnight session start)
    prev_day = trade_date - timedelta(days=1)
    start_time = EST.localize(
        datetime.combine(prev_day, datetime.min.time().replace(hour=20, minute=45))
    )

    # End at 5:00 PM current day (market close)
    end_time = EST.localize(
        datetime.combine(trade_date, datetime.min.time().replace(hour=17, minute=0))
    )

    return start_time, end_time


def calculate_day_bias(cursor, start_time, end_time):
    """Calculate bias for a specific day using same logic as generate_bias_report.py"""
    from generate_bias_report import (
        analyze_overnight_structure,
        analyze_absorption,
        analyze_icebergs,
        analyze_stop_clusters,
        detect_fair_value_gaps,
        detect_market_structure_shift,
        calculate_ipda_ranges,
        analyze_vwap,
        calculate_vwap_standard_deviations,
        calculate_bias,
        get_ict_kill_zone,
        get_power_of_three_phase,
    )

    try:
        # Run all analyses (suppress print output)
        structure = analyze_overnight_structure(cursor, start_time, end_time)
        absorption_zones = analyze_absorption(cursor, start_time, end_time)
        iceberg_positions = analyze_icebergs(cursor, start_time, end_time)
        stop_zones = analyze_stop_clusters(cursor, start_time, end_time)
        fvgs = detect_fair_value_gaps(cursor, start_time, end_time)
        mss_events = detect_market_structure_shift(cursor, start_time, end_time)
        ipda_ranges = calculate_ipda_ranges(cursor, end_time)
        vwap_analysis = analyze_vwap(cursor, start_time, end_time)

        # Get ICT context
        kill_zone = get_ict_kill_zone()
        po3_phase = get_power_of_three_phase(cursor, start_time, end_time)

        # Calculate VWAP bands
        vwap_bands = None
        if vwap_analysis and "vwap_daily" in vwap_analysis:
            vwap_bands = calculate_vwap_standard_deviations(
                cursor, end_time, vwap_analysis["vwap_daily"]
            )

        # Calculate bias
        bias = calculate_bias(
            structure,
            absorption_zones,
            iceberg_positions,
            stop_zones,
            vwap_analysis,
            fvgs,
            mss_events,
            ipda_ranges,
            po3_phase,
            kill_zone,
        )

        return {
            "bias_score": bias["bias_score"],
            "bias_category": bias["bias_category"],
            "confidence": bias[
                "confidence_score"
            ],  # Fixed: use confidence_score from bias dict
            "current_price": structure["current_price"],
            "overnight_low": structure["overnight_low"],
            "overnight_high": structure["overnight_high"],
            "vwap_daily": vwap_analysis.get("vwap_daily") if vwap_analysis else None,
            "vwap_bands": vwap_bands,
            "fvg_count": len(fvgs) if fvgs else 0,
            "mss_count": len(mss_events) if mss_events else 0,
        }
    except Exception as e:
        print(f"Error calculating bias: {e}")
        return None


def get_actual_outcome(cursor, trade_date, start_price, vwap_bands):
    """Determine actual price movement and if targets were hit"""
    # Get price action during trading day (9:30 AM to 4:00 PM)
    day_start = EST.localize(
        datetime.combine(trade_date, datetime.min.time().replace(hour=9, minute=30))
    )
    day_end = EST.localize(
        datetime.combine(trade_date, datetime.min.time().replace(hour=16, minute=0))
    )

    cursor.execute(
        """
        SELECT MIN(low), MAX(high), 
               (SELECT close FROM ohlc_candles 
                WHERE symbol = 'MNQ' AND timeframe = '5m' 
                AND timestamp <= %s 
                ORDER BY timestamp DESC LIMIT 1) as end_price
        FROM ohlc_candles
        WHERE symbol = 'MNQ'
        AND timeframe = '5m'
        AND timestamp BETWEEN %s AND %s
    """,
        (day_end, day_start, day_end),
    )

    result = cursor.fetchone()
    if not result or not result[0]:
        return None

    day_low, day_high, end_price = result
    price_change = end_price - start_price
    price_change_pct = (price_change / start_price) * 100

    outcome = {
        "day_low": float(day_low),
        "day_high": float(day_high),
        "end_price": float(end_price),
        "price_change": float(price_change),
        "price_change_pct": float(price_change_pct),
        "direction": (
            "BULLISH"
            if price_change > 0
            else "BEARISH" if price_change < 0 else "NEUTRAL"
        ),
    }

    # Check if VWAP SD targets were hit
    if vwap_bands:
        outcome["hit_plus_1sd"] = day_high >= vwap_bands["+1sd"]
        outcome["hit_plus_2sd"] = day_high >= vwap_bands["+2sd"]
        outcome["hit_plus_3sd"] = day_high >= vwap_bands["+3sd"]
        outcome["hit_minus_1sd"] = day_low <= vwap_bands["-1sd"]
        outcome["hit_minus_2sd"] = day_low <= vwap_bands["-2sd"]
        outcome["hit_minus_3sd"] = day_low <= vwap_bands["-3sd"]

    return outcome


def evaluate_bias_accuracy(bias_category, actual_direction):
    """Evaluate if bias prediction was correct"""
    if bias_category in ("STRONG_BULLISH", "BULLISH") and actual_direction == "BULLISH":
        return "CORRECT"
    elif (
        bias_category in ("STRONG_BEARISH", "BEARISH") and actual_direction == "BEARISH"
    ):
        return "CORRECT"
    elif bias_category == "NEUTRAL" and actual_direction == "NEUTRAL":
        return "CORRECT"
    elif actual_direction == "NEUTRAL":
        return "PARTIAL"  # Market didn't move significantly
    else:
        return "WRONG"


def run_backtest(cursor, start_date, end_date):
    """Run backtest over date range"""
    print("\n" + "=" * 80)
    print(f"BACKTESTING BIAS GENERATOR")
    print(f"Date Range: {start_date} to {end_date}")
    print("=" * 80)

    trading_days = get_trading_days(cursor, start_date, end_date)

    if not trading_days:
        print("\n❌ No trading days found in this range")
        return None

    print(f"\nFound {len(trading_days)} trading days to analyze")
    print("Processing...\n")

    results = []
    stats = {
        "total_days": 0,
        "correct": 0,
        "wrong": 0,
        "partial": 0,
        "bullish_correct": 0,
        "bullish_total": 0,
        "bearish_correct": 0,
        "bearish_total": 0,
        "target_hits": defaultdict(int),
    }

    for i, trade_date in enumerate(trading_days, 1):
        print(
            f"[{i}/{len(trading_days)}] Analyzing {trade_date.strftime('%Y-%m-%d')}...",
            end=" ",
        )

        start_time, end_time = get_day_range(trade_date)

        # Calculate bias at market open (9:30 AM)
        analysis_time = EST.localize(
            datetime.combine(trade_date, datetime.min.time().replace(hour=9, minute=30))
        )

        bias_data = calculate_day_bias(cursor, start_time, analysis_time)

        if not bias_data:
            print("❌ No data")
            continue

        # Get actual outcome
        outcome = get_actual_outcome(
            cursor, trade_date, bias_data["current_price"], bias_data.get("vwap_bands")
        )

        if not outcome:
            print("❌ No outcome data")
            continue

        # Evaluate accuracy
        accuracy = evaluate_bias_accuracy(
            bias_data["bias_category"], outcome["direction"]
        )

        # Update stats
        stats["total_days"] += 1
        if accuracy == "CORRECT":
            stats["correct"] += 1
            print(
                f"✓ {bias_data['bias_category']} → {outcome['direction']} ({outcome['price_change']:+.2f})"
            )
        elif accuracy == "WRONG":
            stats["wrong"] += 1
            print(
                f"✗ {bias_data['bias_category']} → {outcome['direction']} ({outcome['price_change']:+.2f})"
            )
        else:
            stats["partial"] += 1
            print(
                f"○ {bias_data['bias_category']} → NEUTRAL ({outcome['price_change']:+.2f})"
            )

        # Track by bias type
        if "BULLISH" in bias_data["bias_category"]:
            stats["bullish_total"] += 1
            if accuracy == "CORRECT":
                stats["bullish_correct"] += 1
        elif "BEARISH" in bias_data["bias_category"]:
            stats["bearish_total"] += 1
            if accuracy == "CORRECT":
                stats["bearish_correct"] += 1

        # Track target hits
        if bias_data.get("vwap_bands"):
            if outcome.get("hit_plus_1sd"):
                stats["target_hits"]["plus_1sd"] += 1
            if outcome.get("hit_plus_2sd"):
                stats["target_hits"]["plus_2sd"] += 1
            if outcome.get("hit_plus_3sd"):
                stats["target_hits"]["plus_3sd"] += 1
            if outcome.get("hit_minus_1sd"):
                stats["target_hits"]["minus_1sd"] += 1
            if outcome.get("hit_minus_2sd"):
                stats["target_hits"]["minus_2sd"] += 1
            if outcome.get("hit_minus_3sd"):
                stats["target_hits"]["minus_3sd"] += 1

        # Store result
        results.append(
            {
                "date": trade_date.strftime("%Y-%m-%d"),
                "bias_category": bias_data["bias_category"],
                "bias_score": bias_data["bias_score"],
                "confidence": bias_data["confidence"],
                "start_price": bias_data["current_price"],
                "end_price": outcome["end_price"],
                "price_change": outcome["price_change"],
                "price_change_pct": outcome["price_change_pct"],
                "actual_direction": outcome["direction"],
                "accuracy": accuracy,
                "vwap_bands": bias_data.get("vwap_bands"),
                "outcome": outcome,
            }
        )

    return results, stats


def print_backtest_summary(stats, results):
    """Print backtest performance summary"""
    print("\n" + "=" * 80)
    print("BACKTEST RESULTS SUMMARY")
    print("=" * 80)

    if stats["total_days"] == 0:
        print("\nNo results to display")
        return

    win_rate = (stats["correct"] / stats["total_days"]) * 100

    print(f"\nOverall Performance:")
    print(f"  Total Days:     {stats['total_days']}")
    print(
        f"  Correct:        {stats['correct']} ({stats['correct']/stats['total_days']*100:.1f}%)"
    )
    print(
        f"  Wrong:          {stats['wrong']} ({stats['wrong']/stats['total_days']*100:.1f}%)"
    )
    print(
        f"  Neutral/Partial: {stats['partial']} ({stats['partial']/stats['total_days']*100:.1f}%)"
    )
    print(f"  Win Rate:       {win_rate:.1f}%")

    print(f"\nBy Bias Type:")
    if stats["bullish_total"] > 0:
        bull_rate = (stats["bullish_correct"] / stats["bullish_total"]) * 100
        print(
            f"  Bullish:  {stats['bullish_correct']}/{stats['bullish_total']} ({bull_rate:.1f}%)"
        )
    if stats["bearish_total"] > 0:
        bear_rate = (stats["bearish_correct"] / stats["bearish_total"]) * 100
        print(
            f"  Bearish:  {stats['bearish_correct']}/{stats['bearish_total']} ({bear_rate:.1f}%)"
        )

    print(f"\nVWAP SD Target Hit Rates:")
    if stats["total_days"] > 0:
        print(
            f"  +1 SD: {stats['target_hits']['plus_1sd']}/{stats['total_days']} ({stats['target_hits']['plus_1sd']/stats['total_days']*100:.1f}%)"
        )
        print(
            f"  +2 SD: {stats['target_hits']['plus_2sd']}/{stats['total_days']} ({stats['target_hits']['plus_2sd']/stats['total_days']*100:.1f}%)"
        )
        print(
            f"  +3 SD: {stats['target_hits']['plus_3sd']}/{stats['total_days']} ({stats['target_hits']['plus_3sd']/stats['total_days']*100:.1f}%)"
        )
        print(
            f"  -1 SD: {stats['target_hits']['minus_1sd']}/{stats['total_days']} ({stats['target_hits']['minus_1sd']/stats['total_days']*100:.1f}%)"
        )
        print(
            f"  -2 SD: {stats['target_hits']['minus_2sd']}/{stats['total_days']} ({stats['target_hits']['minus_2sd']/stats['total_days']*100:.1f}%)"
        )
        print(
            f"  -3 SD: {stats['target_hits']['minus_3sd']}/{stats['total_days']} ({stats['target_hits']['minus_3sd']/stats['total_days']*100:.1f}%)"
        )

    # Calculate profit metrics (assuming 1 contract per trade at VWAP -1SD/+1SD targets)
    total_pnl = 0
    winning_trades = 0
    losing_trades = 0

    for result in results:
        if result["accuracy"] == "CORRECT":
            # Assume entry at start price, exit at +/-1SD
            pnl = abs(result["price_change"])
            total_pnl += pnl
            winning_trades += 1
        elif result["accuracy"] == "WRONG":
            # Assume loss of 25 points (100 ticks stop)
            pnl = -25.0
            total_pnl += pnl
            losing_trades += 1

    if stats["total_days"] > 0:
        avg_pnl = total_pnl / stats["total_days"]
        print(f"\nProfit/Loss Analysis (1 contract):")
        print(f"  Total P/L:      ${total_pnl:,.2f}")
        print(f"  Average P/L:    ${avg_pnl:,.2f} per day")
        print(f"  Winning Trades: {winning_trades}")
        print(f"  Losing Trades:  {losing_trades}")


def export_results(results, start_date, end_date):
    """Export backtest results to CSV"""
    output_dir = Path(__file__).parent.parent / "outputs" / "backtests"
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backtest_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{timestamp}.csv"
    filepath = output_dir / filename

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "date",
                "bias_category",
                "bias_score",
                "confidence",
                "start_price",
                "end_price",
                "price_change",
                "price_change_pct",
                "actual_direction",
                "accuracy",
                "day_low",
                "day_high",
                "hit_plus_1sd",
                "hit_plus_2sd",
                "hit_plus_3sd",
                "hit_minus_1sd",
                "hit_minus_2sd",
                "hit_minus_3sd",
            ],
        )
        writer.writeheader()

        for result in results:
            row = {
                "date": result["date"],
                "bias_category": result["bias_category"],
                "bias_score": result["bias_score"],
                "confidence": result["confidence"],
                "start_price": result["start_price"],
                "end_price": result["end_price"],
                "price_change": result["price_change"],
                "price_change_pct": result["price_change_pct"],
                "actual_direction": result["actual_direction"],
                "accuracy": result["accuracy"],
                "day_low": result["outcome"]["day_low"],
                "day_high": result["outcome"]["day_high"],
                "hit_plus_1sd": result["outcome"].get("hit_plus_1sd", False),
                "hit_plus_2sd": result["outcome"].get("hit_plus_2sd", False),
                "hit_plus_3sd": result["outcome"].get("hit_plus_3sd", False),
                "hit_minus_1sd": result["outcome"].get("hit_minus_1sd", False),
                "hit_minus_2sd": result["outcome"].get("hit_minus_2sd", False),
                "hit_minus_3sd": result["outcome"].get("hit_minus_3sd", False),
            }
            writer.writerow(row)

    print(f"\n✓ Results exported to: {filepath}")


def main():
    """Interactive backtesting main"""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Backtest MNQ bias generator")
    parser.add_argument(
        "--auto", action="store_true", help="Auto mode (full range, auto-export)"
    )
    parser.add_argument(
        "--days", type=int, help="Number of days to backtest (auto mode)"
    )
    parser.add_argument(
        "--export", action="store_true", help="Auto-export results to CSV"
    )
    args = parser.parse_args()

    print("\n" + "=" * 80)
    print("MNQ BIAS GENERATOR - INTERACTIVE BACKTESTING")
    print("=" * 80)

    # Connect to database
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        # Get available data ranges
        earliest, latest, ranges = get_available_data_range(cursor)

        if not earliest or not latest:
            print("\n❌ Insufficient data for backtesting")
            return

        today = datetime.now(EST).replace(hour=0, minute=0, second=0, microsecond=0)

        # Auto mode
        if args.auto or args.days:
            if args.days:
                start_date = max(earliest, today - timedelta(days=args.days))
            else:
                start_date = earliest
            end_date = latest
            print(
                f"\n🤖 AUTO MODE: Backtesting from {start_date.date()} to {end_date.date()}"
            )

        # Interactive mode
        else:
            # Interactive date selection
            print("\n" + "=" * 80)
            print("SELECT BACKTEST DATE RANGE")
            print("=" * 80)

            print(f"\nAvailable range: {earliest.date()} to {latest.date()}")
            print("\nPreset Options:")
            print("  1. Last 7 days")
            print("  2. Last 30 days")
            print("  3. Last 90 days")
            print("  4. Full range (all available data)")
            print("  5. Custom date range")

            choice = input("\nSelect option (1-5): ").strip()

            if choice == "1":
                start_date = max(earliest, today - timedelta(days=7))
                end_date = latest
            elif choice == "2":
                start_date = max(earliest, today - timedelta(days=30))
                end_date = latest
            elif choice == "3":
                start_date = max(earliest, today - timedelta(days=90))
                end_date = latest
            elif choice == "4":
                start_date = earliest
                end_date = latest
            elif choice == "5":
                start_input = input(
                    f"Start date (YYYY-MM-DD) [{earliest.date()}]: "
                ).strip()
                end_input = input(f"End date (YYYY-MM-DD) [{latest.date()}]: ").strip()

                start_date = (
                    datetime.strptime(start_input, "%Y-%m-%d")
                    if start_input
                    else earliest
                )
                end_date = (
                    datetime.strptime(end_input, "%Y-%m-%d") if end_input else latest
                )

                start_date = (
                    EST.localize(start_date)
                    if start_date.tzinfo is None
                    else start_date
                )
                end_date = (
                    EST.localize(end_date) if end_date.tzinfo is None else end_date
                )
            else:
                print("Invalid choice, using last 7 days")
                start_date = max(earliest, today - timedelta(days=7))
                end_date = latest

            # Confirm selection
            print(f"\nBacktesting from {start_date.date()} to {end_date.date()}")
            confirm = input("Proceed? (y/n): ").strip().lower()

            if confirm != "y":
                print("Backtest cancelled")
                return

        # Run backtest
        results, stats = run_backtest(cursor, start_date, end_date)

        if results:
            # Print summary
            print_backtest_summary(stats, results)

            # Export results
            if args.auto or args.export:
                export_results(results, start_date, end_date)
            else:
                export = input("\nExport results to CSV? (y/n): ").strip().lower()
                if export == "y":
                    export_results(results, start_date, end_date)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        cursor.close()
        conn.close()
        print("\n" + "=" * 80)
        print("Backtest complete")
        print("=" * 80)


if __name__ == "__main__":
    main()
