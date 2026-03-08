# Order Book

## Book Types

| Type | Description | Key |
|------|-------------|-----|
| `L3_MBO` | Market by order | Individual orders, keyed by order ID |
| `L2_MBP` | Market by price | Aggregated per price level |
| `L1_MBP` | Top-of-book | Best bid/ask only |

Quote, trade, and bar data maintain L1_MBP books automatically.

## Subscribing

```python
def on_start(self):
    # L2/L3 incremental updates
    self.subscribe_order_book_deltas(instrument_id)

    # Aggregated depth snapshots
    self.subscribe_order_book_depth(instrument_id)

    # Full book at intervals
    self.subscribe_order_book_at_interval(instrument_id, interval_ms=1000)
```

### Handlers

```python
def on_order_book_deltas(self, deltas) -> None:
    # Incremental updates
    pass

def on_order_book_depth(self, depth) -> None:
    # OrderBookDepth10 snapshot
    pass

def on_order_book(self, book) -> None:
    # Full OrderBook snapshot (from interval subscription)
    pass
```

## Core Operations

```python
book = self.cache.order_book(instrument_id)

# Top-of-book
book.best_bid_price()
book.best_ask_price()
book.spread()
book.midpoint()

# Analysis
book.get_avg_px_for_quantity(OrderSide.BUY, quantity)
book.get_avg_px_qty_for_exposure(OrderSide.BUY, notional)
book.get_quantity_for_price(OrderSide.BUY, price)

# Simulation
book.simulate_fills(order)
```

## Integrity Rules

| Book Type | Constraint |
|-----------|------------|
| `L1_MBP` | Maximum one level per side |
| `L2_MBP` | One order per price level |
| `L3_MBO` | No structural constraints |
| All | Best bid cannot exceed best ask (locked markets permitted) |

## OwnOrderBook

Tracks your personal orders through their lifecycle (SUBMITTED → ACCEPTED → FILLED). Separate from the public order book.

### Use Cases

- **Auditing**: Reconcile against known open order IDs
- **Filtering**: Subtract own orders from public book → net liquidity
- **Self-trade prevention**: Know where your orders sit
- **Queue position**: Track position in queue at each level

### Filtered Views

```python
# Create net liquidity view by removing your orders
filtered = book.filtered_view(
    own_book=own_book,
    level_limit=10,
    status=status_filter,
    buffer=accepted_buffer_ns,
    timestamp=current_ts,
)

# Full analysis on filtered book
filtered.best_bid_price()
filtered.get_avg_px_for_quantity(OrderSide.BUY, quantity)
```

### Status Filtering

Include/exclude orders by status. Use `accepted_buffer_ns` as a grace period for recently accepted orders to avoid premature filtering.

## Binary/Prediction Markets

For YES/NO pairs, combine complementary sides:

```python
# Combine YES and NO own order books
combined = yes_own.combined_with_opposite(no_own)

# NO-side prices convert via: 1 - price
filtered = book.filtered_view(combined, ...)
```

## OrderBookDelta

Granular update messages with `RecordFlag` bitmask:

- `F_LAST` — final delta in a logical event group (apply book state after this)
- `F_SNAPSHOT` — delta belongs to a snapshot sequence

Always process deltas in order. Apply book state changes after receiving `F_LAST` flag.

## Performance Considerations

- Order books are implemented in Rust for maximum throughput
- L3 books are most expensive to maintain but provide best simulation fidelity
- L1 books are cheapest and sufficient for many strategies
- Use `subscribe_order_book_at_interval` for reduced callback frequency when full tick-by-tick isn't needed
