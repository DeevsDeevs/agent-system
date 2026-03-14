# Pure Rust Trading with NautilusTrader

Writing strategies, actors, and custom data types entirely in Rust — no Python, no PyO3.

Topic-specific Rust API details (actors, backtesting, execution, exchange adapters, order book) live in the matching topic reference files under a `## Rust` section.

## When to Use Pure Rust vs Python

| Concern | Pure Rust | Python |
|---------|-----------|--------|
| Latency-critical strategies | Yes | No |
| Indicator math on hot paths | Yes | No |
| Custom data types with Arrow persistence | Yes | Either |
| Rapid prototyping | No | Yes |
| Exchange adapters (most) | Yes (native) | Yes (PyO3) |
| Live deployment | Yes (`LiveNode`) | Yes (`TradingNode`) |
| Backtesting | Yes (`BacktestEngine`) | Yes |

The kernel is identical in both modes — same event loop, same message bus, same clock. Rust gives you zero GIL overhead and direct control over allocations.

## Cargo Setup

`nautilus-persistence-macros` is not published to crates.io. All nautilus crates must come from git to avoid version mismatches. Use `default-features = false` on every crate — the default enables PyO3 bindings which require Python headers.

```toml
[workspace]
resolver = "2"
members = ["."]

[package]
name = "my-trading-system"
version = "0.1.0"
edition = "2021"

[dependencies]
nautilus-backtest          = { git = "https://github.com/nautechsystems/nautilus_trader.git", default-features = false, features = ["streaming", "high-precision"] }
nautilus-binance           = { git = "https://github.com/nautechsystems/nautilus_trader.git", package = "nautilus-binance",           default-features = false, features = ["high-precision"] }
nautilus-common            = { git = "https://github.com/nautechsystems/nautilus_trader.git", package = "nautilus-common",            default-features = false }
nautilus-core              = { git = "https://github.com/nautechsystems/nautilus_trader.git", package = "nautilus-core",              default-features = false }
nautilus-execution         = { git = "https://github.com/nautechsystems/nautilus_trader.git", package = "nautilus-execution",         default-features = false }
nautilus-indicators        = { git = "https://github.com/nautechsystems/nautilus_trader.git", package = "nautilus-indicators",        default-features = false }
nautilus-live              = { git = "https://github.com/nautechsystems/nautilus_trader.git", package = "nautilus-live",              default-features = false }
nautilus-model             = { git = "https://github.com/nautechsystems/nautilus_trader.git", package = "nautilus-model",             default-features = false, features = ["high-precision"] }
nautilus-persistence-macros= { git = "https://github.com/nautechsystems/nautilus_trader.git", package = "nautilus-persistence-macros" }
nautilus-portfolio         = { git = "https://github.com/nautechsystems/nautilus_trader.git", package = "nautilus-portfolio",         default-features = false }
nautilus-persistence       = { git = "https://github.com/nautechsystems/nautilus_trader.git", package = "nautilus-persistence",       default-features = false, features = ["high-precision"] }
nautilus-serialization     = { git = "https://github.com/nautechsystems/nautilus_trader.git", package = "nautilus-serialization",     default-features = false, features = ["arrow", "high-precision"] }
nautilus-trading           = { git = "https://github.com/nautechsystems/nautilus_trader.git", package = "nautilus-trading",           default-features = false, features = ["examples", "high-precision"] }

ahash      = "0.8"
anyhow     = "1"
arrow      = { version = "57", default-features = false, features = ["ipc", "json", "csv", "ffi"] }
arrow-row  = "57"
serde      = { version = "1", features = ["derive"] }
serde_json = "1"
tokio      = { version = "1", features = ["full"] }
```

`features = ["examples"]` on `nautilus-trading` enables `nautilus-indicators` as an optional dep — there is no `indicators` feature key.

`nautilus-backtest` requires `features = ["streaming"]` to expose `BacktestNode` — without it the type doesn't exist.

`nautilus-persistence` is needed for `ParquetDataCatalog`; add it explicitly.

Add `rust-toolchain.toml` to pin the Rust version (nautilus crates require 1.94+):

```toml
[toolchain]
channel = "1.94.0"
```

## Indicators

Indicators live in `nautilus-indicators`. Enable via `features = ["examples"]` on `nautilus-trading`. Import directly from `nautilus-indicators`:

```rust
use nautilus_indicators::{
    average::ema::ExponentialMovingAverage,
    indicator::{Indicator, MovingAverage},
};

let mut ema = ExponentialMovingAverage::new(10, Some(PriceType::Mid));

// In on_quote:
ema.handle_quote(quote);
if ema.initialized() {
    let value = ema.value();
}

// In on_trade:
ema.handle_trade(trade);
```

## Anti-Hallucination Notes

