# Exchange Adapters

Venue-specific configuration, data types, rate limits, and resync protocols for crypto adapters in NautilusTrader.

## Key Differences Across Adapters

Every exchange adapter has its own configuration, authentication, data availability, and quirks. **Always check the adapter source or NautilusTrader docs for your specific exchange.**

| Aspect | What Varies |
|--------|-------------|
| Symbology | Different suffixes, delimiters, contract naming per venue |
| Authentication | Ed25519, HMAC, wallet keys, passphrases — check adapter config |
| Data subscriptions | Not all subscription types implemented on all adapters |
| `modify_order` | Supported on most — **not dYdX** (cancel+replace only) |
| Rate limits | Weight-based (Binance), per-endpoint (Bybit), per-block (dYdX) |
| Order book resync | Different sequence protocols per venue (lastUpdateId, crossSequence, etc.) |
| REST data endpoints | Different paths, response formats, and available data types |
| Instrument loading | Different config classes and account type enums |

### Symbology

| Venue | Spot | Perpetual | Future |
|-------|------|-----------|--------|
| Binance | `BTCUSDT.BINANCE` | `BTCUSDT-PERP.BINANCE` | `BTCUSDT-250328.BINANCE` |
| Bybit | `BTCUSDT.BYBIT` | `BTCUSDT-LINEAR.BYBIT` | — |
| OKX | `BTC-USDT.OKX` | `BTC-USDT-SWAP.OKX` | `BTC-USDT-240329.OKX` |
| dYdX | — | `BTC-USD-PERP.DYDX` | — |

Symbology is critical — using the wrong format produces silent failures (instrument not found, no data). The `-PERP` suffix is mandatory for Binance perpetuals to distinguish from spot.

## Binance

**Venue ID**: `BINANCE` | **Products**: Spot, USDT-M Futures, Coin-M Futures | **Rust crate**: `crates/adapters/binance/`

### Configuration

```python
from nautilus_trader.adapters.binance import (
    BINANCE, BinanceAccountType, BinanceDataClientConfig, BinanceExecClientConfig,
    BinanceLiveDataClientFactory, BinanceLiveExecClientFactory,
)
from nautilus_trader.adapters.binance.common.enums import BinanceKeyType
from nautilus_trader.config import InstrumentProviderConfig

data_config = BinanceDataClientConfig(
    api_key="...", api_secret="...",
    key_type=BinanceKeyType.ED25519,  # REQUIRED for exec WS API (HMAC rejected)
    account_type=BinanceAccountType.USDT_FUTURES,  # note: USDT_FUTURES (with S)
    instrument_provider=InstrumentProviderConfig(load_all=True),
)

exec_config = BinanceExecClientConfig(
    api_key="...", api_secret="...",
    key_type=BinanceKeyType.ED25519,
    account_type=BinanceAccountType.USDT_FUTURES,
)
```

### Authentication

