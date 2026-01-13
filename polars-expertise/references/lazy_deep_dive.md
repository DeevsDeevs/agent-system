# Lazy Evaluation Deep Dive

Polars lazy evaluation builds a query graph that gets optimized before execution. This reference covers the optimization internals, query plans, and advanced lazy patterns.

## Query Optimization Overview

| Optimization | What It Does | When Applied |
|--------------|--------------|--------------|
| Predicate pushdown | Applies filters at scan level | 1 time |
| Projection pushdown | Selects only needed columns at scan | 1 time |
| Slice pushdown | Loads only required rows (e.g., head/limit) | 1 time |
| Common subplan elimination | Caches shared subtrees/file scans | 1 time |
| Expression simplification | Constant folding, operation substitution | Until fixed point |
| Join ordering | Determines optimal join execution order | 1 time |
| Type coercion | Minimal memory type conversions | Until fixed point |
| Cardinality estimation | Optimal group_by strategy selection | Query-dependent |

## Query Plans

### Viewing Plans

```python
import polars as pl

lf = (
    pl.scan_csv("trades.csv")
    .filter(pl.col("volume") > 1000000)
    .select("symbol", "price", "volume")
    .group_by("symbol")
    .agg(pl.col("price").mean())
)

# Non-optimized plan (what you wrote)
print(lf.explain(optimized=False))

# Optimized plan (what executes)
print(lf.explain())

# Visual graph (requires Graphviz)
lf.show_graph(optimized=True)
```

### Reading Query Plans

Plans read bottom-to-top. Common symbols:
- `sigma` (σ): SELECTION (filter)
- `pi` (π): PROJECTION (column selection)
- `CSV SCAN`: Data source

**Non-optimized plan:**
```
FILTER [(col("volume")) > (1000000)] FROM
  SELECT [col("symbol"), col("price"), col("volume")] FROM
    CSV SCAN trades.csv
    PROJECT */6 COLUMNS
```

**Optimized plan (predicate + projection pushdown):**
```
GROUP_BY [col("symbol")] FROM
  CSV SCAN trades.csv
  PROJECT 3/6 COLUMNS  # Only needed columns
  SELECTION: [(col("volume")) > (1000000)]  # Filter at scan
```

## Optimization Details

### Predicate Pushdown

Filters move to data source level:

```python
# Filter happens during CSV read, not after
lf = (
    pl.scan_csv("large_trades.csv")
    .filter(pl.col("date") >= "2024-01-01")  # Pushed to scan
    .filter(pl.col("volume") > 100000)       # Also pushed
)
```

**Works with:**
- File scans (CSV, Parquet, IPC)
- Joins (pushes to appropriate side)
- Unions

**Blocked by:**
- Aggregations (filter after group_by cannot push through)
- User-defined functions

### Projection Pushdown

Only reads required columns:

```python
# Only symbol and price columns read from disk
lf = (
    pl.scan_parquet("trades.parquet")  # Has 20 columns
    .select("symbol", "price")          # Only 2 needed
    .filter(pl.col("price") > 100)
)
```

**Parquet/IPC benefit**: Column-oriented formats skip entire column chunks.

### Slice Pushdown

Limits data loading for head/tail operations:

```python
# Reads only ~100 rows, not entire file
lf = (
    pl.scan_csv("huge.csv")
    .filter(pl.col("valid") == True)
    .head(100)  # Slice pushes to limit rows read
)
```

**Works with:**
- `.head()`, `.tail()`, `.slice()`
- `.limit()` in SQL

### Common Subplan Elimination

Shared subqueries execute once:

```python
expensive_lf = (
    pl.scan_parquet("market_data.parquet")
    .filter(pl.col("date") >= "2024-01-01")
    .with_columns(
        pl.col("price").rolling_mean(20).alias("ma_20")
    )
)

# Both branches share expensive_lf - computed once
summary = expensive_lf.group_by("symbol").agg(pl.col("price").mean())
detail = expensive_lf.filter(pl.col("price") > pl.col("ma_20"))

# collect_all ensures single computation
results = pl.collect_all([summary, detail])
```

## Execution Modes

### Standard Collection

```python
# Full dataset in memory
df = lf.collect()
```

### Streaming Mode

Processes data in batches for larger-than-memory datasets:

```python
# Streaming execution
df = lf.collect(engine="streaming")
```

**Inspecting streaming plans:**
```python
# Physical plan shows memory intensity
lf.show_graph(streaming=True)
```

