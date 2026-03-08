# Order Book Processing for HFT

Deep dive into NautilusTrader's order book system: L2/L3 books, delta processing, own order tracking, and HFT strategy patterns.

## Order Book Types

| Type | Enum | Granularity | Key Feature |
|------|------|------------|-------------|
| L1_MBP | `BookType.L1_MBP` | Top-of-book only | Fastest, minimal memory |
| L2_MBP | `BookType.L2_MBP` | Aggregated by price level | Standard for most HFT |
| L3_MBO | `BookType.L3_MBO` | Individual orders by order_id | Queue position tracking |

## Subscribing in Strategy

```python
def on_start(self) -> None:
    # L2 order book (most common for crypto)
    self.subscribe_order_book_deltas(
        instrument_id=self.instrument_id,
        book_type=BookType.L2_MBP,
    )

    # L3 order book (if venue supports MBO data)
    self.subscribe_order_book_deltas(
        instrument_id=self.instrument_id,
        book_type=BookType.L3_MBO,
    )

    # Aggregated depth snapshots (top 10 levels)
    self.subscribe_order_book_depth(
        instrument_id=self.instrument_id,
        book_type=BookType.L2_MBP,
    )
```

## Delta Processing

### BookAction Types

| Action | Meaning | When |
|--------|---------|------|
| `BookAction.ADD` | New order/level added | New price level appears |
| `BookAction.UPDATE` | Existing order/level modified | Size changed at price level |
| `BookAction.DELETE` | Order/level removed | Level emptied (size → 0) |
| `BookAction.CLEAR` | Entire book cleared | Connection reset, snapshot incoming |

### RecordFlag.F_LAST — Critical for Correctness

The `F_LAST` flag tells the DataEngine "this is the last delta in the current batch — flush and publish."

**Rules:**
- Single delta (standalone update): ALWAYS set `F_LAST`
- Batch of deltas: Set `F_LAST` ONLY on the last delta
- Without `F_LAST`: DataEngine buffers indefinitely → subscribers never receive data

```python
# CORRECT: Single delta
delta = OrderBookDelta(
    instrument_id=instrument_id,
    action=BookAction.UPDATE,
    order=BookOrder(price=price, size=qty, side=OrderSide.BUY),
    flags=RecordFlag.F_LAST,  # mandatory for standalone
    sequence=seq,
    ts_event=ts_event,
    ts_init=ts_init,
)

# CORRECT: Batch of deltas
for i, update in enumerate(venue_updates):
    flags = RecordFlag.F_LAST if i == len(venue_updates) - 1 else 0
    delta = OrderBookDelta(..., flags=flags)
    self._handle_data(delta)

# WRONG: Never setting F_LAST
# DataEngine never publishes, strategy never receives on_order_book_deltas
```

### Snapshot vs Incremental Updates

**Snapshots** (full book state):
1. Receive from REST API or WS snapshot message
2. First send `CLEAR` action delta
3. Then send all levels as `ADD` actions
4. Set `F_LAST` on the final level

```python
def _process_snapshot(self, instrument_id, snapshot_data):
    deltas = []

    # Clear existing book
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
                price=Price.from_str(level[0]),
                size=Quantity.from_str(level[1]),
                side=OrderSide.BUY if is_bid else OrderSide.SELL,
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

**Incremental updates** (delta-only):
- Receive via WebSocket stream
- Apply directly as `UPDATE` or `DELETE` actions
- Must maintain sequence numbers to detect gaps
- On gap detection → request fresh snapshot

### Managed Order Books

When subscribing with `managed=True` (default), the DataEngine:
1. Creates and maintains `OrderBook` instances in Cache
2. Applies deltas automatically
3. Optionally provides periodic snapshots via timers

Access managed books:
```python
book = self.cache.order_book(self.instrument_id)
```

## Accessing Book Data in Strategy

```python
def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
    book = self.cache.order_book(self.instrument_id)

    # Top of book
    best_bid = book.best_bid_price()    # Price
    best_ask = book.best_ask_price()    # Price
    best_bid_size = book.best_bid_size()  # Quantity
    best_ask_size = book.best_ask_size()  # Quantity

    # Spread
    spread = best_ask - best_bid
    mid = (best_bid + best_ask) / 2

    # Full depth
    bids = book.bids()  # list[BookLevel] - sorted best to worst
    asks = book.asks()  # list[BookLevel] - sorted best to worst

    # Level details
    for level in bids[:5]:  # top 5 bid levels
        price = level.price
        size = level.size    # aggregate size at this level
        count = level.count  # number of orders (L3 only)

    # Book statistics
    bid_depth = sum(level.size for level in bids[:10])
    ask_depth = sum(level.size for level in asks[:10])
    imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)

def on_order_book_depth(self, depth: OrderBookDepth10) -> None:
    # Pre-aggregated top 10 levels (lower latency than full book)
    for i in range(10):
        bid_price = depth.bids[i].price
        bid_size = depth.bids[i].size
        ask_price = depth.asks[i].price
        ask_size = depth.asks[i].size
