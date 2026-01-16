# Polars Core Concepts (Rust)

## Table of Contents
- [Data Structures](#data-structures)
- [Creating DataFrames and Series](#creating-dataframes-and-series)
- [Expressions](#expressions)
- [Lazy vs Eager](#lazy-vs-eager)
- [Error Handling](#error-handling)

## Data Structures

### Hierarchy

```
DataFrame
  └── Column (Vec<Column>)
        └── Series
              └── ChunkedArray<T>
                    └── Arrow Arrays (Vec<dyn Array>)
```

### ChunkedArray<T>

The fundamental data structure - a typed wrapper around Arrow arrays:

```rust
use polars::prelude::*;

// Create from slice
let ca = UInt32Chunked::new("foo".into(), &[1, 2, 3]);

// From iterator
let ca: UInt32Chunked = (0..10).map(Some).collect();

// With builder (more control)
let mut builder = PrimitiveChunkedBuilder::<UInt32Type>::new("foo".into(), 10);
for value in 0..10 {
    builder.append_value(value);
}
let ca = builder.finish();
```

### Series

Type-agnostic columnar data:

```rust
use polars::prelude::*;

// From slice
let s = Series::new("foo".into(), &[1, 2, 3]);

// From iterator
let s: Series = (0..10).map(Some).collect();

// From ChunkedArray
let ca = UInt32Chunked::new("foo".into(), &[Some(1), None, Some(3)]);
let s = ca.into_series();

// Convert to Column
let col = s.into_column();
```

### DataFrame

Two-dimensional data backed by columns:

```rust
use polars::prelude::*;
use polars::df;

// Using df! macro
let df = df![
    "symbol" => ["AAPL", "GOOG"],
    "price" => [150.0, 140.0],
    "volume" => [Some(1000), None]
]?;

// From Vec<Column>
let c1 = Column::new("symbol".into(), &["AAPL", "GOOG"]);
let c2 = Column::new("price".into(), &[150.0, 140.0]);
let df = DataFrame::new_infer_height(vec![c1, c2])?;
```

## Creating DataFrames and Series

### Typed ChunkedArrays

```rust
use polars::prelude::*;

// Numeric types
let int32: Int32Chunked = Int32Chunked::new("a".into(), &[1, 2, 3]);
let float64: Float64Chunked = Float64Chunked::new("b".into(), &[1.0, 2.0, 3.0]);

// String type
let utf8: StringChunked = StringChunked::new("c".into(), &["foo", "bar"]);

// Boolean
let bool_ca: BooleanChunked = BooleanChunked::new("d".into(), &[true, false, true]);

// With nulls
let with_nulls = Int64Chunked::new("e".into(), &[Some(1), None, Some(3)]);
```

### Downcasting Series

Access the underlying ChunkedArray:

```rust
use polars::prelude::*;

fn process_series(s: &Series) -> PolarsResult<()> {
    // Downcast to specific type
    let ca: &Int32Chunked = s.i32()?;
    let ca: &Float64Chunked = s.f64()?;
    let ca: &StringChunked = s.str()?;
    let ca: &BooleanChunked = s.bool()?;

    // Access values
    for opt_val in ca.into_iter() {
        match opt_val {
            Some(val) => println!("{}", val),
            None => println!("null"),
        }
    }
    Ok(())
}
```

## Expressions

### Expression Contexts

Expressions execute within specific contexts:

```rust
use polars::prelude::*;

fn expression_contexts(df: DataFrame) -> PolarsResult<()> {
    let lf = df.lazy();

    // select() - choose and transform columns
    let selected = lf.clone()
        .select([col("symbol"), col("price") * lit(100)])
        .collect()?;

    // with_columns() - add/modify while preserving existing
    let with_new = lf.clone()
        .with_columns([
            (col("price") * col("volume")).alias("notional"),
            col("price").pct_change(lit(1)).alias("return")
        ])
        .collect()?;

    // filter() - row selection
    let filtered = lf.clone()
        .filter(col("volume").gt(lit(1000)))
        .collect()?;

    // group_by().agg() - aggregation
    let grouped = lf.clone()
        .group_by([col("symbol")])
        .agg([
            col("price").mean().alias("avg_price"),
            col("volume").sum().alias("total_volume")
        ])
        .collect()?;

    Ok(())
}
```

### Expression Composition

```rust
use polars::prelude::*;

// Define reusable expressions
fn vwap() -> Expr {
    (col("price") * col("volume")).sum() / col("volume").sum()
}

fn volatility(window: usize) -> Expr {
    col("price").pct_change(lit(1)).rolling_std(RollingOptionsFixedWindow {
        window_size: window,
        min_periods: window,
        ..Default::default()
    })
}

// Use in contexts
fn apply_expressions(lf: LazyFrame) -> PolarsResult<DataFrame> {
    lf.group_by([col("symbol")])
        .agg([
            vwap().alias("vwap"),
            col("price").std(1).alias("std_dev")
        ])
        .collect()
}
```

### Conditional Expressions

```rust
use polars::prelude::*;

fn conditionals(lf: LazyFrame) -> PolarsResult<DataFrame> {
    lf.with_columns([
        // when/then/otherwise
        when(col("price").gt(lit(100)))
            .then(lit("high"))
            .when(col("price").gt(lit(50)))
            .then(lit("medium"))
            .otherwise(lit("low"))
            .alias("price_tier")
    ])
    .collect()
}
```

## Lazy vs Eager

### Eager Mode

Operations execute immediately:

```rust
use polars::prelude::*;
use std::fs::File;

fn eager_operations() -> PolarsResult<()> {
    // Read file immediately
    let file = File::open("data.csv")?;
    let df = CsvReader::new(file).finish()?;

    // Each operation executes right away
    let mask = df.column("price")?.gt(100)?;
    let filtered = df.filter(&mask)?;

    Ok(())
}
```

### Lazy Mode (Preferred)

Operations build a query plan, optimized before execution:

```rust
use polars::prelude::*;

fn lazy_operations() -> PolarsResult<DataFrame> {
    // Build query plan (no execution yet)
    let lf = LazyFrame::scan_parquet("trades.parquet", Default::default())?
        .filter(col("symbol").eq(lit("AAPL")))
        .filter(col("timestamp").gt(lit("2024-01-01")))
        .group_by([col("symbol")])
        .agg([
            col("price").first().alias("open"),
            col("price").max().alias("high"),
            col("price").min().alias("low"),
            col("price").last().alias("close"),
            col("volume").sum()
        ]);

    // View the optimized plan
    println!("{}", lf.explain(true)?);

    // Execute
    lf.collect()
}
```

### Converting Between Modes

```rust
use polars::prelude::*;

fn convert_modes(df: DataFrame) -> PolarsResult<DataFrame> {
    // Eager to Lazy
    let lf: LazyFrame = df.lazy();

    // Lazy to Eager
    let df: DataFrame = lf.collect()?;

    Ok(df)
}
```

### Query Optimizations

Polars automatically applies:

| Optimization | Effect |
|-------------|--------|
| Predicate pushdown | Filters at scan level |
| Projection pushdown | Reads only needed columns |
| Slice pushdown | Limits rows early |
| Common subplan elimination | Caches repeated subqueries |
| Join ordering | Optimizes join sequence |

```rust
use polars::prelude::*;

// Example: only reads symbol="AAPL" rows and price/volume columns
fn optimized_read() -> PolarsResult<DataFrame> {
    LazyFrame::scan_parquet("trades.parquet", Default::default())?
        .filter(col("symbol").eq(lit("AAPL")))  // Pushed to scan
        .select([col("price"), col("volume")])   // Only these columns read
        .collect()
}
```

## Error Handling

### PolarsResult

```rust
use polars::prelude::*;

fn handle_errors() -> PolarsResult<DataFrame> {
    // Use ? for propagation
    let df = df![
        "a" => [1, 2, 3]
    ]?;

    // Explicit error handling
    let result = df.column("nonexistent");
    match result {
        Ok(col) => println!("Found column"),
        Err(e) => println!("Error: {}", e),
    }

    Ok(df)
}
```

### Common Error Patterns

```rust
use polars::prelude::*;

fn safe_operations(df: &DataFrame) -> PolarsResult<()> {
    // Column access - returns Result
    let col = df.column("price")?;

    // Downcasting - returns Result
    let ca = col.f64()?;

    // Type casting - returns Result
    let casted = col.cast(&DataType::Float32)?;

    // Arithmetic - may fail on type mismatch
    let s1 = Series::new("a".into(), &[1, 2, 3]);
    let s2 = Series::new("b".into(), &[1.0, 2.0, 3.0]);
    let sum = &s1 + &s2;  // Coerces types automatically

    Ok(())
}
```

## Type System

### Core Data Types

```rust
use polars::prelude::*;

// Numeric
DataType::Int8, DataType::Int16, DataType::Int32, DataType::Int64
DataType::UInt8, DataType::UInt16, DataType::UInt32, DataType::UInt64
DataType::Float32, DataType::Float64

// Text
DataType::String  // UTF-8 strings
DataType::Categorical(None, CategoricalOrdering::Physical)

// Temporal (requires dtype-* features)
DataType::Date
DataType::Datetime(TimeUnit::Microseconds, None)
DataType::Duration(TimeUnit::Microseconds)
DataType::Time

// Complex
DataType::List(Box::new(DataType::Int64))
DataType::Struct(vec![Field::new("a".into(), DataType::Int64)])

// Other
DataType::Boolean
DataType::Binary
DataType::Null
```

### Type Casting

```rust
use polars::prelude::*;

fn type_operations(s: &Series) -> PolarsResult<Series> {
    // Cast to different type
    let as_f64 = s.cast(&DataType::Float64)?;

    // Check type
    if s.dtype() == &DataType::Int64 {
        println!("It's an Int64");
    }

    // Strict casting (fails on overflow)
    let strict = s.strict_cast(&DataType::Int32)?;

    Ok(as_f64)
}
```

### Null Handling

```rust
use polars::prelude::*;

fn null_operations(df: DataFrame) -> PolarsResult<DataFrame> {
    df.lazy()
        .with_columns([
            // Check nulls
            col("value").is_null().alias("is_missing"),

            // Fill nulls with constant
            col("value").fill_null(lit(0)).alias("filled_const"),

            // Fill with strategy
            col("value").forward_fill(None).alias("filled_forward"),

            // Drop nulls (use filter)
            // Filter rows where value is not null
        ])
        .filter(col("value").is_not_null())
        .collect()
}
```
