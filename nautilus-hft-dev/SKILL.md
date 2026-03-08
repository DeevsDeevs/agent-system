---
name: nautilus-hft-dev
description: >
  Use when developing custom NautilusTrader adapters, exchange integrations, or
  HFT systems. Triggers: "nautilus adapter development", "LiveDataClient implementation",
  "LiveExecutionClient implementation", "Rust adapter", "PyO3 bindings nautilus",
  "nautilus crate", "InstrumentProvider", "WebSocketClient nautilus",
  "HttpClient nautilus", "nautilus FFI", "CVec nautilus", "maturin nautilus",
  "cargo-nextest nautilus", "nautilus order book delta processing",
  "RecordFlag F_LAST", "OrderBookDelta parsing", "nautilus OMS internals",
  "ExecutionEngine internals", "DataEngine internals", "nautilus reconciliation",
  "overfill handling", "nautilus build system", "nautilus testing",
  "custom adapter crypto", "Binance adapter internals", "Bybit adapter internals",
  "dYdX adapter", "Tardis adapter", "Databento adapter", "OKX adapter",
  "exchange adapter factory", "DataClientFactory", "ExecClientFactory",
  "nautilus development environment", "nautilus Cython PyO3 migration",
  "HFT order book strategy nautilus", "tick-level processing nautilus",
  "own order book", "L2 L3 order book nautilus", "book_snapshot deltas",
  "generate_order_status_report", "generate_fill_reports", "ExecutionMassStatus",
  "CacheDatabaseAdapter", "Redis nautilus", "PostgreSQL nautilus".
---

# NautilusTrader HFT Development

Development-focused skill for building custom adapters, exchange integrations, and HFT systems on NautilusTrader. Covers Rust + Python adapter engineering, OMS internals, order book processing, and the full development toolchain.

## Architecture: Hybrid Rust/Python

```
┌─────────────────────────────────────────────────────────────┐
│  Python Layer (Strategy/Config/Orchestration)               │
│  nautilus_trader/adapters/your_exchange/                    │
│    ├── config.py          # Pydantic configs                │
│    ├── factories.py       # DataClientFactory, ExecFactory  │
│    ├── data.py            # LiveMarketDataClient subclass   │
│    ├── execution.py       # LiveExecutionClient subclass    │
│    └── providers.py       # InstrumentProvider              │
├─────────────────────────────────────────────────────────────┤
│  PyO3 Bridge (maturin → _libnautilus.so)                   │
├─────────────────────────────────────────────────────────────┤
│  Rust Core (Performance-Critical)                           │
│  crates/adapters/your_exchange/                            │
│    ├── src/               # HTTP, WebSocket, parsing        │
│    │   ├── http/          # REST client, request signing    │
│    │   ├── websocket/     # WS client, reconnection        │
│    │   ├── parsing/       # Venue → Nautilus type mapping   │
│    │   └── python/        # PyO3 exports                   │
│    └── Cargo.toml                                          │
└─────────────────────────────────────────────────────────────┘
```

**Build pipeline**: `cargo build` → `maturin develop` → single `_libnautilus.so` shared lib. Use `make install-debug` for fast dev iteration.

## Adapter Development Quick Start

### Phase 1: Python-Only Adapter (Fast Prototyping)

Subclass `LiveMarketDataClient` and `LiveExecutionClient`:

```python
from nautilus_trader.live.data_client import LiveMarketDataClient
from nautilus_trader.live.execution_client import LiveExecutionClient
from nautilus_trader.data.messages import SubscribeOrderBook, SubscribeTradeTicks
from nautilus_trader.execution.messages import SubmitOrder, CancelOrder, ModifyOrder

class MyExchangeDataClient(LiveMarketDataClient):
    async def _connect(self) -> None:
        # Open WebSocket, authenticate, restore subscriptions
        pass

    async def _disconnect(self) -> None:
        # Close connections gracefully
        pass

    async def _subscribe_order_book_deltas(self, command: SubscribeOrderBook) -> None:
        # Translate to venue WS subscription, set managed=True for DataEngine book mgmt
        pass

    async def _subscribe_trade_ticks(self, command: SubscribeTradeTicks) -> None:
        # Subscribe to venue trade stream
        pass

class MyExchangeExecClient(LiveExecutionClient):
    async def _connect(self) -> None:
        # Open execution WS/REST, authenticate
        pass

    async def _submit_order(self, command: SubmitOrder) -> None:
        # Translate Nautilus order → venue API call
        # On response: self.generate_order_accepted / self.generate_order_rejected
        pass

    async def _cancel_order(self, command: CancelOrder) -> None:
        # Send cancel to venue
        # On response: self.generate_order_canceled
        pass

    async def _modify_order(self, command: ModifyOrder) -> None:
        # Send amend to venue
        # On response: self.generate_order_updated
        pass
```

### Phase 2: Rust Core (Production Performance)

Build Rust crate in `crates/adapters/your_exchange/`:

```rust
// src/http/client.rs - REST API client
pub struct MyExchangeHttpClient {
    client: HttpClient,
    base_url: String,
    api_key: String,
    api_secret: String,
}

impl MyExchangeHttpClient {
    pub async fn get_instruments(&self) -> Result<Vec<InstrumentResponse>> { ... }
    pub async fn submit_order(&self, req: &OrderRequest) -> Result<OrderResponse> { ... }
    pub async fn cancel_order(&self, order_id: &str) -> Result<()> { ... }
}

// src/python/mod.rs - PyO3 exports
#[pyclass]
pub struct MyExchangeHttpClientPy(Arc<MyExchangeHttpClient>);

#[pymethods]
impl MyExchangeHttpClientPy {
    #[pyo3(name = "get_instruments")]
    fn py_get_instruments<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let client = self.0.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let instruments = client.get_instruments().await?;
            // Convert to Python objects
            Ok(instruments)
        })
    }
}
```

### Factory Registration

```python
from nautilus_trader.live.factories import LiveDataClientFactory, LiveExecClientFactory

class MyExchangeDataFactory(LiveDataClientFactory):
    @staticmethod
    def create(loop, name, config, msgbus, cache, clock):
        return MyExchangeDataClient(
            loop=loop, client_id=ClientId(name), venue=Venue(name),
            msgbus=msgbus, cache=cache, clock=clock, config=config,
        )

# Register with TradingNode
node.add_data_client_factory("MYEXCHANGE", MyExchangeDataFactory)
node.add_exec_client_factory("MYEXCHANGE", MyExchangeExecFactory)
node.build()
```

## Order Book Delta Processing (HFT Critical)

### Delta Format and RecordFlag

```python
from nautilus_trader.model.data import OrderBookDelta, OrderBookDeltas
from nautilus_trader.model.enums import BookAction, RecordFlag

# Single delta (always set F_LAST when it's the last/only delta in a batch)
delta = OrderBookDelta(
    instrument_id=instrument_id,
    action=BookAction.UPDATE,  # ADD, UPDATE, DELETE, CLEAR
    order=BookOrder(price=Price.from_str("50000.00"), size=Quantity.from_str("1.5"), side=OrderSide.BUY),
    flags=RecordFlag.F_LAST,   # CRITICAL: signals DataEngine to flush and publish
    sequence=42,
    ts_event=ts_event,         # nanoseconds UNIX - when exchange generated
    ts_init=ts_init,           # nanoseconds UNIX - when Nautilus received
)

# Batch deltas (only last delta gets F_LAST)
deltas = []
for i, update in enumerate(venue_updates):
    flags = RecordFlag.F_LAST if i == len(venue_updates) - 1 else 0
    deltas.append(OrderBookDelta(..., flags=flags))
```

### Book Types

