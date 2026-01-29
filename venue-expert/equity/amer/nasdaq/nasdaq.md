# Nasdaq Exchange Mechanics

Nasdaq-specific market microstructure. Assumes familiarity with US equity concepts from `equity_amer.md`.

## Overview and Role

### Nasdaq as Operator

Nasdaq operates multiple equity venues:

| Venue | Fee Model | Characteristics |
|-------|-----------|-----------------|
| Nasdaq (XNAS) | Maker-taker | Primary venue, highest volume |
| BX (XBOS) | Inverted | Taker-maker, attracts different flow |
| PSX (XPHL) | Maker-taker | Price/size priority variant |

### Listing vs Trading

Nasdaq is both:
- **Listing venue** for Nasdaq-listed securities (Tape C)
- **Trading venue** for all NMS stocks

Nasdaq-listed securities trade on all NMS exchanges. Consolidated data via UTP SIP (Tape C).

## Order Book Mechanics

### Price-Time Priority

Default matching at Nasdaq:
1. Price priority - better price always wins
2. Time priority - FIFO at same price level

### Order Types

**Basic types:**

| Type | Behavior |
|------|----------|
| Market | Immediate execution at best available |
| Limit | Execute at limit or better |
| Pegged | Track reference (midpoint, primary, market) |
| Reserve | Display partial size, hidden remainder |

**Auction-specific types:**

| Type | Participation |
|------|---------------|
| MOO/MOC | Market-on-Open/Close |
| LOO/LOC | Limit-on-Open/Close |
| IO | Imbalance-Only (offset imbalance) |
| OPG | Opening order |

**Extended order types:**

| Type | Behavior |
|------|----------|
| Primary Peg | Track same-side BBO (bid for buy, ask for sell) |
| Market Peg | Track opposite-side BBO |
| Midpoint Peg | Track NBBO midpoint |
| Discretionary Peg | Midpoint peg with discretionary range to near-side |
| M-ELO | Midpoint Extended Life Order - 10ms minimum rest time |
| RPI | Retail Price Improvement - executes against retail flow only |
| Post-Only | Add liquidity only; cancels if would take |

**M-ELO specifics:**
- Holding period before eligible for execution (originally 500ms, reduced to 10ms in May 2020)
- **Dynamic M-ELO:** Uses ML to adjust holding period every 30 seconds per symbol
- Only executes against other eligible M-ELOs and M-ELO+CB orders
- Only available during market hours (9:30 AM - 4:00 PM ET)
- Designed to protect against latency arbitrage

**RPI specifics:**
- Non-displayed, liquidity-adding order priced at least $0.001 better than NBBO
- Only interacts with incoming Retail Orders (from natural persons, not algos)
- Must be for securities priced > $1.00
- Offset must be in $0.001 increments
- Retail Liquidity Indicator signals RPI interest available (priceless, sizeless)

### Self-Trade Prevention (STP)

Prevents accidental self-trades between a firm's own orders.

**STP Modifiers:**

| Code | Name | Behavior |
|------|------|----------|
| STPO | Cancel Oldest | Resting order cancelled; incoming remains intact |
| STPN | Cancel Newest | Incoming order cancelled; resting remains |
| STPD | Decrement Both | Smaller cancelled, larger decremented by smaller's size |

**STP configuration:**
- Configured at MPID level or port level
- Port level overrides MPID level
- When orders with different STP methods interact, incoming order's method used
- Cancelled orders receive reason code "Q" in FIX/OUCH

**Gotcha:** STP cancellations can affect queue position and fill expectations.

### Displayed vs Non-Displayed Priority

```
Priority Order:
1. Displayed orders (price-time)
2. Non-displayed orders (price-time within non-displayed)
```

Reserve order displayed portion has full priority. Hidden portion has lower priority than all displayed at same price.

### Modify/Replace Behavior

**Modifying an order:**
- Size decrease: Retains time priority
- Size increase: Loses time priority (new timestamp)
- Price change: Loses time priority

**Gotcha:** Queue position models must track modify semantics exactly.

## Opening and Closing Crosses

### Opening Cross

**Purpose:** Establish Official Opening Price (NOOP) for Nasdaq-listed securities.

**Timeline (Eastern Time):**

