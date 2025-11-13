"""
Analyze MBO data to find when institutions EXECUTE (fill) their orders.

This script analyzes Market-By-Order (MBO) data to identify patterns in institutional
order executions, focusing on action='T' (Trade/Execute) and action='F' (Fill).

Key Metrics:
- Time of day distribution (by hour)
- Day of week patterns
- Order size analysis (institutional orders typically larger)
- Execution frequency
"""

import pandas as pd
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Configuration
MBO_DATA_DIR = Path("H:/mbo_csv")
OUTPUT_DIR = Path(
    "F:/TradingAgent/deaProjects/brapi-demo-consumer/outputs/mbo_analysis"
)
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Institutional order thresholds for MNQ
MIN_INSTITUTIONAL_SIZE = 20  # Contracts - 20+ is significant institutional size
WHALE_SIZE = 50  # Contracts - 50+ is whale territory
MEGA_WHALE_SIZE = 100  # Contracts - 100+ is mega whale


def analyze_executions(csv_file):
    """Analyze a single MBO CSV file for execution patterns."""
    print(f"\n{'='*80}")
    print(f"Analyzing Executions: {csv_file.name}")
    print(f"{'='*80}")

    try:
        # Read CSV with specific dtypes for efficiency
        df = pd.read_csv(
            csv_file,
            usecols=["ts_event", "action", "side", "price", "size", "symbol"],
            dtype={
                "action": str,
                "side": str,
                "price": float,
                "size": int,
                "symbol": str,
            },
        )

        print(f"Total rows: {len(df):,}")

        # Filter for executions (action='T' = Trade, action='F' = Fill)
        executions = df[df["action"].isin(["T", "F"])].copy()
        print(f"Total executions (action='T' or 'F'): {len(executions):,}")

        if len(executions) == 0:
            print("⚠️ No executions found in this file")
            return None

        # Parse timestamps
        executions["timestamp"] = pd.to_datetime(executions["ts_event"], utc=True)
        executions = executions.dropna(subset=["timestamp"])

        # Convert to EST (UTC-5)
        executions["timestamp_est"] = executions["timestamp"].dt.tz_convert(
            "US/Eastern"
        )

        # Extract time components
        executions["hour"] = executions["timestamp_est"].dt.hour
        executions["minute"] = executions["timestamp_est"].dt.minute
        executions["day_of_week"] = executions["timestamp_est"].dt.day_name()

        # Filter for institutional-sized executions
        institutional = executions[executions["size"] >= MIN_INSTITUTIONAL_SIZE].copy()
        whales = executions[executions["size"] >= WHALE_SIZE].copy()
        mega_whales = executions[executions["size"] >= MEGA_WHALE_SIZE].copy()

        print(
            f"\nInstitutional executions (size >= {MIN_INSTITUTIONAL_SIZE}): {len(institutional):,}"
        )
        print(
            f"Percentage of total executions: {len(institutional)/len(executions)*100:.2f}%"
        )
        print(f"\n🐋 Whale executions (size >= {WHALE_SIZE}): {len(whales):,}")
        print(f"Percentage of total: {len(whales)/len(executions)*100:.2f}%")
        print(
            f"\n🐋🐋 Mega whale executions (size >= {MEGA_WHALE_SIZE}): {len(mega_whales):,}"
        )
        print(f"Percentage of total: {len(mega_whales)/len(executions)*100:.2f}%")

        # Analyze by side
        buy_execs = institutional[institutional["side"] == "B"]
        sell_execs = institutional[institutional["side"] == "A"]

        print(f"\nInstitutional Buy executions: {len(buy_execs):,}")
        print(f"Institutional Sell executions: {len(sell_execs):,}")

        return {
            "file": csv_file.name,
            "date": csv_file.stem.split("-")[-1],
            "total_executions": len(executions),
            "institutional_executions": len(institutional),
            "whale_executions": len(whales),
            "mega_whale_executions": len(mega_whales),
            "buy_executions": len(buy_execs),
            "sell_executions": len(sell_execs),
            "hourly_dist": institutional.groupby("hour").size().to_dict(),
            "whale_hourly_dist": (
                whales.groupby("hour").size().to_dict() if len(whales) > 0 else {}
            ),
            "dow_dist": institutional.groupby("day_of_week").size().to_dict(),
            "avg_size": institutional["size"].mean(),
            "median_size": institutional["size"].median(),
            "max_size": institutional["size"].max(),
        }

    except Exception as e:
        print(f"❌ Error processing {csv_file.name}: {e}")
        return None


