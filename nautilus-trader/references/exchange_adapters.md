# Exchange Adapters

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

The `-PERP` suffix is mandatory for Binance perpetuals to distinguish from spot.

## Binance

`BINANCE` | Spot, USDT-M Futures, Coin-M Futures

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
    instrument_provider=InstrumentProviderConfig(
        load_ids=frozenset({"BTCUSDT-PERP.BINANCE", "ETHUSDT-PERP.BINANCE"}),
    ),
)
exec_config = BinanceExecClientConfig(
    api_key="...", api_secret="...",
    key_type=BinanceKeyType.ED25519,
    account_type=BinanceAccountType.USDT_FUTURES,
)
```

- `BinanceKeyType`: `HMAC`, `RSA`, `ED25519` — Ed25519 must be **unencrypted** PKCS#8
- `modify_order`: Yes via `PUT /fapi/v1/order` (futures only, **not Spot**)

### Data Types (v1.224.0 tested)

| Subscription | Status | Notes |
|-------------|--------|-------|
| `subscribe_trade_ticks` | WORKS | aggTrade stream |
| `subscribe_quote_ticks` | WORKS | bookTicker (BBO) |
| `subscribe_order_book_deltas` | WORKS | L2 incremental + snapshot rebuild |
| `subscribe_mark_prices` | WORKS | markPrice stream (includes funding) |
| `subscribe_bars` | WORKS | kline stream (1-MINUTE-LAST-EXTERNAL) |
| `subscribe_order_book_depth` | NOT IMPL | Use deltas instead |
| `subscribe_funding_rates` | NOT IMPL | Mark prices include funding |
| `subscribe_index_prices` | NOT IMPL | — |
| `subscribe_instrument_status` | NOT IMPL | — |

### REST Data (OI, Funding, Long/Short)

Not available via subscriptions — use HTTP client:

```python
from nautilus_trader.adapters.binance.factories import get_cached_binance_http_client
from nautilus_trader.adapters.binance import BinanceAccountType
from nautilus_trader.core.nautilus_pyo3 import HttpMethod

client = get_cached_binance_http_client(
    clock=clock, account_type=BinanceAccountType.USDT_FUTURES,
    api_key=api_key, api_secret=api_secret,
)
oi = await client.send_request(HttpMethod.GET, '/fapi/v1/openInterest', {'symbol': 'BTCUSDT'})
fr = await client.send_request(HttpMethod.GET, '/fapi/v1/fundingRate', {'symbol': 'BTCUSDT', 'limit': '3'})
ratio = await client.send_request(HttpMethod.GET, '/futures/data/topLongShortPositionRatio',
    {'symbol': 'BTCUSDT', 'period': '5m', 'limit': '10'})
