# Microstructure Analysis

Quantitative tools for measuring adverse selection, optimizing quotes, and understanding fill quality in crypto HFT on NautilusTrader.

## Adverse Selection

### VPIN (Volume-Synchronized Probability of Informed Trading)

Estimates the probability that volume is driven by informed traders. High VPIN → widen spreads or reduce size.

```python
from collections import deque
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import AggressorSide

class VPINTracker:
    def __init__(self, bucket_size: float, n_buckets: int = 50):
        self.bucket_size = bucket_size  # volume per bucket (e.g., 10 BTC)
        self.n_buckets = n_buckets
        self._buckets: deque[float] = deque(maxlen=n_buckets)
        self._current_buy_vol = 0.0
        self._current_total_vol = 0.0

    def update(self, tick: TradeTick) -> float | None:
        size = float(tick.size)
        if tick.aggressor_side == AggressorSide.BUYER:
            self._current_buy_vol += size
        self._current_total_vol += size

        if self._current_total_vol >= self.bucket_size:
            buy_frac = self._current_buy_vol / self._current_total_vol
            order_imbalance = abs(buy_frac - 0.5) * 2  # normalized [0, 1]
            self._buckets.append(order_imbalance)
            self._current_buy_vol = 0.0
            self._current_total_vol = 0.0

            if len(self._buckets) == self.n_buckets:
                return sum(self._buckets) / self.n_buckets  # VPIN ∈ [0, 1]
        return None
```

**Interpretation**: VPIN > 0.7 signals elevated informed trading. Widen spreads by 50-100% or pause quoting. VPIN < 0.3 is calm — tighten spreads for volume capture.

### Glosten-Milgrom Spread Decomposition

The bid-ask spread compensates for two costs:
- **Adverse selection component**: loss to informed traders who know the true value
- **Order processing component**: fees, inventory risk, operational cost

```
spread = adverse_selection + order_processing
adverse_selection ≈ spread - 2 * (realized_spread)
```

Measure the adverse selection component by comparing trade price to the midpoint after a delay (e.g., 1 second):

### Realized Spread

```python
def realized_spread(
    trade_price: float,
    side_sign: int,       # +1 for buyer-initiated, -1 for seller-initiated
    mid_after_delay: float,
) -> float:
    return 2 * side_sign * (trade_price - mid_after_delay)
```

In NautilusTrader, use timestamps to measure:

```python
def on_trade_tick(self, tick: TradeTick) -> None:
    mid = float(self.cache.order_book(self.instrument_id).midpoint())
    side_sign = 1 if tick.aggressor_side == AggressorSide.BUYER else -1
    # Schedule delayed midpoint capture
    self._pending_spreads.append({
        "trade_price": float(tick.price),
        "side_sign": side_sign,
        "trade_ts": tick.ts_event,
        "mid_at_trade": mid,
    })

def _compute_realized_spreads(self) -> None:
    current_mid = float(self.cache.order_book(self.instrument_id).midpoint())
    for entry in self._pending_spreads:
        rs = 2 * entry["side_sign"] * (entry["trade_price"] - current_mid)
        self._realized_spreads.append(rs)
    self._pending_spreads.clear()
```

Negative average realized spread → you're being adversely selected. Widen quotes or increase VPIN threshold.

## Microprice

Simple midpoint treats bid and ask equally, ignoring size imbalance. Microprice weights by opposite-side volume, giving a better estimate of where the next trade will occur.

### Formula

```
microprice = bid * (ask_size / (bid_size + ask_size)) + ask * (bid_size / (bid_size + ask_size))
```

When ask_size >> bid_size, microprice shifts toward the bid (selling pressure → price likely to drop). When bid_size >> ask_size, microprice shifts toward the ask.

### NautilusTrader Implementation

```python
def _compute_microprice(self) -> Decimal | None:
    book = self.cache.order_book(self.config.instrument_id)
    bid = book.best_bid_price()
    ask = book.best_ask_price()
    bid_sz = book.best_bid_size()
    ask_sz = book.best_ask_size()
    if not all([bid, ask, bid_sz, ask_sz]):
        return None
    bv = float(bid_sz)
    av = float(ask_sz)
    return Decimal(str(
        (float(bid) * av + float(ask) * bv) / (bv + av)
    ))
```

### Multi-Level Extension

Weight across multiple levels for more stable estimates:

```python
def _weighted_microprice(self, depth: int = 3) -> float:
    book = self.cache.order_book(self.config.instrument_id)
    bids = book.bids()[:depth]
    asks = book.asks()[:depth]

    bid_weighted = sum(float(l.price) * float(l.size) for l in bids)
    ask_weighted = sum(float(l.price) * float(l.size) for l in asks)
    bid_total = sum(float(l.size) for l in bids)
    ask_total = sum(float(l.size) for l in asks)

    if bid_total + ask_total == 0:
        return 0.0
    # Cross-weight: bid prices weighted by ask volume and vice versa
    return (bid_weighted * ask_total + ask_weighted * bid_total) / (
        (bid_total + ask_total) * (bid_total + ask_total)
    ) * 2
```

