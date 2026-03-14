# Actors & Signals

## Actor vs Strategy

Both inherit from the same Cython base. Strategy adds order management; Actor is for data processing, signal generation, and non-trading logic.

| Feature | Actor | Strategy |
|---------|-------|----------|
| Subscribe to market data | Yes | Yes |
| Publish signals | Yes | Yes |
| Subscribe to signals | Yes | Yes |
| Clock/timers | Yes | Yes |
| Cache access | Yes | Yes |
| Submit orders | No | Yes |
| Position management | No | Yes |
| Order events | `on_order_filled`, `on_order_canceled` | Full suite |

## Imports

```python
from nautilus_trader.common.actor import Actor  # NOT trading.actor
from nautilus_trader.config import ActorConfig
```

## Actor Lifecycle

```python
class MyActorConfig(ActorConfig, frozen=True):
    ema_period: int = 10

class MyActor(Actor):
    def __init__(self, config: MyActorConfig) -> None:
        super().__init__(config)
        self.ema = ExponentialMovingAverage(config.ema_period)

    def on_start(self) -> None:
        # Subscribe to data, set timers
        inst = self.cache.instruments()[0]
        self.subscribe_trade_ticks(inst.id)

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.ema.handle_trade_tick(tick)
        if self.ema.initialized:
            self.publish_signal(name="ema", value=self.ema.value, ts_event=tick.ts_event)

    def on_stop(self) -> None:
        pass  # cleanup

    def on_save(self) -> dict[str, bytes]:
        return {}  # persist custom state

    def on_load(self, state: dict[str, bytes]) -> None:
        pass  # restore custom state
```

**All Actor `on_` handlers** (same as Strategy minus order management):
`on_start`, `on_stop`, `on_resume`, `on_reset`, `on_save`, `on_load`,
`on_trade_tick`, `on_quote_tick`, `on_bar`, `on_order_book_deltas`, `on_order_book_depth`, `on_order_book`,
`on_mark_price`, `on_index_price`, `on_funding_rate`, `on_instrument`, `on_instrument_status`, `on_instrument_close`,
`on_signal`, `on_data`, `on_historical_data`, `on_event`,
`on_order_filled`, `on_order_canceled` (observe-only, via `subscribe_order_fills`/`subscribe_order_cancels`)

## Signal API (Native — Preferred) *(Python/Cython only)*

