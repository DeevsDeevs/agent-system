# Binance Futures API Specification

Deep technical reference for Binance Futures (USDT-M and COIN-M) perpetual and delivery contracts.

## Overview

Binance operates two futures platforms with different settlement currencies:

| Platform        | Base URL                | Settlement | Contracts           |
|-----------------|-------------------------|------------|---------------------|
| USDT-Margined   | fapi.binance.com        | Stablecoin | Perpetual, Quarterly|
| COIN-Margined   | dapi.binance.com        | Crypto     | Perpetual, Quarterly|

## Contract Types

### USDT-Margined (Linear)

- Settled in USDT (BUSD was supported until Dec 2023, now fully delisted)
- P&L in stablecoin
- Simpler to calculate positions
- Most liquid for major pairs

**Symbol format:** `BTCUSDT`, `ETHUSDT`

### COIN-Margined (Inverse)

- Settled in base asset (BTC, ETH, etc.)
- P&L in crypto
- Natural hedge for miners/holders
- Requires more complex calculations

**Symbol format:** `BTCUSD_PERP`, `BTCUSD_230331`

### Perpetual vs Delivery

| Feature        | Perpetual              | Delivery               |
|----------------|------------------------|------------------------|
| Expiry         | No expiry              | Fixed expiry date      |
| Funding        | Every 8h or 4h         | None                   |
| Settlement     | Continuous             | At expiry              |
| Naming         | `BTCUSDT`, `BTCUSD_PERP` | `BTCUSD_230331`      |

## Funding Rate Mechanism

### Purpose

Funding rate anchors perpetual price to spot index price. When perp trades at premium, longs pay shorts (and vice versa).

### Calculation

**Funding Rate Formula:**
```
Funding Rate = Premium Index + clamp(Interest Rate - Premium Index, -0.05%, 0.05%)
```

**Components:**

| Component       | Description                              |
|-----------------|------------------------------------------|
| Premium Index   | (Mark Price - Index Price) / Index Price |
| Interest Rate   | Fixed at 0.01% per 8h (3.65% annual)     |
| Clamp           | Limits deviation to ±0.05%               |

### Settlement Schedule

**Standard (most pairs):**
- 00:00 UTC
- 08:00 UTC
- 16:00 UTC

**High-frequency (some pairs):**
- Every 4 hours (6 times daily)

**Payment direction:**
```
if funding_rate > 0:
    longs_pay_shorts()
elif funding_rate < 0:
    shorts_pay_longs()
```

**Payment calculation:**
```
Funding Payment = Position Value × Funding Rate
Position Value = Mark Price × Position Size (contracts)
```

### Real-Time Funding Data

