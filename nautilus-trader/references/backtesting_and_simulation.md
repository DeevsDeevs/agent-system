# Backtesting and Simulation

BacktestEngine, BacktestNode, SimulatedExchange, fill/fee/latency models, queue position tracking, and data loading for NautilusTrader.

## Two API Levels

### Low-Level: BacktestEngine

Direct control, entire dataset in memory. Best for rapid iteration.

```python
# BacktestEngineConfig is in backtest.engine, NOT backtest.config (verified v1.224.0)
from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import TraderId, Venue
from nautilus_trader.model.objects import Money, Currency

config = BacktestEngineConfig(
    trader_id=TraderId("BACKTESTER-001"),
    logging=LoggingConfig(log_level="ERROR"),  # reduce noise
)
engine = BacktestEngine(config=config)

# Use Currency.from_str — USDT constant from model.currencies may not exist
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

# Access cache and results after run
accounts = engine.cache.accounts()     # NOT engine.trader.cache
positions = engine.cache.positions()
engine.dispose()                       # cleanup
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
node.build()  # MUST call build() before get_engine() — returns None otherwise

# To add strategy programmatically (instead of ImportableStrategyConfig):
engine = node.get_engine(run_config.id)
engine.add_strategy(my_strategy)

results = node.run()  # returns list[BacktestResult]
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

> **`frozen_account` naming confusion**: `frozen_account=False` means margin checks **ARE active** (the account is NOT frozen). Think of it as a "freeze_account" toggle — False = don't freeze = enforce checks. This catches many people off guard.

### Book Types and Data Requirements

| BookType | Data Required | Matching Behavior |
|----------|---------------|-------------------|
| `L1_MBP` | QuoteTick, TradeTick, Bar | Single-level, market orders may slip 1 tick |
| `L2_MBP` | OrderBookDelta (L2) | Multi-level, market orders walk the book |

Data granularity must match — Nautilus cannot synthesize higher from lower.

### Account Types

| Type | Use Case |
|------|----------|
| `CASH` | Spot trading — locks notional value. **Warning**: market orders may silently produce 0 fills if insufficient quote currency balance or if `frozen_account=False` enforces checks too strictly. Always verify fills. |
| `MARGIN` | Derivatives — tracks initial/maintenance margin. Standard for crypto perps backtesting. |

## Fill Models

### FillModel (Probabilistic)

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

### FillModel Constructor (v1.224.0)

```python
from nautilus_trader.backtest.models import FillModel

# Only these params exist — prob_fill_on_stop does NOT exist
fill_model = FillModel(
    prob_fill_on_limit=0.3,   # probability limit order fills when price touches
    prob_slippage=0.5,        # probability of 1 tick slippage
    random_seed=42,           # for reproducibility
)
```

### Custom FillModel

```python
class ConservativeFillModel(FillModel):
    def is_limit_filled(self) -> bool:
        return self._random.random() < self._prob_fill_on_limit

    def is_stop_filled(self) -> bool:
        return True

    def slippage_ticks(self) -> int:
        if self._random.random() < self._prob_slippage:
            return 1
        return 0
```

### Fill Behavior by Data Type

| Data | Behavior |
|------|----------|
| L2 OrderBookDelta | Market orders walk book across levels. Most realistic. |
| L1 QuoteTick/TradeTick | Single-level. May slip one tick if top exhausted. |
| Bar (OHLCV) | Least realistic. Stops trigger on high/low range. Enable `bar_execution=True`. |

> **Naive fill model bias warning**: Default fill models significantly overstate MM strategy profitability. Limit orders fill whenever price touches the level, ignoring that real fills are correlated with adverse price movement. In reality: (1) you're in a queue behind other orders, (2) when you do fill, it's often because informed flow pushed through your level. **Conservative expectation**: 30-50% of backtest PnL for MM strategies in live. If a strategy isn't profitable with a 50% haircut, it won't work live.

## Queue Position Tracking

```python
engine.add_venue(
    venue=Venue("SIM"),
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,
    starting_balances=[Money(1_000_000, USDT)],
    queue_position=True,  # requires TradeTick data
)
```

**How it works**: When a limit order is placed, queue position is initialized from visible book depth at that price level. As `TradeTick` data arrives at that price, it decrements the queue counter by the trade volume. The order fills only when sufficient volume has traded through.

**Requirements**: TradeTick data alongside OrderBookDelta. Without trade ticks, queue position cannot be estimated.

**Limitation**: Queue position simulation still doesn't model adverse selection — it only models waiting time. Fills that clear your queue in backtest may be informed-flow-driven in reality.

## Custom Fee Models

```python
from nautilus_trader.backtest.models import FeeModel
from nautilus_trader.model.objects import Money

class TieredCryptoFeeModel(FeeModel):
    def get_commission(self, order, fill_qty, fill_px, instrument) -> Money:
        notional = float(fill_qty) * float(fill_px)
        rate = 0.0002 if order.is_passive else 0.0005  # 2/5 bps maker/taker
        return Money(notional * rate, instrument.quote_currency)