**Streaming-compatible operations:**
- Scans, filters, projections
- Most aggregations
- Sorted joins

**Not streaming-compatible (require full materialization):**
- Unsorted joins
- Some window functions
- Sort on unsorted data

### GPU Execution

```python
# Execute on NVIDIA GPU (requires polars[gpu])
df = lf.collect(engine="gpu")
```

### Partial Execution

For development/debugging on large datasets:

```python
# Sample during development
df = lf.head(1000).collect()

# Or limit at scan
lf = pl.scan_parquet("huge.parquet").head(10000)
result = lf.filter(...).collect()
```

## Diverging Queries Pattern

When one lazy computation feeds multiple downstream queries:

```python
# Base expensive computation
base_lf = (
    pl.scan_parquet("trades.parquet")
    .with_columns(
        pl.col("price").pct_change().alias("returns")
    )
)

# Diverging queries
stats_lf = base_lf.group_by("symbol").agg(
    pl.col("returns").mean(),
    pl.col("returns").std()
)

filtered_lf = base_lf.filter(pl.col("returns").abs() > 0.05)

# CRITICAL: Use collect_all to avoid recomputation
stats_df, filtered_df = pl.collect_all([stats_lf, filtered_lf])
# base_lf computed only once!

# BAD: Separate collects recompute base_lf each time
# stats_df = stats_lf.collect()      # Computes base_lf
# filtered_df = filtered_lf.collect() # Computes base_lf AGAIN
```

## LazyFrame Caching Gotchas

LazyFrames are query plans, not cached data:

```python
# WARNING: This recomputes on each use
lf = pl.scan_parquet("data.parquet").filter(...)

result1 = lf.select("a").collect()  # Scans + filters
result2 = lf.select("b").collect()  # Scans + filters AGAIN

# SOLUTION 1: Collect once, then operate on DataFrame
df = lf.collect()
result1 = df.select("a")
result2 = df.select("b")

# SOLUTION 2: Use collect_all for lazy branches
lf1 = lf.select("a")
lf2 = lf.select("b")
result1, result2 = pl.collect_all([lf1, lf2])  # Single scan
```

## Advanced Patterns

### Lazy Schema Inspection

```python
lf = pl.scan_parquet("data.parquet")

# Get schema without loading data
print(lf.collect_schema())

# Get column names
print(lf.collect_schema().names())
```

### Lazy with Sink Operations

Write results directly to files without full materialization:

```python
# Sink to Parquet (streaming write)
lf.sink_parquet("output.parquet")

# Sink to IPC
lf.sink_ipc("output.ipc")

# Sink to CSV
lf.sink_csv("output.csv")
```

### Profile Query Execution

```python
# Returns DataFrame with timing info
df, profile = lf.profile()
print(profile)
```

### Explain Physical Plan

```python
# Logical plan (default)
print(lf.explain())

# Physical plan with more detail
print(lf.explain(physical=True))
```

## Optimization Control

### Disable Specific Optimizations

```python
# For debugging or specific requirements
df = lf.collect(
    predicate_pushdown=False,  # Keep filters where written
    projection_pushdown=False,  # Read all columns
    slice_pushdown=False,       # No slice optimization
    comm_subplan_elim=False     # No subplan caching
)
```

### Force Optimization Barrier

```python
# cache() materializes intermediate result
lf = (
    pl.scan_parquet("data.parquet")
    .filter(...)
    .cache()  # Forces materialization here
    .group_by(...)
    .agg(...)
)
```

## Rust Lazy API

```rust
use polars::prelude::*;

fn main() -> PolarsResult<()> {
    let lf = LazyCsvReader::new("trades.csv")
        .finish()?
        .filter(col("volume").gt(lit(1000000)))
        .select([col("symbol"), col("price")])
        .group_by([col("symbol")])
        .agg([col("price").mean()]);

    // View plan
    println!("{}", lf.explain(true)?);

    // Execute
    let df = lf.collect()?;

    Ok(())
}
```

## Best Practices

1. **Start lazy, end eager**: Use `scan_*` functions, collect only when needed
2. **Check plans**: Use `explain()` to verify optimizations work
3. **Use `collect_all`**: For diverging queries from same source
4. **Sink for ETL**: Use `sink_*` for write-heavy pipelines
5. **Profile in production**: Use `.profile()` to find bottlenecks
6. **Streaming for big data**: Set `engine="streaming"` for larger-than-memory
7. **Don't reuse LazyFrames**: They recompute each time - use `collect_all` or materialize
