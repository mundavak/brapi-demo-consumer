"""
Session Cycle Tracker
Purpose: Track individual session cycles (Asia, London, NY AM, NY PM) with 
         high/low tracking and liquidity sweep detection
Author: AI Assistant
Created: 2025-10-30
"""

from quarterly_theory_engine import *
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import pytz

# =====================================================
# Session Definitions with Quarter Breakdowns
# =====================================================

@dataclass
class SessionQuarters:
    """Quarter time windows within a session"""
    q1_start: int  # Hour
    q1_start_min: int  # Minute
    q1_end: int
    q1_end_min: int
    
    q2_start: int
    q2_start_min: int
    q2_end: int
    q2_end_min: int
    
    q3_start: int
    q3_start_min: int
    q3_end: int
    q3_end_min: int
    
    q4_start: int
    q4_start_min: int
    q4_end: int
    q4_end_min: int

# Session definitions with quarter breakdowns
ASIA_QUARTERS = SessionQuarters(
    q1_start=18, q1_start_min=0, q1_end=19, q1_end_min=30,
    q2_start=19, q2_start_min=30, q2_end=21, q2_end_min=0,
    q3_start=21, q3_start_min=0, q3_end=22, q3_end_min=30,
    q4_start=22, q4_start_min=30, q4_end=24, q4_end_min=0
)

LONDON_QUARTERS = SessionQuarters(
    q1_start=0, q1_start_min=0, q1_end=1, q1_end_min=30,
    q2_start=1, q2_start_min=30, q2_end=3, q2_end_min=0,
    q3_start=3, q3_start_min=0, q3_end=4, q3_end_min=30,
    q4_start=4, q4_start_min=30, q4_end=6, q4_end_min=0
)

NY_AM_QUARTERS = SessionQuarters(
    q1_start=7, q1_start_min=30, q1_end=9, q1_end_min=0,
    q2_start=9, q2_start_min=0, q2_end=10, q2_end_min=30,
    q3_start=10, q3_start_min=30, q3_end=12, q3_end_min=0,
    q4_start=12, q4_start_min=0, q4_end=13, q4_end_min=30
)

NY_PM_QUARTERS = SessionQuarters(
    q1_start=13, q1_start_min=30, q1_end=14, q1_end_min=45,
    q2_start=14, q2_start_min=45, q2_end=16, q2_end_min=0,
    q3_start=16, q3_start_min=0, q3_end=17, q3_end_min=15,
    q4_start=17, q4_start_min=15, q4_end=18, q4_end_min=0
)

SESSION_DEFINITIONS = {
    'ASIA': {
        'start_hour': 18, 'start_min': 0,
        'end_hour': 24, 'end_min': 0,  # Crosses midnight
        'quarters': ASIA_QUARTERS
    },
    'LONDON': {
        'start_hour': 0, 'start_min': 0,
        'end_hour': 6, 'end_min': 0,
        'quarters': LONDON_QUARTERS
    },
    'NY_AM': {
        'start_hour': 7, 'start_min': 30,
        'end_hour': 13, 'end_min': 30,
        'quarters': NY_AM_QUARTERS
    },
    'NY_PM': {
        'start_hour': 13, 'start_min': 30,
        'end_hour': 18, 'end_min': 0,
        'quarters': NY_PM_QUARTERS
    }
}

# =====================================================
# Session Cycle State
# =====================================================

