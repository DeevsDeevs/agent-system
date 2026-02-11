# Equity Markets - Asset Class Fundamentals

## Overview

Equity markets facilitate trading of ownership stakes in corporations. These markets serve critical functions in capital formation, price discovery, and risk transfer.

## Role in Capital Markets

**Primary market:** Companies raise capital through IPOs and secondary offerings. Investment banks underwrite and distribute shares to investors.

**Secondary market:** Investors trade existing shares. Liquidity in secondary markets affects primary market pricing and corporate cost of capital.

## Common Market Structures

### Central Limit Order Book (CLOB)

Most equity markets use CLOBs where:
- Orders queue by price level
- Within a price level, priority rules determine execution order
- Typical priority: price-time (first-in-first-out at each price)

### Quote-Driven vs Order-Driven

| Model | Description | Example |
|-------|-------------|---------|
| Order-driven | Orders match directly in CLOB | Most modern exchanges |
| Quote-driven | Dealers post two-sided quotes | Historical OTC markets |
| Hybrid | Combines both mechanisms | NYSE specialists (historical) |

## Price-Time Priority

The dominant matching rule in equity markets:

1. **Price priority** - Better-priced orders execute first
2. **Time priority** - At same price, earlier orders execute first

Variations exist:
- Pro-rata allocation (some futures markets)
- Size priority (rare)
- Random allocation (some dark pools)

## Order Types

### Basic Orders

| Type | Behavior |
|------|----------|
| Market | Execute immediately at best available price |
| Limit | Execute at specified price or better |
| Stop | Trigger market order when price reached |
| Stop-limit | Trigger limit order when price reached |

### Extended Order Types

Exchanges define additional order types for specific use cases:
- Reserve/iceberg - Display partial size
- Pegged - Track reference price (midpoint, NBBO)
- Auction-only - Participate only in crosses

## Trading Sessions

Typical equity market sessions:

| Session | Characteristics |
|---------|-----------------|
| Pre-market | Limited liquidity, wider spreads |
| Opening auction | Price discovery, concentrated volume |
| Continuous trading | Standard CLOB matching |
| Closing auction | Major volume concentration, index rebalancing |
| After-hours | Limited liquidity, wider spreads |

## Quant Relevance

### Why Microstructure Matters

**Execution quality** - Transaction costs directly impact strategy returns. Understanding venue mechanics enables better execution.

**Alpha signals** - Order flow and microstructure data contain predictive information. Queue dynamics, imbalances, and trade patterns inform short-horizon signals.

**Risk management** - Liquidity conditions affect position sizing and exit costs. Halt and circuit breaker behavior matters for risk models.

### Key Metrics

| Metric | Definition |
|--------|------------|
| Spread | Ask price minus bid price |
| Depth | Size available at each price level |
| Turnover | Volume relative to shares outstanding |
| Volatility | Price variation over time |

## Global Equity Markets

Major markets by region:

**Americas:** NYSE, Nasdaq, TSX, B3
**EMEA:** LSE, Euronext, Deutsche Borse, SIX
**APAC:** TSE, HKEX, SSE, SZSE, ASX, SGX

Each jurisdiction has distinct:
- Regulatory frameworks
- Market structure rules
- Trading hours
- Settlement conventions

See geography-specific files for detailed coverage.
