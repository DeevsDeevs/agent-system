# Exchange Adapters

Venue-specific configuration, data types, rate limits, and resync protocols for crypto adapters in NautilusTrader.

## Key Differences Across Adapters

Every exchange adapter has its own configuration, authentication, data availability, and quirks. **Always check the adapter source or NautilusTrader docs for your specific exchange.**

**Important**: Authentication methods, rate limits, fee structures, and API endpoints can change at any time on the exchange side. The examples below show NautilusTrader's config API — verify exchange-side requirements against their current docs.

| Aspect | What Varies |
|--------|-------------|
| Symbology | Different suffixes, delimiters, contract naming per venue |
| Authentication | Ed25519, HMAC, wallet keys, passphrases — check adapter config |
| Data subscriptions | Not all subscription types implemented on all adapters |
| `modify_order` | Supported on most — **not dYdX, not Binance Spot** (cancel+replace only) |
| Rate limits | Weight-based (Binance), per-endpoint (Bybit), per-block (dYdX) |
| Order book resync | Different sequence protocols per venue (lastUpdateId, crossSequence, etc.) |
| REST data endpoints | Different paths, response formats, and available data types |
| Instrument loading | Different config classes and account type enums |

### Symbology

| Venue | Spot | Perpetual | Future | Option/Other |
|-------|------|-----------|--------|--------------|
| Binance | `BTCUSDT.BINANCE` | `BTCUSDT-PERP.BINANCE` | `BTCUSDT-250328.BINANCE` | — |
| Bybit | `BTCUSDT.BYBIT` | `BTCUSDT-LINEAR.BYBIT` | — | — |
| OKX | `BTC-USDT.OKX` | `BTC-USDT-SWAP.OKX` | `BTC-USDT-240329.OKX` | — |
| dYdX | — | `BTC-USD-PERP.DYDX` | — | — |
| Deribit | `BTC_USDC.DERIBIT` | `BTC-PERPETUAL.DERIBIT` | `BTC-28MAR25.DERIBIT` | `BTC-28MAR25-100000-C.DERIBIT` |
| Hyperliquid | — | `BTC-USD-PERP.HYPERLIQUID` | — | — |
| Kraken | `XXBTZUSD.KRAKEN` | (futures separate) | — | — |
| Polymarket | — | — | — | `{token_id}.POLYMARKET` (BinaryOption) |
| Betfair | — | — | — | `{market_id}-{sel_id}-{handicap}.BETFAIR` |

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
    # fast startup — full "SYMBOL.VENUE" strings required, not bare symbols:
    instrument_provider=InstrumentProviderConfig(
        load_ids=frozenset({"BTCUSDT-PERP.BINANCE", "ETHUSDT-PERP.BINANCE"}),
    ),
    # or load_all=True to load all instruments (slow, minutes)
)

exec_config = BinanceExecClientConfig(
    api_key="...", api_secret="...",
    key_type=BinanceKeyType.ED25519,
    account_type=BinanceAccountType.USDT_FUTURES,
)
```

### Authentication

- `BinanceKeyType` enum: `HMAC`, `RSA`, `ED25519` from `nautilus_trader.adapters.binance.common.enums`
- Ed25519 private key must be **unencrypted** PKCS#8 format. Encrypted keys fail at signing
- Auth methods and requirements may change — check the current NautilusTrader and Binance docs

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

Books rebuild via REST snapshot then apply incremental deltas.

| Data Type | WS Source | Notes |
|-----------|-----------|-------|
| `OrderBookDelta` | depth stream | L2 incremental |
| `TradeTick` | aggTrade/trade | Individual trades |
| `QuoteTick` | bookTicker | Best bid/ask |
| `Bar` | kline / REST | All intervals |
| `MarkPriceUpdate` | markPrice | Mark price + funding rate combined. Note: mark price calculation methods differ per exchange (e.g., EMA-based, index-based) |

### REST Data (OI, Funding, Long/Short) — via BinanceHttpClient

NOT available via Strategy subscriptions — use the HTTP client directly:

```python
from nautilus_trader.adapters.binance.factories import get_cached_binance_http_client
from nautilus_trader.adapters.binance import BinanceAccountType
from nautilus_trader.core.nautilus_pyo3 import HttpMethod
import json

