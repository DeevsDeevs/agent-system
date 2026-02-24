# US Equity Market Structure

**Timezone:** ET (Eastern Time, UTC-5 / UTC-4 DST)

US equity markets operate under Regulation NMS, creating a linked national market system. This document covers concepts shared across all US equity venues.

## Overview and Role

### Market Ecosystem

The US equity market is fragmented by design:
- **16+ lit exchanges** - CLOBs with displayed quotes
- **30+ ATSs/dark pools** - Limited pre-trade transparency
- **Wholesalers/internalizers** - Principal execution of retail flow
- **TRFs** - Off-exchange trade reporting

**Implication:** "The market" is an ecosystem, not a single order book. Microstructure analysis must account for fragmentation.

### Listing vs Trading Venues

Distinction matters:
- **Listing venue** - Where the security is officially listed (NYSE, Nasdaq)
- **Trading venues** - Where the security can trade (any NMS exchange)

A Nasdaq-listed stock trades on NYSE, CBOE, IEX, etc. Listing venue determines some regulatory requirements and tape assignment.

## NBBO and Protected Quotes

### NBBO Definition

The **National Best Bid and Offer (NBBO)** is computed from protected quotations:
- Automated quotes from NMS exchanges
- Displayed, immediately accessible
- Disseminated via SIP

### What NBBO Excludes

NBBO is economically incomplete:

| Excluded Liquidity | Reason |
|--------------------|--------|
| Hidden/reserve orders | Not displayed |
| Odd-lot quotes | Historically excluded (changing with modernization) |
| ATS/dark pool quotes | Not protected quotations |
| Midpoint pegs | Not displayed |

**Gotcha:** Metrics like "price improvement vs NBBO" depend on NBBO completeness for that symbol and date regime.

## Order Book Mechanics

### Standard Priority

US equity CLOBs use **price-time priority**:
1. Better price always wins
2. At same price, earlier timestamp wins

### Displayed vs Non-Displayed

| Order Type | Visibility | Priority |
|------------|------------|----------|
| Displayed | Visible in book | Full price-time |
| Reserve (displayed portion) | Visible | Price-time for displayed |
| Reserve (hidden portion) | Hidden | Lower priority than displayed |
| Midpoint peg | Hidden | Executes at midpoint |

**Gotcha:** Reserve refresh typically loses time priority. Check venue-specific rules.

## NYSE Mechanics

See [[equity/amer/nyse/nyse.md|nyse.md]] for NYSE-specific mechanics (parity allocation, DMM, D-Orders, XDP feed).

Key difference from other US venues: NYSE uses **parity allocation** (not pure price-time) — invalidates standard FIFO queue models for Tape A securities.

## Hidden/Reserve Order Dynamics


### Hidden Depth Prevalence

- 22-25% hidden depth at L1 (Tuttle 2006, Nasdaq 100 study)
- Reserve order minimum display size: 100 shares (standard across venues)
- Hidden orders are non-protected quotations -- excluded from NBBO
- Execution priority: all displayed orders at same price execute before any hidden at that price

### Reserve Refresh Mechanics

| Component | Timestamp Behavior | Priority |
|-----------|--------------------|----------|
| Displayed portion | New timestamp on refresh | Goes to back of displayed queue |
| Hidden portion | Retains original timestamp | Lower priority than ALL displayed at same price |

**Implications for queue models:**
- Reserve refreshes create phantom queue position loss
- Models that assume stable queue position underestimate adverse selection on reserves
- Refresh frequency is unobservable from SIP data; requires direct feed

### Midpoint Extended Life Orders (M-ELO)

| Parameter | Value |
|-----------|-------|
| Initial holding period | 500ms (Mar 2018 launch) |
| Reduced holding period | 10ms (May 2020) |
| Dynamic M-ELO | Sep 2023, AI-powered midpoint estimation |
| Eligible securities | All NMS stocks on Nasdaq |

M-ELO prevents latency arbitrage by requiring both sides to rest before matching. Dynamic M-ELO uses machine learning to determine optimal execution timing at midpoint.

### IEX Speed Bump

| Parameter | Value |
|-----------|-------|
| Delay mechanism | 350us coil (38 miles of fiber) |
| Direction | All inbound and outbound messages |
| CQI trigger frequency | ~0.02% of time |
| Marketable orders caught by CQI | ~32% |

