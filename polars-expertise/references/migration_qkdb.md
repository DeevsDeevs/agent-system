# q/kdb+ to Polars Migration Guide

This guide helps you migrate from q/kdb+ to Polars, covering vector operations, table manipulations, and financial data patterns common in trading systems.

## Philosophical Differences

### q/kdb+ Philosophy
- Right-to-left evaluation
- Implicit iteration over lists
- Tables are lists of dictionaries
- Column-oriented with native time-series support
- Interpreted, terse syntax

### Polars Philosophy
- Left-to-right chained operations
- Explicit expression API
- DataFrame as collection of Series (columns)
- Column-oriented with Apache Arrow
- Compiled Rust backend, Python/Rust frontend

## Core Type Mappings

| q Type | Polars Type | Notes |
|--------|-------------|-------|
| `boolean` / `b` | `pl.Boolean` | |
| `byte` / `x` | `pl.UInt8` | |
| `short` / `h` | `pl.Int16` | |
| `int` / `i` | `pl.Int32` | |
| `long` / `j` | `pl.Int64` | Default integer |
| `real` / `e` | `pl.Float32` | |
| `float` / `f` | `pl.Float64` | Default float |
| `char` / `c` | `pl.String` | Single chars become strings |
| `symbol` / `s` | `pl.Categorical` or `pl.String` | Use Categorical for low-cardinality |
| `timestamp` / `p` | `pl.Datetime("ns")` | Nanosecond precision |
| `date` / `d` | `pl.Date` | |
| `time` / `t` | `pl.Time` | |
| `timespan` / `n` | `pl.Duration` | |

## Vector Operation Mappings

### Basic Arithmetic

| q | Polars | Notes |
|---|--------|-------|
| `x + y` | `pl.col("x") + pl.col("y")` | |
| `x * y` | `pl.col("x") * pl.col("y")` | |
| `sum x` | `pl.col("x").sum()` | |
| `avg x` | `pl.col("x").mean()` | |
| `max x` | `pl.col("x").max()` | |
| `min x` | `pl.col("x").min()` | |
| `med x` | `pl.col("x").median()` | |
| `dev x` | `pl.col("x").std()` | Standard deviation |
| `var x` | `pl.col("x").var()` | Variance |

### List/Array Operations

| q | Polars | Notes |
|---|--------|-------|
| `count x` | `pl.col("x").len()` | Length |
| `first x` | `pl.col("x").first()` | |
| `last x` | `pl.col("x").last()` | |
| `reverse x` | `pl.col("x").reverse()` | |
| `asc x` | `pl.col("x").sort()` | Ascending sort |
| `desc x` | `pl.col("x").sort(descending=True)` | |
| `distinct x` | `pl.col("x").unique()` | |
| `x?y` | `pl.col("x").search_sorted(y)` | Find index (binary search) |
| `x in y` | `pl.col("x").is_in(y)` | Membership |

### Running/Cumulative Operations

| q | Polars | Notes |
|---|--------|-------|
| `sums x` | `pl.col("x").cum_sum()` | Running sum |
| `prds x` | `pl.col("x").cum_prod()` | Running product |
| `maxs x` | `pl.col("x").cum_max()` | Running max |
| `mins x` | `pl.col("x").cum_min()` | Running min |

### Sliding Windows

| q | Polars | Notes |
|---|--------|-------|
| `mavg[n;x]` | `pl.col("x").rolling_mean(n)` | Moving average |
| `msum[n;x]` | `pl.col("x").rolling_sum(n)` | Moving sum |
| `mmax[n;x]` | `pl.col("x").rolling_max(n)` | Moving max |
| `mmin[n;x]` | `pl.col("x").rolling_min(n)` | Moving min |
| `mdev[n;x]` | `pl.col("x").rolling_std(n)` | Moving std dev |

### Deltas and Differences

