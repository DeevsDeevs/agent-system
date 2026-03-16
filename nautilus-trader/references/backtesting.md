# Backtesting & Microstructure

## Two API Levels

### Low-Level: BacktestEngine

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
    venue=Venue("BINANCE"), oms_type=OmsType.NETTING, account_type=AccountType.MARGIN,
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

Multiple instruments: add with `sort=False`, call `engine.sort_data()`, then `engine.run()`.

### High-Level: BacktestNode

Config-driven, streams from ParquetDataCatalog for datasets exceeding memory.

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

```python
engine.add_venue(
    venue=Venue("SIM"), oms_type=OmsType.NETTING, account_type=AccountType.MARGIN,
    base_currency=USDT, starting_balances=[Money(1_000_000, USDT)],
    book_type=BookType.L2_MBP,        # L1_MBP (default), L2_MBP
    queue_position=True,               # limit order queue sim (requires TradeTick data)
    frozen_account=False,              # False = margin checks ARE active
    bar_execution=False,               # True = execute on bar data
    support_contingent_orders=True,    # OTO/OCO/OUO
    use_reduce_only=True,
)
```

> If bar timestamps are open-time, set `ts_init_delta` to bar duration in nanos (e.g. `60_000_000_000` for 1-min) to prevent look-ahead bias.

`L1_MBP`: single-level matching (QuoteTick/TradeTick/Bar). `L2_MBP`: multi-level, walks the book (OrderBookDelta). `CASH` for spot, `MARGIN` for perps.

## Fill Models

```python
from nautilus_trader.backtest.models import FillModel

fill_model = FillModel(prob_fill_on_limit=0.3, prob_slippage=0.5, random_seed=42)
# prob_fill_on_stop does NOT exist
```

Config-driven: use `ImportableFillModelConfig` with `fill_model_path="nautilus_trader.backtest.models:FillModel"`, `config_path="nautilus_trader.backtest.config:FillModelConfig"`.

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

Default fills limit orders on price touch -- overstates passive spread capture. For MM strategies, expect **30-50% of backtest PnL** in live.

## Fee Models

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

Backtest-only -- live uses exchange fill reports.

## Latency Simulation

`LatencyModel(base_latency_nanos=50_000_000, insert_latency_nanos=..., update_latency_nanos=..., cancel_latency_nanos=...)` — pass to `engine.add_venue(..., latency_model=latency_model)`.

## Indicators

```python
from nautilus_trader.indicators import (
    ExponentialMovingAverage,    # EMA(period)
    SimpleMovingAverage,         # SMA(period)
    RelativeStrengthIndex,       # RSI(period) -- value in [0, 1] not [0, 100]
    BollingerBands,              # BB(period, k) -- k is MANDATORY (e.g. 2.0)
    MovingAverageConvergenceDivergence,  # MACD(fast, slow, ma_type) -- NOT (fast, slow, signal)
    AverageTrueRange,            # ATR(period)
    MovingAverageType,           # EXPONENTIAL, SIMPLE, etc.
)

bar_type = BarType.from_str(f"{instrument.id}-1-MINUTE-LAST-INTERNAL")
self.register_indicator_for_bars(bar_type, self.ema)
self.subscribe_bars(bar_type)

def on_bar(self, bar: Bar) -> None:
    if not self.indicators_initialized():
        return  # warmup period -- partial values (not NaN), silently wrong
```

Import: `from nautilus_trader.indicators import X` (NOT `from nautilus_trader.indicators.ema`).

## Data Loading

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

from nautilus_trader.model.data import QuoteTick
data = catalog.query(QuoteTick, instrument_ids=["BTCUSDT-PERP.BINANCE"],
                     start="2024-01-01", end="2024-01-31")
types = catalog.list_data_types()  # NOTE: .data_types() does NOT exist
```

Live cache data is NOT time-sorted -- sort by `ts_init` before `catalog.write_data()`.

### Tardis CSV

```python
from nautilus_trader.adapters.tardis.loaders import TardisCSVDataLoader
deltas_df = TardisCSVDataLoader.load("book_change_BTCUSDT_2024-01.csv")
trades_df = TardisCSVDataLoader.load("trades_BTCUSDT_2024-01.csv")
```

## Test Data Providers

```python
from nautilus_trader.test_kit.providers import TestInstrumentProvider, TestDataProvider
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler

ethusdt = TestInstrumentProvider.ethusdt_binance()   # also: btcusdt_perp_binance(), adausdt_binance()
dp = TestDataProvider()
df = dp.read_csv_ticks("binance/ethusdt-trades.csv")  # returns DataFrame, NOT ticks
ticks = TradeTickDataWrangler(instrument=ethusdt).process(df)
```

## Adverse Selection

### Order Flow Imbalance

Track buy/sell imbalance in volume buckets to detect informed flow. See [custom_data_backtest.rs](../examples/custom_data_backtest.rs) for a Rust implementation using the `#[custom_data]` macro.

`imbalance = |buy_vol - sell_vol| / total_vol` per bucket. High imbalance = widen spreads, low = tighten.

### Glosten-Milgrom Spread Decomposition

```python
def realized_spread(trade_price: float, side_sign: int, mid_after_delay: float) -> float:
    return 2 * side_sign * (trade_price - mid_after_delay)

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

Negative average realized spread = adverse selection. Widen quotes or increase imbalance threshold.

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

Same formula applied to VWAP of top-N levels: `bid_vwap = Σ(price*size)/Σsize` for bids, same for asks, then weight by opposite-side totals. See `book.bids()[:depth]` / `book.asks()[:depth]`.

## Realistic Backtest Checklist

For production-grade backtests: `book_type=L2_MBP`, `queue_position=True` (requires TradeTick data), `latency_model`, custom `FeeModel`/`FillModel`, `frozen_account=False`, OrderBookDelta data for L2, `ts_init_delta` for bar look-ahead prevention.

> See SKILL.md for common hallucination guards.

## Rust

| Concern | Python | Rust |
|---|---|---|
| Engine config | `BacktestEngineConfig(...)` | `BacktestEngineConfig::default()` |
| `add_venue` | Named kwargs | 31 positional `Option<...>` args |
| Account type | `AccountType.MARGIN` | `AccountType::Margin` -- `Cash` panics for perps |
| Catalog async | No restriction | Wrap in `spawn_blocking` |
| `NautilusDataType` | `nautilus_trader.model` | `nautilus_backtest::config` |
| `BacktestNode` | Always available | `features = ["streaming"]` |

### BacktestEngine

```rust
use ahash::AHashMap;
use nautilus_backtest::{config::BacktestEngineConfig, engine::BacktestEngine};
use nautilus_execution::models::{fee::FeeModelAny, fill::FillModelAny};
use nautilus_model::{enums::{AccountType, BookType, OmsType}, identifiers::Venue, types::Money};

let mut engine = BacktestEngine::new(BacktestEngineConfig::default())?;
engine.add_venue(
    Venue::from("BINANCE"), OmsType::Netting, AccountType::Margin, BookType::L1_MBP,
    vec![Money::from("100000 USDT")],
    None, None, AHashMap::new(), None, vec![],
    FillModelAny::default(), FeeModelAny::default(),
    None, None, None, None, None, None, None, None,
    None, None, None, None, None, None, None, None, None,
)?;
engine.add_instrument(&instrument)?;
engine.add_data(data_vec, None, true, true);  // (data, client_id, validate, sort)
engine.add_strategy(my_strategy)?;
engine.run(None, None, None, false)?;
```

### BacktestNode (catalog-backed, `features = ["streaming"]`)

`BacktestVenueConfig::new(...)`, `BacktestDataConfig::new(NautilusDataType::QuoteTick, catalog_path, ...)`, `BacktestRunConfig::new(None, venues, data, engine_config, ...)`. Then `node.build()? → node.get_engine_mut(&id) → engine.add_strategy(s)? → node.run()?`. See [catalog_backtest.rs](../examples/catalog_backtest.rs) for full working example.

### Parquet Catalog Writes (async context)

```rust
use nautilus_persistence::backend::catalog::ParquetDataCatalog;

tokio::task::spawn_blocking(move || -> anyhow::Result<()> {
    let catalog = ParquetDataCatalog::new(&catalog_path, None, None, None, None);
    catalog.write_instruments(instruments)?;
    catalog.write_to_parquet(quotes, None, None, None)?;
    Ok(())
}).await??;
```