CQI (Crumbling Quote Indicator) detects when NBBO is likely about to change. When active, IEX disables price-sliding for incoming orders, protecting resting liquidity from adverse selection.

### Venue-Specific Hidden Order Variants

| Venue | Hidden Type | Special Behavior |
|-------|-------------|------------------|
| Nasdaq | Non-Displayed (NOND) | Standard hidden, retains timestamp |
| Nasdaq | Post-Only Hidden | Adds hidden; if would lock, posts at less aggressive |
| NYSE | Non-Displayed Limit | Below displayed in parity allocation |
| NYSE Arca | Passive Liquidity (PLO) | Pegs to far side of NBBO |
| IEX | Midpoint Peg | D-Peg discretionary, CQI-protected |
| MEMX | Hidden | Standard hidden, price-time within hidden tier |

## Auctions

### Purpose

Centralized single-price auctions concentrate liquidity at key times:
- **Opening auction** - Establishes opening price after overnight gap
- **Closing auction** - Sets official closing price for NAV, index calculations
- **Halt/IPO auction** - Reopens trading after halts

### General Mechanics

1. Orders accumulate during pre-auction period
2. Exchange calculates indicative clearing price
3. At designated time, single-price match occurs
4. Auction prints are distinct from continuous trading

**Volume significance:** Opening auctions typically 3-5% of daily volume; closing auctions 10-20%+.

## Halts and Circuit Breakers

### LULD (Limit Up/Limit Down)

Prevents extreme price moves in individual securities:

**Band Calculation:**
```
Upper Band = Reference Price x (1 + Percentage)
Lower Band = Reference Price x (1 - Percentage)
Reference Price = 5-minute rolling average
```

**Percentage Bands:**

| Tier | Price > $3 | Price $0.75-$3 | Price < $0.75 |
|------|------------|----------------|---------------|
| Tier 1 (S&P 500, Russell 1000) | 5% | 20% | 75% or $0.15 |
| Tier 2 (other NMS) | 10% | 20% | 75% or $0.15 |

**Pause trigger:** If price touches band and stays for 15 seconds, 5-minute trading pause.

**End-of-day:** Bands double in last 25 minutes for Tier 1 and low-priced Tier 2.

### Market-Wide Circuit Breakers (MWCB)

Based on S&P 500 decline from prior close:

| Level | Decline | Action |
|-------|---------|--------|
| Level 1 | 7% | 15-min halt (before 3:25 PM) |
| Level 2 | 13% | 15-min halt (before 3:25 PM) |
| Level 3 | 20% | Trading halted for day |

### Regulatory Halts

Exchanges can halt for:
- News pending/dissemination
- Regulatory concerns
- Listing issues
- Corporate actions

Each halt type has specific reopen mechanics.

## Tick Size and Lot Size

### Current Regime

| Price | Minimum Tick |
|-------|--------------|
| >= $1.00 | $0.01 |
| < $1.00 | $0.0001 (varies) |

**Sub-penny rule:** Quotes in NMS stocks >= $1 must be in $0.01 increments (with exceptions for midpoint orders).

### Round Lot Definition

Historically: 100 shares = 1 round lot

**Modernization (2024+):** Round lot definition changes based on price:
- $250+ stocks: 40 shares
- $1000+ stocks: 10 shares
- $10000+ stocks: 1 share

This affects NBBO inclusion and protected quote status.

**Gotcha:** Tick/lot regime changes are regime shifts that can break backtests.

## Data Feeds

### SIP (Securities Information Processor)

Consolidated market data:

| Tape | Coverage | Plan |
|------|----------|------|
| Tape A | NYSE-listed | CTA/CQ |
| Tape B | Regional exchange-listed | CTA/CQ |
| Tape C | Nasdaq-listed | UTP |

**SIP content:**
- NBBO (top-of-book)
- Last sale (trades)
- No depth beyond top

### Direct Feeds

Exchange-proprietary feeds:
- Full depth-of-book
- Order-level events (add, modify, cancel, execute)
- Auction imbalance data
- Lower latency than SIP

**Gotchas:**
- SIP vs direct feed timestamps can differ
- Cross-feed time alignment requires careful normalization
- Direct feeds are venue-specific; must aggregate for full picture

### Latency Characteristics

| Feed Type | Typical Latency |
|-----------|-----------------|
| SIP | 500us - 1ms |
| Direct (co-located) | 10-50us |
| Direct (remote) | 100us+ network RTT |