```

`/fapi/v1/allForceOrders` (liquidations) deprecated — returns 400.

### Order Book Resync: lastUpdateId Protocol

1. Subscribe WS diff depth stream (`U` = first id, `u` = final id)
2. GET `/fapi/v1/depth` → note `lastUpdateId`
3. Discard where `u <= lastUpdateId`
4. First valid: `U <= lastUpdateId + 1 <= u`
5. Subsequent: `U_next == u_prev + 1`

## Bybit

`BYBIT` | Spot, Linear, Inverse, Options

```python
from nautilus_trader.adapters.bybit import (
    BYBIT, BybitDataClientConfig, BybitExecClientConfig, BybitProductType,
    BybitLiveDataClientFactory, BybitLiveExecClientFactory,
)
data_config = BybitDataClientConfig(
    api_key="...", api_secret="...",
    product_types=[BybitProductType.LINEAR], testnet=False,
)
exec_config = BybitExecClientConfig(
    api_key="...", api_secret="...",
    product_types=[BybitProductType.LINEAR], testnet=False,
)
```

- **Data**: OrderBookDelta (L2, 1/50/200/500 levels), TradeTick, QuoteTick, Bar
- **modify_order**: Yes (REST or WS)
- **Order book resync**: `crossSequence` — verify incoming > last processed, on gap → snapshot

## dYdX (v4)

`DYDX` | Perpetual Futures only

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

Cosmos SDK appchain — orders as blockchain transactions via gRPC. Three transports: HTTP (indexer read), WS (indexer read), gRPC (validator write). `grpc_rate_limit_per_second=4`. Multiple gRPC fallback: `base_url_grpc="https://primary:443,https://fallback:443"`.

### Order Classification

| Category | Storage | Expiry | Use Case |
|----------|---------|--------|----------|
| Short-term | In-memory | Block height | IOC/FOK, or GTC/GTD within ~10s |
| Long-term | On-chain | UTC timestamp | GTC (defaults 90-day), GTD |
| Conditional | On-chain | UTC timestamp | Stop-loss, take-profit triggers |

- Market orders: IOC limit at `oracle_price × 1.01` (buy) / `× 0.99` (sell)
- Short-term: broadcast concurrently, expire silently (no cancel events)
- Long-term: serialized via semaphore with exponential backoff
- **Subaccounts** (0-127): independent positions, orders, margin per wallet
- **modify_order**: Not supported — cancel + replace only

### Data Subscriptions

| Type | Live | Hist | Notes |
|------|------|------|-------|
| Trade ticks | Y | Y | — |
| Quote ticks | Y | N | Synthesized from book BBO |
| Order book deltas | Y | Y | L2 only |
| Bars | Y | Y | 1MIN, 5MINS, 15MINS, 30MINS, 1HOUR, 4HOURS, 1DAY |
| Mark/Index prices | Y | N | Via markets channel |
| Funding rates | Y | N | Via markets channel |

## OKX

`OKX` | Spot, Futures, Perpetual Swaps, Options

- Position modes: net, long/short. Trade modes: cross, isolated, cash
- Symbology: `BTC-USDT` (spot), `BTC-USDT-SWAP` (perp), `BTC-USDT-240329` (future)
- **modify_order**: Yes

## Deribit

`DERIBIT` | Futures, Options, Spot, Combos | `pip install nautilus_trader[deribit]`

```python
from nautilus_trader.adapters.deribit import (
    DERIBIT, DeribitDataClientConfig, DeribitExecClientConfig,
    DeribitLiveDataClientFactory, DeribitLiveExecClientFactory, DeribitProductType,
)
data_config = DeribitDataClientConfig(
    api_key="...", api_secret="...",
    product_types=(DeribitProductType.OPTION, DeribitProductType.FUTURE),
    is_testnet=False, update_instruments_interval_mins=60,
    instrument_provider=InstrumentProviderConfig(load_all=True),
)
exec_config = DeribitExecClientConfig(
    api_key="...", api_secret="...",
    product_types=(DeribitProductType.OPTION,), is_testnet=False,
)
```

- **Auth**: HMAC. Scopes: `account:read`, `trade:read_write`, `wallet:read`
- **Product types**: `FUTURE`, `OPTION`, `SPOT`, `FUTURE_COMBO`, `OPTION_COMBO`
- **Inverse**: BTC-settled, `is_inverse=True`
- **modify_order**: Yes via `private/edit`
- **Greeks**: `GreeksCalculator` — see [options_and_greeks.md](options_and_greeks.md)
- **Orders**: MARKET, LIMIT (`post_only`, `reduce_only`), STOP_MARKET/LIMIT (triggers: last/mark/index). TIF: GTC, GTD (expires 8 UTC), IOC, FOK
- **Book**: 100ms batched default. Raw with `params={"interval": "raw"}` (auth required). Depth: 1, 10, 20

## Hyperliquid

`HYPERLIQUID` | Perpetual Futures (DEX) | `pip install nautilus_trader[hyperliquid]`

```python
from nautilus_trader.adapters.hyperliquid import (
    HYPERLIQUID, HyperliquidDataClientConfig, HyperliquidExecClientConfig,
    HyperliquidLiveDataClientFactory, HyperliquidLiveExecClientFactory,
)
data_config = HyperliquidDataClientConfig(testnet=False)
exec_config = HyperliquidExecClientConfig(
    private_key="...", vault_address=None, testnet=False,
    normalize_prices=True,  # rounds to 5 sig figs
)
```

- **Auth**: EVM wallet private key (not API key)
- **Books**: Full snapshots (not deltas). Cross-margin only
- **modify_order**: Yes
- **Filters**: `filters={"market_types": ["perp"]}` — keys: `market_types`/`kinds`, `bases`, `quotes`

## Kraken

`KRAKEN` | Spot, Futures | `pip install nautilus_trader[kraken]`

```python
from nautilus_trader.adapters.kraken import (
    KRAKEN, KrakenDataClientConfig, KrakenExecClientConfig,
    KrakenLiveDataClientFactory, KrakenLiveExecClientFactory,
)
data_config = KrakenDataClientConfig(
    api_key="...", api_secret="...", product_types=None,
    update_instruments_interval_mins=60,
)
exec_config = KrakenExecClientConfig(
    api_key="...", api_secret="...", product_types=None,
    use_spot_position_reports=False, spot_positions_quote_currency="USDT",
)
```

- Separate URL configs: `base_url_http_spot`, `base_url_http_futures`, `base_url_ws_spot`, `base_url_ws_futures`
- Testnet: futures only (no spot testnet). **modify_order**: Yes

## Polymarket

`POLYMARKET` | Binary Options | `pip install nautilus_trader[polymarket]`

```python
from nautilus_trader.adapters.polymarket.config import PolymarketDataClientConfig, PolymarketExecClientConfig
from nautilus_trader.adapters.polymarket.factories import PolymarketLiveDataClientFactory, PolymarketLiveExecClientFactory
from nautilus_trader.adapters.polymarket.common.constants import POLYMARKET_VENUE

