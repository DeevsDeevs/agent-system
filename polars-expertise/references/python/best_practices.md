# Polars Best Practices (Python)

## Table of Contents
- [Performance Anti-Patterns](#performance-anti-patterns)
- [Time Series Patterns](#time-series-patterns)
- [Financial Data Patterns](#financial-data-patterns)
- [Large File Processing](#large-file-processing)
- [Memory Optimization](#memory-optimization)
- [Expression Patterns](#expression-patterns)

## Performance Anti-Patterns

### NEVER Use These

```python
# ANTI-PATTERN 1: map_elements with Python functions
# This kills parallelization and is 10-100x slower
df.with_columns(
    pl.col("price").map_elements(lambda x: x * 2)  # TERRIBLE
)
# CORRECT:
df.with_columns(pl.col("price") * 2)  # Fast, parallel

# ANTI-PATTERN 2: Row iteration
for row in df.iter_rows():  # TERRIBLE
    process(row)
# CORRECT:
df.with_columns(process_expression)

# ANTI-PATTERN 3: Late projection
df = pl.read_parquet("data.parquet")
result = df.filter(...).select("a", "b")  # Reads ALL columns first
# CORRECT:
lf = pl.scan_parquet("data.parquet")
result = lf.select("a", "b").filter(...).collect()  # Reads only a, b

# ANTI-PATTERN 4: Eager for large data
df = pl.read_csv("huge.csv")  # Loads everything into RAM
# CORRECT:
lf = pl.scan_csv("huge.csv")
result = lf.filter(...).collect(engine="streaming")

# ANTI-PATTERN 5: Converting to pandas unnecessarily
pandas_df = df.to_pandas()
result = pandas_df.groupby("x").mean()  # Why?
# CORRECT:
result = df.group_by("x").agg(pl.all().mean())

# ANTI-PATTERN 6: Creating many intermediate DataFrames
df1 = df.filter(...)
df2 = df1.select(...)
df3 = df2.with_columns(...)  # Each creates a copy
# CORRECT:
result = df.filter(...).select(...).with_columns(...)  # Chained

# ANTI-PATTERN 7: Wrong dtype selection
df = pl.read_csv("data.csv")  # Infers Int64 for small integers
# CORRECT:
df = pl.read_csv("data.csv", dtypes={"small_int": pl.Int16})
```

## Time Series Patterns

### OHLCV Resampling

```python
# Tick data to OHLCV bars
def resample_ohlcv(lf: pl.LazyFrame, interval: str) -> pl.LazyFrame:
    return lf.group_by_dynamic(
        "timestamp",
        every=interval,
        group_by="symbol"
    ).agg(
        pl.col("price").first().alias("open"),
        pl.col("price").max().alias("high"),
        pl.col("price").min().alias("low"),
        pl.col("price").last().alias("close"),
        pl.col("volume").sum().alias("volume"),
        pl.col("price").count().alias("trades")
    )

# Usage
bars_1m = resample_ohlcv(trades_lf, "1m").collect()
bars_5m = resample_ohlcv(trades_lf, "5m").collect()
```

### Rolling Statistics

```python
# Efficient rolling calculations
df.with_columns(
    # Simple moving averages
    pl.col("close").rolling_mean(window_size=20).alias("sma_20"),
    pl.col("close").rolling_mean(window_size=50).alias("sma_50"),

    # Volatility (rolling std)
    pl.col("close").pct_change().rolling_std(window_size=20).alias("volatility"),

    # Rolling correlation
    pl.rolling_corr("close", "volume", window_size=20).alias("corr_20"),

    # Exponential moving average
    pl.col("close").ewm_mean(span=20).alias("ema_20"),

    # Bollinger Bands
    (pl.col("close").rolling_mean(20) + 2 * pl.col("close").rolling_std(20)).alias("bb_upper"),
    (pl.col("close").rolling_mean(20) - 2 * pl.col("close").rolling_std(20)).alias("bb_lower")
)
```

### Time-Based Windows

```python
# Rolling by time duration (not row count)
df.with_columns(
    # 5-minute rolling average
    pl.col("price").rolling_mean(
        window_size="5m",
        by="timestamp"
    ).alias("rolling_5m"),

    # Daily high/low
    pl.col("price").rolling_max(
        window_size="1d",
        by="timestamp"
    ).alias("daily_high")
)
```

### Lag/Lead for Returns

```python
df.with_columns(
    # Returns
    pl.col("close").pct_change().alias("ret_1"),
    pl.col("close").pct_change(5).alias("ret_5"),

    # Log returns
    pl.col("close").log().diff().alias("log_ret"),

    # Forward returns (for labels)
    pl.col("close").pct_change().shift(-1).alias("fwd_ret_1"),
    pl.col("close").pct_change(5).shift(-5).alias("fwd_ret_5"),

    # Lagged features
    pl.col("close").shift(1).alias("close_lag_1"),
    pl.col("volume").shift(1).alias("volume_lag_1")
).over("symbol")  # Per-symbol calculations
```

## Financial Data Patterns

### VWAP Calculation

```python
# Volume-Weighted Average Price
def calculate_vwap(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        vwap=(
            (pl.col("price") * pl.col("volume")).cum_sum() /
            pl.col("volume").cum_sum()
        ).over("symbol")
    )
```

### As-Of Joins for Market Data

```python
# Align trades with quotes
trades.join_asof(
    quotes,
    on="timestamp",
    by="symbol",
    strategy="backward"  # Most recent quote before trade
)

# Join with tolerance
trades.join_asof(
    quotes,
    on="timestamp",
    by="symbol",
    strategy="backward",
    tolerance="100ms"  # Only if quote within 100ms
)
```

### Bid-Ask Spread

```python
quotes.with_columns(
    (pl.col("ask") - pl.col("bid")).alias("spread"),
    (((pl.col("ask") - pl.col("bid")) / pl.col("mid")) * 10000).alias("spread_bps"),
    ((pl.col("bid") + pl.col("ask")) / 2).alias("mid")
)
```

### Position/PnL Tracking

```python
# Calculate position and PnL from trades
trades.with_columns(
    # Cumulative position
    pl.col("signed_qty").cum_sum().over("symbol").alias("position"),

    # Mark-to-market PnL
    (
        pl.col("signed_qty") * pl.col("price") * -1
    ).cum_sum().over("symbol").alias("realized_pnl")
)
```

## Large File Processing

### Partitioned Reads

```python
# Read partitioned parquet efficiently
lf = pl.scan_parquet(
    "data/year=*/month=*/*.parquet",
    hive_partitioning=True
)

# Filter on partitions (predicate pushdown)
result = lf.filter(
    (pl.col("year") == 2024) & (pl.col("month") >= 6)
).collect()
```

### Streaming for Massive Files

```python
# Process larger-than-RAM data
lf = pl.scan_csv("massive.csv")

# Streaming aggregation
result = (
    lf.filter(pl.col("value") > threshold)
    .group_by("category")
    .agg(pl.col("value").sum())
    .collect(engine="streaming")
)

# Streaming write
lf.filter(pl.col("value") > threshold).sink_parquet("output.parquet")
```

### Chunked Processing

```python
# Process in chunks when streaming not possible
def process_in_chunks(path: str, chunk_size: int = 1_000_000):
    results = []
    reader = pl.read_csv_batched(path, batch_size=chunk_size)

    while True:
        batch = reader.next_batches(1)
        if batch is None:
            break
        # Process each batch
        result = process_batch(batch[0])
        results.append(result)

    return pl.concat(results)
```

### Multi-File Processing

```python
# Parallel file reading
lf = pl.scan_parquet("data/*.parquet")  # Reads files in parallel

# Or explicit list
files = ["data1.parquet", "data2.parquet", "data3.parquet"]
lf = pl.scan_parquet(files)

# With schema enforcement
lf = pl.scan_parquet(
    "data/*.parquet",
    schema=expected_schema
)
```

## Memory Optimization

### Dtype Selection

```python
# Read with optimal types
df = pl.read_csv(
    "data.csv",
    dtypes={
        "trade_id": pl.UInt32,      # Not Int64 if fits
        "symbol": pl.Categorical,   # Not String for symbols
        "side": pl.Categorical,     # "buy"/"sell" -> Categorical
        "price": pl.Float32,        # Float32 if precision OK
        "quantity": pl.UInt32,      # Unsigned if always positive
    }
)
```

### Downcast After Load

```python
def optimize_dtypes(df: pl.DataFrame) -> pl.DataFrame:
    """Downcast numeric columns to smallest fitting type."""
    for col in df.columns:
        dtype = df[col].dtype
        if dtype in [pl.Int64, pl.Int32]:
            min_val, max_val = df[col].min(), df[col].max()
            if min_val >= 0:
                if max_val <= 255:
                    df = df.with_columns(pl.col(col).cast(pl.UInt8))
                elif max_val <= 65535:
                    df = df.with_columns(pl.col(col).cast(pl.UInt16))
                elif max_val <= 4294967295:
                    df = df.with_columns(pl.col(col).cast(pl.UInt32))
    return df
```

### Categorical for Low Cardinality

```python
# Identify candidates
for col in df.columns:
    if df[col].dtype == pl.Utf8:
        n_unique = df[col].n_unique()
        total = len(df)
        if n_unique / total < 0.5:  # Less than 50% unique
            print(f"{col}: {n_unique} unique / {total} total - use Categorical")
```

## Expression Patterns

### Reusable Expression Library

```python
# Define expression library for your domain
class FinanceExpr:
    @staticmethod
    def returns(col: str = "close") -> pl.Expr:
        return pl.col(col).pct_change()

    @staticmethod
    def log_returns(col: str = "close") -> pl.Expr:
        return pl.col(col).log().diff()

    @staticmethod
    def volatility(col: str = "close", window: int = 20) -> pl.Expr:
        return pl.col(col).pct_change().rolling_std(window)

    @staticmethod
    def sharpe(returns_col: str, rf: float = 0.0, window: int = 252) -> pl.Expr:
        excess = pl.col(returns_col) - rf / 252
        return (
            excess.rolling_mean(window) /
            excess.rolling_std(window) *
            (252 ** 0.5)
        )

# Usage
df.with_columns(
    ret=FinanceExpr.returns(),
    vol=FinanceExpr.volatility(window=20),
    sharpe=FinanceExpr.sharpe("ret", window=60)
)
```

### Conditional Aggregations

```python
# Complex conditional aggregations
df.group_by("symbol").agg(
    # Count by condition
    up_days=(pl.col("close") > pl.col("open")).sum(),
    down_days=(pl.col("close") < pl.col("open")).sum(),

    # Conditional averages
    pl.col("volume").filter(
        pl.col("close") > pl.col("open")
    ).mean().alias("avg_up_volume"),

    # Weighted conditionals
    vwap_up=(
        pl.when(pl.col("close") > pl.col("open"))
        .then(pl.col("price") * pl.col("volume"))
        .otherwise(0)
        .sum() /
        pl.when(pl.col("close") > pl.col("open"))
        .then(pl.col("volume"))
        .otherwise(0)
        .sum()
    )
)
```

### Pipeline Functions

```python
def clean_market_data(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Standard market data cleaning pipeline."""
    return (
        lf
        .filter(pl.col("price") > 0)
        .filter(pl.col("volume") > 0)
        .with_columns(
            pl.col("timestamp").cast(pl.Datetime),
            pl.col("symbol").cast(pl.Categorical)
        )
        .sort("symbol", "timestamp")
        .unique(subset=["symbol", "timestamp"], keep="last")
    )

def add_technical_features(lf: pl.LazyFrame) -> pl.LazyFrame:
    """Add standard technical indicators."""
    return lf.with_columns(
        pl.col("close").pct_change().over("symbol").alias("returns"),
        pl.col("close").rolling_mean(20).over("symbol").alias("sma_20"),
        pl.col("close").rolling_std(20).over("symbol").alias("volatility_20")
    )

# Compose pipeline
result = (
    pl.scan_parquet("trades/*.parquet")
    .pipe(clean_market_data)
    .pipe(add_technical_features)
    .collect()
)
```