## SIP vs Direct Feed Reconciliation


### CTA Latency Benchmarks

| Exchange to SIP | Quote Median (us) | Trade Median (us) |
|-----------------|--------------------|--------------------|
| NYSE to CTA | 105 | 154 |
| Nasdaq to UTP | 17 | 22 |
| Cboe to CTA | 401-409 | 456-472 |
| Nasdaq to CTA | 540 | 586 |

### SIP-Direct Dislocation

- 97% of SIP-priced trades match direct-feed NBBO (Bartlett & McCrary 2019)
- Mean dislocation duration: 1,002 us (median 489 us)
- Mean dislocation size: $0.0109
- Dislocations cluster during high-volatility periods and around NBBO transitions
- Economic significance: material only for sub-millisecond strategies

### TAQ-LOB Matching

Composite key matching methodology for TAQ-to-LOB reconciliation:

| Field | Resolution | Source |
|-------|------------|--------|
| Symbol | Exact | Both feeds |
| Price | Exact | Both feeds |
| Size | Exact | Both feeds |
| Participant timestamp | Nanosecond | TAQ (post-2015) |

- Holden, Pierson & Wu (2024): matched 654M TAQ-to-LOB trades
- Lee-Ready accuracy improved from 86.75% to 92.05% with matched data
- Pre-2015 TAQ: millisecond timestamps only, matching degrades significantly
- Cross-venue matching requires normalization of exchange-specific timestamp epochs

## Fee Structure

### Maker-Taker Model

Standard model at most exchanges:

| Role | Fee/Rebate |
|------|------------|
| Maker (add liquidity) | Rebate (~$0.0020/share) |
| Taker (remove liquidity) | Fee (~$0.0030/share) |

### Inverted (Taker-Maker) Model

Some venues (BX, EDGA) invert:

| Role | Fee/Rebate |
|------|------------|
| Maker | Fee |
| Taker | Rebate |

Attracts different order flow characteristics.

**Quant implication:** All-in price = execution price +/- fees. Model economics, not just displayed prices.

## Trade Reporting

### On-Exchange Prints

Trades on lit exchanges:
- Reported in real-time via exchange feed
- Included in SIP consolidated tape
- Correspond to queue events in order book

### Off-Exchange Prints (TRF)

Trades executed off-exchange:
- Wholesaler internalization
- ATS/dark pool executions
- Bilateral OTC trades

Reported to TRF within 10 seconds, disseminated on tape.

**Gotcha:** TRF prints are real volume but do not correspond to visible order book queues. Separate in analytics.

## Routing and Reg NMS

### Order Protection Rule (Rule 611)

Prevents trade-throughs of protected quotations:
- Cannot execute at price inferior to NBBO
- Must route to better-priced venues or use ISO

### Intermarket Sweep Order (ISO)

Allows aggressive execution while satisfying 611:
- Simultaneously sweep better-priced protected quotes
- Execute remainder at intended venue
- Creates multi-venue burst activity

**Gotcha:** ISO sweeps complicate microstructure causality analysis.

### Access Fee Cap (Rule 610)

Limits access fees to $0.003/share for protected quotes. Shapes maker-taker economics.

## Best Execution

### Broker Obligation

FINRA Rule 5310 requires best execution:
- Reasonable diligence to obtain best terms
- Consider price, speed, likelihood of execution
- Not just "best price" - multi-dimensional

### SOR Optimization

Smart Order Routers balance:
- Price improvement probability
- Fill rate
- Fees and rebates
- Market impact
- Information leakage

### Wholesalers

Major wholesalers (Citadel Securities, Virtu):
- Execute retail marketable flow as principal
- Provide NBBO-or-better execution
- Hedge net risk on exchanges/ATSs

**PFOF:** Brokers may receive payment for order flow. Disclosed via Rule 606.

## Market Maker Programs


| Program | Quote Width | NBBO Uptime | Rebate |
|---------|-------------|-------------|--------|
| Nasdaq MM | 8-30% designated | Continuous | QMM +$0.0004, top ~$0.0032 |
| Nasdaq QMM | >=1,000 symbols >=25% | 25% in 1,000+ | Remove $0.00295 |
| NYSE DMM | LULD-based % | >=15% (non-ETP)/>=25% (ETP) | Up to $0.0035 |
| NYSE SLP | At NBB/NBO | >=10% at NBBO | ~$0.0032 |
| NYSE Arca LMM | <=2% from NBBO | 90% continuous | Enhanced + $10-40K/yr |
| IEX IEMM | Designated % | Inside >=20%, Depth >=75% | Fee discounts |

