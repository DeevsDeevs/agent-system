---
name: nautilus-trader
description: >
  NautilusTrader algorithmic trading platform — backtesting, live deployment, exchange adapters.
  Use when code involves nautilus_trader imports, Strategy/Actor patterns, BacktestEngine,
  TradingNode, order management, or exchange adapters (Binance, Bybit, OKX, dYdX, Deribit,
  Hyperliquid, Kraken, Polymarket, Betfair, Interactive Brokers).
---

# NautilusTrader

High-performance algorithmic trading platform. Hybrid Python/Rust/Cython architecture for backtesting and live deployment. Single-threaded event-driven kernel for determinism.

**Tested against v1.224.0** — all code validated by running tests.

## Architecture

| Component | Role |
|-----------|------|
| `NautilusKernel` | Single-threaded core: lifecycle, clock, event sequencing. Supports 16+ instrument types: CryptoPerpetual, CryptoFuture, CryptoOption, CurrencyPair, Equity, FuturesContract, FuturesSpread, OptionContract, OptionSpread, BinaryOption, BettingInstrument, Cfd, Commodity, IndexInstrument, PerpetualContract, SyntheticInstrument |
| `MessageBus` | Pub/Sub + Req/Rep message routing across all components |
| `Cache` | In-memory store for instruments, orders, positions, books |
| `DataEngine` | Market data ingestion, buffering (F_LAST rule), distribution |
| `ExecutionEngine` | Order routing, OMS reconciliation, position tracking |
| `RiskEngine` | Pre-trade checks: precision, notional, reduce_only, rate limits |
| `Portfolio` | Real-time aggregated P&L, margin, balances across venues |

One `TradingNode` / `BacktestNode` per process. Background threads for I/O via MessageBus.

## Strategy Pattern

```python
from decimal import Decimal
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import OrderBookDeltas
from nautilus_trader.model.enums import BookType, OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy

class MyConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    trade_size: Decimal = Decimal("0.01")

class MyStrategy(Strategy):
    def __init__(self, config: MyConfig) -> None:
        super().__init__(config)
        self.instrument = None

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if not self.instrument:
            self.log.error(f"Instrument not found: {self.config.instrument_id}")
            return
        self.subscribe_order_book_deltas(
            self.config.instrument_id, book_type=BookType.L2_MBP,
        )

    def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
        book = self.cache.order_book(self.config.instrument_id)
        if not book.best_bid_price():
            return
        mid = float(book.midpoint())
        # Trading logic here

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)
        self.close_all_positions(self.config.instrument_id)
```

Full market maker with skew: [market_maker_backtest.py](examples/market_maker_backtest.py). All examples in `examples/`.

### Strategy Lifecycle

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

    # 2. Register indicators BEFORE subscribing
    bar_type = BarType.from_str(f"{self.config.instrument_id}-1-MINUTE-LAST-INTERNAL")
    self.register_indicator_for_bars(bar_type, self.ema)

    # 3. Subscribe AFTER instrument + indicators ready
    self.subscribe_bars(bar_type)
    self.subscribe_order_book_deltas(self.config.instrument_id, book_type=BookType.L2_MBP)
```

### Silent failures — no error, just 0 data:

| Wrong | What happens |
|-------|-------------|
| `subscribe_quote_ticks()` but only trade data loaded | 0 quotes, no error |
| `subscribe_bars()` EXTERNAL but no bar data loaded | 0 bars, no error |
| `cache.instrument(wrong_id)` | Returns `None`, crashes on `make_price()` later |
| Wrong subscription for loaded data type | 0 callbacks, no exception |

### INTERNAL vs EXTERNAL bars:

| Bar Source | Live | Backtest |
|------------|------|----------|
| `INTERNAL` | Aggregated from tick subscriptions | From `engine.add_data(ticks)` |
| `EXTERNAL` | Venue kline WebSocket (1/min) | From `engine.add_data(bars)` |

### Indicator warmup:

```python
def on_bar(self, bar: Bar) -> None:
    if not self.indicators_initialized():
        return  # CRITICAL — values are WRONG before warmup, not NaN
