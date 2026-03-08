# Backtesting

## Two API Levels

### Low-Level: BacktestEngine

Direct control, entire dataset in memory. Best for rapid iteration with small-to-medium data.

```python
from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.identifiers import TraderId, Venue
from nautilus_trader.model.objects import Money

config = BacktestEngineConfig(trader_id=TraderId("BACKTESTER-001"))
engine = BacktestEngine(config=config)

# Add venue
engine.add_venue(
    venue=Venue("SIM"),
    oms_type=OmsType.NETTING,
    account_type=AccountType.CASH,
    base_currency=USD,
    starting_balances=[Money(100_000, USD)],
)

# Add instrument and data
engine.add_instrument(instrument)
engine.add_data(bars)        # or quote_ticks, trade_ticks, deltas

# Add strategy and run
engine.add_strategy(strategy)
engine.run()
```

### Performance Tip: Deferred Sorting

For multiple instruments, defer sorting until all data is loaded:

```python
engine.add_data(instrument1_bars, sort=False)
engine.add_data(instrument2_bars, sort=False)
engine.add_data(instrument3_bars, sort=False)
engine.sort_data()  # single sort pass
engine.run()
```

### High-Level: BacktestNode

Config-driven, streams from ParquetDataCatalog. Best for large datasets exceeding memory.

```python
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.config import (
    BacktestRunConfig,
    BacktestDataConfig,
    BacktestVenueConfig,
    ImportableStrategyConfig,
)
from nautilus_trader.model import QuoteTick

data_configs = [
    BacktestDataConfig(
        catalog_path="/path/to/catalog",
        data_cls=QuoteTick,
        instrument_id="EUR/USD.SIM",
        start_time="2024-01-01T00:00:00Z",
        end_time="2024-01-02T00:00:00Z",
    ),
]

venue_configs = [
    BacktestVenueConfig(
        name="SIM",
        oms_type="NETTING",
        account_type="CASH",
        starting_balances=["100_000 USD"],
    ),
]

strategy_configs = [
    ImportableStrategyConfig(
        strategy_path="my_package.strategies:EMACross",
        config_path="my_package.strategies:EMACrossConfig",
        config={
            "instrument_id": "EUR/USD.SIM",
            "bar_type": "EUR/USD.SIM-1-MINUTE-BID-INTERNAL",
            "trade_size": "100000",
        },
    ),
]

run_config = BacktestRunConfig(
    venues=venue_configs,
    data=data_configs,
    strategies=strategy_configs,
    start="2024-01-01T00:00:00Z",
    end="2024-01-02T00:00:00Z",
)

node = BacktestNode(configs=[run_config])
results = node.run()
```

## Venue Configuration

### Book Types

| Type | Description | Data Required |
|------|-------------|---------------|
| `L1_MBP` | Top-of-book only (default) | QuoteTick, TradeTick, Bar |
| `L2_MBP` | Multiple price levels | OrderBookDelta (L2) |
| `L3_MBO` | Individual orders | OrderBookDelta (L3) |

Data granularity must match — Nautilus cannot synthesize higher-granularity from lower.

### Account Types

| Type | Use Case |
|------|----------|
| `CASH` | Spot trading, locks notional value |
| `MARGIN` | Derivatives, tracks initial/maintenance margin |
| `BETTING` | Fixed stakes, no leverage |

### Margin Models

```python
from nautilus_trader.config import MarginModelConfig

# Standard: fixed percentage (traditional brokers)
BacktestVenueConfig(
    name="SIM",
    oms_type="NETTING",
    account_type="MARGIN",
    starting_balances=["1_000_000 USD"],
    margin_model=MarginModelConfig(model_type="standard"),
)

# Leveraged: margin reduced by leverage (crypto exchanges, default)
BacktestVenueConfig(
    name="SIM",
    oms_type="NETTING",
    account_type="MARGIN",
    starting_balances=["1_000_000 USD"],
    margin_model=MarginModelConfig(model_type="leveraged"),
)
```

## Fill Models

### FillModel (Probabilistic)

```python
from nautilus_trader.backtest.config import ImportableFillModelConfig

BacktestVenueConfig(
    name="SIM",
    oms_type="NETTING",
    account_type="CASH",
    starting_balances=["100_000 USD"],
    fill_model=ImportableFillModelConfig(
        fill_model_path="nautilus_trader.backtest.models:FillModel",
        config_path="nautilus_trader.backtest.config:FillModelConfig",
        config={
            "prob_fill_on_limit": 0.2,   # queue position simulation
            "prob_slippage": 0.5,         # slippage probability
            "random_seed": 42,
        },
    ),
)
```

### ThreeTierFillModel

Simulates depth with 50/30/20 contracts at 3 price levels.

```python
fill_model=ImportableFillModelConfig(
    fill_model_path="nautilus_trader.backtest.models:ThreeTierFillModel",
)
```

### VolumeSensitiveFillModel

Volume-based fill simulation for more realistic market impact.

## Fill Behavior by Data Type

**L2/L3 data**: Market orders walk the book across price levels. Limit orders fill at their limit price when matched.

**L1 data**: Single-level simulation. Market orders may slip one tick if top-level exhausted.

**Bar data**: STOP_MARKET/TRAILING_STOP_MARKET may fill at trigger price when bars move through high/low.

## Queue Position Tracking

Enable with `queue_position=True` on venue config. Uses trade tick data to decrement quantity ahead in queue, allowing fills when queue clears. More realistic for limit order simulation.

## Bar Timestamp Convention

Bars must use **closing time** for `ts_init` to prevent look-ahead bias. If data uses opening timestamps, set `ts_init_delta` to the bar duration in nanoseconds.

## Multiple Backtest Runs

**Recommended**: Use BacktestNode with separate BacktestRunConfig objects.

**Alternative**: `engine.reset()` between runs — instruments and data persist by default.

```python
engine.run()
results1 = engine.trader.generate_order_fills_report()
engine.reset()
engine.add_strategy(new_strategy)
engine.run()
results2 = engine.trader.generate_order_fills_report()
```

## Data Catalog (ParquetDataCatalog)

```python
from nautilus_trader.persistence.catalog import ParquetDataCatalog

catalog = ParquetDataCatalog("/path/to/catalog")

# Write data
catalog.write_data(quotes)
catalog.write_data(trades)
catalog.write_data(bars)

# Query data
quotes = catalog.query(
    QuoteTick,
    instrument_ids=["EUR/USD.SIM"],
    start="2024-01-01",
    end="2024-01-31",
)

# Consolidate fragmented files
catalog.consolidate_catalog()

# Delete data range
catalog.delete_data_range(QuoteTick, "EUR/USD.SIM", start, end)
```

Supports local filesystem, S3, GCS, Azure Blob Storage.

## Data Loading Pipeline

1. **DataLoader** — reads raw format → pandas DataFrame
2. **DataWrangler** — processes DataFrame → list of Nautilus objects
3. **Output** — ready for BacktestEngine

```python
from nautilus_trader.persistence.wranglers import BarDataWrangler

wrangler = BarDataWrangler(bar_type=bar_type, instrument=instrument)
bars = wrangler.process(df)  # df with columns: open, high, low, close, volume
engine.add_data(bars)
```

Built-in wranglers: `OrderBookDeltaDataWrangler`, `QuoteTickDataWrangler`, `TradeTickDataWrangler`, `BarDataWrangler`.
