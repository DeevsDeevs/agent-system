# Polars Feature Flags (Rust)

## Table of Contents
- [Feature System Overview](#feature-system-overview)
- [Core Features](#core-features)
- [I/O Features](#io-features)
- [Data Type Features](#data-type-features)
- [Operation Features](#operation-features)
- [Performance Features](#performance-features)
- [Common Configurations](#common-configurations)

## Feature System Overview

Polars uses Rust's feature flags to reduce compile times and binary size. Only enable what you need.

### Minimal Setup

```toml
[dependencies]
polars = "0.46"  # Uses default features
```

Default features include: `docs`, `zip_with`, `csv`, `parquet`, `temporal`, `fmt`, `dtype-slim`

### Custom Feature Selection

```toml
[dependencies]
polars = { version = "0.46", default-features = false, features = [
    "lazy",
    "parquet",
    "temporal",
    "dtype-datetime"
] }
```

## Core Features

### Lazy API

```toml
features = ["lazy"]  # Required for LazyFrame
```

Enables:
- `LazyFrame` and query optimization
- Expression DSL (`col()`, `lit()`, etc.)
- Streaming execution

```rust
use polars::prelude::*;

// Requires "lazy" feature
let lf = LazyFrame::scan_parquet("data.parquet", Default::default())?;
let result = lf.filter(col("x").gt(lit(10))).collect()?;
```

### SQL Support

```toml
features = ["sql"]
```

```rust
use polars::prelude::*;
use polars::sql::SQLContext;

let mut ctx = SQLContext::new();
ctx.register("df", df.lazy());
let result = ctx.execute("SELECT * FROM df WHERE x > 10")?.collect()?;
```

### Regex Support

```toml
features = ["lazy", "regex"]
```

```rust
// Column selection by regex
df.lazy().select([col("^sales_.*$")])
```

## I/O Features

| Feature | Description |
|---------|-------------|
| `csv` | CSV reading/writing |
| `parquet` | Parquet format (recommended) |
| `ipc` | Arrow IPC format |
| `ipc_streaming` | Streaming IPC |
| `json` | JSON reading/writing |
| `avro` | Apache Avro format |
| `decompress` | Auto-decompress gzip/zlib/zstd |

### Cloud Storage

```toml
features = ["cloud"]  # Base cloud support
features = ["aws"]    # AWS S3
features = ["azure"]  # Azure Blob
features = ["gcp"]    # Google Cloud Storage
features = ["http"]   # HTTP sources
```

```rust
// Requires "aws" feature
let lf = LazyFrame::scan_parquet("s3://bucket/data.parquet", Default::default())?;
```

## Data Type Features

### Minimal Set (dtype-slim)

```toml
features = ["dtype-slim"]  # Included in default
```

Includes: `Date`, `Datetime`, `Duration`

### Full Set (dtype-full)

```toml
features = ["dtype-full"]
```

Includes all optional types:
- `dtype-date`, `dtype-datetime`, `dtype-duration`, `dtype-time`
- `dtype-array` (fixed-size arrays)
- `dtype-i8`, `dtype-i16`, `dtype-i128`
- `dtype-u8`, `dtype-u16`, `dtype-u128`
- `dtype-f16`
- `dtype-decimal`
- `dtype-categorical`
- `dtype-struct`

### Individual Type Features

```toml
# Enable only what you need
features = [
    "dtype-datetime",
    "dtype-categorical",
    "dtype-struct"
]
```

**Note:** If you get compile errors about missing types, you likely need to enable the corresponding dtype feature.

## Operation Features

### DataFrame Operations

| Feature | Description |
|---------|-------------|
| `rows` | Row-based operations, pivot, transpose |
| `pivot` | Pivot tables (requires `rows`, `dtype-struct`) |
| `asof_join` | As-of joins for time series |
| `cross_join` | Cartesian product joins |
| `semi_anti_join` | Semi and anti joins |
| `dynamic_group_by` | Time-based group by |
| `partition_by` | Partition DataFrame by groups |
| `diagonal_concat` | Concat with different schemas |
| `dataframe_arithmetic` | DataFrame arithmetic ops |

### Series/Expression Operations

| Feature | Description |
|---------|-------------|
| `abs` | Absolute values |
| `cum_agg` | Cumulative sum/min/max |
| `diff` | Difference between elements |
| `pct_change` | Percentage change |
| `rolling_window` | Rolling aggregations |
| `rolling_window_by` | Time-based rolling |
| `rank` | Ranking algorithms |
| `is_in` | Membership checks |
| `is_between` | Range checks |
| `mode` | Most frequent values |
| `ewma` | Exponential moving average |
| `interpolate` | Interpolate nulls |
| `strings` | String utilities |
| `trigonometry` | Trig functions |
| `log` | Logarithms |

### List Operations

```toml
features = [
    "list_eval",      # Apply expressions over lists
    "list_gather",    # Take sublist by indices
    "list_to_struct", # Convert list to struct
    "list_sets",      # Set operations on lists
]
```

## Performance Features

### Nightly Optimizations

```toml
features = ["nightly"]  # Requires nightly Rust
```

Enables:
- SIMD acceleration
- Specialization
- Additional optimizations

```bash
# Build with nightly
rustup override set nightly
cargo build --release --features nightly
```

### SIMD

```toml
features = ["simd"]  # Included with "nightly"
```

### AVX-512

```toml
features = ["avx512"]  # For CPUs with AVX-512
```

### Performant Mode

```toml
features = ["performant"]
```

Enables additional fast paths at the cost of slower compilation:
- `chunked_ids`
- `dtype-u8`, `dtype-u16`, `dtype-f16`, `dtype-struct`
- `cse` (common subexpression elimination)
- `fused` (fused operations)

### Big Index

```toml
features = ["bigidx"]  # For >2^32 rows
```

Uses 64-bit indices instead of 32-bit. Slightly slower but supports massive datasets.

## Common Configurations

### Financial Data Processing

```toml
[dependencies]
polars = { version = "0.46", default-features = false, features = [
    "lazy",
    "parquet",
    "csv",
    "temporal",
    "dtype-datetime",
    "dtype-duration",
    "dtype-f64",
    "asof_join",
    "dynamic_group_by",
    "rolling_window",
    "rolling_window_by",
    "cum_agg",
    "pct_change",
    "diff",
    "rank",
    "fmt"
] }
```

### Data Pipeline / ETL

```toml
[dependencies]
polars = { version = "0.46", default-features = false, features = [
    "lazy",
    "parquet",
    "csv",
    "json",
    "ipc",
    "decompress",
    "cloud",
    "aws",
    "dtype-full",
    "streaming",
    "diagonal_concat",
    "partition_by",
    "fmt"
] }
```

### ML Feature Engineering

```toml
[dependencies]
polars = { version = "0.46", default-features = false, features = [
    "lazy",
    "parquet",
    "dtype-full",
    "ndarray",
    "strings",
    "is_in",
    "is_between",
    "rank",
    "mode",
    "interpolate",
    "pivot",
    "to_dummies",
    "fmt"
] }
```

### Maximum Performance

```toml
[dependencies]
polars = { version = "0.46", features = [
    "nightly",
    "performant"
] }
```

Build command:
```bash
RUSTFLAGS='-C target-cpu=native' cargo build --release
```

### Minimal Binary Size

```toml
[dependencies]
polars = { version = "0.46", default-features = false, features = [
    "lazy",
    "parquet"  # Or just "csv" if you don't need parquet
] }
```

## Compile Time Tips

1. **Start minimal** - Add features as needed
2. **Use sccache** - Cache compilation artifacts
3. **Incremental builds** - Avoid clean builds
4. **Separate dev/prod** - More features for dev, minimal for prod

```bash
# Install sccache
cargo install sccache
export RUSTC_WRAPPER=sccache
```
