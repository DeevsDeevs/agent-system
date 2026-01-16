# Arrow Interoperability (Rust)

## Table of Contents
- [Polars and Arrow](#polars-and-arrow)
- [Zero-Copy Sharing](#zero-copy-sharing)
- [FFI Boundaries](#ffi-boundaries)
- [Integration with Other Libraries](#integration-with-other-libraries)
- [Memory Layout](#memory-layout)

## Polars and Arrow

Polars is built on Apache Arrow's columnar memory format, enabling efficient interoperability with the Arrow ecosystem.

### Internal Structure

```
Polars ChunkedArray<T>
    └── Vec<Box<dyn Array>>  (Arrow arrays)
          └── ArrayData
                ├── Buffers (actual data)
                ├── Null bitmap
                └── Child data (for nested types)
```

## Zero-Copy Sharing

### To Arrow

```rust
use polars::prelude::*;
use arrow::record_batch::RecordBatch;
use arrow::array::ArrayRef;

fn to_arrow(df: &DataFrame) -> Vec<RecordBatch> {
    // Convert DataFrame to Arrow RecordBatches
    df.iter_chunks(false)
        .map(|chunk| {
            // Each chunk becomes a RecordBatch
            let arrays: Vec<ArrayRef> = chunk
                .into_iter()
                .map(|arr| arr.into())
                .collect();

            RecordBatch::try_new(
                df.schema().to_arrow(CompatLevel::newest()),
                arrays,
            ).unwrap()
        })
        .collect()
}

// Direct conversion
fn df_to_arrow_table(df: DataFrame) -> arrow::array::RecordBatch {
    let schema = df.schema().to_arrow(CompatLevel::newest());
    let chunks = df.iter_chunks(false).next().unwrap();
    let arrays: Vec<ArrayRef> = chunks.into_iter().map(|a| a.into()).collect();
    RecordBatch::try_new(schema, arrays).unwrap()
}
```

### From Arrow

```rust
use polars::prelude::*;
use arrow::record_batch::RecordBatch;

fn from_arrow(batch: RecordBatch) -> PolarsResult<DataFrame> {
    let schema = Schema::from_arrow_schema(batch.schema().as_ref());

    let columns: Vec<Column> = batch
        .columns()
        .iter()
        .zip(schema.iter_names())
        .map(|(arr, name)| {
            let series = Series::from_arrow(name, arr.clone()).unwrap();
            series.into_column()
        })
        .collect();

    DataFrame::new_infer_height(columns)
}
```

### Series Conversion

```rust
use polars::prelude::*;

fn series_arrow_conversion() -> PolarsResult<()> {
    // Create Series
    let s = Series::new("values".into(), &[1i64, 2, 3, 4, 5]);

    // Get underlying Arrow arrays
    let chunks = s.chunks();
    for chunk in chunks {
        // chunk is a Box<dyn Array>
        println!("Array length: {}", chunk.len());
    }

    // From Arrow array
    let arr = arrow::array::Int64Array::from(vec![1, 2, 3, 4, 5]);
    let s = Series::from_arrow("from_arrow".into(), Box::new(arr))?;

    Ok(())
}
```

## FFI Boundaries

### C Data Interface

Arrow's C Data Interface allows zero-copy sharing across language boundaries.

```rust
use polars::prelude::*;
use arrow::ffi::{FFI_ArrowArray, FFI_ArrowSchema};

// Export to C
fn export_to_c(s: &Series) -> (FFI_ArrowSchema, FFI_ArrowArray) {
    let chunks = s.chunks();
    let array = chunks.first().unwrap().clone();

    let schema = FFI_ArrowSchema::try_from(s.dtype().to_arrow(CompatLevel::newest())).unwrap();
    let arr = FFI_ArrowArray::new(&*array);

    (schema, arr)
}

// Import from C
fn import_from_c(schema: FFI_ArrowSchema, array: FFI_ArrowArray) -> PolarsResult<Series> {
    let field = arrow::ffi::import_field_from_c(&schema)?;
    let arr = arrow::ffi::import_array_from_c(array, field.data_type().clone())?;

    Series::from_arrow(field.name(), arr)
}
```

### PyArrow Integration

When using pyo3:

```rust
use pyo3::prelude::*;
use polars::prelude::*;

#[pyfunction]
fn process_arrow_table(py: Python, table: &PyAny) -> PyResult<()> {
    // Convert PyArrow table to Polars DataFrame
    // This is handled by polars-python bindings
    Ok(())
}
```

## Integration with Other Libraries

### DataFusion

```rust
use polars::prelude::*;
use datafusion::prelude::*;
use datafusion::arrow::record_batch::RecordBatch;

async fn with_datafusion(df: DataFrame) -> PolarsResult<DataFrame> {
    // Convert to RecordBatches
    let batches: Vec<RecordBatch> = df
        .iter_chunks(false)
        .map(|chunk| {
            let schema = df.schema().to_arrow(CompatLevel::newest());
            let arrays: Vec<_> = chunk.into_iter().map(|a| a.into()).collect();
            RecordBatch::try_new(schema, arrays).unwrap()
        })
        .collect();

    // Use with DataFusion
    let ctx = SessionContext::new();
    let table = MemTable::try_new(batches[0].schema(), vec![batches])?;
    ctx.register_table("df", Arc::new(table))?;

    let df_result = ctx
        .sql("SELECT * FROM df WHERE x > 10")
        .await?
        .collect()
        .await?;

    // Convert back to Polars
    // ... conversion code
    Ok(df)
}
```

### DuckDB

```rust
use polars::prelude::*;
use duckdb::Connection;

fn with_duckdb(df: &DataFrame) -> PolarsResult<DataFrame> {
    let conn = Connection::open_in_memory()?;

    // Register Arrow data with DuckDB
    conn.register_arrow("my_table", df.iter_chunks(false).collect())?;

    // Query using DuckDB
    let mut stmt = conn.prepare("SELECT * FROM my_table WHERE x > 10")?;
    let arrow_result = stmt.query_arrow([])?;

    // Convert back to Polars
    let batches: Vec<_> = arrow_result.collect();
    // ... conversion
    Ok(df.clone())
}
```

## Memory Layout

### Buffer Structure

```
Arrow Primitive Array (e.g., Int64):
┌─────────────────────────────────────┐
│ Validity Bitmap (bit-packed nulls)  │
├─────────────────────────────────────┤
│ Data Buffer (contiguous i64 values) │
└─────────────────────────────────────┘

Arrow String Array:
┌─────────────────────────────────────┐
│ Validity Bitmap                     │
├─────────────────────────────────────┤
│ Offsets Buffer (i32/i64 offsets)    │
├─────────────────────────────────────┤
│ Data Buffer (UTF-8 bytes)           │
└─────────────────────────────────────┘
```

### Memory Efficiency

```rust
use polars::prelude::*;

fn memory_info(df: &DataFrame) {
    // Estimated memory usage
    println!("Estimated size: {} bytes", df.estimated_size());

    // Per-column info
    for col in df.get_columns() {
        println!(
            "Column '{}': {} bytes, {} chunks",
            col.name(),
            col.estimated_size(),
            col.n_chunks()
        );
    }
}
```

### Rechunking

Multiple chunks can occur after operations like concatenation. Rechunking consolidates:

```rust
use polars::prelude::*;

fn optimize_memory(mut df: DataFrame) -> DataFrame {
    // Check chunk count
    let n_chunks: usize = df.get_columns()
        .iter()
        .map(|c| c.n_chunks())
        .max()
        .unwrap_or(1);

    if n_chunks > 1 {
        // Rechunk to single contiguous buffer
        df = df.rechunk();
    }

    df
}
```

## Best Practices

### Zero-Copy Guidelines

1. **Avoid unnecessary copies**
   - Use references when possible
   - Share Arrow buffers directly

2. **Watch for implicit copies**
   - Type casting creates new buffers
   - String operations often copy

3. **Align with Arrow expectations**
   - Use Arrow-native types
   - Respect null semantics

### Cross-Language Sharing

```rust
// Good: Direct Arrow export
let arrow_table = df.to_arrow();  // Zero-copy when possible

// Good: Stream large data
for batch in df.iter_chunks(false) {
    // Process/send each batch
}

// Avoid: Serialization when sharing
let json = df.write_json();  // Expensive for interop
```

### Memory Alignment

Arrow requires 64-byte alignment for SIMD operations:

```rust
use polars::prelude::*;

// Polars handles alignment automatically
// But be aware when interfacing with raw buffers
let s = Series::new("a".into(), &[1i64, 2, 3]);
// Internal buffers are 64-byte aligned
```
