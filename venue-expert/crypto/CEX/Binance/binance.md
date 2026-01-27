# Binance Exchange Mechanics

Binance-specific market microstructure. Assumes familiarity with CEX concepts from `cex.md`.

## Overview and Role

### Binance as Operator

Binance operates multiple platforms:

| Platform        | Description                    | API Base                             |
|-----------------|--------------------------------|--------------------------------------|
| Binance Global  | Main platform (non-US)         | api.binance.com                      |
| Binance.US      | US-regulated entity            | api.binance.us                       |
| Binance Futures | USDT-M and COIN-M derivatives  | fapi.binance.com / dapi.binance.com  |
| Binance Options | European-style options         | eapi.binance.com                     |

**Critical:** Binance.US has separate API with different rate limits, symbols, and features.

### Market Position

- Largest crypto exchange by volume (spot and derivatives)
- Primary price discovery venue for many pairs
- BNB native token for fee discounts

## Data Characteristics

### Update Frequency

WebSocket depth streams support configurable intervals:

| Stream Suffix | Frequency                          |
|---------------|------------------------------------|
| `@100ms`      | 100 milliseconds                   |
| `@250ms`      | 250 milliseconds (default)         |
| `@500ms`      | 500 milliseconds                   |
| `@1000ms`     | 1 second                           |

**Note:** `@0ms` theoretically real-time but dynamically degraded under load.

### Order Book Depth

| Endpoint/Stream     | Max Levels          |
|---------------------|---------------------|
| REST snapshot       | 5000 per side       |
| WebSocket diff      | Incremental updates |
| Partial book stream | 5, 10, 20 levels    |

**Gotcha:** Depth beyond 5000 levels not visible without reconstructing from diffs.

### Timestamps

- Unix milliseconds (server time)
- Sync client clock via `GET /api/v3/time`
- Server time in response headers: `Date` and custom headers

### Connection Limits

| Limit Type             | Value                        |
|------------------------|------------------------------|
| Streams per connection | 1024 (Spot), 200 (Futures)   |
| Connections per 5 min  | 300 per IP                   |
| Inbound messages       | 5/sec (Spot), 10/sec (Futures) |

## Order Book Mechanics

### Matching Engine

**Price-Time Priority:**
Standard CLOB - price first, then time at same price level.

### Order Types

**Basic Types:**

| Type               | API Value            | Behavior                               |
|--------------------|----------------------|----------------------------------------|
| Limit              | `LIMIT`              | Execute at limit or better             |
| Market             | `MARKET`             | Immediate execution                    |
| Stop-Limit         | `STOP_LOSS_LIMIT`    | Trigger limit at stop price            |
| Stop-Market        | `STOP_LOSS`          | Trigger market at stop price           |
| Take-Profit-Limit  | `TAKE_PROFIT_LIMIT`  | Limit order triggered by profit target |
| Take-Profit-Market | `TAKE_PROFIT`        | Market order triggered by profit target |

**Time-in-Force:**

| TIF | Behavior                      |
|-----|-------------------------------|
| GTC | Good-Til-Canceled (default)   |
| IOC | Immediate-or-Cancel           |
| FOK | Fill-or-Kill                  |
| GTX | Post-Only (Good-Til-Crossing) |

**Advanced Types (Futures):**

| Type          | Description                            |
|---------------|----------------------------------------|
| Trailing Stop | Dynamic stop that follows price        |
| TWAP          | Time-weighted execution (institutional) |

### Self-Trade Prevention

Not exposed as configurable STP modifiers like traditional exchanges. Self-trades may execute.

## Rate Limiting

### Weight-Based System

Each endpoint has an assigned weight. Total weight is limited per time window.

**Spot API limits:**

| Limit          | Window     | Weight         |
|----------------|------------|----------------|
| Request weight | 1 minute   | 1200 (default) |
| Orders         | 10 seconds | 100            |
| Orders         | 24 hours   | 200,000        |

