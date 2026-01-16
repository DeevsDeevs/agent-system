# Polars Core Concepts (Python)

## Table of Contents
- [Expressions](#expressions)
- [Data Types](#data-types)
- [Lazy vs Eager Evaluation](#lazy-vs-eager-evaluation)
- [Streaming Mode](#streaming-mode)
- [Parallelization](#parallelization)

## Expressions

Expressions are the foundation of Polars. They describe transformations without executing immediately.

### Expression Contexts

Expressions only execute within specific contexts:

```python
import polars as pl

df = pl.DataFrame({
    "symbol": ["AAPL", "GOOG", "AAPL", "GOOG"],
    "price": [150.0, 140.0, 151.0, 141.0],
    "volume": [1000, 2000, 1500, 2500]
})

# select() - choose and transform columns
df.select("symbol", pl.col("price") * pl.col("volume"))

# with_columns() - add/modify while preserving existing
df.with_columns(
    (pl.col("price") * pl.col("volume")).alias("notional"),
    pl.col("price").pct_change().over("symbol").alias("price_pct")
)

# filter() - row selection
df.filter(pl.col("volume") > 1500)

# group_by().agg() - aggregation
df.group_by("symbol").agg(
    pl.col("price").mean().alias("avg_price"),
    pl.col("volume").sum().alias("total_volume")
)
```

### Expression Composition

Expressions can be stored and reused:

```python
# Define reusable expressions for financial calculations
vwap = (pl.col("price") * pl.col("volume")).sum() / pl.col("volume").sum()
volatility = pl.col("price").std() / pl.col("price").mean()
returns = pl.col("price").pct_change()

# Use in multiple contexts
df.group_by("symbol").agg(
    vwap.alias("vwap"),
    volatility.alias("volatility")
)
```

### Expression Expansion

Apply operations to multiple columns:

```python
# All numeric columns
df.select(pl.col(pl.NUMERIC_DTYPES) * 100)

# Pattern matching
df.select(pl.col("^bid_.*$") - pl.col("^ask_.*$"))  # Spread calculation

# Exclude patterns
df.select(pl.all().exclude("timestamp", "id"))
```

## Data Types

### Core Types

| Type | Python | Use Case |
|------|--------|----------|
| Int64/Int32 | `pl.Int64` | Trade IDs, counts |
| Float64 | `pl.Float64` | Prices, returns |
| Utf8/String | `pl.Utf8` | Symbols, names |
| Datetime | `pl.Datetime` | Timestamps |
| Date | `pl.Date` | Calendar dates |
| Duration | `pl.Duration` | Time differences |
| Categorical | `pl.Categorical` | Low-cardinality strings |
| List | `pl.List` | Variable-length arrays |

### Type Casting

```python
df.with_columns(
    # Downcast for memory efficiency
    pl.col("trade_id").cast(pl.UInt32),

    # Parse timestamps
    pl.col("timestamp_str").str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S%.f"),

    # Categorical for symbols (faster grouping)
    pl.col("symbol").cast(pl.Categorical)
)
```

### Null Handling

```python
# Check nulls
df.filter(pl.col("price").is_not_null())

# Fill strategies
df.with_columns(
    # Forward fill (common for market data)
    pl.col("price").fill_null(strategy="forward"),

    # Fill with group mean
    pl.col("price").fill_null(pl.col("price").mean().over("symbol")),

    # Interpolate
    pl.col("price").interpolate()
)
```

## Lazy vs Eager Evaluation

### When to Use Each

| Lazy (`scan_*`, `.lazy()`) | Eager (`read_*`) |
|---------------------------|------------------|
| Large files (>1GB) | Small exploration |
| Complex pipelines | Interactive work |
| Production jobs | Quick analysis |
| Memory constrained | Simple one-offs |

### Lazy Example

```python
# Lazy: builds query plan, optimizes, then executes
lf = (
    pl.scan_parquet("trades/*.parquet")
    .filter(pl.col("symbol") == "AAPL")
    .filter(pl.col("timestamp") >= "2024-01-01")
    .group_by_dynamic("timestamp", every="1m")
    .agg(
        pl.col("price").first().alias("open"),
        pl.col("price").max().alias("high"),
        pl.col("price").min().alias("low"),
        pl.col("price").last().alias("close"),
        pl.col("volume").sum()
    )
)

# View optimized plan
print(lf.explain())

# Execute
df = lf.collect()
```

### Query Optimization

Polars automatically applies:

| Optimization | Effect |
|-------------|--------|
| Predicate pushdown | Filters at scan level |
| Projection pushdown | Reads only needed columns |
| Slice pushdown | Limits rows early |
| Common subplan elimination | Caches repeated subqueries |
| Join ordering | Optimizes join sequence |

```python
# Example: only reads symbol="AAPL" rows and price/volume columns
lf = (
    pl.scan_parquet("trades.parquet")
    .filter(pl.col("symbol") == "AAPL")  # Pushed to scan
    .select("price", "volume")            # Only these columns read
)
```

## Streaming Mode

Process data larger than RAM:

```python
# Streaming execution
lf = pl.scan_csv("massive_file.csv")
result = lf.filter(pl.col("value") > 100).collect(engine="streaming")

# Streaming write (sink)
lf.filter(pl.col("value") > 100).sink_parquet("output.parquet")

# Check streaming compatibility
print(lf.explain(streaming=True))
```

### Streaming Limitations

Operations that may not stream:
- Sorts on large data
- Some join types
- Certain aggregations

Polars falls back to in-memory automatically when needed.

## Parallelization

### Automatic Parallelization

Polars parallelizes:
- Aggregations within groups
- Window functions
- Expression evaluations
- Multi-file reads

### What Kills Parallelization

```python
# BAD: Python UDF - sequential, slow
df.with_columns(
    pl.col("price").map_elements(lambda x: custom_func(x))  # AVOID
)

# GOOD: Native expressions - parallel, fast
df.with_columns(
    pl.col("price") * 1.1  # Parallelized
)

# BAD: Row iteration
for row in df.iter_rows():  # AVOID
    process(row)

# GOOD: Columnar operations
df.with_columns(processed=process_expr)
```

### Thread Pool Configuration

```python
import os

# Set before importing polars
os.environ["POLARS_MAX_THREADS"] = "8"

# Or check current setting
import polars as pl
print(pl.thread_pool_size())
```

## Memory Format

Polars uses Apache Arrow columnar format:

- Zero-copy sharing with other Arrow libraries
- Efficient SIMD vectorization
- Reduced memory overhead
- Fast serialization

```python
# Check DataFrame memory usage
print(f"Size: {df.estimated_size('mb'):.2f} MB")

# Convert to Arrow
arrow_table = df.to_arrow()

# From Arrow (zero-copy when possible)
df = pl.from_arrow(arrow_table)
```
