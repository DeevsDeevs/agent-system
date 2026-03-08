# Live Trading Operations

TradingNode configuration, state persistence, deployment, and operational concerns.

## TradingNode Setup

```python
from nautilus_trader.config import (
    CacheConfig,
    DatabaseConfig,
    LiveExecEngineConfig,
    LoggingConfig,
    MessageBusConfig,
    TradingNodeConfig,
)
from nautilus_trader.live.node import TradingNode

config = TradingNodeConfig(
    trader_id="CRYPTO-HFT-001",
    logging=LoggingConfig(log_level="INFO"),
    cache=CacheConfig(
        database=DatabaseConfig(
            type="redis",
            host="localhost",
            port=6379,
        ),
    ),
    message_bus=MessageBusConfig(
        database=DatabaseConfig(
            type="redis",
            host="localhost",
            port=6379,
        ),
    ),
    data_engine=LiveDataEngineConfig(),
    exec_engine=LiveExecEngineConfig(
        reconciliation=True,
        reconciliation_lookback_mins=1440,
    ),
    data_clients={
        "BINANCE": BinanceDataClientConfig(
            api_key=os.environ["BINANCE_API_KEY"],
            api_secret=os.environ["BINANCE_API_SECRET"],
            account_type=BinanceAccountType.USDT_FUTURE,
        ),
    },
    exec_clients={
        "BINANCE": BinanceExecClientConfig(
            api_key=os.environ["BINANCE_API_KEY"],
            api_secret=os.environ["BINANCE_API_SECRET"],
            account_type=BinanceAccountType.USDT_FUTURE,
        ),
    },
    timeout_connection=30.0,
    timeout_reconciliation=10.0,
    timeout_portfolio=10.0,
    timeout_disconnection=10.0,
    timeout_post_stop=5.0,
)

node = TradingNode(config=config)

# Register adapter factories
node.add_data_client_factory("BINANCE", BinanceLiveDataClientFactory)
node.add_exec_client_factory("BINANCE", BinanceLiveExecClientFactory)

# Add strategies
node.trader.add_strategy(MyStrategy(my_config))

# Build and run
node.build()
node.run()  # blocks until shutdown signal
```

## TradingNode vs BacktestNode

| Aspect | TradingNode | BacktestNode |
|--------|-------------|--------------|
| Clock | `LiveClock` (real time) | `TestClock` (simulated) |
| Data | Real venue streams | Historical data |
| Execution | Real venue APIs | `SimulatedExchange` |
| Event loop | Async (single loop) | Synchronous |
| Constraint | One per process | Sequential runs OK |
| Strategy code | Identical | Identical |

Same `Strategy` class works in both — adapters abstract the difference.

## State Persistence

### Redis (Recommended for State Recovery)

High-performance key-value store. Stores orders, positions, accounts for fast recovery on restart.

```python
CacheConfig(
    database=DatabaseConfig(
        type="redis",
        host="localhost",
        port=6379,
    ),
)
```

### PostgreSQL (Recommended for Audit Trail)

Full relational persistence. Stores complete order/position/fill history for analysis and compliance.

```python
CacheConfig(
    database=DatabaseConfig(
        type="postgres",
        host="localhost",
        port=5432,
        username="nautilus",
        password="...",
        database="nautilus_trading",
    ),
)
```

### What Gets Persisted

- Orders: Full lifecycle events
- Positions: Open/closed state, fills
- Accounts: Balance snapshots
- Custom strategy state: via `on_save()` / `on_load()`

## Reconciliation

### On Startup

1. TradingNode connects to venue
2. `LiveExecutionEngine` calls `generate_mass_status()` on each `ExecutionClient`
3. Engine compares venue state vs cached state
4. Discrepancies resolved (missing fills applied, status mismatches corrected)

### Configuration

```python
LiveExecEngineConfig(
    reconciliation=True,                    # enable reconciliation
    reconciliation_lookback_mins=1440,      # look back 24 hours
    reconciliation_instrument_ids=None,     # all instruments (or specify list)
    filtered_client_order_ids=[],           # exclude specific orders
)
```

### Timeouts

```python
TradingNodeConfig(
    timeout_connection=30.0,       # seconds to wait for venue connection
    timeout_reconciliation=10.0,   # seconds to wait for reconciliation
    timeout_portfolio=10.0,        # seconds to wait for portfolio init
    timeout_disconnection=10.0,    # seconds to wait for clean disconnect
    timeout_post_stop=5.0,         # seconds after stop for cleanup
)
```