| Time | Event |
|------|-------|
| 4:00 AM | Pre-market opens |
| 9:25 AM | NOII dissemination begins |
| 9:28 AM | MOO/LOO order entry cutoff |
| 9:30 AM | Opening Cross executes |

**NOII (Net Order Imbalance Indicator):**

Disseminated every 5 seconds from 9:25-9:30 AM:
- Indicative clearing price
- Paired shares (matched volume)
- Imbalance size and direction
- Near/far indicative prices

### Closing Cross

**Purpose:** Establish Official Closing Price (NOCP) - critical for index funds, NAV calculations.

**Timeline:**

| Time | Event |
|------|-------|
| 15:50 | NOII dissemination begins (every 1 second) |
| 15:55 | MOC order entry cutoff |
| 15:58 | LOC order entry cutoff |
| 16:00 | Closing Cross executes |

**Volume significance:** Closing Cross often 15-20%+ of daily volume.

### Imbalance Dynamics

NOII fields for analysis:

| Field | Meaning |
|-------|---------|
| Current Reference Price | Midpoint of current inside |
| Near Indicative Clearing Price | Price that maximizes paired shares |
| Far Indicative Clearing Price | Price with imbalance consideration |
| Imbalance Shares | Net buy/sell imbalance |
| Imbalance Direction | B (buy), S (sell), N (none), O (no imbalance) |

**Quant uses:**
- Auction pressure signals
- Institutional flow proxy
- Close price impact estimation

### Auction Price Determination

Cross price determined by:
1. Maximize executable shares
2. Minimize imbalance
3. Minimize distance from reference price

Price collars may apply to prevent erratic prints.

## Halts and Reopenings

### Halt Types

| Code | Reason | Typical Duration |
|------|--------|------------------|
| T1 | News pending | Until news released |
| T2 | News released | Brief |
| T12 | Additional info requested | Variable |
| H4 | Non-compliance | Until resolved |
| H10 | SEC trading suspension | Extended |
| LUDP | LULD pause | 5 minutes |

### Halt Cross (Reopen)

When trading resumes after halt:
1. Orders accumulate during halt
2. NOII disseminated for halt cross
3. Single-price auction reopens trading
4. Continuous trading resumes

**2025 Update:** New Halt Cross Price Protections add price collars to prevent erratic reopen prices. Collars widen in 5-minute intervals if clearing price outside bounds.

### LULD Handling at Nasdaq

When LULD pause triggers:
1. Nasdaq halts continuous matching
2. Orders remain in book
3. LULD pause lasts 5 minutes (extendable)
4. Reopen via halt cross auction

## Tick and Lot Size

### Standard Increments

| Price Range | Min Tick |
|-------------|----------|
| >= $1.00 | $0.01 |
| $0.0001 - $0.9999 | $0.0001 |

### Sub-Penny Midpoint

Midpoint orders can execute at sub-penny prices (actual midpoint), not constrained to $0.01.

### Round Lot Modernization Impact

SEC round lot changes affect Nasdaq:
- Odd-lot orders may now contribute to NBBO for high-priced stocks
- Changes protected quotation determination
- Affects queue position analytics

## Market Data Feeds

### TotalView-ITCH

Nasdaq's premier depth-of-book feed:

**Content:**
- Full order book (all price levels)
- Order-level events (add, execute, cancel, replace)
- Auction imbalance messages (NOII)
- System events and stock directory

**Message Types (ITCH 5.0):**

| Type | Description |
|------|-------------|
| A | Add Order |
| F | Add Order with MPID |
| E | Order Executed |
| C | Order Executed with Price |
| X | Order Cancel |
| D | Order Delete |
| U | Order Replace |
| P | Non-Cross Trade |
| Q | Cross Trade |
| I | NOII (Imbalance) |

**Transport:** MoldUDP64 (multicast) or SoupBinTCP (TCP recovery)

### Nasdaq Basic

Lower-cost alternative:
- Top-of-book only
- Last sale
- No depth or order-level data

**Use case:** Compliance displays, basic monitoring. Not suitable for trading strategies.

### SIP vs Nasdaq Direct

