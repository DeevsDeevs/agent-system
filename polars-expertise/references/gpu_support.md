# GPU Support

Polars provides GPU-accelerated execution for the Lazy API on NVIDIA GPUs using RAPIDS cuDF. Currently in Open Beta.

## System Requirements

| Requirement | Specification |
|-------------|---------------|
| GPU | NVIDIA Volta or higher (compute capability 7.0+) |
| CUDA | CUDA 12 (CUDA 11 deprecated - ends with RAPIDS v25.06) |
| OS | Linux or Windows Subsystem for Linux 2 (WSL2) |
| Memory | GPU RAM sufficient for your workload (80GB handles 50-100GB raw data) |

## Installation

See SKILL.md for base installation. For GPU support:

```bash
uv pip install polars[gpu]

# CUDA 11 (deprecated, ends with RAPIDS v25.08):
uv pip install polars cudf-polars-cu11==25.06
```

## Basic Usage

### Simple GPU Execution

```python
import polars as pl

# Build query with lazy API (required for GPU)
lf = (
    pl.scan_parquet("trades.parquet")
    .filter(pl.col("volume") > 1000000)
    .group_by("symbol")
    .agg(
        pl.col("price").mean().alias("avg_price"),
        pl.col("volume").sum().alias("total_volume")
    )
)

# Execute on GPU
result = lf.collect(engine="gpu")
```

### GPU Engine Configuration

```python
# Select specific GPU on multi-GPU system
result = lf.collect(engine=pl.GPUEngine(device=1))

# Disable CPU fallback - raises exception if unsupported
result = lf.collect(engine=pl.GPUEngine(raise_on_fail=True))
```

## Supported Operations

### Supported

| Category | Operations |
|----------|------------|
| API | LazyFrame, SQL |
| I/O | CSV, Parquet, ndjson, in-memory DataFrames |
| Data Types | Numeric, logical, string, datetime |
| Operations | Filters, aggregations (grouped/rolling), joins, concatenation |
| String | Full string processing |
| Missing Data | Null handling |

### Not Supported (Falls Back to CPU)

| Category | Details |
|----------|---------|
| API | Eager DataFrame, Streaming |
| Data Types | Date, Categorical, Enum, Time, Array, Binary, Object |
| Operations | Time series resampling, folds, user-defined functions |
| I/O | Excel, database formats |
| Other | Datetime with timezone (some expressions), List (some expressions) |

## Diagnosing GPU Usage

### Verbose Mode - Fallback Warnings

```python
import polars as pl

lf = (
    pl.scan_parquet("data.parquet")
    .with_columns(
        pl.col("value").rolling_mean(10).over("group")  # Not GPU-supported
    )
)

with pl.Config() as cfg:
    cfg.set_verbose(True)
    result = lf.collect(engine="gpu")
    # Prints: PerformanceWarning: Query execution with GPU not supported...
```

### Force Failure for Unsupported Operations

```python
try:
    result = lf.collect(engine=pl.GPUEngine(raise_on_fail=True))
except pl.exceptions.ComputeError as e:
    print(f"GPU execution failed: {e}")
```

## When to Use GPU

### GPU Excels At

| Workload | Reason |
|----------|--------|
| Grouped aggregations | Massive parallelism |
| Large joins | GPU memory bandwidth |
| Heavy computations | CUDA acceleration |
| Multiple operations in single query | Amortizes GPU overhead |

### CPU May Be Better

| Workload | Reason |
|----------|--------|
| I/O-bound queries | GPU won't help disk/network bottleneck |
| Small datasets | GPU overhead not worth it |
| Unsupported operations | Frequent fallback adds overhead |
| Data larger than GPU RAM | Out-of-memory errors |

## Interoperability

### CPU-GPU Data Flow

```python
# GPU results are standard CPU DataFrames
gpu_result = lf.collect(engine="gpu")
type(gpu_result)  # polars.DataFrame (CPU-backed)

# Files written by GPU engine readable by CPU
lf.sink_parquet("output.parquet")  # Works with both engines
```

### Transparent Fallback

```python
# Fallback is automatic unless raise_on_fail=True
result = lf.collect(engine="gpu")
# If any operation unsupported -> falls back to CPU engine
# Query still completes, just without GPU acceleration
```

## Financial Data Patterns

### VWAP Calculation (GPU-Compatible)

```python
lf = (
    pl.scan_parquet("trades.parquet")
    .group_by("symbol")
    .agg(
        (pl.col("price") * pl.col("volume")).sum() / pl.col("volume").sum()
    ).alias("vwap")
)
result = lf.collect(engine="gpu")
```

### Daily Stats (GPU-Compatible)

```python
lf = (
    pl.scan_parquet("trades.parquet")
    .with_columns(pl.col("timestamp").dt.date().alias("date"))
    .group_by("symbol", "date")
    .agg(
        pl.col("price").max().alias("high"),
        pl.col("price").min().alias("low"),
        pl.col("price").first().alias("open"),
        pl.col("price").last().alias("close"),
        pl.col("volume").sum().alias("volume")
    )
)
result = lf.collect(engine="gpu")
```

### Rolling Statistics (May Fall Back)

```python
# Grouped rolling window - NOT GPU supported
lf = (
    pl.scan_parquet("trades.parquet")
    .with_columns(
        pl.col("price").rolling_mean(20).over("symbol")  # CPU fallback
    )
)

# Simple rolling (no grouping) - may work
lf = (
    pl.scan_parquet("trades.parquet")
    .with_columns(
        pl.col("price").rolling_mean(20)  # Check support
    )
)
```

## Best Practices

1. **Profile first**: Compare GPU vs CPU on your actual queries
2. **Keep data on GPU**: Minimize CPU-GPU transfers in a pipeline
3. **Batch queries**: Combine operations to amortize GPU overhead
4. **Check support**: Use `raise_on_fail=True` during development
5. **Monitor memory**: GPU OOM is common with large datasets
6. **Use verbose mode**: Identify fallback operations

## Troubleshooting

### ImportError on gpu engine

```bash
uv pip install polars[gpu]  # Missing cudf-polars
```

### CUDA version mismatch

```bash
nvcc --version  # Check CUDA version
uv pip install cudf-polars-cu12  # for CUDA 12
```

### Out of Memory

```python
# Split large queries or use streaming (CPU only)
lf1 = lf.filter(pl.col("date") < "2024-06-01")
lf2 = lf.filter(pl.col("date") >= "2024-06-01")
r1 = lf1.collect(engine="gpu")
r2 = lf2.collect(engine="gpu")
result = pl.concat([r1, r2])
```

### Performance Not Improved

Check for fallback operations:
```python
with pl.Config() as cfg:
    cfg.set_verbose(True)
    result = lf.collect(engine="gpu")
# Look for PerformanceWarning messages
```

## Test Coverage

- 99.2% of Polars unit tests pass with CPU fallback
- 88.8% pass without fallback
- Remaining failures mostly involve debug output differences or type variations
