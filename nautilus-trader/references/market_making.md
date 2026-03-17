# Market Making

> *Rust: See [execution.md](execution.md#rust) for ownership differences. `post_only=True` → pass `None` positionally in Rust.*

## Core Pattern: modify_order as Primary

`modify_order` sends a single amend — lower latency than cancel+replace. Fall back to cancel+replace when rejected or unsupported (dYdX).

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
        self.subscribe_order_book_deltas(self.config.instrument_id, book_type=BookType.L2_MBP)

    def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
        book = self.cache.order_book(self.config.instrument_id)
        if not book.best_bid_price() or not book.best_ask_price():
            return
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
        for side, px, attr in [
            (OrderSide.BUY, bid_px, "_bid_id"), (OrderSide.SELL, ask_px, "_ask_id"),
        ]:
            existing = self.cache.order(getattr(self, attr)) if getattr(self, attr) else None
            if existing and existing.is_open:
                self.modify_order(existing, quantity=qty, price=px)
            else:
                order = self.order_factory.limit(
                    instrument_id=self.config.instrument_id,
                    order_side=side, quantity=qty, price=px,
                    time_in_force=TimeInForce.GTC, post_only=True,
                )
                self.submit_order(order)
                setattr(self, attr, order.client_order_id)

    def on_order_filled(self, event) -> None:
        if event.client_order_id == self._bid_id:
            self._bid_id = None
        elif event.client_order_id == self._ask_id:
            self._ask_id = None

    def _inventory_skew(self) -> Decimal:
        # Long → negative skew (encourage sells), Short → positive (encourage buys)
        positions = self.cache.positions_open(instrument_id=self.config.instrument_id)
        pos = positions[0] if positions else None
        if pos is None:
            return Decimal(0)
        return -(Decimal(str(pos.signed_qty)) / self.config.max_size) * self.config.skew_factor

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)
        self.close_all_positions(self.config.instrument_id)
```

## Spread Calculation

### Fixed

```python
half_spread = Decimal("0.0005")  # 5 bps each side = 10 bps total
```

### ATR-Based

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

### Order Book Imbalance

```python
def _imbalance_adjusted_spread(self, base_half: Decimal) -> tuple[Decimal, Decimal]:
    book = self.cache.order_book(self.config.instrument_id)
    bid_sz = float(book.best_bid_size() or 0)
    ask_sz = float(book.best_ask_size() or 0)
    total = bid_sz + ask_sz
    if total == 0:
        return base_half, base_half
    imbalance = (bid_sz - ask_sz) / total  # [-1, 1]
    bid_half = base_half * Decimal(str(1 - imbalance * 0.3))
    ask_half = base_half * Decimal(str(1 + imbalance * 0.3))
    return bid_half, ask_half
```

## Avellaneda-Stoikov Model

`r(s,q,t) = s - q*gamma*sigma^2*(T-t)` — reservation price. `delta = gamma*sigma^2*(T-t) + (2/gamma)*ln(1+gamma/kappa)` — optimal spread. For perps: `r -= q * funding_rate * dt`.

```python
import math

def _avellaneda_quotes(self, mid: float, inventory: float) -> tuple[float, float]:
    sigma = self.atr.value / mid if self.atr.initialized else 0.01
    tau = self._time_to_horizon()
    gamma = float(self.config.risk_aversion)
    kappa = float(self.config.order_arrival_intensity)
    funding_cost = inventory * self._current_funding_rate * tau
    reservation = mid - inventory * gamma * sigma**2 * tau - funding_cost
    optimal_spread = gamma * sigma**2 * tau + (2 / gamma) * math.log(1 + gamma / kappa)
    bid = reservation - optimal_spread / 2
    ask = reservation + optimal_spread / 2
    return bid, ask
```

## Breakeven and Fee Awareness

- **Adverse selection (taker fill)**: `breakeven = maker_fee + taker_fee`
- **Both sides maker**: `breakeven = 2 * maker_fee`
- Verify: `config.half_spread * 2 > breakeven`
- Access fees: `float(instrument.maker_fee)`, `float(instrument.taker_fee)`

## Order Sizing

Use `instrument.make_qty()` for lot size compliance.

```python
def _safe_size(self) -> Quantity:
    book = self.cache.order_book(self.config.instrument_id)
    min_depth = min(float(book.best_bid_size() or 0), float(book.best_ask_size() or 0))
    max_frac = Decimal(str(min_depth * 0.05))
    base = min(self.config.trade_size, max_frac) if min_depth > 0 else self.config.trade_size
    return self.instrument.make_qty(max(base, self.instrument.min_quantity))
```

## Cross-Venue Spread Capture

```python
def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
    book_a = self.cache.order_book(self.config.instrument_a)
    book_b = self.cache.order_book(self.config.instrument_b)
    if not all([book_a.best_bid_price(), book_a.best_ask_price(),
                book_b.best_bid_price(), book_b.best_ask_price()]):
        return
    edge_ab = float(book_a.best_bid_price() - book_b.best_ask_price())
    cost = float(book_b.best_ask_price()) * self._total_fee
    if edge_ab > cost:
        self._execute_arb(buy_venue=self.config.instrument_b, sell_venue=self.config.instrument_a)
```

## Risk Controls

Max position: `abs(signed_qty) < max_size` before quoting. Loss limit: stop quoting on drawdown. Stale orders: timer-based cleanup. `reduce_only=True` when reducing. Circuit breaker: `on_instrument_status` HALT.

> See SKILL.md for common hallucination guards.

See also: [order_book.md](order_book.md) | [market_maker_backtest.py](../examples/market_maker_backtest.py) | [market_maker_backtest.rs](../examples/market_maker_backtest.rs)
