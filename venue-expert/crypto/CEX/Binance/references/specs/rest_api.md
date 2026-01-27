# Binance REST API Specification

Deep technical reference for Binance REST API endpoints, authentication, and rate limiting.

## Overview

Binance REST API provides synchronous access to market data, trading, and account management. Primary use cases:

| Use Case              | Endpoints                    |
|-----------------------|------------------------------|
| Market data snapshots | /depth, /trades, /klines     |
| Order management      | /order, /openOrders          |
| Account information   | /account, /myTrades          |
| System status         | /time, /exchangeInfo         |

## Base URLs

### Spot API

| Environment | Base URL                     |
|-------------|------------------------------|
| Production  | https://api.binance.com      |
| Backup 1    | https://api1.binance.com     |
| Backup 2    | https://api2.binance.com     |
| Backup 3    | https://api3.binance.com     |
| Backup 4    | https://api4.binance.com     |
| Testnet     | https://testnet.binance.vision |

### Futures USDT-Margined

| Environment | Base URL                     |
|-------------|------------------------------|
| Production  | https://fapi.binance.com     |
| Testnet     | https://testnet.binancefuture.com |

### Futures COIN-Margined

| Environment | Base URL                     |
|-------------|------------------------------|
| Production  | https://dapi.binance.com     |
| Testnet     | https://testnet.binancefuture.com |

## Authentication

### Security Types

| Type        | Description                           | Signature |
|-------------|---------------------------------------|-----------|
| NONE        | Public endpoints                      | No        |
| TRADE       | Order placement/cancellation          | Yes       |
| USER_DATA   | Account, order queries                | Yes       |
| USER_STREAM | Listen key management                 | API key   |
| MARKET_DATA | Market data with higher limits        | API key   |

### Request Signing

**HMAC SHA256 signature:**

```python
import hmac
import hashlib
import time

def sign_request(secret_key, params):
    query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
    signature = hmac.new(
        secret_key.encode('utf-8'),
        query_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature
```

**Request construction:**
```
1. Build query string with all parameters
2. Add timestamp parameter
3. Generate signature from query string
4. Append signature to query string
5. Include API key in X-MBX-APIKEY header
```

**Example:**
```
Query: symbol=BTCUSDT&side=BUY&type=LIMIT&quantity=1&price=16850&timestamp=1672515782136
Signature: HMAC-SHA256(query_string, secret_key)
Full query: symbol=BTCUSDT&side=BUY&type=LIMIT&quantity=1&price=16850&timestamp=1672515782136&signature=abc123...
```

### Timestamp Requirements

| Parameter      | Window                       |
|----------------|------------------------------|
| timestamp      | Required for signed requests |
| recvWindow     | Max 60000ms (default 5000ms) |

**Validation:**
```
server_time - recvWindow <= timestamp <= server_time + 1000
```

**Clock sync endpoint:**
```
GET /api/v3/time
Response: {"serverTime": 1672515782136}
```

## Rate Limiting

### Weight System

Each endpoint has assigned weight. Total weight is limited per time window.

**Spot limits:**

| Limit Type     | Window    | Default Limit |
|----------------|-----------|---------------|
| Request weight | 1 minute  | 6000          |
| Orders         | 10 seconds| 100           |
| Orders         | 1 day     | 200000        |
| Raw requests   | 5 minutes | 61000         |

**Response headers:**
```
X-MBX-USED-WEIGHT-1M: 1200
X-MBX-ORDER-COUNT-10S: 50
X-MBX-ORDER-COUNT-1D: 15000
```

### Endpoint Weights

| Endpoint                  | Weight | Notes                    |
|---------------------------|--------|--------------------------|
| GET /api/v3/depth         | 5-50   | Varies by limit param    |
| GET /api/v3/trades        | 5      |                          |
| GET /api/v3/historicalTrades | 25  | Requires API key         |
| GET /api/v3/klines        | 2      |                          |
| GET /api/v3/ticker/24hr   | 5-80   | Varies by symbol count   |
| GET /api/v3/ticker/price  | 2-4    |                          |
| GET /api/v3/ticker/bookTicker | 2-4 |                         |
| POST /api/v3/order        | 1      |                          |
| DELETE /api/v3/order      | 1      |                          |
| GET /api/v3/openOrders    | 6-40   | Varies by symbol         |
| GET /api/v3/account       | 20     |                          |
| GET /api/v3/myTrades      | 20     |                          |

### Depth Endpoint Weights

| Limit Parameter | Weight |
|-----------------|--------|
| 5, 10, 20, 50   | 5      |
| 100             | 10     |
| 500             | 25     |
| 1000            | 50     |
| 5000            | 250    |

### Ban Escalation

