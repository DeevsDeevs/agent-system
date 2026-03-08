# Simulation

## SimulatedExchange Configuration

Every `BacktestEngine.add_venue()` creates a `SimulatedExchange` internally. Key parameters control matching behavior:

```python
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.model.enums import AccountType, BookType, OmsType
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.model.currencies import USD

engine = BacktestEngine(config=config)

engine.add_venue(
    venue=Venue("SIM"),
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    base_currency=USD,
    starting_balances=[Money(1_000_000, USD)],
    book_type=BookType.L2_MBP,        # L1_MBP (default), L2_MBP, L3_MBO
    queue_position=True,               # track limit order queue position
    frozen_account=False,              # False = enforce margin checks
    bar_execution=False,               # True = execute orders on bar data
    reject_stop_orders=False,          # True = reject stop orders (some venues)
    support_gtd_orders=True,           # Good-til-date support
    support_contingent_orders=True,    # OTO/OCO/OUO support
    use_reduce_only=True,              # enforce reduce_only flag
)
```

### Book Type Selection

| BookType | Data Required | Matching Behavior |
|----------|---------------|-------------------|
| `L1_MBP` | QuoteTick, TradeTick, Bar | Single-level, market orders may slip 1 tick |
| `L2_MBP` | OrderBookDelta (L2) | Multi-level, market orders walk the book |
| `L3_MBO` | OrderBookDelta (L3) | Individual order matching, most realistic |

## Matching Engine Concepts

### Price-Time Priority (default)

Orders matched by best price first, then earliest arrival time. This is the standard matching algorithm used by most exchanges.

In NautilusTrader's `OrderMatchingEngine`:
- Market orders execute against the book at available prices
- Limit orders rest in the book until price matches
- With L2/L3 data, orders walk through multiple price levels consuming liquidity
- With L1 data, simplified single-level matching

### Fill Behavior by Data Type

**L2/L3 OrderBookDelta**: Most realistic. Market orders consume liquidity across price levels. Large orders experience market impact (price slippage across levels).

**L1 QuoteTick/TradeTick**: Top-of-book only. Market orders fill at best bid/ask. If order size exceeds top-of-book quantity, may slip one tick.

**Bar data**: Least realistic. Enable `bar_execution=True`. Bars provide OHLC range — stop orders trigger when price moves through high/low. No book depth simulation.

## Queue Position Tracking

Enable `queue_position=True` for realistic limit order fills:

```python
engine.add_venue(
    venue=Venue("SIM"),
    oms_type=OmsType.NETTING,
    account_type=AccountType.CASH,
    starting_balances=[Money(100_000, USD)],
    queue_position=True,  # requires TradeTick data
)
```

**How it works**: When a limit order is placed, Nautilus estimates queue position based on visible book depth. As `TradeTick` data arrives at that price level, it decrements the queue counter. The order fills only when sufficient volume has traded through, simulating realistic queue waiting.

**Requirements**: TradeTick data alongside OrderBookDelta data. Without trade ticks, queue position cannot be estimated.

## Custom Fill Models

Implement `FillModel` to control fill probability and slippage:

```python
from nautilus_trader.backtest.models import FillModel


class CustomFillModel(FillModel):
    def is_limit_filled(self) -> bool:
        # Return True if limit order should be filled at this step
        # Default uses prob_fill_on_limit probability
        return self._random.random() < self._prob_fill_on_limit

    def is_stop_filled(self) -> bool:
        return True  # stops always fill when triggered

    def slippage_ticks(self) -> int:
        # Number of ticks of slippage for market/stop orders
        if self._random.random() < self._prob_slippage:
            return 1
        return 0
```

Register via `ImportableFillModelConfig`:

```python
from nautilus_trader.backtest.config import ImportableFillModelConfig

BacktestVenueConfig(
    name="SIM",
    oms_type="NETTING",
    account_type="MARGIN",
    starting_balances=["1_000_000 USD"],
    fill_model=ImportableFillModelConfig(
        fill_model_path="my_models:CustomFillModel",
        config_path="my_models:CustomFillModelConfig",
        config={"prob_fill_on_limit": 0.3, "prob_slippage": 0.2},
    ),
)
```

