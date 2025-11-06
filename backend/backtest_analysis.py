#!/usr/bin/env python3
"""
Backtest Analysis Tool
Analyzes historical order flow data and generates trading signals
"""

import redis
import psycopg2
from datetime import datetime, timedelta
import json

class BacktestAnalyzer:
    def __init__(self):
        # Redis connection
        self.redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # TimescaleDB connection
        self.db_conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='trading_data',
            user='postgres',
            password='X74Ot*BvtjgKuCBx'
        )
    
    def analyze_session(self, date_str, start_hour=9, end_hour=12, symbol='MNQ'):
        """
        Analyze a specific trading session
        date_str: 'YYYY-MM-DD' format
        start_hour/end_hour: EST hours (9-12 for NY AM)
        """
        target_date = datetime.strptime(date_str, '%Y-%m-%d')
        start_time = target_date.replace(hour=start_hour, minute=30)
        end_time = target_date.replace(hour=end_hour, minute=0)
        
        print(f"\n{'='*80}")
        print(f"BACKTEST ANALYSIS: {date_str} {start_hour}:30 - {end_hour}:00 EST")
        print(f"Symbol: {symbol}")
        print(f"{'='*80}\n")
        
        # Query order flow data
        absorption_data = self._query_absorption(start_time, end_time, symbol)
        stops_data = self._query_stops(start_time, end_time, symbol)
        iceberg_data = self._query_icebergs(start_time, end_time, symbol)
        
        # Calculate bias
        bias_score, signals = self._calculate_bias(
            absorption_data, stops_data, iceberg_data
        )
        
        # Generate trade recommendation
        recommendation = self._generate_recommendation(bias_score, signals)
        
        return {
            'bias_score': bias_score,
            'signals': signals,
            'recommendation': recommendation,
            'data': {
                'absorption': absorption_data,
                'stops': stops_data,
                'icebergs': iceberg_data
            }
        }
    
    def _query_absorption(self, start_time, end_time, symbol):
        """Query absorption events from TimescaleDB"""
        cursor = self.db_conn.cursor()
        
        query = """
            SELECT 
                timestamp,
                side,
                price,
                absorbed_volume,
                significance_score
            FROM absorption_events
            WHERE symbol LIKE %s
            AND timestamp >= %s
            AND timestamp <= %s
            ORDER BY timestamp
        """
        
        try:
            # Symbol in DB is like 'MNQZ5' (with contract month)
            symbol_pattern = f"{symbol}%"
            cursor.execute(query, (symbol_pattern, start_time, end_time))
            rows = cursor.fetchall()
            
            buy_absorption = sum(row[3] for row in rows if row[1] == 'BUY')
            sell_absorption = sum(row[3] for row in rows if row[1] == 'SELL')
            
            return {
                'buy_volume': buy_absorption,
                'sell_volume': sell_absorption,
                'imbalance': buy_absorption - sell_absorption,
                'events': len(rows)
            }
        except Exception as e:
            print(f"⚠️  No absorption data found: {e}")
            return {'buy_volume': 0, 'sell_volume': 0, 'imbalance': 0, 'events': 0}
        finally:
            cursor.close()
    
    def _query_stops(self, start_time, end_time, symbol):
        """Query stop/iceberg events from TimescaleDB"""
        cursor = self.db_conn.cursor()
        
        query = """
            SELECT 
                timestamp,
                side,
                price,
                detected_size,
                event_type,
                confidence_score
            FROM stops_icebergs
            WHERE symbol LIKE %s
            AND timestamp >= %s
            AND timestamp <= %s
            AND event_type = 'STOP'
            ORDER BY timestamp
        """
        
        try:
            symbol_pattern = f"{symbol}%"
            cursor.execute(query, (symbol_pattern, start_time, end_time))
            rows = cursor.fetchall()
            
            buy_stops = sum(row[3] for row in rows if row[1] == 'BUY')
            sell_stops = sum(row[3] for row in rows if row[1] == 'SELL')
            
            return {
                'buy_stops': buy_stops,
                'sell_stops': sell_stops,
                'total_events': len(rows)
            }
        except Exception as e:
            print(f"⚠️  No stops data found: {e}")
            return {'buy_stops': 0, 'sell_stops': 0, 'total_events': 0}
        finally:
            cursor.close()
    
    def _query_icebergs(self, start_time, end_time, symbol):
        """Query iceberg events from TimescaleDB"""
        cursor = self.db_conn.cursor()
        
        query = """
            SELECT 
                timestamp,
                side,
                price,
                estimated_total_size,
                confidence_score
            FROM stops_icebergs
            WHERE symbol LIKE %s
            AND timestamp >= %s
            AND timestamp <= %s
            AND event_type = 'ICEBERG'
            ORDER BY timestamp
        """
        
        try:
            symbol_pattern = f"{symbol}%"
            cursor.execute(query, (symbol_pattern, start_time, end_time))
            rows = cursor.fetchall()
            
            # Side is 'BUY'/'SELL' in this table
            buy_icebergs = sum(row[3] for row in rows if row[1] == 'BUY')
            sell_icebergs = sum(row[3] for row in rows if row[1] == 'SELL')
            
            return {
                'buy_volume': buy_icebergs,
                'sell_volume': sell_icebergs,
                'total_events': len(rows)
            }
        except Exception as e:
            print(f"⚠️  No iceberg data found: {e}")
            return {'buy_volume': 0, 'sell_volume': 0, 'total_events': 0}
        finally:
            cursor.close()
    
    def _calculate_bias(self, absorption, stops, icebergs):
        """
        Calculate market bias using dashboard algorithm
        Returns: (bias_score, signals_list)
        
        Refined thresholds:
        - Stop imbalance: 1.15x ratio (was 1.5x) - weighted by volume
        - Absorption: 1.3x ratio (was 1.5x)
        - Icebergs: 1.3x ratio (was 1.5x)
        """
        bias_score = 0
        signals = []
        
        # 1. Stop Hunt Analysis (±20 points, volume-weighted)
        # Lowered threshold to 1.15x to catch more nuanced moves
        # ICT Concept: High buy stops = liquidity grab below, expect bullish reversal
        stop_ratio_buy = stops['buy_stops'] / max(stops['sell_stops'], 1)
        stop_ratio_sell = stops['sell_stops'] / max(stops['buy_stops'], 1)
        
        if stop_ratio_buy > 1.15:
            # High buy stops triggered = price moved down to grab liquidity
            # After stop hunt below, expect BULLISH reversal (ICT concept)
            score = 15  # BULLISH signal
            # Add volume weight: +5 points if >20k stops (high conviction)
            if stops['total_events'] > 20000:
                score += 5
            bias_score += score
            signals.append({
                'type': 'STOP_HUNT',
                'score': score,
                'reason': f"Buy-side liquidity grab ({stops['buy_stops']:,} stops) - bullish reversal setup ({stop_ratio_buy:.2f}x)"
            })
        elif stop_ratio_sell > 1.15:
            # High sell stops triggered = price moved up to grab liquidity
            # After stop hunt above, expect BEARISH reversal
            score = -15  # BEARISH signal
            if stops['total_events'] > 20000:
                score -= 5
            bias_score += score
            signals.append({
                'type': 'STOP_HUNT',
                'score': score,
                'reason': f"Sell-side liquidity grab ({stops['sell_stops']:,} stops) - bearish reversal setup ({stop_ratio_sell:.2f}x)"
            })
        
        # 2. Absorption Analysis (±25 points)
        # Lowered threshold to 1.3x for better sensitivity
        abs_ratio_buy = absorption['buy_volume'] / max(absorption['sell_volume'], 1)
        abs_ratio_sell = absorption['sell_volume'] / max(absorption['buy_volume'], 1)
        
        if abs_ratio_buy > 1.3:
            score = 25
            bias_score += score
            signals.append({
                'type': 'ABSORPTION',
                'score': score,
                'reason': f"Strong BUY absorption ({absorption['buy_volume']:,} vs {absorption['sell_volume']:,}) - institutions accumulating ({abs_ratio_buy:.2f}x)"
            })
        elif abs_ratio_sell > 1.3:
            score = -25
            bias_score += score
            signals.append({
                'type': 'ABSORPTION',
                'score': score,
                'reason': f"Strong SELL absorption ({absorption['sell_volume']:,} vs {absorption['buy_volume']:,}) - institutions distributing ({abs_ratio_sell:.2f}x)"
            })
        
        # 3. Iceberg Analysis (±20 points)
        # Lowered threshold to 1.3x
        ice_ratio_buy = icebergs['buy_volume'] / max(icebergs['sell_volume'], 1)
        ice_ratio_sell = icebergs['sell_volume'] / max(icebergs['buy_volume'], 1)
        
        if ice_ratio_buy > 1.3:
            score = 20
            bias_score += score
            signals.append({
                'type': 'ICEBERG',
                'score': score,
                'reason': f"Large hidden BID orders ({icebergs['buy_volume']:,}) - strong support ({ice_ratio_buy:.2f}x)"
            })
        elif ice_ratio_sell > 1.3:
            score = -20
            bias_score += score
            signals.append({
                'type': 'ICEBERG',
                'score': score,
                'reason': f"Large hidden ASK orders ({icebergs['sell_volume']:,}) - strong resistance ({ice_ratio_sell:.2f}x)"
            })
        
        return bias_score, signals
    
    def _generate_recommendation(self, bias_score, signals):
        """Generate trade recommendation based on bias"""
        # Calculate confidence (scale: 0-100%)
        # 60 points = 100% confidence (perfect alignment)
        confidence = min(abs(bias_score) / 60 * 100, 100)
        
        # Determine bias direction
        # Refined thresholds: ±25 for bias (was ±30), 40% confidence for trade (was 50%)
        if bias_score >= 25:
            bias = 'BULLISH'
            action = 'LONG' if confidence >= 40 else 'WAIT'
        elif bias_score <= -25:
            bias = 'BEARISH'
            action = 'SHORT' if confidence >= 40 else 'WAIT'
        else:
            bias = 'NEUTRAL'
            action = 'WAIT'
        
        return {
            'bias': bias,
            'bias_score': bias_score,
            'confidence': round(confidence, 1),
            'action': action,
            'entry_strategy': self._get_entry_strategy(action, bias_score),
            'risk_levels': self._get_risk_levels(action)
        }
    
    def _get_entry_strategy(self, action, bias_score):
        """Get entry strategy based on action"""
        if action == 'LONG':
            return "Enter on pullback to support or after break of resistance"
        elif action == 'SHORT':
            return "Enter on bounce to resistance or after break of support"
        else:
            return "Wait for clearer directional bias (confidence < 50%)"
    
    def _get_risk_levels(self, action):
        """Get risk/reward levels"""
        if action == 'LONG':
            return {
                'stop_loss': '-8 points',
                'scalp_target': '+4 points (1:0.5 R:R)',
                'intraday_target': '+12 points (1:1.5 R:R)'
            }
        elif action == 'SHORT':
            return {
                'stop_loss': '+8 points',
                'scalp_target': '-4 points (1:0.5 R:R)',
                'intraday_target': '-12 points (1:1.5 R:R)'
            }
        else:
            return None
    
    def print_analysis(self, result):
        """Pretty print analysis results"""
        rec = result['recommendation']
        
        print(f"\n📊 MARKET BIAS: {rec['bias']}")
        print(f"   Score: {rec['bias_score']}")
        print(f"   Confidence: {rec['confidence']}%")
        print(f"\n🎯 TRADE RECOMMENDATION: {rec['action']}")
        
        if rec['action'] != 'WAIT':
            print(f"   Entry: {rec['entry_strategy']}")
            levels = rec['risk_levels']
            print(f"   Stop Loss: {levels['stop_loss']}")
            print(f"   Scalp Target: {levels['scalp_target']}")
            print(f"   Intraday Target: {levels['intraday_target']}")
        
        print(f"\n📈 SIGNALS ({len(result['signals'])} total):")
        for signal in result['signals']:
            print(f"   [{signal['type']}] ({signal['score']:+d} points) {signal['reason']}")
        
        print(f"\n📦 DATA SUMMARY:")
        data = result['data']
        print(f"   Absorption: {data['absorption']['events']} events, " +
              f"Buy: {data['absorption']['buy_volume']}, Sell: {data['absorption']['sell_volume']}")
        print(f"   Stops: {data['stops']['total_events']} events, " +
              f"Buy: {data['stops']['buy_stops']}, Sell: {data['stops']['sell_stops']}")
        print(f"   Icebergs: {data['icebergs']['total_events']} events, " +
              f"Buy: {data['icebergs']['buy_volume']}, Sell: {data['icebergs']['sell_volume']}")
        
        print(f"\n{'='*80}\n")
    
    def close(self):
        """Close database connections"""
        self.redis_client.close()
        self.db_conn.close()


if __name__ == "__main__":
    analyzer = BacktestAnalyzer()
    
    try:
        # Analyze yesterday's session (Nov 5, 2025, 9:30-12:00 EST)
        result = analyzer.analyze_session('2025-11-05', start_hour=9, end_hour=12, symbol='MNQ')
        analyzer.print_analysis(result)
        
        # Compare with actual price action
        print("📊 ACTUAL PRICE ACTION (Nov 5, 2025 NY AM):")
        print("   Open (9:30 AM): 25,542.25")
        print("   Close (12:00 PM): 25,774.50")
        print("   Move: +232.25 points (BULLISH)")
        print("   Session High: 25,789.00")
        print("   Session Low: 25,487.75")
        print("   Range: 301.25 points")
        
    finally:
        analyzer.close()