| Violation          | Response     | Duration        |
|--------------------|--------------|-----------------|
| Exceed weight      | HTTP 429     | Wait and retry  |
| Repeated 429s      | HTTP 418     | 2 minutes       |
| Continued abuse    | HTTP 418     | Up to 3 days    |

**Recovery:**
```
1. Check Retry-After header
2. Wait specified duration
3. Do NOT retry during ban period
4. Implement exponential backoff
```

## Error Codes

### HTTP Status Codes

| Code | Meaning                              |
|------|--------------------------------------|
| 200  | Success                              |
| 400  | Bad request (malformed)              |
| 401  | Unauthorized (invalid API key)       |
| 403  | Forbidden (WAF violation)            |
| 404  | Not found                            |
| 418  | IP banned                            |
| 429  | Rate limited                         |
| 500  | Internal server error                |
| 503  | Service unavailable                  |

### API Error Codes

**General errors (-1xxx):**

| Code   | Message                              |
|--------|--------------------------------------|
| -1000  | UNKNOWN                              |
| -1001  | DISCONNECTED                         |
| -1002  | UNAUTHORIZED                         |
| -1003  | TOO_MANY_REQUESTS                    |
| -1006  | UNEXPECTED_RESP                      |
| -1007  | TIMEOUT                              |
| -1014  | UNKNOWN_ORDER_COMPOSITION            |
| -1015  | TOO_MANY_ORDERS                      |
| -1016  | SERVICE_SHUTTING_DOWN                |
| -1020  | UNSUPPORTED_OPERATION                |
| -1021  | INVALID_TIMESTAMP                    |
| -1022  | INVALID_SIGNATURE                    |

**Request errors (-11xx):**

| Code   | Message                              |
|--------|--------------------------------------|
| -1100  | ILLEGAL_CHARS                        |
| -1101  | TOO_MANY_PARAMETERS                  |
| -1102  | MANDATORY_PARAM_EMPTY_OR_MALFORMED   |
| -1103  | UNKNOWN_PARAM                        |
| -1104  | UNREAD_PARAMETERS                    |
| -1105  | PARAM_EMPTY                          |
| -1106  | PARAM_NOT_REQUIRED                   |
| -1108  | BAD_ASSET                            |
| -1109  | BAD_ACCOUNT                          |
| -1110  | BAD_INSTRUMENT_TYPE                  |
| -1111  | BAD_PRECISION                        |
| -1112  | NO_DEPTH                             |
| -1114  | TIF_NOT_REQUIRED                     |
| -1115  | INVALID_TIF                          |
| -1116  | INVALID_ORDER_TYPE                   |
| -1117  | INVALID_SIDE                         |
| -1118  | EMPTY_NEW_CL_ORD_ID                  |
| -1119  | EMPTY_ORG_CL_ORD_ID                  |
| -1120  | BAD_INTERVAL                         |
| -1121  | BAD_SYMBOL                           |
| -1125  | INVALID_LISTEN_KEY                   |
| -1127  | MORE_THAN_XX_HOURS                   |
| -1128  | OPTIONAL_PARAMS_BAD_COMBO            |
| -1130  | INVALID_PARAMETER                    |

**Order errors (-2xxx):**

| Code   | Message                              |
|--------|--------------------------------------|
| -2010  | NEW_ORDER_REJECTED                   |
| -2011  | CANCEL_REJECTED                      |
| -2013  | NO_SUCH_ORDER                        |
| -2014  | BAD_API_KEY_FMT                      |
| -2015  | REJECTED_MBX_KEY                     |
| -2016  | NO_TRADING_WINDOW                    |
| -2018  | BALANCE_NOT_SUFFICIENT               |
| -2019  | MARGIN_NOT_SUFFICIENT                |
| -2020  | UNABLE_TO_FILL                       |
| -2021  | ORDER_WOULD_IMMEDIATELY_TRIGGER      |
| -2022  | REDUCE_ONLY_REJECT                   |
| -2023  | USER_IN_LIQUIDATION                  |
| -2024  | POSITION_NOT_SUFFICIENT              |
| -2025  | MAX_OPEN_ORDER_EXCEEDED              |
| -2026  | REDUCE_ONLY_ORDER_TYPE_NOT_SUPPORTED |

## Key Endpoints

### Exchange Information

```
GET /api/v3/exchangeInfo
```

Returns trading rules and symbol information.

**Response fields:**

| Field              | Description                         |
|--------------------|-------------------------------------|
| timezone           | Server timezone                     |
| serverTime         | Current server time                 |
| rateLimits         | Current rate limit rules            |
| symbols            | Array of trading pairs              |
| symbols[].filters  | Trading rules for symbol            |

**Symbol filters:**

