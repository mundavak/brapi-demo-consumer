"""
Quarterly Theory Analysis Engine
Purpose: Determine AMDX vs XAMD cycles, track phases, generate bias
Author: AI Assistant
Created: 2025-10-29

This module analyzes data from BookMap consumers (Absorption, Stops/Icebergs, MBO)
to determine quarterly cycles and phases in real-time.

Key Responsibilities:
1. Pre-9:45 AM determination of AMDX vs XAMD
2. Real-time phase tracking (Q1, Q2, Q3, Q4)
3. Fake vs Real move detection
4. Bias generation (HTF, Daily, Session)
5. Entry window status management
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import pytz
import redis
import psycopg2
from psycopg2.extras import Json, RealDictCursor
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timezone
EST = pytz.timezone('America/New_York')

# =====================================================
# Enums and Data Classes
# =====================================================

class CycleType(Enum):
    AMDX = "AMDX"  # Accumulation → Manipulation → Distribution → Continuation
    XAMD = "XAMD"  # Continuation → Accumulation → Manipulation → Distribution
    UNKNOWN = "UNKNOWN"

class Quarter(Enum):
    Q1 = "Q1"
    Q2 = "Q2"
    Q3 = "Q3"
    Q4 = "Q4"

class Phase(Enum):
    ACCUMULATION = "ACCUMULATION"
    MANIPULATION = "MANIPULATION"
    DISTRIBUTION = "DISTRIBUTION"
    CONTINUATION = "CONTINUATION"
    REVERSAL = "REVERSAL"
    TRANSITION = "TRANSITION"

class Bias(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

class EntryWindowStatus(Enum):
    CLOSED = "CLOSED"
    OPENING = "OPENING"
    OPEN = "OPEN"
    OPTIMAL = "OPTIMAL"
    CLOSING = "CLOSING"

class Session(Enum):
    ASIA = "ASIA"      # 6:00 PM - 12:00 AM EST
    LONDON = "LONDON"  # 12:00 AM - 6:00 AM EST
    NY_AM = "NY_AM"    # 7:30 AM - 1:30 PM EST
    NY_PM = "NY_PM"    # 1:30 PM - 7:30 PM EST

@dataclass
class TimeWindow:
    """Defines a time window for analysis"""
    start_hour: int
    start_minute: int
    end_hour: int
    end_minute: int
    
    def contains(self, dt: datetime) -> bool:
        """Check if datetime falls within this window"""
        time_minutes = dt.hour * 60 + dt.minute
        start_minutes = self.start_hour * 60 + self.start_minute
        end_minutes = self.end_hour * 60 + self.end_minute
        
        if start_minutes <= end_minutes:
            return start_minutes <= time_minutes < end_minutes
        else:  # Window crosses midnight
            return time_minutes >= start_minutes or time_minutes < end_minutes

@dataclass
class MarketStructure:
    """Market structure analysis"""
    displacement_detected: bool
    fvg_present: bool
    fvg_type: Optional[str]  # 'BSG', 'iFVG', 'Regular'
    one_sided: bool
    liquidity_sweep_detected: bool
    price_zone: str  # 'PREMIUM', 'FAIR_VALUE', 'DISCOUNT'
    
@dataclass
class QuarterlyAnalysis:
    """Complete quarterly analysis result"""
    cycle_type: CycleType
    current_quarter: Quarter
    quarter_phase: Phase
    confidence_score: float
    bias: Bias
    entry_window_status: EntryWindowStatus
    market_structure: MarketStructure
    supporting_evidence: Dict
    recommendation: str

# =====================================================
# Time Window Definitions
# =====================================================

# Daily cycle quarters (6-hour windows)
DAILY_Q1 = TimeWindow(0, 0, 6, 0)    # 12 AM - 6 AM (Asia + London)
DAILY_Q2 = TimeWindow(6, 0, 12, 0)   # 6 AM - 12 PM (NY AM)
DAILY_Q3 = TimeWindow(12, 0, 18, 0)  # 12 PM - 6 PM (NY PM)
DAILY_Q4 = TimeWindow(18, 0, 24, 0)  # 6 PM - 12 AM (After hours)

# Session cycle quarters (90-minute windows)
LONDON_QUARTERS = {
    Quarter.Q1: TimeWindow(0, 0, 1, 30),
    Quarter.Q2: TimeWindow(1, 30, 3, 0),
    Quarter.Q3: TimeWindow(3, 0, 4, 30),
    Quarter.Q4: TimeWindow(4, 30, 6, 0)
}

NY_AM_QUARTERS = {
    Quarter.Q1: TimeWindow(7, 30, 9, 0),
    Quarter.Q2: TimeWindow(9, 0, 10, 30),
    Quarter.Q3: TimeWindow(10, 30, 12, 0),
    Quarter.Q4: TimeWindow(12, 0, 13, 30)
}

NY_PM_QUARTERS = {
    Quarter.Q1: TimeWindow(13, 30, 15, 0),
    Quarter.Q2: TimeWindow(15, 0, 16, 30),
    Quarter.Q3: TimeWindow(16, 30, 18, 0),
    Quarter.Q4: TimeWindow(18, 0, 19, 30)
}

# Session definitions
ASIA_SESSION = TimeWindow(18, 0, 24, 0)   # 6 PM - 12 AM
LONDON_SESSION = TimeWindow(0, 0, 6, 0)   # 12 AM - 6 AM
NY_AM_SESSION = TimeWindow(7, 30, 13, 30) # 7:30 AM - 1:30 PM
NY_PM_SESSION = TimeWindow(13, 30, 19, 30) # 1:30 PM - 7:30 PM

# =====================================================
# Database Connection Manager
# =====================================================

class DatabaseManager:
    """Manages TimescaleDB connections"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.conn = None
        
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.config)
            logger.info("Connected to TimescaleDB")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
            
    def get_cursor(self):
        """Get cursor with RealDictCursor"""
        if not self.conn or self.conn.closed:
            self.connect()
        return self.conn.cursor(cursor_factory=RealDictCursor)
        
    def close(self):
        """Close connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")

# =====================================================
# Redis Connection Manager
# =====================================================

class RedisManager:
    """Manages Redis connections for real-time data"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.client = None
        
    def connect(self):
        """Establish Redis connection"""
        try:
            self.client = redis.Redis(**self.config, decode_responses=True)
            self.client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
            
    def get_latest_data(self, key: str) -> Optional[Dict]:
        """Get latest data from Redis"""
        try:
            data = self.client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None

