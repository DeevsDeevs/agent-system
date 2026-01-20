# SIP Specifications - Securities Information Processor

Technical specifications for US equity consolidated market data feeds.

## Overview

The SIP produces consolidated quote and trade data for NMS securities. Two separate plans:

| Plan | Tape | Coverage |
|------|------|----------|
| CTA/CQ | A, B | NYSE-listed, regional listings |
| UTP | C | Nasdaq-listed |

## UTP Plan (Tape C)

### Governance

Nasdaq UTP Plan governs Tape C data:
- Administered by participating exchanges
- Revenue sharing based on activity
- Technical specs maintained by Nasdaq

**Official site:** https://www.utpplan.com/

### Data Content

**Quotation data (UTP Quotation Data Feed - UQDF):**
- Best bid and offer from each participant
- NBBO calculation
- Quote condition indicators

**Trade data (UTP Trade Data Feed - UTDF):**
- Last sale reports
- Trade condition codes
- Volume information

### Message Types

**Quote messages:**
- Level 1 quote update
- NBBO update
- Quote cancel/correction

**Trade messages:**
- Regular sale
- Trade cancel
- Trade correction
- Prior reference price

### Condition Codes

**Quote conditions:**

| Code | Meaning |
|------|---------|
| A | Slow quote on offer side |
| B | Slow quote on bid side |
| C | Closing quote |
| F | Fast trading |
| O | Opening quote |
| R | Regular two-sided quote |

**Trade conditions:**

| Code | Meaning |
|------|---------|
| @ | Regular sale |
| C | Cash trade |
| E | Automatic execution |
| F | Intermarket sweep |
| H | Price variation |
| I | Odd lot |
| K | Rule 127/155 |
| M | Market center official close |
| O | Opening print |
| Q | Market center official open |
| T | Extended hours |
| U | Extended hours sold |
| Z | Sold out of sequence |

### Timestamp Precision

UTP provides timestamps with microsecond precision. However, SIP latency means timestamps reflect SIP processing time, not exchange event time.

## CTA/CQ Plan (Tape A/B)

### Governance

Consolidated Tape Association Plan:
- CTA Plan (trades)
- CQ Plan (quotes)

Covers NYSE-listed and regional exchange listings.

### Data Content

Similar structure to UTP:
- Consolidated quotes with NBBO
- Consolidated last sale
- Administrative messages

### Differences from UTP

Minor variations in:
- Message formats
- Field definitions
- Condition codes

Functionally similar for most purposes.

## SIP vs Direct Feed Comparison

| Aspect | SIP | Direct Feed |
|--------|-----|-------------|
| Content | Top-of-book only | Full depth |
| Latency | ~500us-1ms | ~10-50us (co-lo) |
| Scope | All NMS exchanges | Single exchange |
| NBBO | Pre-calculated | Must calculate |
| Cost | Included in market data fees | Additional |
| Complexity | Lower | Higher |

## SIP Latency

### Sources of Latency

1. **Collection** - Exchange reports to SIP
2. **Processing** - NBBO calculation, sequencing
3. **Distribution** - Network to recipient

### Typical Latencies

| Scenario | Latency |
|----------|---------|
| SIP processing | 50-200 microseconds |
| Network distribution | 200-500 microseconds |
| Total (co-located) | 300-700 microseconds |
| Total (remote) | 500us - several ms |

### Implications

- Direct feeds arrive before SIP
- SIP NBBO may be stale during fast markets
- Arbitrage opportunities exist (SIP vs direct)

## NBBO Calculation

### Protected Quotation Requirements

For quote to be included in NBBO:
- Automated (no manual intervention)
- Best bid or offer at reporting exchange
- Displayed (not hidden)
- Round lot size (100 shares, or modernized definition)

### Update Frequency

NBBO updates whenever:
- Participating exchange updates quote
- Quote becomes protected/unprotected
- Administrative changes

### NBBO Fields

| Field | Description |
|-------|-------------|
| Best Bid Price | Highest bid among protected quotes |
| Best Bid Size | Aggregate size at best bid |
| Best Offer Price | Lowest offer among protected quotes |
| Best Offer Size | Aggregate size at best offer |
| Bid Exchange(s) | Exchange(s) at best bid |
| Offer Exchange(s) | Exchange(s) at best offer |

## SIP Modernization

### 2024-2025 Changes

**Round lot definition:**
- Price-based round lot tiers
- Affects NBBO inclusion
- High-priced stocks: smaller round lots

**Odd-lot quote inclusion:**
- Odd lots may contribute to NBBO for high-priced stocks
- Changes protected quotation landscape

**Depth of book:**
- Discussions about SIP depth
- Currently top-of-book only

## Implementation Notes

### Feed Handlers

SIP feed handler requirements:
- Parse binary message formats
- Handle retransmissions
- Maintain sequence integrity
- Process administrative messages

### Data Quality

Common issues:
- Gap in sequence numbers (request retransmission)
- Stale quotes (check timestamps)
- Crossed NBBO (locked/crossed market conditions)
- Holiday/half-day schedules

### Time Synchronization

- SIP timestamps are SIP processing time
- Not aligned with exchange timestamps
- Careful with cross-feed analysis

## SIP vs Direct Feed Timestamp Alignment

### Quantified Latency Differences

Based on academic studies of SIP vs direct feed latency:

| Metric | Quote Latency | Trade Latency |
|--------|---------------|---------------|
| Mean | ~1,128 us (1.1 ms) | ~24,255 us (24 ms) |
| Median | ~500-800 us | ~1-5 ms |
| Tail (99th percentile) | 5-20 ms | 50-100+ ms |

**Key insight:** Trade reporting latency is ~20x higher than quote latency.

### NBBO Staleness Frequency

Empirical findings:
- SIP NBBO lags "true" NBBO ~10,000+ times per day for active stocks
- Dislocations typically last 1-2 milliseconds
- Median price dislocation: $0.01 (one tick)
- Mean price dislocation: $0.034 (3.4 cents) due to tail events

### Detecting Stale NBBO

**Synthetic NBBO construction:**
1. Build "true" BBO from direct feeds for each venue
2. Aggregate across venues to get synthetic NBBO
3. Compare to SIP NBBO

**Staleness indicators:**
- SIP NBBO timestamp older than direct feed BBO
- SIP NBBO price differs from synthetic NBBO
- Direct feed shows trade through SIP NBBO

### Timestamp Alignment Procedures

**Clock synchronization requirements:**
- PTP (Precision Time Protocol) recommended for direct feeds
- SIP timestamps may drift up to 16 milliseconds
- GPS or atomic clock reference for accurate alignment

**Alignment algorithm:**
```
1. Record (exchange_timestamp, sip_timestamp) pairs at matching events
2. Compute offset = median(sip_timestamp - exchange_timestamp)
3. Apply offset to normalize SIP timestamps
4. Monitor offset drift over time
5. Recalibrate periodically (hourly minimum)
```

**Gotcha:** SIP timestamp can be earlier than exchange event due to clock drift.

### DST and Calendar Handling

| Event | Handling |
|-------|----------|
| DST spring forward (Mar) | 1-hour gap at 2 AM ET; no feed data during gap |
| DST fall back (Nov) | 1-hour overlap at 2 AM ET; disambiguate with sequence |
| Early close (1 PM ET) | Closing cross at 1 PM, not 4 PM |
| Holidays | No feed data; check exchange calendar |

## Cross-Feed Reconciliation

### Trade Matching Across Feeds

Matching SIP trades to direct feed events is non-trivial:

| Challenge | Description |
|-----------|-------------|
| No common ID | SIP trades have no order reference; ITCH does |
| Timestamp mismatch | Different clocks, different latencies |
| Aggregation | SIP may aggregate; direct feeds show individual events |
| Condition codes | Different code semantics |

**Matching heuristics:**
1. Match on (symbol, price, size, approximate time)
2. Allow time window based on expected latency (2-50 ms)
3. Handle size aggregation (multiple ITCH executes = one SIP print)
4. Validate condition code consistency

### Volume Reconciliation

Daily volume should match:
```
SIP total volume = sum(direct feed volumes) + TRF volume

Discrepancies indicate:
- Missed messages (gaps)
- Trade cancellations not processed
- Late print handling
```

### BBO Consistency Validation

Compare SIP NBBO to synthetic NBBO:

| Check | Expected |
|-------|----------|
| Price match | SIP NBBO = synthetic NBBO (within latency window) |
| Size match | May differ due to aggregation |
| Exchange attribution | Should match venue with best quote |

**Crossed NBBO handling:**
- SIP may show crossed NBBO during fast markets
- Direct feeds may show valid (uncrossed) state
- Log and investigate persistent crosses

## Clearly Erroneous Trade Detection

### Definition

A trade is "clearly erroneous" when the price is substantially inconsistent with the market price at execution time.

### Filing Window

- 30 minutes from execution time for most trades
- Additional 30 minutes for routed executions (max 60 total)

### Validation Approach

Compare trade price to reference price (typically consolidated last sale):
1. Calculate deviation: |trade_price - reference_price| / reference_price
2. Compare to threshold (varies by price tier and session)
3. Flag trades exceeding threshold for review

**Additional factors:**
- System malfunctions or disruptions
- Volume and volatility context
- News or corporate actions
- IPO or recently resumed trading
- Overall market conditions

### Data Quality Filters

For research/analytics, filter trades that may be erroneous:

| Filter | Criteria |
|--------|----------|
| Price reasonableness | Within LULD bands at execution time |
| Size reasonableness | < 10x average trade size for symbol |
| Condition code | Exclude late/out-of-sequence (code Z) |
| Trade type | Exclude clearly marked corrections |

## Official Documentation

**UTP Plan:**
- https://www.utpplan.com/

**CTA Plan:**
- https://www.ctaplan.com/

**Nasdaq Technical Specs:**
- UQDF specification
- UTDF specification

## Data Vendors

SIP data available through:
- Direct from exchanges
- Market data vendors (Bloomberg, Refinitiv)
- Cloud providers (Nasdaq Cloud, AWS Data Exchange)

## Quant Considerations

### When to Use SIP

- Compliance/regulatory requirements
- NBBO reference for best execution
- Lower-frequency strategies
- Cost-sensitive applications

### When SIP is Insufficient

- HFT/latency-sensitive strategies
- Full book reconstruction
- Auction imbalance analysis
- Detailed venue analysis

### Research Applications

- NBBO as benchmark for execution quality
- Spread analysis across time
- Market quality studies
- Regulatory analysis
