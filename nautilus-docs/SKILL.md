---
name: nautilus-docs
description: >
  NautilusTrader trading platform — strategies, backtesting, live deployment, order management,
  market data, Rust native binaries. Use when writing, reviewing, or debugging NautilusTrader
  code (Python or Rust), configuring venue adapters, or answering questions about the platform.
---

# NautilusTrader v1.224.0

**MANDATORY**: Before writing or debugging NautilusTrader code, READ the matching doc from the navigator below. If no entry matches, **grep** `${CLAUDE_SKILL_DIR}/references/docs/` for the class/method/config name. Never guess signatures or constructors.

**MUST READ** before any NautilusTrader work: [architecture.md](references/docs/concepts/architecture.md) (system diagram, data/execution flow, threading model, component FSM) and [actors.md](references/docs/concepts/actors.md) (lifecycle, callbacks, data handler mapping).

## Doc Navigator

### Concepts

| Topic | Doc |
|-------|-----|
| Architecture / overview | [architecture.md](references/docs/concepts/architecture.md), [overview.md](references/docs/concepts/overview.md) |
| Actor development | [actors.md](references/docs/concepts/actors.md) |
| Strategy development | [strategies.md](references/docs/concepts/strategies.md) |
| Backtesting | [backtesting.md](references/docs/concepts/backtesting.md) |
| Live trading | [live.md](references/docs/concepts/live.md) |
| Order types & execution | [orders.md](references/docs/concepts/orders.md), [execution.md](references/docs/concepts/execution.md) |
| Order book | [order_book.md](references/docs/concepts/order_book.md) |
| Data types & custom data | [data.md](references/docs/concepts/data.md), [custom_data.md](references/docs/concepts/custom_data.md) |
| Instruments | [instruments.md](references/docs/concepts/instruments.md) |
| Value types (Price, Quantity, Money) | [value_types.md](references/docs/concepts/value_types.md) |
| Positions & PnL | [positions.md](references/docs/concepts/positions.md) |
| Cache | [cache.md](references/docs/concepts/cache.md) |
| MessageBus | [message_bus.md](references/docs/concepts/message_bus.md) |
| Portfolio | [portfolio.md](references/docs/concepts/portfolio.md) |
| Options & Greeks | [options.md](references/docs/concepts/options.md), [greeks.md](references/docs/concepts/greeks.md) |
| Logging | [logging.md](references/docs/concepts/logging.md) |
| Reports & analysis | [reports.md](references/docs/concepts/reports.md) |
| Visualization | [visualization.md](references/docs/concepts/visualization.md) |
| Adapter development | [concepts/adapters.md](references/docs/concepts/adapters.md), [developer_guide/adapters.md](references/docs/developer_guide/adapters.md) |

### Venue Integrations

| Venue | Doc |
|-------|-----|
| Binance | [binance.md](references/docs/integrations/binance.md) |
| Bybit | [bybit.md](references/docs/integrations/bybit.md) |
| OKX | [okx.md](references/docs/integrations/okx.md) |
| dYdX | [dydx.md](references/docs/integrations/dydx.md) |
| Deribit | [deribit.md](references/docs/integrations/deribit.md) |
| Hyperliquid | [hyperliquid.md](references/docs/integrations/hyperliquid.md) |
| Kraken | [kraken.md](references/docs/integrations/kraken.md) |
| Interactive Brokers | [ib.md](references/docs/integrations/ib.md) |
| Betfair | [betfair.md](references/docs/integrations/betfair.md) |
| Polymarket | [polymarket.md](references/docs/integrations/polymarket.md) |
| Databento | [databento.md](references/docs/integrations/databento.md) |
| Tardis | [tardis.md](references/docs/integrations/tardis.md) |
| BitMEX | [bitmex.md](references/docs/integrations/bitmex.md) |
| AX Exchange | [architect_ax.md](references/docs/integrations/architect_ax.md) |
| Blockchain / DeFi | [blockchain.md](references/docs/integrations/blockchain.md) |

### Dev / Setup

