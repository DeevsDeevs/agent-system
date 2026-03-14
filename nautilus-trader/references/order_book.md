# Order Book Processing

Order book management, delta processing, venue resync protocols, and own order tracking for crypto HFT on NautilusTrader.

## Book Types

| Type | Enum | Granularity | Crypto Available |
|------|------|------------|------------------|
| L1_MBP | `BookType.L1_MBP` | Top-of-book only | Yes — cheapest, sufficient for signals |
| L2_MBP | `BookType.L2_MBP` | Aggregated by price level | Yes — **the ceiling for crypto HFT** |
| L3_MBO | `BookType.L3_MBO` | Individual orders by order_id | **No** — not available on crypto venues |

**L3_MBO is not available on crypto exchanges.** L3 requires per-order-ID feeds only found on traditional exchanges (Databento MBO, ITCH). All crypto venues provide L2 at best. Do not configure `BookType.L3_MBO` for crypto strategies.

Quote, trade, and bar data automatically maintain L1_MBP books in Cache.

## Subscribing

```python
def on_start(self) -> None:
    # L2 incremental updates (most common for crypto HFT)
    self.subscribe_order_book_deltas(
        instrument_id=self.instrument_id,
        book_type=BookType.L2_MBP,
    )

    # Aggregated depth snapshots (top 10 levels, lower overhead)
    self.subscribe_order_book_depth(
        instrument_id=self.instrument_id,
        book_type=BookType.L2_MBP,
    )

    # Full book at intervals (reduced callback frequency)
    self.subscribe_order_book_at_interval(
        instrument_id=self.instrument_id,
        interval_ms=1000,
    )
```

### Handlers

```python
def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
    # Incremental L2 updates — fires at tick frequency
    pass

def on_order_book_depth(self, depth: OrderBookDepth10) -> None:
    # Pre-aggregated top 10 levels — lower latency than full book
    pass

def on_order_book(self, book: OrderBook) -> None:
    # Full book snapshot (from interval subscription)
    pass
```

## Delta Processing

### BookAction Types

| Action | Meaning | When |
|--------|---------|------|
| `BookAction.ADD` | New price level | Level appears in book |
| `BookAction.UPDATE` | Size changed at level | Existing level modified |
| `BookAction.DELETE` | Level removed | Size → 0 |
| `BookAction.CLEAR` | Entire book cleared | Connection reset, snapshot incoming |

### RecordFlag.F_LAST — Critical for Correctness

`F_LAST` tells the DataEngine "this is the last delta in the current batch — flush and publish."

**Rules:**
- Single delta (standalone update): **always** set `F_LAST`
- Batch of deltas: set `F_LAST` **only** on the last delta
- Without `F_LAST`: DataEngine buffers indefinitely → subscribers never receive data

```python
from nautilus_trader.model.data import BookOrder, OrderBookDelta  # BookOrder is in model.data, NOT model.book

# Single delta — always F_LAST
delta = OrderBookDelta(
    instrument_id=instrument_id,
    action=BookAction.UPDATE,
    order=BookOrder(OrderSide.BUY, price, qty, 0),  # positional: side, Price, size, order_id
    flags=RecordFlag.F_LAST,  # mandatory for standalone
    sequence=seq,
    ts_event=ts_event,
    ts_init=ts_init,
)

# Batch — F_LAST only on final
for i, update in enumerate(venue_updates):
    flags = RecordFlag.F_LAST if i == len(venue_updates) - 1 else 0
    delta = OrderBookDelta(..., flags=flags)
    self._handle_data(delta)
```

### Snapshot Processing

When receiving a full book snapshot (REST or WS snapshot message):

1. Send `CLEAR` action delta
2. Send all levels as `ADD` actions
3. Set `F_LAST` on the final level only

```python
def _process_snapshot(self, instrument_id, snapshot_data):
    deltas = []

    clear = OrderBookDelta(
        instrument_id=instrument_id,
        action=BookAction.CLEAR,
        order=None,
        flags=0,
        sequence=0,
        ts_event=ts_event,
        ts_init=self._clock.timestamp_ns(),
    )
    deltas.append(clear)

    all_levels = snapshot_data["bids"] + snapshot_data["asks"]
    for i, level in enumerate(all_levels):
        is_bid = i < len(snapshot_data["bids"])
        flags = RecordFlag.F_LAST if i == len(all_levels) - 1 else 0
        delta = OrderBookDelta(
            instrument_id=instrument_id,
            action=BookAction.ADD,
            order=BookOrder(
                side=OrderSide.BUY if is_bid else OrderSide.SELL,
                price=Price.from_str(level[0]),
                size=Quantity.from_str(level[1]),
                order_id=0,
            ),
            flags=flags,
            sequence=snapshot_data.get("lastUpdateId", 0),
            ts_event=millis_to_nanos(snapshot_data["timestamp"]),
            ts_init=self._clock.timestamp_ns(),
        )
        deltas.append(delta)

    for delta in deltas:
        self._handle_data(delta)
```

