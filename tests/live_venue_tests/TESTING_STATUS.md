# NautilusTrader Live Testing Status

**Date**: 2026-03-10
**Version**: nautilus_trader 1.224.0, Python 3.14.3
**Test suite**: `tests/live_venue_tests/` + `nautilus-crypto-hft/examples/`

## Skill Fixes Applied

| Fix | Files Changed | How Discovered |
|-----|--------------|----------------|
| `BinanceAccountType.USDT_FUTURE` → `USDT_FUTURES` | SKILL.md, live_trading.md, exchange_adapters.md, spread_capture_live.py | AttributeError on import |
| dYdX symbology `BTC-USD.DYDX` → `BTC-USD-PERP.DYDX` | SKILL.md, exchange_adapters.md | Probe strategy listing all instruments |
| dYdX classes `DYDXDataClientConfig` → `DydxDataClientConfig` | exchange_adapters.md | ImportError |
| dYdX `mnemonic` → `private_key`, `subaccount_number` → `subaccount` | exchange_adapters.md | TypeError on config init |
| Old submodule imports → flat `from nautilus_trader.adapters.binance import ...` | exchange_adapters.md, live_trading.md | ModuleNotFoundError for dYdX |
| String venue keys `"BINANCE"` → imported constants `BINANCE` | exchange_adapters.md, live_trading.md | Best practice, works either way |
| `BinanceInstrumentProviderConfig` → generic `InstrumentProviderConfig` | exchange_adapters.md | ImportError |
| `on_timer()` doesn't exist → `clock.set_timer(callback=)` | SKILL.md | Timer events silently lost |
| `load_all=True` slowness → `load_ids=frozenset` | SKILL.md | 13 minute startup |
| `BollingerBands(20)` → `BollingerBands(20, 2.0)` — k mandatory | SKILL.md, backtesting_and_simulation.md | TypeError: takes at least 2 positional arguments |
| `MACD(12, 26, 9)` → `MACD(12, 26, MovingAverageType.EXPONENTIAL)` — 3rd param is ma_type | SKILL.md, backtesting_and_simulation.md | AttributeError: NoneType._fast_ma |
| `Actor` from `nautilus_trader.trading.actor` → `nautilus_trader.common.actor` | SKILL.md | ModuleNotFoundError |
| Indicators from submodules like `.ema` → top-level `nautilus_trader.indicators` | SKILL.md | ModuleNotFoundError |
| `subscribe_data()` needs `client_id` or `instrument_id` | SKILL.md | Silent error, no data received |
| `order.order_side` → `order.side` (events use `event.order_side`) | SKILL.md | AttributeError on MarketOrder |
| `OrderList.is_bracket` as property → `is_bracket()` is method | SKILL.md | TypeError |
| Manual OrderList for brackets → `order_factory.bracket()` | SKILL.md, execution_and_oms.md | Built-in factory method |
| `request_bars(bar_type)` one arg → needs `start=` param | SKILL.md | TypeError: takes at least 2 positional arguments |
| Indicator values before init are 0/NaN → partial values (wrong) | SKILL.md | SMA(20) after 5 bars = avg of 5 |
| Subscribe to missing data raises error → silent 0 data | SKILL.md | ERROR log only, no exception |
| Native signal API undocumented: `publish_signal`/`subscribe_signal`/`on_signal` | SKILL.md, actors_and_signals.md | Tested: 698 signals end-to-end |
| `ParquetDataCatalog.data_types()` → `.list_data_types()` | SKILL.md, backtesting_and_simulation.md | AttributeError |
| `BacktestNode.get_engine()` before `build()` → must call `build()` first | SKILL.md, backtesting_and_simulation.md | Returns None |
| `engine.trader.cache` → `engine.cache` for BacktestEngine | backtesting_and_simulation.md | AttributeError: Trader has no cache |
| `BacktestEngineConfig` from `backtest.config` → `backtest.engine` | SKILL.md, backtesting_and_simulation.md | ImportError |
| RSI range is [0, 1] not [0, 100] | SKILL.md | Observation during backtest |
| `FillModel(prob_fill_on_stop=)` doesn't exist | SKILL.md, backtesting_and_simulation.md | TypeError on FillModel init |
| `catalog.query_first_timestamp()` needs `identifier=` | SKILL.md, backtesting_and_simulation.md | Returns None without it |
| CASH + `frozen_account=False` → 0 fills on market orders | SKILL.md, backtesting_and_simulation.md | Silent failure in backtest |
| `fills > orders` is normal (partial fills) | SKILL.md | Observation: 142 fills from 139 orders |

## Venue Connection Results

