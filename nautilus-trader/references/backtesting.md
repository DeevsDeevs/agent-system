# Backtesting & Microstructure

BacktestEngine, BacktestNode, SimulatedExchange, fill/fee/latency models, adverse selection, microprice, and data loading for NautilusTrader.

## Two API Levels

### Low-Level: BacktestEngine

Direct control, entire dataset in memory. Best for rapid iteration.

```python
from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import TraderId, Venue
from nautilus_trader.model.objects import Money, Currency

config = BacktestEngineConfig(
    trader_id=TraderId("BACKTESTER-001"),
    logging=LoggingConfig(log_level="ERROR"),
)
engine = BacktestEngine(config=config)

engine.add_venue(
    venue=Venue("BINANCE"),
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    base_currency=None,  # None = multi-currency account (standard for crypto)
    starting_balances=[Money(1_000_000, Currency.from_str("USDT"))],
)

engine.add_instrument(instrument)
engine.add_data(ticks)
engine.add_strategy(strategy)
engine.run()

accounts = engine.cache.accounts()     # NOT engine.trader.cache
positions = engine.cache.positions()
engine.dispose()
```

**Deferred sorting** — for multiple instruments, sort once after all data loaded:

```python
engine.add_data(btc_deltas, sort=False)
engine.add_data(eth_deltas, sort=False)
engine.sort_data()
engine.run()
```

### High-Level: BacktestNode

Config-driven, streams from ParquetDataCatalog. For large datasets exceeding memory.

```python
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.config import (
    BacktestRunConfig, BacktestDataConfig, BacktestVenueConfig, ImportableStrategyConfig,
)

run_config = BacktestRunConfig(
    venues=[BacktestVenueConfig(
        name="SIM", oms_type="NETTING", account_type="MARGIN",
        starting_balances=["1_000_000 USDT"],
    )],
    data=[BacktestDataConfig(
        catalog_path="/path/to/catalog", data_cls="OrderBookDelta",
        instrument_id="BTCUSDT-PERP.BINANCE",
        start_time="2024-01-01T00:00:00Z", end_time="2024-02-01T00:00:00Z",
    )],
    strategies=[ImportableStrategyConfig(
        strategy_path="my_package:MarketMaker",
        config_path="my_package:MarketMakerConfig",
        config={"instrument_id": "BTCUSDT-PERP.SIM", "trade_size": "0.1"},
    )],
)

node = BacktestNode(configs=[run_config])
node.build()  # MUST call build() before get_engine()
engine = node.get_engine(run_config.id)
engine.add_strategy(my_strategy)
results = node.run()
```

## Venue Configuration

### SimulatedExchange

```python
engine.add_venue(
    venue=Venue("SIM"),
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    base_currency=USDT,
    starting_balances=[Money(1_000_000, USDT)],
    book_type=BookType.L2_MBP,        # L1_MBP (default), L2_MBP
    queue_position=True,               # limit order queue simulation
    frozen_account=False,              # see warning below
    bar_execution=False,               # True = execute on bar data
    support_contingent_orders=True,    # OTO/OCO/OUO
    use_reduce_only=True,
)
```

> **`frozen_account` naming confusion**: `frozen_account=False` means margin checks **ARE active**. Think of it as "freeze_account" toggle — False = don't freeze = enforce checks.

### Book Types and Data Requirements

| BookType | Data Required | Matching Behavior |
|----------|---------------|-------------------|
| `L1_MBP` | QuoteTick, TradeTick, Bar | Single-level, market orders may slip 1 tick |
| `L2_MBP` | OrderBookDelta (L2) | Multi-level, market orders walk the book |

### Account Types

| Type | Use Case |
|------|----------|
| `CASH` | Spot trading — locks notional value. Market orders may silently produce 0 fills if insufficient balance. |
| `MARGIN` | Derivatives — tracks initial/maintenance margin. Standard for crypto perps backtesting. |

## Fill Models

### FillModel (Probabilistic)

```python
from nautilus_trader.backtest.models import FillModel

fill_model = FillModel(
    prob_fill_on_limit=0.3,   # probability limit order fills when price touches
    prob_slippage=0.5,        # probability of 1 tick slippage
    random_seed=42,           # for reproducibility
)
# prob_fill_on_stop does NOT exist
```

