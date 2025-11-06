# ICT (Inner Circle Trader) Trading Methodology Guide

## Core Concepts

### 1. Market Maker Model (MMXM)

The MMXM framework helps visualize:
- Price retracements and expansions
- Market curve positioning
- Higher timeframe bias confirmation
- Trade entry and exit points

Key Applications:
```python
def analyze_mmxm(price_data, timeframe):
    # Identify curve position
    curve_side = determine_curve_side(price_data)
    
    # Analyze retracements
    retracement_levels = find_retracement_levels(price_data)
    
    # Project expansions
    expansion_targets = calculate_expansions(price_data)
    
    return {
        'curve_side': curve_side,
        'retracements': retracement_levels,
        'expansions': expansion_targets
    }
```

### 2. Fair Value Gaps (FVG)

Types of FVGs:
1. Break Structure Gaps (BSG)
   - Life blood of trends
   - Must follow consistency rule
   - Used for continuation trades

2. Inverted FVGs (iFVG)
   - Form at two-sided gaps
   - Follow sweeps of liquidity
   - High probability reversal zones

Implementation:
```python
def detect_fvg(candles):
    for i in range(1, len(candles)-1):
        if is_bullish_fvg(candles[i-1:i+2]):
            return {
                'type': 'bullish',
                'level': calculate_fvg_level(candles[i-1:i+2])
            }
        elif is_bearish_fvg(candles[i-1:i+2]):
            return {
                'type': 'bearish',
                'level': calculate_fvg_level(candles[i-1:i+2])
            }
    return None
```

### 3. Market Structure

Key Components:
1. Displacement vs Manipulation
   - Displacement = Continuation
   - Manipulation = Reversal
   - Break Structure Points

2. Order Blocks
   - Form before expansive moves
   - Used for trade entry
   - Risk management reference

Analysis Framework:
```python
def analyze_structure(price_data):
    # Find structure points
    highs = find_structure_highs(price_data)
    lows = find_structure_lows(price_data)
    
    # Classify moves
    moves = classify_moves(price_data)
    
    # Identify order blocks
    blocks = find_order_blocks(price_data)
    
    return {
        'structure_points': {'highs': highs, 'lows': lows},
        'move_classification': moves,
        'order_blocks': blocks
    }
```

### 4. Time-Based Analysis

Key Sessions:
1. Asian Session (2300-0200)
   - Accumulation phase
   - Range development
   - Liquidity building

2. London Session (0200-0500)
   - Institutional activity
   - Major moves begin
   - Focus 0300-0400

3. NY Session
   - AM: 0830-1100 (key moves)
   - PM: 1300-1600 (follow-through)

Implementation:
```python
def analyze_session(data, session):
    if session == "asia":
        return analyze_asia_session(data, "2300", "0200")
    elif session == "london":
        return analyze_london_session(data, "0200", "0500")
    elif session == "ny_am":
        return analyze_ny_session(data, "0830", "1100")
    elif session == "ny_pm":
        return analyze_ny_session(data, "1300", "1600")
```

### 5. Weekly Cycles

Day Patterns:
1. Monday
   - Accumulation if Friday accumulated
   - Expansion if Friday distributed

2. Tuesday
   - Manipulation if Monday expanded
   - Accumulation if Monday contracted

3. Wednesday
   - Manipulation/Distribution phase
   - Key reversal day

4. Thursday
   - Distribution continues
   - Reversal possible

5. Friday
   - AMDX or XAMD patterns
   - Based on previous cycle

Analysis:
```python
def analyze_weekly_cycle(week_data):
    monday = analyze_monday(week_data['monday'])
    tuesday = analyze_tuesday(week_data['tuesday'], monday)
    wednesday = analyze_wednesday(week_data['wednesday'])
    thursday = analyze_thursday(week_data['thursday'])
    friday = analyze_friday(week_data['friday'])
    
    return {
        'cycle_type': determine_cycle_type(monday, friday),
        'key_levels': find_cycle_levels(week_data),
        'daily_patterns': {
            'monday': monday,
            'tuesday': tuesday,
            'wednesday': wednesday,
            'thursday': thursday,
            'friday': friday
        }
    }
```

## Trade Implementation

### 1. Entry Strategies

1. Order Block Entries:
```python
def find_entry_opportunity(price, blocks, fvgs):
    valid_blocks = filter_valid_blocks(blocks)
    aligned_fvgs = find_aligned_fvgs(fvgs, valid_blocks)
    
    return analyze_entry_points(price, valid_blocks, aligned_fvgs)
```

2. FVG Based Entries:
```python
def fvg_entry_strategy(price, fvgs, structure):
    # Find high probability FVGs
    quality_fvgs = filter_quality_fvgs(fvgs)
    
    # Check structure alignment
    aligned = check_structure_alignment(quality_fvgs, structure)
    
    # Generate entry points
    return generate_entry_points(aligned)
```

### 2. Risk Management

1. Position Sizing:
```python
def calculate_position_size(account_equity, risk_per_trade, 
                          stop_distance):
    # Base position sizing on risk
    max_risk = account_equity * (risk_per_trade / 100)
    
    # Calculate contracts/lots
    position_size = max_risk / stop_distance
    
    return adjust_for_market_conditions(position_size)
```

2. Stop Placement:
```python
def determine_stop_level(entry, blocks, structure):
    # Find nearest structure point
    structure_stop = find_structure_stop(entry, structure)
    
    # Check order blocks
    block_stop = find_block_stop(entry, blocks)
    
    # Use most conservative
    return max(structure_stop, block_stop)
```

### 3. Trade Management

1. Target Setting:
```python
def set_targets(entry, direction, structure):
    targets = []
    
    # First target at nearest structure
    targets.append(find_first_structure(entry, direction))
    
    # Second at FVG if present
    fvg_target = find_fvg_target(entry, direction)
    if fvg_target:
        targets.append(fvg_target)
    
    # Final at major structure
    targets.append(find_major_structure(entry, direction))
    
    return targets
```

2. Trail Management:
```python
def manage_trail(position, price, blocks):
    # Trail behind new order blocks
    new_blocks = find_new_blocks(price, position['direction'])
    
    if new_blocks:
        return update_trail(position, new_blocks)
    
    # Hold original trail
    return position['current_trail']
```

## Best Practices

1. Analysis Process:
   - Start with weekly cycle
   - Identify key sessions
   - Find structure points
   - Locate order blocks
   - Confirm with FVGs

2. Trade Execution:
   - Wait for session alignment
   - Confirm structure
   - Use multiple timeframes
   - Monitor order flow

3. Risk Management:
   - Fixed % risk per trade
   - Multiple targets
   - Trail with structure
   - Cut losses early

4. Performance Tracking:
   - Log all setups
   - Track success by pattern
   - Monitor risk metrics
   - Review weekly cycles

## Additional Resources

1. Reference Materials:
   - ICT Mentorship PDFs
   - Market Structure Guide
   - Order Flow Analysis
   - Time Analysis Framework

2. Tools:
   - Structure Analysis Tools
   - FVG Detection Scripts
   - Session Analysis Tools
   - Risk Calculator