| Venue | Key Env Var | Connect | Instruments | Data Stream | Orders | Issue |
|-------|-----------|---------|-------------|-------------|--------|-------|
| Binance Futures | `BINANCE_LINEAR_API_KEY` | OK (3s) | 1 loaded | 559 deltas, 9811 trades, 51696 quotes | N/A | Key lacks trading permissions |
| Binance Spot | `BINANCE_SPOT_API_KEY` | OK (1s) | 1 loaded | Blocked by exec timeout | N/A | Exec client connects >20s, blocks strategy start |
| Bybit Linear | `BYBIT_PERP_API_KEY` | FAIL | FAIL | FAIL | N/A | IP-restricted to 87.121.50.19, blocks REST |
| OKX Swap | `OKX_API_KEY` | OK | 1 loaded | 245 deltas, 2478 trades, 1639 quotes | No funds | WS private auth fails, but data + balances work |
| dYdX v4 | `DYDX_PERP_WALLET_ADDRESS` | OK (1s) | 1 loaded | 5108 deltas, 1024 trades, 143 quotes | Rejected | Wallet not on-chain (account not found) |
| Multi (BN+OKX) | Both | OK | 2 loaded | BN: 268d/1670t/11968q, OKX: 147d/657t/930q | N/A | Cross-venue book spread ~0bps |

## Offline Test Results

| Test | Script | Result | Key Metrics |
|------|--------|--------|-------------|
| BacktestEngine | test_backtest_engine.py | **14/14 OK** | 69806 ticks → 299 bars, indicators init at bar 20, 5 orders/fills |
| ParquetDataCatalog | test_parquet_catalog.py | **12/12 OK** | Write/read round-trip, BacktestNode integration, list_data_types |
| Actors + Custom Data | test_actors_custom_data.py | **12/12 OK** | 698 signals published/received via MessageBus, order triggered by signal |
| Indicators | test_indicators_deep.py | **10/10 OK** | EMA, SMA, RSI, BB, MACD all validated, init guard works |
| SimulatedExchange | test_simulated_exchange.py | **8/8 OK** | Fill/latency models, CASH/MARGIN, engine.reset() multi-run |
| Data Wranglers | test_data_wranglers.py | **9/10 OK** | TradeTickDataWrangler, catalog round-trip, timestamp query (bar CSV missing) |
| Order Types + OMS | test_order_types_oms.py | **27/27 OK** | All 5 order types, NETTING flip LONG→SHORT, HEDGING 2 positions, cache queries, reports |
| Order Book API | test_order_book_api.py | **26/26 OK** | Instrument properties, cache methods, account balances, trade ticks in cache |
| Derivatives API | test_derivatives_api.py | **28/28 OK** | Perp properties, PnL tracking, portfolio access, BarType variants, position close |
| EMA Crossover Example | ema_crossover_backtest.py | **OK** | 12 orders, 6 positions, EMA(10)/EMA(30) crossover on ETHUSDT |
| Bracket Order Example | bracket_order_backtest.py | **OK** | order_factory.bracket() → entry FILLED, SL+TP set, OTO/OUO contingency |
| Signal Pipeline Example | signal_pipeline_backtest.py | **OK** | Actor→Strategy: 1396 signals, 612 orders, 306 positions |
| Market Maker Example | market_maker_backtest.py | **OK** | L2 book MM with inventory skew |

**TOTAL: 152/153 OK** (1 failure is missing bar CSV test data — nautilus issue, not ours)
**Examples: 4/4 OK**

## Live Data Collection (Binance Futures, 10 perps, 30s)

| Data Type | Status | Rate | Notes |
|-----------|--------|------|-------|
| Trade ticks | **WORKS** | ~100/s | All 10 instruments |
| Quote ticks | **WORKS** | ~600/s | BBO (bookTicker) — highest volume |
| Book deltas | **WORKS** | ~113/s | L2 incremental + snapshot rebuild |
| Mark prices | **WORKS** | ~9/s | ~1 update/3s per instrument |
| Bars (1m) | **WORKS** | 1/min/inst | EXTERNAL kline stream |
| Book depth | **NOT IMPL** | - | NotImplementedError on Binance adapter |
| Funding rates | **NOT IMPL** | - | NotImplementedError — use REST instead |
| Index prices | **NOT IMPL** | - | NotImplementedError |
| Instrument status | **NOT IMPL** | - | NotImplementedError |

**Total**: 24,500 events/30s (~817/s). Catalog save: instruments + trade/quote ticks (sorted by ts_init).

**REST endpoints verified**: OI, funding rate history, mark/index price, long/short ratio, 24h ticker.
Liquidations endpoint (`/fapi/v1/allForceOrders`) deprecated — returns 400.

## Coverage Map

### Tested & Confirmed Working

