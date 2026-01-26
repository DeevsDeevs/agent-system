# Futures Markets - Asset Class Fundamentals

## Overview

Futures are standardized derivative contracts obligating counterparties to transact an underlying asset at a predetermined price on a future date. Exchanges provide standardization, central clearing, and price discovery.

## Futures vs Forwards

| Attribute | Futures | Forwards |
|-----------|---------|----------|
| Standardization | Exchange-defined terms | Customizable |
| Trading venue | Exchange | OTC bilateral |
| Counterparty risk | CCP-cleared | Direct exposure |
| Margin | Daily mark-to-market | Typically at maturity |
| Liquidity | Centralized, transparent | Fragmented |
| Regulation | Exchange/CFTC/local | Varies |

**Key insight:** Standardization sacrifices flexibility for liquidity and credit risk mitigation.

## Settlement Types

### Physical Delivery

Contract holder takes/makes delivery of underlying asset:
- Agricultural commodities (grain, livestock)
- Energy (crude oil, natural gas)
- Metals (gold, copper)

Delivery involves warehouse receipts, quality grades, delivery points.

### Cash Settlement

Final settlement by cash difference:
- Index futures (S&P 500, equity indices)
- Interest rate futures
- Most financial futures

Settlement price typically derived from spot market reference.

**Gotcha:** Physical delivery contracts require careful position management near expiry to avoid unintended delivery.

## Margin Mechanics

### Initial Margin

Collateral posted when opening position:
- Set by exchange/CCP
- Typically 3-15% of notional value
- Based on historical volatility and stress scenarios
- Higher for concentrated positions

### Maintenance Margin

Minimum margin level to keep position open:
- Usually 75-80% of initial margin
- Breach triggers margin call

### Variation Margin

Daily profit/loss settlement:
- Calculated from daily settlement price
- Cash flows daily between counterparties via CCP
- Realized immediately, not accrued

**Mark-to-market example:**
```
Day 1: Buy 1 contract at 100
Day 2: Settlement price = 102 -> Receive (102-100) x multiplier
Day 3: Settlement price = 99 -> Pay (102-99) x multiplier
```

## Daily Settlement

Futures P&L is realized daily:
1. Exchange determines settlement price (various methods)
2. CCP calculates net position value change
3. Cash transfers occur before next session
4. This eliminates credit risk accumulation

**Quant implication:** Daily settlement creates cash flow drag/benefit vs forward pricing. The difference is the convexity adjustment.

## Contract Specifications

Key terms defined by exchange:

| Element | Description |
|---------|-------------|
| Underlying | Asset or index |
| Contract size | Notional amount per contract |
| Tick size | Minimum price increment |
| Tick value | P&L per tick |
| Expiry months | Which months trade |
| Last trading day | Final trade date |
| Settlement method | Physical or cash |

## Roll Conventions

### Calendar Spreads

Simultaneous long/short in different expiry months. Used for:
- Rolling positions forward
- Expressing term structure views
- Reducing margin vs outright positions

### Roll Period

When most open interest migrates from front to next month:
- Timing varies by product
- Index futures: typically week before expiry
- Commodities: varies by delivery logistics

**Gotcha:** Roll dynamics create predictable patterns in volume, spread, and price.

## Price Discovery

Futures markets often lead spot price discovery:
- Lower transaction costs
- Leverage enables capital efficiency
- Continuous trading vs fragmented spot
- Information aggregation

**Basis** = Spot Price - Futures Price

Basis converges to zero at expiry. Deviations create arbitrage opportunities.

## Key Metrics

| Metric | Definition | Significance |
|--------|------------|--------------|
| Open interest | Outstanding contracts | Market depth, positioning |
| Volume | Contracts traded | Liquidity, activity |
| Basis | Spot - Futures | Cost of carry, arbitrage |
| Term structure | Prices across expiries | Contango/backwardation |
| Implied vol | Options-derived volatility | Market expectation |

### Contango vs Backwardation

| Structure | Definition | Typical Cause |
|-----------|------------|---------------|
| Contango | Far month > Near month | Storage costs, financing |
| Backwardation | Near month > Far month | Supply shortage, convenience yield |

## Quant Relevance

### Why Microstructure Matters

**Execution:** Spread, depth, and queue dynamics affect fill quality. Roll periods have distinct liquidity characteristics.

**Signals:** Order flow, basis movements, term structure shifts contain predictive information.

**Risk:** Margin calls create forced liquidation. Understanding clearing mechanics prevents operational surprises.

### Common Gotchas

1. **Contract continuity** - Building continuous series requires roll adjustment decisions
2. **Notional vs contracts** - Size positions in notional, not contract count
3. **Settlement time** - Varies by exchange; affects end-of-day calculations
4. **Margin efficiency** - Cross-margining reduces capital requirements
5. **Delivery risk** - Physical contracts require active roll management

See geography-specific files for detailed coverage.