| Aspect | UTP SIP (Tape C) | TotalView-ITCH |
|--------|------------------|----------------|
| Content | NBBO + trades | Full depth |
| Latency | ~500us-1ms | ~10-50us (co-lo) |
| Scope | All Tape C venues | Nasdaq only |
| Cost | Lower | Higher |

**Gotcha:** Must aggregate direct feeds from all venues for complete picture.

## Fee Structure

### Nasdaq Fee Schedule

Fees vary by security type, order type, and volume tier:

**Typical rates (Tape C, displayed):**

| Role | Rate |
|------|------|
| Add (provide liquidity) | Rebate $0.0020-0.0032 |
| Remove (take liquidity) | Fee $0.0029-0.0030 |

**Midpoint orders:**
- Typically lower/no rebate for adding
- Lower fee for removing

### BX (Inverted) Fees

BX uses inverted model:

| Role | Rate |
|------|------|
| Add | Fee (small) |
| Remove | Rebate |

Attracts order flow seeking taker rebates.

### Volume Tiers

Higher volume = better rates. Monthly volume thresholds determine rebate/fee levels.

## Trade Reporting

### Nasdaq Prints

Trades executing on Nasdaq book:
- Reported in TotalView-ITCH (Type E, C, P, Q messages)
- Disseminated on UTP SIP
- Correspond to order book events

### Auction Prints

Cross trades (Type Q) for:
- Opening Cross
- Closing Cross
- Halt Cross

Single price, single print consolidating auction volume.

### Non-Nasdaq Prints

Nasdaq-listed stocks trading elsewhere reported via TRF. Not in Nasdaq direct feed.

## Latency Profile

### Co-Location

Nasdaq data center: Carteret, NJ

| Service | Typical Latency |
|---------|-----------------|
| Co-located feed | 10-50 microseconds |
| Co-located order entry | Similar |
| Cross-connect | Varies by provider |

### Feed Processing

For book reconstruction:
- Handle out-of-order packets
- Implement gap detection (sequence numbers)
- Use recovery mechanisms (SoupBinTCP session, snapshot)

## Regulatory Context

### Nasdaq Rulebook

Key rule sections:
- **Equity 4** - Trading rules, order types, crosses
- **Equity 7** - Market data services

### Recent Changes (2024-2025)

- Halt Cross Price Protections (approved Feb 2025)
- NOII/EOII terminology formalization
- Hybrid Closing Cross option

See `references/regulatory/nasdaq_rules.md` for details.

## Gotchas Checklist

1. **Auction print classification** - Cross trades (Type Q) are distinct regime
2. **NOII parsing** - Handle all indicator fields; near vs far price differs
3. **Halt state machine** - Track halt codes, handle reopen auction
4. **Reserve refresh** - Loses time priority; model queue position correctly
5. **Modify semantics** - Size increase loses priority; track carefully
6. **Sequence gaps** - Implement robust recovery; missing messages corrupt book
7. **Cross-feed joins** - Timestamp normalization required between ITCH and SIP
8. **Fee tiers** - Volume-dependent; model economics correctly
9. **BX/PSX differences** - Different fee model, slightly different mechanics
10. **Odd-lot regime** - Round lot definition changes affect analytics
11. **STP cancellations** - Self-trade prevention can cancel resting orders unexpectedly
12. **M-ELO timing** - 10ms minimum rest; cannot cancel immediately after entry
13. **Peg repricing** - Pegged orders reprice on BBO changes; track reference price
14. **Post-Only rejects** - Orders rejected/cancelled if would cross spread

## Implementation Notes

### Book Reconstruction

For full book reconstruction from ITCH:
1. Process stock directory for symbol-locate mapping
2. Handle add/execute/cancel/delete/replace in sequence
3. Track displayed vs non-displayed separately
4. Validate with known prints

### Auction Analysis

For auction research:
1. Capture NOII messages throughout dissemination period
2. Track imbalance evolution
3. Compare indicative to final cross price
4. Analyze fill rates by order type

## References

See `references/` directory:
- `specs/itch_protocol.md` - ITCH 5.0 specification details
- `specs/ouch_protocol.md` - OUCH order entry
- `specs/totalview.md` - TotalView product overview
- `regulatory/nasdaq_rules.md` - Nasdaq rulebook references