| Wrong | Right |
|-------|-------|
| `nautilus_trader_model` | `nautilus_model` — Rust crate name |
| `Strategy` in `nautilus_common` | `Strategy` in `nautilus_trading` |
| `DataActor` in `nautilus_trading` | `DataActor` in `nautilus_common` |
| `features = ["indicators"]` | `features = ["examples"]` on `nautilus-trading` |
| `DataType::new(name, None)` | `DataType::new(name, None, None)` — 3 args |
| `custom_data.inner().as_any()` | `custom_data.data.as_any()` — `.inner()` doesn't exist |
| `publish_signal` / `subscribe_signal` | Cython-only; Rust uses `CustomData` + `msgbus::publish_any` |
| `DataActorConfig::default()` without `new()` | `DataActorCore::new(DataActorConfig::default())` |
| `#[custom_data(pyo3)]` for pure Rust | `#[custom_data]` — no `pyo3` attribute needed |
| nautilus crates from crates.io | Use git source; `nautilus-persistence-macros` not on crates.io |
| `BacktestNode` doesn't exist | Real type in `nautilus_backtest::node`, behind `features = ["streaming"]` |
| `LiveNode` == Python's `TradingNode` | Different type; config via `LiveNodeBuilder`, not `TradingNodeConfig` |
| `NautilusDataType` in `nautilus_model::enums` | In `nautilus_backtest::config` |
| `cancel_all_orders` in `on_stop` | Trading channel closed before `on_stop` fires — call from `on_trade` or other live callbacks |
| `cancel_order(client_order_id, ...)` | `cancel_order` takes `OrderAny`, not `ClientOrderId` |
| `on_order_accepted(&mut self, event: &OrderAccepted) -> Result<()>` | Owned event, no Result, on `Strategy` trait not `DataActor` |
| `AccountType::Cash` for perps in backtest | Use `AccountType::Margin` — Cash panics on futures/perpetuals |
| `ParquetDataCatalog` from async context | Wrap in `tokio::task::spawn_blocking` — creates its own runtime internally |
| Instruments available only after `subscribe_instrument` | Binance loads all instruments at `connect()` — read from cache in `on_start` |
| `cancel_all_orders(id, side, order_type, client)` — 4 args | 3 args: `(instrument_id, order_side, client_id)` — no `order_type` |
| Binance Spot always works for live connections | Panics on high-supply tokens — fix: `features = ["high-precision"]` on `nautilus-binance` + `nautilus-model` |
| `modify_order(order_id, qty, price)` | Takes owned `OrderAny`, not `ClientOrderId`; retrieve via `cache.borrow().order(&id).cloned()` |
| `bracket()` returns `OrderList` | Returns `Vec<OrderAny>`; pass directly to `submit_order_list(orders, None, None)` |
| bracket works without extra config | Requires `support_contingent_orders = Some(true)` in `add_venue` for backtest |
| `submit_order_list` with bracket works in backtest | Two engine bugs prevent this — use manual bracket pattern (see execution.md) |
| `StopMarket` always works in L1 backtest | Hits `todo!("Exhausted simulated book volume")` — use `StopLimit` with trigger==limit price |
| `nautilus-binance` high-precision is off by default | It's the **default** feature; `default-features = false` disables it — re-add explicitly |
| `on_book_delta(&mut self, delta: &OrderBookDelta)` | `on_book_deltas(&mut self, deltas: &OrderBookDeltas)` — plural batch |
| `subscribe_book_deltas(..., Some(10), ...)` with `usize` | `depth` is `Option<NonZeroUsize>` — use `NonZeroUsize::new(10)` |
| Skip `on_stop` in `DataActor` | Warns "`on_stop handler was called when not overridden`" — always implement `on_stop` (even empty) |
| `node.stop()` cleanly exits | WebSocket stays alive ~10s after stop, producing `channel closed` ERRORs — add `std::process::exit(0)` after stop |

## Working Examples

Located in `examples/` (alongside Python counterparts):

| File | Demonstrates |
|------|--------------|
| `ema_crossover_backtest.rs` | `Strategy` trait, EMA crossover on quotes, `BacktestEngine` wiring |
| `signal_actor_backtest.rs` | `DataActor` publishes `#[custom_data]` signal, `Strategy` subscribes via `on_data` |
| `custom_data_backtest.rs` | VPIN accumulator, two actors, custom data round-trip |
| `market_maker_backtest.rs` | `modify_order` API — requotes bid/ask limits on every quote tick |
| `bracket_order_backtest.rs` | Manual bracket pattern (entry + SL + TP); `order_factory.bracket()` API documented |
| `catalog_backtest.rs` | `BacktestNode` reading from Parquet catalog, EMA crossover on live-collected data |
| `live_data_collector.rs` | `LiveNode` + Binance UsdM, quotes/trades/instruments + L2 book deltas into Parquet catalog |
| `live_order_test.rs` | Full order lifecycle: market buy → limit sell → cancel (from `on_trade`) → market sell → flat |
| `live_spot_test.rs` | Binance Spot + `high-precision` feature, SHIB/PEPE instrument loading |
| `live_modify_order_test.rs` | `modify_order` live, `on_order_updated`, `on_order_modify_rejected`, `on_order_rejected` callbacks |

Python counterparts (same directory):
- `ema_crossover_backtest.py` ↔ `ema_crossover_backtest.rs`
- `signal_pipeline_backtest.py` ↔ `signal_actor_backtest.rs`
- `market_maker_backtest.py` ↔ `market_maker_backtest.rs`
- `bracket_order_backtest.py` ↔ `bracket_order_backtest.rs`