**Headers to monitor:**
- `X-MBX-USED-WEIGHT-1M` - Current weight used
- `X-MBX-ORDER-COUNT-10S` - Orders in 10s window
- `X-MBX-ORDER-COUNT-1D` - Orders in 24h window

### Ban Escalation

| Violation       | Consequence                              |
|-----------------|------------------------------------------|
| 429 response    | Temporary block, backoff required        |
| Repeated 429s   | 2 minute IP ban                          |
| Continued abuse | Escalating bans up to 3 days             |
| 418 response    | IP banned - check `Retry-After` header   |

**Recovery:** Wait duration from `Retry-After` header. Do not retry during ban.

## Market Data Feeds

### WebSocket Streams

**Depth Streams:**

| Stream                 | Content                            |
|------------------------|------------------------------------|
| `<symbol>@depth`       | Diff depth stream (1000ms default) |
| `<symbol>@depth@100ms` | Diff depth stream (100ms)          |
| `<symbol>@depth5`      | Partial book (5 levels)            |
| `<symbol>@depth10`     | Partial book (10 levels)           |
| `<symbol>@depth20`     | Partial book (20 levels)           |

**Trade Streams:**

| Stream              | Content           |
|---------------------|-------------------|
| `<symbol>@trade`    | Real-time trades  |
| `<symbol>@aggTrade` | Aggregated trades |

**Ticker Streams:**

| Stream               | Content                 |
|----------------------|-------------------------|
| `<symbol>@ticker`    | 24h rolling window stats |
| `<symbol>@miniTicker`| Simplified ticker       |
| `<symbol>@bookTicker`| Best bid/ask updates    |

### Book Reconstruction

**Diff Depth Protocol:**

1. Open WebSocket to `<symbol>@depth@100ms`
2. Buffer incoming events
3. Get REST snapshot: `GET /api/v3/depth?symbol=X&limit=5000`
4. Drop buffered events where `u` <= `lastUpdateId` from snapshot
5. First processed event: `U` <= `lastUpdateId+1` AND `u` >= `lastUpdateId+1`
6. Each subsequent event: `U` = previous `u` + 1

**Fields:**
- `U` - First update ID in event
- `u` - Final update ID in event
- `lastUpdateId` - Snapshot's last update ID

**Gotcha:** Sequence gap = corrupted book. Must re-snapshot.

### No Built-in Checksum

Unlike some exchanges (Kraken, OKX), Binance does not provide order book checksums.

**Validation alternatives:**
- Periodic REST snapshot comparison
- Cross-venue price sanity check
- Spread reasonableness check

## Fee Structure

### Spot Fees

**Standard rates:**

| Role  | Fee     |
|-------|---------|
| Maker | 0.1000% |
| Taker | 0.1000% |

**BNB discount:** 25% off when paying fees in BNB.

**VIP tiers:** Volume-based discounts:

| VIP Level | 30d Volume (BTC) | Maker   | Taker   |
|-----------|------------------|---------|---------|
| VIP 0     | < 250            | 0.1000% | 0.1000% |
| VIP 1     | >= 250           | 0.0900% | 0.1000% |
| VIP 2     | >= 1,000         | 0.0800% | 0.1000% |
| ...       | ...              | ...     | ...     |
| VIP 9     | >= 150,000       | 0.0200% | 0.0400% |

### Futures Fees

Lower than spot:

| Role  | USDT-M  | COIN-M  |
|-------|---------|---------|
| Maker | 0.0200% | 0.0100% |
| Taker | 0.0400% | 0.0500% |

## Data Quality Concerns

### Dynamic Frequency Degradation

`@0ms` streams may be throttled during high load. 100ms is more reliable.

### Symbol Renames

Historical continuity breaks on renames:
- `LUNA` → `LUNC` (May 2022)
- Various rebrandings

**Mitigation:** Track symbol changes via exchange announcements.

### Depth Snapshot Limitations