Configure via `ImportableFillModelConfig`:
```python
from nautilus_trader.backtest.config import ImportableFillModelConfig

BacktestVenueConfig(
    name="SIM", oms_type="NETTING", account_type="MARGIN",
    starting_balances=["1_000_000 USDT"],
    fill_model=ImportableFillModelConfig(
        fill_model_path="nautilus_trader.backtest.models:FillModel",
        config_path="nautilus_trader.backtest.config:FillModelConfig",
        config={"prob_fill_on_limit": 0.2, "prob_slippage": 0.5, "random_seed": 42},
    ),
)
```

### Built-in Fill Models

| Model | Description |
|-------|-------------|
| `FillModel` | Probabilistic limit fill + configurable slippage |
| `ThreeTierFillModel` | 50/30/20 contracts at 3 price levels |
| `VolumeSensitiveFillModel` | Volume-based fill for market impact |

### Custom FillModel

```python
class ConservativeFillModel(FillModel):
    def is_limit_filled(self) -> bool:
        return self._random.random() < self._prob_fill_on_limit

    def is_stop_filled(self) -> bool:
        return True

    def slippage_ticks(self) -> int:
        return 1 if self._random.random() < self._prob_slippage else 0
```

### Fill Behavior by Data Type

| Data | Behavior |
|------|----------|
| L2 OrderBookDelta | Market orders walk book across levels. Most realistic. |
| L1 QuoteTick/TradeTick | Single-level. May slip one tick if top exhausted. |
| Bar (OHLCV) | Least realistic. Stops trigger on high/low range. Enable `bar_execution=True`. |

### Naive Fill Model Bias

NautilusTrader's default backtest fill model fills limit orders when price touches the level. In reality:

1. **Queue position**: Your order waits behind others at that price. Fills happen only after sufficient volume trades through.
2. **Adverse selection**: When price touches your level and your order fills, it's often because an informed trader pushed price through — the fill is correlated with adverse price movement.
3. **Phantom fills**: In backtest, passive orders "capture spread" on every touch. Live, many touches don't fill you, and those that do are disproportionately the ones that continue moving against you.

**Conservative expectation**: For MM strategies, expect 30-50% of backtest PnL in live. If a strategy isn't profitable with a 50% haircut, it won't work live.

## Queue Position Tracking

```python
engine.add_venue(
    venue=Venue("SIM"), oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    starting_balances=[Money(1_000_000, USDT)],
    queue_position=True,  # requires TradeTick data
)
```

**How it works**: When a limit order is placed, queue position is initialized from visible book depth at that price level. As `TradeTick` data arrives at that price, it decrements the queue counter by the trade volume. The order fills only when sufficient volume has traded through.

**Requirements**: TradeTick data alongside OrderBookDelta. Without trade ticks, queue position cannot be estimated.

**Limitation**: Queue position still doesn't model adverse selection — it only models waiting time.

## Fee Models

### Custom FeeModel

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
        return Money(notional * rate, instrument.quote_currency)
```

Configure `maker_rate` and `taker_rate` to match your actual exchange tier.

**FeeModel is backtest-only** — live trading uses actual fees from exchange fill reports.

### Breakeven Spread

See [market_making.md](market_making.md#breakeven-spread-and-fee-awareness) for breakeven spread formulas and fee awareness. Access fees at runtime: `float(instrument.maker_fee)`, `float(instrument.taker_fee)`.

## Latency Simulation

```python
from nautilus_trader.backtest.models import LatencyModel

latency_model = LatencyModel(
    base_latency_nanos=50_000_000,       # 50ms
    insert_latency_nanos=50_000_000,     # order insert
    update_latency_nanos=50_000_000,     # order modify
    cancel_latency_nanos=50_000_000,     # order cancel
)

engine.add_venue(venue=Venue("SIM"), ..., latency_model=latency_model)
```

Orders can be rejected or modified during the latency window if market moves. Data granularity must match — Nautilus cannot synthesize higher-frequency data from lower.

## Indicators

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

bar_type = BarType.from_str(f"{instrument.id}-1-MINUTE-LAST-INTERNAL")
self.register_indicator_for_bars(bar_type, self.ema)
self.subscribe_bars(bar_type)

def on_bar(self, bar: Bar) -> None:
    if not self.indicators_initialized():
        return  # warmup period — partial values (not NaN), silently wrong
```