data_config = PolymarketDataClientConfig(
    private_key="...", signature_type=0,  # 0=EOA, 1=Email/Magic, 2=Browser proxy
    funder="...", api_key="...", api_secret="...", passphrase="...",
    ws_max_subscriptions_per_connection=200, compute_effective_deltas=False,
)
exec_config = PolymarketExecClientConfig(
    private_key="...", signature_type=0, funder="...",
    api_key="...", api_secret="...", passphrase="...",
)
```

- `BinaryOption` type — YES/NO outcomes as separate instruments. Price: `0.001`–`0.999`
- No `post_only`, `reduce_only`, stop orders, or `modify_order`
- WS: max 200/connection (max 500). Order signing: ~1s latency
- 151k+ instruments — use filters, `load_all=True` is very slow

## Betfair

`BETFAIR` | Sports Betting | `pip install nautilus_trader[betfair]`

```python
from nautilus_trader.adapters.betfair.config import BetfairDataClientConfig, BetfairExecClientConfig
from nautilus_trader.adapters.betfair.factories import BetfairLiveDataClientFactory, BetfairLiveExecClientFactory

data_config = BetfairDataClientConfig(
    account_currency="GBP", username="...", password="...", app_key="...",
    certs_dir="/path/to/certs", subscribe_race_data=False, stream_conflate_ms=0,
)
exec_config = BetfairExecClientConfig(
    account_currency="GBP", username="...", password="...", app_key="...", certs_dir="...",
    use_market_version=False,  # True = price protection
)
```

- **Auth**: SSL cert + username/password/app_key
- **Instruments**: `BettingInstrument` — event_type → competition → event → market → selection
- `BUY` = back, `SELL` = lay. **modify_order**: Yes via `replaceOrders`
- Custom types: `BetfairTicker`, `BetfairStartingPrice`, `BSPOrderBookDelta`

## Interactive Brokers

Venue varies by MIC (`XNAS`, `GLBX`, `CBOE`) | `pip install nautilus_trader[ib]` — see [traditional_finance.md](traditional_finance.md).

## Tardis (Data Only)

`TardisMachineClientConfig(base_url="ws://localhost:8001", book_snapshot_output="deltas")`. Schemas: `book_change`→`OrderBookDelta`, `quote`→`QuoteTick`, `trade`→`TradeTick`, `trade_bar_*`→`Bar`. CSV: `TardisCSVDataLoader.load()` — see [backtesting.md](backtesting.md#tardis-csv-loading).

## Databento (Data Only)

L3 (MBO) support. `MBO`→`OrderBookDelta` (L3), `MBP_1`/`BBO_1S`→`QuoteTick`/`TradeTick`, `MBP_10`→`OrderBookDepth10`, `TRADES`→`TradeTick`, `OHLCV_*`→`Bar`.

## Common Patterns

Factory registration: `node.add_data_client_factory(<VENUE>, <Venue>LiveDataClientFactory)` + same for exec. Import from `adapters.<name>` (except: Polymarket uses `POLYMARKET_VENUE` from `adapters.polymarket.common.constants`, Betfair uses `Venue("BETFAIR")`).

Testnet: `testnet=True` (or `is_testnet=True` for Deribit/dYdX). Reconnection: automatic exponential backoff (1s→60s).

> See SKILL.md for common hallucination guards.

## Rust (Binance)

| Concern | Python | Rust |
|---|---|---|
| Node | `TradingNode(config=...)` | `LiveNodeBuilder::new(trader_id, env)?` |
| Data/Exec client | Config-dict driven | `add_data_client(None, Box::new(Factory::new()), Box::new(config))?` |
| Run | `node.start()` + signal wait | `node.run().await?` (blocks until stop) |
| Spot instruments | Works | Requires `features = ["high-precision"]` |

### LiveNodeBuilder

`BinanceDataClientConfig { product_types: vec![BinanceProductType::UsdM], environment: BinanceEnvironment::Mainnet, api_key, api_secret, ... }` + `BinanceExecClientConfig { trader_id, account_id, product_types, environment, use_ws_trading: true, ... }`. Then `LiveNodeBuilder::new(trader_id, Environment::Live)?.add_data_client(...)?.add_exec_client(...)?.build()?`. Run with `tokio::select!` for timeout/ctrl-c. Data-only: omit `add_exec_client`. See [live_order_test.rs](../examples/live_order_test.rs) for full working example.

Instruments load via HTTP at `connect()`, available in cache **before** `on_start`.

### Binance Spot SBE Overflow Bug

`parse_sbe_lot_size_filter` casts `maxQty` (i64→u64) then scales by 10^8. High-supply tokens (SHIB, PEPE) overflow `u64::MAX`. Fix — `high-precision` switches `QuantityRaw` to `u128`:

```toml
nautilus-model   = { ..., features = ["high-precision"] }
nautilus-binance = { ..., features = ["high-precision"] }
```

`nautilus-binance` includes this as a **default** feature. `default-features = false` silently disables it.

## Related Examples

- [spread_capture_live.py](../examples/spread_capture_live.py) — live spread capture
- [live_data_collector.rs](../examples/live_data_collector.rs) — Rust Binance data collection
- [live_order_test.rs](../examples/live_order_test.rs) — Rust order lifecycle
- [live_spot_test.rs](../examples/live_spot_test.rs) — Rust Spot + high-precision
- [binance_enrichment_actor.py](../examples/binance_enrichment_actor.py) — REST OI + funding actor