client = get_cached_binance_http_client(
    clock=clock, account_type=BinanceAccountType.USDT_FUTURES,
    api_key=api_key, api_secret=api_secret,
)

oi = await client.send_request(HttpMethod.GET, '/fapi/v1/openInterest', {'symbol': 'BTCUSDT'})
fr = await client.send_request(HttpMethod.GET, '/fapi/v1/fundingRate', {'symbol': 'BTCUSDT', 'limit': '3'})
mark = await client.send_request(HttpMethod.GET, '/fapi/v1/premiumIndex', {'symbol': 'BTCUSDT'})
ratio = await client.send_request(HttpMethod.GET, '/futures/data/topLongShortPositionRatio',
    {'symbol': 'BTCUSDT', 'period': '5m', 'limit': '10'})
```

**NOTE**: `/fapi/v1/allForceOrders` (liquidations) deprecated — returns 400.

### Rate Limits

Binance uses a weight-based system for REST and separate order rate limits. Check the Binance API docs for current limits — they change and differ between spot and futures.

### modify_order

Supported via `PUT /fapi/v1/order`. Amends price and/or quantity in place.

### Order Book Resync: lastUpdateId Protocol

1. Subscribe WS diff depth stream (updates have `U` first id, `u` final id)
2. GET `/fapi/v1/depth` → note `lastUpdateId`
3. Discard WS updates where `u <= lastUpdateId`
4. First valid update: `U <= lastUpdateId + 1 <= u`
5. Subsequent: `U_next == u_prev + 1`

### Factory

See [Factory Registration](#factory-registration) for the pattern. Constant: `BINANCE`.

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

### Key Details

- **Data**: OrderBookDelta (L2, 1/50/200/500 levels), TradeTick, QuoteTick, Bar
- **modify_order**: Supported via REST or WS
- **Order book resync**: `crossSequence` — verify incoming > last processed. On gap → snapshot resync

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

- Cosmos SDK appchain — orders submitted as blockchain transactions via gRPC
- Three transport layers: HTTP (indexer read), WebSocket (indexer read), gRPC (validator write)
- Block time ~0.5s (variable)
- `grpc_rate_limit_per_second=4` on exec config — controls order submission throughput
- Multiple gRPC URL fallback: `base_url_grpc="https://primary:443,https://fallback:443"`

### Order Classification

| Category | Storage | Expiry | Use Case |
|----------|---------|--------|----------|
| Short-term | In-memory | Block height | IOC/FOK, or GTC/GTD within ~10s |
| Long-term | On-chain | UTC timestamp | GTC (defaults 90-day), GTD |
| Conditional | On-chain | UTC timestamp | Stop-loss, take-profit triggers |

- Market orders: aggressive IOC limit at `oracle_price × 1.01` (buy) / `× 0.99` (sell)
- Short-term orders broadcast concurrently, expire silently without cancel events
- Long-term orders serialized via semaphore with exponential backoff
- **Subaccounts** (0-127) per wallet — each has independent positions, orders, margin. Configure via `DydxExecClientConfig(subaccount=0)`

### Data Subscriptions

| Type | Live | Historical | Notes |
|------|------|-----------|-------|
| Trade ticks | Yes | Yes | — |
| Quote ticks | Yes | No | Synthesized from order book top-of-book |
| Order book deltas | Yes | Yes | L2 depth only |
| Bars | Yes | Yes | 1MIN, 5MINS, 15MINS, 30MINS, 1HOUR, 4HOURS, 1DAY |
| Mark/Index prices | Yes | No | Via markets channel |
| Funding rates | Yes | No | Via markets channel |

### Rate Limits

dYdX rate limits are blockchain-based — short-term orders have per-subaccount limits, long-term orders are constrained by block time. The `grpc_rate_limit_per_second` config controls adapter-side throttling. Check dYdX docs for current limits.

### modify_order

**Not supported.** Cancel + replace only.

## OKX

**Venue ID**: `OKX` | **Products**: Spot, Futures, Perpetual Swaps, Options | **Rust crate**: `crates/adapters/okx/`

### Key Details

- Supports net and long/short position modes
- Trade modes: cross margin, isolated margin, cash
- Symbology: `BTC-USDT` (spot), `BTC-USDT-SWAP` (perp), `BTC-USDT-240329` (future)
- **modify_order**: Supported

## Deribit

**Venue ID**: `DERIBIT` | **Products**: Futures, Options, Spot, Future Combos, Option Combos | **Requires**: `pip install nautilus_trader[deribit]`

### Configuration

```python
from nautilus_trader.adapters.deribit import (
    DERIBIT, DeribitDataClientConfig, DeribitExecClientConfig,
    DeribitLiveDataClientFactory, DeribitLiveExecClientFactory,
    DeribitProductType,
)
from nautilus_trader.config import InstrumentProviderConfig