## Venue-Specific Resync Protocols

> **Note**: These protocols are handled internally by the NautilusTrader adapter — strategy developers do not need to implement them. This section is for understanding/debugging book synchronization issues, and for custom adapter development.

### Binance: lastUpdateId Protocol

Binance order book synchronization requires careful sequence handling:

1. Subscribe to WS diff depth stream (receives incremental updates with `U` first update ID and `u` final update ID)
2. Request REST snapshot — note `lastUpdateId`
3. Discard WS updates where `u <= lastUpdateId` (stale before snapshot)
4. First valid WS update must satisfy: `U <= lastUpdateId + 1 <= u`
5. Subsequent updates: `U_next == u_prev + 1` (no gaps)

```python
def _on_binance_book_update(self, msg: dict) -> None:
    first_id = msg["U"]
    final_id = msg["u"]

    if self._snapshot_id is None:
        self._buffer.append(msg)
        return

    if final_id <= self._snapshot_id:
        return  # stale, discard

    if self._first_update:
        if not (first_id <= self._snapshot_id + 1 <= final_id):
            self.log.warning("Snapshot/stream mismatch, requesting new snapshot")
            asyncio.ensure_future(self._resync_book())
            return
        self._first_update = False

    if first_id != self._last_final_id + 1:
        self.log.warning(f"Sequence gap: expected {self._last_final_id + 1}, got {first_id}")
        asyncio.ensure_future(self._resync_book())
        return

    self._last_final_id = final_id
    self._apply_update(msg)
```

### Bybit: crossSequence

Bybit uses `crossSequence` for ordering:

1. Each WS update contains `crossSequence`
2. Verify incoming `crossSequence > last_processed_crossSequence`
3. On gap → request snapshot via REST, resubscribe

### Generic Resync Protocol

```
detect gap → buffer incoming updates
  → request REST snapshot
  → apply snapshot (CLEAR + ADD)
  → replay buffered updates with sequence > snapshot
  → resume normal processing
```

## Accessing Book Data in Strategy

```python
def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
    book = self.cache.order_book(self.instrument_id)

    # Top of book
    best_bid = book.best_bid_price()    # Price
    best_ask = book.best_ask_price()    # Price
    bid_size = book.best_bid_size()     # Quantity
    ask_size = book.best_ask_size()     # Quantity
    spread = best_ask - best_bid
    mid = (best_bid + best_ask) / 2

    # Full depth
    bids = book.bids()  # list[BookLevel] sorted best→worst
    asks = book.asks()

    for level in bids[:5]:
        price = level.price
        size = level.size     # aggregate size at this level
        # level.count does NOT exist — use level.orders() for L3:
        # order_count = len(level.orders())  # L3 only — crypto typically L2

    # Book analysis
    bid_depth = sum(float(l.size) for l in bids[:10])
    ask_depth = sum(float(l.size) for l in asks[:10])
    imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)

    # Execution cost estimation
    avg_px = book.get_avg_px_for_quantity(Quantity.from_str("1.0"), OrderSide.BUY)
    worst_px = book.get_worst_px_for_quantity(Quantity.from_str("1.0"), OrderSide.BUY)
    # get_avg_px_qty_for_exposure() does NOT exist — compute manually:
    # notional / avg_px gives approximate quantity for target exposure

def on_order_book_depth(self, depth: OrderBookDepth10) -> None:
    # Pre-aggregated — lower latency than full book access
    for i in range(10):
        bid_price = depth.bids[i].price
        bid_size = depth.bids[i].size
        ask_price = depth.asks[i].price
        ask_size = depth.asks[i].size
```

## Own Order Book

Tracks YOUR active orders by price level, separate from the venue order book.

### Use Cases

- **Self-trade prevention**: Know where your orders sit before placing new ones
- **Queue position estimation**: Track position in queue at each level
- **Net liquidity**: Subtract own orders from public book to see true available liquidity
- **Reconciliation**: Compare own book state vs venue reports

```python
def on_start(self) -> None:
    own_book = self.cache.own_order_book(self.instrument_id)

def check_before_submit(self, price: Price, side: OrderSide) -> bool:
    own_book = self.cache.own_order_book(self.instrument_id)
    levels = own_book.bids() if side == OrderSide.BUY else own_book.asks()
    for level in levels:
        if level.price == price:
            return False  # already have order at this price
    return True
```

### Filtered Views

Remove your orders from the public book to reveal net liquidity.
**NOTE**: `book.filtered_view()` does NOT exist in v1.224.0 — implement manually:

