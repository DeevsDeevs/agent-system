# Binance WebSocket API Specification

Deep technical reference for Binance WebSocket market data and user data streams.

## Overview

Binance provides WebSocket connections for real-time market data and user account updates. Three primary stream categories exist:

| Category       | Purpose                    | Authentication |
|----------------|----------------------------|----------------|
| Market Streams | Public order book, trades  | None           |
| User Streams   | Orders, balances, positions| Listen key     |
| Combined       | Multiple streams per conn  | Varies         |

## Connection Endpoints

### Spot

| Environment | Base URL                              | Port |
|-------------|---------------------------------------|------|
| Production  | `wss://stream.binance.com`            | 9443 |
| Backup      | `wss://stream.binance.com`            | 443  |
| Testnet     | `wss://testnet.binance.vision`        | 443  |

### Futures USDT-Margined

| Environment | Base URL                              |
|-------------|---------------------------------------|
| Production  | `wss://fstream.binance.com`           |
| Testnet     | `wss://stream.binancefuture.com`      |

### Futures COIN-Margined

| Environment | Base URL                              |
|-------------|---------------------------------------|
| Production  | `wss://dstream.binance.com`           |
| Testnet     | `wss://dstream.binancefuture.com`     |

## Connection Protocol

### URL Patterns

**Single stream:**
```
wss://stream.binance.com:9443/ws/<streamName>
```

**Combined streams:**
```
wss://stream.binance.com:9443/stream?streams=<stream1>/<stream2>/<stream3>
```

### Connection Limits

| Limit Type                | Spot           | Futures        |
|---------------------------|----------------|----------------|
| Streams per connection    | 1024           | 200            |
| Connections per 5 minutes | 300 per IP     | 300 per IP     |
| Inbound messages/second   | 5              | 10             |
| Max message size          | 4096 bytes     | 4096 bytes     |

### Keepalive

- Connections drop after 24 hours automatically
- Server sends ping frames every 3 minutes
- Client must respond with pong within 10 minutes
- No user-level heartbeat messages required (WebSocket ping/pong sufficient)

### Disconnection Handling

**Reasons for disconnection:**
1. Server maintenance (often unannounced)
2. Client pong timeout (>10 minutes)
3. Rate limit violation
4. Network issues

**Reconnection protocol:**
```
1. Detect disconnection (read error, ping timeout)
2. Wait: min(2^attempt * 100ms, 30000ms)
3. Reconnect to endpoint
4. Resubscribe to streams
5. For order book: full resync required
```

## Market Data Streams

### Aggregate Trade Stream

Real-time aggregated trade updates.

**Stream name:** `<symbol>@aggTrade`

**Update frequency:** Real-time

**Payload:**
```json
{
  "e": "aggTrade",
  "E": 1672515782136,
  "s": "BTCUSDT",
  "a": 164325236,
  "p": "16850.00",
  "q": "0.001",
  "f": 265598345,
  "l": 265598348,
  "T": 1672515782136,
  "m": true,
  "M": true
}
```

| Field | Type   | Description                              |
|-------|--------|------------------------------------------|
| e     | STRING | Event type                               |
| E     | LONG   | Event time (Unix ms)                     |
| s     | STRING | Symbol                                   |
| a     | LONG   | Aggregate trade ID                       |
| p     | STRING | Price                                    |
| q     | STRING | Quantity                                 |
| f     | LONG   | First trade ID                           |
| l     | LONG   | Last trade ID                            |
| T     | LONG   | Trade time (Unix ms)                     |
| m     | BOOL   | Is buyer the maker?                      |
| M     | BOOL   | Ignore (legacy field)                    |

### Trade Stream

Individual trade updates (higher volume than aggTrade).

**Stream name:** `<symbol>@trade`

**Payload:**
```json
{
  "e": "trade",
  "E": 1672515782136,
  "s": "BTCUSDT",
  "t": 265598345,
  "p": "16850.00",
  "q": "0.001",
  "b": 88446532,
  "a": 88446531,
  "T": 1672515782136,
  "m": true,
  "M": true
}
```

