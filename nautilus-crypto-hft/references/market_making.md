# Market Making

Market making patterns for NautilusTrader: inventory skew, spread methods, Avellaneda-Stoikov, fee-aware quoting, and anti-fingerprinting.

## Core Pattern: modify_order as Primary

`modify_order` sends a single amend message — fewer messages, less detectable, lower latency than cancel+replace. Fall back to cancel+replace only when modify is rejected or unsupported (dYdX).

```python
from decimal import Decimal
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import OrderBookDeltas
from nautilus_trader.model.enums import BookType, OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy


class MarketMakerConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    trade_size: Decimal
    max_size: Decimal = Decimal("10")
    half_spread: Decimal = Decimal("0.0005")  # must exceed breakeven
    skew_factor: Decimal = Decimal("0.5")


class MarketMaker(Strategy):
    def __init__(self, config: MarketMakerConfig) -> None:
        super().__init__(config)
        self.instrument = None
        self._bid_id = None
        self._ask_id = None

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.log.error(f"Instrument not found: {self.config.instrument_id}")
            self.stop()
            return
        self.subscribe_order_book_deltas(
            self.config.instrument_id, book_type=BookType.L2_MBP,
        )

    def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
        book = self.cache.order_book(self.config.instrument_id)
        if not book.best_bid_price() or not book.best_ask_price():
            return

        # Microprice: volume-weighted mid
        bv, av = float(book.best_bid_size()), float(book.best_ask_size())
        mid = Decimal(str(
            (float(book.best_bid_price()) * av + float(book.best_ask_price()) * bv) / (bv + av)
        ))
        self._requote(mid)

    def _requote(self, mid: Decimal) -> None:
        skew = self._inventory_skew()
        bid_px = self.instrument.make_price(mid * (1 - self.config.half_spread + skew))
        ask_px = self.instrument.make_price(mid * (1 + self.config.half_spread + skew))
        qty = self.instrument.make_qty(self.config.trade_size)

        # Modify existing orders if possible
        bid_order = self.cache.order(self._bid_id) if self._bid_id else None
        if bid_order and bid_order.is_open:
            self.modify_order(bid_order, quantity=qty, price=bid_px)
        else:
            bid = self.order_factory.limit(
                instrument_id=self.config.instrument_id,
                order_side=OrderSide.BUY, quantity=qty, price=bid_px,
                time_in_force=TimeInForce.GTC, post_only=True,
            )
            self.submit_order(bid)
            self._bid_id = bid.client_order_id

        ask_order = self.cache.order(self._ask_id) if self._ask_id else None
        if ask_order and ask_order.is_open:
            self.modify_order(ask_order, quantity=qty, price=ask_px)
        else:
            ask = self.order_factory.limit(
                instrument_id=self.config.instrument_id,
                order_side=OrderSide.SELL, quantity=qty, price=ask_px,
                time_in_force=TimeInForce.GTC, post_only=True,
            )
            self.submit_order(ask)
            self._ask_id = ask.client_order_id

    def _inventory_skew(self) -> Decimal:
        pos = self.cache.position_for_instrument(self.config.instrument_id)
        if pos is None:
            return Decimal(0)
        return -(pos.signed_qty / self.config.max_size) * self.config.skew_factor

    def on_order_filled(self, event) -> None:
        # Position updated by engine — next book update triggers _requote with new skew
        self.log.info(f"Filled: {event.client_order_id} @ {event.last_px}")

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)
        self.close_all_positions(self.config.instrument_id)
```

### Inventory Skew

```
skew = -(signed_qty / max_size) * skew_factor
```

| Position | Skew | Effect |
|----------|------|--------|
| Long +5 (max 10) | -0.25 | Both quotes shift down → encourage sells |
| Short -5 (max 10) | +0.25 | Both quotes shift up → encourage buys |
| Flat 0 | 0 | Symmetric quotes |

## Spread Calculation Methods

### Fixed Spread (Must Exceed Breakeven)

```python
half_spread = Decimal("0.0005")  # 5 bps each side = 10 bps total
# Verify: total spread (10 bps) > breakeven (7 bps for Binance VIP0)
```

### ATR-Based / Volatility Spread

```python
from nautilus_trader.indicators import AverageTrueRange

class VolatilityMMConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal
    atr_period: int = 20
    atr_multiple: Decimal = Decimal("1.5")
    min_spread: Decimal = Decimal("0.0007")  # floor at breakeven

class VolatilityMM(Strategy):
    def __init__(self, config: VolatilityMMConfig) -> None:
        super().__init__(config)
        self.atr = AverageTrueRange(config.atr_period)

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        self.register_indicator_for_bars(self.config.bar_type, self.atr)
        self.subscribe_bars(self.config.bar_type)
        self.subscribe_order_book_deltas(self.config.instrument_id)

    def _calculate_half_spread(self) -> Decimal:
        if not self.atr.initialized:
            return self.config.min_spread
        spread = Decimal(str(self.atr.value)) * self.config.atr_multiple
        return max(spread / 2, self.config.min_spread)
```

### Order Book Imbalance Spread