data_config = DeribitDataClientConfig(
    api_key="...",
    api_secret="...",
    product_types=(DeribitProductType.OPTION, DeribitProductType.FUTURE),
    is_testnet=False,                  # note: is_testnet, not testnet
    update_instruments_interval_mins=60,
    instrument_provider=InstrumentProviderConfig(load_all=True),
)

exec_config = DeribitExecClientConfig(
    api_key="...", api_secret="...",
    product_types=(DeribitProductType.OPTION,),
    is_testnet=False,
)
```

### Key Details

- **Authentication**: HMAC (api_key + api_secret). Required scopes: `account:read`, `trade:read_write`, `wallet:read`
- **Product types**: `DeribitProductType.FUTURE`, `OPTION`, `SPOT`, `FUTURE_COMBO`, `OPTION_COMBO`
- **Symbology**: `BTC-28MAR25-100000-C.DERIBIT` (options), `BTC-28MAR25.DERIBIT` (futures), `BTC_USDC.DERIBIT` (spot), `BTC-PERPETUAL.DERIBIT` (perps)
- **Instruments**: `CryptoOption` for options, `CryptoFuture` for futures
- **Inverse**: Deribit options and futures are BTC-settled (inverse). `is_inverse=True`
- **modify_order**: Supported via `private/edit`
- **Option greeks**: Use `GreeksCalculator` — see [options_and_greeks.md](options_and_greeks.md)
- **Matching engine**: Equinix LD4, Slough, UK

- **Order types**: MARKET, LIMIT (`post_only`, `reduce_only`), STOP_MARKET/LIMIT (triggers: last/mark/index price). TIF: GTC, GTD (expires 8 UTC), IOC, FOK
- **Order book**: Default 100ms batched. Raw tick-by-tick with `params={"interval": "raw"}` (requires auth). Depth: 1, 10 (default), 20

### Testnet

`DeribitDataClientConfig(is_testnet=True)` — note `is_testnet`, not `testnet`.

## Hyperliquid

**Venue ID**: `HYPERLIQUID` | **Products**: Perpetual Futures (DEX) | **Requires**: `pip install nautilus_trader[hyperliquid]`

### Configuration

```python
from nautilus_trader.adapters.hyperliquid import (
    HYPERLIQUID, HyperliquidDataClientConfig, HyperliquidExecClientConfig,
    HyperliquidLiveDataClientFactory, HyperliquidLiveExecClientFactory,
)

data_config = HyperliquidDataClientConfig(
    testnet=False,
)