# =====================================================
# Data Fetcher - Gets data from Redis/TimescaleDB
# =====================================================

class DataFetcher:
    """Fetches absorption, stops, icebergs, MBO data from databases"""
    
    def __init__(self, db_manager: DatabaseManager, redis_manager: RedisManager):
        self.db = db_manager
        self.redis = redis_manager
        
    def get_absorption_data(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Fetch absorption events within time range"""
        cursor = self.db.get_cursor()
        try:
            cursor.execute("""
                SELECT * FROM absorption_events
                WHERE timestamp BETWEEN %s AND %s
                ORDER BY timestamp ASC
            """, (start_time, end_time))
            return cursor.fetchall()
        finally:
            cursor.close()
            
    def get_stops_icebergs_data(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Fetch stops and iceberg events within time range"""
        cursor = self.db.get_cursor()
        try:
            cursor.execute("""
                SELECT * FROM stops_icebergs_events
                WHERE timestamp BETWEEN %s AND %s
                ORDER BY timestamp ASC
            """, (start_time, end_time))
            return cursor.fetchall()
        finally:
            cursor.close()
            
    def get_mbo_summary(self, start_time: datetime, end_time: datetime) -> Dict:
        """Get MBO data summary (aggressive orders, directional bias)"""
        cursor = self.db.get_cursor()
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(CASE WHEN side = 'BUY' THEN 1 ELSE 0 END) as buy_orders,
                    SUM(CASE WHEN side = 'SELL' THEN 1 ELSE 0 END) as sell_orders,
                    AVG(CASE WHEN is_aggressive THEN 1.0 ELSE 0.0 END) as aggressive_pct,
                    SUM(CASE WHEN side = 'BUY' AND is_aggressive THEN size ELSE 0 END) as aggressive_buy_volume,
                    SUM(CASE WHEN side = 'SELL' AND is_aggressive THEN size ELSE 0 END) as aggressive_sell_volume
                FROM mbo_events
                WHERE timestamp BETWEEN %s AND %s
            """, (start_time, end_time))
            result = cursor.fetchone()
            
            # Calculate directional bias
            if result['total_orders'] > 0:
                buy_pct = (result['buy_orders'] / result['total_orders']) * 100
                sell_pct = (result['sell_orders'] / result['total_orders']) * 100
                
                # Aggressive volume bias
                total_aggressive = result['aggressive_buy_volume'] + result['aggressive_sell_volume']
                if total_aggressive > 0:
                    aggressive_buy_pct = (result['aggressive_buy_volume'] / total_aggressive) * 100
                else:
                    aggressive_buy_pct = 50.0
                    
                result['buy_pct'] = buy_pct
                result['sell_pct'] = sell_pct
                result['aggressive_buy_pct'] = aggressive_buy_pct
                result['aggressive_sell_pct'] = 100 - aggressive_buy_pct
            
            return dict(result) if result else {}
        finally:
            cursor.close()
            
    def get_latest_price(self) -> Optional[float]:
        """Get latest price from Redis"""
        data = self.redis.get_latest_data('latest_price')
        return data.get('price') if data else None

# =====================================================
# Continuation in next file due to length...
# =====================================================
