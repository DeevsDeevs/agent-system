---
name: nautilus-trader
description: >
  Use when working with NautilusTrader algorithmic trading platform. Triggers:
  "nautilus_trader", "NautilusTrader", "BacktestEngine", "BacktestNode",
  "TradingNode", "SimulatedExchange", "StrategyConfig", "ExecAlgorithm",
  "OrderEmulator", "DataEngine", "ExecutionEngine", "RiskEngine", "MessageBus",
  "NautilusKernel", "ParquetDataCatalog", "DataCatalog", "LiveDataClient",
  "LiveExecutionClient", "InstrumentProvider", "OrderBookDelta", "QuoteTick",
  "TradeTick", "BarType", "bar aggregation", "TWAP execution algorithm",
  "order factory", "submit_order", "register_indicator_for_bars",
  "subscribe_bars", "subscribe_quote_ticks", "subscribe_trade_ticks",
  "OmsType", "NETTING", "HEDGING", "venue adapter", "Binance adapter",
  "Interactive Brokers adapter", "Bybit adapter", "Databento adapter",
  "Tardis adapter", "fill model", "fee model", "contingent orders",
  "OTO", "OCO", "OUO", "trailing stop", "market if touched",
  "execution reconciliation", "cache system", "Actor vs Strategy".
---

# NautilusTrader

High-performance, production-grade algorithmic trading platform. Hybrid Python/Rust/Cython architecture for backtesting and live deployment across asset classes.

## Quick Start

```bash
# Stable release
pip install -U nautilus_trader

# Latest development
pip install -U nautilus_trader --pre
```

```python
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig
from nautilus_trader.model.identifiers import TraderId

config = BacktestEngineConfig(trader_id=TraderId("BACKTESTER-001"))
engine = BacktestEngine(config=config)
```

## Architecture Overview

**Design**: Event-driven, domain-driven design with hexagonal (ports & adapters) architecture. Crash-only design prioritizing data integrity over availability.

**Core kernel** (single-threaded):

| Component | Role |
|-----------|------|
| `NautilusKernel` | Central orchestration, lifecycle management |
| `MessageBus` | Pub/Sub, Req/Rep, point-to-point messaging |
| `Cache` | In-memory storage for instruments, orders, positions |
| `DataEngine` | Market data processing and routing |
| `ExecutionEngine` | Order lifecycle, routing, reconciliation |
| `RiskEngine` | Pre-trade checks, position monitoring |
| `Portfolio` | Real-time aggregated portfolio state |

**Environments**: Backtest (historical + simulated venues), Sandbox (real-time + simulated), Live (real-time + live venues).

**Threading**: Single-threaded kernel for determinism. Background threads for network I/O, persistence, adapters — communicate via MessageBus channels.

**Constraint**: One `TradingNode` or `BacktestNode` per process. Sequential execution supported, not concurrent.

## Strategy Pattern

```python
from decimal import Decimal
from nautilus_trader.config import StrategyConfig
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId


class MyConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal
    fast_ema: int = 10
    slow_ema: int = 20


class MyStrategy(Strategy):
    def __init__(self, config: MyConfig) -> None:
        super().__init__(config)
        self.instrument = None
        self.fast_ema = ExponentialMovingAverage(config.fast_ema)
        self.slow_ema = ExponentialMovingAverage(config.slow_ema)

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.log.error(f"Instrument not found: {self.config.instrument_id}")
            self.stop()
            return

        self.register_indicator_for_bars(self.config.bar_type, self.fast_ema)
        self.register_indicator_for_bars(self.config.bar_type, self.slow_ema)
        self.request_bars(self.config.bar_type)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar) -> None:
        if not self.indicators_initialized():
            return
        if self.fast_ema.value >= self.slow_ema.value:
            if self.portfolio.is_flat(self.config.instrument_id):
                order = self.order_factory.market(
                    instrument_id=self.config.instrument_id,
                    order_side=OrderSide.BUY,
                    quantity=self.instrument.make_qty(self.config.trade_size),
                    time_in_force=TimeInForce.GTC,
                )
                self.submit_order(order)

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)
        self.close_all_positions(self.config.instrument_id)
```

### Lifecycle Methods

