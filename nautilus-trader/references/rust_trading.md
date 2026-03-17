# Pure Rust Trading

Topic-specific Rust API details live in matching topic reference files under `## Rust` sections.

## Rust vs Python

| Concern | Pure Rust | Python |
|---------|-----------|--------|
| Latency-critical strategies | Yes | No |
| Indicator math on hot paths | Yes | No |
| Custom data types with Arrow persistence | Yes | Either |
| Rapid prototyping | No | Yes |
| Exchange adapters (most) | Yes (native) | Yes (PyO3) |
| Live deployment | Yes (`LiveNode`) | Yes (`TradingNode`) |
| Backtesting | Yes (`BacktestEngine`) | Yes |

## Cargo Setup

All nautilus crates must come from git (`nautilus-persistence-macros` not on crates.io). Use `default-features = false` on every crate — the default enables PyO3 bindings which require Python headers.

```toml
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

- `features = ["examples"]` on `nautilus-trading` enables `nautilus-indicators` — no `indicators` feature key.
- `nautilus-backtest` requires `features = ["streaming"]` to expose `BacktestNode`.
- `nautilus-persistence` needed for `ParquetDataCatalog`; add explicitly.
- Requires Rust 1.94+. Pin via `rust-toolchain.toml`: `channel = "1.94.0"`

## Indicators

```rust
use nautilus_indicators::{
    average::ema::ExponentialMovingAverage,
    indicator::{Indicator, MovingAverage},
};

let mut ema = ExponentialMovingAverage::new(10, Some(PriceType::Mid));
ema.handle_quote(quote);
if ema.initialized() {
    let value = ema.value();
}
ema.handle_trade(trade);
```

## Anti-Hallucination Notes

> See SKILL.md for common hallucination guards.

## Required Boilerplate

Every Rust actor/strategy needs `Deref<Target=DataActorCore>` + `DerefMut` + `Debug`. Canonical impl in `ema_crossover_backtest.rs`:

```rust
impl Deref for MyActor {
    type Target = DataActorCore;
    fn deref(&self) -> &Self::Target { &self.core }
}
impl DerefMut for MyActor {
    fn deref_mut(&mut self) -> &mut Self::Target { &mut self.core }
}
impl Debug for MyActor {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("MyActor").finish()
    }
}
```

Strategies also need `impl Strategy` with `core()`/`core_mut()` returning `&StrategyCore`.

## Working Examples

| File | Demonstrates |
|------|--------------|
| `ema_crossover_backtest.rs` | `Strategy` trait, EMA crossover, `BacktestEngine` wiring |
| `signal_actor_backtest.rs` | `DataActor` publishes `#[custom_data]` signal, `Strategy` subscribes via `on_data` |
| `custom_data_backtest.rs` | Imbalance accumulator, two actors, custom data round-trip |
| `market_maker_backtest.rs` | `modify_order` — requotes bid/ask limits on every quote tick |
| `bracket_order_backtest.rs` | Manual bracket pattern (entry + SL + TP); `order_factory.bracket()` API |
| `catalog_backtest.rs` | `BacktestNode` from Parquet catalog |
| `live_data_collector.rs` | `LiveNode` + Binance UsdM, quotes/trades/instruments + L2 book deltas into Parquet |
| `live_order_test.rs` | Full order lifecycle: market buy -> limit sell -> cancel -> market sell -> flat |
| `live_spot_test.rs` | Binance Spot + `high-precision`, SHIB/PEPE instrument loading |
| `live_modify_order_test.rs` | `modify_order` live, order update/reject callbacks |
