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
| `NautilusKernel` | Single-threaded core: lifecycle, clock, event sequencing. 16+ instrument types. |
| `MessageBus` | Pub/Sub + Req/Rep routing across all components |
| `Cache` | In-memory store: instruments, orders, positions, books |
| `DataEngine` | Data ingestion, buffering (F_LAST rule), distribution |
| `ExecutionEngine` | Order routing, OMS reconciliation, position tracking |
| `RiskEngine` | Pre-trade checks: precision, notional, reduce_only, rate limits |
| `Portfolio` | Aggregated P&L, margin, balances across venues |

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
        # Trading logic here

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)
        self.close_all_positions(self.config.instrument_id)
```

Full examples: [ema_crossover_backtest.py](examples/ema_crossover_backtest.py), [market_maker_backtest.py](examples/market_maker_backtest.py) (L2 MM with skew). All examples in `examples/`.

### Strategy Lifecycle

| Method | When |
|--------|------|
| `on_start()` | Subscribe data, cache instrument, register indicators |
| `on_stop()` | Cancel orders, close positions, cleanup |
| `on_resume()` / `on_reset()` | State management between runs |
| `on_save() → dict[str, bytes]` | Persist custom state |
| `on_load(state)` | Restore custom state |

## Subscription Ordering (Critical)

### Live node config — REQUIRED before any strategy code runs:

```python
instrument_provider=InstrumentProviderConfig(
    load_ids=frozenset({"BTCUSDT-PERP.BINANCE"}),  # REQUIRED — no instruments = 0 data, no error
)
```

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
| No `load_ids` / `load_all` in `InstrumentProviderConfig` | 0 instruments in cache, all subscriptions produce 0 data |
| Wrong subscription for loaded data type | 0 callbacks, no exception |

### INTERNAL vs EXTERNAL bars:

| Bar Source | Live | Backtest |
|------------|------|----------|
| `INTERNAL` | Aggregated from tick subscriptions | From `engine.add_data(ticks)` |
| `EXTERNAL` | Venue kline WebSocket (1/min) | From `engine.add_data(bars)` |

### Indicator warmup:

Indicators produce **partial values** before warmup (not NaN) — guard with `indicators_initialized()`. See [backtesting.md](references/backtesting.md).

Data availability varies by adapter — check [exchange_adapters.md](references/exchange_adapters.md). For missing data, build an Actor that polls REST — see [binance_enrichment_actor.py](examples/binance_enrichment_actor.py).

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

Bracket orders: `order_factory.bracket(instrument_id, order_side, quantity, tp_price, sl_trigger_price)` → `submit_order_list(bracket)`. See [execution.md](references/execution.md).

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
book.bids() / book.asks()                               # list[BookLevel]
book.get_avg_px_for_quantity(OrderSide.BUY, qty)         # execution cost
# Does NOT exist: book.filtered_view(), get_avg_px_qty_for_exposure(), level.count
```

> Full book API: [order_book.md](references/order_book.md)

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

**Clock**: `set_timer("name", interval=timedelta(...), callback=fn)` for recurring, `set_time_alert("name", time, callback=fn)` for one-shot. No `on_timer()` method. See [operations.md](references/operations.md).

**Data-only node**: Omit `exec_clients`. Harmless WARN at startup, `channel closed` errors at shutdown (~10s) — known race condition.

**Instruments**: `load_ids=frozenset({"BTCUSDT-PERP.BINANCE"})` REQUIRED in `InstrumentProviderConfig`. Full `"SYMBOL.VENUE"` strings. `load_all=True` works but slow.

**Fills**: `fills > orders` normal (partials). CASH + `frozen_account=False` = 0 fills if insufficient balance. Use MARGIN for derivatives.

**BacktestEngine**: `engine.cache` (not `engine.trader.cache`). `BacktestEngineConfig` from `nautilus_trader.backtest.engine`. `Currency.from_str("USDT")`. `base_currency=None` for multi-currency.

**Actors**: `from nautilus_trader.common.actor import Actor`. For signal computation, REST polling, enrichment.

**Signals**: `publish_signal(name="x", value=42.5, ts_event=...)` — values must be int/float/str. For structured data use `Data` subclass + `publish_data`.

**Greeks**: `GreeksCalculator(cache, clock)` — 2 args only. BS: `from nautilus_trader.core.nautilus_pyo3 import black_scholes_greeks`.

**Adapter configs**: msgspec Structs — enumerate via `cls.__struct_fields__`. Naming: `BinanceDataClientConfig`, `BybitDataClientConfig`, `DydxDataClientConfig` (not DYDX).

**Cython vs pyo3**: Both exist for most instruments. Cython has different constructor signatures (Equity lacks `max_price`/`min_price`). Use `TestInstrumentProvider` (Cython) or `TestInstrumentProviderPyo3`.

## Common Hallucinations

These do NOT exist in v1.224.0:

| Hallucination | Reality |
|--------------|---------|
| `cache.position_for_instrument(id)` | `cache.positions_open(instrument_id=id)` returns list |
| `engine.trader.cache` | `engine.cache` directly |
| `book.filtered_view()` / `get_avg_px_qty_for_exposure()` / `level.count` | `cache.own_order_book()`, `get_avg_px_for_quantity()`, `book.update_count` |
| `BookOrder(price=, size=, side=)` | 4 positional args: `BookOrder(OrderSide.BUY, Price, Quantity, order_id=0)`. Import from `model.data` |
| `GenericDataWrangler` / `catalog.data_types()` | Use specific wranglers (TradeTickDataWrangler etc). `catalog.list_data_types()` |
| `BacktestEngineConfig` from `nautilus_trader.config` | from `nautilus_trader.backtest.engine`. `CacheConfig` from `nautilus_trader.config` |
| `BacktestEngine.add_venue(venue=BacktestVenueConfig(...))` | Takes positional args. `BacktestVenueConfig` is for `BacktestRunConfig` only |
| `FillModel(prob_fill_on_stop=...)` | Only: prob_fill_on_limit, prob_slippage, random_seed |
| `LoggingConfig(log_file_path=)` / `cache.orders_filled()` | `log_directory=` / `cache.orders_closed()` |
| `pos.signed_qty / Decimal(...)` | TypeError: returns float — `Decimal(str(pos.signed_qty))` |
| `from nautilus_trader.trading.actor` | `from nautilus_trader.common.actor import Actor` |
| Indicator imports: `from nautilus_trader.indicators.ema` | `from nautilus_trader.indicators import ExponentialMovingAverage` (flat namespace) |
| `RSI` in [0,100] / `BollingerBands(20)` / `MACD(12,26,9)` | RSI in [0,1]. BB needs k: `BollingerBands(20, 2.0)`. MACD 3rd arg is `MovingAverageType` |
| Indicator warmup returns NaN | Returns partial values (silently wrong) — guard with `indicators_initialized()` |
| `publish_signal(value=dict(...))` | KeyError — values must be int, float, or str |
| Encrypted Ed25519 / `on_timer()` as callback | Unencrypted PKCS#8. Use `clock.set_timer(callback=handler)` |
| `order.order_side` / `request_bars(bar_type)` one arg | `order.side`. Requires `start`: `request_bars(bar_type, start=...)` |
| `GreeksCalculator(cache, clock, logger)` | 2 args only. BS: `from nautilus_trader.core.nautilus_pyo3 import black_scholes_greeks` |
| `SyntheticInstrument(sym, prec, comps, formula)` | 6 required args — also needs `ts_event`, `ts_init` |
| `DYDXDataClientConfig` / `DydxOraclePrice` | `DydxDataClientConfig` (mixed case). OraclePrice doesn't exist in v1.224.0 |
| `Equity(..., max_price=)` / `FuturesContract(..., size_precision=)` | Equity rejects these kwargs. FuturesContract hardcodes to 0/1 in Cython |
| `BookType.L3_MBO` for crypto | L3 not available on crypto — L2 at best |
| `subscribe_funding_rates()` / `subscribe_instrument_status()` | Not all adapters support. Binance lacks instrument_status |
| `MarketStatusAction.RESUME` / `InstrumentStatus` stops orders | RESUME doesn't exist (use TRADING). InstrumentStatus doesn't auto-stop orders |
| `BinanceAccountType.USDT_FUTURE` (no S) | Must be `USDT_FUTURES` (with S) |
| `load_ids=frozenset({"BTCUSDT-PERP"})` bare symbol | Full InstrumentId required: `frozenset({"BTCUSDT-PERP.BINANCE"})` |
| `modify_order` auto-fallback | No auto cancel+replace — adapter errors if venue doesn't support |
| `from nautilus_trader.common.clock import TestClock` | `from nautilus_trader.common.component import LiveClock` |

## Reference Navigator

Load proactively: **live** → exchange_adapters + operations, **backtest** → backtesting, **Rust** → rust_trading.

| Task | References | Examples |
|------|-----------|----------|
| **Backtest** | [backtesting.md](references/backtesting.md), [execution.md](references/execution.md) | `ema_crossover_backtest.py`, `bracket_order_backtest.py` |
| **Live (Python)** | [execution.md](references/execution.md), [exchange_adapters.md](references/exchange_adapters.md), [operations.md](references/operations.md) | `spread_capture_live.py` |
| **Live (Rust)** | [rust_trading.md](references/rust_trading.md), [exchange_adapters.md](references/exchange_adapters.md), [operations.md](references/operations.md) | `live_data_collector.rs`, `live_order_test.rs` |
| **Data-only node** | [exchange_adapters.md](references/exchange_adapters.md), [operations.md](references/operations.md) | `live_data_collector.rs` |
| **Market making** | [market_making.md](references/market_making.md), [order_book.md](references/order_book.md) | `market_maker_backtest.py`, `market_maker_backtest.rs` |
| **Actors & signals** | [actors_and_signals.md](references/actors_and_signals.md) | `signal_pipeline_backtest.py`, `signal_actor_backtest.rs` |
| **Options & Greeks** | [options_and_greeks.md](references/options_and_greeks.md) | `deribit_option_greeks_backtest.py` |
| **Prediction markets** | [prediction_and_betting.md](references/prediction_and_betting.md) | `polymarket_binary_backtest.py` |
| **TradFi / Derivatives** | [traditional_finance.md](references/traditional_finance.md), [derivatives.md](references/derivatives.md) | — |
| **Custom adapter** | [adapter_development_python.md](references/adapter_development_python.md), [adapter_development_rust.md](references/adapter_development_rust.md) | `custom_adapter_minimal.py` |
| **Dev environment** | [dev_environment.md](references/dev_environment.md) | — |
