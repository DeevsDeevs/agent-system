# SEC Regulation NMS

Regulation National Market System - the foundational regulatory framework for US equity markets.

## Overview

Adopted by the SEC in 2005 (effective 2007), Reg NMS modernized US equity market structure. Key goals:
- Strengthen price protection across markets
- Improve access to quotations
- Enhance market data infrastructure
- Reduce sub-penny trading

## Key Rules

### Rule 611 - Order Protection Rule

**Purpose:** Prevent trade-throughs of protected quotations.

**Core requirement:** Trading centers must establish procedures to prevent executions at prices inferior to protected quotations displayed by other trading centers.

**Protected quotation defined:**
- Automated quote
- Displayed on NMS exchange
- Best bid or offer at that exchange

**Exceptions to Rule 611:**

| Exception | Description |
|-----------|-------------|
| Intermarket Sweep | ISO that simultaneously routes to better prices |
| Flickering Quote | Quote changed during routing |
| Self-Help | Responding trading center experiencing delay |
| Benchmark | VWAP or other benchmark trades |
| Crossed Market | NBBO is crossed |
| Opening/Closing | Single-priced auction transactions |

**ISO mechanics:**
- Sender marks order as ISO
- Simultaneously routes orders to all better-priced protected quotes
- Allows execution at intended venue at ISO price

### Rule 610 - Access to Quotations

**Access fee cap:** Maximum $0.003 per share for accessing protected quotations.

**Purpose:** Ensure quotes are genuinely accessible; prevent prohibitive access fees that undermine price protection.

**Locked/crossed market prohibition:** Rules against quoting at or through the NBBO without immediately routing.

**2024 amendments:** SEC proposed reducing access fee cap and narrowing tick sizes. Implementation ongoing.

### Rule 606 - Order Routing Disclosure

**Quarterly disclosure requirements:**

For non-directed orders:
- Identity of top 10 venues receiving order flow
- Payment for order flow amounts
- Profit sharing arrangements
- Description of routing relationships

**Format:** Publicly available on broker websites.

### Rule 605 - Execution Quality Disclosure

**Monthly execution quality statistics:**

| Metric | Description |
|--------|-------------|
| Effective spread | Actual execution price vs midpoint |
| Quoted spread | NBBO spread at order receipt |
| Price improvement | Percent receiving better than NBBO |
| Fill rate | Percent of orders filled |
| Speed | Time to execution |

**2024 updates:** Modernized to include:
- Odd-lot orders
- Fractional shares
- More granular size buckets
- Short sale indicator

### Rule 612 - Sub-Penny Rule

**Prohibition:** Cannot accept, rank, or display quotations in NMS stocks priced >= $1.00 in increments less than $0.01.

**Exception:** Stocks priced < $1.00 may quote in $0.0001 increments.

**Midpoint exception:** Sub-penny executions permitted at actual midpoint of NBBO.

**2024 amendments:** SEC adopted variable tick sizes based on trading characteristics. Narrower ticks for liquid stocks.

## NMS Plan Structure

### SIP Plans

| Plan | Coverage | Tape |
|------|----------|------|
| CTA/CQ Plan | NYSE-listed, regional | Tape A, B |
| UTP Plan | Nasdaq-listed | Tape C |

### Governance

Plans governed by participating exchanges. Revenue sharing based on quoting/trading activity.

## Reg NMS Modernization (2024-2025)

### Adopted Changes

**Rule 605 updates:**
- Expanded coverage (odd-lots, fractional)
- More granular reporting
- Improved comparability

**Tick size reform:**
- Variable ticks based on spread/volume metrics
- Narrower ticks for liquid stocks
- Wider ticks possible for illiquid

**Access fee reform:**
- Reduced caps considered
- Tied to tick size

### Under Consideration

**Rule 611 reconsideration:**
- SEC Chair Atkins historically opposed Rule 611
- Roundtable held December 2024
- Potential rescission or modification

**Rationale for review:**
- Market complexity increased
- 17+ exchanges (vs 8 in 2005)
- Order routing costs
- Internalization patterns

## Official Sources

**SEC Reg NMS materials:**
- Adopting release: https://www.sec.gov/files/rules/final/34-51808.pdf
- Rule 611 spotlight: https://www.sec.gov/spotlight/emsac/memo-rule-611-regulation-nms.pdf
- Rule 611 FAQ: https://www.sec.gov/divisions/marketreg/rule611faq.pdf

**CFR citations:**
- 17 CFR 242.600 - Definitions
- 17 CFR 242.610 - Access rule
- 17 CFR 242.611 - Order protection
- 17 CFR 242.612 - Sub-penny rule

**eCFR link:** https://www.ecfr.gov/current/title-17/chapter-II/part-242

## Quant Implications

### For Execution Models

- Route optimization must respect 611 constraints
- ISO usage enables aggressive execution
- Access fee cap affects maker-taker economics
- Tick size changes affect queue dynamics

### For Research

- 605 data provides execution quality benchmarks
- 606 data reveals routing patterns and PFOF
- Regime changes (tick size, fee caps) are structural breaks

### For Compliance

- Trade-through monitoring required
- ISO documentation needed
- Best execution policies must incorporate Reg NMS

## Key Dates

| Date | Event |
|------|-------|
| June 2005 | Reg NMS adopted |
| March 2007 | Rule 611 compliance deadline |
| 2024 | Rule 605 modernization adopted |
| 2024 | Tick size/fee cap reforms adopted |
| Dec 2024 | Rule 611 roundtable |
| 2025+ | Potential 611 changes |