| q | Polars | Notes |
|---|--------|-------|
| `deltas x` | `pl.col("x").diff()` | First differences |
| `ratios x` | `pl.col("x") / pl.col("x").shift(1)` | Ratio to previous |
| `1 _ x` | `pl.col("x").slice(1)` | Drop first |
| `-1 _ x` | `pl.col("x").head(-1)` | Drop last |
| `n # x` | `pl.col("x").head(n)` | Take first n |
| `-n # x` | `pl.col("x").tail(n)` | Take last n |

### Prev/Next

| q | Polars | Notes |
|---|--------|-------|
| `prev x` | `pl.col("x").shift(1)` | Previous value |
| `next x` | `pl.col("x").shift(-1)` | Next value |
| `xprev[n;x]` | `pl.col("x").shift(n)` | N periods back |

## Table Operations

### Creating Tables

**q:**
```q
t:([] sym:`AAPL`MSFT`AAPL; price:150.0 280.0 152.0; size:100 200 150)
```

**Polars:**
```python
t = pl.DataFrame({
    "sym": ["AAPL", "MSFT", "AAPL"],
    "price": [150.0, 280.0, 152.0],
    "size": [100, 200, 150]
})
```

### Selection (qSQL vs Polars)

**q:**
```q
select sym, price from t where size > 100
```

**Polars:**
```python
t.filter(pl.col("size") > 100).select("sym", "price")
```

### Aggregation

**q:**
```q
select avg price, sum size by sym from t
```

**Polars:**
```python
t.group_by("sym").agg(
    pl.col("price").mean(),
    pl.col("size").sum()
)
```

### Update (Adding Columns)

**q:**
```q
update vwap: size wavg price by sym from t
```

**Polars:**
```python
t.with_columns(
    vwap=(pl.col("price") * pl.col("size")).sum().over("sym") /
         pl.col("size").sum().over("sym")
)
```

### Delete (Dropping Rows)

**q:**
```q
delete from t where size < 100
```

**Polars:**
```python
t.filter(pl.col("size") >= 100)
```

### Sorting

**q:**
```q
`sym`price xasc t
```

**Polars:**
```python
t.sort("sym", "price")
```

### Joins

| q | Polars | Notes |
|---|--------|-------|
| `t1 lj t2` | `t1.join(t2, on="key", how="left")` | Left join |
| `t1 ij t2` | `t1.join(t2, on="key", how="inner")` | Inner join |
| `t1 uj t2` | `pl.concat([t1, t2])` | Union (vertical) |
| `t1 aj \`time\`sym t2` | `t1.join_asof(t2, on="time", by="sym")` | As-of join |
| `t1 wj ...` | `t1.join_asof(...).with_columns(...)` | Window join (manual) |

## Financial Data Patterns

### OHLCV Bars from Ticks

**q:**
```q
select o:first price, h:max price, l:min price, c:last price, v:sum size
by sym, time.minute from trades
```

**Polars:**
```python
trades.group_by("sym", pl.col("time").dt.truncate("1m")).agg(
    pl.col("price").first().alias("o"),
    pl.col("price").max().alias("h"),
    pl.col("price").min().alias("l"),
    pl.col("price").last().alias("c"),
    pl.col("size").sum().alias("v")
)
```

### VWAP

**q:**
```q
select vwap: size wavg price by sym from trades
```

**Polars:**
```python
trades.group_by("sym").agg(
    vwap=(pl.col("price") * pl.col("size")).sum() / pl.col("size").sum()
)
```

### Intraday Returns

**q:**
```q
update ret: 1 - price % prev price by sym from trades
```

**Polars:**
```python
trades.with_columns(
    ret=(pl.col("price") / pl.col("price").shift(1) - 1).over("sym")
)
```

### Rolling Volatility

**q:**
```q
update vol: mdev[20; log price - log prev price] by sym from trades
```

**Polars:**
```python
trades.with_columns(
    pl.col("price").log().diff().rolling_std(20).over("sym").alias("vol")
)
```