Import path: `from nautilus_trader.indicators import X` (NOT `from nautilus_trader.indicators.ema`).

## Bar Timestamp Convention (ts_init_delta)

Bars must use **closing time** for `ts_init` to prevent look-ahead bias.

> **If your bar data uses opening timestamps**: Set `ts_init_delta` to the bar duration in nanoseconds. For 1-minute bars: `ts_init_delta = 60_000_000_000`.

## Data Loading Pipeline

### DataWrangler

```python
from nautilus_trader.persistence.wranglers import (
    OrderBookDeltaDataWrangler, QuoteTickDataWrangler,
    TradeTickDataWrangler, BarDataWrangler,
)

wrangler = OrderBookDeltaDataWrangler(instrument)
deltas = wrangler.process(df_raw)
engine.add_data(deltas)
```

### ParquetDataCatalog

```python
from nautilus_trader.persistence.catalog import ParquetDataCatalog

catalog = ParquetDataCatalog("/path/to/catalog")

catalog.write_data([instrument])  # must be a list
catalog.write_data(trade_ticks)   # MUST be sorted by ts_init

instruments = catalog.instruments()
ticks = catalog.trade_ticks(instrument_ids=["ETHUSDT.BINANCE"])
quotes = catalog.quote_ticks(instrument_ids=["BTCUSDT-PERP.BINANCE"])
deltas = catalog.order_book_deltas(instrument_ids=["BTCUSDT-PERP.BINANCE"])

# Generic query with time range
from nautilus_trader.model.data import QuoteTick
data = catalog.query(QuoteTick, instrument_ids=["BTCUSDT-PERP.BINANCE"],
                     start="2024-01-01", end="2024-01-31")

types = catalog.list_data_types()  # NOTE: .data_types() does NOT exist

first = catalog.query_first_timestamp(TradeTick, identifier="ETHUSDT.BINANCE")
last = catalog.query_last_timestamp(TradeTick, identifier="ETHUSDT.BINANCE")

catalog.consolidate_catalog()  # optimize Parquet file layout
```

Supports local filesystem, S3, GCS, Azure Blob Storage. May need `pip install "fsspec[http]" requests` for remote access.

**Live cache data sorting**: Live cache data is NOT time-sorted. Sort before writing:

```python
trades = list(cache.trade_ticks(inst_id))
trades.sort(key=lambda x: x.ts_init)
catalog.write_data(trades)
```

### Tardis CSV Loading

```python
from nautilus_trader.adapters.tardis.loaders import TardisCSVDataLoader

deltas_df = TardisCSVDataLoader.load("book_change_BTCUSDT_2024-01.csv")
trades_df = TardisCSVDataLoader.load("trades_BTCUSDT_2024-01.csv")
```

## Test Data Providers

```python
from nautilus_trader.test_kit.providers import TestInstrumentProvider, TestDataProvider
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler

ethusdt = TestInstrumentProvider.ethusdt_binance()
btcusdt_perp = TestInstrumentProvider.btcusdt_perp_binance()
# Also: adausdt_binance(), btcusdt_binance(), btcusdt_future_binance(), etc.

dp = TestDataProvider()
df = dp.read_csv_ticks("binance/ethusdt-trades.csv")  # returns DataFrame
# Also: dp.read_csv_bars(), dp.read_parquet_ticks(), dp.read_parquet_bars()

wrangler = TradeTickDataWrangler(instrument=ethusdt)
ticks = wrangler.process(df)  # list[TradeTick]
```

**Note**: `read_csv_ticks` returns a pandas DataFrame, NOT tick objects. Must use a Wrangler to convert.

## Multi-Venue Simulation

```python
engine.add_venue(venue=Venue("BINANCE"), oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN, base_currency=USDT,
    starting_balances=[Money(500_000, USDT)])
engine.add_venue(venue=Venue("BYBIT"), oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN, base_currency=USDT,
    starting_balances=[Money(500_000, USDT)])
```

Each venue has independent matching, fills, and balances.