```python
# Manual filtered view: subtract own orders from public book
own_book = self.cache.own_order_book(self.instrument_id)
book = self.cache.order_book(self.instrument_id)

# Get public book levels and subtract own order sizes
for level in book.bids():
    own_levels = own_book.bids()
    own_at_price = sum(float(ol.size) for ol in own_levels if ol.price == level.price)
    net_size = float(level.size) - own_at_price
```

### Safe Cancel Pattern

```python
open_orders = [
    o for o in self.cache.orders_open(instrument_id=self.instrument_id)
    if o.status != OrderStatus.PENDING_CANCEL
]
for order in open_orders:
    self.cancel_order(order)
```

The `accepted_buffer_ns` parameter filters inflight orders using timestamp guards — prevents operating on orders not yet confirmed by venue.

## Managed Books

When subscribing with `managed=True` (default), the DataEngine:
1. Creates and maintains `OrderBook` instances in Cache
2. Applies deltas automatically as they arrive
3. Optionally provides periodic snapshots via timers

Access managed books: `book = self.cache.order_book(instrument_id)`

## Performance

- Order books are implemented in **Rust** — all operations (apply_delta, best_bid, etc.) execute as native code
- Use **L2 over L3** for crypto — less data, sufficient for all crypto HFT strategies
- **OrderBookDepth10** for signal generation — pre-aggregated, lower overhead than full book traversal
- **Cache instrument reference** in `on_start()` — avoid repeated lookups in hot path
- Keep `on_order_book_deltas` minimal — fires at tick frequency
- Always validate **sequence numbers** to detect gaps early

## Anti-Hallucination Notes

| Hallucination | Reality |
|--------------|---------|
| `BookType.L3_MBO` for crypto | Not available on crypto exchanges — L3 requires per-order-ID feeds (traditional exchanges only) |
| `book.filtered_view()` | Does NOT exist — implement manually by subtracting `own_order_book()` from public book |
| `level.count` / `book.count` | `book.update_count` for update count. `level.orders()` for L3 order list |
| `get_avg_px_qty_for_exposure()` | Does NOT exist — compute manually: `notional / get_avg_px_for_quantity()` |
| Omitting `F_LAST` flag on deltas | DataEngine buffers indefinitely — subscribers never receive data |
| `book.best_bid_price()` returns float | Returns `Price` object — cast with `float(book.best_bid_price())` |
| `from nautilus_trader.model.book import BookOrder` | `from nautilus_trader.model.data import BookOrder` — BookOrder is in `model.data` |
| `BookOrder(price=, size=, side=)` kwargs | Positional only: `BookOrder(OrderSide, Price, Quantity, order_id)` |

## Rust

| Concern | Python | Rust |
|---|---|---|
| Subscribe method | `subscribe_order_book_deltas(instrument_id=..., book_type=...)` | `subscribe_book_deltas(id, book_type, NonZeroUsize::new(10), None, false, None)` |
| Callback name | `on_order_book_deltas(deltas)` | `on_book_deltas(deltas: &OrderBookDeltas)` — plural **batch** |
| Depth type | `Optional[int]` | `Option<NonZeroUsize>` — use `NonZeroUsize::new(n)` |
| `managed` flag | `managed=True` (default, kwarg) | `managed: bool` (positional, no default) |

### L2 Subscriptions

```rust
use std::num::NonZeroUsize;
use nautilus_model::{
    data::{OrderBookDelta, OrderBookDeltas},
    enums::BookType,
};

// In on_start:
self.subscribe_book_deltas(
    self.instrument_id,
    BookType::L2_MBP,
    NonZeroUsize::new(10), // depth: top-10 levels; None = full book
    None,                  // client_id
    false,                 // managed: false = raw deltas, true = engine-managed book
    None,                  // params
);

// Callback — receives a batch per exchange message (snapshot or incremental):
fn on_book_deltas(&mut self, deltas: &OrderBookDeltas) -> Result<()> {
    self.collected.lock().unwrap().extend_from_slice(&deltas.deltas);
    Ok(())
}
```

`OrderBookDelta` is `Copy` — `extend_from_slice` works directly from `deltas.deltas: Vec<OrderBookDelta>`.

### Writing Deltas to Parquet

`write_to_parquet` accepts `Vec<OrderBookDelta>` (individual items), not `Vec<OrderBookDeltas>` (batch containers):

```rust
catalog.write_to_parquet(deltas_vec, None, None, None)?;
// → {catalog_path}/order_book_delta/{instrument_id}/{ts_start}-{ts_end}.parquet
```

## Related Examples

- [market_maker_backtest.py](../examples/market_maker_backtest.py) — L2 market maker with skew
- [market_maker_backtest.rs](../examples/market_maker_backtest.rs) — Rust market maker with modify_order

See also: [market_making.md](market_making.md) for spread calculation, inventory management, and venue support.
