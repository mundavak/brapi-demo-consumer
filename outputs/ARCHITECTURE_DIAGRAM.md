# Quarterly Theory System Architecture

## Complete Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                   BOOKMAP LAYER                                      │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐       │
│  │  Absorption   │  │ Stops/Icebergs│  │  MBO Orders   │  │ Market Price  │       │
│  │   Consumer    │  │   Consumer    │  │   Consumer    │  │    Feed       │       │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘       │
│          │                  │                  │                  │                 │
└──────────┼──────────────────┼──────────────────┼──────────────────┼─────────────────┘
           │                  │                  │                  │
           │                  │                  │                  │
           ▼                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                              STORAGE LAYER (Redis + TimescaleDB)                     │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │  REDIS (Hot Storage)                                                          │  │
│  │  ├─ latest_price → {"price": 18450.5, "timestamp": "..."}                    │  │
│  │  ├─ latest_absorption → {"side": "BID", "significance": 0.87, ...}           │  │
│  │  └─ session_<id> → Real-time session data                                    │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │  TIMESCALEDB (Cold Storage - Existing Tables)                                │  │
│  │  ├─ absorption_events (timestamp, side, significance, volume, ...)           │  │
│  │  ├─ stops_icebergs_events (timestamp, event_type, stop_type, price, ...)    │  │
│  │  └─ mbo_events (timestamp, side, size, price, is_aggressive, ...)           │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │  TIMESCALEDB (Quarterly Theory Tables - NEW)                                 │  │
│  │  ├─ quarterly_cycles (cycle_type, current_quarter, phase, confidence, ...)  │  │
│  │  ├─ phase_transitions (from/to quarter/phase, trigger, supporting_data, ...)│  │
│  │  ├─ htf_bias (timeframe, bias, key_levels, market_structure, ...)           │  │
│  │  └─ session_bias (session, bias, entry_window_status, fake/real flags, ...) │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
           │                  │                  │                  │
           │                  │                  │                  │
           ▼                  ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                         ANALYSIS LAYER (Python Backend Service)                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │  DATA FETCHER                                                                 │  │
