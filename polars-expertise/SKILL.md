---
name: polars-expertise
description: >
  This skill should be used when the user asks about Polars DataFrame library
  (Apache Arrow) for Python or Rust. Triggers: "polars expressions", "lazy vs eager",
  "scan_parquet streaming", "convert pandas to polars", "pyspark to polars",
  "kdb to polars", "group_by_dynamic", "rolling_mean", "polars window functions",
  "asof join", "polars GPU", "polars parquet", "LazyFrame". Time series: OHLCV
  resampling, rolling windows, financial data patterns. Performance: native
  expressions over map_elements, early projection, categorical types, streaming.
---

# Polars

High-performance DataFrame library built on Apache Arrow. Supports Python and Rust with expression-based API, lazy evaluation, and automatic parallelization.

## Quick Start

### Python

```bash
uv pip install polars
# GPU support: uv pip install polars[gpu]
```

```python
import polars as pl

# Eager: immediate execution
df = pl.DataFrame({"symbol": ["AAPL", "GOOG"], "price": [150.0, 140.0]})
df.filter(pl.col("price") > 145).select("symbol", "price")

# Lazy: optimized execution (preferred for large data)
lf = pl.scan_parquet("trades.parquet")
result = lf.filter(pl.col("volume") > 1000).group_by("symbol").agg(
    pl.col("price").mean().alias("avg_price")
).collect()
```

### Rust

```toml
# Cargo.toml - select features you need
[dependencies]
polars = { version = "0.46", features = ["lazy", "parquet", "temporal"] }
```

```rust
use polars::prelude::*;

fn main() -> PolarsResult<()> {
    // Eager
    let df = df![
        "symbol" => ["AAPL", "GOOG"],
        "price" => [150.0, 140.0]
    ]?;

    // Lazy (preferred)
    let lf = LazyFrame::scan_parquet("trades.parquet", Default::default())?;
    let result = lf
        .filter(col("volume").gt(lit(1000)))
        .group_by([col("symbol")])
        .agg([col("price").mean().alias("avg_price")])
        .collect()?;
    Ok(())
}
```

## Core Pattern: Expressions

Everything in Polars is an expression. Expressions are composable, lazy, and parallelized.

```python
# Expression building blocks
pl.col("price")                      # column reference
pl.col("price") * pl.col("volume")   # arithmetic
pl.col("price").mean().over("symbol") # window function
pl.when(cond).then(a).otherwise(b)   # conditional
```

Expressions execute in contexts: `select()`, `with_columns()`, `filter()`, `group_by().agg()`

## When to Use Lazy

| Use Lazy (`scan_*`, `.lazy()`) | Use Eager (`read_*`) |
|-------------------------------|----------------------|
| Large files (> RAM) | Small data, exploration |
| Complex pipelines | Simple one-off ops |
| Need query optimization | Interactive notebooks |
| Streaming required | Immediate feedback |

Lazy benefits: predicate pushdown, projection pushdown, parallel execution, streaming.

## Style: Use `.alias()` for Column Naming

Always use `.alias("name")` instead of `name=expr` kwargs:

```python
# GOOD: Explicit .alias() - works everywhere, composable
df.with_columns(
    (pl.col("price") * pl.col("volume")).alias("value"),
    pl.col("price").mean().over("symbol").alias("avg_price")
)

# AVOID: Kwarg style - less flexible, doesn't chain
df.with_columns(
    value=pl.col("price") * pl.col("volume"),  # avoid
    avg_price=pl.col("price").mean().over("symbol")  # avoid
)
```

`.alias()` is explicit, chains with other methods, and works consistently in all contexts.

## Anti-Patterns - AVOID

```python
# BAD: Python functions kill parallelization
df.with_columns(pl.col("x").map_elements(lambda x: x * 2))  # SLOW

# GOOD: Native expressions are parallel
df.with_columns((pl.col("x") * 2).alias("x"))  # FAST

# BAD: Row iteration
for row in df.iter_rows():  # SLOW
    process(row)

# GOOD: Columnar operations
df.with_columns(process_expr)  # FAST

# BAD: Late projection
lf.filter(...).collect().select("a", "b")  # reads all columns

# GOOD: Early projection
lf.select("a", "b").filter(...).collect()  # reads only needed columns
```

