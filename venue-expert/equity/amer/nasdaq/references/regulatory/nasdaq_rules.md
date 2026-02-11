# Nasdaq Rulebook References

Key Nasdaq rules governing trading, market data, and exchange operations.

## Rulebook Structure

Nasdaq rules organized in series:

| Series | Coverage |
|--------|----------|
| General | Definitions, membership |
| Equity 1-3 | Membership, fees |
| Equity 4 | Trading rules |
| Equity 5 | Order types |
| Equity 6 | Quotation requirements |
| Equity 7 | Market data |
| Listing Rules | Listing standards |

**Official source:** https://listingcenter.nasdaq.com/rulebook/nasdaq/rules

## Equity 4 - Trading Rules

### Rule 4751 - Definitions

Key definitions for trading:
- Order types
- Time-in-force
- Display instructions
- Trade conditions

### Rule 4752 - Order Entry

Requirements for order entry:
- Order attributes
- Validation rules
- Rejection conditions

### Rule 4753 - Nasdaq Opening Cross

Defines opening auction:

**Order types eligible:**
- MOO (Market-on-Open)
- LOO (Limit-on-Open)
- IO (Imbalance Only)
- Regular limit orders

**Cutoffs:**
- 9:28 AM: MOO entry cutoff
- 9:30 AM: Cross execution

**Price determination:**
- Maximize shares executed
- Minimize imbalance
- Minimize distance from reference

### Rule 4754 - Nasdaq Closing Cross

Defines closing auction:

**Order types eligible:**
- MOC (Market-on-Close)
- LOC (Limit-on-Close)
- IO (Imbalance Only)
- Regular limit orders

**Cutoffs:**
- 3:55 PM: MOC entry cutoff
- 3:58 PM: LOC entry cutoff
- 4:00 PM: Cross execution

**NOII dissemination:**
- Starts 3:50 PM
- Every second until close

### Rule 4755 - Halt Cross

Reopening after trading halts:
- Accumulation period
- Price discovery process
- Price collars (2025 updates)

**2025 Price Protections:**
- Initial 5-minute display period
- Price collars applied
- Widening if outside bounds

### Rule 4756 - Odd Lot Orders

Handling of orders < 100 shares:
- May participate in crosses
- Quote eligibility (modernization)
- Execution priority

### Rule 4757 - Book Processing

Order book mechanics:
- Price-time priority
- Display vs non-displayed
- Reserve order handling

## Equity 5 - Order Types

### Standard Order Types

| Type | Rule | Behavior |
|------|------|----------|
| Market | 4751(a) | Immediate at best price |
| Limit | 4751(a) | At limit or better |
| Pegged | 4751(f) | Track reference price |
| Reserve | 4751(g) | Hidden size |
| Midpoint | 4751(f) | Midpoint of NBBO |

### Time-in-Force

| TIF | Duration |
|-----|----------|
| Day | Until 4:00 PM |
| IOC | Immediate or cancel |
| GTC | Until executed/canceled |
| GTX | Until extended hours end |
| System Hours | 4:00 AM - 8:00 PM |
| Market Hours | 9:30 AM - 4:00 PM |

### Display Instructions

| Instruction | Behavior |
|-------------|----------|
| Displayed | Visible in book |
| Non-Displayed | Hidden |
| Post-Only | Add only, no take |
| Attributable | Show MPID |

## Equity 6 - Quotation Requirements

### Market Maker Obligations

Registered market makers must:
- Maintain two-sided quotes
- Honor minimum sizes
- Meet continuous quoting requirements

### Quote Sizes

Minimum quote sizes vary by:
- Security tier
- Price level
- Market conditions

### Quote Update Requirements

- Maximum spread requirements
- Time-in-force minimums
- Away market compliance

## Equity 7 - Market Data

### Rule 7014 - TotalView

TotalView-ITCH specifications:
- Data content
- Message types
- Dissemination rules

### Rule 7015 - NOII

Net Order Imbalance Indicator:
- Content specification
- Dissemination schedule
- Usage restrictions

### Rule 7016 - Basic Data

Nasdaq Basic specifications:
- Top-of-book only
- Last sale
- Licensing requirements

## Halt Codes

### Trading Halts

| Code | Reason |
|------|--------|
| T1 | News pending |
| T2 | News released |
| T5 | Single stock trading pause (LULD) |
| T6 | Extraordinary market activity |
| T8 | ETF NAV not available |
| T12 | Additional info requested by Nasdaq |

### Regulatory Halts

| Code | Reason |
|------|--------|
| H1 | SEC trading suspension |
| H2 | Listing not current |
| H4 | Non-compliance |
| H9 | Not current in SEC filings |
| H10 | SEC trading suspension (10-day) |
| H11 | SEC trading suspension (settled) |

### LULD Codes

| Code | Meaning |
|------|---------|
| LUDP | LULD pause |
| LUDS | LULD straddle |

## Recent Rule Changes

### 2024-2025 Updates

**Halt Cross Price Protections (SR-NASDAQ-2024-065):**
- Price collars for halt reopenings
- Widening mechanism
- Approved February 2025

**NOII/EOII Terminology:**
- Formal definitions added
- Alternative terms recognized

**Hybrid Closing Cross:**
- Optional mechanism
- Additional flexibility

## Compliance Considerations

### Order Entry

- Validate order types against rules
- Check time-in-force validity
- Ensure display instruction compliance

### Execution

- Handle crosses correctly
- Process halts appropriately
- Report trades timely

### Market Making

- Meet quoting obligations
- Maintain minimum sizes
- Honor displayed quotes

## Official Resources

**Nasdaq Rulebook:**
- https://listingcenter.nasdaq.com/rulebook/nasdaq/rules

**Trader Resources:**
- https://www.nasdaqtrader.com/

**Rule Filings:**
- https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&company=nasdaq&type=SR&dateb=&owner=include&count=40

## Quant Implications

### Order Type Selection

Choose based on:
- Execution objective
- Cost considerations
- Information leakage

### Auction Participation

Understand rules for:
- Entry cutoffs
- Order type eligibility
- Price determination

### Data Usage

Know restrictions on:
- Market data redistribution
- Derived data products
- Display requirements