│  │  ├─ get_absorption_data(start_time, end_time) → List[Dict]                  │  │
│  │  ├─ get_stops_icebergs_data(start_time, end_time) → List[Dict]              │  │
│  │  ├─ get_mbo_summary(start_time, end_time) → Dict (aggregated metrics)       │  │
│  │  └─ get_latest_price() → float                                               │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│           │                                                                          │
│           ▼                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │  SESSION ANALYZER                                                             │  │
│  │  ├─ Asia Session (18:00-00:00): Accumulation vs Expansion                   │  │
│  │  ├─ London Session (00:00-06:00): Confirmation                               │  │
│  │  └─ Pre-NY Session (07:30-09:30): Validation                                 │  │
│  │                                                                                │  │
│  │  Indicators:                                                                  │  │
│  │  • Absorption balance: 40-60% = Accumulation, <40/>60 = Expansion           │  │
│  │  • Stops bidirectional: Both sides = Accumulation, One side = Expansion     │  │
│  │  • Aggressive orders: <70% = Accumulation, >70% = Expansion                 │  │
│  │  • Displacement: Aggressive >70% + Directional = Expansion                  │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│           │                                                                          │
│           ▼                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │  CYCLE DETERMINATOR (Pre-9:45 AM)                                            │  │
│  │                                                                                │  │
│  │  Combine Session Results:                                                     │  │
│  │  ┌──────────────────────────────────────────────────────────────┐            │  │
│  │  │ IF Asia + London = ACCUMULATION                              │            │  │
│  │  │    → AMDX Profile (87% confidence)                           │            │  │
│  │  │    → Q1 Accumulation starting                                │            │  │
│  │  │    → Q2 will be Manipulation (CLOSED for entries)           │            │  │
│  │  │    → Q3 will be Distribution (OPTIMAL entry window)          │            │  │
│  │  └──────────────────────────────────────────────────────────────┘            │  │
│  │  ┌──────────────────────────────────────────────────────────────┐            │  │
│  │  │ IF Asia + London = EXPANSION                                 │            │  │
│  │  │    → XAMD Profile (82% confidence)                           │            │  │
│  │  │    → Q1 Continuation from previous day                       │            │  │
│  │  │    → Q2 will be Accumulation (consolidation)                 │            │  │
│  │  │    → Q3 will be Manipulation (CLOSED for entries)            │            │  │
│  │  │    → Q4 will be Distribution (OPTIMAL entry window)          │            │  │
│  │  └──────────────────────────────────────────────────────────────┘            │  │
│  │                                                                                │  │
│  │  Output: Write to quarterly_cycles table                                     │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│           │                                                                          │
│           ▼                                                                          │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │  PHASE TRACKER (Real-Time, Every 60 Seconds)                                 │  │
│  │                                                                                │  │
│  │  1. Determine Current Quarter:                                               │  │
│  │     • Q1: 00:00-06:00  • Q2: 06:00-12:00                                     │  │
│  │     • Q3: 12:00-18:00  • Q4: 18:00-00:00                                     │  │
│  │                                                                                │  │
│  │  2. Identify Phase Within Quarter (Last 5 Minutes Analysis):                │  │
│  │     ┌────────────────────────────────────────────────────────┐              │  │
│  │     │ ACCUMULATION: Balanced absorption, bidirectional stops │              │  │
│  │     │ MANIPULATION: Liquidity sweeps, stops + reversal       │              │  │
│  │     │ DISTRIBUTION: Displacement + directional flow          │              │  │
│  │     │ CONTINUATION: Trend extension, moderate activity       │              │  │
│  │     └────────────────────────────────────────────────────────┘              │  │
│  │                                                                                │  │
│  │  3. Detect Phase Transitions:                                                │  │
│  │     • Time window end (Q1→Q2 at 06:00)                                       │  │
│  │     • Displacement detected (Accumulation→Distribution)                      │  │
│  │     • Liquidity sweep (Accumulation→Manipulation)                            │  │
│  │     → Write to phase_transitions table                                       │  │
│  │                                                                                │  │
│  │  4. Calculate Entry Window Status:                                           │  │
│  │     ┌────────────────────────────────────────────────────────┐              │  │
│  │     │ AMDX: Q3 Distribution = OPTIMAL, Q4 = OPEN             │              │  │
│  │     │       Q2 Manipulation = CLOSED                          │              │  │
│  │     │ XAMD: Q4 Distribution = OPTIMAL, Q3 Manipulation = CLOSED │           │  │
│  │     └────────────────────────────────────────────────────────┘              │  │
│  │                                                                                │  │
│  │  5. Detect Fake vs Real Moves:                                               │  │
│  │     ┌────────────────────────────────────────────────────────┐              │  │
│  │     │ FAKE: Q2 Manipulation + Liquidity Sweep + Reversal    │              │  │
│  │     │       → Set fake_move_detected = TRUE                  │              │  │
│  │     │ REAL: Q3 Distribution + Displacement + Follow-through  │              │  │
│  │     │       → Set real_move_confirmed = TRUE                 │              │  │
│  │     └────────────────────────────────────────────────────────┘              │  │
│  │                                                                                │  │
│  │  Output: Write to session_bias table (every 60 seconds)                     │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
           │                                                    │
           │                                                    │
           ▼                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                           PRESENTATION LAYER (Dashboard UI)                          │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │  QUARTERLY THEORY PANEL (React Component)                                    │  │
