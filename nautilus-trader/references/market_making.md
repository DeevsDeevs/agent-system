# Market Making

## MarketMaker Strategy Pattern

The core NautilusTrader market making pattern: maintain two-sided quotes around midpoint, adjust for inventory risk.

```python
from decimal import Decimal
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.book import OrderBook
from nautilus_trader.model.data import OrderBookDeltas, QuoteTick
from nautilus_trader.model.enums import BookType, OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy


class MarketMakerConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    trade_size: Decimal
    max_size: Decimal = Decimal("10")
    spread: Decimal = Decimal("0.001")       # 10 bps default
    skew_factor: Decimal = Decimal("0.5")    # inventory adjustment strength
    order_id_tag: str = "MM"


class MarketMaker(Strategy):
    def __init__(self, config: MarketMakerConfig) -> None:
        super().__init__(config)
        self.instrument = None
        self.book = None
        self._last_mid = None

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.log.error(f"Instrument not found: {self.config.instrument_id}")
            self.stop()
            return

        self.book = OrderBook(self.config.instrument_id, BookType.L2_MBP)
        self.subscribe_order_book_deltas(self.config.instrument_id)

    def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
        self.book.apply_deltas(deltas)
        if not self.book.best_bid_price() or not self.book.best_ask_price():
            return

        mid = (self.book.best_bid_price() + self.book.best_ask_price()) / 2
        if mid != self._last_mid:
            self._last_mid = mid
            self._requote(mid)

    def _requote(self, mid: Decimal) -> None:
        self.cancel_all_orders(self.config.instrument_id)

        skew = self._inventory_skew()
        half_spread = self.config.spread / 2

        bid_price = mid * (1 - half_spread + skew)
        ask_price = mid * (1 + half_spread + skew)

        bid = self.order_factory.limit(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(self.config.trade_size),
            price=self.instrument.make_price(bid_price),
            time_in_force=TimeInForce.GTC,
            post_only=True,
        )
        ask = self.order_factory.limit(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.SELL,
            quantity=self.instrument.make_qty(self.config.trade_size),
            price=self.instrument.make_price(ask_price),
            time_in_force=TimeInForce.GTC,
            post_only=True,
        )
        self.submit_order(bid)
        self.submit_order(ask)

    def _inventory_skew(self) -> Decimal:
        position = self.cache.position_for_instrument(self.config.instrument_id)
        if position is None:
            return Decimal(0)
        signed_qty = position.signed_qty
        return -(signed_qty / self.config.max_size) * self.config.skew_factor

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)
        self.close_all_positions(self.config.instrument_id)
```

### Inventory Skew Logic

The skew shifts both bid and ask prices to discourage accumulation:

```
skew = -(signed_qty / max_size) * skew_factor
```

| Position | Skew Effect | Result |
|----------|-------------|--------|
| Long +5 (max 10) | skew = -0.25 | Bid lower, ask lower → encourage sells |
| Short -5 (max 10) | skew = +0.25 | Bid higher, ask higher → encourage buys |
| Flat 0 | skew = 0 | Symmetric quotes |

### Quote Management

**Cancel-all + re-quote**: On every midpoint change, cancel all open orders and place new ones. Simple but generates more messages. Suitable for backtests and slower venues.

**Modify-in-place**: Track open bid/ask order IDs, use `self.modify_order()` to update price. Fewer messages, better for live high-frequency. Requires careful state tracking.

## Spread Calculation Patterns

### Fixed Spread
```python
half_spread = Decimal("0.0005")  # 5 bps each side
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

class VolatilityMM(Strategy):
    def __init__(self, config: VolatilityMMConfig) -> None:
        super().__init__(config)
        self.atr = AverageTrueRange(config.atr_period)

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        self.register_indicator_for_bars(self.config.bar_type, self.atr)
        self.subscribe_bars(self.config.bar_type)
        self.subscribe_order_book_deltas(self.config.instrument_id)

    def _calculate_spread(self) -> Decimal:
        if not self.atr.initialized:
            return Decimal("0.001")  # fallback
        return Decimal(str(self.atr.value)) * self.config.atr_multiple
```

