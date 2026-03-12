---
name: nautilus-crypto-hft
description: >
  NautilusTrader for crypto HFT and market making. Triggers: "nautilus_trader",
  "NautilusTrader", "BacktestEngine", "BacktestNode", "TradingNode",
  "SimulatedExchange", "StrategyConfig", "ExecAlgorithm", "OrderEmulator",
  "DataEngine", "ExecutionEngine", "RiskEngine", "MessageBus", "NautilusKernel",
  "ParquetDataCatalog", "LiveDataClient", "LiveExecutionClient",
  "InstrumentProvider", "OrderBookDelta", "QuoteTick", "TradeTick", "BarType",
  "submit_order", "modify_order", "OmsType", "NETTING", "HEDGING",
  "venue adapter", "Binance adapter", "Bybit adapter", "dYdX adapter",
  "OKX adapter", "Tardis adapter", "Databento adapter", "Rust adapter",
  "PyO3 bindings nautilus", "nautilus crate", "nautilus FFI", "CVec nautilus",
  "maturin nautilus", "RecordFlag F_LAST", "OMS internals", "reconciliation",
  "order book delta processing", "L2 L3 order book", "market making nautilus",
  "HFT order book strategy", "microprice", "adverse selection", "VPIN",
  "breakeven spread", "CryptoPerpetual", "CryptoFuture",
  "funding rate", "mark price", "liquidation", "fill model", "fee model",
  "latency model", "queue position", "custom adapter crypto",
  "OrderList", "submit_order_list", "ContingencyType", "bracket order",
  "set_timer", "set_time_alert", "clock", "timer", "Actor", "ActorConfig",
  "publish_signal", "subscribe_signal", "on_signal", "publish_data",
  "order_factory.bracket", "trailing_stop", "on_market_exit",
  "open interest", "OpenInterest", "BinanceEnrichmentActor", "OpenInterestData",
  "FundingRateUpdate", "BinanceFuturesMarkPriceUpdate", "HttpClient nautilus",
  "queue_for_executor", "enrichment actor".
---

# NautilusTrader — Crypto HFT

High-performance algorithmic trading platform. Hybrid Python/Rust/Cython architecture for backtesting and live deployment. Single-threaded event-driven kernel for determinism.

**Tested against v1.224.0** — all code in this skill is validated by running tests.

## Quick Start: Compact Market Maker

```python
from decimal import Decimal
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import OrderBookDeltas
from nautilus_trader.model.enums import BookType, OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy

class MMConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    trade_size: Decimal
    max_size: Decimal = Decimal("10")
    half_spread: Decimal = Decimal("0.0005")  # must exceed breakeven
    skew_factor: Decimal = Decimal("0.5")

class MM(Strategy):
    def __init__(self, config: MMConfig) -> None:
        super().__init__(config)
        self.instrument = None
        self._bid_id = None
        self._ask_id = None

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        self.subscribe_order_book_deltas(
            self.config.instrument_id, book_type=BookType.L2_MBP,
        )

    def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
        book = self.cache.order_book(self.config.instrument_id)
        if not book.best_bid_price() or not book.best_ask_price():
            return
        bv = float(book.best_bid_size())
        av = float(book.best_ask_size())
        mid = (float(book.best_bid_price()) * av + float(book.best_ask_price()) * bv) / (bv + av)
        self._requote(Decimal(str(mid)))

    def _requote(self, mid: Decimal) -> None:
        positions = self.cache.positions_open(instrument_id=self.config.instrument_id)
        pos = positions[0] if positions else None
        skew = Decimal(0) if pos is None else -(Decimal(str(pos.signed_qty)) / self.config.max_size) * self.config.skew_factor
        bid_px = self.instrument.make_price(mid * (1 - self.config.half_spread + skew))
        ask_px = self.instrument.make_price(mid * (1 + self.config.half_spread + skew))
        qty = self.instrument.make_qty(self.config.trade_size)

        bid_order = self.cache.order(self._bid_id) if self._bid_id else None
        ask_order = self.cache.order(self._ask_id) if self._ask_id else None

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

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)
        self.close_all_positions(self.config.instrument_id)
```

## Architecture