exec_config = HyperliquidExecClientConfig(
    private_key="...",                  # EVM wallet private key
    vault_address=None,                 # for vault trading (optional)
    testnet=False,
    normalize_prices=True,              # default: True — rounds to 5 sig figs
)
```

### Key Details

- **Authentication**: EVM wallet private key (not API key). Sign orders with wallet
- **Symbology**: `BTC-USD-PERP.HYPERLIQUID` (perps), `PURR-USDC-SPOT.HYPERLIQUID` (spot)
- **normalize_prices**: `True` by default. Rounds prices to 5 significant figures (`95123.456` → `95123.0`, `1.23456` → `1.2346`). Disable only if you handle precision yourself
- **Vault trading**: Set `vault_address` to trade on behalf of a vault. Wallet must be authorized trader
- **Order books**: Full snapshots (not deltas). Higher bandwidth, no gap detection needed
- **Cross-margin only**: No isolated margin mode
- **On-chain settlement**: All trades settle on Hyperliquid's L1
- **modify_order**: Supported

### Instrument Provider Filters

```python
from nautilus_trader.config import InstrumentProviderConfig

instrument_provider=InstrumentProviderConfig(
    load_all=True,
    filters={"market_types": ["perp"]},  # or "kinds"
)
# Filter keys: market_types/kinds: ["perp","spot"] | bases: ["BTC","ETH"] | quotes: ["USDC"]
```

## Kraken

**Venue ID**: `KRAKEN` | **Products**: Spot, Futures | **Requires**: `pip install nautilus_trader[kraken]`

### Configuration

```python
from nautilus_trader.adapters.kraken import (
    KRAKEN, KrakenDataClientConfig, KrakenExecClientConfig,
    KrakenLiveDataClientFactory, KrakenLiveExecClientFactory,
)

data_config = KrakenDataClientConfig(
    api_key="...",
    api_secret="...",
    product_types=None,                 # load both spot and futures
    update_instruments_interval_mins=60,
)

exec_config = KrakenExecClientConfig(
    api_key="...", api_secret="...",
    product_types=None,
    use_spot_position_reports=False,    # if True, subscribes to spot position updates
    spot_positions_quote_currency="USDT",
)
```

### Key Details

- **Authentication**: API key + secret (separate keys for spot vs futures may be needed)
- **Separate URLs**: `base_url_http_spot`, `base_url_http_futures`, `base_url_ws_spot`, `base_url_ws_futures`
- **Testnet**: Futures testnet only (no spot testnet)
- **modify_order**: Supported

## Polymarket

**Venue ID**: `POLYMARKET` | **Products**: Binary Options (prediction markets) | **Requires**: `pip install nautilus_trader[polymarket]` (needs `py_clob_client`)

### Configuration

```python
from nautilus_trader.adapters.polymarket.config import (
    PolymarketDataClientConfig, PolymarketExecClientConfig,
)
from nautilus_trader.adapters.polymarket.factories import (
    PolymarketLiveDataClientFactory, PolymarketLiveExecClientFactory,
)
from nautilus_trader.adapters.polymarket.common.constants import POLYMARKET_VENUE

data_config = PolymarketDataClientConfig(
    private_key="...",                  # Polygon wallet key
    signature_type=0,                   # 0=EOA, 1=Email/Magic, 2=Browser proxy
    funder="...",                       # Polygon wallet address
    api_key="...",
    api_secret="...",
    passphrase="...",
    ws_max_subscriptions_per_connection=200,  # Polymarket limit: 500
    compute_effective_deltas=False,     # ~1ms overhead if True
)

exec_config = PolymarketExecClientConfig(
    private_key="...",
    signature_type=0,
    funder="...",
    api_key="...", api_secret="...", passphrase="...",
)
```

### Key Details

- **Authentication**: Polygon (MATIC) wallet + API credentials. Orders signed on-chain
- **Instruments**: `BinaryOption` type. Each market has YES/NO outcomes as separate instruments
- **Instrument IDs**: Token ID based, loaded via instrument provider
- **Price range**: `0.001` to `0.999` (probability)
- **Execution constraints**: No `post_only`, no `reduce_only`, no stop orders, no `modify_order`. Market BUY orders may need `quote_quantity=True`
- **WS subscriptions**: Max 200 per connection (configurable, Polymarket max 500)
- **Order signing latency**: ~1s due to on-chain signature
- **151k+ instruments**: Use instrument provider filters — `load_all=True` will be very slow

## Betfair

**Venue ID**: `BETFAIR` | **Products**: Sports Betting (BettingInstrument) | **Requires**: `pip install nautilus_trader[betfair]` (needs `betfair_parser`)

### Configuration

```python
from nautilus_trader.adapters.betfair.config import BetfairDataClientConfig, BetfairExecClientConfig
from nautilus_trader.adapters.betfair.factories import BetfairLiveDataClientFactory, BetfairLiveExecClientFactory