| Field | Type   | Description                              |
|-------|--------|------------------------------------------|
| t     | LONG   | Trade ID                                 |
| b     | LONG   | Buyer order ID                           |
| a     | LONG   | Seller order ID                          |

### Kline/Candlestick Stream

**Stream name:** `<symbol>@kline_<interval>`

**Intervals:** 1s, 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M

**Payload:**
```json
{
  "e": "kline",
  "E": 1672515782136,
  "s": "BTCUSDT",
  "k": {
    "t": 1672515780000,
    "T": 1672515839999,
    "s": "BTCUSDT",
    "i": "1m",
    "f": 265598340,
    "L": 265598350,
    "o": "16849.00",
    "c": "16850.00",
    "h": "16851.00",
    "l": "16848.00",
    "v": "1.234",
    "n": 11,
    "x": false,
    "q": "20789.123",
    "V": "0.617",
    "Q": "10394.561",
    "B": "0"
  }
}
```

| Field | Description                              |
|-------|------------------------------------------|
| t     | Kline start time                         |
| T     | Kline close time                         |
| i     | Interval                                 |
| f     | First trade ID                           |
| L     | Last trade ID                            |
| o     | Open price                               |
| c     | Close price                              |
| h     | High price                               |
| l     | Low price                                |
| v     | Base asset volume                        |
| n     | Number of trades                         |
| x     | Is this kline closed?                    |
| q     | Quote asset volume                       |
| V     | Taker buy base asset volume              |
| Q     | Taker buy quote asset volume             |

### Book Ticker Stream

Best bid/ask updates (highest frequency ticker).

**Stream name:** `<symbol>@bookTicker`

**Update frequency:** Real-time (every BBO change)

**Payload:**
```json
{
  "u": 400900217,
  "s": "BTCUSDT",
  "b": "16849.00",
  "B": "0.450",
  "a": "16850.00",
  "A": "0.320"
}
```

| Field | Description                              |
|-------|------------------------------------------|
| u     | Order book updateId                      |
| s     | Symbol                                   |
| b     | Best bid price                           |
| B     | Best bid quantity                        |
| a     | Best ask price                           |
| A     | Best ask quantity                        |

### Partial Book Depth Streams

Top N levels of order book.

**Stream names:**
- `<symbol>@depth5` - Top 5 levels
- `<symbol>@depth10` - Top 10 levels
- `<symbol>@depth20` - Top 20 levels

**Update frequency:** 1000ms or 100ms (with @100ms suffix)

**Payload:**
```json
{
  "lastUpdateId": 160,
  "bids": [
    ["16849.00", "0.450"],
    ["16848.00", "1.200"]
  ],
  "asks": [
    ["16850.00", "0.320"],
    ["16851.00", "0.890"]
  ]
}
```

### Diff Depth Stream

Incremental order book updates.

**Stream name:** `<symbol>@depth` or `<symbol>@depth@100ms`

**Update frequencies:**
- `@depth` - 1000ms (default)
- `@depth@100ms` - 100ms
- `@depth@250ms` - 250ms (available on some symbols)
- `@depth@500ms` - 500ms

**Payload:**
```json
{
  "e": "depthUpdate",
  "E": 1672515782136,
  "s": "BTCUSDT",
  "U": 157,
  "u": 160,
  "b": [
    ["16849.00", "0.450"],
    ["16848.00", "0.000"]
  ],
  "a": [
    ["16850.00", "0.320"]
  ]
}
```

| Field | Description                              |
|-------|------------------------------------------|
| U     | First update ID in event                 |
| u     | Final update ID in event                 |
| b     | Bids to update (price, quantity)         |
| a     | Asks to update (price, quantity)         |

**Important:** Quantity "0.000" means remove price level.

## Order Book Reconstruction Protocol

### Initial Sync