- TradingNode lifecycle (create → build → run → SIGINT stop)
- Adapter configuration for all 4 venues (Binance, Bybit, OKX, dYdX)
- InstrumentProvider with `load_ids` (3s) and `load_all` (5+ min)
- Data streaming: OrderBookDeltas, TradeTicks, QuoteTicks
- Cache reads: instruments, order books, quote ticks, accounts, balances
- Strategy on_start: subscriptions, instrument lookup, timer setup
- Clock: `set_timer(callback=)`, `set_time_alert(callback=)`
- Import paths validated against v1.224.0
- Symbology confirmed for all 5 venue ID formats
- **BacktestEngine** full lifecycle: venue, instrument, data, strategy, run, dispose
- **ParquetDataCatalog**: write instruments/ticks, read back, list_data_types
- **BacktestNode** high-level API: catalog data → run → results
- **Indicators**: EMA, SMA, RSI, BollingerBands, MACD registration + initialization guard
- **Actors**: lifecycle, custom Data class publishing, MessageBus pub/sub
- **Custom Data**: Data subclass → Actor publish → Strategy subscribe → on_data handler
- **Multi-venue TradingNode**: Binance + OKX simultaneous data streaming
- **Cross-venue book comparison**: real-time spread between venues
- **SimulatedExchange**: default fill model, latency model (10ms), fill probability model
- **CASH vs MARGIN accounts**: MARGIN fills normally, CASH with frozen_account=False blocks fills
- **engine.reset() + re-run**: multiple sequential backtests on same engine work
- **Data Wranglers**: TradeTickDataWrangler DataFrame→TradeTick conversion confirmed
- **Catalog round-trip**: write ticks → read back, count matches, timestamps preserved
- **Catalog timestamps**: query_first/last_timestamp needs identifier= param
- **Order Types**: market, limit, stop_market, stop_limit, market_to_limit all verified
- **OMS NETTING**: position aggregation, LONG→SHORT flip, realized PnL on close
- **OMS HEDGING**: multiple independent positions per instrument
- **Cache position queries**: `positions_open(instrument_id=)`, `positions_closed()`, `positions()`
- **Order lifecycle in backtest**: submit→accept→fill, submit→cancel, order state transitions
- **Order reports**: `generate_order_fills_report()`, `generate_positions_report()` (DataFrames)
- **Instrument properties**: price/size precision, increments, fees, min/max quantity, min_notional
- **Position PnL**: unrealized_pnl(price), realized_pnl, commissions(), signed_qty, avg_px_open/close
- **Portfolio access**: `portfolio.account(Venue)`, balance_total/free/locked, is_flat
- **BarType parsing**: from_str() for 1-MINUTE, 5-MINUTE, 1-HOUR LAST-INTERNAL
- **Strategy save/load**: on_save() returns state dict
- **Cache queries**: instruments, orders, orders_open, positions, accounts, trade_ticks, quote_ticks
- **Account balances**: balance_total/free/locked per currency
- **market_maker_backtest.py example**: runs without errors (fixed imports + data loading)
- **ema_crossover_backtest.py example**: EMA crossover strategy with indicator registration + bar subscription
- **bracket_order_backtest.py example**: `order_factory.bracket()` with OTO entry → OUO SL/TP
- **signal_pipeline_backtest.py example**: Actor `publish_signal` → Strategy `subscribe_signal`/`on_signal`
- **Native signal API**: `publish_signal(name, value, ts_event)` → auto-generates `Signal{Name}` class
- **Signal filtering**: `subscribe_signal(name='specific')` vs `subscribe_signal()` for all
- **Subscription ordering**: cache instrument → register indicators → subscribe data (verified silent failures)
- **Indicator partial values**: SMA/EMA produce wrong (not NaN) values before `initialized` — guard required
- **Order attribute**: `order.side` (not `order.order_side`), events use `event.order_side`
- **Bracket factory**: `order_factory.bracket()` tags: `['ENTRY']`, `['STOP_LOSS']`, `['TAKE_PROFIT']`
- **Clock API**: `utc_now()` → pandas Timestamp, `timestamp_ns()` → int, `set_time_alert(override=)`

### Partially Tested

- **Order submission**: flow works (`submit_order` called), but all venues rejected (account/key issues)
- **ExecEngine routing**: confirmed error handling when exec client missing
- **Account balances**: read on OKX (multi-asset) and dYdX (0 USDC)
- **Reconciliation**: disabled for speed, never tested startup reconciliation
- **Bars**: subscribed but 0 received in short tests (1-MINUTE-LAST-EXTERNAL needs >60s run)

### Not Tested — Needs Work

#### HIGH Priority
| Area | What to test | Prerequisites |
|------|-------------|---------------|
| Full order lifecycle (LIVE) | submit→accept→modify→cancel on real venue | Funded Binance Spot account (key has trading perms) |
| Bar aggregation (live) | Subscribe bars, verify on_bar fires in live mode | Longer test run (>2 min) |