| Topic | Doc |
|-------|-----|
| Installation | [installation.md](references/docs/getting_started/installation.md) |
| Quickstart | [quickstart.py](references/docs/getting_started/quickstart.py) |
| Backtest examples | [backtest_high_level.py](references/docs/getting_started/backtest_high_level.py), [backtest_low_level.py](references/docs/getting_started/backtest_low_level.py) |
| Environment setup | [environment_setup.md](references/docs/developer_guide/environment_setup.md) |
| Rust development | [rust.md](references/docs/developer_guide/rust.md) |
| Python development | [python.md](references/docs/developer_guide/python.md) |
| Testing | [testing.md](references/docs/developer_guide/testing.md) |
| Data testing spec | [spec_data_testing.md](references/docs/developer_guide/spec_data_testing.md) |
| Execution testing spec | [spec_exec_testing.md](references/docs/developer_guide/spec_exec_testing.md) |
| Test datasets | [test_datasets.md](references/docs/developer_guide/test_datasets.md) |
| Coding standards | [coding_standards.md](references/docs/developer_guide/coding_standards.md) |
| Benchmarking | [benchmarking.md](references/docs/developer_guide/benchmarking.md), [criterion_template.rs](references/docs/dev_templates/criterion_template.rs), [iai_template.rs](references/docs/dev_templates/iai_template.rs) |
| FFI | [ffi.md](references/docs/developer_guide/ffi.md) |

### Tutorials

| Tutorial | Doc |
|----------|-----|
| FX mean reversion (AX) | [fx_mean_reversion_ax.md](references/docs/tutorials/fx_mean_reversion_ax.md) |
| Gold book imbalance (AX) | [gold_book_imbalance_ax.md](references/docs/tutorials/gold_book_imbalance_ax.md) |
| dYdX grid market maker | [grid_market_maker_dydx.md](references/docs/tutorials/grid_market_maker_dydx.md) |
| BitMEX grid market maker | [grid_market_maker_bitmex.md](references/docs/tutorials/grid_market_maker_bitmex.md) |
| Backtest Binance orderbook | [backtest_orderbook_binance.py](references/docs/tutorials/backtest_orderbook_binance.py) |
| Backtest Bybit orderbook | [backtest_orderbook_bybit.py](references/docs/tutorials/backtest_orderbook_bybit.py) |
| Backtest FX bars | [backtest_fx_bars.py](references/docs/tutorials/backtest_fx_bars.py) |
| Databento data catalog | [data_catalog_databento.py](references/docs/tutorials/data_catalog_databento.py) |
| Loading external data | [loading_external_data.py](references/docs/tutorials/loading_external_data.py) |

### Search Strategy

When the navigator doesn't cover your need, grep `${CLAUDE_SKILL_DIR}/references/docs/` for the class, method, or config name. **Concepts docs** have working code examples with correct signatures. **Integration docs** have venue-specific configs, supported features, and gotchas. Read BEFORE writing code — never invent an API call.

## Supporting Files

- **[battle_tested.md](references/battle_tested.md)** — Load when: Rust Strategy pattern, credentials, patching deps, on_start() ordering, market making, backtest config, venue gotchas, backtest→live migration, hot path performance, state persistence, fill/latency metrics, log rotation, custom indicators, data pipeline validation.
- **[REBUILD.md](references/REBUILD.md)** — Meta-prompt for regenerating this skill when NautilusTrader API changes.

## Rust Standalone Binary

Git dependencies, no workspace clone needed. All crates: `{ git = "https://github.com/nautechsystems/nautilus_trader.git" }`. Naming: `nautilus-{name}` (Cargo) → `nautilus_{name}` (Rust).

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

All `nautilus-{venue}`: binance, bybit, okx, kraken, bitmex, deribit, dydx, hyperliquid, databento, tardis, betfair, polymarket, architect-ax, sandbox. See Venue Integrations docs for config details.

### Which crates for your task

| Use case | Crates |
|----------|--------|
| Data-only live actor | `nautilus-common`, `nautilus-model`, `nautilus-live`, `nautilus-{venue}` |
| Live strategy (orders) | above + `nautilus-trading` |
| Backtest | `nautilus-common`, `nautilus-model`, `nautilus-backtest` (+ `streaming`), `nautilus-trading` |
| With indicators | add `nautilus-trading` with `features = ["examples"]` |
| With Parquet catalog | add `nautilus-persistence` |
| `high-precision` (128-bit) | Default on most crates — `default-features = false` disables it, re-add explicitly |

