# Actors & Signals

## Actor vs Strategy

Strategy adds order management; Actor is for data processing, signal generation, and non-trading logic. Both share the same Cython base.

| Feature | Actor | Strategy |
|---------|-------|----------|
| Subscribe to market data | Yes | Yes |
| Publish signals | Yes | Yes |
| Submit orders | No | Yes |
| Position management | No | Yes |
| Order events | `on_order_filled`, `on_order_canceled` | Full suite |

## Imports

```python
from nautilus_trader.common.actor import Actor  # NOT trading.actor
from nautilus_trader.config import ActorConfig
```

**All Actor `on_` handlers** (same as Strategy minus order management):
`on_start`, `on_stop`, `on_resume`, `on_reset`, `on_save`, `on_load`,
`on_trade_tick`, `on_quote_tick`, `on_bar`, `on_order_book_deltas`, `on_order_book_depth`, `on_order_book`,
`on_mark_price`, `on_index_price`, `on_funding_rate`, `on_instrument`, `on_instrument_status`, `on_instrument_close`,
`on_signal`, `on_data`, `on_historical_data`, `on_event`,
`on_order_filled`, `on_order_canceled` (observe-only, via `subscribe_order_fills`/`subscribe_order_cancels`)

## Signal API *(Python/Cython only)*

