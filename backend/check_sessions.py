#!/usr/bin/env python3
"""
Correct session analysis - verify Asia and London levels
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

# Nov 5 (yesterday)
nov5 = df[df["dt"].dt.date == pd.Timestamp("2025-11-05").date()]
print("=== NOV 5 (Yesterday) ===")
print(f'High: {nov5["high"].max()}')
print(f'Low: {nov5["low"].min()}')
print(f'Close: {nov5.iloc[-1]["close"]}')
print()

# Asia session Nov 5 18:00 to Nov 6 02:00
asia = df[(df["dt"] >= "2025-11-05 18:00") & (df["dt"] <= "2025-11-06 02:59")]
print("=== ASIA SESSION (Nov 5 18:00 - Nov 6 02:00) ===")
print(f'High: {asia["high"].max()}')
print(f'Low: {asia["low"].min()}')
print(asia[["dt", "high", "low", "close"]])
print()

# London session Nov 6 03:00 to 08:00
london = df[(df["dt"] >= "2025-11-06 03:00") & (df["dt"] <= "2025-11-06 08:59")]
print("=== LONDON SESSION (Nov 6 03:00 - 08:00) ===")
print(f'High: {london["high"].max()}')
print(f'Low: {london["low"].min()}')
print(london[["dt", "high", "low", "close"]])