│  │  ┌────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  CYCLE OVERVIEW                                                         │ │  │
│  │  │  Daily Cycle: AMDX ✓ (87% confidence)                                  │ │  │
│  │  │  Current Quarter: Q2 (Manipulation)                                    │ │  │
│  │  │  Session Cycle: AMDX - Q2                                              │ │  │
│  │  └────────────────────────────────────────────────────────────────────────┘ │  │
│  │  ┌────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  PHASE STATUS                                                           │ │  │
│  │  │  Phase: MANIPULATION                                                    │ │  │
│  │  │  Status: ⚠️ Liquidity sweep in progress - DO NOT CHASE                 │ │  │
│  │  │  Time to Q3: 45 minutes                                                │ │  │
│  │  │  Transition Trigger: LIQUIDITY_SWEEP detected                          │ │  │
│  │  └────────────────────────────────────────────────────────────────────────┘ │  │
│  │  ┌────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  BIAS & ENTRY WINDOW                                                    │ │  │
│  │  │  Daily Bias: BULLISH (85%)                                             │ │  │
│  │  │  Session Bias: BULLISH (78%)                                           │ │  │
│  │  │  Entry Window: CLOSED ⛔                                                │ │  │
│  │  │  Recommendation: Wait for Q2 manipulation to complete.                 │ │  │
│  │  │                  Real move expected in Q3 after 12:00 PM.              │ │  │
│  │  └────────────────────────────────────────────────────────────────────────┘ │  │
│  │  ┌────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  MARKET STRUCTURE                                                       │ │  │
│  │  │  Displacement: Not Present ✗                                           │ │  │
│  │  │  FVG Present: No                                                        │ │  │
│  │  │  Price Zone: DISCOUNT (Good for buys when entry window opens)         │ │  │
│  │  │  Action Type: Two-Sided (Manipulation phase)                          │ │  │
│  │  │  Liquidity Sweep: ⚠️ DETECTED at 18,450 (Asia high)                   │ │  │
│  │  └────────────────────────────────────────────────────────────────────────┘ │  │
│  │  ┌────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  KEY LEVELS                                                             │ │  │
│  │  │  True Open: 18,435                                                     │ │  │
│  │  │  Fair Value: 18,445 (50% of impulse)                                  │ │  │
│  │  │  Premium Zone: 18,445 to 18,480                                       │ │  │
│  │  │  Discount Zone: 18,410 to 18,445 ← CURRENT                           │ │  │
│  │  │  Previous Q High/Low: 18,480 / 18,410                                 │ │  │
│  │  └────────────────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                      │
│  ┌──────────────────────────────────────────────────────────────────────────────┐  │
│  │  SIGNAL ENHANCEMENT (Pattern Library + Quarterly Context)                    │  │
│  │  ┌────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Absorption Event Detected: BID-heavy (0.87 significance)             │ │  │
│  │  │  Pattern Matched: Retracement Entry (90% base confidence)             │ │  │
│  │  │  Quarterly Context: Q2 Manipulation phase, CLOSED entry window        │ │  │
│  │  │  ⚠️ DOWNGRADE TO FAKE MOVE (-30 points)                               │ │  │
│  │  │  Final Confidence: 60% (Likely fake absorption - trap setup)          │ │  │
│  │  │  Signal: "DO NOT ENTER - Absorption in manipulation phase"            │ │  │
│  │  └────────────────────────────────────────────────────────────────────────┘ │  │
│  │                                                                                │  │
│  │  [30 minutes later - Q3 Distribution begins]                                 │  │
│  │                                                                                │  │
│  │  ┌────────────────────────────────────────────────────────────────────────┐ │  │
│  │  │  Absorption Event Detected: ASK-heavy (0.91 significance)             │ │  │
│  │  │  Displacement Detected: +65 ticks in 4 minutes                         │ │  │
│  │  │  Pattern Matched: Retracement Entry (90% base confidence)             │ │  │
│  │  │  Quarterly Context: Q3 Distribution phase, OPTIMAL entry window       │ │  │
│  │  │  ✅ UPGRADE TO REAL MOVE (+45 points)                                 │ │  │
│  │  │  Final Confidence: 100% (Real move confirmed)                         │ │  │
│  │  │  Signal: "✅ REAL MOVE - Enter on pullback to 18,460"                 │ │  │
│  │  │  Entry: 18,460 | Stop: 18,448 | Target: 18,520 | R:R = 1:5           │ │  │
│  │  └────────────────────────────────────────────────────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Time-Based Quarter Progression (AMDX Day Example)

```
TIME      QUARTER   PHASE          CHARACTERISTICS                    ENTRY WINDOW
────────  ────────  ─────────────  ───────────────────────────────────────────────
00:00 AM    Q1      ACCUMULATION   Asia + London: Two-sided flow,        CLOSED
- 06:00 AM                         balanced absorption, range building   (Building)
                                   ✓ Bidirectional stops
                                   ✓ Moderate aggressive orders (<70%)

06:00 AM    Q2      MANIPULATION   NY Open: Liquidity sweeps,            CLOSED
- 12:00 PM                         fake moves, stop runs                 (Danger Zone)
                                   ⚠️ Stops triggered with reversals
                                   ⚠️ Absorption appears/disappears
                                   ⚠️ fake_move_detected = TRUE

12:00 PM    Q3      DISTRIBUTION   NY PM: Real move begins,              OPTIMAL ✅
- 06:00 PM                         directional flow confirmed            (Best Entry)
                                   ✅ Displacement detected
                                   ✅ FVG creation
                                   ✅ Directional absorption (>60%)
                                   ✅ Aggressive orders >70%
                                   ✅ real_move_confirmed = TRUE

06:00 PM    Q4      CONTINUATION   After hours: Trend extension          OPEN
- 12:00 AM                         or consolidation                      (Acceptable)
                                   ○ Sustained directional bias
                                   ○ Moderate volume
```

## Service Timing Diagram

