# US Equity Market Structure

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

See `references/specs/sip_specs.md` for detailed alignment procedures.

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

## References

See `references/` directory for detailed documentation:
- `regulatory/sec_reg_nms.md` - Reg NMS rules
- `regulatory/finra_rules.md` - FINRA requirements
- `regulatory/rule_605_606.md` - Disclosure rules
- `specs/sip_specs.md` - SIP specifications
