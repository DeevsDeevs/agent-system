# Clock & Timers

## Clock API

Every `Strategy` and `Actor` has `self.clock` — a `Clock` instance (BacktestClock in backtest, LiveClock in live). Same interface, different time sources.

```python
# Current time
self.clock.utc_now()       # pandas Timestamp (tz-aware UTC)
self.clock.timestamp_ns()  # int — nanosecond epoch
self.clock.timestamp_ms()  # int — millisecond epoch
self.clock.timestamp_us()  # int — microsecond epoch
self.clock.timestamp()     # float — seconds epoch
self.clock.local_now(tz)   # pandas Timestamp in local timezone
```

## Recurring Timer

Fires repeatedly at fixed interval until canceled.

```python
from datetime import timedelta

def on_start(self) -> None:
    self.clock.set_timer(
        "rebalance",                               # unique name
        interval=timedelta(seconds=10),            # firing interval
        callback=self._on_rebalance,               # handler
    )

def _on_rebalance(self, event) -> None:
    # event is a TimeEvent with: name, ts_event, ts_init
    positions = self.cache.positions_open(instrument_id=self.instrument_id)
    # ... rebalancing logic
```

**Full signature**:
```python
clock.set_timer(
    name,                    # str — unique timer name
    interval,                # timedelta — firing interval
    start_time=None,         # Optional[datetime] — when to start (default: now)
    stop_time=None,          # Optional[datetime] — when to stop (default: never)
    callback=None,           # Callable[[TimeEvent], None] — handler (REQUIRED in practice)
    allow_past=True,         # bool — allow start_time in the past
    fire_immediately=False,  # bool — fire once immediately on creation
)
```

## One-Shot Time Alert

Fires once at a specific time, then auto-removes.

```python
from datetime import timedelta

self.clock.set_time_alert(
    "exit_funding",                                  # unique name
    alert_time=self.clock.utc_now() + timedelta(seconds=30),  # when to fire
    callback=self._on_exit_funding,                  # handler
)

def _on_exit_funding(self, event) -> None:
    self.close_all_positions(self.instrument_id)
```

**Full signature**:
```python
clock.set_time_alert(
    name,                    # str — unique alert name
    alert_time,              # datetime — when to fire
    callback=None,           # Callable[[TimeEvent], None]
    override=False,          # bool — overwrite existing alert with same name
    allow_past=True,         # bool — allow alert_time in the past
)
```

## Cancel Timer

```python
self.clock.cancel_timer("rebalance")   # cancel specific timer
self.clock.cancel_timers()             # cancel ALL timers
```

## Timer Callback Signature

All timer callbacks receive a `TimeEvent`:

```python
def _on_timer(self, event) -> None:
    # event.name      — str, timer name
    # event.ts_event  — int, nanosecond epoch when timer was scheduled to fire
    # event.ts_init   — int, nanosecond epoch when event was created
    pass
```

## Anti-Patterns

| Wrong | Right |
|-------|-------|
| `def on_timer(self, event)` | Doesn't exist. Use `clock.set_timer(callback=handler)` |
| `time.sleep(5)` in callback | Blocks the entire event loop. Use `set_time_alert` instead |
| Timer without callback | Callback is required — without it, timer fires but nothing happens |
| Multiple timers with same name | Raises error. Cancel first or use `override=True` on alerts |

## Patterns

### Periodic Position Check

```python
def on_start(self) -> None:
    self.clock.set_timer(
        "position_check", interval=timedelta(seconds=5),
        callback=self._check_positions,
    )

def _check_positions(self, event) -> None:
    positions = self.cache.positions_open(instrument_id=self.config.instrument_id)
    if not positions:
        return
    pos = positions[0]
    pnl = pos.unrealized_pnl(self.cache.quote_tick(self.config.instrument_id).bid_price)
    if float(pnl) < -100:  # drawdown limit
        self.close_position(pos)
        self.log.warning(f"Position closed: drawdown {pnl}")
```

### Stale Order Cleanup

```python
def on_start(self) -> None:
    self.clock.set_timer(
        "stale_cleanup", interval=timedelta(seconds=30),
        callback=self._cleanup_stale_orders,
    )

def _cleanup_stale_orders(self, event) -> None:
    now_ns = self.clock.timestamp_ns()
    for order in self.cache.orders_open(instrument_id=self.config.instrument_id):
        age_secs = (now_ns - order.ts_init) / 1_000_000_000
        if age_secs > 60:
            self.cancel_order(order)
```

### Funding Rate Window

Perpetual funding typically settles at 00:00, 08:00, 16:00 UTC.

```python
from datetime import timedelta

def on_start(self) -> None:
    self.clock.set_timer(
        "funding_check", interval=timedelta(minutes=1),
        callback=self._check_funding_window,
    )

def _check_funding_window(self, event) -> None:
    now = self.clock.utc_now()
    hour, minute = now.hour, now.minute
    # Funding windows: 00:00, 08:00, 16:00 UTC
    for fh in (0, 8, 16):
        minutes_until = ((fh - hour) % 8) * 60 - minute
        if 0 < minutes_until <= 5:  # 5 minutes before funding
            self._enter_funding_trade()
            break
```

### Self-Termination (Live Trading)

Stop the node programmatically (used in tests and time-limited runs):

```python
import os
import signal as sig

def _shutdown(self, event) -> None:
    self.cancel_all_orders(self.config.instrument_id)
    self.close_all_positions(self.config.instrument_id)
    # Schedule kill after cleanup
    self.clock.set_time_alert(
        "kill",
        alert_time=self.clock.utc_now() + timedelta(seconds=2),
        callback=lambda _: os.kill(os.getpid(), sig.SIGINT),
    )
```

### Data Collection with Status Reporting

```python
def on_start(self) -> None:
    self.start_time = self.clock.timestamp()
    self.clock.set_timer(
        "status", interval=timedelta(seconds=5),
        callback=self._report_status,
    )
    self.clock.set_timer(
        "shutdown", interval=timedelta(seconds=60),
        callback=self._shutdown,
    )

def _report_status(self, event) -> None:
    elapsed = self.clock.timestamp() - self.start_time
    self.log.info(f"[{elapsed:.0f}s] Events: {self.event_count}")
```

## Backtest vs Live Behavior

| Aspect | Backtest | Live |
|--------|----------|------|
| Time source | Data timestamps (simulated) | System clock (real) |
| Timer precision | Exact — fires at scheduled data time | Approximate — async event loop |
| `utc_now()` | Advances with data replay | Real UTC time |
| `fire_immediately` | Fires at current data time | Fires immediately on creation |
| `set_time_alert` | Fires when data time passes alert time | Fires at real wall-clock time |
