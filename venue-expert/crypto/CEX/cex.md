# Centralized Exchanges (CEX) - Category Fundamentals

CEX-specific market microstructure. Assumes familiarity with crypto concepts from `crypto.md`.

## Overview

Centralized exchanges operate traditional order book infrastructure for crypto assets. They provide:
- Custodial services (exchange holds assets)
- Matching engine (CLOB)
- Fiat on/off ramps
- Derivatives products

## Common Architecture

### Order Book Mechanics

**Price-Time Priority:**
Most CEX use standard price-time:
1. Better price wins
2. Earlier order wins at same price

**Order Types (common across CEX):**

| Type        | Behavior                                  |
|-------------|-------------------------------------------|
| Limit       | Execute at limit or better                |
| Market      | Execute immediately at best available     |
| Stop-Limit  | Trigger limit order at stop price         |
| Stop-Market | Trigger market order at stop price        |
| Post-Only   | Add liquidity only; cancel if would take  |
| IOC         | Immediate-or-Cancel                       |
| FOK         | Fill-or-Kill (entire quantity or nothing) |

### Data Feeds

**WebSocket Streams:**
- Order book snapshots and incremental updates
- Trade feeds
- Ticker/24h stats
- User order updates (authenticated)

**REST API:**
- Historical data
- Account management
- Order placement (backup)

**Common patterns:**
- Incremental book updates require local reconstruction
- Sequence numbers for gap detection
- Periodic snapshots for validation

## Fee Structure

### Maker-Taker Model

| Role                     | Typical Range  |
|--------------------------|----------------|
| Maker (add liquidity)    | 0.00% - 0.10%  |
| Taker (remove liquidity) | 0.03% - 0.10%  |

**VIP tiers:** Volume-based discounts common.

**Token discounts:** Many exchanges offer fee reduction for holding/paying with native token.

### Hidden Costs

- Withdrawal fees (often significant)
- Funding rates (perpetuals)
- Liquidation penalties
- Spread (illiquid pairs)

## Rate Limiting

### Common Patterns

**Weight-based:** Each endpoint has a weight; total weight limited per time window.

**Request-based:** Simple request count per time window.

**IP vs Account:** Limits may apply per IP, per account, or both.

Enforcement varies by exchange (429 → temporary ban → extended ban). See exchange-specific files for exact limits and escalation policies.

## Data Quality Issues

### WebSocket Reliability

CEX WebSocket feeds require local order book reconstruction from incremental updates. Core pattern: heartbeat monitoring → exponential backoff reconnect → full snapshot resync → sequence validation.

Missed updates corrupt the local book state. Checksum support varies by exchange (OKX, Kraken: CRC32; Binance: none). See exchange-specific files for reconstruction protocols and validation approaches.

## Trading Hours

**24/7 Operation:**
- No session boundaries
- No circuit breakers
- Maintenance windows (often unannounced, typically Sunday UTC)

**Funding rate settlements (derivatives):**
- Typically every 8 hours
- 00:00, 08:00, 16:00 UTC common
- Creates predictable flow patterns

## Instrument Naming

### Spot Pairs

Common conventions:
- `BTC/USDT`, `BTCUSDT`, `BTC-USDT` (varies by exchange)
- Base/Quote ordering
- Stablecoin pairs dominate volume

### Perpetuals

Common suffixes:
- `BTCUSDT_PERP`, `BTC-USDT-PERPETUAL`, `BTCUSD_PERP`
- Linear (quote-settled) vs Inverse (base-settled)

## Cross-Exchange Considerations

### Arbitrage

**Latency sources:**
- Geographic distance to matching engine
- API processing time
- Withdrawal/deposit confirmation times

**Fee impact:**
- Taker fees on both legs
- Withdrawal fees
- Potential slippage

### Aggregation

For execution:
- Normalize order book formats
- Align timestamps
- Account for fee differences
- Handle partial fills across venues

## Known Gotchas

1. **Maintenance windows** - Often unannounced, break connections
2. **Symbol renames** - Break historical continuity (LUNA→LUNC)
3. **Delistings** - 24-48h notice affects data availability
4. **API versioning** - Breaking changes with limited notice
5. **Testnet ≠ Production** - Data quality differs significantly
6. **Regional restrictions** - Geo-blocking, different limits
7. **Wash trading** - Reported volume unreliable
8. **Liquidation cascades** - Extreme microstructure during events

## Exchange Comparison

| Exchange | Spot Depth | Update Freq | Checksum | Notes                  |
|----------|------------|-------------|----------|------------------------|
| Binance  | 5000       | 100ms       | No       | Largest volume         |
| Bybit    | 500        | 20ms        | No       | Fast updates           |
| OKX      | 400        | 100ms       | CRC32    | Has checksum           |
| Kraken   | L2/L3      | 10ms        | CRC32    | Microsecond timestamps |
| Coinbase | Full       | 50ms        | No       | US-focused             |

See exchange-specific files for detailed mechanics.