**Flash Crash evidence:** Buy-side depth fell to ~25% midday levels, sell-side ~15%. DMMs who stayed helped curtail turmoil (MacKenzie 2015).

## Disclosures

### Rule 605

Execution quality reporting:
- Monthly statistics by market center
- Effective/quoted spread, price improvement
- Fill rates, speed metrics

### Rule 606

Routing disclosure:
- Quarterly reports on order routing
- Payment for order flow amounts
- Material routing relationships

## Data Quality Considerations

### Tick Validation

Filter potentially erroneous data:

| Check | Criteria |
|-------|----------|
| Price bounds | Within LULD bands at time of trade |
| Size bounds | Not unreasonably large (e.g., < 10x typical) |
| Zero price | Flag for investigation |
| Condition codes | Filter out-of-sequence (Z), corrections |

### Timestamp Quality

| Issue | Detection | Handling |
|-------|-----------|----------|
| SIP vs direct misalignment | Median offset > expected | Recalibrate offset |
| Clock drift | Offset changes over time | Monitor and correct |
| Out-of-order messages | Sequence gaps | Buffer and reorder |
| DST transitions | Mar/Nov anomalies | Calendar-aware processing |

### Cross-Feed Consistency

Reconcile across data sources:
- Volume totals should match (SIP = direct + TRF)
- BBO prices should align (within latency tolerance)
- Trade counts should reconcile (accounting for aggregation)

See `references/specs/sip_specs.md` [[equity/amer/references/specs/sip_specs.md|sip_specs.md]] for detailed alignment procedures.

## Data Validation Checklist


45-check architecture organized in 12 sections (A-L):

| Section | Checks | Critical | High | Medium | Key Checks |
|---------|--------|----------|------|--------|------------|
| A: Sequence Integrity | 5 | 3 | 2 | 0 | Session ID, seq monotonicity, gap retransmission |
| B: Timestamp Monotonicity | 4 | 1 | 2 | 1 | Non-decreasing, Replace consistency, range |
| C: Book Consistency | 4 | 3 | 1 | 0 | No negatives, no crossed book, no phantoms |
| D: Cross-Type Consistency | 4 | 2 | 2 | 0 | E/C to A/F chain, no ref reuse |
| E: Auction Validation | 4 | 0 | 3 | 1 | NOII intervals, cross price in collar |
| F: Corporate Action | 4 | 2 | 1 | 1 | Stock Directory completeness, locate mapping |
| G: Halt State Machine | 4 | 0 | 2 | 2 | Valid transitions T->H->Q->T, halt codes |
| H: Trade Break | 3 | 1 | 1 | 1 | Order NOT restored after break |
| I: Volume Reconciliation | 2 | 0 | 1 | 1 | ITCH vs SIP within 0.1% |
| J: Stock Locate | 3 | 2 | 0 | 1 | Daily locate-to-symbol map |
| K: System Events | 2 | 1 | 1 | 0 | O->S->Q->M->E->C sequence |
| L: Best Practices | 6 | 0 | 4 | 2 | Withdrawn quotes, locked NBBO, printable flag |

**Totals:** 45 checks -- 13 Critical, 19 High, 13 Medium.

**Processing order:** Transport (A) -> Timestamp (B) -> Reference Data (J,K) -> State Machine (G) -> Order Lifecycle (C,D) -> Auction (E) -> Trade Breaks (H) -> Volume (I) -> Corporate Actions (F) -> Best Practices (L).

Full 45-check detail in `nasdaq/references/specs/itch_protocol.md` [[equity/amer/nasdaq/references/specs/itch_protocol.md|itch_protocol.md]].

## Empirical Parameters


### Spread Parameters

| Tier | Effective Spread (bps) |
|------|------------------------|
| Mega-cap (top 50) | 1-3 (AAPL/MSFT ~0.7) |
| Large-cap (S&P 500) | 2-7 (Hagstromer 2021: mean 3.2) |
| Mid-cap (S&P 400) | 5-15 |
| Small-cap (R2000) | 10-30 |
| Micro-cap | 30-200+ |

**Intraday pattern:** J-shaped. Open 50-200% above average, midday trough, close moderate widening.