Ed25519 is the recommended key type for Binance. See [NautilusTrader Binance docs](https://nautilustrader.io/docs/nightly/integrations/binance/).

- `BinanceKeyType` enum: `HMAC`, `RSA`, `ED25519` from `nautilus_trader.adapters.binance.common.enums`
- Ed25519 private key must be **unencrypted** PKCS#8 format. Encrypted keys fail at signing
- HMAC may fall back to REST-based auth on some account types, with reduced functionality

### Data Types — What Actually Works (v1.224.0 tested)

| Subscription | Status | Rate (10 perps, 30s) | Notes |
|-------------|--------|---------------------|-------|
| `subscribe_trade_ticks` | **WORKS** | ~100/s | aggTrade stream |
| `subscribe_quote_ticks` | **WORKS** | ~600/s | bookTicker (BBO) — highest volume |
| `subscribe_order_book_deltas` | **WORKS** | ~113/s | L2 incremental + snapshot rebuild |
| `subscribe_mark_prices` | **WORKS** | ~9/s | markPrice stream (includes funding info) |
| `subscribe_bars` | **WORKS** | 1/min/inst | kline stream (1-MINUTE-LAST-EXTERNAL) |
| `subscribe_order_book_depth` | **NOT IMPL** | - | NotImplementedError — use deltas instead |
| `subscribe_funding_rates` | **NOT IMPL** | - | NotImplementedError — mark prices include funding |
| `subscribe_index_prices` | **NOT IMPL** | - | NotImplementedError |
| `subscribe_instrument_status` | **NOT IMPL** | - | NotImplementedError |

**Total throughput**: ~24,500 events/30s (~817/s) across 10 instruments.

Books rebuild via REST snapshot then apply incremental deltas. BTC spread=0.01bps, ETH spread=0.05bps.

| Data Type | WS Source | Notes |
|-----------|-----------|-------|
| `OrderBookDelta` | depth stream | L2 incremental |
| `TradeTick` | aggTrade/trade | Individual trades |
| `QuoteTick` | bookTicker | Best bid/ask |
| `Bar` | kline / REST | All intervals |
| `MarkPriceUpdate` | markPrice | Mark price + funding rate combined |

### REST Data (OI, Funding, Long/Short) — via BinanceHttpClient

Open interest, funding rates, long/short ratios, and mark price are available via REST.
These are NOT available via Strategy subscriptions — use the HTTP client directly:

```python
from nautilus_trader.adapters.binance.factories import get_cached_binance_http_client
from nautilus_trader.adapters.binance import BinanceAccountType
from nautilus_trader.core.nautilus_pyo3 import HttpMethod
import json

# Inside an async context (Actor/Strategy coroutine, or asyncio.run):
client = get_cached_binance_http_client(
    clock=clock,
    account_type=BinanceAccountType.USDT_FUTURES,
    api_key=api_key, api_secret=api_secret,
)

# Open Interest
oi = await client.send_request(HttpMethod.GET, '/fapi/v1/openInterest', {'symbol': 'BTCUSDT'})
data = json.loads(oi)  # {"symbol":"BTCUSDT","openInterest":"81811.143","time":...}

# Funding Rate (latest N)
fr = await client.send_request(HttpMethod.GET, '/fapi/v1/fundingRate',
    {'symbol': 'BTCUSDT', 'limit': '3'})

# Mark Price + Index Price
mark = await client.send_request(HttpMethod.GET, '/fapi/v1/premiumIndex',
    {'symbol': 'BTCUSDT'})
# {"markPrice":"68575.50","indexPrice":"68617.50","lastFundingRate":"-0.000031",...}

# Top Trader Long/Short Ratio
ratio = await client.send_request(HttpMethod.GET,
    '/futures/data/topLongShortPositionRatio',
    {'symbol': 'BTCUSDT', 'period': '5m', 'limit': '3'})

# 24h Ticker (volume)
ticker = await client.send_request(HttpMethod.GET, '/fapi/v1/ticker/24hr',
    {'symbol': 'BTCUSDT'})
```

**NOTE**: `/fapi/v1/allForceOrders` (liquidations) is deprecated — returns 400 "endpoint out of maintenance".

### Rate Limits

| Type | Limit |
|------|-------|
| REST weight | 2400/min (most endpoints cost 1-20 weight) |
| Order rate | 10 orders/sec, 100K orders/day |
| WS connections | 5/sec per IP |

### modify_order

Supported via `PUT /fapi/v1/order`. Amends price and/or quantity in place.

### Order Book Resync: lastUpdateId Protocol

1. Subscribe WS diff depth stream (updates have `U` first id, `u` final id)
2. GET `/fapi/v1/depth` → note `lastUpdateId`
3. Discard WS updates where `u <= lastUpdateId`
4. First valid update: `U <= lastUpdateId + 1 <= u`
5. Subsequent: `U_next == u_prev + 1`

### Factory

```python
from nautilus_trader.adapters.binance import (
    BINANCE, BinanceLiveDataClientFactory, BinanceLiveExecClientFactory,
)
node.add_data_client_factory(BINANCE, BinanceLiveDataClientFactory)
node.add_exec_client_factory(BINANCE, BinanceLiveExecClientFactory)
```

## Bybit

**Venue ID**: `BYBIT` | **Products**: Spot, Linear, Inverse, Options | **Rust crate**: `crates/adapters/bybit/`

### Configuration

```python
from nautilus_trader.adapters.bybit import (
    BYBIT, BybitDataClientConfig, BybitExecClientConfig, BybitProductType,
    BybitLiveDataClientFactory, BybitLiveExecClientFactory,
)

data_config = BybitDataClientConfig(
    api_key="...", api_secret="...",
    product_types=[BybitProductType.LINEAR],
    testnet=False,
)

exec_config = BybitExecClientConfig(
    api_key="...", api_secret="...",
    product_types=[BybitProductType.LINEAR],
    testnet=False,
)
```

### Data Types

| Data Type | WS Source | Notes |
|-----------|-----------|-------|
| `OrderBookDelta` | orderbook | L2, 1/50/200/500 levels |
| `TradeTick` | publicTrade | Trades |
| `QuoteTick` | tickers | Best bid/ask |
| `Bar` | kline | Standard intervals |

### Rate Limits

| Type | Limit |
|------|-------|
| REST | 120 req/min per endpoint |
| Order WS | 10 orders/sec |
| Order REST | 10 req/sec per endpoint |

### modify_order

Supported. Single amend message via REST or WS.

### Order Book Resync: crossSequence

Each update contains `crossSequence`. Verify incoming > last processed. On gap → snapshot resync.

### Factory

```python
from nautilus_trader.adapters.bybit import (
    BYBIT, BybitLiveDataClientFactory, BybitLiveExecClientFactory,
)
node.add_data_client_factory(BYBIT, BybitLiveDataClientFactory)
node.add_exec_client_factory(BYBIT, BybitLiveExecClientFactory)
```

## dYdX (v4)

**Venue ID**: `DYDX` | **Products**: Perpetual Futures only | **Rust crate**: `crates/adapters/dydx/`

### Configuration

```python
from nautilus_trader.adapters.dydx import (
    DYDX, DydxDataClientConfig, DydxExecClientConfig,
    DydxLiveDataClientFactory, DydxLiveExecClientFactory,
)

data_config = DydxDataClientConfig(wallet_address="...", is_testnet=False)

exec_config = DydxExecClientConfig(
    wallet_address="...", subaccount=0, private_key="...",
    is_testnet=False, max_retries=3,
    retry_delay_initial_ms=500, retry_delay_max_ms=5000,
)
```

### Key Details

- Cosmos SDK chain — orders submitted as **blockchain transactions** via gRPC
- Indexer API (REST + WS) for market data
- `DydxOraclePrice` custom data type

### Rate Limits

| Type | Limit |
|------|-------|
| Short-term orders | 100 per 10s per subaccount |
| Long-term orders | 1 per block (~1s) |

### modify_order

**Not supported.** Cancel + replace only. This is the only major crypto venue where modify_order falls back.

### Factory

```python
from nautilus_trader.adapters.dydx import (
    DYDX, DydxLiveDataClientFactory, DydxLiveExecClientFactory,
)
node.add_data_client_factory(DYDX, DydxLiveDataClientFactory)
node.add_exec_client_factory(DYDX, DydxLiveExecClientFactory)
```

## OKX

**Venue ID**: `OKX` | **Products**: Spot, Futures, Perpetual Swaps, Options | **Rust crate**: `crates/adapters/okx/`

### Key Details

- Supports net and long/short position modes
- Trade modes: cross margin, isolated margin, cash
- Symbology: `BTC-USDT` (spot), `BTC-USDT-SWAP` (perp), `BTC-USDT-240329` (future)
- **modify_order**: Supported

## Tardis (Data Provider Only)

**No execution** — historical crypto data replay.

```python
from nautilus_trader.adapters.tardis.config import TardisMachineClientConfig

config = TardisMachineClientConfig(
    base_url="ws://localhost:8001",
    book_snapshot_output="deltas",  # "deltas" or "depth10"
)
```

### Schema → Nautilus Type

| Tardis Schema | Nautilus Type |
|---------------|--------------|
| book_change | `OrderBookDelta` |
| book_snapshot_* | `OrderBookDeltas` / `OrderBookDepth10` |
| quote | `QuoteTick` |
| trade | `TradeTick` |
| trade_bar_* | `Bar` |
| instrument | `CurrencyPair`, `CryptoFuture`, `CryptoPerpetual` |

### CSV Loading

```python
from nautilus_trader.adapters.tardis.loaders import TardisCSVDataLoader

df = TardisCSVDataLoader.load("book_change_BTCUSDT_binance.csv")
wrangler = OrderBookDeltaDataWrangler(instrument)
deltas = wrangler.process(df)
```

## Databento (Data Provider Only)

**No execution** — US equities, futures, options. Useful for L3 (MBO) testing since crypto doesn't have L3.

### Schema → Nautilus Type

| Databento Schema | Nautilus Type |
|------------------|--------------|
| MBO | `OrderBookDelta` (L3) |
| MBP_1, BBO_1S | `QuoteTick`, `TradeTick` |
| MBP_10 | `OrderBookDepth10` |
| TRADES | `TradeTick` |
| OHLCV_* | `Bar` |
| DEFINITION | `Instrument` |

## modify_order Support Matrix

| Venue | modify_order | Fallback |
|-------|-------------|----------|
| Binance | Yes (REST amend) | Cancel + replace |
| Bybit | Yes (REST/WS) | Cancel + replace |
| dYdX | **No** | Cancel + replace only |
| OKX | Yes | Cancel + replace |

For MM strategies: prefer modify_order where supported. On dYdX, cancel+replace is the only option.

## Common Patterns

### URL Resolution

All adapters support testnet via config:
```python
config = SomeExchangeConfig(testnet=True)  # routes to testnet URLs
```

### Rate Limiting

Rate limit structures differ significantly across exchanges:

| Exchange | REST Limits | Order Limits | WS Limits |
|----------|------------|-------------|-----------|
| Binance | 2400 weight/min (endpoints cost 1-20 weight) | 10 orders/sec, 100K/day | 5 connections/sec per IP |
| Bybit | 120 req/min per endpoint | 10 orders/sec | Per-subscription limits |
| dYdX | Per-block (~1s for long-term orders) | 100 short-term per 10s | Indexer WS limits |
| OKX | Per-endpoint tiered | 60 orders/2s | Connection-based |

**NautilusTrader handling**:
- Adapters internally manage rate limits for standard data subscriptions and order operations
- `RiskEngineConfig` provides order-level rate protection:
  ```python
  RiskEngineConfig(
      max_order_submit_rate="100/00:00:01",   # max 100 submits per second
      max_order_modify_rate="100/00:00:01",   # max 100 modifies per second
  )
  ```

**Strategy-level REST polling**: When using the HTTP client directly (e.g., OI polling via timer), calculate your request rate:
- `requests_per_min = (instruments × polls_per_min)`
- Stay well under the exchange limit — budget 50% headroom for other operations
- Different endpoints may share or have separate rate limit pools

### Reconnection Protocol

1. Detect disconnect (ping timeout or read error)
2. Exponential backoff: 1s → 2s → 4s → 8s → max 60s
3. Re-authenticate
4. Re-subscribe all active subscriptions
5. Request snapshot for order books

