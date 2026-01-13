# Polars Performance Optimization (Rust)

## Table of Contents
- [Custom Allocators](#custom-allocators)
- [Compiler Optimizations](#compiler-optimizations)
- [Feature Flags for Performance](#feature-flags-for-performance)
- [Environment Variables](#environment-variables)
- [Code Patterns](#code-patterns)
- [Benchmarking](#benchmarking)

## Custom Allocators

Using a custom allocator can improve performance by 10-25%.

### Jemalloc (Recommended for Linux/macOS)

```toml
# Cargo.toml
[dependencies]
tikv-jemallocator = "0.6"
```

```rust
// main.rs or lib.rs - at the top
use tikv_jemallocator::Jemalloc;

#[global_allocator]
static GLOBAL: Jemalloc = Jemalloc;
```

### Mimalloc (Cross-platform)

```toml
# Cargo.toml
[dependencies]
mimalloc = { version = "0.1", default-features = false }
```

```rust
use mimalloc::MiMalloc;

#[global_allocator]
static GLOBAL: MiMalloc = MiMalloc;
```

### Allocator Comparison

| Allocator | Best For | Notes |
|-----------|----------|-------|
| Jemalloc | Linux, macOS | Best overall for OLAP |
| Mimalloc | Windows, cross-platform | Good general purpose |
| System | Default | Baseline, no extra deps |

## Compiler Optimizations

### Release Profile

```toml
# Cargo.toml
[profile.release]
lto = "thin"           # Link-time optimization
codegen-units = 1      # Better optimization, slower compile
opt-level = 3          # Maximum optimization
```

### Native CPU Features

```bash
# Build for current CPU architecture
RUSTFLAGS='-C target-cpu=native' cargo build --release

# Or specify architecture
RUSTFLAGS='-C target-cpu=skylake' cargo build --release
```

### Profile-Guided Optimization (PGO)

```bash
# Step 1: Build with instrumentation
RUSTFLAGS='-Cprofile-generate=/tmp/pgo-data' cargo build --release

# Step 2: Run representative workload
./target/release/my_app --process-data

# Step 3: Merge profile data
llvm-profdata merge -o /tmp/pgo-data/merged.profdata /tmp/pgo-data

# Step 4: Build with profile data
RUSTFLAGS='-Cprofile-use=/tmp/pgo-data/merged.profdata' cargo build --release
```

## Feature Flags for Performance

### Nightly Features

```toml
features = ["nightly"]
```

Requires nightly Rust:
```bash
rustup override set nightly
```

Enables:
- SIMD vectorization
- Specialization
- Additional optimizations

### SIMD

```toml
features = ["simd"]  # Enabled with "nightly"
```

### Performant Mode

```toml
features = ["performant"]
```

Enables fast paths at cost of compile time:
- Common subexpression elimination
- Fused operations
- Optimal dtype handling

### AVX-512

```toml
features = ["avx512"]
```

For modern Intel CPUs with AVX-512 support.

## Environment Variables

### Thread Pool

```bash
# Set number of threads (default: num_cpus)
export POLARS_MAX_THREADS=8

# Or in Rust
std::env::set_var("POLARS_MAX_THREADS", "8");
```

### Partitioning

```bash
# Disable partitioned group_by (for debugging)
export POLARS_NO_PARTITION=1

# Force partitioned group_by
export POLARS_FORCE_PARTITION=1

# Partition threshold (default 1000)
export POLARS_PARTITION_UNIQUE_COUNT=500
```

### Debugging

```bash
# Verbose output
export POLARS_VERBOSE=1

# Panic on error (for debugging)
export POLARS_PANIC_ON_ERR=1

# Include backtrace in errors
export POLARS_BACKTRACE_IN_ERR=1
```

### Parquet

```bash
# Ignore parquet statistics (for debugging)
export POLARS_NO_PARQUET_STATISTICS=1
```

## Code Patterns

### Use Lazy Mode

```rust
// GOOD: Lazy mode enables optimizations
let result = LazyFrame::scan_parquet("data.parquet", Default::default())?
    .filter(col("x").gt(lit(10)))
    .select([col("x"), col("y")])
    .collect()?;

// BAD: Eager reads all data first
let df = ParquetReader::new(File::open("data.parquet")?).finish()?;
let filtered = df.filter(&df.column("x")?.gt(10)?)?;
```

### Project Early

```rust
// GOOD: Project columns early
lf.select([col("a"), col("b")])
    .filter(col("a").gt(lit(10)))
    .collect()?

// BAD: Read all columns, filter, then project
lf.filter(col("a").gt(lit(10)))
    .collect()?
    .select(["a", "b"])?
```

### Avoid Python-style UDFs

```rust
// GOOD: Native expressions
lf.with_columns([col("x") * lit(2)])

// BAD: map function (sequential, not parallelized)
lf.with_columns([col("x").map(|s| {
    Ok(Some(s.multiply(&Series::new("".into(), [2]))?))
}, GetOutput::same_type())])
```

### Use Categorical for Low Cardinality

```rust
// GOOD: Categorical for repeated strings
let df = df.lazy()
    .with_columns([col("symbol").cast(DataType::Categorical(None, Default::default()))])
    .collect()?;

// Faster groupby and joins with categorical
```

### Rechunk After Operations

```rust
// After multiple concatenations, rechunk for better cache locality
let combined = pl::concat(dfs, UnionArgs::default())?;
let combined = combined.rechunk();
```

### Streaming for Large Data

```rust
// Use streaming for out-of-memory data
let result = lf
    .filter(col("x").gt(lit(10)))
    .group_by([col("category")])
    .agg([col("value").sum()])
    .collect()?;  // Streaming is automatic in new_streaming
```

## Benchmarking

### Setup

```toml
# Cargo.toml
[dev-dependencies]
criterion = { version = "0.5", features = ["html_reports"] }

[[bench]]
name = "my_benchmark"
harness = false
```

### Basic Benchmark

```rust
// benches/my_benchmark.rs
use criterion::{criterion_group, criterion_main, Criterion, black_box};
use polars::prelude::*;

fn benchmark_filter(c: &mut Criterion) {
    let df = df![
        "x" => (0..1_000_000).collect::<Vec<i64>>(),
        "y" => (0..1_000_000).map(|i| i as f64).collect::<Vec<f64>>()
    ].unwrap();

    c.bench_function("filter_large", |b| {
        b.iter(|| {
            let mask = black_box(&df).column("x").unwrap().gt(500_000).unwrap();
            black_box(&df).filter(&mask).unwrap()
        })
    });
}

criterion_group!(benches, benchmark_filter);
criterion_main!(benches);
```

### Run Benchmarks

```bash
cargo bench

# With specific feature flags
cargo bench --features nightly,performant
```

### Profiling

```bash
# Using perf (Linux)
perf record --call-graph dwarf ./target/release/my_app
perf report

# Using flamegraph
cargo install flamegraph
cargo flamegraph --bin my_app
```

## Performance Checklist

- [ ] Using custom allocator (jemalloc/mimalloc)?
- [ ] Building with `--release`?
- [ ] Using `RUSTFLAGS='-C target-cpu=native'`?
- [ ] Using lazy mode for complex pipelines?
- [ ] Projecting columns early?
- [ ] Using categorical for low-cardinality strings?
- [ ] Avoiding map functions where expressions work?
- [ ] Appropriate thread pool size for workload?
- [ ] Features enabled: `performant`, `nightly` (if applicable)?