> *Not available in pure Rust — see [## Rust](#rust).*

```python
# Publishing
self.publish_signal(
    name="momentum",     # str — becomes Signal{Name} (e.g. SignalMomentum)
    value=42.5,          # int, float, or str ONLY (dict/list cause KeyError)
    ts_event=tick.ts_event,  # int — nanosecond epoch (optional, default 0)
)

# Subscribing
self.subscribe_signal(name="momentum")  # specific signal
self.subscribe_signal()                  # ALL signals
```

Properties: `signal.value`, `signal.ts_event`, `signal.ts_init`. Distinguish types via `type(signal).__name__` (e.g. `"SignalMomentum"`).

### End-to-End Example

```python
from nautilus_trader.common.actor import Actor
from nautilus_trader.config import ActorConfig, StrategyConfig
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model.data import TradeTick
from nautilus_trader.trading.strategy import Strategy

class EmaActorConfig(ActorConfig, frozen=True):
    period: int = 20

class EmaActor(Actor):
    def __init__(self, config: EmaActorConfig) -> None:
        super().__init__(config)
        self.ema = ExponentialMovingAverage(config.period)
        self.count = 0

    def on_start(self) -> None:
        inst = self.cache.instruments()[0]
        self.subscribe_trade_ticks(inst.id)

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.count += 1
        self.ema.handle_trade_tick(tick)
        if self.ema.initialized and self.count % 50 == 0:
            self.publish_signal(name="ema", value=self.ema.value, ts_event=tick.ts_event)

class SignalStrategy(Strategy):
    def __init__(self, config: StrategyConfig) -> None:
        super().__init__(config)
        self.last_ema = None

    def on_start(self) -> None:
        self.subscribe_signal(name="ema")

    def on_signal(self, signal) -> None:
        self.last_ema = signal.value
```

## Custom Data API

```python
from nautilus_trader.core.data import Data
from nautilus_trader.model.data import DataType

class ImbalanceData(Data):
    def __init__(self, imbalance: float, volume: float, ts_event: int, ts_init: int) -> None:
        self.imbalance = imbalance
        self.volume = volume
        self._ts_event = ts_event
        self._ts_init = ts_init

    @property
    def ts_event(self) -> int:
        return self._ts_event

    @property
    def ts_init(self) -> int:
        return self._ts_init
```

Publishing and subscribing:
```python
data_type = DataType(ImbalanceData, metadata={"name": "imbalance"})
self.publish_data(data_type=data_type, data=imbalance_instance)

self.subscribe_data(data_type=DataType(ImbalanceData, metadata={"name": "imbalance"}))

def on_data(self, data) -> None:
    if isinstance(data, ImbalanceData):
        self.current_imbalance = data.imbalance
```

Requirements: `ts_event`/`ts_init` properties returning `int` (nanosecond epoch). Metadata dict must match exactly between publisher and subscriber. `on_data` receives ALL custom data — use `isinstance()` to filter.

## Signal vs Custom Data

| Aspect | `publish_signal` | `publish_data` |
|--------|-----------------|----------------|
| Value type | int, float, or str only | Custom Data subclass |
| Setup | No class needed | Define class + DataType |
| Handler | `on_signal(signal)` | `on_data(data)` |
| Multi-field | Single scalar only | Named fields |

## Registration

```python
engine.add_actor(MyActor(MyActorConfig()))    # Backtest
engine.add_strategy(MyStrategy(config))
node.trader.add_actor(actor)                  # Live
node.trader.add_strategy(strategy)
```

Actors start before strategies. Within each group, order follows registration order.

## Actor for External Data (Live) *(Python only)*

> `HttpClient` and `queue_for_executor` are PyO3 bindings — not in pure-Rust mode.

```python
from nautilus_trader.core.nautilus_pyo3 import HttpClient

class RestPollerActor(Actor):
    def __init__(self, config=None):
        super().__init__(config)

    def on_start(self):
        self._http = HttpClient()
        self.clock.set_timer("poll", interval=timedelta(seconds=5), callback=self._on_timer)

    def _on_timer(self, event):
        self.queue_for_executor(self._fetch)  # schedules async coro from sync context

    async def _fetch(self):
        resp = await self._http.get("https://api.example.com/data", params={"key": "val"})
        # parse resp.body, create custom Data, publish_data(...)
```

> See SKILL.md for common hallucination guards.

## Rust

| Concern | Python | Rust |
|---|---|---|
| Strategy base | `class MyStrategy(Strategy)` | Struct with `Deref/DerefMut` to `DataActorCore` |
| Actor base | `class MyActor(Actor)` | Struct with `DataActor` trait + `DataActorCore` |
| Signals | `publish_signal(name, value)` | Cython-only; use `#[custom_data]` + `msgbus::publish_any` |
| Callback return | `None` | `Result<()>` for DataActor; `()` for Strategy |
| Config | `StrategyConfig(strategy_id=...)` | `StrategyConfig { strategy_id: Some(...), ..Default::default() }` |
| Cache access | `self.cache.positions_open(...)` | `self.cache_rc().borrow()` — RefCell, must scope borrows |

### Strategy Trait

Struct with `StrategyCore`, impl `Deref<Target=DataActorCore>` + `DerefMut` + `Debug`, impl `DataActor` (handlers return `Result<()>`), impl `Strategy` (`core()`/`core_mut()`). See [ema_crossover_backtest.rs](../examples/ema_crossover_backtest.rs) for a complete minimal example.

```rust
use nautilus_trading::strategy::{Strategy, StrategyConfig, StrategyCore};
use nautilus_common::actor::{DataActor, DataActorCore};

// Order submission
let order = self.core.order_factory().market(
    self.instrument_id, OrderSide::Buy, self.trade_size,
    None, None, None, None, None, None, None,
);
self.submit_order(order, None, None)?;

// Cache — borrow must be dropped before any &mut self call
let cache = self.cache_rc();
let open = cache.borrow().positions_open(None, Some(&self.instrument_id), None, None, None);
drop(cache);
```

### DataActor Trait

Same pattern as Strategy but with `DataActorCore` + `DataActorConfig::default()` instead of `StrategyCore`. Deref/DerefMut/Debug impls identical. Clone `instrument_ids` before iterating to avoid borrow conflict with `self.subscribe_trades()`. See [signal_actor_backtest.rs](../examples/signal_actor_backtest.rs) for a complete Actor example.

### Custom Data Types

```rust
use nautilus_core::UnixNanos;
use nautilus_persistence_macros::custom_data;

#[custom_data]
pub struct TradeImbalance {
    pub instrument_id: InstrumentId,
    pub buy_volume: f64,
    pub sell_volume: f64,
    pub imbalance: f64,
    pub ts_event: UnixNanos,  // REQUIRED
    pub ts_init: UnixNanos,   // REQUIRED
}
```

Supported field types: `f64`, `f32`, `i64`, `i32`, `u64`, `u32`, `u16`, `u8`, `bool`, `String`, `InstrumentId`, `Vec<f64>`, `Vec<u8>`.

```rust
// Register once at startup
nautilus_serialization::ensure_custom_data_registered::<TradeImbalance>();

// Publish
use std::sync::Arc;
use nautilus_common::{msgbus, msgbus::switchboard::get_custom_topic};
use nautilus_model::data::{CustomData, DataType};

let custom = CustomData::from_arc(Arc::new(snapshot));
let topic = get_custom_topic(&custom.data_type);
msgbus::publish_any(topic, &custom);

// Subscribe (in on_start)
let data_type = DataType::new(stringify!(TradeImbalance), None, None);
self.subscribe_data(data_type, None, None);

// Receive (in on_data)
fn on_data(&mut self, data: &CustomData) -> Result<()> {
    let Some(snap) = data.data.as_any().downcast_ref::<TradeImbalance>() else {
        return Ok(());
    };
    println!("imbalance={:.4}", snap.imbalance);
    Ok(())
}
```

`CustomData` has `.data: Arc<dyn CustomDataTrait>` — no `.inner()` method exists.

### Signal Pattern (Actor -> Strategy)

Rust equivalent of Python's `publish_signal`/`subscribe_signal` — define a `#[custom_data]` struct, publish via `msgbus::publish_any`, subscribe via `subscribe_data(DataType::new("SignalName", None, None), None, None)`, receive in `on_data`. See Custom Data Types section above for the full pattern.

## Related Examples

- [signal_pipeline_backtest.py](../examples/signal_pipeline_backtest.py) — Actor signal pipeline
- [signal_actor_backtest.rs](../examples/signal_actor_backtest.rs) — Rust DataActor signal pub/sub
- [binance_enrichment_actor.py](../examples/binance_enrichment_actor.py) — Actor polling REST for OI + funding
