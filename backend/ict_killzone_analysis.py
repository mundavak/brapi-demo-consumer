#!/usr/bin/env python3
"""
ICT Killzone Session Analysis
Asia: 20:00-24:00 EST (8 PM - Midnight)
London: 02:00-05:00 EST (2 AM - 5 AM)
"""

import pandas as pd
from datetime import datetime, timezone
import pytz

df = pd.read_csv("../KnowledgeBase/CME_MINI_MNQ1!, 60.csv")
df["dt"] = df["time"].apply(
    lambda x: datetime.fromtimestamp(x, tz=timezone.utc).astimezone(
        pytz.timezone("America/New_York")
    )
)

print("=" * 80)
print("ICT KILLZONE SESSION ANALYSIS")
print("=" * 80)
print()

# Nov 5 (yesterday) - Previous Day
nov5 = df[df["dt"].dt.date == pd.Timestamp("2025-11-05").date()]
print("=== PREVIOUS DAY (Nov 5) ===")
d1_high = nov5["high"].max()
d1_low = nov5["low"].min()
d1_open = nov5.iloc[0]["open"]
d1_close = nov5.iloc[-1]["close"]
print(f"Open:  ${d1_open:,.2f}")
print(f"High:  ${d1_high:,.2f}")
print(f"Low:   ${d1_low:,.2f}")
print(f"Close: ${d1_close:,.2f}")
print(f"Range: {d1_high - d1_low:.2f} points")
print(f"Move:  {d1_close - d1_open:+.2f} points")
print()

# Asia Killzone: Nov 5 20:00 to Nov 6 00:00 (midnight)
asia = df[(df["dt"] >= "2025-11-05 20:00") & (df["dt"] < "2025-11-06 00:00")]
print("=== ASIA KILLZONE (Nov 5 20:00 - 24:00 EST) ===")
if len(asia) > 0:
    asia_high = asia["high"].max()
    asia_low = asia["low"].min()
    asia_open = asia.iloc[0]["open"]
    asia_close = asia.iloc[-1]["close"]
    print(f"High:  ${asia_high:,.2f}")
    print(f"Low:   ${asia_low:,.2f}")
    print(f"Open:  ${asia_open:,.2f}")
    print(f"Close: ${asia_close:,.2f}")
    print(f"Range: {asia_high - asia_low:.2f} points")
    print(f"Move:  {asia_close - asia_open:+.2f} points")
    print()
    print("Hour-by-hour:")
    print(asia[["dt", "open", "high", "low", "close"]])
else:
    print("No data found")
    asia_high = None
    asia_low = None
print()

# London Killzone: Nov 6 02:00 to 05:00
london = df[(df["dt"] >= "2025-11-06 02:00") & (df["dt"] < "2025-11-06 06:00")]
print("=== LONDON KILLZONE (Nov 6 02:00 - 05:00 EST) ===")
if len(london) > 0:
    london_high = london["high"].max()
    london_low = london["low"].min()
    london_open = london.iloc[0]["open"]
    london_close = london.iloc[-1]["close"]
    print(f"High:  ${london_high:,.2f}")
    print(f"Low:   ${london_low:,.2f}")
    print(f"Open:  ${london_open:,.2f}")
    print(f"Close: ${london_close:,.2f}")
    print(f"Range: {london_high - london_low:.2f} points")
    print(f"Move:  {london_close - london_open:+.2f} points")
    print()
    print("Hour-by-hour:")
    print(london[["dt", "open", "high", "low", "close"]])
else:
    print("No data found")
    london_high = None
    london_low = None
print()

# Key Levels Summary
print("=" * 80)
print("KEY LEVELS")
print("=" * 80)
print(f"PDH (Previous Day High): ${d1_high:,.2f}")
print(f"PDL (Previous Day Low):  ${d1_low:,.2f}")
if asia_high is not None:
    print(f"Asia High:               ${asia_high:,.2f}")
    print(f"Asia Low:                ${asia_low:,.2f}")
if london_high is not None:
    print(f"London High:             ${london_high:,.2f}")
    print(f"London Low:              ${london_low:,.2f}")
print()
