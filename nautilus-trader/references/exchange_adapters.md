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
    instrument_provider=InstrumentProviderConfig(load_all=True),
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

# Top Trader Long/Short Ratio (period and limit are configurable)
ratio = await client.send_request(HttpMethod.GET,
    '/futures/data/topLongShortPositionRatio',
    {'symbol': 'BTCUSDT', 'period': '5m', 'limit': '10'})

# 24h Ticker (volume)
ticker = await client.send_request(HttpMethod.GET, '/fapi/v1/ticker/24hr',
    {'symbol': 'BTCUSDT'})
```

**NOTE**: `/fapi/v1/allForceOrders` (liquidations) is deprecated — returns 400 "endpoint out of maintenance".

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

Bybit uses per-endpoint rate limits for REST and separate order rate limits. Check the Bybit API docs for current values.

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

### Order Types

| Type | Supported | Notes |
|------|-----------|-------|
| MARKET | Yes | Immediate execution |
| LIMIT | Yes | `post_only`, `reduce_only` supported |
| STOP_MARKET | Yes | Trigger types: `last_price`, `mark_price`, `index_price` |
| STOP_LIMIT | Yes | Conditional limit |
| TIF | — | GTC, GTD (expires 8 UTC), IOC, FOK |

### Order Book Subscriptions

```python
# Default: 100ms batched, no auth required
strategy.subscribe_order_book_deltas(instrument_id)

# Raw tick-by-tick (requires authentication)
strategy.subscribe_order_book_deltas(
    instrument_id,
    params={"interval": "raw"},  # raw, 100ms, agg2
)
```

Depth options: `1`, `10` (default), `20`

### Rate Limits

Deribit uses a credit-based rate limit system with separate pools for general REST, order operations, and connection limits. Check the Deribit API docs for current values.

### Testnet

```python
config = DeribitDataClientConfig(is_testnet=True)
```

### Factory

```python
node.add_data_client_factory(DERIBIT, DeribitLiveDataClientFactory)
node.add_exec_client_factory(DERIBIT, DeribitLiveExecClientFactory)
```

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
- **Symbology**: `BTC-USD-PERP.HYPERLIQUID`
- **normalize_prices**: `True` by default. Rounds prices to 5 significant figures. Example: `95123.456` → `95123.0`. Disable only if you handle precision yourself
- **Vault trading**: Set `vault_address` to trade on behalf of a vault
- **Order books**: Full snapshots (not deltas). Higher bandwidth than incremental adapters
- **Cross-margin only**: No isolated margin mode
- **On-chain settlement**: All trades settle on Hyperliquid's L1

### Factory

```python
node.add_data_client_factory(HYPERLIQUID, HyperliquidLiveDataClientFactory)
node.add_exec_client_factory(HYPERLIQUID, HyperliquidLiveExecClientFactory)
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

### Factory

```python
node.add_data_client_factory(KRAKEN, KrakenLiveDataClientFactory)
node.add_exec_client_factory(KRAKEN, KrakenLiveExecClientFactory)
```

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

### Factory

```python
node.add_data_client_factory(POLYMARKET_VENUE, PolymarketLiveDataClientFactory)
node.add_exec_client_factory(POLYMARKET_VENUE, PolymarketLiveExecClientFactory)
```

## Betfair

**Venue ID**: `BETFAIR` | **Products**: Sports Betting (BettingInstrument) | **Requires**: `pip install nautilus_trader[betfair]` (needs `betfair_parser`)

### Configuration

```python
from nautilus_trader.adapters.betfair.config import (
    BetfairDataClientConfig, BetfairExecClientConfig,
)
from nautilus_trader.adapters.betfair.factories import (
    BetfairLiveDataClientFactory, BetfairLiveExecClientFactory,
)

data_config = BetfairDataClientConfig(
    account_currency="GBP",            # required
    username="...",
    password="...",
    app_key="...",
    certs_dir="/path/to/certs",        # SSL certificate directory
    subscribe_race_data=False,          # True = live GPS tracking data
    stream_conflate_ms=0,               # 0 = no conflation (default None = Betfair default)
)

exec_config = BetfairExecClientConfig(
    account_currency="GBP",
    username="...", password="...", app_key="...", certs_dir="...",
    use_market_version=False,           # True = price protection via market version
    order_request_rate_per_second=20,
)
```

### Key Details

- **Authentication**: SSL certificate + username/password/app_key. Requires Betfair-issued certificates
- **Instruments**: `BettingInstrument` with full hierarchy: event_type → competition → event → market → selection
- **Back/Lay model**: `OrderSide.BUY` maps to **back** (bet for), `OrderSide.SELL` maps to **lay** (bet against)
- **use_market_version**: When `True`, orders include the latest market version. If the market has moved (version advanced), Betfair lapses the order instead of matching — provides price protection
- **subscribe_race_data**: Enables Race Change Messages (RCM) with live GPS tracking data (Total Performance Data)
- **stream_conflate_ms**: Set to `0` for no conflation (full tick stream). Default `None` uses Betfair's default which applies conflation
- **modify_order**: Supported via `replaceOrders`
- **Custom data types**: `BetfairTicker`, `BetfairStartingPrice`, `BSPOrderBookDelta`

### Factory

```python
from nautilus_trader.model.identifiers import Venue
BETFAIR = Venue("BETFAIR")
node.add_data_client_factory(BETFAIR, BetfairLiveDataClientFactory)
node.add_exec_client_factory(BETFAIR, BetfairLiveExecClientFactory)
```

## Interactive Brokers

**Venue ID**: Varies by exchange MIC (e.g., `XNAS`, `GLBX`, `CBOE`) | **Products**: Equities, Futures, Options, FX, CFDs | **Requires**: `pip install nautilus_trader[ib]` (needs `ibapi`)

See [traditional_finance.md](traditional_finance.md) for full IB details including DockerizedIBGateway, IBContract, options/futures chain building, and session hours.

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

### URL Resolution

All adapters support testnet via config:
```python
config = SomeExchangeConfig(testnet=True)  # routes to testnet URLs
```

### Rate Limiting

Rate limit structures differ significantly across exchanges — weight-based (Binance), per-endpoint (Bybit, Kraken), per-block (dYdX), credit-based (Deribit), on-chain (Hyperliquid), etc. **Always check the exchange's current API docs** as these change frequently. Some exchanges also have different limits for different account tiers.

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