@dataclass
class SessionCycleState:
    """Current state of a session cycle"""
    session: str
    session_start: datetime
    session_end: datetime
    cycle_type: Optional[str] = None
    confidence: float = 0.0
    
    # High/Low tracking
    session_high: float = 0.0
    session_low: float = float('inf')
    session_high_time: Optional[datetime] = None
    session_low_time: Optional[datetime] = None
    session_open: Optional[float] = None
    session_close: Optional[float] = None
    
    # Quarter-specific highs/lows
    q1_high: float = 0.0
    q1_low: float = float('inf')
    q2_high: float = 0.0
    q2_low: float = float('inf')
    q3_high: float = 0.0
    q3_low: float = float('inf')
    q4_high: float = 0.0
    q4_low: float = float('inf')
    
    # Current quarter
    current_quarter: Optional[str] = None
    quarter_phase: Optional[str] = None
    
    # Liquidity sweeps detected during session
    liquidity_sweeps: List[Dict] = None
    
    # Session characteristics
    total_volume: int = 0
    aggressive_buy_volume: int = 0
    aggressive_sell_volume: int = 0
    directional_bias: Optional[str] = None
    
    # Flags
    manipulation_detected: bool = False
    reversal_after_sweep: bool = False
    is_completed: bool = False
    
    def __post_init__(self):
        if self.liquidity_sweeps is None:
            self.liquidity_sweeps = []

# =====================================================
# Session Cycle Tracker
# =====================================================

