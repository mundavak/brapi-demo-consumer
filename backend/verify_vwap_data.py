"""
Verify VWAP data import and show relationship with candle data.
"""

import psycopg2
from datetime import datetime, timedelta
import pytz

# Database connection
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "trading_data",
    "user": "postgres",
    "password": "X74Ot*BvtjgKuCBx",
}


def verify_vwap_data():
    """Query and display VWAP data with candle context."""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    print("\n" + "=" * 80)
    print("VWAP DATA VERIFICATION")
    print("=" * 80)

    # Overall statistics
    cursor.execute(
        """
        SELECT 
            COUNT(*) as total_records,
            COUNT(vwap_930am) as records_with_930am,
            COUNT(vwap_daily) as records_with_daily,
            MIN(timestamp) as earliest,
            MAX(timestamp) as latest,
            COUNT(DISTINCT timeframe) as timeframe_count,
            COUNT(DISTINCT DATE(timestamp)) as days_count
        FROM vwap_levels
    """
    )
    stats = cursor.fetchone()
    print(f"\n📊 Overall Statistics:")
    print(f"   Total VWAP records: {stats[0]:,}")
    print(f"   Records with 9:30 AM VWAP: {stats[1]:,}")
    print(f"   Records with Daily VWAP: {stats[2]:,}")
    print(f"   Date range: {stats[3]} to {stats[4]}")
    print(f"   Timeframes: {stats[5]}")
    print(f"   Days covered: {stats[6]}")

    # Timeframe breakdown
    cursor.execute(
        """
        SELECT 
            timeframe,
            COUNT(*) as record_count,
            MIN(timestamp) as earliest,
            MAX(timestamp) as latest
        FROM vwap_levels
        GROUP BY timeframe
        ORDER BY timeframe
    """
    )
    print(f"\n📈 Breakdown by Timeframe:")
    for row in cursor.fetchall():
        print(f"   {row[0]:>4}: {row[1]:>4} records ({row[2]} to {row[3]})")

    # Latest data with price context
    cursor.execute(
        """
        SELECT 
            v.timestamp,
            v.timeframe,
            c.close as price,
            v.vwap_930am,
            v.vwap_daily,
            ROUND((c.close - v.vwap_930am)::numeric, 2) as diff_930am,
            ROUND((c.close - v.vwap_daily)::numeric, 2) as diff_daily,
            CASE 
                WHEN c.close > v.vwap_daily THEN 'ABOVE Daily (Bullish)'
                WHEN c.close < v.vwap_daily THEN 'BELOW Daily (Bearish)'
                ELSE 'AT Daily VWAP'
            END as bias
        FROM vwap_levels v
        JOIN ohlc_candles c ON 
            v.timestamp = c.timestamp 
            AND v.symbol = c.symbol 
            AND v.timeframe = c.timeframe
        WHERE v.timestamp >= NOW() - INTERVAL '4 hours'
        ORDER BY v.timestamp DESC
        LIMIT 10
        """
    )

    print(f"\n🕐 Latest VWAP Data (Last 4 Hours):")
    print(
        f"{'Time':<20} {'TF':<4} {'Price':>10} {'9:30 VWAP':>10} {'Diff':>8} {'Daily VWAP':>10} {'Diff':>8} {'Bias':<25}"
    )
    print("-" * 115)

    for row in cursor.fetchall():
        timestamp = row[0].strftime("%Y-%m-%d %H:%M")
        timeframe = row[1]
        price = f"${row[2]:,.2f}"
        vwap_930 = f"${row[3]:,.2f}"
        diff_930 = f"{float(row[5]):+.2f}"
        vwap_daily = f"${row[4]:,.2f}"
        diff_daily = f"{float(row[6]):+.2f}"
        bias = row[7]

        print(
            f"{timestamp:<20} {timeframe:<4} {price:>10} {vwap_930:>10} {diff_930:>8} {vwap_daily:>10} {diff_daily:>8} {bias:<25}"
        )

    # Judas swing detection (price crosses 9:30 AM VWAP)
    cursor.execute(
        """
        WITH vwap_with_lag AS (
            SELECT 
                v.timestamp,
                v.timeframe,
                c.close,
                v.vwap_930am,
                LAG(c.close) OVER (PARTITION BY v.timeframe ORDER BY v.timestamp) as prev_close,
                CASE 
                    WHEN LAG(c.close) OVER (PARTITION BY v.timeframe ORDER BY v.timestamp) < v.vwap_930am 
                         AND c.close > v.vwap_930am THEN 'BULLISH CROSS'
                    WHEN LAG(c.close) OVER (PARTITION BY v.timeframe ORDER BY v.timestamp) > v.vwap_930am 
                         AND c.close < v.vwap_930am THEN 'BEARISH CROSS'
                    ELSE NULL
                END as cross_type
            FROM vwap_levels v
            JOIN ohlc_candles c ON 
                v.timestamp = c.timestamp 
                AND v.symbol = c.symbol 
                AND v.timeframe = c.timeframe
            WHERE v.timestamp >= NOW() - INTERVAL '2 hours'
        )
        SELECT 
            timestamp,
            timeframe,
            close,
            vwap_930am,
            cross_type
        FROM vwap_with_lag
        WHERE cross_type IS NOT NULL
        ORDER BY timestamp DESC
        LIMIT 5
    """
    )

    crosses = cursor.fetchall()
    if crosses:
        print(f"\n⚡ Recent 9:30 AM VWAP Crosses (Potential Judas Swings):")
        print(
            f"{'Time':<20} {'TF':<4} {'Price':>10} {'9:30 VWAP':>10} {'Cross Type':<20}"
        )
        print("-" * 70)
        for row in crosses:
            timestamp = row[0].strftime("%Y-%m-%d %H:%M")
            print(
                f"{timestamp:<20} {row[1]:<4} ${row[2]:>9,.2f} ${row[3]:>9,.2f} {row[4]:<20}"
            )
    else:
        print(f"\n⚡ No 9:30 AM VWAP crosses in last 2 hours")

    # Current market position
    cursor.execute(
        """
        SELECT 
            v.timestamp,
            v.timeframe,
            c.close,
            v.vwap_930am,
            v.vwap_daily,
            ROUND((100.0 * (c.close - v.vwap_930am::numeric) / v.vwap_930am::numeric)::numeric, 2) as pct_from_930,
            ROUND((100.0 * (c.close - v.vwap_daily::numeric) / v.vwap_daily::numeric)::numeric, 2) as pct_from_daily
        FROM vwap_levels v
        JOIN ohlc_candles c ON 
            v.timestamp = c.timestamp 
            AND v.symbol = c.symbol 
            AND v.timeframe = c.timeframe
        WHERE v.timestamp = (SELECT MAX(timestamp) FROM vwap_levels WHERE timeframe = '5m')
        AND v.timeframe = '5m'
        """
    )

    current = cursor.fetchone()
    if current:
        print(f"\n💹 Current Market Position (5m):")
        print(f"   Time: {current[0].strftime('%Y-%m-%d %H:%M')}")
        print(f"   Price: ${current[2]:,.2f}")
        print(f"   9:30 AM VWAP: ${current[3]:,.2f} ({current[5]:+.2f}%)")
        print(f"   Daily VWAP: ${current[4]:,.2f} ({current[6]:+.2f}%)")

        if current[2] > current[4]:
            print(f"   📈 BIAS: BULLISH (above Daily VWAP)")
        elif current[2] < current[4]:
            print(f"   📉 BIAS: BEARISH (below Daily VWAP)")
        else:
            print(f"   ➡️  BIAS: NEUTRAL (at Daily VWAP)")

    print("\n" + "=" * 80)
    print("✅ VWAP DATA VERIFICATION COMPLETE")
    print("=" * 80 + "\n")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    verify_vwap_data()