| Component | Role |
|-----------|------|
| `NautilusKernel` | Single-threaded core: lifecycle, clock, event sequencing |
| `MessageBus` | Pub/Sub + Req/Rep message routing across all components |
| `Cache` | In-memory store for instruments, orders, positions, books |
| `DataEngine` | Market data ingestion, buffering (F_LAST rule), distribution |
| `ExecutionEngine` | Order routing, OMS reconciliation, position tracking |
| `RiskEngine` | Pre-trade checks: precision, notional, reduce_only, rate limits |
| `Portfolio` | Real-time aggregated P&L, margin, balances across venues |

**Constraint**: One `TradingNode` / `BacktestNode` per process. Background threads for network I/O communicate via MessageBus channels.

## Strategy Lifecycle

| Method | When |
|--------|------|
| `on_start()` | Subscribe data, cache instrument, register indicators |
| `on_stop()` | Cancel orders, close positions, cleanup |
| `on_resume()` / `on_reset()` | State management between runs |
| `on_save() → dict[str, bytes]` | Persist custom state |
| `on_load(state)` | Restore custom state |

## Subscription Ordering (Critical)

### Correct `on_start()` sequence:

```python
def on_start(self) -> None:
    # 1. Cache instrument FIRST — returns None if not loaded (silent, crashes later)
    self.instrument = self.cache.instrument(self.config.instrument_id)
    if self.instrument is None:
        self.log.error(f"Instrument not found: {self.config.instrument_id}")
        return

    # 2. Register indicators for bar type BEFORE subscribing
    bar_type = BarType.from_str(f"{self.config.instrument_id}-1-MINUTE-LAST-INTERNAL")
    self.register_indicator_for_bars(bar_type, self.ema)

    # 3. Subscribe to data AFTER instrument confirmed and indicators registered
    self.subscribe_bars(bar_type)
    self.subscribe_trade_ticks(self.config.instrument_id)
    self.subscribe_order_book_deltas(self.config.instrument_id, book_type=BookType.L2_MBP)
```

### Silent failures — no error, just 0 data:

| Wrong | What happens |
|-------|-------------|
| `subscribe_quote_ticks()` but only trade data loaded | 0 quotes, no error |
| `subscribe_bars()` EXTERNAL but no bar data loaded | 0 bars, no error |
| `subscribe_trade_ticks(fake_id)` | ERROR log but no exception, 0 data |
| `cache.instrument(wrong_id)` | Returns `None`, crashes on `make_price()` later |
| `subscribe_order_book_deltas()` but only trade data loaded | 0 deltas, no error |

### INTERNAL vs EXTERNAL bars:

| Bar Source | Data Required | Backtest | Live |
|------------|--------------|----------|------|
| `INTERNAL` | Trade ticks (or quote ticks) loaded | Aggregated locally from ticks | Aggregated from subscribed tick stream |
| `EXTERNAL` | Bar data loaded (or venue kline stream) | From `engine.add_data(bars)` | From venue kline WebSocket |

In live: EXTERNAL is 1 bar/min/instrument from venue. INTERNAL aggregates from your tick subscriptions with more flexibility (tick/volume/value bars).

### Indicator warmup — why `indicators_initialized()` matters:

```python
def on_bar(self, bar: Bar) -> None:
    if not self.indicators_initialized():
        return  # CRITICAL — values are WRONG before warmup, not NaN

    # SMA(20) after 5 bars = average of 5 bars (not 20) — silently incorrect
    # Only after 20 bars does SMA(20).initialized become True
```

SMA/EMA/RSI produce **partial values** before warmup — not NaN, not zero, just wrong numbers. Trading on partial indicators produces garbage signals.

## Data Subscriptions — What Actually Works

Subscriptions are adapter-dependent. Strategy has the methods, but not all adapters implement them. Availability varies — check [exchange_adapters.md](references/exchange_adapters.md) for per-venue support.

| Subscription | Typical | Callback | Notes |
|-------------|---------|----------|-------|
| `subscribe_trade_ticks` | **YES** | `on_trade_tick` | aggTrade / publicTrade stream |
| `subscribe_quote_ticks` | **YES** | `on_quote_tick` | BBO bookTicker — highest volume |
| `subscribe_order_book_deltas` | **YES** | `on_order_book_deltas` | L2 incremental + snapshot rebuild |
| `subscribe_mark_prices` | **YES** | `on_mark_price` | includes funding info on some adapters |
| `subscribe_bars` | **YES** | `on_bar` | EXTERNAL kline stream, 1/min/instrument |
| `subscribe_order_book_depth` | **SOME** | `on_order_book_depth` | Not on all adapters — use deltas as fallback |
| `subscribe_funding_rates` | **SOME** | `on_funding_rate` | Not on all adapters — use mark prices or REST |
| `subscribe_index_prices` | **SOME** | `on_index_price` | Not on all adapters |
| `subscribe_instrument_status` | **SOME** | `on_instrument_status` | Not on all adapters |
| `subscribe_data` | **YES** | `on_data` | Custom data via MessageBus (actors, signals) |

