# ICT KillZone Analysis Framework

## Overview

The ICT (Inner Circle Trader) KillZone analysis framework identifies high-probability trading opportunities during specific time windows when institutional activity is most prevalent.

## Key Components

### 1. Time Windows

- **London KillZone**
  - Time: 2:00-5:00 AM EST
  - Focus: European institutional activity
  - Key patterns: Accumulation/Distribution

- **NY KillZone**
  - Time: 8:30-11:00 AM EST  
  - Focus: US institutional activity
  - Key patterns: Stop runs, reversals

### 2. Market Classification

- **Opening Zones**
  - PREMIUM: Above equilibrium - fade upward moves
  - DISCOUNT: Below equilibrium - fade downward moves
  - EQUILIBRIUM: Near midpoint - wait for direction

- **Day Types**
  - Trending: Strong directional bias
  - Range-Bound: Oscillating between levels
  - Rotation: Shifting between zones

### 3. Order Flow Analysis

- **Institutional Patterns**
  - Absorption at levels
  - Volume clusters
  - Stop hunts
  - Distribution/accumulation

- **Flow Metrics**
  - Volume delta
  - Large trade analysis
  - Price level changes
  - Bid/ask imbalances

### 4. Success Metrics

- **Zone Performance**
  - Premium: 87.5% success rate
  - Equilibrium: 50.0% success rate
  - Discount: 71.4% success rate

- **Risk/Reward**
  - Minimum: 10:1
  - Average: 7.88:1
  - Median: 0.61:1

## Trading Strategy

### 1. Zone Analysis

1. Identify previous day's range:
   - High
   - Low
   - Equilibrium (midpoint)

2. Classify opening zone:
   ```python
   def classify_opening_zone(open_price, prev_eq, prev_high, prev_low):
       buffer = (prev_high - prev_low) * 0.1
       
       if open_price > prev_eq + buffer:
           return "PREMIUM"
       elif open_price < prev_eq - buffer:
           return "DISCOUNT"
       else:
           return "EQUILIBRIUM"
   ```

3. Monitor zone interactions:
   - Price acceptance/rejection
   - Volume patterns
   - Order flow characteristics

### 2. Pattern Recognition

1. Judas Swing Detection:
   ```python
   def detect_judas_swing(initial_move, following_move):
       if initial_move['size'] * 1.5 < following_move['size']:
           if initial_move['direction'] != following_move['direction']:
               return True
       return False
   ```

2. Institutional Activity:
   ```python
   def analyze_institutional_activity(volume, trades, orders):
       large_trades = filter_large_trades(trades)
       absorption = detect_absorption(orders)
       clusters = find_volume_clusters(volume)
       
       return assess_activity(large_trades, absorption, clusters)
   ```

### 3. Trade Execution

1. Entry Rules:
   - Wait for zone confirmation
   - Look for institutional footprint
   - Monitor order flow alignment
   - Verify risk/reward ratio

2. Exit Rules:
   - Take profits at opposite zone
   - Trail stops behind swings
   - Monitor reversal patterns
   - Watch institutional flow

## Implementation Guide

### 1. Data Requirements

- Market data with millisecond precision
- Order book depth information
- Trade-by-trade analysis
- Volume profile data

### 2. Analysis Components

```python
class ICTAnalyzer:
    def __init__(self):
        self.zones = {"PREMIUM": [], "DISCOUNT": [], "EQUILIBRIUM": []}
        self.patterns = []
        self.trades = []
    
    def analyze_session(self, data):
        # Analyze previous day
        prev_range = self.get_prev_day_range(data)
        
        # Classify opening zone
        open_zone = self.classify_opening_zone(data)
        
        # Monitor killzones
        london_activity = self.analyze_london_session(data)
        ny_activity = self.analyze_ny_session(data)
        
        # Track institutional activity
        inst_patterns = self.detect_institutional_patterns(data)
        
        return self.generate_signals(prev_range, open_zone, 
                                  london_activity, ny_activity,
                                  inst_patterns)
```

### 3. Risk Management

1. Position Sizing:
   ```python
   def calculate_position_size(account_size, risk_per_trade, 
                             stop_distance, success_rate):
       # Base size on risk parameters
       max_risk = account_size * (risk_per_trade / 100)
       
       # Adjust for success probability
       adjusted_size = max_risk * success_rate
       
       # Calculate contracts based on stop
       return adjusted_size / stop_distance
   ```

2. Stop Placement:
   - Outside institutional levels
   - Beyond swing points
   - Behind key volume nodes
   - Protected from hunts

### 4. Performance Tracking

1. Metrics to Monitor:
   - Success rate by zone
   - Average R/R ratio
   - Maximum drawdown
   - Win/loss streaks

2. Analysis Requirements:
   - Track all setups
   - Log institutional activity
   - Record zone performance
   - Monitor pattern success

## Best Practices

1. **Analysis**
   - Always start with previous day's range
   - Wait for clear zone classification
   - Look for multiple confirmations
   - Monitor institutional activity

2. **Trading**
   - Trade with zone alignment
   - Wait for order flow confirmation
   - Monitor post-entry activity
   - Follow institutional flow

3. **Risk Management**
   - Size positions appropriately
   - Place stops strategically
   - Take profits at targets
   - Cut losses quickly

## Resources

1. Key Files:
   - Trading Knowledge Base (JSON)
   - ICT Analysis Tools (Python)
   - Performance Metrics (CSV)
   - Pattern Database (SQL)

2. Documentation:
   - Framework Guide (PDF)
   - Implementation Notes (MD)
   - Best Practices (PDF)
   - Case Studies (HTML)