class SessionCycleTracker:
    """Tracks session cycles with high/low and liquidity sweep detection"""
    
    def __init__(self, db_manager: DatabaseManager, data_fetcher):
        self.db = db_manager
        self.data_fetcher = data_fetcher
        self.active_sessions: Dict[str, SessionCycleState] = {}
        self.key_levels_cache: Dict[str, Dict] = {}  # Cache of key levels
        
    def initialize_session(self, session: str, current_time: datetime) -> SessionCycleState:
        """Initialize a new session cycle"""
        current_time_est = current_time.astimezone(EST) if current_time.tzinfo else EST.localize(current_time)
        
        # Get session definition
        session_def = SESSION_DEFINITIONS[session]
        
        # Calculate session start/end times
        if session == 'ASIA':
            # Asia crosses midnight
            session_start = current_time_est.replace(
                hour=session_def['start_hour'], 
                minute=session_def['start_min'], 
                second=0, 
                microsecond=0
            )
            session_end = (session_start + timedelta(hours=6)).replace(hour=0, minute=0)
        else:
            session_start = current_time_est.replace(
                hour=session_def['start_hour'],
                minute=session_def['start_min'],
                second=0,
                microsecond=0
            )
            session_end = current_time_est.replace(
                hour=session_def['end_hour'],
                minute=session_def['end_min'],
                second=0,
                microsecond=0
            )
        
        # Create session state
        state = SessionCycleState(
            session=session,
            session_start=session_start,
            session_end=session_end
        )
        
        # Get first price as session open
        current_price = self.data_fetcher.get_latest_price()
        if current_price:
            state.session_open = current_price
            state.session_high = current_price
            state.session_low = current_price
            state.session_high_time = current_time_est
            state.session_low_time = current_time_est
        
        self.active_sessions[session] = state
        logger.info(f"Initialized {session} session: {session_start} to {session_end}")
        
        return state
        
    def update_session_high_low(self, session: str, current_time: datetime, current_price: float):
        """Update session high/low tracking"""
        if session not in self.active_sessions:
            return
            
        state = self.active_sessions[session]
        
        # Update session high
        if current_price > state.session_high:
            state.session_high = current_price
            state.session_high_time = current_time
            logger.debug(f"{session} new high: {current_price} at {current_time.strftime('%H:%M:%S')}")
            
        # Update session low
        if current_price < state.session_low:
            state.session_low = current_price
            state.session_low_time = current_time
            logger.debug(f"{session} new low: {current_price} at {current_time.strftime('%H:%M:%S')}")
            
        # Determine current quarter and update quarter-specific highs/lows
        current_quarter = self._determine_quarter(session, current_time)
        state.current_quarter = current_quarter
        
        if current_quarter == 'Q1':
            state.q1_high = max(state.q1_high, current_price)
            state.q1_low = min(state.q1_low, current_price) if state.q1_low != float('inf') else current_price
        elif current_quarter == 'Q2':
            state.q2_high = max(state.q2_high, current_price)
            state.q2_low = min(state.q2_low, current_price) if state.q2_low != float('inf') else current_price
        elif current_quarter == 'Q3':
            state.q3_high = max(state.q3_high, current_price)
            state.q3_low = min(state.q3_low, current_price) if state.q3_low != float('inf') else current_price
        elif current_quarter == 'Q4':
            state.q4_high = max(state.q4_high, current_price)
            state.q4_low = min(state.q4_low, current_price) if state.q4_low != float('inf') else current_price
            
    def _determine_quarter(self, session: str, current_time: datetime) -> str:
        """Determine which quarter we're in within the session"""
        quarters = SESSION_DEFINITIONS[session]['quarters']
        time_minutes = current_time.hour * 60 + current_time.minute
        
        q1_start = quarters.q1_start * 60 + quarters.q1_start_min
        q1_end = quarters.q1_end * 60 + quarters.q1_end_min
        q2_start = quarters.q2_start * 60 + quarters.q2_start_min
        q2_end = quarters.q2_end * 60 + quarters.q2_end_min
        q3_start = quarters.q3_start * 60 + quarters.q3_start_min
        q3_end = quarters.q3_end * 60 + quarters.q3_end_min
        q4_start = quarters.q4_start * 60 + quarters.q4_start_min
        q4_end = quarters.q4_end * 60 + quarters.q4_end_min
        
        if q1_start <= time_minutes < q1_end:
            return 'Q1'
        elif q2_start <= time_minutes < q2_end:
            return 'Q2'
        elif q3_start <= time_minutes < q3_end:
            return 'Q3'
        elif q4_start <= time_minutes < q4_end:
            return 'Q4'
        else:
            return 'Q1'  # Default
            
    def detect_liquidity_sweeps(self, session: str, current_time: datetime, current_price: float):
        """Detect if current price swept any key liquidity levels"""
        if session not in self.active_sessions:
            return
            
        # Get key levels for sweep detection
        key_levels = self._get_key_levels(current_time)
        
        # Check each level
        for level in key_levels:
            level_name = level['name']
            level_price = level['price']
            level_type = level['type']
            
            # Determine if sweep occurred
            sweep_detected = False
            tolerance_ticks = 3
            tick_size = 0.25  # NQ tick size
            tolerance = tick_size * tolerance_ticks
            
            if level_type.endswith('HIGH'):
                # Sweeping a high requires price to go above
                sweep_detected = current_price >= (level_price + tolerance)
            elif level_type.endswith('LOW'):
                # Sweeping a low requires price to go below
                sweep_detected = current_price <= (level_price - tolerance)
                
            if sweep_detected:
                # Check if already recorded
                existing_sweep = any(
                    s['level_name'] == level_name 
                    for s in self.active_sessions[session].liquidity_sweeps
                )
                
                if not existing_sweep:
                    sweep_event = {
                        'timestamp': current_time,
                        'level_name': level_name,
                        'level_price': level_price,
                        'level_type': level_type,
                        'sweep_price': current_price,
                        'ticks_beyond': abs(current_price - level_price) / tick_size,
                        'confirmed': True  # Will check for close beyond level later
                    }
                    
                    self.active_sessions[session].liquidity_sweeps.append(sweep_event)
                    
                    logger.info(f"LIQUIDITY SWEEP DETECTED: {session} - {level_name} at {level_price} swept by {current_price}")
                    
                    # Write to database
                    self._write_liquidity_sweep(session, sweep_event)
                    
    def _get_key_levels(self, current_time: datetime) -> List[Dict]:
        """Get key liquidity levels for sweep detection"""
        levels = []
        
        # Check cache first
        cache_key = current_time.strftime('%Y-%m-%d')
        if cache_key in self.key_levels_cache:
            return self.key_levels_cache[cache_key]
        
        cursor = self.db.get_cursor()
        
        try:
            # Get previous day high/low
            cursor.execute("""
                SELECT 
                    'PREVIOUS_DAY_HIGH' as name,
                    MAX(session_high) as price,
                    'DAILY_HIGH' as type
                FROM session_cycles
                WHERE session_end::date = %s::date - INTERVAL '1 day'
                AND session_high IS NOT NULL
            """, (current_time,))
            
            prev_day_high = cursor.fetchone()
            if prev_day_high and prev_day_high['price']:
                levels.append(dict(prev_day_high))
                
            cursor.execute("""
                SELECT 
                    'PREVIOUS_DAY_LOW' as name,
                    MIN(session_low) as price,
                    'DAILY_LOW' as type
                FROM session_cycles
                WHERE session_end::date = %s::date - INTERVAL '1 day'
                AND session_low IS NOT NULL
            """, (current_time,))
            
            prev_day_low = cursor.fetchone()
            if prev_day_low and prev_day_low['price']:
                levels.append(dict(prev_day_low))
                
            # Get session highs/lows from today
            for sess in ['ASIA', 'LONDON']:
                cursor.execute("""
                    SELECT 
                        %s || '_HIGH' as name,
                        session_high as price,
                        'SESSION_HIGH' as type
                    FROM session_cycles
                    WHERE session = %s
                    AND session_start::date = %s::date
                    AND session_high IS NOT NULL
                    ORDER BY session_start DESC
                    LIMIT 1
                """, (sess, sess, current_time))
                
                sess_high = cursor.fetchone()
                if sess_high and sess_high['price']:
                    levels.append(dict(sess_high))
                    
                cursor.execute("""
                    SELECT 
                        %s || '_LOW' as name,
                        session_low as price,
                        'SESSION_LOW' as type
                    FROM session_cycles
                    WHERE session = %s
                    AND session_start::date = %s::date
                    AND session_low IS NOT NULL
                    ORDER BY session_start DESC
                    LIMIT 1
                """, (sess, sess, current_time))
                
                sess_low = cursor.fetchone()
                if sess_low and sess_low['price']:
                    levels.append(dict(sess_low))
                    
            # Cache the levels
            self.key_levels_cache[cache_key] = levels
            
        finally:
            cursor.close()
            
        return levels
        
    def _write_liquidity_sweep(self, session: str, sweep_event: Dict):
        """Write liquidity sweep to database"""
        cursor = self.db.get_cursor()
        
        try:
            cursor.execute("""
                INSERT INTO liquidity_sweeps (
                    timestamp, symbol, session, sweep_type,
                    level_price, level_source, sweep_price,
                    ticks_beyond, sweep_confirmed
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                sweep_event['timestamp'],
                'NQ',
                session,
                sweep_event['level_type'],
                sweep_event['level_price'],
                sweep_event['level_name'],
                sweep_event['sweep_price'],
                sweep_event['ticks_beyond'],
                sweep_event['confirmed']
            ))
            
            self.db.conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to write liquidity sweep: {e}")
            self.db.conn.rollback()
        finally:
            cursor.close()
            
    def check_reversal_after_sweep(self, session: str, current_time: datetime, current_price: float):
        """Check if price reversed after a recent liquidity sweep"""
        if session not in self.active_sessions:
            return
            
        state = self.active_sessions[session]
        
        # Check recent sweeps (within last 5 minutes)
        recent_sweeps = [
            s for s in state.liquidity_sweeps
            if (current_time - s['timestamp']).total_seconds() <= 300  # 5 minutes
            and not s.get('reversal_checked', False)
        ]
        
        for sweep in recent_sweeps:
            sweep_price = sweep['sweep_price']
            level_type = sweep['level_type']
            
            # Check for reversal
            reversal_detected = False
            
            if level_type.endswith('HIGH'):
                # After sweeping high, reversal = price drops significantly
                if current_price < (sweep_price - 10 * 0.25):  # 10 ticks down
                    reversal_detected = True
            elif level_type.endswith('LOW'):
                # After sweeping low, reversal = price rises significantly
                if current_price > (sweep_price + 10 * 0.25):  # 10 ticks up
                    reversal_detected = True
                    
            if reversal_detected:
                sweep['reversal_detected'] = True
                sweep['reversal_time'] = current_time
                sweep['reversal_price'] = current_price
                sweep['reversal_duration'] = (current_time - sweep['timestamp']).total_seconds()
                
                state.manipulation_detected = True
                state.reversal_after_sweep = True
                
                logger.warning(f"REVERSAL DETECTED: {session} - Sweep at {sweep_price} reversed to {current_price}")
                
                # Update database
                self._update_sweep_reversal(sweep)
                
            sweep['reversal_checked'] = True
            
    def _update_sweep_reversal(self, sweep: Dict):
        """Update liquidity sweep with reversal information"""
        cursor = self.db.get_cursor()
        
        try:
            cursor.execute("""
                UPDATE liquidity_sweeps
                SET reversal_detected = TRUE,
                    reversal_time = %s,
                    reversal_price = %s,
                    reversal_duration_seconds = %s,
                    is_fake_move = TRUE
                WHERE timestamp = %s
                AND level_source = %s
            """, (
                sweep.get('reversal_time'),
                sweep.get('reversal_price'),
                sweep.get('reversal_duration'),
                sweep['timestamp'],
                sweep['level_name']
            ))
            
            self.db.conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to update sweep reversal: {e}")
            self.db.conn.rollback()
        finally:
            cursor.close()
            
    def complete_session(self, session: str):
        """Mark session as completed and write final data to database"""
        if session not in self.active_sessions:
            return
            
        state = self.active_sessions[session]
        state.is_completed = True
        
        # Get current price as session close
        state.session_close = self.data_fetcher.get_latest_price() or state.session_close
        
        # Calculate volatility
        if state.session_high and state.session_low:
            state.directional_bias = self._calculate_directional_bias(state)
            
        # Write to database
        self._write_session_cycle(state)
        
        logger.info(f"Completed {session} session - High: {state.session_high}, Low: {state.session_low}, Sweeps: {len(state.liquidity_sweeps)}")
        
    def _calculate_directional_bias(self, state: SessionCycleState) -> str:
        """Calculate directional bias from session data"""
        if state.aggressive_buy_volume > state.aggressive_sell_volume * 1.5:
            return 'BULLISH'
        elif state.aggressive_sell_volume > state.aggressive_buy_volume * 1.5:
            return 'BEARISH'
        else:
            return 'NEUTRAL'
            
    def _write_session_cycle(self, state: SessionCycleState):
        """Write completed session cycle to database"""
        cursor = self.db.get_cursor()
        
        try:
            # Convert inf to None for database
            q1_low = None if state.q1_low == float('inf') else state.q1_low
            q2_low = None if state.q2_low == float('inf') else state.q2_low
            q3_low = None if state.q3_low == float('inf') else state.q3_low
            q4_low = None if state.q4_low == float('inf') else state.q4_low
            session_low = None if state.session_low == float('inf') else state.session_low
            
            cursor.execute("""
                INSERT INTO session_cycles (
                    timestamp, symbol, session, session_start, session_end,
                    cycle_type, confidence_score, current_quarter, quarter_phase,
                    session_high, session_low, session_high_time, session_low_time,
                    session_open, session_close,
                    q1_high, q1_low, q2_high, q2_low, q3_high, q3_low, q4_high, q4_low,
                    liquidity_sweeps, manipulation_detected, reversal_after_sweep,
                    volatility, directional_bias, is_completed
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                state.session_end,
                'NQ',
                state.session,
                state.session_start,
                state.session_end,
                state.cycle_type,
                state.confidence,
                state.current_quarter,
                state.quarter_phase,
                state.session_high,
                session_low,
                state.session_high_time,
                state.session_low_time,
                state.session_open,
                state.session_close,
                state.q1_high if state.q1_high > 0 else None,
                q1_low,
                state.q2_high if state.q2_high > 0 else None,
                q2_low,
                state.q3_high if state.q3_high > 0 else None,
                q3_low,
                state.q4_high if state.q4_high > 0 else None,
                q4_low,
                Json(state.liquidity_sweeps),
                state.manipulation_detected,
                state.reversal_after_sweep,
                state.session_high - session_low if session_low else None,
                state.directional_bias,
                state.is_completed
            ))
            
            self.db.conn.commit()
            logger.info(f"Written {state.session} session cycle to database")
            
        except Exception as e:
            logger.error(f"Failed to write session cycle: {e}")
            self.db.conn.rollback()
        finally:
            cursor.close()