### REST-Only Data (OI, Funding, Long/Short)

Some data types are not available via subscription on any adapter — use the adapter's HTTP client directly. See [exchange_adapters.md](references/exchange_adapters.md) for per-venue code examples and endpoints.

## Execution Methods

```python
self.submit_order(order)           # new order to venue
self.modify_order(order, quantity, price, trigger_price)  # amend in-place (preferred)
self.cancel_order(order)           # cancel single
self.cancel_all_orders(instrument_id)  # cancel all for instrument
self.close_position(position)      # market close
self.close_all_positions(instrument_id)
```

## Cache API (Verified)

```python
# Instruments
self.cache.instrument(instrument_id)     # single instrument
self.cache.instruments()                 # all instruments

# Positions — NO position_for_instrument() method
positions = self.cache.positions_open(instrument_id=inst_id)   # list of open
pos = positions[0] if positions else None                       # single (NETTING)
self.cache.positions_closed(instrument_id=inst_id)             # closed list
self.cache.positions(instrument_id=inst_id)                    # all (open + closed)
self.cache.position(position_id)                               # by PositionId (not InstrumentId)

# Orders
self.cache.orders(instrument_id=inst_id)       # all orders
self.cache.orders_open(instrument_id=inst_id)  # open only
self.cache.order(client_order_id)              # single by ID

# Books
book = self.cache.order_book(instrument_id)    # only if subscribed to book data
own_book = self.cache.own_order_book(instrument_id)  # your orders by price level

# Data in cache
self.cache.trade_ticks(instrument_id)   # recent trade ticks
self.cache.quote_ticks(instrument_id)   # recent quote ticks
self.cache.accounts()                   # all accounts
self.cache.bars(bar_type)              # recent bars

# BacktestEngine: use engine.cache directly (NOT engine.trader.cache)
engine.cache.accounts()
engine.cache.positions_open()
```

## Order Book API (Verified)

L2_MBP (market-by-price) is the ceiling for crypto HFT. L3_MBO is **not available** on crypto venues.

```python
book = self.cache.order_book(instrument_id)
best_bid = book.best_bid_price()
best_ask = book.best_ask_price()
spread = float(book.spread())
mid = float(book.midpoint())
bids = book.bids()  # list[BookLevel] — each has: price, size, side, exposure
asks = book.asks()

# Execution cost
avg_px = book.get_avg_px_for_quantity(OrderSide.BUY, Quantity.from_str("1.0"))
worst_px = book.get_worst_px_for_quantity(OrderSide.BUY, Quantity.from_str("1.0"))
qty_at_price = book.get_quantity_for_price(OrderSide.BUY, Price.from_str("68000"))
```

**Does NOT exist**: `book.filtered_view()`, `book.get_avg_px_qty_for_exposure()`, `level.count`. Use `book.update_count` (not `book.count`)

**F_LAST rule**: Every delta batch must end with `RecordFlag.F_LAST`. Without it, DataEngine buffers indefinitely and subscribers starve.

## Position & PnL (Verified)

```python
pos.side                  # PositionSide.LONG / SHORT
pos.quantity              # absolute quantity
pos.signed_qty            # positive=long, negative=short
pos.avg_px_open           # average entry price
pos.avg_px_close          # average exit price (after close)
pos.unrealized_pnl(last_price)  # from current price vs entry
pos.realized_pnl          # computed on close
pos.commissions()          # list[Money] accumulated from fills
pos.is_open / pos.is_closed
pos.entry                 # OrderSide of opening trade
pos.instrument_id
pos.strategy_id
```

## Portfolio API (Verified)

```python
account = self.portfolio.account(Venue("BINANCE"))
account.balance_total(Currency.from_str("USDT"))
account.balance_free(Currency.from_str("USDT"))
account.balance_locked(Currency.from_str("USDT"))
self.portfolio.is_flat(instrument_id)
self.portfolio.net_position(instrument_id)
self.portfolio.unrealized_pnls(Venue("BINANCE"))
```

## Bracket Orders (Verified)

`order_factory.bracket()` creates an `OrderList` with entry + SL + TP, properly linked:

```python
bracket = self.order_factory.bracket(
    instrument_id=inst.id,
    order_side=OrderSide.BUY,
    quantity=inst.make_qty(Decimal("0.01")),
    tp_price=inst.make_price(Decimal("440.00")),         # take-profit limit
    sl_trigger_price=inst.make_price(Decimal("415.00")), # stop-loss trigger
    # Defaults: entry=MARKET, SL=STOP_MARKET, TP=LIMIT(post_only=True)
    # Contingency: entry=OTO→children, SL↔TP=OUO (one-updates-other)
)
self.submit_order_list(bracket)  # submits all 3 atomically
# bracket.orders[0] = entry (tags=['ENTRY'])
# bracket.orders[1] = stop-loss (tags=['STOP_LOSS'])
# bracket.orders[2] = take-profit (tags=['TAKE_PROFIT'])
```

**Venue requirement**: `support_contingent_orders=True` on backtest venue config. On live venues, OTO/OUO support varies.

Full `bracket()` signature supports: `entry_order_type`, `entry_price`, `tp_order_type`, `sl_order_type`, `tp_trailing_offset`, `sl_trailing_offset`, `emulation_trigger`, and more. See [execution_and_oms.md](references/execution_and_oms.md).

## OMS Quick Reference

- **NETTING**: One position per instrument. All fills aggregate. Standard for crypto perps.
  `BUY 1.0 → LONG 1.0 → BUY 0.5 → LONG 1.5 → SELL 2.0 → SHORT 0.5`
- **HEDGING**: Multiple positions per instrument. Isolated P&L per trade.

Strategy `oms_type` can differ from venue. ExecutionEngine reconciles via virtual position IDs.

## Indicators (Verified)

```python
from nautilus_trader.indicators import (
    ExponentialMovingAverage,    # EMA(period)
    SimpleMovingAverage,         # SMA(period)
    RelativeStrengthIndex,       # RSI(period) — value in [0, 1] not [0, 100]
    BollingerBands,              # BB(period, k) — k is MANDATORY (e.g. 2.0)
    MovingAverageConvergenceDivergence,  # MACD(fast, slow, ma_type) — NOT (fast, slow, signal)
    AverageTrueRange,            # ATR(period)
    MovingAverageType,           # EXPONENTIAL, SIMPLE, etc.
)

# Registration: auto-update indicators on each bar
bar_type = BarType.from_str(f"{instrument.id}-1-MINUTE-LAST-INTERNAL")
self.register_indicator_for_bars(bar_type, self.ema)
self.subscribe_bars(bar_type)

# Guard: indicators_initialized() returns True only when ALL registered indicators ready
def on_bar(self, bar: Bar) -> None:
    if not self.indicators_initialized():
        return  # warmup period (e.g. 20 bars for SMA(20))
```

## Signals (Native API)

`publish_signal(name="momentum", value=42.5, ts_event=tick.ts_event)` → auto-generates `SignalMomentum` class. Subscribe: `subscribe_signal(name="momentum")` or `subscribe_signal()` for all. Handler: `on_signal(self, signal)` — `signal.value` is the value, `type(signal).__name__` for routing. Values must be int/float/str only (dict → KeyError). For structured data, use `Data` subclass + `publish_data` (see [actors_and_signals.md](references/actors_and_signals.md)).

## Actors (Verified)

`from nautilus_trader.common.actor import Actor` (NOT `trading.actor`). Actors are Strategies without order management — same lifecycle, data subscriptions, clock/timers. Use to separate signal computation from trading logic. Registration: `engine.add_actor()` for backtest, `node.trader.add_actor()` for live.

Custom data: `Data` subclass + `publish_data`/`subscribe_data`, `queue_for_executor()` for async HTTP. See [actors_and_signals.md](references/actors_and_signals.md) and [binance_enrichment_actor.py](examples/binance_enrichment_actor.py).

## ParquetDataCatalog (Verified)

```python
from nautilus_trader.persistence.catalog import ParquetDataCatalog

catalog = ParquetDataCatalog("/path/to/catalog")
catalog.write_data([instrument])
catalog.write_data(trade_ticks)    # MUST be sorted by ts_init

# Read back
instruments = catalog.instruments()
ticks = catalog.trade_ticks(instrument_ids=["ETHUSDT.BINANCE"])
types = catalog.list_data_types()  # NOT .data_types()

# Live cache data is NOT time-sorted — sort before writing:
trades = list(cache.trade_ticks(inst_id))
trades.sort(key=lambda x: x.ts_init)
catalog.write_data(trades)
```

