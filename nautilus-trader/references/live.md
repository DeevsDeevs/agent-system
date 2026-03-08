# Live Trading

## TradingNode Setup

```python
from nautilus_trader.live.node import TradingNode
from nautilus_trader.config import TradingNodeConfig

config = TradingNodeConfig(
    trader_id="TRADER-001",
    timeout_connection=30.0,
    timeout_reconciliation=10.0,
    data_clients={...},
    exec_clients={...},
)

node = TradingNode(config=config)
node.trader.add_strategy(strategy)
node.run()
```

## Critical Constraints

- **No Jupyter notebooks** for live trading — event loop conflicts cause instability
- **One TradingNode per process** — additional nodes require separate processes
- **No blocking on event loop** — `on_bar()`, `on_tick()` handlers must return quickly
- User code on the event loop must avoid I/O, sleep, or heavy computation

## Windows Shutdown

```python
try:
    node.run()
except KeyboardInterrupt:
    pass
finally:
    try:
        node.stop()
    finally:
        node.dispose()
```

On Windows, `asyncio` event loops lack `loop.add_signal_handler`, requiring manual shutdown.

## Execution Reconciliation

Aligns internal state with venue reality by recovering missed events.

### Startup Reconciliation

Handles on startup:
- Order state discrepancies
- Missed or multiple fills
- External orders placed outside the system
- Position quantity mismatches

### Continuous Reconciliation

| Setting | Default | Purpose |
|---------|---------|---------|
| `reconciliation` | `True` | Enable startup reconciliation |
| `inflight_check_interval_ms` | 2,000 | In-flight order check frequency |
| `open_check_interval_secs` | `None` | Open order polling frequency (5-10s recommended) |
| `open_check_lookback_mins` | 60 | Order history lookback (never reduce below 60) |
| `position_check_interval_secs` | `None` | Position discrepancy checks |

### Order Resolution (Max Retries Exceeded)

| Current Status | Resolution | Rationale |
|----------------|------------|-----------|
| `SUBMITTED` | `REJECTED` | No confirmation received |
| `PENDING_UPDATE` | `CANCELED` | Modification unacknowledged |
| `PENDING_CANCEL` | `CANCELED` | Cancel never confirmed |

### Safety Rules

- "Not found" resolutions only in full-history mode
- Open-only mode skips checks (venue "open orders" excludes closed)
- Recent order protection: 5-second buffer (default) to prevent race condition false positives

## State Persistence

### Cache Configuration

```python
from nautilus_trader.config import CacheConfig

cache_config = CacheConfig(
    database="redis",      # or "postgres"
    encoding="msgpack",    # or "json"
    timestamps_as_iso8601=False,
    buffer_interval_ms=100,
)
```

Enables recovery of orders, positions, and account state across restarts.

## Memory Management

Long-running sessions need periodic purging:

```python
from nautilus_trader.config import LiveExecEngineConfig

exec_config = LiveExecEngineConfig(
    purge_closed_orders_interval_secs=600,    # 10 minutes
    purge_closed_positions_interval_secs=600,
    purge_account_events_interval_secs=900,   # 15 minutes
)
```

Safety buffer ensures 60-minute retention before removal.

## External Order Claims

Declare instruments whose external orders (placed outside Nautilus) should be claimed:

```python
from nautilus_trader.config import StrategyConfig

class MyConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    external_order_claims: list[str] = ["BTCUSDT-PERP.BINANCE"]
```

External orders appear via `on_order_accepted`, `on_order_filled` etc.

## Multi-Venue Configuration

```python
config = TradingNodeConfig(
    data_clients={
        "BINANCE": BinanceDataClientConfig(
            account_type=BinanceAccountType.USDT_FUTURES,
            api_key="...",
            api_secret="...",
        ),
        "DATABENTO": DatabentoDataClientConfig(
            api_key="...",
        ),
    },
    exec_clients={
        "BINANCE": BinanceExecClientConfig(
            account_type=BinanceAccountType.USDT_FUTURES,
            api_key="...",
            api_secret="...",
        ),
    },
)
```

## MessageBus External Streaming

```python
from nautilus_trader.config import MessageBusConfig

msgbus_config = MessageBusConfig(
    database="redis",
    stream="nautilus",     # Redis stream name
    use_instance_id=True,  # per-instance isolation
    streams_prefix="trader",
)
```

Enables external systems to consume Nautilus events via Redis streams.