data_config = BetfairDataClientConfig(
    account_currency="GBP", username="...", password="...", app_key="...",
    certs_dir="/path/to/certs",        # SSL certificate directory
    subscribe_race_data=False,          # True = live GPS tracking data
    stream_conflate_ms=0,               # 0 = no conflation
)

exec_config = BetfairExecClientConfig(
    account_currency="GBP", username="...", password="...", app_key="...", certs_dir="...",
    use_market_version=False,           # True = price protection via market version
)
```

### Key Details

- **Authentication**: SSL certificate + username/password/app_key
- **Instruments**: `BettingInstrument` — hierarchy: event_type → competition → event → market → selection
- **Back/Lay**: `OrderSide.BUY` = back (bet for), `OrderSide.SELL` = lay (bet against)
- **use_market_version**: `True` → order lapses if market has moved (price protection)
- **modify_order**: Supported via `replaceOrders`
- **Custom data types**: `BetfairTicker`, `BetfairStartingPrice`, `BSPOrderBookDelta`

## Interactive Brokers

**Venue ID**: Varies by exchange MIC (e.g., `XNAS`, `GLBX`, `CBOE`) | **Products**: Equities, Futures, Options, FX, CFDs | **Requires**: `pip install nautilus_trader[ib]` (needs `ibapi`)

See [traditional_finance.md](traditional_finance.md) for full IB details including DockerizedIBGateway, IBContract, options/futures chain building, and session hours.

## Tardis (Data Provider Only)

**No execution** — historical crypto data replay. Config: `TardisMachineClientConfig(base_url="ws://localhost:8001", book_snapshot_output="deltas")`. Schemas: `book_change` → `OrderBookDelta`, `quote` → `QuoteTick`, `trade` → `TradeTick`, `trade_bar_*` → `Bar`. CSV loading via `TardisCSVDataLoader.load()` — see [backtesting.md](backtesting.md#tardis-csv-loading).

## Databento (Data Provider Only)

**No execution** — US equities, futures, options. L3 (MBO) support. Schemas: `MBO` → `OrderBookDelta` (L3), `MBP_1`/`BBO_1S` → `QuoteTick`/`TradeTick`, `MBP_10` → `OrderBookDepth10`, `TRADES` → `TradeTick`, `OHLCV_*` → `Bar`.

## modify_order Support Matrix

| Venue | modify_order | Fallback |
|-------|-------------|----------|
| Binance Futures | Yes (`PUT /fapi/v1/order`) | Cancel + replace |
| Binance Spot | **No** (adapter rejects) | Cancel + replace only |
| Bybit | Yes (REST/WS) | Cancel + replace |
| dYdX | **No** | Cancel + replace only |
| OKX | Yes | Cancel + replace |
| Deribit | Yes (`private/edit`) | Cancel + replace |
| Hyperliquid | Yes | Cancel + replace |
| Kraken | Yes | Cancel + replace |
| Polymarket | **No** | Cancel + replace only |
| Betfair | Yes (`replaceOrders`) | Cancel + replace |

**Binance Spot limitation** (verified): The adapter explicitly rejects `modify_order` on Spot — "only supported for USDT_FUTURES and COIN_FUTURES account types". Use cancel + new order on Spot.

If your strategy uses `modify_order` and the target exchange/account type doesn't support it, use cancel + new order instead. The adapter will not auto-fallback — it will error.

## Common Patterns

### Factory Registration

All adapters follow the same pattern — import venue constant and factory classes, register with node:

```python
from nautilus_trader.adapters.<adapter> import (
    <VENUE>, <Venue>LiveDataClientFactory, <Venue>LiveExecClientFactory,
)
node.add_data_client_factory(<VENUE>, <Venue>LiveDataClientFactory)
node.add_exec_client_factory(<VENUE>, <Venue>LiveExecClientFactory)
```

| Venue | Constant | Import Path | Notes |
|-------|----------|-------------|-------|
| Binance | `BINANCE` | `adapters.binance` | |
| Bybit | `BYBIT` | `adapters.bybit` | |
| dYdX | `DYDX` | `adapters.dydx` | |
| Deribit | `DERIBIT` | `adapters.deribit` | |
| Hyperliquid | `HYPERLIQUID` | `adapters.hyperliquid` | |
| Kraken | `KRAKEN` | `adapters.kraken` | |
| Polymarket | `POLYMARKET_VENUE` | `adapters.polymarket.common.constants` + `adapters.polymarket.factories` | |
| Betfair | `Venue("BETFAIR")` | `adapters.betfair.factories` | Construct manually |

### Testnet

All adapters support testnet via config: `testnet=True` (or `is_testnet=True` for Deribit/dYdX).

### Rate Limiting

Rate limit structures differ across exchanges — weight-based (Binance), per-endpoint (Bybit, Kraken), per-block (dYdX), credit-based (Deribit), on-chain (Hyperliquid). **Always check the exchange's current API docs.**

Adapters internally manage rate limits. `RiskEngineConfig` provides order-level rate protection (see [execution.md](execution.md#riskengine)).

**Strategy-level REST polling**: `requests_per_min = instruments × polls_per_min`. Budget 50% headroom.

### Reconnection

Handled automatically by adapters: exponential backoff (1s → 60s), re-authenticate, re-subscribe, request book snapshots. See [operations.md](operations.md#reconnection-handling) for strategy-level handling.

## Anti-Hallucination Notes

| Hallucination | Reality |
|--------------|---------|
| `BinanceAccountType.USDT_FUTURE` | `USDT_FUTURES` (with S) |
| `testnet=True` for Deribit/dYdX | `is_testnet=True` — note `is_testnet`, not `testnet` |
| `modify_order` works on all venues | Not supported on dYdX, Binance Spot, Polymarket — adapter errors, no auto-fallback |
| `DYDXDataClientConfig` (uppercase) | `DydxDataClientConfig` (mixed case Dydx) |
| `-PERP` suffix optional for Binance | Mandatory — `BTCUSDT-PERP.BINANCE` for perpetuals, `BTCUSDT.BINANCE` for spot |
| `subscribe_instrument_status()` on Binance | Binance does NOT implement this |

## Rust (Binance)

The Binance adapter is pure Rust — no PyO3 headers, no Python dependency.

| Concern | Python | Rust |
|---|---|---|
| Node class | `TradingNode(config=TradingNodeConfig(...))` | `LiveNodeBuilder::new(trader_id, env)?` builder pattern |
| Adding data client | Config-dict driven | `add_data_client(None, Box::new(BinanceDataClientFactory::new()), Box::new(config))?` |
| Adding exec client | Config-dict driven | `add_exec_client(None, Box::new(BinanceExecutionClientFactory::new()), Box::new(config))?` |
| Run | `node.start()` + signal wait | `node.run().await?` (async, blocks until stop) |
| Spot instrument loading | Works | Requires `features = ["high-precision"]` — see Spot SBE Overflow below |

### LiveNodeBuilder

```rust
use nautilus_binance::{
    common::enums::{BinanceEnvironment, BinanceProductType},
    config::{BinanceDataClientConfig, BinanceExecClientConfig},
    factories::{BinanceDataClientFactory, BinanceExecutionClientFactory},
};
use nautilus_common::enums::Environment;
use nautilus_live::builder::LiveNodeBuilder;
use nautilus_model::identifiers::{AccountId, TraderId};