```python
def _imbalance_adjusted_spread(self, base_half: Decimal) -> tuple[Decimal, Decimal]:
    book = self.cache.order_book(self.config.instrument_id)
    bid_sz = float(book.best_bid_size() or 0)
    ask_sz = float(book.best_ask_size() or 0)
    total = bid_sz + ask_sz
    if total == 0:
        return base_half, base_half
    imbalance = (bid_sz - ask_sz) / total  # [-1, 1]
    # Positive imbalance = buy pressure → widen ask, tighten bid
    bid_half = base_half * Decimal(str(1 - imbalance * 0.3))
    ask_half = base_half * Decimal(str(1 + imbalance * 0.3))
    return bid_half, ask_half
```

## Avellaneda-Stoikov Model

Theoretical framework for optimal market making under inventory risk.

**Reservation price** (indifference price accounting for inventory risk):
```
r(s, q, t) = s - q * γ * σ² * (T - t)
```
- `s` = mid price, `q` = inventory, `γ` = risk aversion, `σ` = volatility, `T-t` = time to horizon

**Optimal spread**:
```
δ = γ * σ² * (T - t) + (2/γ) * ln(1 + γ/κ)
```
- `κ` = order arrival intensity

**Funding carrying cost for perps**: When holding a perp position, add funding cost to reservation price adjustment:
```
r_adjusted = s - q * [γ * σ² * (T - t) + funding_rate * Δt]
```

```python
import math

def _avellaneda_quotes(self, mid: float, inventory: float) -> tuple[float, float]:
    sigma = self.atr.value / mid if self.atr.initialized else 0.01
    tau = self._time_to_horizon()
    gamma = float(self.config.risk_aversion)
    kappa = float(self.config.order_arrival_intensity)

    # Funding carrying cost (perps)
    funding_cost = inventory * self._current_funding_rate * tau
    reservation = mid - inventory * gamma * sigma**2 * tau - funding_cost

    optimal_spread = gamma * sigma**2 * tau + (2 / gamma) * math.log(1 + gamma / kappa)
    bid = reservation - optimal_spread / 2
    ask = reservation + optimal_spread / 2
    return bid, ask
```

## Breakeven Spread and Fee Awareness

| Venue | Maker (bps) | Taker (bps) | Breakeven (bps) |
|-------|-------------|-------------|-----------------|
| Binance VIP0 | 2.0 | 5.0 | 7.0 |
| Bybit VIP0 | 2.0 | 5.5 | 7.5 |
| dYdX | 2.0 | 5.0 | 7.0 |
| OKX VIP0 | 2.0 | 5.0 | 7.0 |

**When adverse selection forces a taker fill**: `breakeven = maker_fee + taker_fee`

**Pure MM both sides maker**: `breakeven = 2 * maker_fee`

Always verify: `config.half_spread * 2 > breakeven`. A strategy that quotes inside breakeven loses money on every round trip.

## Order Sizing

- Never exceed 5-10% of best level depth — larger orders leak information
- Reduce size as position approaches max (inventory-weighted)
- Always use `instrument.make_qty()` for lot size compliance

```python
import random

def _safe_size(self) -> Quantity:
    book = self.cache.order_book(self.config.instrument_id)
    min_depth = min(float(book.best_bid_size() or 0), float(book.best_ask_size() or 0))
    max_frac = Decimal(str(min_depth * 0.05))
    base = min(self.config.trade_size, max_frac) if min_depth > 0 else self.config.trade_size
    # Randomize ±5% for anti-fingerprinting
    jitter = Decimal(str(random.uniform(0.95, 1.05)))
    return self.instrument.make_qty(max(base * jitter, self.instrument.min_quantity))
```

## Anti-Fingerprinting

| Pattern to Avoid | Mitigation |
|-----------------|------------|
| Fixed order sizes | Randomize ±5% with `random.uniform` |
| Regular requote intervals | Jitter timer by ±20% |
| Symmetric quotes | Inventory skew creates natural asymmetry |
| Cancel+replace pairs | Use `modify_order` (single message) |
| Round-number sizes | `instrument.make_qty()` with jittered Decimal |

## Cross-Venue Spread Capture

When the same instrument trades on multiple venues, capture the spread when prices diverge after fees.

```python
def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
    book_a = self.cache.order_book(self.config.instrument_a)
    book_b = self.cache.order_book(self.config.instrument_b)
    if not all([book_a.best_bid_price(), book_a.best_ask_price(),
                book_b.best_bid_price(), book_b.best_ask_price()]):
        return

    # Buy on B, sell on A (A.bid > B.ask)
    edge_ab = float(book_a.best_bid_price() - book_b.best_ask_price())
    cost = float(book_b.best_ask_price()) * self._total_fee  # maker+taker across venues
    if edge_ab > cost:
        self._execute_arb(buy_venue=self.config.instrument_b, sell_venue=self.config.instrument_a)
```

**Latency matters**: Cross-venue arb is latency-sensitive. The slower leg risks adverse fill. Submit the harder-to-fill side first.

## Risk Controls

| Control | Implementation |
|---------|---------------|
| Max position | Check `abs(signed_qty) < max_size` before quoting |
| Loss limit | Track portfolio PnL, stop quoting if drawdown exceeded |
| Stale orders | Timer-based periodic cleanup of old open orders |
| reduce_only | Set `reduce_only=True` when only reducing position |
| Circuit breaker | Handle `on_instrument_status` → HALT stops quoting |

```python
def _should_quote(self) -> bool:
    pos = self.cache.position_for_instrument(self.config.instrument_id)
    if pos and abs(pos.signed_qty) >= float(self.config.max_size):
        return False
    return True
```
