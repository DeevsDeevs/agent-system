# Operational Patterns

Production patterns for live crypto HFT with NautilusTrader.

## Graceful Shutdown

`on_stop()` is called when the node receives SIGINT or `node.stop()` is called. It must clean up.

```python
def on_stop(self) -> None:
    self.cancel_all_orders(self.config.instrument_id)
    self.close_all_positions(self.config.instrument_id)
```

For multi-instrument strategies:
```python
def on_stop(self) -> None:
    for inst_id in self.instrument_ids:
        try:
            self.cancel_all_orders(inst_id)
            self.close_all_positions(inst_id)
        except Exception as e:
            self.log.error(f"Cleanup error for {inst_id}: {e}")
```

`close_all_positions` submits market orders with `reduce_only=True`. Fills may arrive after `on_stop` returns — the engine handles this.

## Programmatic Shutdown

Stop the node from within a strategy (for timed runs, error conditions):

```python
import os
import signal as sig

def _initiate_shutdown(self) -> None:
    self.cancel_all_orders(self.config.instrument_id)
    self.close_all_positions(self.config.instrument_id)
    self.clock.set_time_alert(
        "kill",
        alert_time=self.clock.utc_now() + timedelta(seconds=2),
        callback=lambda _: os.kill(os.getpid(), sig.SIGINT),
    )
```

The 2-second delay gives fills time to arrive before the node shuts down.

## Error Recovery

### Order Rejection

Venue rejects the order (insufficient margin, invalid price, etc.):

```python
def on_order_rejected(self, event) -> None:
    self.log.warning(f"Order rejected: {event.reason}")
    # Clear tracked order ID so next cycle creates a new order
    if event.client_order_id == self._bid_id:
        self._bid_id = None
    elif event.client_order_id == self._ask_id:
        self._ask_id = None
```

### Modify Rejection

Venue rejects the amend (order already filled, price invalid):

```python
def on_order_modify_rejected(self, event) -> None:
    self.log.warning(f"Modify rejected: {event.reason}")
    # Cancel and re-create instead
    order = self.cache.order(event.client_order_id)
    if order and order.is_open:
        self.cancel_order(order)
```

### Cancel Rejection

```python
def on_order_cancel_rejected(self, event) -> None:
    self.log.warning(f"Cancel rejected: {event.reason}")
    # Order may have filled between cancel request and rejection
    order = self.cache.order(event.client_order_id)
    if order and order.is_closed:
        self.log.info("Order already closed, nothing to do")
```

### Denial (Pre-Trade)

RiskEngine denies the order before it reaches the venue:

```python
def on_order_denied(self, event) -> None:
    self.log.error(f"Order denied by RiskEngine: {event.reason}")
    # Likely: precision error, notional limit, rate limit
    # Do NOT retry immediately — fix the root cause
```

## Drawdown Circuit Breaker

Track PnL and halt trading when drawdown exceeds threshold:

```python
class CircuitBreakerMixin:
    def _init_circuit_breaker(self, max_drawdown_usdt: float = 100.0):
        self._max_drawdown = max_drawdown_usdt
        self._halted = False
        self.clock.set_timer(
            "pnl_check", interval=timedelta(seconds=5),
            callback=self._check_pnl,
        )

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

After WebSocket reconnection, the order book may be stale until a fresh snapshot arrives:

```python
def on_order_book_deltas(self, deltas) -> None:
    book = self.cache.order_book(self.config.instrument_id)
    if not book.best_bid_price() or not book.best_ask_price():
        return  # book not yet rebuilt

    spread = float(book.spread())
    mid = float(book.midpoint())
    spread_bps = (spread / mid) * 10_000 if mid > 0 else float('inf')

    # Abnormally wide spread suggests stale/rebuilding book
    if spread_bps > 50:
        self.log.warning(f"Wide spread {spread_bps:.1f}bps — possible stale book")
        return  # skip requoting until book stabilizes
```

## Memory Purge (Long-Running)

NautilusTrader accumulates closed orders and positions in cache. For long-running sessions, configure purging:

```python
from nautilus_trader.config import LiveExecEngineConfig

exec_config = LiveExecEngineConfig(
    reconciliation=True,
    reconciliation_lookback_mins=60,
)
```

Cache purge is automatic for closed orders/positions. For explicit control in a strategy:
```python
# Periodically check cache sizes
def _monitor_cache(self, event) -> None:
    orders = self.cache.orders()
    positions = self.cache.positions()
    self.log.info(f"Cache: {len(orders)} orders, {len(positions)} positions")
```

## Reconnection Handling

WebSocket reconnection is handled automatically by adapters. Strategy-level considerations:

1. **Order book**: Adapter requests fresh snapshot on reconnect. Book rebuilds transparently.
2. **Open orders**: Reconciliation queries venue for open orders on reconnect.
3. **Positions**: Reconciliation verifies position state matches venue.
4. **Data gaps**: Ticks/deltas during disconnect are lost. No backfill.

Strategy should handle the gap:
```python
def on_order_book_deltas(self, deltas) -> None:
    book = self.cache.order_book(self.config.instrument_id)
    if book.update_count == 0:
        return  # book empty — awaiting snapshot after reconnect
```

## Logging in Production

```python
from nautilus_trader.config import LoggingConfig

logging = LoggingConfig(
    log_level="INFO",          # DEBUG is extremely verbose
    log_level_file="DEBUG",    # full debug to file only
    log_directory="/var/log/nautilus/",
    log_file_format=None,      # default format
    log_colors=False,          # no ANSI in files
    bypass_logging=False,      # never bypass in production
)
```

Strategy logging:
```python
self.log.info("Normal operation")
self.log.warning("Recoverable issue")
self.log.error("Needs attention")
self.log.debug("Verbose detail")  # only visible at DEBUG level
```

## Health Monitoring via External Streaming

Stream MessageBus events to Redis/Kafka for external monitoring:

```python
from nautilus_trader.config import DatabaseConfig, MessageBusConfig

msgbus_config = MessageBusConfig(
    database=DatabaseConfig(type="redis", host="localhost", port=6379),
    external_streams=["data.*", "events.order.*", "events.position.*"],
)
```

## Reconciliation Configuration

```python
from nautilus_trader.config import LiveExecEngineConfig

exec_config = LiveExecEngineConfig(
    reconciliation=True,                      # enable reconciliation
    reconciliation_lookback_mins=60,          # how far back to check
    reconciliation_instrument_ids=None,       # None = all instruments
    open_check_lookback_mins=30,              # open order check window
    open_check_threshold_ms=5000,             # skip recently submitted orders
    max_single_order_queries_per_cycle=10,    # rate limit queries
    single_order_query_delay_ms=100,          # delay between queries
    reconciliation_startup_delay_secs=10,     # DO NOT reduce below 10
)
```

**Key gotchas**:
- `reconciliation_startup_delay_secs < 10` causes premature reconciliation
- `open_check_lookback_mins` too short → false "missing order" resolutions
- Flatten positions before restart if possible to avoid mismatch
- External orders (manual trades) during lookback window cause mismatches

## Timeouts

```python
config = TradingNodeConfig(
    timeout_connection=20.0,        # seconds to connect to venues
    timeout_reconciliation=60.0,    # seconds for order/position reconciliation
    timeout_portfolio=120.0,        # seconds for portfolio initialization
    timeout_disconnection=10.0,     # seconds for graceful disconnect
    timeout_post_stop=10.0,         # seconds after stop for final cleanup
)
```

Increase `timeout_reconciliation` for accounts with many open orders. Increase `timeout_portfolio` for multi-venue setups.
