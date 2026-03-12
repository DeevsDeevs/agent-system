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

## Signal API (Native — Preferred)

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

## Actor for External Data (Live)

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
