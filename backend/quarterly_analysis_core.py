"""
Quarterly Theory Core Analysis Logic
Purpose: Session analysis, cycle determination, phase tracking
Author: AI Assistant
Created: 2025-10-29

This module contains the core algorithms for:
1. Asia/London/Pre-NY session analysis
2. AMDX vs XAMD cycle determination
3. Phase identification and transitions
4. Fake vs Real move classification
"""

from quarterly_theory_engine import *
from typing import Dict, List, Tuple, Optional
import numpy as np

# =====================================================
# Session Analyzer
# =====================================================

class SessionAnalyzer:
    """Analyzes individual sessions (Asia, London, Pre-NY)"""
    
    def __init__(self, data_fetcher: DataFetcher):
        self.data_fetcher = data_fetcher
        
    def analyze_session(self, start_time: datetime, end_time: datetime, session_name: str) -> Dict:
        """
        Analyze a session for Accumulation vs Expansion characteristics
        
        Returns:
            {
                'session': str,
                'classification': 'ACCUMULATION' or 'EXPANSION',
                'confidence': float (0-100),
                'indicators': {
                    'absorption_balance': float,
                    'stops_bidirectional': bool,
                    'aggressive_pct': float,
                    'displacement_detected': bool
                },
                'bias': 'BULLISH' or 'BEARISH' or 'NEUTRAL'
            }
        """
        logger.info(f"Analyzing {session_name} session: {start_time} to {end_time}")
        
        # Fetch data
        absorption_data = self.data_fetcher.get_absorption_data(start_time, end_time)
        stops_data = self.data_fetcher.get_stops_icebergs_data(start_time, end_time)
        mbo_summary = self.data_fetcher.get_mbo_summary(start_time, end_time)
        
        # Calculate indicators
        indicators = self._calculate_indicators(absorption_data, stops_data, mbo_summary)
        
        # Classify session
        classification, confidence = self._classify_session(indicators)
        
        # Determine bias
        bias = self._determine_bias(indicators, absorption_data, mbo_summary)
        
        return {
            'session': session_name,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'classification': classification,
            'confidence': confidence,
            'indicators': indicators,
            'bias': bias,
            'raw_data_counts': {
                'absorption_events': len(absorption_data),
                'stops_events': len(stops_data),
                'mbo_orders': mbo_summary.get('total_orders', 0)
            }
        }
        
    def _calculate_indicators(self, absorption_data: List[Dict], 
                             stops_data: List[Dict], 
                             mbo_summary: Dict) -> Dict:
        """Calculate all indicators for classification"""
        
        # Absorption Balance (0-100, where 50 = balanced)
        if absorption_data:
            bid_significant = sum(1 for e in absorption_data if e.get('side') == 'BID' and e.get('significance', 0) > 0.5)
            ask_significant = sum(1 for e in absorption_data if e.get('side') == 'ASK' and e.get('significance', 0) > 0.5)
            total_significant = bid_significant + ask_significant
            
            if total_significant > 0:
                absorption_balance = (bid_significant / total_significant) * 100
            else:
                absorption_balance = 50.0
        else:
            absorption_balance = 50.0
            
        # Stops Bidirectional (True if stops triggered on both sides)
        if stops_data:
            buy_stops = sum(1 for e in stops_data if e.get('stop_type') == 'BUY_STOP')
            sell_stops = sum(1 for e in stops_data if e.get('stop_type') == 'SELL_STOP')
            stops_bidirectional = buy_stops > 0 and sell_stops > 0
            stop_balance = min(buy_stops, sell_stops) / max(buy_stops, sell_stops, 1)
        else:
            stops_bidirectional = False
            stop_balance = 0.0
            
        # Aggressive Order Percentage
        aggressive_pct = mbo_summary.get('aggressive_pct', 0.0) * 100
        aggressive_buy_pct = mbo_summary.get('aggressive_buy_pct', 50.0)
        aggressive_sell_pct = mbo_summary.get('aggressive_sell_pct', 50.0)
        
        # Displacement Detection (aggressive orders >70% + directional absorption)
        displacement_detected = (
            aggressive_pct > 70.0 and 
            (absorption_balance < 40.0 or absorption_balance > 60.0)
        )
        
        # Iceberg Presence (large hidden orders)
        iceberg_count = sum(1 for e in stops_data if e.get('event_type') == 'ICEBERG_DETECTED')
        iceberg_stacking = iceberg_count > 2  # Multiple icebergs = accumulation/distribution
        
        return {
            'absorption_balance': round(absorption_balance, 2),
            'absorption_balanced': 40.0 <= absorption_balance <= 60.0,
            'stops_bidirectional': stops_bidirectional,
            'stop_balance': round(stop_balance, 2),
            'aggressive_pct': round(aggressive_pct, 2),
            'aggressive_buy_pct': round(aggressive_buy_pct, 2),
            'aggressive_sell_pct': round(aggressive_sell_pct, 2),
            'displacement_detected': displacement_detected,
            'iceberg_count': iceberg_count,
            'iceberg_stacking': iceberg_stacking
        }
        
    def _classify_session(self, indicators: Dict) -> Tuple[str, float]:
        """
        Classify session as ACCUMULATION or EXPANSION with confidence
        
        ACCUMULATION indicators:
        - Balanced absorption (40-60%)
        - Bidirectional stops
        - Moderate aggressive orders (<70%)
        - No displacement
        - Two-sided action
        
        EXPANSION indicators:
        - Directional absorption (>60% or <40%)
        - Unidirectional stops
        - High aggressive orders (>70%)
        - Displacement detected
        - One-sided action
        """
        accumulation_score = 0
        expansion_score = 0
        
        # Absorption indicator
        if indicators['absorption_balanced']:
            accumulation_score += 25
        else:
            expansion_score += 25
            
        # Stops indicator
        if indicators['stops_bidirectional']:
            accumulation_score += 20
        else:
            expansion_score += 20
            
        # Aggressive orders
        if indicators['aggressive_pct'] < 70.0:
            accumulation_score += 20
        else:
            expansion_score += 25
            
        # Displacement
        if indicators['displacement_detected']:
            expansion_score += 25
        else:
            accumulation_score += 15
            
        # Iceberg stacking (sign of building position)
        if indicators['iceberg_stacking']:
            accumulation_score += 20
            
        # Calculate confidence (0-100)
        total_score = accumulation_score + expansion_score
        
        if accumulation_score > expansion_score:
            confidence = (accumulation_score / total_score) * 100 if total_score > 0 else 50.0
            return 'ACCUMULATION', round(confidence, 2)
        else:
            confidence = (expansion_score / total_score) * 100 if total_score > 0 else 50.0
            return 'EXPANSION', round(confidence, 2)
            
    def _determine_bias(self, indicators: Dict, absorption_data: List[Dict], mbo_summary: Dict) -> str:
        """Determine session bias (BULLISH, BEARISH, NEUTRAL)"""
        
        # Use aggressive order direction
        aggressive_buy_pct = indicators['aggressive_buy_pct']
        aggressive_sell_pct = indicators['aggressive_sell_pct']
        
        # Use absorption direction
        absorption_balance = indicators['absorption_balance']
        
        # Combine signals
        if aggressive_buy_pct > 60.0 and absorption_balance > 55.0:
            return 'BULLISH'
        elif aggressive_sell_pct > 60.0 and absorption_balance < 45.0:
            return 'BEARISH'
        else:
            return 'NEUTRAL'

