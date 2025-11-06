"""
Quarterly Theory Database Writer
Purpose: Write analysis results to TimescaleDB quarterly theory tables
Author: AI Assistant
Created: 2025-10-29
"""

from quarterly_theory_engine import *
from quarterly_analysis_core import (
    SessionAnalyzer, 
    CycleDeterminator, 
    PhaseTracker
)
from session_cycle_tracker import SessionCycleTracker
from psycopg2.extras import Json
import json

class QuarterlyDatabaseWriter:
    """Writes quarterly theory analysis results to TimescaleDB"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        
    def write_cycle_determination(self, cycle_data: Dict, symbol: str = 'NQ'):
        """Write daily cycle determination to quarterly_cycles table"""
        cursor = self.db.get_cursor()
        
        try:
            # Extract data
            cycle_type = cycle_data['cycle_type']
            confidence = cycle_data['confidence']
            determination_time = datetime.fromisoformat(cycle_data['determination_time'])
            
            # Build supporting evidence
            supporting_evidence = {
                'sessions': cycle_data['sessions'],
                'reasoning': cycle_data['reasoning'],
                'next_quarter_prediction': cycle_data['next_quarter_expected']
            }
            
            # Determine current quarter based on time
            current_time = determination_time.astimezone(EST)
            if DAILY_Q1.contains(current_time):
                current_quarter = 'Q1'
            elif DAILY_Q2.contains(current_time):
                current_quarter = 'Q2'
            elif DAILY_Q3.contains(current_time):
                current_quarter = 'Q3'
            else:
                current_quarter = 'Q4'
                
            # Map quarter to phase based on cycle type
            phase_map = {
                'AMDX': {'Q1': 'ACCUMULATION', 'Q2': 'MANIPULATION', 'Q3': 'DISTRIBUTION', 'Q4': 'CONTINUATION'},
                'XAMD': {'Q1': 'CONTINUATION', 'Q2': 'ACCUMULATION', 'Q3': 'MANIPULATION', 'Q4': 'DISTRIBUTION'}
            }
            quarter_phase = phase_map.get(cycle_type, {}).get(current_quarter, 'TRANSITION')
            
            # Insert record
            cursor.execute("""
                INSERT INTO quarterly_cycles (
                    timestamp, symbol, timeframe, cycle_type, 
                    current_quarter, quarter_phase, confidence_score, 
                    supporting_evidence
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                determination_time,
                symbol,
                'daily',
                cycle_type,
                current_quarter,
                quarter_phase,
                confidence,
                Json(supporting_evidence)
            ))
            
            self.db.conn.commit()
            logger.info(f"Written daily cycle: {cycle_type} {current_quarter} ({confidence:.1f}%)")
            
        except Exception as e:
            logger.error(f"Failed to write cycle determination: {e}")
            self.db.conn.rollback()
            raise
        finally:
            cursor.close()
            
    def write_phase_transition(self, from_quarter: str, to_quarter: str, 
                              from_phase: str, to_phase: str,
                              trigger: str, price: float, 
                              supporting_data: Dict, symbol: str = 'NQ'):
        """Write phase transition to phase_transitions table"""
        cursor = self.db.get_cursor()
        
        try:
            cursor.execute("""
                INSERT INTO phase_transitions (
                    timestamp, symbol, from_quarter, to_quarter,
                    from_phase, to_phase, transition_trigger,
                    price_at_transition, supporting_data
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                datetime.now(EST),
                symbol,
                from_quarter,
                to_quarter,
                from_phase,
                to_phase,
                trigger,
                price,
                Json(supporting_data)
            ))
            
            self.db.conn.commit()
            logger.info(f"Phase transition recorded: {from_quarter}/{from_phase} → {to_quarter}/{to_phase}")
            
        except Exception as e:
            logger.error(f"Failed to write phase transition: {e}")
            self.db.conn.rollback()
        finally:
            cursor.close()
            
    def write_htf_bias(self, timeframe: str, bias: str, confidence: float,
                       key_levels: Dict, market_structure: Dict,
                       determination_method: str, valid_hours: int = 24,
                       symbol: str = 'NQ'):
        """Write higher timeframe bias to htf_bias table"""
        cursor = self.db.get_cursor()
        
        try:
            valid_until = datetime.now(EST) + timedelta(hours=valid_hours)
            
            cursor.execute("""
                INSERT INTO htf_bias (
                    timestamp, symbol, timeframe, bias, confidence_score,
                    key_levels, market_structure, determination_method,
                    valid_until, is_active
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                datetime.now(EST),
                symbol,
                timeframe,
                bias,
                confidence,
                Json(key_levels),
                Json(market_structure),
                determination_method,
                valid_until,
                True
            ))
            
            self.db.conn.commit()
            logger.info(f"HTF bias written: {timeframe} {bias} ({confidence:.1f}%)")
            
        except Exception as e:
            logger.error(f"Failed to write HTF bias: {e}")
            self.db.conn.rollback()
        finally:
            cursor.close()
            
    def write_session_bias(self, session: str, bias: str, confidence: float,
                          true_open_price: float, current_quarter: str,
                          quarter_phase: str, premium_high: float,
                          discount_low: float, fair_value: float,
                          price_zone: str, entry_recommendation: str,
                          fake_move_detected: bool, real_move_confirmed: bool,
                          entry_window_status: str, supporting_data: Dict,
                          symbol: str = 'NQ'):
        """Write session bias to session_bias table"""
        cursor = self.db.get_cursor()
        
        try:
            cursor.execute("""
                INSERT INTO session_bias (
                    timestamp, symbol, session, bias, confidence_score,
                    true_open_price, current_quarter, quarter_phase,
                    premium_zone_high, discount_zone_low, fair_value,
                    current_price_zone, entry_recommendation,
                    fake_move_detected, real_move_confirmed,
                    entry_window_status, supporting_data
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                datetime.now(EST),
                symbol,
                session,
                bias,
                confidence,
                true_open_price,
                current_quarter,
                quarter_phase,
                premium_high,
                discount_low,
                fair_value,
                price_zone,
                entry_recommendation,
                fake_move_detected,
                real_move_confirmed,
                entry_window_status,
                Json(supporting_data)
            ))
            
            self.db.conn.commit()
            logger.info(f"Session bias written: {session} {bias} - {entry_window_status}")
            
        except Exception as e:
            logger.error(f"Failed to write session bias: {e}")
            self.db.conn.rollback()
        finally:
            cursor.close()
            
    def get_current_cycle(self, symbol: str = 'NQ') -> Optional[Dict]:
        """Get most recent cycle determination"""
        cursor = self.db.get_cursor()
        
        try:
            cursor.execute("""
                SELECT * FROM quarterly_cycles
                WHERE symbol = %s AND timeframe = 'daily'
                ORDER BY timestamp DESC
                LIMIT 1
            """, (symbol,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
            
        finally:
            cursor.close()

# =====================================================
# Main Service Orchestrator
# =====================================================

class QuarterlyTheoryService:
    """Main service that orchestrates all quarterly theory analysis"""
    
    def __init__(self, db_config: Dict, redis_config: Dict):
        # Initialize managers
        self.db_manager = DatabaseManager(db_config)
        self.redis_manager = RedisManager(redis_config)
        
        # Connect
        self.db_manager.connect()
        self.redis_manager.connect()
        
        # Initialize components
        self.data_fetcher = DataFetcher(self.db_manager, self.redis_manager)
        self.session_analyzer = SessionAnalyzer(self.data_fetcher)
        self.cycle_determinator = CycleDeterminator(self.session_analyzer)
        self.phase_tracker = PhaseTracker(self.data_fetcher)
        self.db_writer = QuarterlyDatabaseWriter(self.db_manager)
        self.session_tracker = SessionCycleTracker(self.db_manager, self.data_fetcher)
        
        # State
        self.current_cycle_type = None
        self.current_quarter = None
        self.current_phase = None
        self.last_determination_date = None
        self.current_session = None
        
    async def run_pre_market_determination(self):
        """
        Run pre-market determination (before 9:45 AM EST)
        Should be called between 9:00 AM - 9:45 AM
        """
        now = datetime.now(EST)
        today = now.date()
        
        # Check if already determined for today
        if self.last_determination_date == today:
            logger.info(f"Cycle already determined for {today}")
            return
            
        logger.info("=" * 60)
        logger.info("Starting Pre-9:45 AM Cycle Determination")
        logger.info("=" * 60)
        
        # Determine cycle
        cycle_data = self.cycle_determinator.determine_daily_cycle(now)
        
        # Store results
        self.current_cycle_type = cycle_data['cycle_type']
        self.last_determination_date = today
        
        # Write to database
        self.db_writer.write_cycle_determination(cycle_data)
        
        # Log results
        logger.info(f"""
        Daily Cycle: {cycle_data['cycle_type']} ✓ ({cycle_data['confidence']:.1f}% confidence)
        Reasoning: {cycle_data['reasoning']}
        Next Quarter Expected: {cycle_data['next_quarter_expected']['next_quarter']} in {cycle_data['next_quarter_expected']['minutes_until']} minutes
        """)
        
        return cycle_data
        
    async def run_realtime_tracking(self):
        """
        Run real-time phase tracking (every 60 seconds during active hours)
        Includes session cycle tracking with high/low and liquidity sweep detection
        """
        now = datetime.now(EST)
        
        # Determine current session
        new_session = self._determine_current_session(now)
        
        # Check for session transition
        if new_session != self.current_session:
            # Complete previous session if exists
            if self.current_session:
                self.session_tracker.complete_session(self.current_session)
                
            # Initialize new session
            if new_session:
                self.session_tracker.initialize_session(new_session, now)
                
            self.current_session = new_session
            logger.info(f"Session transition: {self.current_session}")
            
        # Update session high/low tracking
        if self.current_session:
            current_price = self.data_fetcher.get_latest_price()
            if current_price:
                self.session_tracker.update_session_high_low(
                    self.current_session, 
                    now, 
                    current_price
                )
                
                # Detect liquidity sweeps
                self.session_tracker.detect_liquidity_sweeps(
                    self.current_session,
                    now,
                    current_price
                )
                
                # Check for reversals after sweeps
                self.session_tracker.check_reversal_after_sweep(
                    self.current_session,
                    now,
                    current_price
                )
        
        # Ensure we have cycle type
        if not self.current_cycle_type:
            # Try to load from database
            cycle_record = self.db_writer.get_current_cycle()
            if cycle_record:
                self.current_cycle_type = cycle_record['cycle_type']
            else:
                logger.warning("No cycle type determined yet - run pre-market determination first")
                return
                
        # Determine current quarter
        if DAILY_Q1.contains(now):
            new_quarter = 'Q1'
        elif DAILY_Q2.contains(now):
            new_quarter = 'Q2'
        elif DAILY_Q3.contains(now):
            new_quarter = 'Q3'
        else:
            new_quarter = 'Q4'
            
        # Check for quarter transition
        if self.current_quarter and new_quarter != self.current_quarter:
            logger.info(f"Quarter transition detected: {self.current_quarter} → {new_quarter}")
            
            # Get current price
            price = self.data_fetcher.get_latest_price()
            
            # Write transition
            self.db_writer.write_phase_transition(
                from_quarter=self.current_quarter,
                to_quarter=new_quarter,
                from_phase=self.current_phase or 'UNKNOWN',
                to_phase='TRANSITION',
                trigger='TIME_WINDOW_END',
                price=price or 0.0,
                supporting_data={'time': now.isoformat()}
            )
            
        self.current_quarter = new_quarter
        
        # Track phase
        phase_data = self.phase_tracker.track_phase(
            self.current_cycle_type, 
            self.current_quarter, 
            now
        )
        
        self.current_phase = phase_data['phase']
        
        # Determine entry window status
        entry_window_status = self._determine_entry_window(
            self.current_cycle_type,
            self.current_quarter,
            self.current_phase
        )
        
        # Get current price and calculate zones
        current_price = self.data_fetcher.get_latest_price() or 0.0
        
        # For now, use placeholder zones (should be calculated from actual data)
        fair_value = current_price
        premium_high = current_price + 50  # Adjust based on actual range
        discount_low = current_price - 50
        
        if current_price > fair_value:
            price_zone = 'PREMIUM'
        elif current_price < fair_value:
            price_zone = 'DISCOUNT'
        else:
            price_zone = 'FAIR_VALUE'
            
        # Determine bias from phase tracking
        bias = 'NEUTRAL'  # Simplified - should integrate with session analyzer
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            self.current_cycle_type,
            self.current_quarter,
            self.current_phase,
            entry_window_status,
            price_zone
        )
        
        # Detect fake/real moves
        fake_move_detected = (self.current_quarter == 'Q2' and 
                            self.current_phase == 'MANIPULATION')
        real_move_confirmed = (self.current_quarter == 'Q3' and 
                             self.current_phase == 'DISTRIBUTION')
        
        # Write session bias
        self.db_writer.write_session_bias(
            session='NY_AM' if now.hour < 13 else 'NY_PM',
            bias=bias,
            confidence=phase_data['confidence'],
            true_open_price=current_price,  # Should track actual true open
            current_quarter=self.current_quarter,
            quarter_phase=self.current_phase,
            premium_high=premium_high,
            discount_low=discount_low,
            fair_value=fair_value,
            price_zone=price_zone,
            entry_recommendation=recommendation,
            fake_move_detected=fake_move_detected,
            real_move_confirmed=real_move_confirmed,
            entry_window_status=entry_window_status,
            supporting_data=phase_data
        )
        
        # Log status
        logger.info(f"""
        [{now.strftime('%H:%M:%S')}] Cycle: {self.current_cycle_type} | Quarter: {self.current_quarter} | Phase: {self.current_phase}
        Entry Window: {entry_window_status} | {phase_data['status_message']}
        """)
        
    def _determine_current_session(self, current_time: datetime) -> Optional[str]:
        """Determine which session we're currently in"""
        hour = current_time.hour
        minute = current_time.minute
        time_minutes = hour * 60 + minute
        
        # ASIA: 18:00-00:00 (6 PM - 12 AM)
        if (hour >= 18) or (hour == 0 and minute == 0):
            return 'ASIA'
        # LONDON: 00:00-06:00 (12 AM - 6 AM)
        elif 0 <= hour < 6:
            return 'LONDON'
        # NY_AM: 07:30-13:30 (7:30 AM - 1:30 PM)
        elif (hour == 7 and minute >= 30) or (8 <= hour < 13) or (hour == 13 and minute < 30):
            return 'NY_AM'
        # NY_PM: 13:30-18:00 (1:30 PM - 6:00 PM)
        elif (hour == 13 and minute >= 30) or (14 <= hour < 18):
            return 'NY_PM'
        else:
            # Outside active sessions (6:00 AM - 7:30 AM pre-market period)
            return None
    
    def _determine_entry_window(self, cycle_type: str, quarter: str, phase: str) -> str:
        """Determine entry window status"""
        
        # Entry window is OPEN during Q3 (distribution) and Q4 (continuation)
        # For AMDX: Q3 = Distribution, Q4 = Continuation
        # For XAMD: Q3 = Manipulation (avoid), Q4 = Distribution
        
        if cycle_type == 'AMDX':
            if quarter == 'Q3' and phase == 'DISTRIBUTION':
                return 'OPTIMAL'
            elif quarter == 'Q4' and phase == 'CONTINUATION':
                return 'OPEN'
            elif quarter == 'Q2' and phase == 'MANIPULATION':
                return 'CLOSED'
            else:
                return 'OPENING' if quarter == 'Q2' else 'CLOSING'
                
        else:  # XAMD
            if quarter == 'Q4' and phase == 'DISTRIBUTION':
                return 'OPTIMAL'
            elif quarter == 'Q3' and phase == 'MANIPULATION':
                return 'CLOSED'
            else:
                return 'OPENING' if quarter == 'Q3' else 'CLOSING'
                
    def _generate_recommendation(self, cycle_type: str, quarter: str, 
                                phase: str, entry_status: str, 
                                price_zone: str) -> str:
        """Generate actionable recommendation"""
        
        if entry_status == 'OPTIMAL':
            return f"ENTRY WINDOW OPTIMAL - Real move active in {quarter}. Look for sweep rejection entries in {price_zone} zone."
        elif entry_status == 'OPEN':
            return f"Entry window open ({quarter}). Monitor for continuation setups."
        elif entry_status == 'CLOSED':
            return f"DO NOT TRADE - {phase} phase active. Wait for manipulation to complete."
        elif entry_status == 'OPENING':
            return f"Entry window opening soon. Prepare for {quarter} transition."
        else:
            return f"Entry window closing. Avoid new positions."
            
    async def start_service(self):
        """Start the quarterly theory service (main loop)"""
        logger.info("Quarterly Theory Service Started")
        
        while True:
            try:
                now = datetime.now(EST)
                
                # Run pre-market determination between 9:00-9:45 AM
                if 9 <= now.hour < 10 and now.minute < 45:
                    if self.last_determination_date != now.date():
                        await self.run_pre_market_determination()
                        
                # Run real-time tracking during active hours (7:30 AM - 8:00 PM)
                if 7 <= now.hour < 20:
                    await self.run_realtime_tracking()
                    
                # Sleep for 60 seconds
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Service error: {e}", exc_info=True)
                await asyncio.sleep(60)
                
    def close(self):
        """Cleanup resources"""
        self.db_manager.close()
        logger.info("Service stopped")

# =====================================================
# Entry Point
# =====================================================

async def main():
    """Main entry point"""
    
    # Load configuration
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'bookmap_data',
        'user': 'postgres',
        'password': 'your_password'
    }
    
    redis_config = {
        'host': 'localhost',
        'port': 6379,
        'db': 0
    }
    
    # Create service
    service = QuarterlyTheoryService(db_config, redis_config)
    
    try:
        # Start service
        await service.start_service()
    except KeyboardInterrupt:
        logger.info("Service interrupted by user")
    finally:
        service.close()

if __name__ == '__main__':
    asyncio.run(main())