### As-of Joins (Quote/Trade Matching)

**q:**
```q
aj[`sym`time; trades; quotes]
```

**Polars:**
```python
trades.sort("time").join_asof(
    quotes.sort("time"),
    on="time",
    by="sym",
    strategy="backward"  # Last quote before trade
)
```

### Time-Weighted Average

**q:**
```q
update twap: (deltas time) wavg price by sym from quotes
```

**Polars:**
```python
quotes.with_columns(
    pl.col("time").diff().over("sym").alias("dt")
).with_columns(
    twap=(pl.col("price") * pl.col("dt")).sum().over("sym") /
         pl.col("dt").sum().over("sym")
)
```

## Performance Considerations

### What q/kdb+ Does Better
- Native nanosecond timestamps with timezone
- Built-in IPC and pub/sub
- Extremely fast as-of joins on sorted data
- Integrated timeseries database (kdb+)
- Lower memory footprint for timeseries

### What Polars Does Better
- Complex query optimization (predicate pushdown)
- Multi-threaded by default
- Better for ad-hoc analysis
- Larger ecosystem (Python)
- No licensing costs
- Better for batch processing

### Memory Comparison

q/kdb+ uses compact in-memory representation optimized for timeseries. Polars uses Arrow format optimized for analytics. For dense timeseries with many symbols, kdb+ may use less memory. For wide tables with mixed types, they're comparable.

### Speed Expectations

| Operation | Relative Performance |
|-----------|---------------------|
| Simple aggregations | Polars often faster (multi-threaded) |
| As-of joins (sorted) | q/kdb+ faster |
| Complex multi-step queries | Polars faster (optimization) |
| Tick data ingestion | kdb+ faster (built-in) |
| Ad-hoc analysis | Polars faster (better optimization) |

## Migration Strategy

### Phase 1: Batch Analytics
Move batch analytics (EOD processing, reporting) to Polars first. Keep kdb+ for real-time.

### Phase 2: Historical Analysis
Use Polars for historical backtesting and research. Export kdb+ data to Parquet.

### Phase 3: Evaluate Real-time
Consider Polars streaming for lower-frequency real-time needs. Keep kdb+ for HFT.

## Code Translation Examples

### Example 1: Daily Stats

**q:**
```q
select
    open: first price,
    high: max price,
    low: min price,
    close: last price,
    volume: sum size,
    trades: count i
by sym, date from trades
```

**Polars:**
```python
(
    trades
    .group_by("sym", pl.col("timestamp").dt.date().alias("date"))
    .agg(
        pl.col("price").first().alias("open"),
        pl.col("price").max().alias("high"),
        pl.col("price").min().alias("low"),
        pl.col("price").last().alias("close"),
        pl.col("size").sum().alias("volume"),
        pl.len().alias("trades")
    )
)
```

### Example 2: Moving Spread

**q:**
```q
update spread: mavg[100; ask - bid] by sym from quotes
```

**Polars:**
```python
quotes.with_columns(
    spread=(pl.col("ask") - pl.col("bid")).rolling_mean(100).over("sym")
)
```

### Example 3: Fill Forward

**q:**
```q
update price: fills price by sym from quotes
```

**Polars:**
```python
quotes.with_columns(
    pl.col("price").forward_fill().over("sym").alias("price")
)
```

## Key Syntax Differences Summary

| q Pattern | Polars Pattern |
|-----------|----------------|
| Right-to-left: `avg x` | Left-to-right: `pl.col("x").mean()` |
| Implicit iteration | Explicit `.over()` for groups |
| `select ... by` | `.group_by().agg()` |
| `update col: expr` | `.with_columns(col=expr)` |
| `x?y` (find) | `.search_sorted()` or `.filter()` |
| `x wavg y` | `(x * y).sum() / y.sum()` |
| `fills x` | `.forward_fill()` |
| `aj` | `.join_asof()` |