## Multi-Venue Trading

Single TradingNode can connect to multiple venues simultaneously:

```python
config = TradingNodeConfig(
    data_clients={
        "BINANCE": BinanceDataClientConfig(...),
        "BYBIT": BybitDataClientConfig(...),
    },
    exec_clients={
        "BINANCE": BinanceExecClientConfig(...),
        "BYBIT": BybitExecClientConfig(...),
    },
)

node = TradingNode(config)
node.add_data_client_factory("BINANCE", BinanceLiveDataClientFactory)
node.add_exec_client_factory("BINANCE", BinanceLiveExecClientFactory)
node.add_data_client_factory("BYBIT", BybitLiveDataClientFactory)
node.add_exec_client_factory("BYBIT", BybitLiveExecClientFactory)
```

Strategies can subscribe to data from any venue and submit orders to any venue.

## Backtest → Live Transition

Zero code changes in strategy. Only configuration differs:

```python
# Backtest
engine = BacktestEngine(BacktestEngineConfig(trader_id="BACKTESTER-001"))
engine.add_venue(...)
engine.add_data(historical_deltas)
engine.add_strategy(MyStrategy(config))
engine.run()

# Live (same strategy, different node)
node = TradingNode(TradingNodeConfig(trader_id="LIVE-001", ...))
node.trader.add_strategy(MyStrategy(config))  # SAME config, SAME strategy
node.build()
node.run()
```

## Error Handling and Reconnection

### WebSocket Reconnection

Adapters implement automatic reconnection:

```python
# Databento example
DatabentoDataClientConfig(
    reconnect_timeout_mins=60,  # keep trying for 60 minutes
)

# dYdX example
DYDXExecClientConfig(
    max_retries=3,
    retry_delay_initial_ms=500,
    retry_delay_max_ms=5000,
)
```

### Reconnection strategy:
1. Detect disconnect (read error or ping timeout)
2. Exponential backoff: 1s → 2s → 4s → 8s → max 60s
3. Re-authenticate
4. Re-subscribe to all active subscriptions
5. For order books: request fresh snapshot to resync

### Strategy-Level Error Handling

```python
def on_order_rejected(self, event: OrderRejected) -> None:
    self.log.warning(f"Order rejected: {event.reason}")
    # Decide: retry, adjust, or halt

def on_order_cancel_rejected(self, event: OrderCancelRejected) -> None:
    self.log.error(f"Cancel rejected: {event.reason}")
    # May need to query order status

def on_order_modify_rejected(self, event: OrderModifyRejected) -> None:
    self.log.warning(f"Modify rejected: {event.reason}")
    # Cancel and re-submit instead
```

## Deployment

### Standalone Python Script (Recommended)

```python
# run_trading.py
import asyncio
from my_strategy import MyStrategy, MyConfig
from nautilus_trader.live.node import TradingNode

def main():
    config = TradingNodeConfig(...)
    node = TradingNode(config)
    # ... setup ...
    node.build()

    try:
        node.run()
    except KeyboardInterrupt:
        node.stop()

if __name__ == "__main__":
    main()
```

Run with: `python run_trading.py`

### Docker

```dockerfile
FROM python:3.12-slim

RUN pip install nautilus_trader

COPY strategies/ /app/strategies/
COPY config/ /app/config/
COPY run_trading.py /app/

WORKDIR /app
CMD ["python", "run_trading.py"]
```

### DO NOT use Jupyter notebooks for live trading:
- Event loop conflicts with notebook kernel
- No proper signal handling
- No process management
- Risk of accidental cell re-execution

## Logging

```python
LoggingConfig(
    log_level="INFO",       # DEBUG, INFO, WARNING, ERROR
    log_level_file="DEBUG", # file can be more verbose
    log_file_path="logs/",  # directory for log files
)
```

Logging is implemented in Rust for performance. Logs include:
- Component name
- Timestamp (nanosecond precision)
- Thread ID
- Structured key-value pairs

## Operational Checklist

- [ ] State persistence configured (Redis or PostgreSQL)?
- [ ] Reconciliation enabled with appropriate lookback?
- [ ] API keys in environment variables (not hardcoded)?
- [ ] Logging configured with file output?
- [ ] Timeouts set appropriately for venue latency?
- [ ] Running as standalone script (not notebook)?
- [ ] Signal handling for graceful shutdown?
- [ ] Monitoring/alerting on strategy state changes?
- [ ] Separate testnet validation before mainnet?
