# Crypto Markets - Asset Class Fundamentals

## Overview

Cryptocurrency markets facilitate trading of digital assets on blockchain-based networks. Unlike traditional markets, crypto operates 24/7/365 across centralized exchanges (CEX) and decentralized protocols (DEX).

## Market Structure Types

### Centralized Exchanges (CEX)

Traditional order book model:
- Custodial - exchange holds assets
- Central limit order book (CLOB)
- Maker/taker fee structure
- KYC/AML requirements (most jurisdictions)

Examples: Binance, Coinbase, Kraken, OKX, Bybit

### Decentralized Exchanges (DEX)

On-chain trading mechanisms:
- Non-custodial - users control keys
- Automated Market Makers (AMM) - liquidity pools
- Order books (on-chain or hybrid)
- No KYC (pseudonymous)

Examples: Uniswap, dYdX, GMX, Curve

### Hybrid Models

Combining CEX speed with DEX custody:
- Off-chain matching, on-chain settlement
- Self-custody with central order book
- Layer 2 solutions for speed

## Common Market Structures

### Order Book (CEX)

Similar to traditional equity markets:
- Price-time priority (typically)
- Limit and market orders
- Iceberg/reserve orders
- Stop orders

### Automated Market Makers (DEX)

Algorithmic pricing via bonding curves:
- Constant product: x * y = k (Uniswap v2)
- Concentrated liquidity (Uniswap v3)
- Stable swap curves (Curve)
- Virtual AMM (perpetuals)

## Trading Sessions

**24/7 Operation:**
- No market open/close
- No circuit breakers (most venues)
- Maintenance windows (often unannounced)
- Funding rate settlements (derivatives, typically 8h)

## Instrument Types

| Type      | Description                                  |
|-----------|----------------------------------------------|
| Spot      | Direct asset exchange (BTC/USDT)             |
| Perpetual | Futures without expiry, funding rate mechanism |
| Futures   | Fixed expiry contracts                       |
| Options   | Calls/puts on crypto assets                  |
| Margin    | Leveraged spot trading                       |

## Quant Relevance

### Why Microstructure Matters

**Cross-exchange arbitrage** - Price discrepancies exploitable across venues. Latency and fee structure critical.

**Funding rate signals** - Perp funding rates indicate market sentiment and positioning.

**Liquidity fragmentation** - Volume spread across many venues. Aggregation necessary for execution.

**On-chain data** - Blockchain provides transparency unavailable in traditional markets (wallet flows, DEX trades).

### Key Metrics

| Metric        | Definition                                     |
|---------------|------------------------------------------------|
| Spread        | Ask minus bid (varies wildly by pair/venue)    |
| Depth         | Size at each level (often thin)                |
| Funding Rate  | Periodic payment between longs/shorts (perps)  |
| Open Interest | Total outstanding derivative positions         |
| Volume        | Often inflated by wash trading                 |

## Data Quality Concerns

**Universal issues:**
- Wash trading inflates volume
- Timestamp accuracy varies
- Exchange-reported vs calculated metrics differ
- API rate limits affect completeness

**CEX-specific:**
- WebSocket disconnections corrupt order book
- Sequence gaps require resync
- No built-in checksums (most exchanges)

**DEX-specific:**
- Block time affects "real-time" data
- MEV affects execution
- Gas costs affect small trades

## Known Gotchas

1. **Stablecoin depegs** - "USD" pairs aren't actually USD
2. **Liquidation cascades** - Self-reinforcing, extreme moves
3. **Exchange insolvency** - Counterparty risk (FTX, etc.)
4. **Regulatory actions** - Sudden delistings, geo-blocks
5. **Chain congestion** - Affects DEX execution and withdrawals
6. **Hard forks** - Asset duplication, replay attacks

## Global Landscape

**Major CEX by region:**
- Global: Binance, OKX, Bybit
- US: Coinbase, Kraken
- Asia: Upbit (Korea), bitFlyer (Japan)

**Major DEX by chain:**
- Ethereum: Uniswap, Curve, dYdX
- Solana: Jupiter, Raydium
- Arbitrum: GMX, Camelot

See category-specific files (CEX, DEX) for detailed coverage.