```

SMA/EMA/RSI produce **partial values** before warmup — not NaN, not zero, just wrong numbers. See [backtesting_and_simulation.md](references/backtesting_and_simulation.md) for indicator imports and registration.

## Data Subscriptions

Availability varies by adapter — check [exchange_adapters.md](references/exchange_adapters.md).

| Subscription | Typical | Callback | Notes |
|-------------|---------|----------|-------|
| `subscribe_trade_ticks` | **YES** | `on_trade_tick` | aggTrade / publicTrade |
| `subscribe_quote_ticks` | **YES** | `on_quote_tick` | BBO bookTicker |
| `subscribe_order_book_deltas` | **YES** | `on_order_book_deltas` | L2 incremental |
| `subscribe_mark_prices` | **YES** | `on_mark_price` | includes funding on some adapters |
| `subscribe_bars` | **YES** | `on_bar` | EXTERNAL kline |
| `subscribe_order_book_depth` | **SOME** | `on_order_book_depth` | Use deltas as fallback |
| `subscribe_funding_rates` | **SOME** | `on_funding_rate` | Use mark prices or REST |
| `subscribe_data` | **YES** | `on_data` | Custom data via MessageBus |

**Missing subscriptions?** If `NotImplementedError` but data is critical:
1. **Build an Actor** that polls REST on a timer — see [binance_enrichment_actor.py](examples/binance_enrichment_actor.py)
2. **Adjust strategy** to use alternatives (e.g. mark prices include funding on some adapters)

REST-only data (OI, funding, long/short) — use adapter HTTP client. See [exchange_adapters.md](references/exchange_adapters.md).

## Execution & OMS

```python
self.submit_order(order)           # new order
self.modify_order(order, quantity, price, trigger_price)  # amend in-place
self.cancel_order(order)           # cancel single
self.cancel_all_orders(instrument_id)
self.close_position(position)      # market close
self.close_all_positions(instrument_id)
```

**`modify_order`** not supported everywhere — check [exchange_adapters.md](references/exchange_adapters.md) support matrix. Use cancel + new order as fallback.

**OMS**: NETTING = one position per instrument (standard crypto). HEDGING = multiple per instrument.
`BUY 1.0 → LONG 1.0 → BUY 0.5 → LONG 1.5 → SELL 2.0 → SHORT 0.5`

Bracket orders: `order_factory.bracket(instrument_id, order_side, quantity, tp_price, sl_trigger_price)` → `submit_order_list(bracket)`. See [execution_and_oms.md](references/execution_and_oms.md).

## Verified API

### Cache

```python
self.cache.instrument(instrument_id)                    # None if not loaded
self.cache.positions_open(instrument_id=inst_id)        # list — NO position_for_instrument()
self.cache.orders_open(instrument_id=inst_id)           # list
self.cache.order(client_order_id)                       # by ClientOrderId
self.cache.order_book(instrument_id)                    # None if not subscribed
self.cache.quote_ticks(instrument_id)                   # recent quotes
self.cache.trade_ticks(instrument_id)                   # recent trades
self.cache.bars(bar_type)                               # recent bars
# BacktestEngine: engine.cache (NOT engine.trader.cache)
```

### Order Book

L2_MBP is the ceiling for crypto. L3_MBO not available on crypto venues.

```python
book = self.cache.order_book(instrument_id)
book.best_bid_price() / book.best_ask_price() / book.spread() / book.midpoint()
book.bids() / book.asks()                               # list[BookLevel]: price, size, side, exposure
book.get_avg_px_for_quantity(OrderSide.BUY, qty)         # execution cost
book.get_quantity_for_price(OrderSide.BUY, price)        # depth query
# Does NOT exist: book.filtered_view(), get_avg_px_qty_for_exposure(), level.count
```

**F_LAST rule**: Every delta batch must end with `RecordFlag.F_LAST` or DataEngine buffers indefinitely.

### Position & Portfolio

```python
pos.side / pos.quantity / pos.signed_qty                # signed_qty: float, positive=long
pos.avg_px_open / pos.unrealized_pnl(last_price) / pos.realized_pnl
pos.commissions()                                        # list[Money]