### Order Book Imbalance Spread
```python
def _calculate_imbalance(self) -> float:
    bid_size = float(self.book.best_bid_size())
    ask_size = float(self.book.best_ask_size())
    total = bid_size + ask_size
    if total == 0:
        return 0.0
    return (bid_size - ask_size) / total  # range [-1, 1]

def _adjust_spread_for_imbalance(self, base_spread: Decimal) -> tuple[Decimal, Decimal]:
    imbalance = self._calculate_imbalance()
    # Positive imbalance = more bids = buying pressure → widen ask, tighten bid
    bid_spread = base_spread / 2 * Decimal(str(1 - imbalance * 0.3))
    ask_spread = base_spread / 2 * Decimal(str(1 + imbalance * 0.3))
    return bid_spread, ask_spread
```

## VolatilityMarketMaker Pattern

Uses ATR to dynamically size the spread. Wider spread in volatile markets, tighter in calm markets.

Key config: `atr_period`, `atr_multiple`, `trade_size`, `bar_type` for ATR calculation + `instrument_id` for order book subscription.

## OrderBookImbalance Pattern

Directional strategy driven by L2 book imbalance. When bid volume significantly exceeds ask volume, signals buying pressure.

```python
class OrderBookImbalanceConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    trade_size: Decimal
    trigger_imbalance: float = 0.6  # enter when imbalance > threshold

class OrderBookImbalance(Strategy):
    def on_order_book_deltas(self, deltas):
        self.book.apply_deltas(deltas)
        imbalance = self._calculate_imbalance()
        if imbalance > self.config.trigger_imbalance:
            if self.portfolio.is_flat(self.config.instrument_id):
                self._buy()
        elif imbalance < -self.config.trigger_imbalance:
            if self.portfolio.is_flat(self.config.instrument_id):
                self._sell()
```

## Avellaneda-Stoikov Reference Model

Theoretical framework for optimal market making under inventory risk.

**Reservation price** (indifference price accounting for inventory risk):
```
r(s, q, t) = s - q * γ * σ² * (T - t)
```
- `s` = mid price, `q` = inventory, `γ` = risk aversion
- `σ` = volatility, `T - t` = time to horizon

**Optimal spread**:
```
δ = γ * σ² * (T - t) + (2/γ) * ln(1 + γ/κ)
```
- `κ` = order arrival intensity parameter

**Implementation sketch**:
```python
def _avellaneda_quotes(self, mid: float, inventory: float) -> tuple[float, float]:
    sigma = self.atr.value / mid  # normalized volatility
    tau = self._time_to_horizon()
    gamma = float(self.config.risk_aversion)

    reservation_price = mid - inventory * gamma * sigma**2 * tau
    optimal_spread = gamma * sigma**2 * tau + (2 / gamma) * math.log(1 + gamma / self.config.kappa)

    bid = reservation_price - optimal_spread / 2
    ask = reservation_price + optimal_spread / 2
    return bid, ask
```

## Risk Controls

| Control | Implementation |
|---------|---------------|
| Max position | Check `signed_qty` vs `max_size` before quoting |
| Skew adjustment | Shift quotes to reduce inventory (see above) |
| Reduce-only | Use `reduce_only=True` on orders that would reduce position |
| Stale order cleanup | Cancel orders on `on_stop()`, use timer for periodic cleanup |
| Loss limits | Track PnL via `self.portfolio`, stop quoting if drawdown exceeded |

```python
def _should_quote(self) -> bool:
    position = self.cache.position_for_instrument(self.config.instrument_id)
    if position and abs(position.signed_qty) >= float(self.config.max_size):
        return False
    return True
```

## Order Lifecycle in MM Context

1. **Quote placement**: Submit bid + ask limit orders (post_only to ensure maker)
2. **Fill notification**: `on_order_filled()` fires → position changes → recalculate skew
3. **Midpoint change**: Cancel stale quotes → recalculate prices → submit new quotes
4. **Partial fill**: Order remains open with reduced quantity, position updated
5. **Quote refresh**: Periodic or event-driven cancellation of stale orders

```python
def on_order_filled(self, event) -> None:
    self.log.info(f"Filled: {event.client_order_id} @ {event.last_px}")
    # Position automatically updated by engine
    # Next book update triggers _requote with new skew
```
