# Data System

## Data Types

| Type | Description | Granularity |
|------|-------------|-------------|
| `OrderBookDelta` | Individual order book updates | L1/L2/L3 |
| `OrderBookDepth10` | Aggregated snapshot (10 levels/side) | L2 |
| `QuoteTick` | Best bid/ask with sizes | L1 |
| `TradeTick` | Individual trade/match events | — |
| `Bar` | OHLCV candles | — |
| `MarkPriceUpdate` | Derivative mark prices | — |
| `FundingRateUpdate` | Perpetual funding rates | — |
| `InstrumentStatus` | Instrument state changes | — |
| `InstrumentClose` | Instrument close events | — |

### Data Hierarchy (descending detail)

1. Order Book L3 (market-by-order)
2. Order Book L2 (market-by-price)
3. Quote Ticks (L1)
4. Trade Ticks
5. Bars

## Bar Types

### String Format

`{instrument_id}-{step}-{aggregation}-{price_type}-{source}`

```python
from nautilus_trader.model import BarType

# Time-based bars
bar_type = BarType.from_str("BTCUSDT-PERP.BINANCE-1-MINUTE-LAST-EXTERNAL")
bar_type = BarType.from_str("AAPL.XNAS-5-MINUTE-LAST-INTERNAL")

# Tick bars
bar_type = BarType.from_str("BTCUSDT-PERP.BINANCE-100-TICK-LAST-INTERNAL")

# Volume bars
bar_type = BarType.from_str("BTCUSDT-PERP.BINANCE-1000-VOLUME-LAST-INTERNAL")

# Composite (bar-to-bar)
bar_type = BarType.from_str("AAPL.XNAS-5-MINUTE-LAST-INTERNAL@1-MINUTE-EXTERNAL")
```

### Aggregation Methods

**Time-based**: MILLISECOND, SECOND, MINUTE, HOUR, DAY, WEEK, MONTH, YEAR

**Threshold-based**: TICK, VOLUME, VALUE, RENKO

**Information-driven**: TICK_IMBALANCE, TICK_RUNS, VOLUME_IMBALANCE, VOLUME_RUNS, VALUE_IMBALANCE, VALUE_RUNS

Information-driven bars adapt sampling frequency to market activity, closing when buy/sell imbalance or consecutive runs reach thresholds.

### Price Types

| Type | Source |
|------|--------|
| `LAST` | Trade ticks |
| `BID` | Quote ticks (bid side) |
| `ASK` | Quote ticks (ask side) |
| `MID` | Quote ticks (midpoint) |

### Sources

| Source | Meaning |
|--------|---------|
| `INTERNAL` | Aggregated by Nautilus from raw ticks |
| `EXTERNAL` | Pre-aggregated from venue/provider |

## Record Flags

Each `OrderBookDelta` carries a `RecordFlag` bitmask:

- `F_LAST` — final delta in a logical event group
- `F_SNAPSHOT` — delta belongs to a snapshot

## Timestamps

- `ts_event` — when event occurred externally (nanoseconds UNIX)
- `ts_init` — when Nautilus initialized the object
- Latency = `ts_init - ts_event`

## Custom Data Types

```python
from nautilus_trader.core.data import Data

class MySignal(Data):
    def __init__(self, value: float, ts_event: int, ts_init: int):
        self.value = value
        self._ts_event = ts_event
        self._ts_init = ts_init

    @property
    def ts_event(self) -> int:
        return self._ts_event

    @property
    def ts_init(self) -> int:
        return self._ts_init
```

**Publishing** (from Actor/Strategy):

```python
from nautilus_trader.model.data import DataType

self.publish_data(DataType(MySignal), signal_instance)
```

**Subscribing**:

```python
self.subscribe_data(DataType(MySignal), client_id=None)

def on_data(self, data) -> None:
    if isinstance(data, MySignal):
        self.log.info(f"Signal: {data.value}")
```

## Data Catalog (ParquetDataCatalog)

### Dual Backend

**Rust backend** (optimized): OrderBookDelta, QuoteTick, TradeTick, Bar, MarkPriceUpdate

**PyArrow backend** (flexible): Custom data types, advanced filtering

### Operations

```python
from nautilus_trader.persistence.catalog import ParquetDataCatalog

catalog = ParquetDataCatalog("/path/to/catalog")

# Write
catalog.write_data(quotes)
catalog.write_data(trades)

# Query
quotes = catalog.query(
    QuoteTick,
    instrument_ids=["EUR/USD.SIM"],
    start="2024-01-01",
    end="2024-01-31",
)

# Maintenance
catalog.consolidate_catalog()
catalog.delete_data_range(QuoteTick, "EUR/USD.SIM", start, end)
```

### Storage Backends

Local filesystem, S3, GCS, Azure Blob Storage.

### Gap Analysis

```python
# Identify missing time intervals
gaps = catalog.get_gaps(QuoteTick, "EUR/USD.SIM", start, end)
coverage = catalog.get_coverage(QuoteTick, "EUR/USD.SIM")
```

## Data Wranglers

Transform external data (pandas DataFrame) → Nautilus objects:

```python
from nautilus_trader.persistence.wranglers import (
    BarDataWrangler,
    QuoteTickDataWrangler,
    TradeTickDataWrangler,
    OrderBookDeltaDataWrangler,
)

# Bars: requires columns [open, high, low, close, volume] with timestamp index
bar_wrangler = BarDataWrangler(bar_type=bar_type, instrument=instrument)
bars = bar_wrangler.process(df)

# Quotes: requires [bid_price, ask_price] columns
quote_wrangler = QuoteTickDataWrangler(instrument=instrument)
quotes = quote_wrangler.process(df)

# Trades: individual trade records
trade_wrangler = TradeTickDataWrangler(instrument=instrument)
trades = trade_wrangler.process(df)
```

## DataEngine

Routes data through the system:

```
External Ingestion → DataEngine Processing → Caching → Event Publishing → Consumer Delivery
```

Handles subscriptions, request routing, bar aggregation, and data type normalization.

## Streaming (StreamWriter)

```python
from nautilus_trader.persistence.streaming import StreamWriter

writer = StreamWriter(path="/path/to/output", flush_interval_ms=1000)
writer.write(data)
writer.close()
```

Writes Nautilus objects to rotating feather files for real-time persistence.