# =====================================================
# Cycle Determinator
# =====================================================

class CycleDeterminator:
    """Determines AMDX vs XAMD cycle type"""
    
    def __init__(self, session_analyzer: SessionAnalyzer):
        self.session_analyzer = session_analyzer
        
    def determine_daily_cycle(self, date: datetime) -> Dict:
        """
        Determine AMDX vs XAMD for the given date using overnight data
        Must complete before 9:45 AM EST
        
        Process:
        1. Analyze Asia session (previous day 6 PM - 12 AM)
        2. Analyze London session (current day 12 AM - 6 AM)
        3. Analyze Pre-NY session (current day 7:30 AM - 9:30 AM)
        4. Combine results to determine cycle type
        
        Returns:
            {
                'date': str,
                'cycle_type': 'AMDX' or 'XAMD',
                'confidence': float (0-100),
                'sessions': {
                    'asia': {...},
                    'london': {...},
                    'pre_ny': {...}
                },
                'reasoning': str
            }
        """
        date_est = date.astimezone(EST) if date.tzinfo else EST.localize(date)
        logger.info(f"Determining daily cycle for {date_est.date()}")
        
        # Define session time ranges
        previous_day = date_est - timedelta(days=1)
        
        asia_start = previous_day.replace(hour=18, minute=0, second=0)
        asia_end = date_est.replace(hour=0, minute=0, second=0)
        
        london_start = date_est.replace(hour=0, minute=0, second=0)
        london_end = date_est.replace(hour=6, minute=0, second=0)
        
        pre_ny_start = date_est.replace(hour=7, minute=30, second=0)
        pre_ny_end = date_est.replace(hour=9, minute=30, second=0)
        
        # Analyze each session
        asia_analysis = self.session_analyzer.analyze_session(asia_start, asia_end, 'ASIA')
        london_analysis = self.session_analyzer.analyze_session(london_start, london_end, 'LONDON')
        pre_ny_analysis = self.session_analyzer.analyze_session(pre_ny_start, pre_ny_end, 'PRE_NY')
        
        # Determine cycle type
        cycle_type, confidence, reasoning = self._combine_sessions(
            asia_analysis, london_analysis, pre_ny_analysis
        )
        
        return {
            'date': date_est.date().isoformat(),
            'determination_time': datetime.now(EST).isoformat(),
            'cycle_type': cycle_type,
            'confidence': confidence,
            'sessions': {
                'asia': asia_analysis,
                'london': london_analysis,
                'pre_ny': pre_ny_analysis
            },
            'reasoning': reasoning,
            'next_quarter_expected': self._predict_next_quarter(cycle_type, date_est)
        }
        
    def _combine_sessions(self, asia: Dict, london: Dict, pre_ny: Dict) -> Tuple[str, float, str]:
        """
        Combine session analyses to determine AMDX or XAMD
        
        AMDX Profile:
        - Q1 (Asia/London): Accumulation (two-sided, balanced)
        - Q2 (NY AM): Manipulation (sweeps, fake moves)
        - Q3 (NY PM): Distribution (true directional move)
        - Q4 (After hours): Continuation
        
        XAMD Profile:
        - Q1 (Asia/London): Expansion/Continuation from previous day
        - Q2 (NY AM): Accumulation (consolidation, range building)
        - Q3 (NY PM): Manipulation (liquidity sweep)
        - Q4 (After hours): Distribution
        
        Logic:
        - If Asia/London = ACCUMULATION → likely AMDX (Q1 accumulation starting)
        - If Asia/London = EXPANSION → likely XAMD (Q1 continuation from previous day)
        """
        
        # Extract classifications
        asia_class = asia['classification']
        london_class = london['classification']
        pre_ny_class = pre_ny['classification']
        
        # Extract confidences
        asia_conf = asia['confidence']
        london_conf = london['confidence']
        pre_ny_conf = pre_ny['confidence']
        
        # Scoring system
        amdx_score = 0
        xamd_score = 0
        
        # Asia session (most important for overnight classification)
        if asia_class == 'ACCUMULATION':
            amdx_score += 40 * (asia_conf / 100)
        else:  # EXPANSION
            xamd_score += 40 * (asia_conf / 100)
            
        # London session (confirmation)
        if london_class == 'ACCUMULATION':
            amdx_score += 30 * (london_conf / 100)
        else:  # EXPANSION
            xamd_score += 30 * (london_conf / 100)
            
        # Pre-NY session (validation)
        if pre_ny_class == 'ACCUMULATION':
            amdx_score += 20 * (pre_ny_conf / 100)
        elif pre_ny_class == 'EXPANSION':
            # Early distribution signs
            xamd_score += 20 * (pre_ny_conf / 100)
        else:
            # Manipulation starting (Q2 for AMDX)
            amdx_score += 10
            
        # Determine cycle type
        total_score = amdx_score + xamd_score
        
        if amdx_score > xamd_score:
            cycle_type = 'AMDX'
            confidence = (amdx_score / total_score) * 100 if total_score > 0 else 50.0
            reasoning = f"Asia {asia_class} ({asia_conf:.0f}%), London {london_class} ({london_conf:.0f}%) → AMDX Q1 Accumulation starting"
        else:
            cycle_type = 'XAMD'
            confidence = (xamd_score / total_score) * 100 if total_score > 0 else 50.0
            reasoning = f"Asia {asia_class} ({asia_conf:.0f}%), London {london_class} ({london_conf:.0f}%) → XAMD Q1 Continuation from previous day"
            
        return cycle_type, round(confidence, 2), reasoning
        
    def _predict_next_quarter(self, cycle_type: str, current_time: datetime) -> Dict:
        """Predict when next quarter will begin"""
        
        if cycle_type == 'AMDX':
            # Q1: 12 AM-6 AM, Q2: 6 AM-12 PM, Q3: 12 PM-6 PM, Q4: 6 PM-12 AM
            if DAILY_Q1.contains(current_time):
                next_q = 'Q2'
                next_time = current_time.replace(hour=6, minute=0, second=0)
            elif DAILY_Q2.contains(current_time):
                next_q = 'Q3'
                next_time = current_time.replace(hour=12, minute=0, second=0)
            elif DAILY_Q3.contains(current_time):
                next_q = 'Q4'
                next_time = current_time.replace(hour=18, minute=0, second=0)
            else:
                next_q = 'Q1'
                next_time = (current_time + timedelta(days=1)).replace(hour=0, minute=0, second=0)
        else:  # XAMD
            # Same time windows but different characteristics
            if DAILY_Q1.contains(current_time):
                next_q = 'Q2'
                next_time = current_time.replace(hour=6, minute=0, second=0)
            elif DAILY_Q2.contains(current_time):
                next_q = 'Q3'
                next_time = current_time.replace(hour=12, minute=0, second=0)
            elif DAILY_Q3.contains(current_time):
                next_q = 'Q4'
                next_time = current_time.replace(hour=18, minute=0, second=0)
            else:
                next_q = 'Q1'
                next_time = (current_time + timedelta(days=1)).replace(hour=0, minute=0, second=0)
                
        minutes_until = int((next_time - current_time).total_seconds() / 60)
        
        return {
            'next_quarter': next_q,
            'expected_time': next_time.isoformat(),
            'minutes_until': minutes_until
        }