**Endpoint:** `GET /fapi/v1/premiumIndex`

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "markPrice": "16850.00000000",
  "indexPrice": "16848.50000000",
  "estimatedSettlePrice": "16849.00000000",
  "lastFundingRate": "0.00010000",
  "nextFundingTime": 1672531200000,
  "interestRate": "0.00010000",
  "time": 1672515782136
}
```

**Stream:** `<symbol>@markPrice` or `<symbol>@markPrice@1s`

### Funding Rate History

**Endpoint:** `GET /fapi/v1/fundingRate`

**Parameters:**

| Parameter | Required | Description              |
|-----------|----------|--------------------------|
| symbol    | Yes      | Contract symbol          |
| startTime | No       | Start time (Unix ms)     |
| endTime   | No       | End time (Unix ms)       |
| limit     | No       | Default 100, max 1000    |

## Leverage System

### Leverage Tiers

Binance uses tiered leverage based on position size (notional value).

**BTCUSDT example tiers:**

| Tier | Position Notional  | Max Leverage | Maint. Margin |
|------|--------------------|--------------|--------------:|
| 1    | 0 - 50,000 USDT    | 125x         | 0.40%         |
| 2    | 50,000 - 250,000   | 100x         | 0.50%         |
| 3    | 250,000 - 1,000,000| 50x          | 1.00%         |
| 4    | 1,000,000 - 5,000,000 | 20x       | 2.50%         |
| 5    | 5,000,000 - 10,000,000 | 10x      | 5.00%         |
| 6    | 10,000,000 - 20,000,000 | 5x      | 10.00%        |
| 7    | > 20,000,000       | 4x           | 12.50%        |

**Note:** Tiers vary by symbol. Query via `/fapi/v1/leverageBracket`.

### Leverage Adjustment

**Endpoint:** `POST /fapi/v1/leverage`

**Parameters:**

| Parameter | Required | Description              |
|-----------|----------|--------------------------|
| symbol    | Yes      | Contract symbol          |
| leverage  | Yes      | Target leverage (1-125)  |
| timestamp | Yes      | Current timestamp        |

**Response:**
```json
{
  "leverage": 20,
  "maxNotionalValue": "5000000",
  "symbol": "BTCUSDT"
}
```

### Margin Mode

**Cross margin:** Entire account balance used as margin. Higher capital efficiency, higher risk.

**Isolated margin:** Margin isolated per position. Limited loss, lower efficiency.

**Change margin mode:**
```
POST /fapi/v1/marginType
Parameters: symbol, marginType (ISOLATED/CROSSED)
```

## Mark Price and Liquidation

### Mark Price Calculation

Mark price is used for liquidation and unrealized P&L to prevent manipulation.

**Formula (simplified):**
```
Mark Price = Index Price × (1 + Funding Basis)
Funding Basis = Funding Rate × (Time Until Funding / Funding Interval)
```

**Components:**

| Component   | Description                              |
|-------------|------------------------------------------|
| Index Price | Weighted average from multiple spot exchanges |
| Funding Basis | Prevents sudden jumps at funding time  |

### Index Price Sources

For BTCUSDT, index is weighted average from:
- Binance
- HTX (formerly Huobi, rebranded Sep 2023)
- OKX
- Bitfinex
- Coinbase
- Bitstamp
- Kraken

**Weighting:** Equal weight with outlier removal.

### Liquidation Mechanics

**Liquidation price calculation (long position, isolated):**
```
Liquidation Price = Entry Price × (1 - Initial Margin Rate + Maintenance Margin Rate)
```

**Liquidation price calculation (short position, isolated):**
```
Liquidation Price = Entry Price × (1 + Initial Margin Rate - Maintenance Margin Rate)
```

**Cross margin liquidation:**
```
Liquidation occurs when:
Account Margin Balance ≤ Maintenance Margin
```

> **Warning:** The isolated formulas above are simplified. Cross-margin liquidation is significantly more complex — it considers total account balance, all open positions, and unrealized PnL across positions. Binance does not publish the exact cross-margin formula. Use `GET /fapi/v3/positionRisk` to get the pre-calculated `liquidationPrice` for each position.

### Maintenance Margin

**Endpoint:** `GET /fapi/v3/positionRisk` (v1 is retired, v2 deprecated)

**Response includes:**
```json
{
  "symbol": "BTCUSDT",
  "positionAmt": "1.000",
  "entryPrice": "16800.00",
  "markPrice": "16850.00",
  "unRealizedProfit": "50.00",
  "liquidationPrice": "15200.00",
  "leverage": "10",
  "marginType": "isolated",
  "isolatedMargin": "1680.00",
  "isAutoAddMargin": "false",
  "positionSide": "BOTH"
}
```

### Insurance Fund

When liquidation results in bankruptcy (position can't cover losses):
1. Insurance fund absorbs the loss
2. If insurance fund insufficient, ADL triggers

**Insurance fund data:** `GET /fapi/v1/assetIndex`

### Auto-Deleveraging (ADL)

When insurance fund can't cover liquidation losses:
1. Profitable positions ranked by leverage and P&L
2. Top-ranked positions force-closed against bankrupt position
3. Notification sent to affected users

**ADL indicator:** Returned in position risk endpoint.

## Position Modes

### One-Way Mode (Default)

Single position per symbol. New orders affect existing position.

| Current | Order Side | Result          |
|---------|------------|-----------------|
| Long 1  | BUY 0.5    | Long 1.5        |
| Long 1  | SELL 1.5   | Short 0.5       |
| None    | SELL 1     | Short 1         |

### Hedge Mode

Separate long and short positions. Must specify `positionSide`.

| Order Side | positionSide | Result          |
|------------|--------------|-----------------|
| BUY        | LONG         | Open/add long   |
| SELL       | LONG         | Close long      |
| SELL       | SHORT        | Open/add short  |
| BUY        | SHORT        | Close short     |

**Change position mode:**
```
POST /fapi/v1/positionSide/dual
Parameters: dualSidePosition (true/false)
```

## Order Types (Futures-Specific)

### Standard Types

Same as spot with additional options:

| Type              | Description                              |
|-------------------|------------------------------------------|
| LIMIT             | Standard limit order                     |
| MARKET            | Immediate execution                      |
| STOP              | Stop market order                        |
| STOP_MARKET       | Stop market (same as STOP)               |
| TAKE_PROFIT       | Take profit market                       |
| TAKE_PROFIT_MARKET| Take profit market (same as TAKE_PROFIT) |
| TRAILING_STOP_MARKET | Dynamic trailing stop                 |

### Trailing Stop

**Parameters:**

| Parameter       | Description                              |
|-----------------|------------------------------------------|
| activationPrice | Price to activate trailing               |
| callbackRate    | Trailing distance (0.1% - 5%)            |

**Behavior:**
```
Long position:
  Trigger price = Highest price since activation - (Highest × callback rate)