> *Not available in pure Rust. Use `#[custom_data]` struct + `msgbus::publish_any` + `subscribe_data` — see [## Rust](#rust).*

The simplest way to pass data between components. No custom class needed.

### Publishing

```python
# In Actor or Strategy
self.publish_signal(
    name="momentum",     # str — becomes class name Signal{Name} (e.g. SignalMomentum)
    value=42.5,          # int, float, or str ONLY (dict/list cause KeyError)
    ts_event=tick.ts_event,  # int — nanosecond epoch (optional, default 0)
)
```

Framework auto-generates a `Signal{Name}` class. Name is capitalized: `"momentum"` → `SignalMomentum`, `"ema"` → `SignalEma`.

### Subscribing

```python
# In Strategy or Actor on_start()
self.subscribe_signal(name="momentum")  # specific signal
self.subscribe_signal()                  # ALL signals (empty name)
```

### Receiving

```python
def on_signal(self, signal) -> None:
    # signal.value     — the value you published
    # signal.ts_event  — int, nanosecond epoch
    # signal.ts_init   — int, nanosecond epoch
    # type(signal).__name__  — "SignalMomentum", "SignalEma", etc.

    # Distinguish signal types by class name
    sig_type = type(signal).__name__
    if sig_type == "SignalMomentum":
        self._handle_momentum(signal.value)
    elif sig_type == "SignalEma":
        self._handle_ema(signal.value)
```

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
        # Use signal value for trading decisions
```

## Custom Data API (Advanced)

For structured data with multiple fields, use custom `Data` subclass + `publish_data`/`subscribe_data`.

```python
from nautilus_trader.core.data import Data
from nautilus_trader.model.data import DataType
from nautilus_trader.model.identifiers import ClientId

class VPINData(Data):
    def __init__(self, vpin: float, volume: float, ts_event: int, ts_init: int) -> None:
        self.vpin = vpin
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

### Publishing Custom Data

```python
# In Actor
data_type = DataType(VPINData, metadata={"name": "vpin"})
self.publish_data(data_type=data_type, data=vpin_instance)
```

### Subscribing to Custom Data

```python
# In Strategy on_start()
self.subscribe_data(
    data_type=DataType(VPINData, metadata={"name": "vpin"}),
)

def on_data(self, data) -> None:
    if isinstance(data, VPINData):
        self.current_vpin = data.vpin
```

**Custom Data requirements**:
- Must implement `ts_event` and `ts_init` as properties returning `int` (nanosecond epoch)
- Metadata dict must match exactly between publisher and subscriber
- `on_data` receives ALL custom data — use `isinstance()` to filter

## Signal vs Custom Data

| Aspect | `publish_signal` | `publish_data` |
|--------|-----------------|----------------|
| Value type | int, float, or str only | Custom Data subclass |
| Setup | Zero — no class needed | Define class + DataType |
| Handler | `on_signal(signal)` | `on_data(data)` |
| Filtering | `subscribe_signal(name=...)` | `isinstance()` in handler |
| Multi-field | Not supported (single scalar) | Native named fields |
| Use when | Simple numeric signals | Structured multi-field data |

**Recommendation**: Start with `publish_signal` for simple signals. Only use custom Data when you need multiple typed fields.

## Registration

### Backtest
```python
actor = MyActor(MyActorConfig())
engine.add_actor(actor)
strategy = MyStrategy(config)
engine.add_strategy(strategy)
```

### Live
```python
node.trader.add_actor(actor)
node.trader.add_strategy(strategy)
```

**Order matters**: Actors are started before strategies. Within each group, order follows registration order.

## Multi-Actor Coordination

Multiple actors can publish different signals that one strategy consumes:

```python
class VolumeActor(Actor):
    def on_trade_tick(self, tick):
        self.volume_sum += float(tick.size)
        if self.count % 100 == 0:
            self.publish_signal(name="volume", value=self.volume_sum)

class SpreadActor(Actor):
    def on_quote_tick(self, tick):
        spread = float(tick.ask_price) - float(tick.bid_price)
        self.publish_signal(name="spread", value=spread, ts_event=tick.ts_event)

class ComboStrategy(Strategy):
    def on_start(self):
        self.subscribe_signal()  # subscribe to ALL signals
        self.volume = 0.0
        self.spread = 0.0

    def on_signal(self, signal):
        sig_type = type(signal).__name__
        if sig_type == "SignalVolume":
            self.volume = signal.value
        elif sig_type == "SignalSpread":
            self.spread = signal.value
```

## Actor for External Data (Live) *(Python only)*

> *`HttpClient` and `queue_for_executor` are PyO3 bindings — not available in pure-Rust mode.*

Poll REST APIs on a timer and publish results as custom data:

```python
from nautilus_trader.core.nautilus_pyo3 import HttpClient

class RestPollerActor(Actor):
    def on_start(self):
        self._http = HttpClient()
        self.clock.set_timer("poll", interval=timedelta(seconds=5), callback=self._on_timer)

    def _on_timer(self, event):
        self.queue_for_executor(self._fetch)  # schedule async from sync callback

    async def _fetch(self):
        resp = await self._http.get("https://api.example.com/data", params={"key": "val"})
        # parse resp.body, create custom Data, publish_data(...)
```

> For a full working example with `OpenInterestData` and `FundingRateUpdate`,
> see `examples/binance_enrichment_actor.py`.

## Anti-Hallucination Notes

| Hallucination | Reality |
|--------------|---------|
| `from nautilus_trader.trading.actor import Actor` | `from nautilus_trader.common.actor import Actor` |
| `publish_signal(value=dict(...))` | Values must be int, float, or str — dict causes KeyError |
| `on_signal` receives typed fields | Single scalar value only — use custom Data for multi-field |
| `Actor.subscribe_trade_ticks()` in `__init__` | Must subscribe in `on_start()` — cache not available in `__init__` |
| Custom `Data` without `ts_event`/`ts_init` | Both required as properties — use `_ts_event`/`_ts_init` backing fields |

## Rust

| Concern | Python | Rust |
|---|---|---|
| Strategy base | `class MyStrategy(Strategy): super().__init__(config)` | Struct with `Deref/DerefMut` to `DataActorCore`; no class inheritance |
| Actor base | `class MyActor(Actor)` | Struct with `DataActor` trait + `DataActorCore` |
| Signals | `publish_signal(name, value)` / `subscribe_signal(name, callback)` | Cython-only; use `#[custom_data]` struct + `msgbus::publish_any` + `subscribe_data` |
| Callback return | `None` | `Result<()>` for DataActor; `()` (no Result) for Strategy event callbacks |
| Config | `StrategyConfig(strategy_id=..., order_id_tag=...)` Pydantic kwargs | `StrategyConfig { strategy_id: Some(...), ..Default::default() }` |
| Cache access | `self.cache.positions_open(...)` | `self.cache_rc().borrow().positions_open(...)` — RefCell, must scope borrows |

### Strategy Trait

```rust
use std::{fmt::Debug, ops::{Deref, DerefMut}};
use anyhow::Result;
use nautilus_common::actor::{DataActor, DataActorCore};
use nautilus_model::{
    data::QuoteTick,
    enums::OrderSide,
    identifiers::{InstrumentId, StrategyId},
    types::Quantity,
};
use nautilus_trading::strategy::{Strategy, StrategyConfig, StrategyCore};

struct MyStrategy {
    core: StrategyCore,
    instrument_id: InstrumentId,
    trade_size: Quantity,
}

impl MyStrategy {
    fn new(instrument_id: InstrumentId, trade_size: Quantity) -> Self {
        let config = StrategyConfig {
            strategy_id: Some(StrategyId::from("MY_STRATEGY-001")),
            order_id_tag: Some("001".to_string()),
            ..Default::default()
        };
        Self { core: StrategyCore::new(config), instrument_id, trade_size }
    }
}

impl Deref for MyStrategy {
    type Target = DataActorCore;
    fn deref(&self) -> &Self::Target { &self.core }
}
impl DerefMut for MyStrategy {
    fn deref_mut(&mut self) -> &mut Self::Target { &mut self.core }
}
impl Debug for MyStrategy {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("MyStrategy").finish()
    }
}

impl DataActor for MyStrategy {
    fn on_start(&mut self) -> Result<()> {
        self.subscribe_quotes(self.instrument_id, None, None);
        Ok(())
    }
    fn on_stop(&mut self) -> Result<()> {
        self.unsubscribe_quotes(self.instrument_id, None, None);
        Ok(())
    }
    fn on_quote(&mut self, quote: &QuoteTick) -> Result<()> {
        Ok(())
    }
}

impl Strategy for MyStrategy {
    fn core(&self) -> &StrategyCore { &self.core }
    fn core_mut(&mut self) -> &mut StrategyCore { &mut self.core }
}
```

Order submission and cache access:

```rust
// Market order — 7 trailing None args
let order = self.core.order_factory().market(
    self.instrument_id, OrderSide::Buy, self.trade_size,
    None, None, None, None, None, None, None,
);
self.submit_order(order, None, None)?;

// Close all positions on one instrument
self.close_all_positions(self.instrument_id, None, None, None, None, None, None)?;

// Cache — borrow must be dropped before any &mut self call
let cache = self.cache_rc();
let open = cache.borrow().positions_open(None, Some(&self.instrument_id), None, None, None);
drop(cache);
```

### DataActor Trait

Actor without order management — signal computation, data enrichment, VPIN, etc.

```rust
use nautilus_common::actor::{DataActor, DataActorCore, DataActorConfig};
use nautilus_model::data::TradeTick;

struct SignalActor {
    core: DataActorCore,
    instrument_ids: Vec<InstrumentId>,
}

impl SignalActor {
    fn new(instrument_ids: Vec<InstrumentId>) -> Self {
        Self { core: DataActorCore::new(DataActorConfig::default()), instrument_ids }
    }
}

// Deref/DerefMut/Debug impls identical to Strategy pattern above

impl DataActor for SignalActor {
    fn on_start(&mut self) -> Result<()> {
        // Clone IDs before iterating to avoid borrow conflict with &mut self
        let ids: Vec<InstrumentId> = self.instrument_ids.clone();
        for id in ids {
            self.subscribe_trades(id, None, None);
        }
        Ok(())
    }
    fn on_trade(&mut self, trade: &TradeTick) -> Result<()> {
        Ok(())
    }
}
```

Available subscription methods (on `DataActorCore` via `Deref`):
- `subscribe_quotes(instrument_id, client_id, params)`
- `subscribe_trades(instrument_id, client_id, params)`
- `subscribe_bars(bar_type, await_partial, client_id, params)`
- `subscribe_book_deltas(instrument_id, book_type, depth, client_id, managed, params)`
- `subscribe_data(data_type, client_id, params)` — custom data types
- Matching `unsubscribe_*` for each

Handler callbacks (override in `impl DataActor`):
- `on_start / on_stop / on_reset`
- `on_quote(&mut self, quote: &QuoteTick) -> Result<()>`
- `on_trade(&mut self, trade: &TradeTick) -> Result<()>`
- `on_bar(&mut self, bar: &Bar) -> Result<()>`
- `on_book_deltas(&mut self, deltas: &OrderBookDeltas) -> Result<()>` — batch, not single delta
- `on_instrument(&mut self, instrument: &InstrumentAny) -> Result<()>`
- `on_data(&mut self, data: &CustomData) -> Result<()>` — custom data types

### Custom Data Types

```rust
use nautilus_core::UnixNanos;
use nautilus_persistence_macros::custom_data;

#[custom_data]
pub struct VpinSnapshot {
    pub instrument_id: InstrumentId,
    pub buy_volume: f64,
    pub sell_volume: f64,
    pub vpin: f64,
    pub ts_event: UnixNanos,  // REQUIRED
    pub ts_init: UnixNanos,   // REQUIRED — compilation fails without both
}
```

Supported field types: `f64`, `f32`, `i64`, `i32`, `u64`, `u32`, `u16`, `u8`, `bool`, `String`, `InstrumentId`, `Vec<f64>`, `Vec<u8>`.

Register once at startup before publishing or querying:
```rust
nautilus_serialization::ensure_custom_data_registered::<VpinSnapshot>();
```

Publishing:
```rust
use std::sync::Arc;
use nautilus_common::{msgbus, msgbus::switchboard::get_custom_topic};
use nautilus_model::data::CustomData;

let snapshot = VpinSnapshot { /* ... */ };
let custom = CustomData::from_arc(Arc::new(snapshot));
let topic = get_custom_topic(&custom.data_type);
msgbus::publish_any(topic, &custom);
```

Subscribing (in `on_start`):
```rust
use nautilus_model::data::DataType;
let data_type = DataType::new(stringify!(VpinSnapshot), None, None);
self.subscribe_data(data_type, None, None);
```

Receiving (in `on_data`):
```rust
fn on_data(&mut self, data: &CustomData) -> Result<()> {
    let Some(snap) = data.data.as_any().downcast_ref::<VpinSnapshot>() else {
        return Ok(());
    };
    println!("vpin={:.4}", snap.vpin);
    Ok(())
}
```

`CustomData` has a public `.data: Arc<dyn CustomDataTrait>` field — no `.inner()` method exists.

### Signal Pattern (Actor → Strategy)

Python's `publish_signal`/`subscribe_signal` are Cython-only. The Rust equivalent:

```rust
#[custom_data]
pub struct MomentumSignal {
    pub value: f64,
    pub ts_event: UnixNanos,
    pub ts_init: UnixNanos,
}
```

Actor publishes via `msgbus::publish_any`. Strategy subscribes via `subscribe_data(DataType::new("MomentumSignal", None, None), None, None)` and receives in `on_data`.
| `queue_for_executor` is async | It schedules an async coroutine from a sync context — the callback itself is sync |

## Related Examples

- [signal_pipeline_backtest.py](../examples/signal_pipeline_backtest.py) — Actor signal pipeline with publish_signal
- [signal_actor_backtest.rs](../examples/signal_actor_backtest.rs) — Rust DataActor signal pub/sub
- [binance_enrichment_actor.py](../examples/binance_enrichment_actor.py) — Actor polling REST for OI + funding data