### Impact Parameters

**Almgren-Chriss (2005) calibration:**

| Parameter | Symbol | Value | Meaning |
|-----------|--------|-------|---------|
| Permanent impact | gamma | 0.314 | Price shift per unit participation |
| Temporary impact | eta | 0.142 | Execution cost per unit speed |
| Impact exponent | beta | 0.6 | Concavity of impact function |

**Universal square-root law:**
```
G = sigma * sqrt(|Q|/V) * theta
```
Where sigma = daily volatility, Q = order size, V = daily volume, theta ~ 1.

**Impact decay:**

| Horizon | Retained Impact |
|---------|-----------------|
| Same-day (EOD) | ~2/3 of peak |
| ~5 days | ~60% of day-1 |
| ~50 days | ~50% of day-1 |

Permanent component is the fraction that does not revert. Temporary component decays exponentially with half-life of minutes to hours depending on participation rate.

### Fill Rate (Back-of-Queue, Large-Tick)

| Horizon | Fill Rate |
|---------|-----------|
| 1 second | ~1-5% |
| 10 seconds | ~5-15% |
| 1 minute | ~10-30% |
| End-of-day | ~20-50% |

### Order Book Imbalance (OBI) Predictive Power

- **L1 OFI:** R-squared ~65% contemporaneous 10s (Cont, Kukanov & Stoikov 2014)
- **Multi-level (10 levels):** R-squared ~80%
- **Signal half-life:** 5-30 seconds

### Large Print Refill

4-phase pattern:
1. Response-latency (<1s)
2. HFT reaction (1-5s)
3. Stimulated refill (5-10s)
4. Normalization (10+s)

- 50% depth restored in 2-5 seconds
- 100% in 5-10 seconds
- Limit order intensity takes ~30 min to normalize

## Gotchas Checklist

1. **NBBO completeness** - Hidden liquidity, odd-lots, regime changes
2. **Feed alignment** - SIP vs direct timestamps differ by 1-25ms typically
3. **TRF classification** - Separate off-exchange from lit prints
4. **Auction regime** - Treat open/close/halt prints distinctly
5. **Fee economics** - Model all-in cost, not displayed price
6. **ISO bursts** - Multi-venue activity complicates causality
7. **Tick/lot modernization** - Regime changes break backtests
8. **Halt state machine** - Handle halt codes explicitly
9. **Erroneous trades** - Validate against LULD bands; filter outliers
10. **NBBO staleness** - SIP NBBO stale ~10,000x/day in active stocks

## Regime Change Database


| Date | Event | Impact |
|------|-------|--------|
| 2005-06-29 | Reg NMS adopted | Penny tick, $0.003 cap, sub-penny prohibited |
| 2007-02-05 | Reg NMS Phase 2 all NMS | Full order protection |
| 2007-07-03 | Uptick rule eliminated | No short-sale test until 2010 |
| 2010-02-24 | Alt Uptick Rule (201) | 10% decline triggers restriction |
| 2010-05-06 | Flash Crash | Prompted LULD |
| 2013-04-08 | LULD Phase I + MWCB reform | Price bands replace SSCBs; S&P 500-based 7/13/20% |
| 2013-08-05 | LULD Phase II all NMS | SSCBs fully retired |
| 2016-10-03 | Tick Size Pilot | $0.05 tick ~1,200 stocks |
| 2018-03-12 | Nasdaq M-ELO | 500ms holding |
| 2018-09-28 | Tick Pilot ends | All return to penny |
| 2019-04-11 | LULD permanent | No longer pilot |
| 2020-03-09-18 | 4x MWCB Level 1 (COVID) | First triggers under new rules |
| 2020-05-11 | M-ELO reduced to 10ms | Broadened M-ELO |
| 2020-12-09 | MDI Rule adopted | Round lot redef, competing consolidators |
| 2024-09-18 | Tick/access fee reform | Half-penny tick ~1,700 stocks, $0.001 cap |
| 2025-10-31 | Compliance delayed to Nov 2026 | Penny tick persists through Oct 2026 |
| 2025-11-03 | New round lot definitions live | Tiered: 100/40/10/1 by price |

### Backtesting Regime Boundaries