## Performance Checklist

- [ ] Using `scan_*` (lazy) for large files?
- [ ] Projecting columns early in pipeline?
- [ ] Using native expressions (no `map_elements`)?
- [ ] Categorical dtype for low-cardinality strings?
- [ ] Appropriate integer sizes (i32 vs i64)?
- [ ] Streaming for out-of-memory data? (`collect(engine="streaming")`)

## Reference Navigator

### Python References

| Topic | File | When to Load |
|-------|------|--------------|
| Expressions, types, lazy/eager | [python/core_concepts.md](references/python/core_concepts.md) | Understanding fundamentals |
| Select, filter, group_by, window | [python/operations.md](references/python/operations.md) | Common operations |
| CSV, Parquet, streaming I/O | [python/io_guide.md](references/python/io_guide.md) | Reading/writing data |
| Joins, pivots, reshaping | [python/transformations.md](references/python/transformations.md) | Combining/reshaping data |
| Performance, patterns | [python/best_practices.md](references/python/best_practices.md) | Optimization |

### Rust References

| Topic | File | When to Load |
|-------|------|--------------|
| DataFrame, Series, ChunkedArray | [rust/core_concepts.md](references/rust/core_concepts.md) | Rust API fundamentals |
| Expression API in Rust | [rust/operations.md](references/rust/operations.md) | Operations syntax |
| Readers, writers, streaming | [rust/io_guide.md](references/rust/io_guide.md) | I/O operations |
| Feature flags, crates | [rust/features.md](references/rust/features.md) | Cargo setup |
| Allocators, SIMD, nightly | [rust/performance.md](references/rust/performance.md) | Performance tuning |
| Zero-copy, FFI, Arrow | [rust/arrow_interop.md](references/rust/arrow_interop.md) | Arrow integration |

### Shared References

| Topic | File | When to Load |
|-------|------|--------------|
| SQL queries on DataFrames | [sql_interface.md](references/sql_interface.md) | SQL syntax needed |
| Query optimization, streaming | [lazy_deep_dive.md](references/lazy_deep_dive.md) | Understanding lazy engine |
| NVIDIA GPU acceleration | [gpu_support.md](references/gpu_support.md) | GPU setup/usage |

### Migration Guides

| From | File | When to Load |
|------|------|--------------|
| pandas | [migration_pandas.md](references/migration_pandas.md) | Converting pandas code |
| PySpark | [migration_spark.md](references/migration_spark.md) | Converting Spark code |
| q/kdb+ | [migration_qkdb.md](references/migration_qkdb.md) | Converting kdb code |

## Time Series / Financial Data Quick Patterns

```python
# OHLCV resampling
df.group_by_dynamic("timestamp", every="1m").agg(
    pl.col("price").first().alias("open"),
    pl.col("price").max().alias("high"),
    pl.col("price").min().alias("low"),
    pl.col("price").last().alias("close"),
    pl.col("volume").sum()
)

# Rolling statistics
df.with_columns(
    pl.col("price").rolling_mean(window_size=20).alias("sma_20"),
    pl.col("price").rolling_std(window_size=20).alias("volatility")
)

# As-of join for market data alignment
trades.join_asof(quotes, on="timestamp", by="symbol", strategy="backward")
```

Load [python/best_practices.md](references/python/best_practices.md) for comprehensive time series patterns.

## Runnable Examples

| Example | File | Purpose |
|---------|------|---------|
| Financial OHLCV | [examples/financial_ohlcv.py](examples/financial_ohlcv.py) | OHLCV resampling, rolling stats, VWAP |
| Pandas Migration | [examples/pandas_migration.py](examples/pandas_migration.py) | Side-by-side pandas vs polars |
| Streaming Large Files | [examples/streaming_large_file.py](examples/streaming_large_file.py) | Out-of-memory processing patterns |

## Development Tips

Use LSP for navigating Polars code:
- **Python**: Pyright/Pylance provides excellent type inference for Polars expressions
- **Rust**: rust-analyzer understands Polars types and expression chains

LSP operations like `goToDefinition` and `hover` help explore Polars API without leaving the editor.