| Method | When |
|--------|------|
| `on_start()` | Strategy starts — subscribe data, register indicators |
| `on_stop()` | Strategy stops — cleanup, cancel orders, close positions |
| `on_resume()` | Resume from stopped state |
| `on_reset()` | Reset indicators between backtests |
| `on_dispose()` | Final cleanup before disposal |
| `on_degrade()` / `on_fault()` | Partial/critical failure handling |
| `on_save() -> dict[str, bytes]` | Persist custom state |
| `on_load(state: dict[str, bytes])` | Restore custom state |

### Data Handlers

| Method | Data Type |
|--------|-----------|
| `on_bar(bar)` | Bar (OHLCV) |
| `on_quote_tick(tick)` | QuoteTick (best bid/ask) |
| `on_trade_tick(tick)` | TradeTick (individual trades) |
| `on_order_book_deltas(deltas)` | OrderBookDelta (L2/L3 updates) |
| `on_order_book_depth(depth)` | OrderBookDepth10 (aggregated snapshot) |
| `on_order_book(book)` | Full OrderBook snapshot |
| `on_instrument(instrument)` | Instrument definition |
| `on_historical_data(data)` | Historical data response |
| `on_data(data)` | Custom data types |

### Order Event Handlers

All order events flow: specific handler → `on_order_event()` → `on_event()`.

| Handler | Event |
|---------|-------|
| `on_order_initialized` | `OrderInitialized` |
| `on_order_submitted` | `OrderSubmitted` |
| `on_order_accepted` | `OrderAccepted` |
| `on_order_rejected` | `OrderRejected` |
| `on_order_denied` | `OrderDenied` |
| `on_order_filled` | `OrderFilled` |
| `on_order_canceled` | `OrderCanceled` |
| `on_order_expired` | `OrderExpired` |
| `on_order_triggered` | `OrderTriggered` |
| `on_order_updated` | `OrderUpdated` |
| `on_order_emulated` | `OrderEmulated` |
| `on_order_released` | `OrderReleased` |
| `on_order_pending_update` | `OrderPendingUpdate` |
| `on_order_pending_cancel` | `OrderPendingCancel` |
| `on_order_modify_rejected` | `OrderModifyRejected` |
| `on_order_cancel_rejected` | `OrderCancelRejected` |

### Execution Methods

```python
self.submit_order(order)
self.submit_order_list(order_list)
self.modify_order(order, quantity, price, trigger_price)
self.cancel_order(order)
self.cancel_orders(orders)
self.cancel_all_orders(instrument_id)
self.close_position(position)
self.close_all_positions(instrument_id)
self.query_order(order)
```

## Order Types

All orders created via `self.order_factory` inside a Strategy:

```python
# Market Order
order = self.order_factory.market(
    instrument_id=instrument_id,
    order_side=OrderSide.BUY,
    quantity=Quantity.from_str("0.1"),
    time_in_force=TimeInForce.GTC,
)

# Limit Order
order = self.order_factory.limit(
    instrument_id=instrument_id,
    order_side=OrderSide.SELL,
    quantity=Quantity.from_int(10),
    price=Price.from_str("5000.00"),
    time_in_force=TimeInForce.GTC,
    post_only=True,
)

# Stop-Market Order
order = self.order_factory.stop_market(
    instrument_id=instrument_id,
    order_side=OrderSide.SELL,
    quantity=Quantity.from_int(1),
    trigger_price=Price.from_int(50000),
    trigger_type=TriggerType.LAST_PRICE,
    reduce_only=True,
)

# Stop-Limit Order
order = self.order_factory.stop_limit(
    instrument_id=instrument_id,
    order_side=OrderSide.BUY,
    quantity=Quantity.from_int(50_000),
    price=Price.from_str("1.30000"),
    trigger_price=Price.from_str("1.30010"),
    time_in_force=TimeInForce.GTD,
    expire_time=pd.Timestamp("2024-06-06T12:00", tz="UTC"),
)

# Market-If-Touched Order
order = self.order_factory.market_if_touched(
    instrument_id=instrument_id,
    order_side=OrderSide.SELL,
    quantity=Quantity.from_int(10),
    trigger_price=Price.from_str("10000.00"),
    trigger_type=TriggerType.LAST_PRICE,
)

# Market-To-Limit Order
order = self.order_factory.market_to_limit(
    instrument_id=instrument_id,
    order_side=OrderSide.BUY,
    quantity=Quantity.from_int(200_000),
    time_in_force=TimeInForce.GTC,
)

# Trailing-Stop-Market Order
order = self.order_factory.trailing_stop_market(
    instrument_id=instrument_id,
    order_side=OrderSide.SELL,
    quantity=Quantity.from_int(10),
    activation_price=Price.from_str("5000"),
    trailing_offset=Decimal(100),
    trailing_offset_type=TrailingOffsetType.BASIS_POINTS,
    trigger_type=TriggerType.LAST_PRICE,
    reduce_only=True,
)

# Trailing-Stop-Limit Order
order = self.order_factory.trailing_stop_limit(
    instrument_id=instrument_id,
    order_side=OrderSide.SELL,
    quantity=Quantity.from_int(10),
    activation_price=Price.from_str("5000"),
    price=Price.from_str("4990"),
    trigger_price=Price.from_str("4995"),
    trailing_offset=Decimal(50),
    trailing_offset_type=TrailingOffsetType.BASIS_POINTS,
    trigger_type=TriggerType.LAST_PRICE,
)

# Limit-If-Touched Order
order = self.order_factory.limit_if_touched(
    instrument_id=instrument_id,
    order_side=OrderSide.BUY,
    quantity=Quantity.from_int(10),
    price=Price.from_str("4990.00"),
    trigger_price=Price.from_str("5000.00"),
    trigger_type=TriggerType.LAST_PRICE,
)
```

