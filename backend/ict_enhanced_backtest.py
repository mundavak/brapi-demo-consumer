"""
ICT-Enhanced Comprehensive Backtest Analysis
Incorporates:
- ICT Judas Swing detection
- Iceberg sub-type weighting
- Confidence thresholds
- Price context (session levels)
- Low institutional activity warnings
"""

import psycopg2
import redis
from datetime import datetime, timedelta
import pytz


class ICTEnhancedBacktest:
    def __init__(self):
        self.db_conn = psycopg2.connect(
            host="localhost",
            database="trading_data",
            user="postgres",
            password="X74Ot*BvtjgKuCBx",
        )
        self.redis_conn = redis.Redis(
            host="localhost", port=6379, decode_responses=True
        )

        # ICT Killzone times (EST)
        self.ASIA_START = 20  # 8 PM
        self.ASIA_END = 24  # Midnight
        self.LONDON_START = 2  # 2 AM
        self.LONDON_END = 5  # 5 AM

        # Iceberg sub-type reliability weights
        self.SUBTYPE_WEIGHTS = {
            "TRADE": 1.0,
            "EXECUTION": 0.8,
            "DETECTION": 0.5,
            "MOVEMENT": 0.3,
            "CANCELLATION": 0.2,
            None: 0.5,  # Legacy data without sub-type
        }

        # Signal thresholds
        self.CONFIDENCE_THRESHOLD = 30  # Below this = WAIT
        self.MIN_ICEBERGS_PRENY = 20  # Expected minimum for reliable signal

    def get_session_levels(self, date_str):
        """Get previous day and session highs/lows using ICT killzone times"""
        cur = self.db_conn.cursor()

        est = pytz.timezone("America/New_York")
        date = datetime.strptime(date_str, "%Y-%m-%d")
        prev_date = date - timedelta(days=1)

        # Previous Day (full day - midnight to midnight EST)
        prev_start = est.localize(prev_date.replace(hour=0, minute=0, second=0))
        prev_end = est.localize(date.replace(hour=0, minute=0, second=0))

        cur.execute(
            """
            SELECT MAX(high), MIN(low), 
                   (SELECT close FROM ohlc_candles 
                    WHERE symbol LIKE '%%MNQ%%'
                    AND timestamp >= to_timestamp(%s)
                    AND timestamp < to_timestamp(%s)
                    ORDER BY timestamp DESC LIMIT 1) as close
            FROM ohlc_candles
            WHERE symbol LIKE '%%MNQ%%'
              AND timestamp >= to_timestamp(%s)
              AND timestamp < to_timestamp(%s)
        """,
            (
                prev_start.timestamp(),
                prev_end.timestamp(),
                prev_start.timestamp(),
                prev_end.timestamp(),
            ),
        )

        result = cur.fetchone()
        pdh, pdl, prev_close = result if result else (None, None, None)

        # Asia Killzone (20:00-24:00 previous day)
        asia_start = est.localize(
            prev_date.replace(hour=self.ASIA_START, minute=0, second=0)
        )
        asia_end = prev_end  # Midnight

        cur.execute(
            """
            SELECT MAX(high), MIN(low)
            FROM ohlc_candles
            WHERE symbol LIKE '%%MNQ%%'
              AND timestamp >= to_timestamp(%s)
              AND timestamp < to_timestamp(%s)
        """,
            (asia_start.timestamp(), asia_end.timestamp()),
        )

        result = cur.fetchone()
        asia_high, asia_low = result if result else (None, None)

        # London Killzone (02:00-05:00 current day)
        london_start = est.localize(
            date.replace(hour=self.LONDON_START, minute=0, second=0)
        )
        london_end = est.localize(
            date.replace(hour=self.LONDON_END, minute=0, second=0)
        )

        cur.execute(
            """
            SELECT MAX(high), MIN(low)
            FROM ohlc_candles
            WHERE symbol LIKE '%%MNQ%%'
              AND timestamp >= to_timestamp(%s)
              AND timestamp < to_timestamp(%s)
        """,
            (london_start.timestamp(), london_end.timestamp()),
        )

        result = cur.fetchone()
        london_high, london_low = result if result else (None, None)

        cur.close()

        return {
            "pdh": pdh,
            "pdl": pdl,
            "prev_close": prev_close,
            "asia_high": asia_high,
            "asia_low": asia_low,
            "london_high": london_high,
            "london_low": london_low,
        }

    def analyze_stops(self, start_time, end_time):
        """Analyze stop hunts in PRE_NY window"""
        cur = self.db_conn.cursor()

        cur.execute(
            """
            SELECT 
                side,
                COUNT(*) as count,
                SUM(COALESCE(estimated_total_size, detected_size)) as volume
            FROM stops_icebergs
            WHERE symbol LIKE '%%MNQ%%'
              AND event_type IN ('STOP', 'STOP_CLUSTER')
              AND timestamp >= to_timestamp(%s)
              AND timestamp < to_timestamp(%s)
            GROUP BY side
        """,
            (start_time.timestamp(), end_time.timestamp()),
        )

        results = cur.fetchall()
        cur.close()

        buy_stops = sell_stops = 0
        buy_vol = sell_vol = 0

        for side, count, vol in results:
            if side == "BUY":
                buy_stops = count
                buy_vol = vol or 0
            else:
                sell_stops = count
                sell_vol = vol or 0

        # ICT: BUY stops swept = bullish reversal expected
        if sell_stops > 0:
            ratio = buy_stops / sell_stops
        else:
            ratio = 999 if buy_stops > 0 else 1

        if ratio > 1.2:
            signal = "BULLISH"
            score = min((ratio - 1) * 25, 30)
        elif ratio < 0.8:
            signal = "BEARISH"
            score = min((1 / ratio - 1) * 25, 30)
        else:
            signal = "NEUTRAL"
            score = 0

        return {
            "signal": signal,
            "score": (
                score if signal == "BULLISH" else -score if signal == "BEARISH" else 0
            ),
            "buy_stops": buy_stops,
            "sell_stops": sell_stops,
            "ratio": ratio,
        }

    def analyze_icebergs(self, start_time, end_time):
        """Analyze icebergs with sub-type weighting"""
        cur = self.db_conn.cursor()

        cur.execute(
            """
            SELECT 
                side,
                iceberg_subtype,
                COUNT(*) as count,
                SUM(COALESCE(estimated_total_size, detected_size)) as volume
            FROM stops_icebergs
            WHERE symbol LIKE '%%MNQ%%'
              AND event_type = 'ICEBERG'
              AND timestamp >= to_timestamp(%s)
              AND timestamp < to_timestamp(%s)
            GROUP BY side, iceberg_subtype
        """,
            (start_time.timestamp(), end_time.timestamp()),
        )

        results = cur.fetchall()
        cur.close()

        buy_weighted = sell_weighted = 0
        buy_count = sell_count = 0
        subtype_breakdown = {"BUY": {}, "SELL": {}}

        for side, subtype, count, vol in results:
            weight = self.SUBTYPE_WEIGHTS.get(subtype, 0.5)
            weighted = count * weight

            if side == "BUY":
                buy_weighted += weighted
                buy_count += count
                subtype_breakdown["BUY"][subtype or "NULL"] = count
            else:
                sell_weighted += weighted
                sell_count += count
                subtype_breakdown["SELL"][subtype or "NULL"] = count

        total_icebergs = buy_count + sell_count

        # Check for low institutional activity
        low_activity = total_icebergs < self.MIN_ICEBERGS_PRENY

        if sell_weighted > 0:
            ratio = buy_weighted / sell_weighted
        else:
            ratio = 999 if buy_weighted > 0 else 1

        if ratio > 1.3:
            signal = "BULLISH"
            score = min((ratio - 1) * 15, 20)
        elif ratio < 0.7:
            signal = "BEARISH"
            score = min((1 / ratio - 1) * 15, 20)
        else:
            signal = "NEUTRAL"
            score = 0

        # Reduce score if low activity
        if low_activity and score != 0:
            score *= 0.5

        return {
            "signal": signal,
            "score": (
                score if signal == "BULLISH" else -score if signal == "BEARISH" else 0
            ),
            "buy_count": buy_count,
            "sell_count": sell_count,
            "buy_weighted": buy_weighted,
            "sell_weighted": sell_weighted,
            "total_icebergs": total_icebergs,
            "low_activity": low_activity,
            "breakdown": subtype_breakdown,
        }

    def analyze_mbo(self, start_time, end_time):
        """Analyze MBO order flow"""
        cur = self.db_conn.cursor()

        cur.execute(
            """
            SELECT 
                side,
                COUNT(*) as orders,
                SUM(size) as volume
            FROM mbo_data
            WHERE symbol LIKE '%%MNQ%%'
              AND action = 'ADD'
              AND timestamp >= to_timestamp(%s)
              AND timestamp < to_timestamp(%s)
            GROUP BY side
        """,
            (start_time.timestamp(), end_time.timestamp()),
        )

        results = cur.fetchall()
        cur.close()

        buy_orders = sell_orders = 0
        buy_vol = sell_vol = 0

        for side, orders, vol in results:
            if side == "BUY":
                buy_orders = orders
                buy_vol = vol or 0
            else:
                sell_orders = orders
                sell_vol = vol or 0

        order_ratio = buy_orders / sell_orders if sell_orders > 0 else 999
        vol_ratio = buy_vol / sell_vol if sell_vol > 0 else 999

        if order_ratio > 1.1 and vol_ratio > 1.1:
            signal = "BULLISH"
            score = min((order_ratio - 1) * 20, 25)
        elif order_ratio < 0.9 and vol_ratio < 0.9:
            signal = "BEARISH"
            score = min((1 / order_ratio - 1) * 20, 25)
        else:
            signal = "NEUTRAL"
            score = 0

        return {
            "signal": signal,
            "score": (
                score if signal == "BULLISH" else -score if signal == "BEARISH" else 0
            ),
            "buy_orders": buy_orders,
            "sell_orders": sell_orders,
            "order_ratio": order_ratio,
            "vol_ratio": vol_ratio,
        }

    def check_price_context(self, current_price, session_levels, signal):
        """Check if price context suggests liquidity sweep risk"""
        warnings = []

        london_high = session_levels.get("london_high")
        london_low = session_levels.get("london_low")
        asia_low = session_levels.get("asia_low")
        pdh = session_levels.get("pdh")

        # Check for liquidity sweeps
        if london_high and current_price > london_high:
            if signal == "BULLISH":
                warnings.append("RISK: Price swept London high - potential Judas swing")

        if london_low and current_price < london_low:
            if signal == "BEARISH":
                warnings.append("RISK: Price swept London low - potential reversal")

        if asia_low and current_price < asia_low:
            warnings.append("INFO: Price below Asia low - extended move")

        if pdh and current_price > pdh:
            warnings.append("INFO: Price above PDH - momentum trade")

        return warnings

    def generate_signal(self, date_str, current_price=None):
        """Generate comprehensive trading signal with ICT enhancements"""

        est = pytz.timezone("America/New_York")
        date = datetime.strptime(date_str, "%Y-%m-%d")

        # PRE_NY window
        preny_start = est.localize(date.replace(hour=7, minute=30, second=0))
        preny_end = est.localize(date.replace(hour=9, minute=0, second=0))

        print("=" * 80)
        print(f"ICT-ENHANCED BACKTEST - {date_str}")
        print("=" * 80)
        print(f"PRE_NY Analysis: 7:30-9:00 AM EST")
        if current_price:
            print(f"Current Price: ${current_price:,.2f}")
        print()

        # Get session levels
        print("SESSION LEVELS:")
        levels = self.get_session_levels(date_str)
        for key, value in levels.items():
            if value:
                print(f"  {key.upper()}: ${value:,.2f}")
        print()

        # Analyze components
        print("ORDER FLOW ANALYSIS:")
        print("-" * 80)

        stops = self.analyze_stops(preny_start, preny_end)
        print(f"STOPS: {stops['signal']:8} ({stops['score']:+.1f} pts)")
        print(
            f"  BUY: {stops['buy_stops']:,} | SELL: {stops['sell_stops']:,} | Ratio: {stops['ratio']:.2f}x"
        )

        icebergs = self.analyze_icebergs(preny_start, preny_end)
        print(f"ICEBERGS: {icebergs['signal']:8} ({icebergs['score']:+.1f} pts)")
        print(f"  Total: {icebergs['total_icebergs']} events")
        print(
            f"  BUY: {icebergs['buy_count']} (weighted: {icebergs['buy_weighted']:.1f})"
        )
        print(
            f"  SELL: {icebergs['sell_count']} (weighted: {icebergs['sell_weighted']:.1f})"
        )
        if icebergs["low_activity"]:
            print(
                f"  ⚠️  WARNING: Low institutional activity (< {self.MIN_ICEBERGS_PRENY} icebergs)"
            )
            print(f"  → Signal confidence reduced by 50%")

        mbo = self.analyze_mbo(preny_start, preny_end)
        print(f"MBO FLOW: {mbo['signal']:8} ({mbo['score']:+.1f} pts)")
        print(f"  Orders: {mbo['order_ratio']:.2f}x | Volume: {mbo['vol_ratio']:.2f}x")
        print()

        # Calculate total score
        total_score = stops["score"] + icebergs["score"] + mbo["score"]
        max_score = 75
        confidence = min(abs(total_score) / max_score * 100, 95)

        # Apply low activity penalty
        if icebergs["low_activity"]:
            confidence *= 0.5

        print("=" * 80)
        print(f"TOTAL SCORE: {total_score:+.1f} / ±{max_score}")
        print(f"CONFIDENCE: {confidence:.1f}%")
        print("=" * 80)

        # Determine signal
        if confidence < self.CONFIDENCE_THRESHOLD:
            final_signal = "WAIT"
            print(f"SIGNAL: {final_signal}")
            print(
                f"REASON: Insufficient confidence ({confidence:.1f}% < {self.CONFIDENCE_THRESHOLD}%)"
            )
        elif total_score >= 15:
            final_signal = "LONG"
            print(f"SIGNAL: {final_signal}")
        elif total_score <= -15:
            final_signal = "SHORT"
            print(f"SIGNAL: {final_signal}")
        else:
            final_signal = "WAIT"
            print(f"SIGNAL: {final_signal}")
            print(f"REASON: Score too close to neutral ({total_score:+.1f})")

        print()

        # Price context warnings
        if current_price:
            warnings = self.check_price_context(current_price, levels, final_signal)
            if warnings:
                print("PRICE CONTEXT WARNINGS:")
                for warning in warnings:
                    print(f"  ⚠️  {warning}")
                print()

        return {
            "signal": final_signal,
            "confidence": confidence,
            "score": total_score,
            "components": {"stops": stops, "icebergs": icebergs, "mbo": mbo},
            "levels": levels,
            "warnings": warnings if current_price else [],
        }

    def close(self):
        self.db_conn.close()
        self.redis_conn.close()


if __name__ == "__main__":
    analyzer = ICTEnhancedBacktest()

    # Test with Nov 6, 2025 (Judas swing day)
    result = analyzer.generate_signal("2025-11-06", current_price=25802)

    print("\n" + "=" * 80)
    print("OUTCOME ANALYSIS")
    print("=" * 80)
    print("What Actually Happened:")
    print("  9:30 AM: Judas swing to $25,840 (NY PM midpoint)")
    print("  Then: -512 point drop to $25,328")
    print("  Pattern: Classic ICT liquidity sweep → reversal")
    print()
    print("Model Performance:")
    if result["signal"] == "WAIT":
        print("  ✅ CORRECT: Model output WAIT (avoided trap)")
    elif result["signal"] == "LONG" and result["confidence"] < 40:
        print("  ⚠️  PARTIAL: Model showed low confidence (should WAIT)")
    else:
        print(
            f"  ❌ INCORRECT: Model said {result['signal']} with {result['confidence']:.1f}% confidence"
        )

    analyzer.close()
