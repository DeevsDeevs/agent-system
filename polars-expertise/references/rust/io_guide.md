# Polars I/O Guide (Rust)

## Table of Contents
- [CSV](#csv)
- [Parquet](#parquet)
- [IPC/Arrow](#ipcarrow)
- [JSON](#json)
- [Cloud Storage](#cloud-storage)
- [Streaming](#streaming)

## CSV

**Feature:** `csv`

### Reading CSV

```rust
use polars::prelude::*;
use std::fs::File;

// Basic read
fn read_csv() -> PolarsResult<DataFrame> {
    let file = File::open("data.csv")?;
    CsvReader::new(file).finish()
}

// With options
fn read_csv_options() -> PolarsResult<DataFrame> {
    let file = File::open("data.csv")?;
    CsvReader::new(file)
        .with_has_header(true)
        .with_separator(b',')
        .with_n_rows(Some(1000))  // Limit rows
        .with_columns(Some(Arc::new(vec!["col1".into(), "col2".into()])))
        .with_dtypes(Some(Arc::new(Schema::from_iter([
            Field::new("id".into(), DataType::Int64),
            Field::new("price".into(), DataType::Float64),
        ]))))
        .with_null_values(Some(NullValues::AllColumnsSingle("NA".into())))
        .finish()
}

// Lazy (recommended for large files)
fn scan_csv() -> PolarsResult<LazyFrame> {
    LazyCsvReader::new("data.csv")
        .with_has_header(true)
        .with_separator(b',')
        .finish()
}
```

### Writing CSV

```rust
use polars::prelude::*;
use std::fs::File;

fn write_csv(df: &mut DataFrame) -> PolarsResult<()> {
    let mut file = File::create("output.csv")?;
    CsvWriter::new(&mut file)
        .include_header(true)
        .with_separator(b',')
        .with_quote_char(b'"')
        .finish(df)?;
    Ok(())
}
```

## Parquet

**Feature:** `parquet`

### Reading Parquet

```rust
use polars::prelude::*;
use std::fs::File;

// Eager
fn read_parquet() -> PolarsResult<DataFrame> {
    let file = File::open("data.parquet")?;
    ParquetReader::new(file).finish()
}

// With options
fn read_parquet_options() -> PolarsResult<DataFrame> {
    let file = File::open("data.parquet")?;
    ParquetReader::new(file)
        .with_columns(Some(vec!["col1".into(), "col2".into()]))
        .with_n_rows(Some(1000))
        .with_parallel(ParallelStrategy::Auto)
        .finish()
}

// Lazy (recommended)
fn scan_parquet() -> PolarsResult<LazyFrame> {
    LazyFrame::scan_parquet("data.parquet", Default::default())
}

// Multiple files
fn scan_parquet_glob() -> PolarsResult<LazyFrame> {
    LazyFrame::scan_parquet("data/*.parquet", Default::default())
}

// With scan options
fn scan_parquet_options() -> PolarsResult<LazyFrame> {
    let args = ScanArgsParquet {
        n_rows: Some(10000),
        parallel: ParallelStrategy::Auto,
        rechunk: false,
        ..Default::default()
    };
    LazyFrame::scan_parquet("data.parquet", args)
}
```

### Writing Parquet

```rust
use polars::prelude::*;
use std::fs::File;

fn write_parquet(df: &mut DataFrame) -> PolarsResult<u64> {
    let file = File::create("output.parquet")?;
    ParquetWriter::new(file)
        .with_compression(ParquetCompression::Snappy)  // Fast
        // .with_compression(ParquetCompression::Zstd(Some(ZstdLevel::try_new(3)?)))  // Better compression
        .with_statistics(StatisticsOptions::full())  // Enables predicate pushdown
        .finish(df)
}

// Partitioned write
fn write_partitioned(lf: LazyFrame) -> PolarsResult<()> {
    lf.sink_parquet(
        "output/",
        ParquetWriteOptions {
            compression: ParquetCompression::Snappy,
            statistics: StatisticsOptions::full(),
            ..Default::default()
        },
    )
}
```

## IPC/Arrow

**Feature:** `ipc`

### Reading IPC

```rust
use polars::prelude::*;
use std::fs::File;

fn read_ipc() -> PolarsResult<DataFrame> {
    let file = File::open("data.arrow")?;
    IpcReader::new(file).finish()
}

fn scan_ipc() -> PolarsResult<LazyFrame> {
    LazyFrame::scan_ipc("data.arrow", Default::default())
}
```

### Writing IPC

```rust
use polars::prelude::*;
use std::fs::File;

fn write_ipc(df: &mut DataFrame) -> PolarsResult<()> {
    let file = File::create("output.arrow")?;
    IpcWriter::new(file)
        .with_compression(Some(IpcCompression::ZSTD))
        .finish(df)
}
```

## JSON

**Feature:** `json`

### Reading JSON

```rust
use polars::prelude::*;
use std::fs::File;

// NDJSON (newline-delimited JSON) - recommended
fn read_ndjson() -> PolarsResult<DataFrame> {
    let file = File::open("data.ndjson")?;
    JsonReader::new(file)
        .with_json_format(JsonFormat::JsonLines)
        .finish()
}

// Standard JSON
fn read_json() -> PolarsResult<DataFrame> {
    let file = File::open("data.json")?;
    JsonReader::new(file)
        .with_json_format(JsonFormat::Json)
        .finish()
}

// Lazy NDJSON scan
fn scan_ndjson() -> PolarsResult<LazyFrame> {
    LazyFrame::scan_ndjson("data.ndjson", Default::default())
}
```

### Writing JSON

```rust
use polars::prelude::*;
use std::fs::File;

fn write_json(df: &mut DataFrame) -> PolarsResult<()> {
    let mut file = File::create("output.json")?;
    JsonWriter::new(&mut file)
        .with_json_format(JsonFormat::Json)
        .finish(df)
}

fn write_ndjson(df: &mut DataFrame) -> PolarsResult<()> {
    let mut file = File::create("output.ndjson")?;
    JsonWriter::new(&mut file)
        .with_json_format(JsonFormat::JsonLines)
        .finish(df)
}
```

## Cloud Storage

**Features:** `cloud`, `aws`, `azure`, `gcp`

### AWS S3

```rust
use polars::prelude::*;

// Set credentials via environment
// AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION

fn read_s3() -> PolarsResult<LazyFrame> {
    LazyFrame::scan_parquet("s3://bucket/path/data.parquet", Default::default())
}

fn read_s3_glob() -> PolarsResult<LazyFrame> {
    LazyFrame::scan_parquet("s3://bucket/path/*.parquet", Default::default())
}
```

### Azure Blob

```rust
use polars::prelude::*;

// Set credentials via environment
// AZURE_STORAGE_ACCOUNT_NAME, AZURE_STORAGE_ACCOUNT_KEY

fn read_azure() -> PolarsResult<LazyFrame> {
    LazyFrame::scan_parquet("az://container/path/data.parquet", Default::default())
}
```

### Google Cloud Storage

```rust
use polars::prelude::*;

// Set credentials via environment
// GOOGLE_APPLICATION_CREDENTIALS

fn read_gcs() -> PolarsResult<LazyFrame> {
    LazyFrame::scan_parquet("gs://bucket/path/data.parquet", Default::default())
}
```

### HTTP

```rust
use polars::prelude::*;

fn read_http() -> PolarsResult<LazyFrame> {
    LazyFrame::scan_parquet("https://example.com/data.parquet", Default::default())
}
```

## Streaming

### Streaming Reads

```rust
use polars::prelude::*;

fn streaming_process() -> PolarsResult<DataFrame> {
    // Streaming is handled automatically with new_streaming feature
    LazyFrame::scan_parquet("very_large.parquet", Default::default())?
        .filter(col("value").gt(lit(100)))
        .group_by([col("category")])
        .agg([col("value").sum()])
        .collect()  // Streaming execution when possible
}
```

### Streaming Writes (Sink)

```rust
use polars::prelude::*;

fn sink_to_parquet() -> PolarsResult<()> {
    LazyFrame::scan_csv("large.csv", Default::default())?
        .filter(col("value").gt(lit(100)))
        .sink_parquet(
            "output.parquet",
            ParquetWriteOptions::default(),
        )
}
```

### Batched CSV Reading

```rust
use polars::prelude::*;
use std::fs::File;

fn process_csv_batches() -> PolarsResult<Vec<DataFrame>> {
    let file = File::open("large.csv")?;
    let reader = CsvReader::new(file)
        .batched(None)?;  // Returns batched reader

    let mut results = Vec::new();
    while let Some(batch) = reader.next_batches(1)? {
        for df in batch {
            // Process each batch
            let processed = df.filter(&df.column("x")?.gt(100)?)?;
            results.push(processed);
        }
    }
    Ok(results)
}
```

## Best Practices

### Format Selection

| Format | Use When |
|--------|----------|
| Parquet | Large files, archival, data lakes |
| CSV | Human-readable, legacy systems |
| IPC/Arrow | Fast transfer, zero-copy |
| NDJSON | Streaming JSON, logs |

### Reading Large Files

```rust
// 1. Always use lazy mode
let lf = LazyFrame::scan_parquet("large.parquet", Default::default())?;

// 2. Project columns early
let lf = lf.select([col("a"), col("b")]);

// 3. Filter early (predicate pushdown)
let lf = lf.filter(col("a").gt(lit(100)));

// 4. Collect at the end
let df = lf.collect()?;
```

### Writing Large Files

```rust
// 1. Use Parquet with compression
ParquetWriter::new(file)
    .with_compression(ParquetCompression::Zstd(Some(ZstdLevel::try_new(3)?)))
    .with_statistics(StatisticsOptions::full())
    .finish(&mut df)?;

// 2. Use sink for streaming writes
lf.sink_parquet("output.parquet", ParquetWriteOptions::default())?;
```