# =====================================================
# Phase Tracker
# =====================================================

class PhaseTracker:
    """Tracks real-time phase transitions within quarters"""
    
    def __init__(self, data_fetcher: DataFetcher):
        self.data_fetcher = data_fetcher
        self.current_phase = None
        
    def track_phase(self, cycle_type: str, current_quarter: str, current_time: datetime) -> Dict:
        """
        Track current phase within quarter
        
        Returns:
            {
                'quarter': str,
                'phase': str,
                'confidence': float,
                'duration_minutes': int,
                'transition_expected_in': int,
                'triggers_active': list,
                'status_message': str
            }
        """
        # Get last 5 minutes of data for real-time analysis
        end_time = current_time
        start_time = current_time - timedelta(minutes=5)
        
        absorption_data = self.data_fetcher.get_absorption_data(start_time, end_time)
        stops_data = self.data_fetcher.get_stops_icebergs_data(start_time, end_time)
        mbo_summary = self.data_fetcher.get_mbo_summary(start_time, end_time)
        
        # Detect phase based on characteristics
        phase, confidence, triggers = self._identify_phase(
            cycle_type, current_quarter, absorption_data, stops_data, mbo_summary
        )
        
        # Generate status message
        status_message = self._generate_status_message(cycle_type, current_quarter, phase)
        
        return {
            'quarter': current_quarter,
            'phase': phase,
            'confidence': confidence,
            'triggers_active': triggers,
            'status_message': status_message,
            'timestamp': current_time.isoformat()
        }
        
    def _identify_phase(self, cycle_type: str, quarter: str, 
                       absorption: List[Dict], stops: List[Dict], 
                       mbo: Dict) -> Tuple[str, float, List[str]]:
        """Identify current phase within quarter"""
        
        # Calculate indicators
        directional_absorption = False
        manipulation_detected = False
        displacement_detected = False
        
        if absorption:
            bid_count = sum(1 for e in absorption if e.get('side') == 'BID')
            ask_count = sum(1 for e in absorption if e.get('side') == 'ASK')
            total = bid_count + ask_count
            directional_absorption = (bid_count / total > 0.6 or ask_count / total > 0.6) if total > 0 else False
            
        if stops:
            # Manipulation: stops swept with immediate reversal
            for i, stop in enumerate(stops):
                if i < len(stops) - 1:
                    next_stop = stops[i + 1]
                    time_diff = (next_stop['timestamp'] - stop['timestamp']).total_seconds()
                    if time_diff < 60 and stop['stop_type'] != next_stop['stop_type']:
                        manipulation_detected = True
                        break
                        
        aggressive_pct = mbo.get('aggressive_pct', 0) * 100
        if aggressive_pct > 70 and directional_absorption:
            displacement_detected = True
            
        # Phase determination based on cycle type and quarter
        triggers = []
        
        if cycle_type == 'AMDX':
            if quarter == 'Q1':
                phase = 'ACCUMULATION'
                confidence = 80.0
                if not directional_absorption:
                    triggers.append('BALANCED_FLOW')
            elif quarter == 'Q2':
                phase = 'MANIPULATION'
                confidence = 85.0 if manipulation_detected else 70.0
                if manipulation_detected:
                    triggers.append('LIQUIDITY_SWEEP')
            elif quarter == 'Q3':
                phase = 'DISTRIBUTION'
                confidence = 90.0 if displacement_detected else 75.0
                if displacement_detected:
                    triggers.append('DISPLACEMENT_DETECTED')
                if directional_absorption:
                    triggers.append('DIRECTIONAL_FLOW')
            else:  # Q4
                phase = 'CONTINUATION'
                confidence = 75.0
                
        else:  # XAMD
            if quarter == 'Q1':
                phase = 'CONTINUATION'
                confidence = 75.0
            elif quarter == 'Q2':
                phase = 'ACCUMULATION'
                confidence = 80.0
            elif quarter == 'Q3':
                phase = 'MANIPULATION'
                confidence = 85.0 if manipulation_detected else 70.0
                if manipulation_detected:
                    triggers.append('LIQUIDITY_SWEEP')
            else:  # Q4
                phase = 'DISTRIBUTION'
                confidence = 90.0 if displacement_detected else 75.0
                if displacement_detected:
                    triggers.append('DISPLACEMENT_DETECTED')
                    
        return phase, confidence, triggers
        
    def _generate_status_message(self, cycle_type: str, quarter: str, phase: str) -> str:
        """Generate human-readable status message"""
        
        if phase == 'ACCUMULATION':
            return f"Market in ACCUMULATION phase ({quarter}). Balanced flow, building position. Wait for setup."
        elif phase == 'MANIPULATION':
            return f"MANIPULATION phase ({quarter}) ACTIVE. Liquidity sweep in progress. DO NOT CHASE - Let fake move complete."
        elif phase == 'DISTRIBUTION':
            return f"DISTRIBUTION phase ({quarter}) ACTIVE. Real move confirmed. Entry window OPEN - Look for sweep rejection entries."
        elif phase == 'CONTINUATION':
            return f"CONTINUATION phase ({quarter}). Trend extension or consolidation. Monitor for next cycle start."
        else:
            return f"Phase transition detected ({quarter}). Monitoring for confirmation."