```

## Own Order Book

Tracks YOUR active orders by price level, separate from venue order book. Critical for:
- Real-time order state monitoring
- Self-trade prevention
- Queue position estimation
- Reconciliation validation

```python
def on_start(self) -> None:
    own_book = self.cache.own_order_book(self.instrument_id)

def check_before_submit(self, price: Price, side: OrderSide) -> bool:
    own_book = self.cache.own_order_book(self.instrument_id)
    # Check if we already have an order at this price
    # Prevents duplicate orders at same level
    for level in own_book.bids() if side == OrderSide.BUY else own_book.asks():
        if level.price == price:
            return False  # already have order here
    return True
```

### Safe Cancel Pattern

```python
# Exclude PENDING_CANCEL to avoid duplicate cancel requests
open_orders = [
    o for o in self.cache.orders_open(instrument_id=self.instrument_id)
    if o.status != OrderStatus.PENDING_CANCEL
]
for order in open_orders:
    self.cancel_order(order)
```

The `accepted_buffer_ns` parameter filters inflight orders using timestamp guards, preventing operations on orders not yet confirmed by venue.

## HFT Strategy Patterns

### Spread Capture with Order Book

```python
class SpreadCaptureStrategy(Strategy):
    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        self.subscribe_order_book_deltas(
            self.config.instrument_id,
            book_type=BookType.L2_MBP,
        )
        self.subscribe_trade_ticks(self.config.instrument_id)

    def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
        book = self.cache.order_book(self.config.instrument_id)
        if book.best_bid_price() is None or book.best_ask_price() is None:
            return

        spread = book.best_ask_price() - book.best_bid_price()
        min_spread = self.instrument.price_increment * self.config.min_spread_ticks

        if spread > min_spread:
            self._update_quotes(book)

    def _update_quotes(self, book) -> None:
        mid = (book.best_bid_price() + book.best_ask_price()) / 2

        # Inventory-aware skew
        position = self.cache.position(self.config.instrument_id)
        signed_qty = position.signed_qty if position else 0
        skew = -(signed_qty / self.config.max_position) * self.config.skew_factor

        bid_price = self.instrument.make_price(mid * (1 - self.config.half_spread + skew))
        ask_price = self.instrument.make_price(mid * (1 + self.config.half_spread + skew))

        self._cancel_and_replace(bid_price, ask_price)
```

### Book Imbalance Signal

```python
def compute_imbalance(self, book, depth: int = 5) -> float:
    bids = book.bids()[:depth]
    asks = book.asks()[:depth]

    bid_volume = sum(float(l.size) for l in bids)
    ask_volume = sum(float(l.size) for l in asks)

    if bid_volume + ask_volume == 0:
        return 0.0

    return (bid_volume - ask_volume) / (bid_volume + ask_volume)
    # >0 = buy pressure, <0 = sell pressure
```

### Sequence Gap Detection

```python
class GapDetectingDataClient(LiveMarketDataClient):
    def __init__(self, ...):
        super().__init__(...)
        self._last_sequence: dict[InstrumentId, int] = {}

    def _process_order_book_update(self, msg: dict) -> None:
        instrument_id = self._get_instrument_id(msg["symbol"])
        sequence = msg["u"]

        last_seq = self._last_sequence.get(instrument_id)
        if last_seq is not None and sequence != last_seq + 1:
            self.log.warning(
                f"Sequence gap for {instrument_id}: expected {last_seq + 1}, got {sequence}"
            )
            # Request fresh snapshot to resync
            asyncio.ensure_future(self._resync_book(instrument_id))
            return

        self._last_sequence[instrument_id] = sequence
        # Process deltas normally...
```

## Backtesting with Order Book Data

### Loading Order Book Data

```python
from nautilus_trader.persistence.wranglers import OrderBookDeltaDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider

instrument = TestInstrumentProvider.btcusdt_binance()
wrangler = OrderBookDeltaDataWrangler(instrument)

# From raw DataFrame (Tardis, Databento, custom)
deltas = wrangler.process(df_raw)
deltas.sort(key=lambda x: x.ts_init)  # ensure chronological order

# Add to BacktestEngine
engine.add_data(deltas)
```

### Tardis Integration for Historical Book Data

```python
from nautilus_trader.adapters.tardis.loaders import TardisCSVDataLoader

# Load order book changes
deltas_df = TardisCSVDataLoader.load("book_change_BTCUSDT_2024-01.csv")

# Load trade data
trades_df = TardisCSVDataLoader.load("trades_BTCUSDT_2024-01.csv")
```

## Performance Considerations

1. **Use L2 over L3** unless queue position tracking is required — significantly less data
2. **Process deltas, not snapshots** — incremental updates are orders of magnitude faster
3. **Cache instrument reference** in `on_start()` — avoid repeated cache lookups
4. **Keep `on_order_book_deltas` minimal** — this fires at tick frequency
5. **Use `OrderBookDepth10`** for signal generation — pre-aggregated, lower overhead than full book
6. **Rust OrderBook implementation** — all book operations (apply_delta, best_bid, etc.) execute in Rust regardless of Python strategy
7. **Sequence tracking** — always validate sequence numbers to detect gaps early