| Period | Key Constraint |
|--------|----------------|
| Pre-2005 | Decimal conversion (2001), pre-Reg NMS fee structure |
| 2005-2007 | Reg NMS adopted but not fully phased in |
| Pre-2007 | Requires uptick rule modeling for short sales |
| 2007-2010 | No short-sale price test; unrestricted shorting |
| 2010-2013 | Alt uptick rule active; pre-LULD (SSCBs instead) |
| 2013-2016 | LULD regime; pre-Tick Pilot |
| Oct 2016-Sep 2018 | Tick Pilot: ~1,200 stocks at $0.05 tick |
| 2019-2024 | LULD permanent; penny tick universal |
| Sep 2024-Oct 2026 | Half-penny tick ~1,700 stocks; $0.001 access fee cap |
| Nov 2026+ | New round lot definitions; competing consolidators |

LULD Amendment 10 (Jul 2016): 80% fewer halts via wider bands and straddle-state elimination.

## Outage & Corruption Registry


| Date | Venue | Duration | Severity | Handling |
|------|-------|----------|----------|----------|
| 2010-05-06 | All US + CME | ~36 min | CRITICAL | Exclude busted trades; flag 2:32-3:07 PM |
| 2013-08-22 | Nasdaq SIP | ~3 hrs | CRITICAL | Exclude 12:14-3:25 PM all Tape C |
| 2014-10 | CTA SIP | ~27 min | HIGH | Flag SIP data 1:07-1:41 PM |
| 2015-07-08 | NYSE | ~3.5 hrs | HIGH | Exclude NYSE venue; flag NBBO quality |
| 2020-03-09-18 | All US + CME | 15 min each | HIGH | Flag halt windows; extensive LULD pauses |
| 2024-06-03 | CTA SIP (NYSE) | ~2 hrs | HIGH | Exclude erroneous prints; use bust notices |

### Outage Handling Protocol

1. **CRITICAL events:** Exclude entire window from all analytics; do not interpolate
2. **HIGH events:** Flag window; venue-specific exclusion; validate NBBO quality in surrounding periods
3. Check exchange bust/correction notices for affected prints
4. SIP outages affect all Tape participants -- cascade to NBBO quality downstream
5. For multi-day studies spanning outages: use dummy variable or exclude entire day
6. Flash Crash busted-trade threshold: 60%+ from pre-2:40 PM reference price

## Vendor Data Quirks


### Dataset-Specific Issues

| Vendor/Dataset | Critical Quirk | Impact |
|----------------|----------------|--------|
| TAQ Monthly (MTAQ) | Second-level timestamps; withdrawn quotes unflagged | 43% effective spread overestimation vs DTAQ (Holden & Jacobsen 2014) |
| TAQ Daily (DTAQ) | Millisecond to microsecond mid-2015 | Timestamp regime break in historical analysis |
| LOBSTER | Nasdaq-only; day-unique order IDs; unadjusted prices | No multi-venue book; no corp action adjustment |
| LOBSTER | Hidden Type P = executed portion only | Understates hidden liquidity |
| Bloomberg | Bar timestamp = bar OPEN time | Off-by-one-period if misinterpreted as close |
| Bloomberg | No retroactive corp action adjustments post ex-date open | Stale adjustments for undetermined dividends |
| WRDS | Microsecond upgrade mid-2015 | Pre-2015: millisecond; post-2015: microsecond participant timestamps |

### TAQ Version Comparison

| Feature | MTAQ | DTAQ |
|---------|------|------|
| Timestamp resolution | 1 second | Millisecond (pre-2015) / Microsecond (post-2015) |
| Withdrawn quote flags | Missing | Present |
| Effective spread accuracy | ~43% overestimated | Baseline |
| Availability | 1993+ | 2003+ |
| Storage | Compressed monthly | Daily files |

### Survivorship Bias Corrections

- **Backbone:** CRSP PERMNO as primary identifier
- **Shumway correction:** Impute -30% NYSE/AMEX, -55% Nasdaq for missing performance-related delistings
- **Missing data:** 13% of delistings (2,742 of 20,680) still missing returns as of ~2017
- **Implication:** Uncorrected delisting bias overstates returns by 0.5-1.0% annually for small-cap portfolios

## References

See `references/` directory for detailed documentation:
- `regulatory/sec_reg_nms.md` - Reg NMS rules
- `regulatory/finra_rules.md` - FINRA requirements
- `regulatory/rule_605_606.md` - Disclosure rules
- `specs/sip_specs.md` - SIP specifications
