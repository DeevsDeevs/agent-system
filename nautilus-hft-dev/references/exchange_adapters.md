# Exchange Adapter Reference

Detailed reference for existing NautilusTrader exchange adapters. Use as patterns for custom adapter development.

## Binance

**Venue ID**: `BINANCE`
**Products**: Spot, USDT-M Futures, Coin-M Futures
**Rust crate**: `crates/adapters/binance/`

### Configuration

```python
from nautilus_trader.adapters.binance.config import (
    BinanceDataClientConfig,
    BinanceExecClientConfig,
    BinanceInstrumentProviderConfig,
)

data_config = BinanceDataClientConfig(
    api_key="...",
    api_secret="...",
    account_type=BinanceAccountType.USDT_FUTURE,  # SPOT, USDT_FUTURE, COIN_FUTURE
    testnet=False,
    instrument_provider=BinanceInstrumentProviderConfig(
        load_all=True,
        query_commission_rates=True,
    ),
)

exec_config = BinanceExecClientConfig(
    api_key="...",
    api_secret="...",
    account_type=BinanceAccountType.USDT_FUTURE,
    testnet=False,
)
```

### Data Types Supported

| Data Type | Source | Notes |
|-----------|--------|-------|
| `OrderBookDelta` | WS depth stream | L2 incremental updates |
| `OrderBookDepth10` | WS depth5/depth10 | Aggregated snapshots |
| `TradeTick` | WS aggTrade/trade | Individual trades |
| `QuoteTick` | WS bookTicker | Best bid/ask |
| `Bar` | WS kline / REST | All standard intervals |
| `BinanceTicker` | WS 24hrTicker | Custom data type |
| `BinanceFuturesMarkPriceUpdate` | WS markPrice | Futures mark + funding |

### Binance-Specific: SBE Encoding

Binance Spot uses Simple Binary Encoding (SBE) for REST and WebSocket. Requires Ed25519 authentication for SBE market data streams.

### Order Types

Market, Limit, Stop-Market, Stop-Limit, Trailing-Stop-Market. Supports `post_only`, `reduce_only`, `time_in_force` (GTC, IOC, FOK, GTD).

### Factory Registration

```python
from nautilus_trader.adapters.binance.factories import (
    BinanceLiveDataClientFactory,
    BinanceLiveExecClientFactory,
)

node.add_data_client_factory("BINANCE", BinanceLiveDataClientFactory)
node.add_exec_client_factory("BINANCE", BinanceLiveExecClientFactory)
```

## Bybit

**Venue ID**: `BYBIT`
**Products**: Spot, Linear (USDT perps/futures), Inverse (coin perps/futures), Options
**Rust crate**: `crates/adapters/bybit/`

### Configuration

```python
from nautilus_trader.adapters.bybit.config import (
    BybitDataClientConfig,
    BybitExecClientConfig,
)

data_config = BybitDataClientConfig(
    api_key="...",
    api_secret="...",
    product_types=[BybitProductType.LINEAR],  # LINEAR, INVERSE, SPOT, OPTION
    testnet=False,
)

exec_config = BybitExecClientConfig(
    api_key="...",
    api_secret="...",
    product_types=[BybitProductType.LINEAR],
    testnet=False,
    auto_repay_spot_borrows=False,  # spot margin feature
)
```

### Data Types

| Data Type | Source | Notes |
|-----------|--------|-------|
| `OrderBookDelta` | WS orderbook | L2 depth, 1/50/200/500 levels |
| `TradeTick` | WS publicTrade | Trades |
| `QuoteTick` | WS tickers | Best bid/ask |
| `Bar` | WS kline | Standard intervals |
| `BybitTickerData` | WS tickers | Custom extended ticker |

### PyO3 Exports

```python
# Rust types exposed to Python:
from nautilus_trader.adapters.bybit import (
    BybitProductType,
    BybitHttpClient,
    BybitWebSocketClient,
)
```

## dYdX (v4)

**Venue ID**: `DYDX`
**Products**: Perpetual Futures only (no spot, no options)
**Rust crate**: `crates/adapters/dydx/`

### Configuration

```python
from nautilus_trader.adapters.dydx.config import (
    DYDXDataClientConfig,
    DYDXExecClientConfig,
)

data_config = DYDXDataClientConfig(
    wallet_address="...",
    is_testnet=False,
)

exec_config = DYDXExecClientConfig(
    wallet_address="...",
    subaccount_number=0,
    mnemonic="...",
    is_testnet=False,
    max_retries=3,
    retry_delay_initial_ms=500,
    retry_delay_max_ms=5000,
)
```

### Key Details

- Uses Indexer API (REST + WS) for data
- Uses gRPC for transaction submission (order placement)
- Cosmos SDK-based chain — orders submitted as blockchain transactions
- Supports `DydxOraclePrice` custom data type

### Factory Registration

```python
from nautilus_trader.adapters.dydx.factories import (
    DYDXLiveDataClientFactory,
    DYDXLiveExecClientFactory,
)

node.add_data_client_factory("DYDX", DYDXLiveDataClientFactory)
node.add_exec_client_factory("DYDX", DYDXLiveExecClientFactory)
```

## Databento (Data Provider Only)

**Venue ID**: `DATABENTO` (maps to underlying venues: XNAS, XNYS, GLBX, etc.)
**Products**: US equities, futures, options
**No execution client** — data only
**Rust crate**: `crates/adapters/databento/`