| Filter              | Description                        |
|---------------------|------------------------------------|
| PRICE_FILTER        | Price precision and limits         |
| LOT_SIZE            | Quantity precision and limits      |
| MIN_NOTIONAL        | Minimum order value                |
| ICEBERG_PARTS       | Max iceberg parts                  |
| MARKET_LOT_SIZE     | Market order quantity limits       |
| MAX_NUM_ORDERS      | Max open orders                    |
| MAX_NUM_ALGO_ORDERS | Max algo orders                    |
| PERCENT_PRICE       | Price vs mark price limits         |

### Order Book Depth

```
GET /api/v3/depth?symbol=BTCUSDT&limit=1000
```

**Parameters:**

| Parameter | Required | Description              |
|-----------|----------|--------------------------|
| symbol    | Yes      | Trading pair             |
| limit     | No       | 5, 10, 20, 50, 100, 500, 1000, 5000 |

**Response:**
```json
{
  "lastUpdateId": 1027024,
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

### Recent Trades

```
GET /api/v3/trades?symbol=BTCUSDT&limit=500
```

**Parameters:**

| Parameter | Required | Description              |
|-----------|----------|--------------------------|
| symbol    | Yes      | Trading pair             |
| limit     | No       | Default 500, max 1000    |

### Historical Trades

```
GET /api/v3/historicalTrades?symbol=BTCUSDT&limit=500&fromId=12345
```

**Note:** Requires API key (MARKET_DATA permission).

**Parameters:**

| Parameter | Required | Description              |
|-----------|----------|--------------------------|
| symbol    | Yes      | Trading pair             |
| limit     | No       | Default 500, max 1000    |
| fromId    | No       | Trade ID to fetch from   |

### Klines/Candlesticks

```
GET /api/v3/klines?symbol=BTCUSDT&interval=1h&limit=500
```

**Parameters:**

| Parameter | Required | Description              |
|-----------|----------|--------------------------|
| symbol    | Yes      | Trading pair             |
| interval  | Yes      | 1s,1m,3m,5m,15m,30m,1h,2h,4h,6h,8h,12h,1d,3d,1w,1M |
| startTime | No       | Start time (Unix ms)     |
| endTime   | No       | End time (Unix ms)       |
| limit     | No       | Default 500, max 1000    |

**Response:** Array of arrays:
```
[
  [
    1499040000000,      // Open time
    "0.01634000",       // Open
    "0.80000000",       // High
    "0.01575800",       // Low
    "0.01577100",       // Close
    "148976.11427815",  // Volume
    1499644799999,      // Close time
    "2434.19055334",    // Quote asset volume
    308,                // Number of trades
    "1756.87402397",    // Taker buy base asset volume
    "28.46694368",      // Taker buy quote asset volume
    "17928899.62484339" // Ignore
  ]
]
```

### 24hr Ticker Statistics

```
GET /api/v3/ticker/24hr?symbol=BTCUSDT
```

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "priceChange": "100.00",
  "priceChangePercent": "0.60",
  "weightedAvgPrice": "16800.00",
  "prevClosePrice": "16750.00",
  "lastPrice": "16850.00",
  "lastQty": "0.001",
  "bidPrice": "16849.00",
  "bidQty": "0.450",
  "askPrice": "16850.00",
  "askQty": "0.320",
  "openPrice": "16750.00",
  "highPrice": "17000.00",
  "lowPrice": "16500.00",
  "volume": "10000.00000000",
  "quoteVolume": "168000000.00",
  "openTime": 1672429382136,
  "closeTime": 1672515782136,
  "firstId": 265500000,
  "lastId": 265598345,
  "count": 98345
}
```

## Order Management

### Place Order

```
POST /api/v3/order
```

**Parameters:**

| Parameter        | Required | Description                    |
|------------------|----------|--------------------------------|
| symbol           | Yes      | Trading pair                   |
| side             | Yes      | BUY or SELL                    |
| type             | Yes      | Order type                     |
| timeInForce      | Varies   | GTC, IOC, FOK, GTX             |
| quantity         | Varies   | Order quantity                 |
| quoteOrderQty    | Varies   | Quote quantity (market orders) |
| price            | Varies   | Order price                    |
| newClientOrderId | No       | Custom order ID                |
| stopPrice        | Varies   | Trigger price for stops        |
| icebergQty       | No       | Iceberg quantity               |
| newOrderRespType | No       | ACK, RESULT, FULL              |
| recvWindow       | No       | Timestamp window               |
| timestamp        | Yes      | Current timestamp              |

**Order types and required parameters:**

| Type              | Required Parameters                      |
|-------------------|------------------------------------------|
| LIMIT             | timeInForce, quantity, price             |
| MARKET            | quantity OR quoteOrderQty                |
| STOP_LOSS         | quantity, stopPrice                      |
| STOP_LOSS_LIMIT   | timeInForce, quantity, price, stopPrice  |
| TAKE_PROFIT       | quantity, stopPrice                      |
| TAKE_PROFIT_LIMIT | timeInForce, quantity, price, stopPrice  |
| LIMIT_MAKER       | quantity, price (post-only)              |