def aggregate_analysis(results):
    """Aggregate results across all files."""
    print(f"\n\n{'='*80}")
    print("AGGREGATE ANALYSIS - WHEN DO INSTITUTIONS EXECUTE ORDERS?")
    print(f"{'='*80}\n")

    # Combine hourly distributions
    hourly_totals = defaultdict(int)
    whale_hourly_totals = defaultdict(int)
    dow_totals = defaultdict(int)

    total_institutional = 0
    total_whales = 0
    total_mega_whales = 0
    total_executions = 0

    for result in results:
        if result:
            total_institutional += result["institutional_executions"]
            total_whales += result["whale_executions"]
            total_mega_whales += result["mega_whale_executions"]
            total_executions += result["total_executions"]

            for hour, count in result["hourly_dist"].items():
                hourly_totals[hour] += count

            for hour, count in result["whale_hourly_dist"].items():
                whale_hourly_totals[hour] += count

            for dow, count in result["dow_dist"].items():
                dow_totals[dow] += count

    print(f"📊 Total Files Analyzed: {len([r for r in results if r])}")
    print(f"📊 Total Executions: {total_executions:,}")
    print(f"📊 Total Institutional Executions (20+ contracts): {total_institutional:,}")
    print(f"📊 Institutional %: {total_institutional/total_executions*100:.2f}%")
    print(
        f"🐋 Total Whale Executions (50+ contracts): {total_whales:,} ({total_whales/total_executions*100:.2f}%)"
    )
    print(
        f"🐋🐋 Total Mega Whale Executions (100+ contracts): {total_mega_whales:,} ({total_mega_whales/total_executions*100:.2f}%)"
    )

    # Sort by hour
    hourly_sorted = sorted(hourly_totals.items())

    print(f"\n{'='*80}")
    print("HOURLY DISTRIBUTION OF EXECUTIONS (EST Timezone)")
    print(f"{'='*80}")
    print(f"{'Hour':<10} {'Count':<15} {'Percentage':<15} {'Bar'}")
    print(f"{'-'*80}")

    for hour, count in hourly_sorted:
        pct = count / total_institutional * 100
        bar_len = int(pct / 2)  # Scale for display
        bar = "█" * bar_len

        # Highlight peak hours
        if pct > 8:  # More than 8% = significant
            marker = " 🔥 PEAK"
        elif pct > 5:
            marker = " ⭐ HIGH"
        else:
            marker = ""

        print(f"{hour:02d}:00{'':<5} {count:<15,} {pct:<14.2f}% {bar}{marker}")

    print(f"\n{'='*80}")
    print("DAY OF WEEK DISTRIBUTION")
    print(f"{'='*80}")

    # Order days properly
    day_order = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ]
    dow_ordered = [(day, dow_totals.get(day, 0)) for day in day_order]

    print(f"{'Day':<15} {'Count':<15} {'Percentage':<15} {'Bar'}")
    print(f"{'-'*80}")

    for day, count in dow_ordered:
        if count > 0:
            pct = count / total_institutional * 100
            bar_len = int(pct / 2)
            bar = "█" * bar_len

            if pct > 22:  # More than average for 5-day week
                marker = " 🔥 PEAK"
            elif pct > 18:
                marker = " ⭐ HIGH"
            else:
                marker = ""

            print(f"{day:<15} {count:<15,} {pct:<14.2f}% {bar}{marker}")

    # Find top 3 hours for institutional and whales
    top_hours = sorted(hourly_totals.items(), key=lambda x: x[1], reverse=True)[:3]
    top_whale_hours = sorted(
        whale_hourly_totals.items(), key=lambda x: x[1], reverse=True
    )[:3]

    print(f"\n{'='*80}")
    print("🎯 KEY FINDINGS - WHEN INSTITUTIONS EXECUTE ORDERS MOST")
    print(f"{'='*80}\n")

    print("🕐 TOP 3 HOURS FOR INSTITUTIONAL EXECUTIONS (20+ contracts, EST):")
    for i, (hour, count) in enumerate(top_hours, 1):
        pct = count / total_institutional * 100
        time_label = f"{hour:02d}:00 - {hour:02d}:59"

        # Identify session
        if 4 <= hour < 9:
            session = "Pre-Market"
        elif 9 <= hour < 16:
            session = "Regular Hours"
        elif 16 <= hour < 20:
            session = "After-Hours"
        else:
            session = "Extended Hours"

        print(f"   {i}. {time_label} - {count:,} executions ({pct:.2f}%) [{session}]")

    print("\n🐋 TOP 3 HOURS FOR WHALE EXECUTIONS (50+ contracts, EST):")
    for i, (hour, count) in enumerate(top_whale_hours, 1):
        if total_whales > 0:
            pct = count / total_whales * 100
            time_label = f"{hour:02d}:00 - {hour:02d}:59"

            # Identify session
            if 4 <= hour < 9:
                session = "Pre-Market"
            elif 9 <= hour < 16:
                session = "Regular Hours"
            elif 16 <= hour < 20:
                session = "After-Hours"
            else:
                session = "Extended Hours"

            print(
                f"   {i}. {time_label} - {count:,} executions ({pct:.2f}%) [{session}]"
            )

    # Save results
    output_file = (
        OUTPUT_DIR
        / f"institutional_executions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )

    with open(output_file, "w") as f:
        f.write("INSTITUTIONAL ORDER EXECUTION ANALYSIS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Files: {len([r for r in results if r])}\n")
        f.write(f"Total Institutional Executions: {total_institutional:,}\n\n")

        f.write("HOURLY DISTRIBUTION (EST)\n")
        f.write("-" * 80 + "\n")
        for hour, count in hourly_sorted:
            pct = count / total_institutional * 100
            f.write(f"{hour:02d}:00 - {count:,} executions ({pct:.2f}%)\n")

        f.write("\n\nTOP HOURS:\n")
        f.write("-" * 80 + "\n")
        for i, (hour, count) in enumerate(top_hours, 1):
            pct = count / total_institutional * 100
            f.write(f"{i}. {hour:02d}:00 - {count:,} executions ({pct:.2f}%)\n")

    print(f"\n✅ Analysis saved to: {output_file}")

    return hourly_totals, dow_totals


def main():
    """Main analysis function."""
    print("=" * 80)
    print("INSTITUTIONAL ORDER EXECUTION TIMING ANALYSIS")
    print("Analyzing action='T' and 'F' (executions/fills) across all MBO data")
    print("=" * 80)

    # Get all MBO CSV files
    csv_files = sorted(MBO_DATA_DIR.glob("*.csv"))

    if not csv_files:
        print(f"❌ No CSV files found in {MBO_DATA_DIR}")
        return

    print(f"\nFound {len(csv_files)} MBO data files")
    print(
        f"Date range: {csv_files[0].stem.split('-')[-1]} to {csv_files[-1].stem.split('-')[-1]}"
    )

    # Analyze each file
    results = []
    for csv_file in csv_files:
        result = analyze_executions(csv_file)
        results.append(result)

    # Aggregate analysis
    if any(results):
        hourly, dow = aggregate_analysis(results)
    else:
        print("\n❌ No valid results to aggregate")


if __name__ == "__main__":
    main()