```
TIME          SERVICE ACTION                              DATABASE WRITES
────────────  ──────────────────────────────────────────  ───────────────────────
06:00 PM      Service starts monitoring                   None
  (Day -1)

12:00 AM      Asia session analysis begins                None (collecting data)
  (Day 0)

06:00 AM      London session analysis begins              None (collecting data)

07:30 AM      Service activates real-time tracking        session_bias (every 60s)
              Pre-NY session analysis begins

09:00 AM      Pre-market determination triggered          None (processing)
              - Fetch Asia session data
              - Fetch London session data
              - Fetch Pre-NY session data

09:15 AM      Analysis complete                           quarterly_cycles ✓
              Determination: AMDX (87% confidence)        (Daily cycle written)

09:30 AM      NY Market opens                             session_bias (every 60s)
              Real-time tracking continues                phase_transitions
                                                          (on Q1→Q2 transition)

10:30 AM      Fake move detected in Q2                    session_bias ✓
              fake_move_detected = TRUE                   (fake_move flag set)

12:00 PM      Q2→Q3 transition detected                   phase_transitions ✓
              entry_window_status: CLOSED → OPTIMAL       (Q2→Q3 logged)

12:15 PM      Real move confirmed in Q3                   session_bias ✓
              real_move_confirmed = TRUE                  (real_move flag set)
              Displacement detected

06:00 PM      Q3→Q4 transition                            phase_transitions ✓
              entry_window_status: OPTIMAL → OPEN         (Q3→Q4 logged)

08:00 PM      Service enters sleep mode                   None
              (Outside active trading hours)
```

## Pattern Library Integration Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  ABSORPTION EVENT ARRIVES FROM CONSUMER                          │
│  {side: "BID", significance: 0.87, price: 18445, ...}          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  PATTERN LIBRARY MATCHING                                        │
│  - Check indicators from pattern_library_fake_vs_real.json      │
│  - Base confidence: 90% (Retracement Entry pattern)             │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  QUERY QUARTERLY CONTEXT                                         │
│  SELECT current_quarter, quarter_phase, entry_window_status,    │
│         fake_move_detected, real_move_confirmed                 │
│  FROM session_bias                                               │
│  WHERE timestamp = (SELECT MAX(timestamp) FROM session_bias)    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  CONFIDENCE ADJUSTMENT                                           │
│  IF current_quarter = 'Q2' AND quarter_phase = 'MANIPULATION':  │
│     confidence -= 30  (Fake move phase)                         │
│  IF entry_window_status = 'CLOSED':                             │
│     confidence -= 20  (Wrong timing)                            │
│  IF fake_move_detected = TRUE:                                  │
│     confidence -= 40  (Active manipulation)                     │
│                                                                  │
│  RESULT: 90 - 30 - 20 - 40 = 0%                                │
│  → REJECT SIGNAL                                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│  DISPLAY TO TRADER                                               │
│  ⚠️ SIGNAL REJECTED                                             │
│  Reason: "Absorption detected during Q2 Manipulation phase.     │
│          This is likely a fake move (trap setup). DO NOT ENTER."│
└─────────────────────────────────────────────────────────────────┘
```

## Success Flow: Real Move Entry

```
11:45 AM: Manipulation completes
  ↓ (Wait 15 minutes)
12:00 PM: Q3 Distribution begins
  ↓ (Service detects quarter transition)
12:05 PM: Displacement detected (+65 ticks in 4 min)
  ↓ (Service sets real_move_confirmed = TRUE)
12:10 PM: Price pulls back to 18,460 (sweep rejection level)
  ↓ (Absorption event: ASK-heavy 0.91)
12:11 PM: Pattern Library matches "Retracement Entry" (90% base)
  ↓ (Query quarterly context)
12:11 PM: Context: Q3 Distribution, OPTIMAL entry window, real_move_confirmed=TRUE
  ↓ (Confidence adjustment: 90 + 20 + 15 + 10 = 100%)
12:11 PM: ✅ SIGNAL APPROVED - Display to trader
  ↓ (Trader sees entry recommendation)
12:12 PM: Trader enters at 18,460
  ↓ (Stop: 18,448, Target: 18,520)
12:45 PM: Target reached at 18,520 (+60 ticks profit, R:R 1:5)
```

---

**Key Takeaway**: The Quarterly Theory service provides TIME-BASED CONTEXT that transforms pattern recognition from "What is happening?" to "What is happening AND when is it happening?" - enabling traders to distinguish fake moves (Q2 Manipulation) from real moves (Q3 Distribution) with high confidence.