**Response (FULL):**
```json
{
  "symbol": "BTCUSDT",
  "orderId": 28,
  "orderListId": -1,
  "clientOrderId": "6gCrw2kRUAF9CvJDGP16IP",
  "transactTime": 1507725176595,
  "price": "16850.00",
  "origQty": "1.00000000",
  "executedQty": "0.00000000",
  "cummulativeQuoteQty": "0.00000000",
  "status": "NEW",
  "timeInForce": "GTC",
  "type": "LIMIT",
  "side": "BUY",
  "fills": []
}
```

### Cancel Order

```
DELETE /api/v3/order
```

**Parameters:**

| Parameter         | Required | Description              |
|-------------------|----------|--------------------------|
| symbol            | Yes      | Trading pair             |
| orderId           | Varies   | Order ID                 |
| origClientOrderId | Varies   | Original client order ID |
| newClientOrderId  | No       | Used to identify cancel  |
| recvWindow        | No       | Timestamp window         |
| timestamp         | Yes      | Current timestamp        |

**Note:** Must provide either orderId or origClientOrderId.

### Query Order

```
GET /api/v3/order
```

**Parameters:**

| Parameter         | Required | Description              |
|-------------------|----------|--------------------------|
| symbol            | Yes      | Trading pair             |
| orderId           | Varies   | Order ID                 |
| origClientOrderId | Varies   | Original client order ID |
| recvWindow        | No       | Timestamp window         |
| timestamp         | Yes      | Current timestamp        |

### Current Open Orders

```
GET /api/v3/openOrders
```

**Parameters:**

| Parameter  | Required | Description              |
|------------|----------|--------------------------|
| symbol     | No       | Trading pair (omit for all) |
| recvWindow | No       | Timestamp window         |
| timestamp  | Yes      | Current timestamp        |

**Weight:** 6 with symbol, 40 without symbol.

### Account Information

```
GET /api/v3/account
```

**Response:**
```json
{
  "makerCommission": 10,
  "takerCommission": 10,
  "buyerCommission": 0,
  "sellerCommission": 0,
  "canTrade": true,
  "canWithdraw": true,
  "canDeposit": true,
  "updateTime": 1672515782136,
  "accountType": "SPOT",
  "balances": [
    {
      "asset": "BTC",
      "free": "1.00000000",
      "locked": "0.50000000"
    }
  ],
  "permissions": ["SPOT"]
}
```

### Account Trade List

```
GET /api/v3/myTrades
```

**Parameters:**

| Parameter  | Required | Description              |
|------------|----------|--------------------------|
| symbol     | Yes      | Trading pair             |
| orderId    | No       | Filter by order ID       |
| startTime  | No       | Start time (Unix ms)     |
| endTime    | No       | End time (Unix ms)       |
| fromId     | No       | Trade ID to fetch from   |
| limit      | No       | Default 500, max 1000    |
| recvWindow | No       | Timestamp window         |
| timestamp  | Yes      | Current timestamp        |

## Best Practices

### Request Optimization

1. **Use WebSocket for real-time data** - REST for snapshots only
2. **Batch requests where possible** - /ticker/24hr accepts array
3. **Cache exchangeInfo** - Refresh daily or on error
4. **Use appropriate depth limits** - Don't fetch 5000 levels if 100 suffices

### Error Handling

```python
def handle_response(response):
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 60))
        time.sleep(retry_after)
        return retry()

    if response.status_code == 418:
        # IP banned - do not retry
        raise BannedError(response.headers.get('Retry-After'))

    data = response.json()
    if 'code' in data and data['code'] < 0:
        raise BinanceAPIError(data['code'], data['msg'])

    return data
```

### Clock Synchronization

```python
def sync_clock():
    response = requests.get('https://api.binance.com/api/v3/time')
    server_time = response.json()['serverTime']
    local_time = int(time.time() * 1000)
    return server_time - local_time  # offset

# Apply offset to all signed requests
timestamp = int(time.time() * 1000) + clock_offset
```

## Implementation Checklist

- [ ] Implement HMAC-SHA256 signing
- [ ] Sync clock with server time endpoint
- [ ] Monitor rate limit headers on every response
- [ ] Handle 429/418 responses gracefully
- [ ] Parse and handle API error codes
- [ ] Cache exchangeInfo and refresh periodically
- [ ] Validate order parameters against symbol filters
- [ ] Use recvWindow appropriately (not too large)
- [ ] Log all request/response for debugging
- [ ] Implement retry logic with exponential backoff