REST snapshot limited to 5000 levels. Deep book beyond this requires:
- Continuous diff accumulation
- Accepting incomplete view

### Delisting Impact

24-48 hours before delisting:
- Liquidity decreases
- Spreads widen
- Data may become unreliable

## Futures-Specific Mechanics

### Funding Rate

**Settlement:** Every 8 hours (00:00, 08:00, 16:00 UTC)

**Calculation:**
```
Funding Rate = Premium Index + clamp(Interest Rate - Premium Index, -0.05%, 0.05%)
```

**Impact:**
- Positive rate: longs pay shorts
- Negative rate: shorts pay longs
- Creates predictable flow near settlement

### Mark Price

Used for liquidations and unrealized PnL:
- Based on index price + funding basis
- Prevents manipulation via spot price spikes
- Different from last traded price

### Liquidation

**Tiers:** Position size determines maintenance margin requirement.

**Insurance Fund:** Absorbs losses from bankrupt positions.

**ADL (Auto-Deleveraging):** When insurance fund insufficient, profitable positions force-closed.

## API Endpoints Reference

### Key REST Endpoints

| Endpoint             | Method | Description          |
|----------------------|--------|----------------------|
| `/api/v3/depth`      | GET    | Order book snapshot  |
| `/api/v3/trades`     | GET    | Recent trades        |
| `/api/v3/klines`     | GET    | Candlestick data     |
| `/api/v3/ticker/24hr`| GET    | 24h statistics       |
| `/api/v3/order`      | POST   | Place order          |
| `/api/v3/openOrders` | GET    | Current open orders  |

### WebSocket Base URLs

| Environment    | URL                                |
|----------------|------------------------------------|
| Spot           | `wss://stream.binance.com:9443/ws` |
| Spot (backup)  | `wss://stream.binance.com:443/ws`  |
| Futures USDT-M | `wss://fstream.binance.com/ws`     |
| Futures COIN-M | `wss://dstream.binance.com/ws`     |

## Gotchas Checklist

1. **Sequence gaps** - Require full resync; no recovery mechanism
2. **No checksum** - Must validate via REST snapshots
3. **Weight limits** - Shared between REST and WebSocket API calls
4. **Binance.US ≠ Binance** - Completely separate API
5. **Testnet quality** - Data differs significantly from production
6. **Delisting window** - Data unreliable 24-48h before removal
7. **Status 418** - IP banned; must wait `Retry-After` duration
8. **Symbol case** - API expects uppercase (`BTCUSDT`, not `btcusdt`)
9. **Timestamp sync** - Required for signed requests; use server time
10. **Funding settlements** - Predictable flow every 8h
11. **Stream limits** - 1024 streams max per connection
12. **Connection limits** - 300 new connections per 5 min per IP
13. **Message rate** - 5 inbound msg/sec limit (Spot)
14. **Order book depth** - Max 5000 levels via REST

## Implementation Notes

### Connection Management

**Recommended pattern:**
```
1. Maintain persistent WebSocket connections
2. Implement heartbeat monitoring (no activity = potential disconnect)
3. Use multiple connections for many symbols
4. Implement exponential backoff for reconnection
5. Always resync book state after reconnect
```

### Order Book Maintenance

**Recommended pattern:**
```
1. Subscribe to depth@100ms stream
2. Buffer events
3. Fetch REST snapshot
4. Apply buffered events with sequence validation
5. Continue applying real-time events
6. Periodically validate against REST snapshot
7. On sequence gap: full resync
```

### Clock Synchronization

For signed requests:
```
1. Fetch server time: GET /api/v3/time
2. Calculate offset: server_time - local_time
3. Apply offset to request timestamps
4. Re-sync periodically (drift occurs)
```

## References

See `references/` directory:
- `specs/websocket_api.md` - WebSocket API specification
- `specs/rest_api.md` - REST API specification
- `specs/futures_api.md` - Futures-specific endpoints
- `regulatory/terms_of_service.md` - Platform rules