**When to use**: Always prefer microprice over simple midpoint for MM quoting. The improvement is most significant when book imbalance is high.

## Order-to-Fill Latency Measurement

### Execution Latency

```python
def on_order_filled(self, event) -> None:
    order = self.cache.order(event.client_order_id)
    # fill_ts_event: when exchange matched the order
    # submit_ts_init: when Nautilus sent the order
    fill_latency_ns = event.ts_event - order.ts_init
    fill_latency_ms = fill_latency_ns / 1_000_000
    self._latencies.append(fill_latency_ms)
    self.log.info(f"Fill latency: {fill_latency_ms:.1f}ms")
```

### Data Latency

```python
def on_order_book_deltas(self, deltas) -> None:
    # ts_event: when exchange generated the update
    # ts_init: when Nautilus received it
    for delta in deltas:
        data_latency_ns = delta.ts_init - delta.ts_event
        data_latency_ms = data_latency_ns / 1_000_000
```

### Clock Synchronization

- **NTP requirement**: Sync local clock to <1ms accuracy via NTP or PTP
- **ts_event from exchange**: Always populate from exchange timestamp, not local clock
- **Clock drift**: If exchange and local clocks drift, latency measurements become unreliable. Monitor `ts_init - ts_event` — if it goes negative, clocks are desynchronized
- **Impact**: Inaccurate latency → wrong queue position estimates → overstated backtest PnL

## Fee Optimization and Breakeven Spread

### Breakeven Formula

When adverse selection forces a taker fill on one side:
```
breakeven_spread = maker_fee + taker_fee
```

For pure MM where both sides fill as maker:
```
breakeven_spread = 2 * maker_fee
```

### Venue Fees at Runtime

Fee tiers differ by exchange, VIP level, volume, and token discounts. Access fees loaded from the exchange at runtime:

```python
instrument = self.cache.instrument(instrument_id)
maker_fee = float(instrument.maker_fee)
taker_fee = float(instrument.taker_fee)
breakeven = maker_fee + taker_fee
```

**FeeModel is backtest-only** — live trading uses actual fees from exchange fill reports. For realistic backtesting, configure a custom `FeeModel` that matches your actual fee tier (see below).

### Custom FeeModel in Backtest

```python
from nautilus_trader.backtest.models import FeeModel
from nautilus_trader.model.objects import Money

class TieredCryptoFeeModel(FeeModel):
    def __init__(self, maker_rate: float = 0.0002, taker_rate: float = 0.0005):
        self._maker_rate = maker_rate
        self._taker_rate = taker_rate

    def get_commission(self, order, fill_qty, fill_px, instrument) -> Money:
        notional = float(fill_qty) * float(fill_px)
        rate = self._maker_rate if order.is_passive else self._taker_rate
        fee = notional * rate
        return Money(fee, instrument.quote_currency)
```

Configure `maker_rate` and `taker_rate` to match your actual exchange tier. Check your exchange's fee schedule — rates vary by VIP level, volume, and token discount programs.

## Naive Fill Model Bias

### The Problem

NautilusTrader's default backtest fill model fills limit orders when price touches the level. In reality:

1. **Queue position**: Your order waits behind others at that price. Fills happen only after sufficient volume trades through.
2. **Adverse selection**: When price touches your level and your order fills, it's often because an informed trader pushed price through — the fill itself is correlated with adverse price movement.
3. **Phantom fills**: In backtest, your passive orders "capture spread" on every touch. Live, many of those touches don't fill you, and those that do are disproportionately the ones that continue moving against you.

### Mitigation

```python
# Enable queue position simulation
engine.add_venue(
    venue=Venue("SIM"),
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    starting_balances=[Money(1_000_000, USDT)],
    queue_position=True,  # requires TradeTick data
)
```

Even with queue position enabled, adverse selection is not modeled. The fill-when-queue-clears assumption still overstates profitability because it doesn't account for information content of the fills.

### Conservative Expectation

For MM strategies, expect 30-50% of backtest PnL in live. If a backtest shows 100 bps/day, budget for 30-50 bps/day live. If the strategy isn't profitable with a 50% haircut, it won't work live.

## Order Sizing via Book Depth API

NautilusTrader provides full book depth access for sizing decisions:

```python
def _compute_safe_size(self) -> Decimal:
    book = self.cache.order_book(self.config.instrument_id)
    best_bid_size = float(book.best_bid_size()) if book.best_bid_size() else 0
    best_ask_size = float(book.best_ask_size()) if book.best_ask_size() else 0
    min_depth = min(best_bid_size, best_ask_size)
    # Size relative to available liquidity — tune fraction per your strategy
    max_frac = min_depth * 0.05
    size = min(float(self.config.trade_size), max_frac)
    return self.instrument.make_qty(Decimal(str(max(size, float(self.instrument.min_quantity)))))
```

Always use `instrument.make_qty()` for lot size compliance.