let data_config = BinanceDataClientConfig {
    product_types: vec![BinanceProductType::UsdM],  // or Spot, CoinM
    environment: BinanceEnvironment::Mainnet,
    base_url_http: None,
    base_url_ws: None,
    api_key: std::env::var("BINANCE_LINEAR_API_KEY").ok(),
    api_secret: std::env::var("BINANCE_LINEAR_API_SECRET").ok(),
};

let exec_config = BinanceExecClientConfig {
    trader_id: trader_id.clone(),
    account_id: AccountId::from("BINANCE-001"),
    product_types: vec![BinanceProductType::UsdM],
    environment: BinanceEnvironment::Mainnet,
    base_url_http: None,
    base_url_ws: None,
    base_url_ws_trading: None,
    use_ws_trading: true,
    api_key,
    api_secret,
};

let mut node = LiveNodeBuilder::new(trader_id, Environment::Live)?
    .with_timeout_connection(30)
    .with_reconciliation(false)
    .add_data_client(None, Box::new(BinanceDataClientFactory::new()), Box::new(data_config))?
    .add_exec_client(None, Box::new(BinanceExecutionClientFactory::new()), Box::new(exec_config))?
    .build()?;

node.add_strategy(my_strategy)?;

// Timed run — stops after N seconds
tokio::select! {
    result = node.run() => result?,
    _ = tokio::time::sleep(std::time::Duration::from_secs(60)) => {
        node.stop().await?;
    }
}
```

Data-only node (no exec client): omit `add_exec_client` — node connects and streams normally, emits harmless warnings.

`BinanceProductType`: `Spot`, `UsdM` (perpetuals/futures), `CoinM`.

### Instrument Availability at Startup

Binance loads all instruments via HTTP at `connect()` time, **before** `on_start` fires. Instruments are already in cache:

```rust
fn on_start(&mut self) -> Result<()> {
    let cache = self.cache_rc();
    for id in &self.instrument_ids {
        if let Some(inst) = cache.borrow().instrument(id) {
            self.instruments.push(inst.clone());
        }
    }
    // subscribe_instrument only delivers future updates (e.g. expiry rollovers)
    for id in self.instrument_ids.clone() {
        self.subscribe_quotes(id, None, None);
    }
    Ok(())
}
```

### Binance Spot SBE Overflow Bug

**Root cause**: `parse_sbe_lot_size_filter` in `nautilus-binance/src/common/parse.rs` reads `maxQty` as `i64`, casts via unchecked `as u64`, then scales by 10^8 for fixed-point `QuantityRaw`. High-supply tokens (SHIB, PEPE) have `maxQty` in the trillions: `9_000_000_000_000 × 10^8 = 9×10^20` overflows `u64::MAX` (1.8×10^19) and panics.

**Fix**: Enable `high-precision` in `Cargo.toml` — switches `QuantityRaw` from `u64` to `u128`:

```toml
nautilus-model   = { ..., features = ["high-precision"] }
nautilus-binance = { ..., features = ["high-precision"] }
```

`nautilus-binance` includes `high-precision` as a **default** feature. Using `default-features = false` silently disables it — adding it back explicitly is the correct fix.

Affects live connections only (instrument HTTP endpoint). Backtests with `TestInstrumentProvider` stubs are unaffected.


## Related Examples

- [spread_capture_live.py](../examples/spread_capture_live.py) — live spread capture strategy
- [live_data_collector.rs](../examples/live_data_collector.rs) — Rust LiveNode + Binance data collection
- [live_order_test.rs](../examples/live_order_test.rs) — Rust full order lifecycle (live)
- [live_spot_test.rs](../examples/live_spot_test.rs) — Rust Spot + high-precision
- [binance_enrichment_actor.py](../examples/binance_enrichment_actor.py) — Actor polling REST for OI + funding
