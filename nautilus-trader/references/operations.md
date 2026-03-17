# Operations

## Clock API *(Python only)*

> *No `self.clock` on Rust. Use `std::time::Instant` — see [## Rust](#rust).*

`self.clock` on every `Strategy`/`Actor` — `BacktestClock` in backtest, `LiveClock` in live.

| Method | Returns |
|--------|---------|
| `utc_now()` | pandas Timestamp (tz-aware UTC) |
| `timestamp_ns()` | int (nanosecond epoch) |
| `timestamp_ms()` | int (millisecond epoch) |
| `timestamp_us()` | int (microsecond epoch) |
| `timestamp()` | float (seconds epoch) |
| `local_now(tz)` | pandas Timestamp (local) |

## Recurring Timer

```python
def on_start(self) -> None:
    self.clock.set_timer(
        "rebalance", interval=timedelta(seconds=10),
        callback=self._on_rebalance,
    )

def _on_rebalance(self, event) -> None:
    positions = self.cache.positions_open(instrument_id=self.instrument_id)
```

Full signature: `clock.set_timer(name, interval, start_time=None, stop_time=None, callback=None, allow_past=True, fire_immediately=False)`

## One-Shot Time Alert

```python
self.clock.set_time_alert(
    "exit_funding",
    alert_time=self.clock.utc_now() + timedelta(seconds=30),
    callback=self._on_exit_funding,
)
```

Full signature: `clock.set_time_alert(name, alert_time, callback=None, override=False, allow_past=True)`

## Cancel Timer

```python
self.clock.cancel_timer("rebalance")   # cancel specific timer
self.clock.cancel_timers()             # cancel ALL timers
```

## Timer Anti-Patterns

| Wrong | Right |
|-------|-------|
| `def on_timer(self, event)` | Doesn't exist. Use `clock.set_timer(callback=handler)` |
| `time.sleep(5)` in callback | Blocks event loop. Use `set_time_alert` instead |
| Timer without callback | Required — without it, nothing happens |
| Multiple timers with same name | Raises error. Cancel first or use `override=True` on alerts |

## Timer Patterns

### Periodic Position Check

```python
def on_start(self) -> None:
    self.clock.set_timer("position_check", interval=timedelta(seconds=5),
        callback=self._check_positions)

def _check_positions(self, event) -> None:
    positions = self.cache.positions_open(instrument_id=self.config.instrument_id)
    if not positions:
        return
    pos = positions[0]
    pnl = pos.unrealized_pnl(self.cache.quote_tick(self.config.instrument_id).bid_price)
    if float(pnl) < -100:
        self.close_position(pos)
```

### Stale Order Cleanup

```python
def on_start(self) -> None:
    self.clock.set_timer("stale_cleanup", interval=timedelta(seconds=30),
        callback=self._cleanup_stale_orders)

def _cleanup_stale_orders(self, event) -> None:
    now_ns = self.clock.timestamp_ns()
    for order in self.cache.orders_open(instrument_id=self.config.instrument_id):
        age_secs = (now_ns - order.ts_init) / 1_000_000_000
        if age_secs > 60:
            self.cancel_order(order)
```

### Programmatic Shutdown

```python
def _initiate_shutdown(self) -> None:
    self.cancel_all_orders(self.config.instrument_id)
    self.close_all_positions(self.config.instrument_id)
    self.clock.set_time_alert("kill",
        alert_time=self.clock.utc_now() + timedelta(seconds=2),
        callback=lambda _: os.kill(os.getpid(), signal.SIGINT))
```

2-second delay gives fills time to arrive before shutdown.

| Aspect | Backtest | Live |
|--------|----------|------|
| Time source | Data timestamps (simulated) | System clock (real) |
| Timer precision | Exact | Approximate (async event loop) |
| `set_time_alert` | Fires when data time passes alert | Fires at wall-clock time |

## Graceful Shutdown

> *Rust: `cancel_all_orders`/`close_all_positions` in `on_stop` silently fail — channel closes before `on_stop` fires. Cancel from `on_trade` instead.*

`on_stop()` fires on SIGINT or `node.stop()`. `close_all_positions` submits `reduce_only=True` market orders; fills may arrive after return. Multi-instrument: loop with try/except.

```python
def on_stop(self) -> None:
    self.cancel_all_orders(self.config.instrument_id)
    self.close_all_positions(self.config.instrument_id)
```

## Error Recovery

```python
def on_order_rejected(self, event) -> None:
    self.log.warning(f"Order rejected: {event.reason}")
    if event.client_order_id == self._bid_id:
        self._bid_id = None
    elif event.client_order_id == self._ask_id:
        self._ask_id = None

def on_order_modify_rejected(self, event) -> None:
    order = self.cache.order(event.client_order_id)
    if order and order.is_open:
        self.cancel_order(order)

def on_order_cancel_rejected(self, event) -> None:
    self.log.warning(f"Cancel rejected: {event.reason}")

def on_order_denied(self, event) -> None:
    self.log.error(f"Order denied by RiskEngine: {event.reason}")
```

## Drawdown Circuit Breaker

```python
class CircuitBreakerMixin:
    def _init_circuit_breaker(self, max_drawdown_usdt: float = 100.0):
        self._max_drawdown = max_drawdown_usdt
        self._halted = False
        self.clock.set_timer("pnl_check", interval=timedelta(seconds=5),
            callback=self._check_pnl)

    def _check_pnl(self, event) -> None:
        if self._halted:
            return
        pnls = self.portfolio.unrealized_pnls(self.config.instrument_id.venue)
        if pnls:
            total = sum(float(v) for v in pnls.values())
            if total < -self._max_drawdown:
                self._halted = True
                self.log.error(f"CIRCUIT BREAKER: PnL={total:.2f}, halting")
                self.cancel_all_orders(self.config.instrument_id)
                self.close_all_positions(self.config.instrument_id)
```

## Stale Book Detection

```python
def on_order_book_deltas(self, deltas) -> None:
    book = self.cache.order_book(self.config.instrument_id)
    if not book.best_bid_price() or not book.best_ask_price():
        return
    spread = float(book.spread())
    mid = float(book.midpoint())
    spread_bps = (spread / mid) * 10_000 if mid > 0 else float('inf')
    if spread_bps > 50:
        self.log.warning(f"Wide spread {spread_bps:.1f}bps — possible stale book")
        return
```

## Reconnection Handling

WebSocket reconnection is automatic. Book rebuilds from snapshot, orders/positions reconcile with venue. Ticks during disconnect are lost.

```python
def on_order_book_deltas(self, deltas) -> None:
    book = self.cache.order_book(self.config.instrument_id)
    if book.update_count == 0:
        return  # awaiting snapshot after reconnect
```

## Logging *(Python only)*

> *Rust: no `self.log`. Use `println!()` or `tracing` crate.*

`LoggingConfig(log_level="INFO", log_level_file="DEBUG", log_directory="/var/log/nautilus/")`. Methods: `self.log.info()`, `.warning()`, `.error()`, `.debug()` (DEBUG level only).

## Health Monitoring via External Streaming *(Python only)*

`MessageBusConfig(database=DatabaseConfig(type="redis", ...), external_streams=["data.*", "events.order.*", "events.position.*"])`

## Rust

### Timer Pattern

No `self.clock`. Track timing with `std::time::Instant`, checked on every market event:

```rust
struct MyStrategy {
    core: StrategyCore,
    action_after: Option<std::time::Instant>,
}

fn on_order_accepted(&mut self, event: OrderAccepted) {
    self.action_after = Some(std::time::Instant::now());
}

fn on_trade(&mut self, trade: &TradeTick) -> Result<()> {
    if let Some(t) = self.action_after {
        if t.elapsed() >= std::time::Duration::from_secs(5) {
            self.cancel_all_orders(self.instrument_id, None, None)?;
            self.action_after = None;
        }
    }
    Ok(())
}
```

### Error Callbacks

```rust
impl Strategy for MyStrategy {
    fn on_order_rejected(&mut self, event: OrderRejected) {
        println!("Rejected: {}", event.reason);
        if Some(event.client_order_id) == self.bid_order_id {
            self.bid_order_id = None;
        }
    }
    fn on_order_cancel_rejected(&mut self, event: OrderCancelRejected) {
        println!("Cancel rejected: {}", event.reason);
    }
    fn on_order_modify_rejected(&mut self, event: OrderModifyRejected) {
        println!("Modify rejected: {}", event.reason);
    }
}
```

### Logging

`println!()` for basic. Structured: `tracing` crate (`info!`, `warn!`, `error!`) with `tracing_subscriber::fmt::init()`.

### Shutdown

`cancel_all_orders` in Rust `on_stop` is a silent no-op (channel already closed). Use `tokio::select!` with `node.run()`, timeout, and `ctrl_c()`. After `node.stop()`, WS stays alive ~10s — use `std::process::exit(0)`. See `live_data_collector.rs` for full pattern.

## Related Examples

- [spread_capture_live.py](../examples/spread_capture_live.py)
- [live_data_collector.rs](../examples/live_data_collector.rs)
