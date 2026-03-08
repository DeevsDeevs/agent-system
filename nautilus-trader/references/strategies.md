# Strategies

## Strategy vs Actor

`Actor` — receives data, handles events, manages state. No order management.

`Strategy` — extends Actor with order management (order_factory, submit_order, position tracking, portfolio access).

Use Actors for: data collection, signal computation, monitoring, custom data publishing.
Use Strategies for: anything that places orders.

## Configuration Pattern

Configs are frozen Pydantic models inheriting `StrategyConfig`:

```python
from decimal import Decimal
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model import BarType, InstrumentId


class MyConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal
    fast_ema_period: int = 10
    slow_ema_period: int = 20
    order_id_tag: str = "001"

config = MyConfig(
    instrument_id=InstrumentId.from_str("ETHUSDT-PERP.BINANCE"),
    bar_type=BarType.from_str("ETHUSDT-PERP.BINANCE-15-MINUTE[LAST]-EXTERNAL"),
    trade_size=Decimal(1),
)
```

Access config in strategy via `self.config`.

## Indicator Registration

Indicators auto-update when registered to a data source:

```python
from nautilus_trader.indicators import ExponentialMovingAverage

def __init__(self, config):
    super().__init__(config)
    self.fast_ema = ExponentialMovingAverage(config.fast_ema_period)
    self.slow_ema = ExponentialMovingAverage(config.slow_ema_period)

def on_start(self):
    # Auto-update indicators when bars arrive
    self.register_indicator_for_bars(self.config.bar_type, self.fast_ema)
    self.register_indicator_for_bars(self.config.bar_type, self.slow_ema)

    # Also available:
    # self.register_indicator_for_quote_ticks(instrument_id, indicator)
    # self.register_indicator_for_trade_ticks(instrument_id, indicator)
```

Always check `self.indicators_initialized()` before using indicator values in handlers.

## Data Subscriptions

```python
def on_start(self):
    # Bars
    self.subscribe_bars(bar_type)
    self.request_bars(bar_type)      # historical fill

    # Ticks
    self.subscribe_quote_ticks(instrument_id)
    self.subscribe_trade_ticks(instrument_id)

    # Order book
    self.subscribe_order_book_deltas(instrument_id)
    self.subscribe_order_book_depth(instrument_id)
    self.subscribe_order_book_at_interval(instrument_id, interval_ms=1000)

    # Instrument
    self.request_instrument(instrument_id)
    self.subscribe_instrument_status(instrument_id)
```

## Position Tracking

```python
def on_bar(self, bar):
    # Check position state
    if self.portfolio.is_flat(self.config.instrument_id):
        self.enter_long()
    elif self.portfolio.is_net_long(self.config.instrument_id):
        self.exit_long()

def on_position_opened(self, event):
    self.log.info(f"Opened: {event.position}")

def on_position_changed(self, event):
    self.log.info(f"Changed: {event.position}")

def on_position_closed(self, event):
    self.log.info(f"Closed: {event.position}")
```

### Position Event Handlers

| Handler | Trigger |
|---------|---------|
| `on_position_opened(event)` | First fill creates position |
| `on_position_changed(event)` | Subsequent fills modify position |
| `on_position_closed(event)` | Net quantity reaches zero |
| `on_position_event(event)` | All position events |

## OMS Types

| Strategy OMS | Venue OMS | Result |
|--------------|-----------|--------|
| `NETTING` | `NETTING` | Single position per instrument |
| `HEDGING` | `HEDGING` | Multiple independent positions |
| `NETTING` | `HEDGING` | Venue multiple, Nautilus single |
| `HEDGING` | `NETTING` | Venue single, Nautilus virtual positions |

## Order Management Patterns

### Bracket Order (Entry + Stop-Loss + Take-Profit)

```python
def enter_long(self):
    entry = self.order_factory.limit(
        instrument_id=self.config.instrument_id,
        order_side=OrderSide.BUY,
        quantity=self.instrument.make_qty(self.config.trade_size),
        price=self.instrument.make_price(entry_price),
    )
    stop_loss = self.order_factory.stop_market(
        instrument_id=self.config.instrument_id,
        order_side=OrderSide.SELL,
        quantity=self.instrument.make_qty(self.config.trade_size),
        trigger_price=self.instrument.make_price(sl_price),
        reduce_only=True,
    )
    take_profit = self.order_factory.limit(
        instrument_id=self.config.instrument_id,
        order_side=OrderSide.SELL,
        quantity=self.instrument.make_qty(self.config.trade_size),
        price=self.instrument.make_price(tp_price),
        reduce_only=True,
    )
    order_list = OrderList(
        order_list_id=OrderListId("BRACKET-001"),
        orders=[entry, stop_loss, take_profit],
        contingency_type=ContingencyType.OTO,
    )
    self.submit_order_list(order_list)
```

### Modifying Orders

```python
def on_order_accepted(self, event):
    order = self.cache.order(event.client_order_id)
    self.modify_order(
        order=order,
        quantity=new_qty,
        price=new_price,
    )
```

## Timers and Scheduling

```python
def on_start(self):
    # One-shot alert
    self.clock.set_time_alert(
        name="close_positions",
        alert_time=pd.Timestamp("2024-01-01 15:55:00", tz="UTC"),
    )

    # Recurring timer
    self.clock.set_timer(
        name="rebalance",
        interval=pd.Timedelta(minutes=5),
    )

def on_event(self, event):
    if isinstance(event, TimeEvent):
        if event.name == "close_positions":
            self.close_all_positions(self.config.instrument_id)
        elif event.name == "rebalance":
            self.rebalance()
```

## System Access

| Property | Use |
|----------|-----|
| `self.cache` | Instruments, orders, positions, market data |
| `self.portfolio` | Portfolio state, P&L, exposure |
| `self.clock` | Time, timers, alerts |
| `self.log` | Structured logging |
| `self.msgbus` | Publish/subscribe messaging |
| `self.order_factory` | Create orders |
| `self.config` | Strategy configuration |

## State Persistence

```python
def on_save(self) -> dict[str, bytes]:
    return {
        "trade_count": str(self.trade_count).encode(),
        "last_signal": self.last_signal.encode(),
    }

def on_load(self, state: dict[str, bytes]) -> None:
    self.trade_count = int(state["trade_count"].decode())
    self.last_signal = state["last_signal"].decode()
```
