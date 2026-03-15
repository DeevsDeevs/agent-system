---
name: nautilus-docs
description: >
  NautilusTrader trading platform — strategies, backtesting, live deployment, order management,
  market data, Rust native binaries. Use when writing, reviewing, or debugging NautilusTrader
  code (Python or Rust), configuring venue adapters, or answering questions about the platform.
argument-hint: "[topic or question]"
---

# NautilusTrader v1.224.0

Read the relevant doc before generating code or answering questions. Docs are a git submodule (sparse checkout, `docs/` only) from [nautilus_trader](https://github.com/nautechsystems/nautilus_trader). Use `${CLAUDE_SKILL_DIR}/references/upstream/docs/` for doc file paths.

## Doc Navigator

### Concepts

| Topic | Doc |
|-------|-----|
| Architecture / overview | [architecture.md](references/upstream/docs/concepts/architecture.md), [overview.md](references/upstream/docs/concepts/overview.md) |
| Actor development | [actors.md](references/upstream/docs/concepts/actors.md) |
| Strategy development | [strategies.md](references/upstream/docs/concepts/strategies.md) |
| Backtesting | [backtesting.md](references/upstream/docs/concepts/backtesting.md) |
| Live trading | [live.md](references/upstream/docs/concepts/live.md) |
| Order types & execution | [orders.md](references/upstream/docs/concepts/orders.md), [execution.md](references/upstream/docs/concepts/execution.md) |
| Order book | [order_book.md](references/upstream/docs/concepts/order_book.md) |
| Data types & custom data | [data.md](references/upstream/docs/concepts/data.md), [custom_data.md](references/upstream/docs/concepts/custom_data.md) |
| Instruments | [instruments.md](references/upstream/docs/concepts/instruments.md) |
| Value types (Price, Quantity, Money) | [value_types.md](references/upstream/docs/concepts/value_types.md) |
| Positions & PnL | [positions.md](references/upstream/docs/concepts/positions.md) |
| Cache | [cache.md](references/upstream/docs/concepts/cache.md) |
| MessageBus | [message_bus.md](references/upstream/docs/concepts/message_bus.md) |
| Portfolio | [portfolio.md](references/upstream/docs/concepts/portfolio.md) |
| Options & Greeks | [options.md](references/upstream/docs/concepts/options.md), [greeks.md](references/upstream/docs/concepts/greeks.md) |
| Logging | [logging.md](references/upstream/docs/concepts/logging.md) |
| Reports & analysis | [reports.md](references/upstream/docs/concepts/reports.md) |
| Visualization | [visualization.md](references/upstream/docs/concepts/visualization.md) |
| Adapter development | [concepts/adapters.md](references/upstream/docs/concepts/adapters.md), [developer_guide/adapters.md](references/upstream/docs/developer_guide/adapters.md) |

### Venue Integrations

| Venue | Doc |
|-------|-----|
| Binance | [binance.md](references/upstream/docs/integrations/binance.md) |
| Bybit | [bybit.md](references/upstream/docs/integrations/bybit.md) |
| OKX | [okx.md](references/upstream/docs/integrations/okx.md) |
| dYdX | [dydx.md](references/upstream/docs/integrations/dydx.md) |
| Deribit | [deribit.md](references/upstream/docs/integrations/deribit.md) |
| Hyperliquid | [hyperliquid.md](references/upstream/docs/integrations/hyperliquid.md) |
| Kraken | [kraken.md](references/upstream/docs/integrations/kraken.md) |
| Interactive Brokers | [ib.md](references/upstream/docs/integrations/ib.md) |
| Betfair | [betfair.md](references/upstream/docs/integrations/betfair.md) |
| Polymarket | [polymarket.md](references/upstream/docs/integrations/polymarket.md) |
| Databento | [databento.md](references/upstream/docs/integrations/databento.md) |
| Tardis | [tardis.md](references/upstream/docs/integrations/tardis.md) |
| BitMEX | [bitmex.md](references/upstream/docs/integrations/bitmex.md) |
| AX Exchange | [architect_ax.md](references/upstream/docs/integrations/architect_ax.md) |

### Dev / Setup

| Topic | Doc |
|-------|-----|
| Installation | [installation.md](references/upstream/docs/getting_started/installation.md) |
| Quickstart | [quickstart.py](references/upstream/docs/getting_started/quickstart.py) |
| Environment setup | [environment_setup.md](references/upstream/docs/developer_guide/environment_setup.md) |
| Rust development | [rust.md](references/upstream/docs/developer_guide/rust.md) |
| Testing | [testing.md](references/upstream/docs/developer_guide/testing.md) |
| Coding standards | [coding_standards.md](references/upstream/docs/developer_guide/coding_standards.md) |
| Benchmarking | [benchmarking.md](references/upstream/docs/developer_guide/benchmarking.md) |
| FFI | [ffi.md](references/upstream/docs/developer_guide/ffi.md) |

### Tutorials

| Tutorial | Doc |
|----------|-----|
| FX mean reversion (AX) | [ax_fx_mean_reversion.md](references/upstream/docs/tutorials/ax_fx_mean_reversion.md) |
| Gold book imbalance (AX) | [ax_gold_book_imbalance.md](references/upstream/docs/tutorials/ax_gold_book_imbalance.md) |
| dYdX grid market maker | [dydx_grid_market_maker.md](references/upstream/docs/tutorials/dydx_grid_market_maker.md) |
| BitMEX grid market maker | [bitmex_grid_market_maker.md](references/upstream/docs/tutorials/bitmex_grid_market_maker.md) |
| Backtest Binance orderbook | [backtest_binance_orderbook.py](references/upstream/docs/tutorials/backtest_binance_orderbook.py) |
| Backtest Bybit orderbook | [backtest_bybit_orderbook.py](references/upstream/docs/tutorials/backtest_bybit_orderbook.py) |
| Backtest FX bars | [backtest_fx_bars.py](references/upstream/docs/tutorials/backtest_fx_bars.py) |
| Databento data catalog | [databento_data_catalog.py](references/upstream/docs/tutorials/databento_data_catalog.py) |
| Loading external data | [loading_external_data.py](references/upstream/docs/tutorials/loading_external_data.py) |

## Supporting Files

- **[battle_tested.md](references/battle_tested.md)** — Non-obvious patterns verified against live exchanges. Load when: writing on_start() ordering, market making, signal pipelines, backtest config, venue-specific gotchas, performance optimization.
- **[REBUILD.md](references/REBUILD.md)** — Meta-prompt for regenerating this skill when NautilusTrader API changes.

## Rust Standalone Binary

External Rust binaries work via git dependencies. No need to clone the nautilus workspace. Requires Rust 1.94+, edition 2024.

All crates: `{ git = "https://github.com/nautechsystems/nautilus_trader.git" }`. Add `default-features = false` if no Python headers. Naming: `nautilus-{name}` in Cargo.toml → `nautilus_{name}` in Rust.

### Crate Map

| Layer | Crate | Provides |
|-------|-------|----------|
| Foundation | `nautilus-core` | Primitives, FFI |
| Foundation | `nautilus-model` | `InstrumentId`, `TraderId`, `Price`, `Quantity`, orders, positions, instruments |
| Foundation | `nautilus-common` | `DataActor`, `DataActorCore`, `DataActorConfig`, timers, message bus, component lifecycle |
| Trading | `nautilus-trading` | `Strategy` trait (extends DataActor), order/position management |
| Runtime | `nautilus-live` | `LiveNode`, `LiveNodeBuilder` |
| Runtime | `nautilus-backtest` | `BacktestNode`, `BacktestEngine` — needs `features = ["streaming"]` |
| Infra | `nautilus-indicators` | EMA, SMA, RSI, MACD, Bollinger — enable via `nautilus-trading` `features = ["examples"]` |
| Infra | `nautilus-persistence` | Parquet catalog, DataFusion |
| Infra | `nautilus-serialization` | Arrow, MessagePack encoding |
| Infra | `nautilus-network` | HTTP/WebSocket clients |
| Infra | `nautilus-cryptography` | HMAC, Ed25519 signing |
| Infra | `nautilus-infrastructure` | Redis, logging, monitoring |
| Infra | `nautilus-analysis` | Performance stats |
| Engine | `nautilus-data` | Data engine internals |
| Engine | `nautilus-execution` | Order routing internals |
| Engine | `nautilus-portfolio` | Account/position aggregation |
| Engine | `nautilus-risk` | Pre-trade checks |
| System | `nautilus-system` | Kernel orchestration |
| Test | `nautilus-testkit` | Test fixtures, mock instruments |

### Adapter Crates

All follow `nautilus-{venue}` naming:

| Crate | Markets |
|-------|---------|
| `nautilus-binance` | Spot, USDT-M, COIN-M |
| `nautilus-bybit` | Spot, Perpetuals |
| `nautilus-okx` | Spot, Futures, Options |
| `nautilus-kraken` | Spot, Futures |
| `nautilus-bitmex` | Perpetuals |
| `nautilus-deribit` | Options |
| `nautilus-dydx` | Perpetuals (DEX) |
| `nautilus-hyperliquid` | Perpetuals (DEX) |
| `nautilus-databento` | Historical data provider |
| `nautilus-tardis` | Historical data provider |
| `nautilus-betfair` | Betting exchange |
| `nautilus-polymarket` | Prediction markets |
| `nautilus-architect-ax` | FX, commodities |
| `nautilus-sandbox` | Simulated exchange |

### Which crates for your task

| Use case | Crates |
|----------|--------|
| Data-only live actor | `nautilus-common`, `nautilus-model`, `nautilus-live`, `nautilus-{venue}` |
| Live strategy (orders) | above + `nautilus-trading` |
| Backtest | `nautilus-common`, `nautilus-model`, `nautilus-backtest` (+ `streaming`), `nautilus-trading` |
| With indicators | add `nautilus-trading` with `features = ["examples"]` |
| With Parquet catalog | add `nautilus-persistence` |
| `high-precision` (128-bit) | Default on most crates — `default-features = false` disables it, re-add explicitly |

### DataActor pattern (the only way to build custom Rust actors)

```rust
use std::ops::{Deref, DerefMut};
use nautilus_common::actor::{DataActor, DataActorConfig, DataActorCore};
use nautilus_model::data::TradeTick;
use nautilus_model::identifiers::InstrumentId;

#[derive(Debug)]
struct MyActor {
    core: DataActorCore,  // REQUIRED — blanket impls derive Actor+Component from this
    instrument_id: InstrumentId,
}

impl Deref for MyActor {
    type Target = DataActorCore;
    fn deref(&self) -> &Self::Target { &self.core }
}
impl DerefMut for MyActor {
    fn deref_mut(&mut self) -> &mut Self::Target { &mut self.core }
}

impl DataActor for MyActor {
    fn on_start(&mut self) -> anyhow::Result<()> {
        self.subscribe_trades(self.instrument_id, None, None); // 3 args
        Ok(())
    }
    fn on_trade(&mut self, trade: &TradeTick) -> anyhow::Result<()> {
        let px = trade.price.as_f64();
        let qty = trade.size.as_f64();
        // logic here
        Ok(())
    }
    fn on_stop(&mut self) -> anyhow::Result<()> { Ok(()) } // MUST implement — warns if missing
}

// Constructor:
impl MyActor {
    fn new(instrument_id: InstrumentId) -> Self {
        Self {
            core: DataActorCore::new(DataActorConfig { actor_id: Some("MyActor-001".into()), ..Default::default() }),
            instrument_id,
        }
    }
}
```

### LiveNode + Binance wiring

```rust
use nautilus_binance::common::enums::{BinanceEnvironment, BinanceProductType};
use nautilus_binance::config::BinanceDataClientConfig;
use nautilus_binance::factories::BinanceDataClientFactory;
use nautilus_common::enums::Environment;
use nautilus_live::node::LiveNode;
use nautilus_model::identifiers::TraderId;

let data_config = BinanceDataClientConfig {
    product_types: vec![BinanceProductType::UsdM],  // or Spot, CoinM
    environment: BinanceEnvironment::Mainnet,       // or Testnet
    api_key: Some(key),
    api_secret: Some(secret),  // Ed25519: wrap in PEM headers
    ..Default::default()
};

let mut node = LiveNode::builder(TraderId::from("MY-001"), Environment::Live)?
    .with_name("MyNode")
    .add_data_client(None, Box::new(BinanceDataClientFactory::new()), Box::new(data_config))?
    .build()?;

node.add_actor(my_actor)?;
node.run().await?;
```

**Do NOT use `env_logger`** — Nautilus registers its own `log` backend. `env_logger::init()` will crash with "logger already initialized". Use `log::info!()` directly.

## Common Hallucinations

These do NOT exist in v1.224.0:

| Hallucination | Reality |
|--------------|---------|
| `cache.position_for_instrument(id)` | `cache.positions_open(instrument_id=id)` returns list |
| `engine.trader.cache` | `engine.cache` directly |
| `book.filtered_view()` | Use `cache.own_order_book()` |
| `book.get_avg_px_qty_for_exposure()` | Use `get_avg_px_for_quantity()` + `get_quantity_for_price()` |
| `level.count` / `book.count` | `book.update_count` |
| `BookOrder(price=, size=, side=)` | 4 positional args: `BookOrder(OrderSide.BUY, Price, Quantity, order_id=0)`. Import from `model.data`, NOT `model.book` |
| `GenericDataWrangler` | TradeTickDataWrangler, QuoteTickDataWrangler, OrderBookDeltaDataWrangler, BarDataWrangler |
| `catalog.data_types()` | `catalog.list_data_types()` |
| `BacktestEngineConfig` from `nautilus_trader.config` | from `nautilus_trader.backtest.engine` or `nautilus_trader.backtest.config` |
| `FillModel(prob_fill_on_stop=...)` | Only: prob_fill_on_limit, prob_slippage, random_seed |
| `LoggingConfig(log_file_path=)` | `log_directory=` |
| `cache.orders_filled()` | `cache.orders_closed()` |
| `pos.signed_qty / Decimal(...)` | TypeError: returns float — `Decimal(str(pos.signed_qty))` |
| `from nautilus_trader.trading.actor` | `from nautilus_trader.common.actor import Actor` |
| `from nautilus_trader.indicators.ema` | `from nautilus_trader.indicators import ExponentialMovingAverage` |
| `BollingerBands(20)` | `BollingerBands(20, 2.0)` — k mandatory |
| `MACD(12, 26, 9)` | 3rd param is `MovingAverageType`, not signal_period |
| `publish_signal(value=dict(...))` | KeyError — values must be int, float, or str |
| Encrypted Ed25519 private key | Must be unencrypted PKCS#8 |
| `on_timer()` as callback | `clock.set_timer(callback=handler)` |
| `order.order_side` | `order.side` — events use `event.order_side` |
| `request_bars(bar_type)` one arg | Requires `start`: `request_bars(bar_type, start=datetime(...))` |
| `GreeksCalculator(cache, clock, logger)` | Only 2 args: `GreeksCalculator(cache, clock)` |
| `SyntheticInstrument(sym, prec, comps, formula)` | 6 required args — also needs `ts_event`, `ts_init` |
| `from nautilus_trader.core.nautilus_pyo3` wrong path | `from nautilus_trader.core.nautilus_pyo3 import black_scholes_greeks` |
| `BacktestEngine.add_venue(venue=BacktestVenueConfig(...))` | Takes positional args. `BacktestVenueConfig` is for `BacktestRunConfig` only |
| `DYDXDataClientConfig` (uppercase) | `DydxDataClientConfig` (mixed case) |
| `DydxOraclePrice` custom data type | Does not exist in v1.224.0 |
| `from nautilus_trader.common.clock import TestClock` | Use `from nautilus_trader.common.component import LiveClock` |
| `from nautilus_trader.common.config import CacheConfig` | `from nautilus_trader.config import CacheConfig` or `nautilus_trader.cache.config` |
| `Equity(..., max_price=, min_price=)` | Constructor rejects these kwargs — properties exist but return None |
| `FuturesContract(..., size_precision=, size_increment=)` | Hardcoded to 0/1 in Cython |
| `RSI` value in [0, 100] | Value in [0, 1] — divide by 100 if comparing to standard |
| Indicator warmup returns NaN | Returns partial values (silently wrong, not NaN) — guard with `indicators_initialized()` |
| `BookType.L3_MBO` for crypto | L3 not available on crypto exchanges — L2 at best. L3 is for traditional exchanges only |
| `subscribe_funding_rates()` everywhere | Method exists on Strategy but not all adapters support the feed |
| `subscribe_instrument_status()` on Binance | Binance does NOT implement this — not all adapters support it |
| `MarketStatusAction.RESUME` | Does not exist — use `TRADING` to detect resumption |
| `BinanceAccountType.USDT_FUTURE` (no S) | Must be `USDT_FUTURES` (with S) |
| `load_ids=frozenset({"BTCUSDT-PERP"})` bare symbol | Must be full InstrumentId: `frozenset({"BTCUSDT-PERP.BINANCE"})` — crashes at connect with `missing '.' separator` |
| `modify_order` auto-fallback | Adapter errors if venue doesn't support — no auto cancel+replace fallback |
| `InstrumentStatus` stops order flow | Does NOT automatically stop orders — strategy must react manually |
| Omitting `load_ids` from `InstrumentProviderConfig` | REQUIRED — without it, 0 instruments load, all subscriptions silently produce 0 data |
| `frozen_account=True` means checks active | INVERTED: `True` = checks DISABLED, `False` = checks ACTIVE |
| `testnet=True` for Deribit/dYdX | `is_testnet=True` |
| `AccountType.CASH` for perps backtest | Use `AccountType.MARGIN` — CASH + perps = 0 fills silently |
| `book.best_bid_price()` returns float | Returns `Price` object — cast with `float()` for arithmetic |
| **Rust-specific** | |
| `LiveNode::new(config)` or `LiveNodeConfig::builder()` | `LiveNode::builder(trader_id, Environment::Live)?.build()?` |
| `BinanceDataClientConfig::builder()` | Struct literal: `BinanceDataClientConfig { product_types: vec![...], ..Default::default() }` |
| `BinanceAccountType::UsdtFutures` (Rust) | `BinanceProductType::UsdM` from `nautilus_binance::common::enums` |
| `nautilus_core::identifiers::InstrumentId` | `nautilus_model::identifiers::InstrumentId` |
| `DataActor` in `nautilus_trading` | `DataActor` in `nautilus_common::actor` |
| `env_logger` alongside Nautilus | Crashes — Nautilus registers its own `log` backend. Use `log::info!()` directly |
| Nautilus crates from crates.io | Must use git source — `nautilus-persistence-macros` not on crates.io |
| `nautilus_trader_model` crate name | `nautilus_model` |
| `on_book_delta` (singular) | `on_book_deltas` (plural — batch) |
| Skip `on_stop` in DataActor | Warns "on_stop handler was called when not overridden" — always implement |
| `cancel_all_orders` in `on_stop` | Trading channel closed before `on_stop` — call from `on_trade` or other live callbacks |
| `node.stop()` exits cleanly | WebSocket lingers ~10s producing `channel closed` errors — add `std::process::exit(0)` after stop |