```

Register via `ImportableFillModelConfig` pattern (same approach, using `FeeModelConfig`).

## Latency Simulation

```python
from nautilus_trader.backtest.models import LatencyModel

latency_model = LatencyModel(
    base_latency_nanos=50_000_000,       # 50ms
    insert_latency_nanos=50_000_000,     # order insert
    update_latency_nanos=50_000_000,     # order modify
    cancel_latency_nanos=50_000_000,     # order cancel
)

engine.add_venue(
    venue=Venue("SIM"), ...,
    latency_model=latency_model,
)
```

Orders can be rejected or modified during the latency window if market moves.

## Bar Timestamp Convention (ts_init_delta)

Bars must use **closing time** for `ts_init` to prevent look-ahead bias.

> **If your bar data uses opening timestamps**: Set `ts_init_delta` to the bar duration in nanoseconds. Without this, bars appear available before they close — your strategy sees future information. For 1-minute bars: `ts_init_delta = 60_000_000_000` (60 seconds in nanoseconds).

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

# Write instruments first, then data
catalog.write_data([instrument])  # must be a list
catalog.write_data(trade_ticks)   # list of TradeTick/QuoteTick/etc.

# Read back — typed methods (preferred)
instruments = catalog.instruments()
ticks = catalog.trade_ticks(instrument_ids=["ETHUSDT.BINANCE"])
quotes = catalog.quote_ticks(instrument_ids=["BTCUSDT-PERP.BINANCE"])
deltas = catalog.order_book_deltas(instrument_ids=["BTCUSDT-PERP.BINANCE"])

# List what's in the catalog
types = catalog.list_data_types()  # e.g. ['currency_pair', 'trade_tick']
# NOTE: .data_types() does NOT exist — use .list_data_types()

# Generic query
data = catalog.query(QuoteTick, instrument_ids=["..."], start="2024-01-01", end="2024-01-31")

# Timestamps — MUST pass identifier, else returns None
first = catalog.query_first_timestamp(TradeTick, identifier="ETHUSDT.BINANCE")
last = catalog.query_last_timestamp(TradeTick, identifier="ETHUSDT.BINANCE")

catalog.consolidate_catalog()
```

Supports local filesystem, S3, GCS, Azure Blob Storage.

### Tardis CSV Loading

```python
from nautilus_trader.adapters.tardis.loaders import TardisCSVDataLoader

deltas_df = TardisCSVDataLoader.load("book_change_BTCUSDT_2024-01.csv")
trades_df = TardisCSVDataLoader.load("trades_BTCUSDT_2024-01.csv")
```

## Test Data Providers

Built-in test data for quick backtest setup without external data:

```python
from nautilus_trader.test_kit.providers import TestInstrumentProvider, TestDataProvider
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler

# Pre-built instruments (no API needed)
ethusdt = TestInstrumentProvider.ethusdt_binance()        # CurrencyPair
btcusdt_perp = TestInstrumentProvider.btcusdt_perp_binance()  # CryptoPerpetual
# Also: adausdt_binance, btcusdt_binance, btcusdt_future_binance, etc.

# Test data (pulled from GitHub on first use, cached locally)
dp = TestDataProvider()
df = dp.read_csv_ticks("binance/ethusdt-trades.csv")  # returns DataFrame
# Methods: read_csv_ticks, read_csv_bars, read_parquet_ticks, read_parquet_bars

# Wrangle DataFrame → NautilusTrader objects
wrangler = TradeTickDataWrangler(instrument=ethusdt)
ticks = wrangler.process(df)  # list[TradeTick]
# Wranglers: TradeTickDataWrangler, QuoteTickDataWrangler,
#            OrderBookDeltaDataWrangler, BarDataWrangler
```

**Note**: `read_csv_ticks` returns a pandas DataFrame, NOT a list of tick objects. Must use a Wrangler to convert. `pip install "fsspec[http]" requests` may be needed for GitHub data access.

## Multi-Venue Simulation

```python
engine.add_venue(venue=Venue("BINANCE"), oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN, base_currency=USDT,
    starting_balances=[Money(500_000, USDT)])
engine.add_venue(venue=Venue("BYBIT"), oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN, base_currency=USDT,
    starting_balances=[Money(500_000, USDT)])
```

Each venue has independent matching, fills, and balances. Cross-venue strategies work naturally via `instrument_id` routing.

### Synthetic Instruments

```python
from nautilus_trader.model.instruments import SyntheticInstrument

synthetic = SyntheticInstrument(
    symbol=Symbol("BTC-SPREAD"), price_precision=2,
    components=[
        InstrumentId.from_str("BTCUSDT-PERP.BINANCE"),
        InstrumentId.from_str("BTCUSDT.BINANCE"),
    ],
    formula="(components[0] - components[1])",
    ts_event=0, ts_init=0,
)
```

## Multiple Runs

```python
engine.run()
results1 = engine.trader.generate_order_fills_report()
engine.reset()
engine.add_strategy(new_strategy)
engine.run()
results2 = engine.trader.generate_order_fills_report()
```

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