Short position:
  Trigger price = Lowest price since activation + (Lowest × callback rate)
```

### Reduce-Only Orders

Ensures order can only reduce position, not flip sides.

**Parameter:** `reduceOnly=true`

**Use cases:**
- Stop loss orders
- Take profit orders
- Avoid accidental position increase

### Close Position

Close entire position at market:
```
POST /fapi/v1/order
Parameters:
  symbol: BTCUSDT
  side: SELL (for long position)
  type: MARKET
  closePosition: true
```

## Key Futures Endpoints

### Account Information

```
GET /fapi/v2/account
```

**Response:**
```json
{
  "totalInitialMargin": "1680.00000000",
  "totalMaintMargin": "67.20000000",
  "totalWalletBalance": "10000.00000000",
  "totalUnrealizedProfit": "50.00000000",
  "totalMarginBalance": "10050.00000000",
  "totalPositionInitialMargin": "1680.00000000",
  "totalOpenOrderInitialMargin": "0.00000000",
  "totalCrossWalletBalance": "8320.00000000",
  "totalCrossUnPnl": "50.00000000",
  "availableBalance": "8320.00000000",
  "maxWithdrawAmount": "8320.00000000",
  "assets": [...],
  "positions": [...]
}
```

### Position Risk

```
GET /fapi/v2/positionRisk
```

Returns all positions with liquidation prices, unrealized P&L.

### Leverage Brackets

```
GET /fapi/v1/leverageBracket
```

Returns all leverage tiers for all or specific symbols.

### Income History

```
GET /fapi/v1/income
```

**Parameters:**

| Parameter  | Required | Description                    |
|------------|----------|--------------------------------|
| symbol     | No       | Contract symbol                |
| incomeType | No       | TRANSFER, WELCOME_BONUS, REALIZED_PNL, FUNDING_FEE, COMMISSION, INSURANCE_CLEAR |
| startTime  | No       | Start time (Unix ms)           |
| endTime    | No       | End time (Unix ms)             |
| limit      | No       | Default 100, max 1000          |

### Open Interest

```
GET /fapi/v1/openInterest
```

**Response:**
```json
{
  "symbol": "BTCUSDT",
  "openInterest": "12345.678",
  "time": 1672515782136
}
```

### Long/Short Ratio

```
GET /futures/data/globalLongShortAccountRatio
```

**Parameters:**

| Parameter | Required | Description              |
|-----------|----------|--------------------------|
| symbol    | Yes      | Contract symbol          |
| period    | Yes      | 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d |
| limit     | No       | Default 30, max 500      |

## WebSocket Streams (Futures-Specific)

### Mark Price Stream

**All symbols:** `!markPrice@arr` or `!markPrice@arr@1s`

**Single symbol:** `<symbol>@markPrice` or `<symbol>@markPrice@1s`

### Continuous Kline

**Stream:** `<pair>_<contractType>@continuousKline_<interval>`

Example: `btcusdt_perpetual@continuousKline_1m`

### Liquidation Orders

**All symbols:** `!forceOrder@arr`

**Single symbol:** `<symbol>@forceOrder`

### Book Ticker

Same as spot but includes different update IDs for futures.

### User Data Streams

**Account update:**
```json
{
  "e": "ACCOUNT_UPDATE",
  "T": 1672515782136,
  "E": 1672515782136,
  "a": {
    "B": [
      {
        "a": "USDT",
        "wb": "10000.00000000",
        "cw": "8320.00000000",
        "bc": "0.00000000"
      }
    ],
    "P": [
      {
        "s": "BTCUSDT",
        "pa": "1.000",
        "ep": "16800.00000000",
        "cr": "50.00000000",
        "up": "50.00000000",
        "mt": "isolated",
        "iw": "1680.00000000",
        "ps": "LONG"
      }
    ],
    "m": "ORDER"
  }
}
```

**Order update:**
```json
{
  "e": "ORDER_TRADE_UPDATE",
  "T": 1672515782136,
  "E": 1672515782136,
  "o": {
    "s": "BTCUSDT",
    "c": "my_order_id",
    "S": "BUY",
    "o": "LIMIT",
    "f": "GTC",
    "q": "1.000",
    "p": "16850.00",
    "ap": "0.00",
    "sp": "0.00",
    "x": "NEW",
    "X": "NEW",
    "i": 8886774,
    "l": "0.000",
    "z": "0.000",
    "L": "0.00",
    "n": "0.00000000",
    "N": "USDT",
    "T": 1672515782136,
    "t": 0,
    "b": "0.00",
    "a": "0.00",
    "m": false,
    "R": false,
    "wt": "CONTRACT_PRICE",
    "ot": "LIMIT",
    "ps": "BOTH",
    "cp": false,
    "rp": "0.00000000",
    "pP": false,
    "si": 0,
    "ss": 0
  }
}
```

## Rate Limits (Futures)

| Limit Type     | Window    | Limit              |
|----------------|-----------|-------------------|
| Request weight | 1 minute  | 2400              |
| Orders         | 1 minute  | 1200              |
| Orders         | 10 seconds| 300               |

**Note:** Limits are separate from spot API.

## Risk Management

### Position Limit

Maximum position size varies by symbol and tier:

**BTCUSDT:**
- Max position: 500 BTC (at lowest leverage)
- Reduces at higher leverage tiers

### Daily Loss Limit

Account may be restricted if daily realized loss exceeds threshold.

### Circuit Breakers

Unlike traditional markets, Binance Futures has limited circuit breaker mechanisms:
- Extreme volatility may trigger increased margin requirements
- Insurance fund depletion may halt trading temporarily

## Implementation Checklist

- [ ] Understand funding rate calculation and timing
- [ ] Implement leverage tier lookups for position sizing
- [ ] Monitor maintenance margin vs account balance
- [ ] Handle ADL notifications
- [ ] Track mark price vs last price for P&L
- [ ] Implement liquidation price warnings
- [ ] Use reduce-only for stop orders
- [ ] Monitor funding payments in income history
- [ ] Handle position mode (one-way vs hedge)
- [ ] Validate orders against leverage tier limits