## Live TradingNode

Each exchange adapter has its own config classes, factory, and auth requirements. Example (Binance):

```python
from nautilus_trader.adapters.binance import (
    BINANCE, BinanceAccountType, BinanceDataClientConfig, BinanceExecClientConfig,
    BinanceLiveDataClientFactory, BinanceLiveExecClientFactory,
)
from nautilus_trader.adapters.binance.common.enums import BinanceKeyType

node = TradingNode(config=TradingNodeConfig(
    timeout_connection=30,
    data_clients={BINANCE: BinanceDataClientConfig(
        api_key=key, api_secret=secret, key_type=BinanceKeyType.ED25519,
        account_type=BinanceAccountType.USDT_FUTURES,
        instrument_provider=InstrumentProviderConfig(
            load_all=False, load_ids=frozenset({InstrumentId.from_str("BTCUSDT-PERP.BINANCE")}),
        ),
    )},
    exec_clients={BINANCE: BinanceExecClientConfig(
        api_key=key, api_secret=secret, key_type=BinanceKeyType.ED25519,
        account_type=BinanceAccountType.USDT_FUTURES,
    )},
))
node.add_data_client_factory(BINANCE, BinanceLiveDataClientFactory)
node.add_exec_client_factory(BINANCE, BinanceLiveExecClientFactory)
node.trader.add_strategy(my_strategy)
node.build()
node.run()  # blocks until SIGINT
```

Auth varies by exchange (Binance=Ed25519, Bybit/OKX=HMAC, dYdX=wallet keys). Min notional/qty constraints loaded at runtime via InstrumentProvider — check `instrument.min_notional`. See [exchange_adapters.md](references/exchange_adapters.md) for per-venue config and [live_trading.md](references/live_trading.md) for full setup.

## Mental Model — How It Actually Works

**Event flow**: Venue WS → DataClient → DataEngine (buffers until F_LAST) → MessageBus → Strategy callbacks. Single-threaded — every callback must return fast. Never `time.sleep()`.

**Clock**: `self.clock.set_timer("name", interval=timedelta(seconds=10), callback=handler)` for recurring, `self.clock.set_time_alert("name", alert_time, callback=handler)` for one-shot. `cancel_timer("name")` to stop. `utc_now()` returns pandas Timestamp, `timestamp_ns()` returns int. No `on_timer()` method exists. See [clock_and_timers.md](references/clock_and_timers.md).

**Instruments**: `load_ids=frozenset({...})` for fast startup. `load_all=True` takes minutes. Use adapter-specific enums for account types (e.g. `BinanceAccountType.USDT_FUTURES`) — strings cause AttributeError.

**Books**: Only populated if you subscribe to book data. `cache.order_book()` returns None otherwise. Book rebuilds via REST snapshot + incremental deltas. Spreads vary by instrument and venue.

**Fills**: `fills > orders` is normal — single order can produce multiple partial fills. CASH account + `frozen_account=False` silently produces 0 fills if balance insufficient. Use `AccountType.MARGIN` for derivatives.

**BacktestEngine**: Use `engine.cache` directly (not `engine.trader.cache`). Call `BacktestEngineConfig` from `nautilus_trader.backtest.engine` (not `backtest.config`). `Currency.from_str("USDT")` not bare `USDT` constant. `base_currency=None` for multi-currency accounts.

**BacktestNode**: Must call `node.build()` before `get_engine()` or it returns None.

**SimulatedExchange**: `FillModel(prob_fill_on_limit=0.3, prob_slippage=0.5, random_seed=42)` — no `prob_fill_on_stop` param. `LatencyModel` takes nanoseconds for all params.

## Things That Don't Exist

These are common hallucinations. None exist in v1.224.0:

| Hallucination | Reality |
|--------------|---------|
| `cache.position_for_instrument(id)` | `cache.positions_open(instrument_id=id)` returns list |
| `engine.trader.cache` | `engine.cache` directly on BacktestEngine |
| `book.filtered_view()` | Implement manually with `cache.own_order_book()` |
| `book.get_avg_px_qty_for_exposure()` | Use `get_avg_px_for_quantity()`, `get_quantity_for_price()` |
| `book.count` | Use `book.update_count` instead |
| `level.count` | BookLevel has: price, size, side, exposure, orders |
| `GenericDataWrangler` | Only: TradeTickDataWrangler, QuoteTickDataWrangler, OrderBookDeltaDataWrangler, BarDataWrangler |
| `catalog.data_types()` | `catalog.list_data_types()` |
| `BacktestEngineConfig` from `backtest.config` | from `nautilus_trader.backtest.engine` |
| `FillModel(prob_fill_on_stop=...)` | Param doesn't exist — only prob_fill_on_limit, prob_slippage, random_seed |
| `BookOrder(price=, size=, side=)` | Missing `order_id`: `BookOrder(side=, price=, size=, order_id=0)` |
| `get_avg_px_for_quantity(side, qty)` | Args reversed: `get_avg_px_for_quantity(quantity, order_side)` |
| `LoggingConfig(log_file_path=)` | Use `log_directory=` instead |
| `cache.orders_filled()` | Use `cache.orders_closed()` |
| `pos.signed_qty / Decimal(...)` | TypeError: `pos.signed_qty` returns float — wrap: `Decimal(str(pos.signed_qty))` |
| `from nautilus_trader.trading.actor` | `from nautilus_trader.common.actor import Actor` |
| `from nautilus_trader.indicators.ema` | `from nautilus_trader.indicators import ExponentialMovingAverage` |
| `BollingerBands(20)` | `BollingerBands(20, 2.0)` — k is mandatory |
| `MACD(12, 26, 9)` | 3rd param is `MovingAverageType`, not signal_period |
| `TestDataProvider.audusd_ticks()` | `dp.read_csv_ticks("binance/ethusdt-trades.csv")` |
| `subscribe_funding_rates()` on some adapters | NotImplementedError — use enrichment Actor pattern with REST polling |
| OI WebSocket stream on some exchanges | May not exist — poll REST on timer, check per-venue availability |
| `publish_signal(value=dict(...))` | KeyError — signal values must be int, float, or str only |
| HMAC keys for exec WS API (some exchanges) | Rejected — check adapter docs for required auth method |
| Encrypted Ed25519 private key | Fails — must be unencrypted PKCS#8 |
| `subscribe_order_book_depth()` on some adapters | NotImplementedError — use `subscribe_order_book_deltas()` |
| `subscribe_instrument_status()` on some adapters | NotImplementedError — monitor via REST or external feeds |
| `on_timer()` as Strategy callback | Use `clock.set_timer(callback=handler)` |
| `order.order_side` | `order.side` — events use `event.order_side`, orders use `order.side` |
| `is_bracket` as property | `bracket.is_bracket()` is a method, not property |
| Manual OrderList for brackets | Use `order_factory.bracket(...)` — built-in factory method |
| Subscribing produces an error if data isn't available | Silent: 0 callbacks, no exception, just ERROR log |
| Indicator values are NaN/zero before `initialized` | Partial values (e.g. SMA(20) after 5 bars = avg of 5) — wrong, not missing |
| `request_bars(bar_type)` with one arg | Requires `start` datetime: `request_bars(bar_type, start=datetime(...))` |

## References

Load these for detailed coverage of specific topics:

- **Trading**: [market_making.md](references/market_making.md), [execution_and_oms.md](references/execution_and_oms.md), [derivatives.md](references/derivatives.md)
- **Data**: [order_book.md](references/order_book.md), [microstructure.md](references/microstructure.md), [actors_and_signals.md](references/actors_and_signals.md)
- **Infrastructure**: [live_trading.md](references/live_trading.md), [backtesting_and_simulation.md](references/backtesting_and_simulation.md), [clock_and_timers.md](references/clock_and_timers.md)
- **Venues**: [exchange_adapters.md](references/exchange_adapters.md), [operational_patterns.md](references/operational_patterns.md)
- **Development**: [adapter_development_python.md](references/adapter_development_python.md), [adapter_development_rust.md](references/adapter_development_rust.md), [dev_environment.md](references/dev_environment.md)

## Runnable Examples

All in `examples/`: [market_maker_backtest.py](examples/market_maker_backtest.py) (L2 MM), [spread_capture_live.py](examples/spread_capture_live.py) (live MM), [custom_adapter_minimal.py](examples/custom_adapter_minimal.py) (adapter skeleton), [ema_crossover_backtest.py](examples/ema_crossover_backtest.py), [bracket_order_backtest.py](examples/bracket_order_backtest.py), [signal_pipeline_backtest.py](examples/signal_pipeline_backtest.py), [binance_enrichment_actor.py](examples/binance_enrichment_actor.py) (OI+funding).