account = self.portfolio.account(Venue("BINANCE"))
account.balance_total(Currency.from_str("USDT"))
account.balance_free(Currency.from_str("USDT"))
self.portfolio.net_position(instrument_id)
```

## Mental Model

**Event flow**: Venue WS → DataClient → DataEngine (buffers until F_LAST) → MessageBus → Strategy callbacks. Single-threaded — every callback must return fast. Never `time.sleep()`.

**Clock**: `set_timer("name", interval=timedelta(...), callback=fn)` for recurring, `set_time_alert("name", time, callback=fn)` for one-shot. No `on_timer()` method. See [clock_and_timers.md](references/clock_and_timers.md).

**Instruments**: `load_ids=frozenset({...})` for fast startup. `load_all=True` takes minutes. Use adapter-specific enums for account types.

**Fills**: `fills > orders` is normal (partials). CASH + `frozen_account=False` = 0 fills if insufficient balance. Use `AccountType.MARGIN` for derivatives.

**BacktestEngine**: `engine.cache` (not `engine.trader.cache`). `BacktestEngineConfig` from `nautilus_trader.backtest.engine`. `Currency.from_str("USDT")` not bare constant. `base_currency=None` for multi-currency. Two venue APIs: low-level `engine.add_venue(venue=Venue("X"), oms_type=OmsType.NETTING, account_type=AccountType.MARGIN, starting_balances=[Money...])` vs high-level `BacktestRunConfig(venues=[BacktestVenueConfig(...)])`.

**SimulatedExchange**: `FillModel(prob_fill_on_limit=0.3, prob_slippage=0.5, random_seed=42)` — no `prob_fill_on_stop`. `LatencyModel` takes nanoseconds.

**Actors**: `from nautilus_trader.common.actor import Actor` (NOT `trading.actor`). Strategies without order management. Use for signal computation, REST polling, enrichment. See [actors_and_signals.md](references/actors_and_signals.md).

**Signals**: `publish_signal(name="x", value=42.5, ts_event=...)` — values must be int/float/str (dict → KeyError). For structured data use `Data` subclass + `publish_data`. See [actors_and_signals.md](references/actors_and_signals.md).

**Greeks**: `GreeksCalculator(cache, clock)` — 2 args only. Uses `cache.price(id, PriceType.MID)` internally. BS functions via `from nautilus_trader.core.nautilus_pyo3 import black_scholes_greeks`. Cache methods: `cache.greeks()`, `cache.add_greeks()`, `cache.yield_curve()`, `cache.index_price()`. See [options_and_greeks.md](references/options_and_greeks.md).

**Adapter configs**: All are msgspec Structs — enumerate fields via `cls.__struct_fields__`. Config class naming: `BinanceDataClientConfig`, `BybitDataClientConfig`, `DeribitDataClientConfig`, `DydxDataClientConfig` (not DYDX), `KrakenDataClientConfig`, `OKXDataClientConfig`, `HyperliquidDataClientConfig`. Optional deps: Polymarket (`py_clob_client`), Betfair (`betfair_parser`), IB (`ibapi`).

**Cython vs pyo3**: Most instrument types have both Cython and pyo3 (Rust) implementations. Cython versions have slightly different constructor signatures (e.g., Equity lacks `max_price`/`min_price`, FuturesContract lacks `size_precision`). Use `TestInstrumentProvider` (Cython) or `TestInstrumentProviderPyo3` for test fixtures. `legs()` method works on Cython instruments but not pyo3.

## Common Hallucinations

These do NOT exist in v1.224.0:

| Hallucination | Reality |
|--------------|---------|
| `cache.position_for_instrument(id)` | `cache.positions_open(instrument_id=id)` returns list |
| `engine.trader.cache` | `engine.cache` directly |
| `book.filtered_view()` | Use `cache.own_order_book()` |
| `book.get_avg_px_qty_for_exposure()` | Use `get_avg_px_for_quantity()` + `get_quantity_for_price()` |
| `level.count` / `book.count` | `book.update_count` |
| `GenericDataWrangler` | TradeTickDataWrangler, QuoteTickDataWrangler, OrderBookDeltaDataWrangler, BarDataWrangler |
| `catalog.data_types()` | `catalog.list_data_types()` |
| `BacktestEngineConfig` from `backtest.config` | from `nautilus_trader.backtest.engine` |
| `FillModel(prob_fill_on_stop=...)` | Only: prob_fill_on_limit, prob_slippage, random_seed |
| `BookOrder(price=, size=, side=)` | Missing `order_id`: `BookOrder(side=, price=, size=, order_id=0)` |
| `LoggingConfig(log_file_path=)` | `log_directory=` |
| `cache.orders_filled()` | `cache.orders_closed()` |
| `pos.signed_qty / Decimal(...)` | TypeError: returns float — `Decimal(str(pos.signed_qty))` |
| `from nautilus_trader.trading.actor` | `from nautilus_trader.common.actor import Actor` |
| `from nautilus_trader.indicators.ema` | `from nautilus_trader.indicators import ExponentialMovingAverage` |
| `BollingerBands(20)` | `BollingerBands(20, 2.0)` — k mandatory |
| `MACD(12, 26, 9)` | 3rd param is `MovingAverageType`, not signal_period |
| `publish_signal(value=dict(...))` | KeyError — values must be int, float, or str |
| Encrypted Ed25519 private key | Must be unencrypted PKCS#8 |
| `on_timer()` as callback | `clock.set_timer(callback=handler)` |
| `order.order_side` | `order.side` — events use `event.order_side` |
| `request_bars(bar_type)` one arg | Requires `start`: `request_bars(bar_type, start=datetime(...))` |
| `subscribe_option_greeks()` | Does not exist — use `GreeksCalculator` manually |
| `subscribe_option_chain()` | Does not exist — load via `InstrumentProviderConfig` |
| `GreeksCalculator(cache, clock, logger)` | Only 2 args: `GreeksCalculator(cache, clock)` |
| `formula="(c0 - c1)"` in SyntheticInstrument | Use instrument ID values: `formula="A.X - B.X"` |
| `SyntheticInstrument(sym, prec, comps, formula)` | 6 required args — also needs `ts_event`, `ts_init` |
| `DydxOraclePrice` custom data type | Does not exist in v1.224.0 |
| `from nautilus_pyo3 import black_scholes_greeks` | `from nautilus_trader.core.nautilus_pyo3 import black_scholes_greeks` |
| `from nautilus_trader.common.clock import TestClock` | Use `from nautilus_trader.common.component import LiveClock` |
| `from nautilus_trader.common.config import CacheConfig` | `from nautilus_trader.cache.config import CacheConfig` |
| `Equity(..., max_price=, min_price=)` | Cython Equity has no max_price/min_price params |
| `FuturesContract(..., size_precision=, size_increment=)` | Cython FuturesContract has no size_precision/size_increment — hardcoded to 0/1 |
| `BacktestEngine.add_venue(venue=BacktestVenueConfig(...))` | Takes positional args: `add_venue(venue=Venue, oms_type=, account_type=, starting_balances=)`. `BacktestVenueConfig` is for `BacktestRunConfig` only |
| `DYDXDataClientConfig` (uppercase) | `DydxDataClientConfig` (mixed case) |

## References

Detailed coverage in supporting files:

- **Trading**: [market_making.md](references/market_making.md), [execution_and_oms.md](references/execution_and_oms.md), [derivatives.md](references/derivatives.md)
- **Options & Greeks**: [options_and_greeks.md](references/options_and_greeks.md) — CryptoOption, OptionContract, OptionSpread, BinaryOption, GreeksCalculator, Black-Scholes
- **Prediction & Betting**: [prediction_and_betting.md](references/prediction_and_betting.md) — Polymarket (BinaryOption), Betfair (BettingInstrument)
- **DEX & On-Chain**: [dex_and_onchain.md](references/dex_and_onchain.md) — Hyperliquid, dYdX v4 supplements
- **Traditional Finance**: [traditional_finance.md](references/traditional_finance.md) — Equity, FuturesContract, Interactive Brokers
- **Synthetic**: [synthetic_instruments.md](references/synthetic_instruments.md) — SyntheticInstrument formula-based derived instruments
- **Data**: [order_book.md](references/order_book.md), [microstructure.md](references/microstructure.md), [actors_and_signals.md](references/actors_and_signals.md)
- **Infrastructure**: [live_trading.md](references/live_trading.md), [backtesting_and_simulation.md](references/backtesting_and_simulation.md), [clock_and_timers.md](references/clock_and_timers.md)
- **Venues**: [exchange_adapters.md](references/exchange_adapters.md) (12 adapters), [operational_patterns.md](references/operational_patterns.md)
- **Development**: [adapter_development_python.md](references/adapter_development_python.md), [adapter_development_rust.md](references/adapter_development_rust.md), [dev_environment.md](references/dev_environment.md)

## Examples

Working code: [market_maker_backtest.py](examples/market_maker_backtest.py) (L2 MM with skew), [ema_crossover_backtest.py](examples/ema_crossover_backtest.py), [bracket_order_backtest.py](examples/bracket_order_backtest.py), [signal_pipeline_backtest.py](examples/signal_pipeline_backtest.py), [binance_enrichment_actor.py](examples/binance_enrichment_actor.py) (OI+funding), [spread_capture_live.py](examples/spread_capture_live.py) (live), [custom_adapter_minimal.py](examples/custom_adapter_minimal.py), [deribit_option_greeks_backtest.py](examples/deribit_option_greeks_backtest.py) (options + greeks), [polymarket_binary_backtest.py](examples/polymarket_binary_backtest.py) (prediction markets).