### Synthetic Instruments in Backtest

```python
from nautilus_trader.model.instruments import SyntheticInstrument
from nautilus_trader.model.identifiers import Symbol

synthetic = SyntheticInstrument(
    symbol=Symbol("BTC-SPREAD"), price_precision=2,
    components=[btc_inst.id, eth_inst.id],
    formula="BTCUSDT-PERP.BINANCE - ETHUSDT-PERP.BINANCE * 20",
    ts_event=0, ts_init=0,
)
```

See [derivatives.md](derivatives.md#syntheticinstrument) for full SyntheticInstrument API.

## Multiple Runs

```python
engine.run()
results1 = engine.trader.generate_order_fills_report()
engine.reset()
engine.add_strategy(new_strategy)
engine.run()
```

## Adverse Selection

### VPIN (Volume-Synchronized Probability of Informed Trading)

Estimates the probability that volume is driven by informed traders. High VPIN → widen spreads or reduce size.

```python
from collections import deque
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import AggressorSide

class VPINTracker:
    def __init__(self, bucket_size: float, n_buckets: int = 50):
        self.bucket_size = bucket_size
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
            order_imbalance = abs(buy_frac - 0.5) * 2
            self._buckets.append(order_imbalance)
            self._current_buy_vol = 0.0
            self._current_total_vol = 0.0

            if len(self._buckets) == self.n_buckets:
                return sum(self._buckets) / self.n_buckets
        return None
```

**Interpretation**: VPIN > 0.7 → elevated informed trading, widen spreads 50-100%. VPIN < 0.3 → calm, tighten spreads.

### Glosten-Milgrom Spread Decomposition

The bid-ask spread compensates for adverse selection (loss to informed traders) and order processing (fees, inventory risk). Measure adverse selection via realized spread:

```python
def realized_spread(trade_price: float, side_sign: int, mid_after_delay: float) -> float:
    return 2 * side_sign * (trade_price - mid_after_delay)
```

Track realized spreads over time with delayed midpoint capture:

```python
def on_order_filled(self, event) -> None:
    side_sign = 1 if event.order_side == OrderSide.BUY else -1
    self._pending_spreads.append((event.last_px, side_sign, self.clock.timestamp_ns()))

def _compute_realized_spreads(self, event) -> None:
    now_ns = self.clock.timestamp_ns()
    book = self.cache.order_book(self.config.instrument_id)
    mid_after = float(book.midpoint()) if book.midpoint() else None
    if mid_after is None:
        return
    completed = []
    for px, sign, ts in self._pending_spreads:
        if now_ns - ts >= 5_000_000_000:  # 5s delay
            rs = 2 * sign * (float(px) - mid_after)
            completed.append(rs)
    for _ in completed:
        self._pending_spreads.popleft()
```

Negative average realized spread → you're being adversely selected. Widen quotes or increase VPIN threshold.

## Microprice

Simple midpoint ignores size imbalance. Microprice weights by opposite-side volume for a better estimate of where the next trade will occur.

```
microprice = bid * (ask_size / (bid_size + ask_size)) + ask * (bid_size / (bid_size + ask_size))
```

```python
def _compute_microprice(self) -> Decimal | None:
    book = self.cache.order_book(self.config.instrument_id)
    bid = book.best_bid_price()
    ask = book.best_ask_price()
    bid_sz = book.best_bid_size()
    ask_sz = book.best_ask_size()
    if not all([bid, ask, bid_sz, ask_sz]):
        return None
    bv, av = float(bid_sz), float(ask_sz)
    return Decimal(str((float(bid) * av + float(ask) * bv) / (bv + av)))
```

### Multi-Level Extension

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
    return (bid_weighted * ask_total + ask_weighted * bid_total) / (
        (bid_total + ask_total) * (bid_total + ask_total)
    ) * 2
```

Always prefer microprice over simple midpoint for MM quoting. The improvement is most significant when book imbalance is high.

## Order-to-Fill Latency Measurement

### Execution Latency

```python
def on_order_filled(self, event) -> None:
    order = self.cache.order(event.client_order_id)
    fill_latency_ns = event.ts_event - order.ts_init
    fill_latency_ms = fill_latency_ns / 1_000_000
```

### Data Latency

```python
def on_order_book_deltas(self, deltas) -> None:
    for delta in deltas:
        data_latency_ms = (delta.ts_init - delta.ts_event) / 1_000_000
```

### Clock Synchronization

- **NTP requirement**: Sync local clock to <1ms accuracy via NTP or PTP
- **ts_event from exchange**: Always populate from exchange timestamp, not local clock
- **Clock drift**: If `ts_init - ts_event` goes negative, clocks are desynchronized
- **Impact**: Inaccurate latency → wrong queue position estimates → overstated backtest PnL

## Order Sizing via Book Depth

See [market_making.md](market_making.md#order-sizing) for the `_safe_size()` pattern. Always use `instrument.make_qty()` for lot size compliance.

## Realistic Backtest Checklist

| Setting | Purpose | Default |
|---------|---------|---------|
| `book_type=L2_MBP` | Multi-level matching | `L1_MBP` |
| `queue_position=True` | Limit order queue | `False` |
| `latency_model` | Network delay | None |
| Custom `FeeModel` | Venue-accurate fees | Fixed |
| Custom `FillModel` | Realistic fills | Probabilistic |
| `frozen_account=False` | Margin enforcement | `False` |
| TradeTick data | Queue position + spread | — |
| OrderBookDelta data | L2 matching | — |
| ts_init_delta | Bar look-ahead prevention | 0 |

## Anti-Hallucination Notes

| Hallucination | Reality |
|--------------|---------|
| `engine.trader.cache` | `engine.cache` directly |
| `BacktestEngineConfig` from `nautilus_trader.config` | `from nautilus_trader.backtest.engine` or `nautilus_trader.backtest.config` |
| `BacktestEngine.add_venue(venue=BacktestVenueConfig(...))` | Takes positional args. `BacktestVenueConfig` is for `BacktestRunConfig` only |
| `FillModel(prob_fill_on_stop=...)` | Only: `prob_fill_on_limit`, `prob_slippage`, `random_seed` |
| `frozen_account=True` means checks active | Inverted: `False` = checks active, `True` = frozen (no checks) |
| `catalog.data_types()` | `catalog.list_data_types()` |
| `GenericDataWrangler` | Use specific: `TradeTickDataWrangler`, `QuoteTickDataWrangler`, `OrderBookDeltaDataWrangler`, `BarDataWrangler` |
| `RSI` value in [0, 100] | Value in [0, 1] — divide by 100 if comparing to standard |
| `MACD(fast, slow, signal_period)` | 3rd param is `MovingAverageType`, not signal period |
| Indicator warmup returns NaN | Returns partial values (silently wrong) — guard with `indicators_initialized()` |
| `from nautilus_trader.indicators.ema` | `from nautilus_trader.indicators import ExponentialMovingAverage` |

## Rust

| Concern | Python | Rust |
|---|---|---|
| Engine config | `BacktestEngineConfig(trader_id=..., logging=...)` named kwargs | `BacktestEngineConfig::default()` — trader_id assigned internally |
| `add_venue` | Named kwargs with defaults | 31 positional args, all `Option<...>` |
| Account type for perps | `AccountType.MARGIN` | `AccountType::Margin` — `Cash` panics when trading futures/perpetuals |
| Catalog writes from async | No restriction | Must wrap in `tokio::task::spawn_blocking` — catalog creates its own runtime internally |
| `NautilusDataType` location | `nautilus_trader.model` | `nautilus_backtest::config` — NOT `nautilus_model` |
| `BacktestNode` availability | Always available | Behind `features = ["streaming"]` on `nautilus-backtest` |

### BacktestEngine

```rust
use ahash::AHashMap;
use nautilus_backtest::{config::BacktestEngineConfig, engine::BacktestEngine};
use nautilus_execution::models::{fee::FeeModelAny, fill::FillModelAny};
use nautilus_model::{
    enums::{AccountType, BookType, OmsType},
    identifiers::Venue,
    types::Money,
};

let config = BacktestEngineConfig::default();
let mut engine = BacktestEngine::new(config)?;

// add_venue takes 31 positional args — most are Option<...>
engine.add_venue(
    Venue::from("BINANCE"),
    OmsType::Netting,
    AccountType::Margin,  // Margin required for perps/futures
    BookType::L1_MBP,
    vec![Money::from("100000 USDT")],
    None,              // base_currency
    None,              // default_leverage
    AHashMap::new(),   // leverages (per-instrument map)
    None,              // margin_model
    vec![],            // modules
    FillModelAny::default(),
    FeeModelAny::default(),
    None,  // latency_model
    None,  // routing
    None,  // reject_stop_orders
    None,  // support_gtd_orders
    None,  // support_contingent_orders
    None,  // use_position_ids
    None,  // use_random_ids
    None,  // use_reduce_only
    None,  // use_message_queue
    None,  // use_market_order_acks
    None,  // bar_execution
    None,  // bar_adaptive_high_low_ordering
    None,  // trade_execution
    None,  // liquidity_consumption
    None,  // allow_cash_borrowing
    None,  // frozen_account
    None,  // queue_position
    None,  // oto_full_trigger
    None,  // price_protection_points
)?;

engine.add_instrument(&instrument)?;
engine.add_data(data_vec, None, true, true);  // (data, client_id, validate, sort)
engine.add_strategy(my_strategy)?;
engine.add_actor(my_actor)?;

engine.run(None, None, None, false)?;  // (start, end, run_config_id, streaming)

let result = engine.get_result();
println!("{} iterations, {} orders", result.iterations, result.total_orders);
```

### BacktestNode (catalog-backed)

Behind `features = ["streaming"]` on `nautilus-backtest`. For large datasets that don't fit in memory.

```rust
use nautilus_backtest::{
    config::{
        BacktestDataConfig, BacktestEngineConfig, BacktestRunConfig,
        BacktestVenueConfig, NautilusDataType,  // NautilusDataType is here, NOT in nautilus_model
    },
    node::BacktestNode,
};
use ustr::Ustr;

let venue_config = BacktestVenueConfig::new(
    Ustr::from("BINANCE"), OmsType::Netting, AccountType::Margin, BookType::L1_MBP,
    None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
    vec!["100000 USDT".to_string()],
    None, None, None, None,
);

let data_config = BacktestDataConfig::new(
    NautilusDataType::QuoteTick,
    catalog_path.to_string(),
    None, None, Some(instrument_id), None, None, None, None, None, None, None, None, None,
);

let run_config = BacktestRunConfig::new(
    None, vec![venue_config], vec![data_config],
    BacktestEngineConfig::default(), None, None, None, None,
);

let mut node = BacktestNode::new(vec![run_config])?;
node.build()?;
let config_id = node.configs()[0].id().to_string();
let engine = node.get_engine_mut(&config_id).ok_or_else(|| anyhow::anyhow!("engine not found"))?;
engine.add_strategy(my_strategy)?;
let results = node.run()?;
println!("{} iterations, {} orders", results[0].iterations, results[0].total_orders);
```

### Parquet Catalog Writes (from async context)

`ParquetDataCatalog` internally calls `tokio::runtime::Runtime::block_on`. Calling it from `#[tokio::main]` panics with `cannot start a runtime from within a runtime`. Wrap in `spawn_blocking`:

```rust
use nautilus_persistence::backend::catalog::ParquetDataCatalog;

tokio::task::spawn_blocking(move || -> anyhow::Result<()> {
    let catalog = ParquetDataCatalog::new(&catalog_path, None, None, None, None);
    catalog.write_instruments(instruments)?;
    catalog.write_to_parquet(quotes, None, None, None)?;
    catalog.write_to_parquet(trades, None, None, None)?;
    catalog.write_to_parquet(deltas, None, None, None)?;  // Vec<OrderBookDelta>
    Ok(())
}).await??;
```

Written files land at:
- `{catalog_path}/instruments/`
- `{catalog_path}/quote_tick/{instrument_id}/{ts_start}-{ts_end}.parquet`
- `{catalog_path}/trade_tick/{instrument_id}/{ts_start}-{ts_end}.parquet`
- `{catalog_path}/order_book_delta/{instrument_id}/{ts_start}-{ts_end}.parquet`
| Data granularity auto-synthesis | Nautilus cannot synthesize higher-frequency data from lower |