### TimeInForce Options

| Value | Meaning |
|-------|---------|
| `GTC` | Good-til-canceled |
| `IOC` | Immediate-or-cancel |
| `FOK` | Fill-or-kill |
| `GTD` | Good-til-date (requires `expire_time`) |
| `DAY` | Day order |
| `AT_THE_OPEN` | At the opening auction |
| `AT_THE_CLOSE` | At the closing auction |

### Contingent Orders

```python
from nautilus_trader.model.orders import OrderList

# OTO (One-Triggers-Other): entry triggers stop-loss
entry = self.order_factory.limit(...)
stop_loss = self.order_factory.stop_market(...)
order_list = OrderList(
    order_list_id=OrderListId("OTO-001"),
    orders=[entry, stop_loss],
    contingency_type=ContingencyType.OTO,
)
self.submit_order_list(order_list)

# OCO (One-Cancels-Other): take-profit OR stop-loss
# OUO (One-Updates-Other): linked bracket orders
```

## Data Types

| Type | Description |
|------|-------------|
| `OrderBookDelta` | Granular order book updates (L1/L2/L3) |
| `OrderBookDepth10` | Aggregated snapshot up to 10 levels |
| `QuoteTick` | Best bid/ask with sizes |
| `TradeTick` | Individual trade events |
| `Bar` | OHLCV candles |
| `MarkPriceUpdate` | Derivative mark prices |
| `FundingRateUpdate` | Perpetual funding rates |
| `InstrumentStatus` | Instrument state changes |
| `InstrumentClose` | Instrument close events |

### Bar Type Syntax

Format: `{instrument_id}-{step}-{aggregation}-{price_type}-{source}`

```
AAPL.XNAS-5-MINUTE-LAST-INTERNAL    # 5-minute trade bars, internally aggregated
BTCUSDT.BINANCE-1-HOUR-LAST-EXTERNAL # 1-hour bars from exchange
```

**Composite bars** (bar-to-bar): `AAPL.XNAS-5-MINUTE-LAST-INTERNAL@1-MINUTE-EXTERNAL`

**Aggregation methods**: TICK, VOLUME, VALUE, RENKO, TICK_IMBALANCE, TICK_RUNS, VOLUME_IMBALANCE, VOLUME_RUNS, VALUE_IMBALANCE, VALUE_RUNS, MILLISECOND, SECOND, MINUTE, HOUR, DAY, WEEK, MONTH

**Price types**: LAST, BID, ASK, MID

**Sources**: INTERNAL (aggregated by Nautilus), EXTERNAL (from venue)

### Timestamps

- `ts_event` — when event occurred (nanoseconds UNIX)
- `ts_init` — when Nautilus initialized the object
- Latency = `ts_init - ts_event`

## Value Types

Fixed-point arithmetic — no floating-point errors for financial calculations.

| Type | Purpose | Signed |
|------|---------|--------|
| `Price` | Market prices, quotes, levels | Yes |
| `Quantity` | Trade sizes, order amounts | No (unsigned) |
| `Money` | Monetary amounts, P&L, balances | Yes (currency-aware) |

All are **immutable**. Arithmetic returns new instances. Precision controls display, not identity.