| Type | Granularity | Use Case |
|------|------------|----------|
| `L3_MBO` | Individual orders by order_id | Queue position tracking, HFT |
| `L2_MBP` | Aggregated by price level | Spread capture, mid-frequency |
| `L1_MBP` | Top-of-book only | Signal generation, latency-sensitive |

### Strategy: Accessing Order Book

```python
def on_start(self) -> None:
    self.subscribe_order_book_deltas(self.instrument_id, book_type=BookType.L2_MBP)

def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
    book = self.cache.order_book(self.instrument_id)
    best_bid = book.best_bid_price()
    best_ask = book.best_ask_price()
    spread = best_ask - best_bid
    mid = (best_bid + best_ask) / 2

    # Full depth access
    bids = book.bids()  # list of BookLevel
    asks = book.asks()  # list of BookLevel
```

## OMS Internals

### Execution Flow

```
Strategy.submit_order(order)
    → OrderEmulator (if emulation_trigger set, holds order locally)
    → ExecAlgorithm (if exec_algorithm_id set, e.g. TWAP splits)
    → RiskEngine (validates price/qty precision, max notional, reduce_only)
        → DENIED if fails → OrderDenied event
    → ExecutionEngine (routes to correct ExecutionClient by venue)
    → ExecutionClient._submit_order(command)
        → Venue API call
        → On ACK: generate_order_accepted()
        → On FILL: generate_order_filled()
        → On REJECT: generate_order_rejected()
```

### OMS Types

- **NETTING**: One position per instrument. Fills aggregate. Opposite fills reduce/flip. Standard for crypto perps.
- **HEDGING**: Multiple positions per instrument. Each tracked independently. Used when strategy needs isolated P&L tracking.

Strategy `oms_type` can differ from venue `oms_type`. ExecutionEngine reconciles by overriding `position_id` on fill events.

### Execution Client: Generating Events

```python
# After venue acknowledges order
self.generate_order_accepted(
    strategy_id=strategy_id,
    instrument_id=instrument_id,
    client_order_id=client_order_id,
    venue_order_id=VenueOrderId(venue_response["orderId"]),
    ts_event=ts_event,
)

# After venue reports fill
self.generate_order_filled(
    strategy_id=strategy_id,
    instrument_id=instrument_id,
    client_order_id=client_order_id,
    venue_order_id=venue_order_id,
    venue_position_id=None,  # venue-assigned position ID (optional)
    trade_id=TradeId(venue_response["tradeId"]),
    order_side=order_side,
    order_type=order_type,
    last_qty=Quantity.from_str(venue_response["qty"]),
    last_px=Price.from_str(venue_response["price"]),
    quote_currency=currency,
    commission=Money.from_str(f"{venue_response['commission']} {currency}"),
    liquidity_side=LiquiditySide.MAKER,  # or TAKER
    ts_event=ts_event,
)
```

### Reconciliation on Startup

```python
# LiveExecutionClient must implement these for state recovery:
async def generate_order_status_report(self, command) -> OrderStatusReport | None:
    # Query venue for single order status
    pass

async def generate_order_status_reports(self, command) -> list[OrderStatusReport]:
    # Query venue for all open orders
    pass

async def generate_fill_reports(self, command) -> list[FillReport]:
    # Query venue for recent fills
    pass

async def generate_position_status_reports(self, command) -> list[PositionStatusReport]:
    # Query venue for open positions
    pass

async def generate_mass_status(self, lookback_mins=None) -> ExecutionMassStatus | None:
    # Combined status report for all orders/positions/fills
    pass
```

Config: `LiveExecEngineConfig(reconciliation=True, reconciliation_lookback_mins=1440)`

### Overfill Handling

Overfills happen in crypto due to race conditions, WS replays, DEX mechanics. Config:

```python
LiveExecEngineConfig(allow_overfills=True)  # default: False
```

Duplicate detection: `is_duplicate_fill()` checks `trade_id + side + price + qty`. Duplicates logged and skipped.

## Own Order Book

Tracks YOUR orders by price level (separate from venue book). For HFT queue-position strategies.

