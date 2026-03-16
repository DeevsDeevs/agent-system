# Order Book Processing

## Book Types

| Type | Enum | Granularity |
|------|------|------------|
| L1_MBP | `BookType.L1_MBP` | Top-of-book only |
| L2_MBP | `BookType.L2_MBP` | Aggregated by price level — **the ceiling for crypto** |
| L3_MBO | `BookType.L3_MBO` | Individual orders — **not available on crypto venues** |

Quote, trade, and bar data automatically maintain L1_MBP books in Cache.

## Subscribing

```python
def on_start(self) -> None:
    self.subscribe_order_book_deltas(instrument_id=self.instrument_id, book_type=BookType.L2_MBP)
    self.subscribe_order_book_depth(instrument_id=self.instrument_id, book_type=BookType.L2_MBP)
    self.subscribe_order_book_at_interval(instrument_id=self.instrument_id, interval_ms=1000)
```

Handlers:
```python
def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None: ...  # Incremental L2
def on_order_book_depth(self, depth: OrderBookDepth10) -> None: ...   # Top 10 levels
def on_order_book(self, book: OrderBook) -> None: ...                 # Interval snapshot
```

## Delta Processing

### BookAction Types

| Action | Meaning |
|--------|---------|
| `BookAction.ADD` | New price level |
| `BookAction.UPDATE` | Size changed at level |
| `BookAction.DELETE` | Level removed (size = 0) |
| `BookAction.CLEAR` | Entire book cleared (reset/snapshot incoming) |

### RecordFlag.F_LAST

`F_LAST` tells the DataEngine "last delta in batch — flush and publish." Without it, DataEngine buffers indefinitely. Single delta: **always** set `F_LAST`. Batch: set `F_LAST` **only** on the last delta.

```python
from nautilus_trader.model.data import BookOrder, OrderBookDelta  # BookOrder is in model.data, NOT model.book

delta = OrderBookDelta(
    instrument_id=instrument_id,
    action=BookAction.UPDATE,
    order=BookOrder(OrderSide.BUY, price, qty, 0),  # positional: side, Price, size, order_id
    flags=RecordFlag.F_LAST,
    sequence=seq, ts_event=ts_event, ts_init=ts_init,
)

# Batch — F_LAST only on final
for i, update in enumerate(venue_updates):
    flags = RecordFlag.F_LAST if i == len(venue_updates) - 1 else 0
    delta = OrderBookDelta(..., flags=flags)
    self._handle_data(delta)
```

### Snapshot Processing

CLEAR then ADD all levels, `F_LAST` on final level only.

```python
def _process_snapshot(self, instrument_id, snapshot_data):
    deltas = []
    deltas.append(OrderBookDelta(
        instrument_id=instrument_id, action=BookAction.CLEAR,
        order=None, flags=0, sequence=0,
        ts_event=ts_event, ts_init=self._clock.timestamp_ns(),
    ))
    all_levels = snapshot_data["bids"] + snapshot_data["asks"]
    for i, level in enumerate(all_levels):
        is_bid = i < len(snapshot_data["bids"])
        deltas.append(OrderBookDelta(
            instrument_id=instrument_id, action=BookAction.ADD,
            order=BookOrder(
                side=OrderSide.BUY if is_bid else OrderSide.SELL,
                price=Price.from_str(level[0]),
                size=Quantity.from_str(level[1]),
                order_id=0,
            ),
            flags=RecordFlag.F_LAST if i == len(all_levels) - 1 else 0,
            sequence=snapshot_data.get("lastUpdateId", 0),
            ts_event=millis_to_nanos(snapshot_data["timestamp"]),
            ts_init=self._clock.timestamp_ns(),
        ))
    for delta in deltas:
        self._handle_data(delta)
```

## Venue Resync Protocols

> For debugging book sync and custom adapter development.

### Binance: lastUpdateId

1. Subscribe WS diff depth (`U` = first ID, `u` = final ID)
2. REST snapshot, note `lastUpdateId`
3. Discard WS where `u <= lastUpdateId`
4. First valid: `U <= lastUpdateId + 1 <= u`
5. Subsequent: `U_next == u_prev + 1` (no gaps)

```python
def _on_binance_book_update(self, msg: dict) -> None:
    first_id, final_id = msg["U"], msg["u"]
    if self._snapshot_id is None:
        self._buffer.append(msg); return
    if final_id <= self._snapshot_id:
        return
    if self._first_update:
        if not (first_id <= self._snapshot_id + 1 <= final_id):
            asyncio.ensure_future(self._resync_book()); return
        self._first_update = False
    if first_id != self._last_final_id + 1:
        asyncio.ensure_future(self._resync_book()); return
    self._last_final_id = final_id
    self._apply_update(msg)
```

### Bybit: crossSequence

