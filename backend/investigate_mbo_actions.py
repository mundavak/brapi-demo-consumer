"""
Investigate what T and F action codes really mean in MBO data.

Understanding the distinction between:
- action='A' - Add order to book (limit order placement)
- action='T' - Trade (but what side? aggressor or passive?)
- action='F' - Fill (but what side? aggressor or passive?)
"""

import pandas as pd
from pathlib import Path

# Read a sample file
csv_file = Path("H:/mbo_csv/glbx-mdp3-20251016.mbo.csv")

print("=" * 80)
print("INVESTIGATING MBO ACTION CODES T and F")
print("=" * 80)

df = pd.read_csv(csv_file, nrows=500000)

print(f"\nTotal rows: {len(df):,}")
print("\nAction counts:")
print(df["action"].value_counts())

# Get trades
trades = df[df["action"].isin(["T", "F"])].copy()
trades = trades.sort_values("ts_event")

print(f"\n\nTotal T+F actions: {len(trades):,}")

print("\n" + "=" * 80)
print("EXAMINING T/F PAIRS AT SAME TIMESTAMP")
print("=" * 80)

# Group by timestamp to find pairs
grouped = trades.groupby("ts_event")

print("\nLooking for timestamps with both T and F...")
count = 0
for ts, group in grouped:
    if len(group) >= 2:
        actions = group["action"].unique()
        if "T" in actions and "F" in actions:
            count += 1
            if count <= 5:  # Show first 5 examples
                print(f"\n--- Timestamp: {ts} ---")
                print(
                    group[["action", "side", "price", "size", "order_id"]].to_string()
                )

print(f"\nTotal timestamps with both T and F: {count}")

# Check if T and F always come in pairs
print("\n" + "=" * 80)
print("HYPOTHESIS: T = Trade (aggressor/taker), F = Fill (passive/maker)")
print("=" * 80)

print("\nIf this is true, we should see:")
print("- T and F occur at same timestamp")
print("- T has opposite side from F")
print("- Same price and size")

# Look at specific examples
print("\n\nFirst 20 T/F events:")
print(trades[["ts_event", "action", "side", "price", "size", "order_id"]].head(20))

# Check sizes
print("\n" + "=" * 80)
print("SIZE ANALYSIS")
print("=" * 80)

t_sizes = df[df["action"] == "T"]["size"]
f_sizes = df[df["action"] == "F"]["size"]

print(f"\naction='T' sizes:")
print(f"  Mean: {t_sizes.mean():.2f}")
print(f"  Median: {t_sizes.median():.2f}")
print(f"  Max: {t_sizes.max()}")
print(
    f"  >= 20 contracts: {(t_sizes >= 20).sum():,} ({(t_sizes >= 20).sum()/len(t_sizes)*100:.2f}%)"
)

print(f"\naction='F' sizes:")
print(f"  Mean: {f_sizes.mean():.2f}")
print(f"  Median: {f_sizes.median():.2f}")
print(f"  Max: {f_sizes.max()}")
print(
    f"  >= 20 contracts: {(f_sizes >= 20).sum():,} ({(f_sizes >= 20).sum()/len(f_sizes)*100:.2f}%)"
)

print("\n" + "=" * 80)
print("CONCLUSION")
print("=" * 80)
print(
    """
Based on Databento MBO schema:
- action='A' = Add order to book (limit order placement)
- action='C' = Cancel order
- action='M' = Modify order
- action='T' = Trade (AGGRESSOR side - the market order that executed)
- action='F' = Fill (PASSIVE side - the limit order that got filled)
- action='R' = Reset (book clear)

When a trade happens:
1. Market order comes in (action='T') - AGGRESSOR
2. Matches with limit order on book (action='F') - PASSIVE/MAKER

So my "execution analysis" was actually measuring BOTH sides of each trade!
The aggressor (T) and the passive fill (F) happen at the same microsecond.

This means:
- I was double-counting executions (both T and F for same trade)
- Need to analyze ONLY action='T' for true "aggressive institutional execution"
- Or analyze ONLY action='F' for "when institutional limit orders get filled"
"""
)