### Configuration

```python
from nautilus_trader.adapters.databento.config import DatabentoDataClientConfig

config = DatabentoDataClientConfig(
    api_key="...",
    bars_timestamp_on_close=True,  # default: True
)
```

### Schema → Nautilus Type Mapping

| Databento Schema | Nautilus Type | Notes |
|------------------|--------------|-------|
| MBO | `OrderBookDelta` | L3 market-by-order |
| MBP_1, BBO_1S, BBO_1M, CMBP_1, CBBO_1S, CBBO_1M, TCBBO, TBBO | `QuoteTick`, `TradeTick` | Top-of-book |
| MBP_10 | `OrderBookDepth10` | Top 10 levels |
| TRADES | `TradeTick` | Trade events |
| OHLCV_1S/1M/1H/1D/EOD | `Bar` | OHLCV bars |
| DEFINITION | `Instrument` | Instrument definitions |
| IMBALANCE | `DatabentoImbalance` | Custom type |
| STATISTICS | `DatabentoStatistics` | Custom type |
| STATUS | `InstrumentStatus` | Market status |

### Features

- Historical client (`DatabentoHistoricalClient`): HTTP-based historical data
- Live client (`DatabentoLiveClient`): Raw TCP streaming
- Automatic reconnection with backoff strategies
- `reconnect_timeout_mins` config for reconnection duration

## Tardis (Crypto Data Provider Only)

**Venue ID**: Maps to underlying crypto venues
**Products**: All major crypto exchanges historical + replay
**No execution client** — data only
**Rust crate**: `crates/adapters/tardis/`

### Configuration

```python
from nautilus_trader.adapters.tardis.config import TardisMachineClientConfig

config = TardisMachineClientConfig(
    base_url="ws://localhost:8001",  # Tardis Machine server
    book_snapshot_output="deltas",  # "deltas" or "depth10"
)
```

### Schema → Nautilus Type Mapping

| Tardis Schema | Nautilus Type | Notes |
|---------------|--------------|-------|
| book_change | `OrderBookDelta` | Incremental book updates |
| book_snapshot_* | `OrderBookDeltas` or `OrderBookDepth10` | Depends on `book_snapshot_output` config |
| quote, quote_10s | `QuoteTick` | Best bid/ask |
| trade | `TradeTick` | Trade events |
| trade_bar_* | `Bar` | Aggregated bars |
| instrument | Various instrument types | `CurrencyPair`, `CryptoFuture`, `CryptoPerpetual`, `OptionContract` |

### CSV Loading for Backtesting

```python
from nautilus_trader.adapters.tardis.loaders import TardisCSVDataLoader

# Load and wrangle book data
df = TardisCSVDataLoader.load("book_change_BTCUSDT_binance.csv")
wrangler = OrderBookDeltaDataWrangler(instrument)
deltas = wrangler.process(df)
```

## OKX

**Venue ID**: `OKX`
**Products**: Spot, Futures, Perpetual Swaps, Options
**Rust crate**: `crates/adapters/okx/`

### Key Details

- Supports net and long/short position modes
- Trade modes: cross margin, isolated margin, cash
- Symbology: `BTC-USDT` (spot), `BTC-USDT-SWAP` (perp), `BTC-USDT-240329` (future)

## Interactive Brokers

**Venue ID**: `INTERACTIVE_BROKERS`
**Products**: Multi-asset (equities, futures, options, forex, crypto)

### Key Details

- Connects via TWS/Gateway (local or Dockerized)
- `DockerizedIBGatewayConfig` for containerized gateway
- Supports spread contracts with exchange parameters
- Not primarily a crypto adapter — multi-asset brokerage

```python
from nautilus_trader.adapters.interactive_brokers.config import (
    IBDataClientConfig,
    IBExecClientConfig,
    DockerizedIBGatewayConfig,
)
```

## Additional Crypto Adapters

These are available but less documented:
- **BitMEX**: Inverse perpetuals/futures
- **Coinbase International**: Institutional crypto
- **Kraken**: Spot and futures
- **Polymarket**: Binary options (prediction markets, CLOB API)

## Adapter Selection Guide for Crypto HFT

| Need | Adapter |
|------|---------|
| Binance USDT perpetuals | Binance (USDT_FUTURE) |
| Bybit linear perpetuals | Bybit (LINEAR) |
| dYdX v4 perpetuals | dYdX |
| Historical book replay | Tardis |
| US equities L3 | Databento (MBO) |
| Multi-venue execution | Multiple adapters on same TradingNode |
| Custom DEX/venue | Build custom adapter (see python_adapters.md, rust_adapters.md) |

## Common Patterns Across All Adapters

### URL Resolution

All adapters support testnet/mainnet via config flag:

```python
config = SomeExchangeDataClientConfig(testnet=True)  # routes to testnet URLs
```

In Rust: `common/urls.rs` handles URL resolution per environment.

### Rate Limiting

REST endpoints have venue-imposed rate limits. Adapters should:
- Track request counts per endpoint
- Implement backoff when approaching limits
- Queue requests when limits hit
- Log warnings at threshold (e.g., 80% of limit)

### Reconnection

WebSocket clients should:
1. Detect disconnection (ping/pong timeout or read error)
2. Exponential backoff: 1s → 2s → 4s → 8s → max 60s
3. Re-authenticate after reconnection
4. Re-subscribe to all active subscriptions
5. Request snapshot to resync state (for order books)
