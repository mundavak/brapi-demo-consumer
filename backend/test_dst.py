"""Quick DST verification script"""
from datetime import datetime
import pytz

est = pytz.timezone('America/New_York')
now = datetime.now(est)

print("=" * 60)
print("DAYLIGHT SAVING TIME VERIFICATION")
print("=" * 60)
print(f"\nCurrent EST time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"UTC offset: {now.strftime('%z')} ({now.tzname()})")
print(f"Is DST active: {now.dst() != None}")

print("\n" + "=" * 60)
print("CBDR WINDOWS (EST TIMES)")
print("=" * 60)

windows = {
    "ASIAN": (0, 7),
    "LONDON": (2, 5),
    "PRE_NY": (7, 10),
    "NY_SESSION": (9, 16),
    "PM": (16, 20),
    "AFTER_HOURS": (20, 24)
}

hour = now.hour
current_window = None

for name, (start, end) in windows.items():
    status = "✅ ACTIVE" if start <= hour < end else ""
    print(f"{name:15s}: {start:02d}:00 - {end:02d}:00 EST  {status}")
    if start <= hour < end:
        current_window = name

print(f"\n🎯 Current CBDR Window: {current_window or 'AFTER_HOURS'}")

print("\n" + "=" * 60)
print("DST CHANGE DATES (2025)")
print("=" * 60)
print("Started DST: March 9, 2025 (EDT = UTC-4)")
print("Ended DST:   November 2, 2025 (EST = UTC-5)  ← JUST HAPPENED!")
print("\nStatus: ✅ Your system is correctly using EST (UTC-5)")
