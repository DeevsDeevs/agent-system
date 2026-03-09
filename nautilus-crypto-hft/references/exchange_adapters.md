# Exchange Adapters

Venue-specific configuration, data types, rate limits, and resync protocols for crypto adapters in NautilusTrader.

## Binance

**Venue ID**: `BINANCE` | **Products**: Spot, USDT-M Futures, Coin-M Futures | **Rust crate**: `crates/adapters/binance/`

### Configuration

```python
from nautilus_trader.adapters.binance.config import (
    BinanceDataClientConfig, BinanceExecClientConfig, BinanceInstrumentProviderConfig,
)

data_config = BinanceDataClientConfig(
    api_key="...", api_secret="...",
    account_type=BinanceAccountType.USDT_FUTURE,
    testnet=False,
    instrument_provider=BinanceInstrumentProviderConfig(load_all=True, query_commission_rates=True),
)

exec_config = BinanceExecClientConfig(
    api_key="...", api_secret="...",
    account_type=BinanceAccountType.USDT_FUTURE,
    testnet=False,
)
```

### Data Types

| Data Type | WS Source | Notes |
|-----------|-----------|-------|
| `OrderBookDelta` | depth stream | L2 incremental |
| `OrderBookDepth10` | depth5/depth10 | Aggregated snapshots |
| `TradeTick` | aggTrade/trade | Individual trades |
| `QuoteTick` | bookTicker | Best bid/ask |
| `Bar` | kline / REST | All intervals |
| `BinanceFuturesMarkPriceUpdate` | markPrice | Mark + funding |

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
from nautilus_trader.adapters.binance.factories import (
    BinanceLiveDataClientFactory, BinanceLiveExecClientFactory,
)
node.add_data_client_factory("BINANCE", BinanceLiveDataClientFactory)
node.add_exec_client_factory("BINANCE", BinanceLiveExecClientFactory)
```

## Bybit

**Venue ID**: `BYBIT` | **Products**: Spot, Linear, Inverse, Options | **Rust crate**: `crates/adapters/bybit/`

### Configuration

```python
from nautilus_trader.adapters.bybit.config import BybitDataClientConfig, BybitExecClientConfig

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
from nautilus_trader.adapters.bybit.factories import (
    BybitLiveDataClientFactory, BybitLiveExecClientFactory,
)
node.add_data_client_factory("BYBIT", BybitLiveDataClientFactory)
node.add_exec_client_factory("BYBIT", BybitLiveExecClientFactory)
```

## dYdX (v4)

**Venue ID**: `DYDX` | **Products**: Perpetual Futures only | **Rust crate**: `crates/adapters/dydx/`

### Configuration

```python
from nautilus_trader.adapters.dydx.config import DYDXDataClientConfig, DYDXExecClientConfig

data_config = DYDXDataClientConfig(wallet_address="...", is_testnet=False)

exec_config = DYDXExecClientConfig(
    wallet_address="...", subaccount_number=0, mnemonic="...",
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
from nautilus_trader.adapters.dydx.factories import (
    DYDXLiveDataClientFactory, DYDXLiveExecClientFactory,
)
node.add_data_client_factory("DYDX", DYDXLiveDataClientFactory)
node.add_exec_client_factory("DYDX", DYDXLiveExecClientFactory)
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

For MM strategies: prefer modify_order. On dYdX, cancel+replace is the only option — budget for higher message count and fingerprinting exposure.

## Common Patterns

### URL Resolution

All adapters support testnet via config:
```python
config = SomeExchangeConfig(testnet=True)  # routes to testnet URLs
```

### Rate Limiting

- Track request counts per endpoint
- Backoff at 80% of limit
- Queue requests when limit hit
- Log warnings at threshold

### Reconnection Protocol

1. Detect disconnect (ping timeout or read error)
2. Exponential backoff: 1s → 2s → 4s → 8s → max 60s
3. Re-authenticate
4. Re-subscribe all active subscriptions
5. Request snapshot for order books

### Symbology

| Venue | Spot | Perpetual | Future |
|-------|------|-----------|--------|
| Binance | `BTCUSDT.BINANCE` | `BTCUSDT-PERP.BINANCE` | `BTCUSDT-250328.BINANCE` |
| Bybit | `BTCUSDT.BYBIT` | `BTCUSDT-LINEAR.BYBIT` | — |
| OKX | `BTC-USDT.OKX` | `BTC-USDT-SWAP.OKX` | `BTC-USDT-240329.OKX` |
| dYdX | — | `BTC-USD.DYDX` | — |

The `-PERP` suffix is mandatory for Binance perpetuals to distinguish from spot.