```python
Price.from_str("1.23456")
Quantity.from_int(100)
Money.from_str("10000 USD")
instrument.make_price(Decimal("1.23456"))
instrument.make_qty(Decimal("100"))
```

## Instrument Types

16 instrument classes: `Equity`, `CurrencyPair`, `FuturesContract`, `FuturesSpread`, `OptionsContract`, `OptionsSpread`, `CryptoFuture`, `CryptoPerpetual`, `CryptoOption`, `PerpetualContract`, `Cfd`, `Commodity`, `IndexInstrument`, `BinaryOption`, `BettingInstrument`, `SyntheticInstrument`.

ID format: `{symbol}.{venue}` — e.g., `ETHUSDT-PERP.BINANCE`, `AAPL.XNAS`, `EUR/USD.IDEALPRO`

Always use `instrument.make_price()` and `instrument.make_qty()` for precision compliance.

## Anti-Patterns

```python
# BAD: Float prices — precision errors
Price(1.23456)

# GOOD: String or Decimal construction
Price.from_str("1.23456")
instrument.make_price(Decimal("1.23456"))

# BAD: Blocking the event loop in live trading
def on_bar(self, bar):
    time.sleep(5)  # blocks everything

# BAD: Using Jupyter notebooks for live trading
# Use proper Python scripts/processes

# BAD: Multiple TradingNode instances in one process

# BAD: Ignoring indicator initialization
def on_bar(self, bar):
    # Always check first:
    if not self.indicators_initialized():
        return

# BAD: Not caching instrument on start
def on_bar(self, bar):
    inst = self.cache.instrument(self.config.instrument_id)  # repeated lookup
```

## Market Making Quick Reference

**Core pattern**: Maintain two-sided quotes around midpoint, adjust for inventory risk via skew.

```python
skew = -(signed_qty / max_size) * skew_factor
bid = mid * (1 - half_spread + skew)
ask = mid * (1 + half_spread + skew)
```

**Spread methods**: Fixed, ATR-based (volatility-adaptive), order book imbalance-driven.

**Avellaneda-Stoikov**: `reservation_price = mid - q * γ * σ² * (T-t)`, optimal spread includes risk aversion and order arrival intensity.

See [market_making.md](references/market_making.md) for full patterns and examples.

## Derivatives Quick Reference

**Mark price**: Fair value for liquidation/PnL, not for matching. Subscribe via `DataType(MarkPriceUpdate)`.

**Funding rate**: Perpetuals only. Positive rate = longs pay shorts. Subscribe via `DataType(FundingRateUpdate)`.

**Instruments**: `CryptoPerpetual` (no expiry, funding), `CryptoFuture` (expiry, basis convergence).

**Circuit breakers**: Subscribe `instrument_status` → handle `MarketStatusAction.HALT` / `RESUME`.

See [derivatives.md](references/derivatives.md) for liquidation mechanics, funding arbitrage, basis trading.

## Reference Navigator

| Topic | File | When to Load |
|-------|------|--------------|
| Backtesting | [backtesting.md](references/backtesting.md) | BacktestEngine, BacktestNode, fill models, venue config |
| Strategies | [strategies.md](references/strategies.md) | Strategy patterns, indicators, advanced order management |
| Adapters | [adapters.md](references/adapters.md) | Custom adapters, venue integrations, InstrumentProvider |
| Rust Adapters | [rust_adapters.md](references/rust_adapters.md) | Rust crate structure, PyO3 bindings, HTTP/WS clients, adapter dev guide |
| Market Making | [market_making.md](references/market_making.md) | MM strategies, inventory skew, spread calculation, Avellaneda-Stoikov |
| Simulation | [simulation.md](references/simulation.md) | SimulatedExchange, custom fill/fee models, matching engines, latency |
| Derivatives | [derivatives.md](references/derivatives.md) | Mark price, funding rates, liquidation, circuit breakers, CryptoPerpetual |
| Data System | [data.md](references/data.md) | DataEngine, data catalog, wranglers, custom data types |
| Execution | [execution.md](references/execution.md) | ExecutionEngine, RiskEngine, ExecAlgorithm, TWAP, contingent orders |
| Live Trading | [live.md](references/live.md) | TradingNode, reconciliation, state persistence |
| Architecture | [architecture.md](references/architecture.md) | Core components, MessageBus, Cache, threading model |
| Order Book | [order_book.md](references/order_book.md) | Order book management, OwnOrderBook, filtered views |