```python
# Access in strategy
own_book = self.cache.own_order_book(self.instrument_id)
# Use accepted_buffer_ns to filter inflight orders
# Exclude PENDING_CANCEL to avoid duplicate cancel attempts
```

## Anti-Patterns

```python
# BAD: Not setting RecordFlag.F_LAST on last delta in batch
# Result: DataEngine never publishes the batch, subscribers starve

# BAD: Using float for price/quantity construction
Price(1.23456)  # WRONG - precision errors
Price.from_str("1.23456")  # CORRECT

# BAD: Blocking event loop in adapter callbacks
async def _subscribe_order_book_deltas(self, command):
    time.sleep(1)  # blocks entire kernel

# BAD: Not implementing reconciliation methods
# Result: state drift between Nautilus and venue after restart

# BAD: Ignoring ts_event vs ts_init distinction
# ts_event = exchange timestamp, ts_init = local receipt time
# Latency = ts_init - ts_event

# BAD: Forgetting CVec drop helper in FFI code
# Result: memory leak or double-free crash
```

## Development Environment Setup

```bash
# 1. Install prerequisites
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
curl -LsSf https://astral.sh/uv/install.sh | sh
sudo apt-get install clang  # Linux only

# 2. Clone and install
git clone --branch develop --depth 1 https://github.com/nautechsystems/nautilus_trader
cd nautilus_trader
uv sync --active --all-groups --all-extras  # or: make install
make install-debug  # faster builds for development

# 3. Set PyO3 env vars (Linux/macOS)
export LD_LIBRARY_PATH=$(python -c "import sysconfig; print(sysconfig.get_config_var('LIBDIR'))")
export PYO3_PYTHON=$(which python)

# 4. Pre-commit hooks
pre-commit install

# 5. Run tests
make cargo-test     # Rust tests via cargo-nextest
pytest              # Python tests
```

## Performance Checklist

- [ ] Rust core for HTTP/WS clients? (parsing, signing, reconnection)
- [ ] RecordFlag.F_LAST set on final delta in every batch?
- [ ] Using `instrument.make_price()` / `make_qty()` for precision?
- [ ] Reconciliation methods implemented for all execution clients?
- [ ] ts_event populated from exchange timestamps (not local clock)?
- [ ] WebSocket reconnection with backoff implemented?
- [ ] Rate limiting on REST endpoints?
- [ ] Duplicate fill detection enabled?
- [ ] State persistence configured (Redis/PostgreSQL) for production?
- [ ] Using `make install-debug` during development?

## Reference Navigator

| Topic | File | When to Load |
|-------|------|--------------|
| Python Adapter Templates | [python_adapters.md](references/python_adapters.md) | Building LiveDataClient / LiveExecutionClient |
| Rust Adapter Guide | [rust_adapters.md](references/rust_adapters.md) | Rust crate structure, PyO3 exports, HTTP/WS clients |
| OMS Internals | [oms_internals.md](references/oms_internals.md) | ExecutionEngine, RiskEngine, order state machine, reconciliation |
| Order Book HFT | [order_book_hft.md](references/order_book_hft.md) | L2/L3 books, delta processing, own order book, queue position |
| Exchange Adapters | [exchange_adapters.md](references/exchange_adapters.md) | Binance, Bybit, dYdX, OKX, Tardis, Databento specifics |
| Dev Environment | [dev_environment.md](references/dev_environment.md) | Build system, testing, CI/CD, FFI memory contract |
| Live Trading Ops | [live_ops.md](references/live_ops.md) | TradingNode config, persistence, Docker, reconnection |

## Existing Adapter Examples

| Example | File | Purpose |
|---------|------|---------|
| Custom Data Adapter | [examples/custom_data_adapter.py](examples/custom_data_adapter.py) | Full LiveMarketDataClient for crypto exchange |
| Custom Exec Adapter | [examples/custom_exec_adapter.py](examples/custom_exec_adapter.py) | Full LiveExecutionClient with fill generation |