```
1. Open WebSocket connection
2. Subscribe to <symbol>@depth@100ms
3. Buffer all incoming depthUpdate events
4. GET /api/v3/depth?symbol=X&limit=5000
5. Drop buffered events where u <= lastUpdateId from snapshot
6. Process first event where U <= lastUpdateId+1 AND u >= lastUpdateId+1
7. Continue processing: each event's U must equal previous event's u + 1
```

### Sequence Validation

For each depthUpdate event after the first:
```
if (current.U != previous.u + 1) {
    // Gap detected - book corrupted
    // Must restart from step 1
}
```

### Update Application

```python
def apply_update(book, side, price, quantity):
    if quantity == "0" or quantity == "0.00000000":
        book[side].pop(price, None)
    else:
        book[side][price] = quantity
```

### Resync Triggers

Must perform full resync when:
1. Sequence gap detected
2. WebSocket reconnection
3. Spread becomes negative (sanity check failed)
4. Price diverges >1% from other venues

## User Data Streams

### Listen Key Management

**Create listen key:**
```
POST /api/v3/userDataStream
Response: {"listenKey": "pqia91ma19a5s61cv6a81va65sdf19v8a65a1a5s61cv6a81va65sdf19v8a65a1"}
```

**Keepalive (every 30 minutes):**
```
PUT /api/v3/userDataStream?listenKey=<key>
```

**Delete:**
```
DELETE /api/v3/userDataStream?listenKey=<key>
```

**Listen key expiry:** 60 minutes without keepalive

### Account Update

Triggered by balance changes.

```json
{
  "e": "outboundAccountPosition",
  "E": 1672515782136,
  "u": 1672515782136,
  "B": [
    {
      "a": "BTC",
      "f": "1.00000000",
      "l": "0.50000000"
    }
  ]
}
```

| Field | Description                              |
|-------|------------------------------------------|
| u     | Time of last account update              |
| B     | Balances array                           |
| a     | Asset                                    |
| f     | Free balance                             |
| l     | Locked balance                           |

### Order Update

```json
{
  "e": "executionReport",
  "E": 1672515782136,
  "s": "BTCUSDT",
  "c": "my_order_id",
  "S": "BUY",
  "o": "LIMIT",
  "f": "GTC",
  "q": "1.00000000",
  "p": "16850.00",
  "P": "0.00000000",
  "F": "0.00000000",
  "g": -1,
  "C": "",
  "x": "NEW",
  "X": "NEW",
  "r": "NONE",
  "i": 4293153,
  "l": "0.00000000",
  "z": "0.00000000",
  "L": "0.00000000",
  "n": "0",
  "N": null,
  "T": 1672515782136,
  "t": -1,
  "I": 8641984,
  "w": true,
  "m": false,
  "M": false,
  "O": 1672515782136,
  "Z": "0.00000000",
  "Y": "0.00000000",
  "Q": "0.00000000"
}
```

| Field | Description                              |
|-------|------------------------------------------|
| c     | Client order ID                          |
| S     | Side (BUY/SELL)                          |
| o     | Order type                               |
| f     | Time in force                            |
| q     | Order quantity                           |
| p     | Order price                              |
| x     | Current execution type                   |
| X     | Current order status                     |
| r     | Order reject reason                      |
| i     | Order ID                                 |
| l     | Last executed quantity                   |
| z     | Cumulative filled quantity               |
| L     | Last executed price                      |
| n     | Commission amount                        |
| N     | Commission asset                         |
| T     | Transaction time                         |
| t     | Trade ID                                 |
| m     | Is this trade the maker side?            |

**Execution types (x):**
- NEW
- CANCELED
- REPLACED
- REJECTED
- TRADE
- EXPIRED

**Order statuses (X):**
- NEW
- PARTIALLY_FILLED
- FILLED
- CANCELED
- PENDING_CANCEL
- REJECTED
- EXPIRED

## Futures-Specific Streams

### Mark Price Stream

**Stream name:** `<symbol>@markPrice` or `<symbol>@markPrice@1s`