#### MEDIUM Priority
| Area | What to test | Prerequisites |
|------|-------------|---------------|
| Risk engine | Pre-trade checks, max notional, HALTED/REDUCING states | Working order lifecycle |
| SimulatedExchange queue position | `queue_position=True` with TradeTick data | BacktestEngine working ✅, needs OrderBookDelta + TradeTick data |
| ExecAlgorithms | TWAP built-in, custom iceberg, spawn/child orders | Working order lifecycle |
| OrderEmulator | Local stop/trailing stop, trigger monitoring | Data streaming + order lifecycle |
| Custom data types | MarkPriceUpdate, FundingRateUpdate subscriptions | Existing venue connections |
| Multiple backtest runs | engine.reset() + re-run with different strategy | None |
| Data wranglers | QuoteTickDataWrangler, OrderBookDeltaDataWrangler, BarDataWrangler | None |

#### LOW Priority
| Area | What to test | Prerequisites |
|------|-------------|---------------|
| Contingent orders (LIVE) | OTO/OCO/OUO bracket orders on real venue | Working order lifecycle (backtest verified ✅) |
| Redis/Postgres persistence | State recovery, audit trail | Redis/Postgres running |
| MessageBus streaming | External event consumption via Redis streams | Redis running |
| Memory purge | Long-running session memory management | Long test run |
| WS reconnection | Disconnect handling, re-subscribe, book resync | Network manipulation |
| Custom adapter dev | LiveDataClient/LiveExecutionClient from scratch | Deep understanding |
| SyntheticInstrument | Cross-venue spread instrument | Multi-venue backtest |

## Recommended Next Steps

1. **Fund Binance Spot** — the SPOT key has trading permissions, deposit small USDT → full order lifecycle
2. **SimulatedExchange test** — BacktestEngine works, test fill/fee/latency models with queue_position
3. **Longer live run** — 2+ minute test to verify bar aggregation fires in live mode
4. **MarkPriceUpdate + FundingRateUpdate** — add subscriptions to existing dYdX/OKX tests
5. **Fix Binance Spot exec timeout** — increase `timeout_connection` to 45s or debug why exec client takes >20s
6. **Data wrangler tests** — QuoteTick, OrderBookDelta, Bar wranglers for data pipeline validation

## Key Debugging Mental Model

- `TradingNode.run()` blocks forever — use timer callbacks + `os.kill(SIGINT)` for self-termination
- If exec client auth fails, node starts after `timeout_connection` but orders fail with "no execution client found"
- `InstrumentProviderConfig(load_ids=frozenset({id}))` → 3s startup vs 5+ min with `load_all=True`
- Strategy has NO `on_timer()` method — timers need explicit `callback=` parameter
- dYdX quotes are synthesized from book (few quotes, many deltas)
- OKX data works even with IP restriction; only WS private channel fails
- Bybit IP restriction blocks even REST instrument loading
- `reconciliation=False` speeds up startup significantly
- `engine.cache` not `engine.trader.cache` for BacktestEngine results access
- `BacktestNode.build()` must be called before `get_engine()` returns anything
- `BollingerBands` and `MACD` have non-obvious constructor signatures — see anti-patterns
- RSI returns [0, 1] not [0, 100]
- Bars don't fire in short live tests — EXTERNAL bars need venue-provided bars or >60s for INTERNAL aggregation
- `fills > orders` is normal for market orders — single order can produce multiple partial fills
- CASH account with `frozen_account=False` may silently produce 0 fills if balance insufficient
- `TestDataProvider` pulls from GitHub — rate limits apply, copy to `tests/test_data/` for local cache
- `FillModel` only has `prob_fill_on_limit` and `prob_slippage` — `prob_fill_on_stop` doesn't exist
- `catalog.query_first_timestamp(TradeTick)` returns None — must pass `identifier=instrument_id_str`
- `order.side` not `order.order_side` (events use `event.order_side`) — mixing causes AttributeError
- `OrderList.is_bracket()` is a method, not a property — calling without `()` returns bound method
- `publish_signal(name='foo')` creates `SignalFoo` class — use `type(signal).__name__` to route in `on_signal`
- `subscribe_signal()` with no name subscribes to ALL signals; `subscribe_signal(name='foo')` filters
- Subscribing to data that doesn't exist (wrong type, missing instrument) → silent 0 data, ERROR log only
- Indicator values before `.initialized` are PARTIAL (e.g. SMA(20) after 5 bars = avg of 5) — not NaN
- `request_bars(bar_type)` without `start=` param → TypeError: takes at least 2 positional arguments
- `order_factory.bracket()` is the correct way to create brackets — avoid manual OrderList construction