### Rust vs Python

- **No `load_ids` / `InstrumentProviderConfig` in Rust** — adapters auto-discover all instruments at connect
- **Logging**: Nautilus owns the `log` backend. Use `log::info!()`. Output goes to stdout. No `RUST_LOG` env var, no `env_logger`
- **First build**: minutes (430+ crates). Incremental: ~2s. Use `cargo build` not `--release` for iteration
- **`#[derive(Debug)]` on all actor structs** — Nautilus requires `Debug` trait; missing it = compile error (zero-cost, fine for prod)
- **Callback naming**: Rust drops `_tick` suffix — `on_trade` not `on_trade_tick`, `on_quote` not `on_quote_tick`, `subscribe_trades` not `subscribe_trade_ticks`
- **Trade fields**: `trade.price.as_f64()`, `trade.size.as_f64()`, `trade.aggressor_side` (`AggressorSide::Buyer`/`Seller`)
- **`node.run().await`** blocks the event loop. Callbacks fire during run. `on_stop` fires on shutdown signal
- **Adapter configs** are struct literals with `..Default::default()`. Full names: `{Venue}DataClientConfig`, `{Venue}ExecutionClientConfig`. Factory: `{Venue}DataClientFactory`, `{Venue}ExecutionClientFactory`
- **Ed25519 keys (v0.55.0)**: HTTP signature URL-encoding bug — HMAC keys may also be auto-detected as Ed25519 if valid base64. See battle_tested.md

### DataActor pattern (Nautilus-specific — don't generalize Deref/DerefMut elsewhere)

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
        log::info!("px={} qty={}", trade.price.as_f64(), trade.size.as_f64());
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

## Common Hallucinations

### Python

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

### Rust

| Hallucination | Reality |
|--------------|---------|
| `LiveNode::new(config)` or `LiveNodeConfig::builder()` | `LiveNode::builder(trader_id, Environment::Live)?.build()?` |
| `BinanceDataClientConfig::builder()` | Struct literal: `BinanceDataClientConfig { product_types: vec![...], ..Default::default() }` |
| `BinanceAccountType::UsdtFutures` (Rust) | `BinanceProductType::UsdM` from `nautilus_binance::common::enums` |
| `nautilus_core::identifiers::InstrumentId` | `nautilus_model::identifiers::InstrumentId` |
| `DataActor` in `nautilus_trading` | `DataActor` in `nautilus_common::actor` |
| `env_logger` alongside Nautilus | Crashes — Nautilus owns `log` backend. Use `log::info!()` |
| Nautilus crates from crates.io | Git source only |
| `nautilus_trader_model` | `nautilus_model` |
| `on_book_delta` (singular) | `on_book_deltas` (plural — batch) |
| Skip `on_stop` in DataActor | Warns "on_stop handler was called when not overridden" — always implement |
| `cancel_all_orders` in `on_stop` | Trading channel closed before `on_stop` — use earlier callbacks |
| `node.stop()` exits cleanly | WebSocket lingers ~10s. Use `tokio::time::timeout` on shutdown |
| `event.duration_ns` on PositionClosed | `event.duration` — no `_ns` suffix |
| `event.realized_pnl` is `Money` | `Option<Money>` — use `{:?}` format, not `{}` |
| `node.add_actor(strategy)` for Strategy | `node.add_strategy(strategy)?;` — Strategy ≠ DataActor |
| `Deref<Target = StrategyCore>` for Strategy | `Deref<Target = DataActorCore>` — StrategyCore auto-derefs through |
| `BinanceExecClientFactory` | `BinanceExecutionClientFactory` — full name, same for config |
| Patching a nautilus crate | Fork on GitHub + `[patch]` in Cargo.toml. See battle_tested.md |
| Ed25519 keys in Rust HTTP adapters (v0.55.0) | URL-encoding bug — base64 `+/=` not encoded. Needs fork |