```json
{
  "e": "markPriceUpdate",
  "E": 1672515782136,
  "s": "BTCUSDT",
  "p": "16850.00000000",
  "i": "16849.50000000",
  "P": "16848.00000000",
  "r": "0.00010000",
  "T": 1672531200000
}
```

| Field | Description                              |
|-------|------------------------------------------|
| p     | Mark price                               |
| i     | Index price                              |
| P     | Estimated settle price                   |
| r     | Funding rate                             |
| T     | Next funding time                        |

### Liquidation Stream

**Stream name:** `<symbol>@forceOrder`

```json
{
  "e": "forceOrder",
  "E": 1672515782136,
  "o": {
    "s": "BTCUSDT",
    "S": "SELL",
    "o": "LIMIT",
    "f": "IOC",
    "q": "0.001",
    "p": "16800.00",
    "ap": "16810.00",
    "X": "FILLED",
    "l": "0.001",
    "z": "0.001",
    "T": 1672515782136
  }
}
```

### All Market Liquidation Stream

**Stream name:** `!forceOrder@arr`

Receives all liquidation orders across all symbols.

## Combined Streams

### Subscription via URL

```
wss://stream.binance.com:9443/stream?streams=btcusdt@trade/btcusdt@depth@100ms
```

### Dynamic Subscription

After connection, send subscription message:

```json
{
  "method": "SUBSCRIBE",
  "params": [
    "btcusdt@trade",
    "btcusdt@depth@100ms"
  ],
  "id": 1
}
```

**Unsubscribe:**
```json
{
  "method": "UNSUBSCRIBE",
  "params": ["btcusdt@trade"],
  "id": 2
}
```

**List subscriptions:**
```json
{
  "method": "LIST_SUBSCRIPTIONS",
  "id": 3
}
```

**Response format:**
```json
{
  "result": null,
  "id": 1
}
```

## Error Handling

### WebSocket Close Codes

| Code | Reason                                   |
|------|------------------------------------------|
| 1000 | Normal closure                           |
| 1001 | Going away (server shutdown)             |
| 1006 | Abnormal closure (no close frame)        |
| 1008 | Policy violation (rate limit)            |
| 1011 | Unexpected condition                     |

### Rate Limit Violations

When inbound message rate exceeded:
1. Connection may be dropped with code 1008
2. IP may be temporarily banned
3. Monitor `Retry-After` header on REST endpoints

## Performance Considerations

### Latency Sources

| Source                    | Typical Latency       |
|---------------------------|-----------------------|
| Server processing         | <1ms                  |
| Network (same region)     | 1-5ms                 |
| Network (cross-region)    | 50-200ms              |
| Message queuing           | Variable under load   |

### Recommended Practices

1. **Co-locate** - Deploy in AWS Tokyo (ap-northeast-1) for lowest latency
2. **Connection pooling** - Reuse connections, avoid frequent reconnects
3. **Buffer management** - Use ring buffers to handle bursts
4. **Sequence validation** - Always check for gaps
5. **Clock sync** - Sync with NTP; validate server timestamps

### Stream Selection

| Use Case                  | Recommended Stream              |
|---------------------------|---------------------------------|
| BBO only                  | `@bookTicker`                   |
| Top of book               | `@depth5` or `@depth10`         |
| Full book                 | `@depth@100ms` + REST snapshot  |
| Trade monitoring          | `@aggTrade`                     |
| Fill tracking             | User data stream                |

## Implementation Checklist

- [ ] Handle WebSocket ping/pong automatically
- [ ] Implement exponential backoff for reconnection
- [ ] Buffer events during REST snapshot fetch
- [ ] Validate sequence numbers on every update
- [ ] Detect and handle stale data (no updates >30s)
- [ ] Implement resync on sequence gaps
- [ ] Monitor connection count against limits
- [ ] Track message rate against limits
- [ ] Handle listen key renewal for user streams
- [ ] Log all disconnections with timestamps