### Built-in Fill Models

| Model | Description |
|-------|-------------|
| `FillModel` | Probabilistic fill with configurable limit fill probability and slippage |
| `ThreeTierFillModel` | Simulates depth with 50/30/20 contracts at 3 price levels |
| `VolumeSensitiveFillModel` | Volume-based fill simulation for market impact modeling |

## Custom Fee Models

Implement `FeeModel` for venue-specific fee structures:

```python
from nautilus_trader.backtest.models import FeeModel
from nautilus_trader.model.objects import Money


class TieredFeeModel(FeeModel):
    def get_commission(
        self,
        order,
        fill_qty,
        fill_px,
        instrument,
    ) -> Money:
        notional = float(fill_qty) * float(fill_px)
        # Maker/taker differentiation
        if order.is_passive:
            rate = 0.0002  # 2 bps maker
        else:
            rate = 0.0005  # 5 bps taker
        fee = notional * rate
        return Money(fee, instrument.quote_currency)
```

**Cython naming**: When registering Cython-implemented fee models, use the module path that Cython exposes (typically same as Python path).

## Latency Simulation

Model network and processing delays:

```python
from nautilus_trader.backtest.models import LatencyModel

latency_model = LatencyModel(
    base_latency_nanos=50_000_000,       # 50ms base
    insert_latency_nanos=50_000_000,     # 50ms order insert
    update_latency_nanos=50_000_000,     # 50ms order modify
    cancel_latency_nanos=50_000_000,     # 50ms order cancel
)

engine.add_venue(
    venue=Venue("SIM"),
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    starting_balances=[Money(1_000_000, USD)],
    latency_model=latency_model,
)
```

Latency applies between order submission and venue acknowledgment. Orders can be rejected or modified during the latency window if market moves.

## Multi-Venue Simulation

Add multiple venues with independent configurations:

```python
engine.add_venue(
    venue=Venue("BINANCE"),
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    base_currency=USDT,
    starting_balances=[Money(500_000, USDT)],
)

engine.add_venue(
    venue=Venue("BYBIT"),
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    base_currency=USDT,
    starting_balances=[Money(500_000, USDT)],
)

# Add instruments and data for each venue separately
engine.add_instrument(binance_btcusdt)
engine.add_instrument(bybit_btcusdt)
engine.add_data(binance_trades)
engine.add_data(bybit_trades)
```

Each venue has independent order matching, fills, and account balances. Cross-venue strategies (arbitrage) work naturally — the strategy submits orders to different venues via `instrument_id` routing.

## Synthetic Instruments

Create custom derived instruments for spread/basis simulation:

```python
from nautilus_trader.model.instruments import SyntheticInstrument
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue

synthetic = SyntheticInstrument(
    symbol=Symbol("BTC-SPREAD"),
    price_precision=2,
    components=[
        InstrumentId.from_str("BTCUSDT-PERP.BINANCE"),
        InstrumentId.from_str("BTCUSDT.BINANCE"),
    ],
    formula="(components[0] - components[1])",
    ts_event=0,
    ts_init=0,
)
```

Synthetic instruments derive their price from component instruments using a formula. Subscribe to the synthetic to receive derived data updates when any component updates.

## Realistic Backtest Checklist

| Setting | Purpose | Default |
|---------|---------|---------|
| `book_type=L2_MBP` | Multi-level book matching | `L1_MBP` |
| `queue_position=True` | Limit order queue simulation | `False` |
| `latency_model` | Network delay simulation | None |
| Custom `FillModel` | Realistic fill behavior | Probabilistic |
| Custom `FeeModel` | Venue-accurate fees | Fixed commission |
| `frozen_account=False` | Enforce margin/balance checks | `False` |
| TradeTick data | Required for queue position | — |
| OrderBookDelta data | Required for L2/L3 matching | — |