Verify `crossSequence > last_processed`. On gap: REST snapshot, resubscribe.

### Generic Resync

```
detect gap → buffer → REST snapshot → CLEAR + ADD → replay buffered (seq > snapshot) → resume
```

## Accessing Book Data

```python
def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
    book = self.cache.order_book(self.instrument_id)
    best_bid = book.best_bid_price()    # returns Price, not float
    best_ask = book.best_ask_price()
    bid_size = book.best_bid_size()     # Quantity
    ask_size = book.best_ask_size()
    spread = best_ask - best_bid
    mid = (best_bid + best_ask) / 2

    bids = book.bids()  # list[BookLevel] sorted best→worst
    asks = book.asks()
    for level in bids[:5]:
        price = level.price
        size = level.size
        # level.count does NOT exist — use level.orders() for L3 only

    bid_depth = sum(float(l.size) for l in bids[:10])
    ask_depth = sum(float(l.size) for l in asks[:10])
    imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)

    avg_px = book.get_avg_px_for_quantity(Quantity.from_str("1.0"), OrderSide.BUY)
    worst_px = book.get_worst_px_for_quantity(Quantity.from_str("1.0"), OrderSide.BUY)
    # get_avg_px_qty_for_exposure() does NOT exist — use notional / avg_px

def on_order_book_depth(self, depth: OrderBookDepth10) -> None:
    for i in range(10):
        bid_price, bid_size = depth.bids[i].price, depth.bids[i].size
        ask_price, ask_size = depth.asks[i].price, depth.asks[i].size
```

## Own Order Book

Tracks active orders by price level for self-trade prevention, queue position, net liquidity, reconciliation.

```python
own_book = self.cache.own_order_book(self.instrument_id)

def check_before_submit(self, price: Price, side: OrderSide) -> bool:
    own_book = self.cache.own_order_book(self.instrument_id)
    levels = own_book.bids() if side == OrderSide.BUY else own_book.asks()
    return not any(level.price == price for level in levels)
```

`book.filtered_view()` does NOT exist — subtract own orders manually:

```python
own_book = self.cache.own_order_book(self.instrument_id)
book = self.cache.order_book(self.instrument_id)
for level in book.bids():
    own_at_price = sum(float(ol.size) for ol in own_book.bids() if ol.price == level.price)
    net_size = float(level.size) - own_at_price
```

### Safe Cancel

```python
open_orders = [
    o for o in self.cache.orders_open(instrument_id=self.instrument_id)
    if o.status != OrderStatus.PENDING_CANCEL
]
for order in open_orders:
    self.cancel_order(order)
```

`accepted_buffer_ns` filters inflight orders not yet confirmed by venue.

## Managed Books

`managed=True` (default): DataEngine creates/maintains `OrderBook` in Cache, applies deltas automatically. Access: `book = self.cache.order_book(instrument_id)`

## Performance

Use L2 for crypto. `OrderBookDepth10` for signals (pre-aggregated, lower overhead). Cache instrument in `on_start()`. Keep `on_order_book_deltas` minimal — fires at tick frequency.

> See SKILL.md for common hallucination guards.

## Rust

| Concern | Python | Rust |
|---|---|---|
| Subscribe | `subscribe_order_book_deltas(instrument_id=..., book_type=...)` | `subscribe_book_deltas(id, book_type, NonZeroUsize::new(10), None, false, None)` |
| Callback | `on_order_book_deltas(deltas)` | `on_book_deltas(deltas: &OrderBookDeltas)` |
| Depth type | `Optional[int]` | `Option<NonZeroUsize>` |
| `managed` | `managed=True` (default, kwarg) | `managed: bool` (positional, no default) |

```rust
use std::num::NonZeroUsize;
use nautilus_model::{data::{OrderBookDelta, OrderBookDeltas}, enums::BookType};

self.subscribe_book_deltas(
    self.instrument_id, BookType::L2_MBP,
    NonZeroUsize::new(10), None, false, None,
);

fn on_book_deltas(&mut self, deltas: &OrderBookDeltas) -> Result<()> {
    self.collected.lock().unwrap().extend_from_slice(&deltas.deltas);
    Ok(())
}
```

`OrderBookDelta` is `Copy` — `extend_from_slice` works directly from `deltas.deltas: Vec<OrderBookDelta>`.

### Writing Deltas to Parquet

`write_to_parquet` accepts `Vec<OrderBookDelta>`, not `Vec<OrderBookDeltas>`:

```rust
catalog.write_to_parquet(deltas_vec, None, None, None)?;
```

## Related

- [market_maker_backtest.py](../examples/market_maker_backtest.py) — L2 market maker with skew
- [market_maker_backtest.rs](../examples/market_maker_backtest.rs) — Rust market maker with modify_order
- [market_making.md](market_making.md) — spread calculation, inventory management