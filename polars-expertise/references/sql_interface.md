# SQL Interface

Polars provides SQL support through `SQLContext`, translating SQL queries into expressions for native execution with full query optimization.

## SQLContext Setup

### Basic Initialization

```python
import polars as pl

# Create context with DataFrame registration
df = pl.DataFrame({
    "symbol": ["AAPL", "AAPL", "MSFT", "MSFT"],
    "price": [150.0, 152.0, 280.0, 285.0],
    "volume": [1000000, 1200000, 800000, 900000]
})

ctx = pl.SQLContext(frames={"trades": df})
```

### Registration Methods

```python
# Register single DataFrame
ctx = pl.SQLContext()
ctx.register("trades", df)

# Register multiple DataFrames
ctx.register_many({
    "trades": trades_df,
    "quotes": quotes_df,
    "orders": orders_df
})

# Register LazyFrames (recommended for large data)
lf = pl.scan_parquet("trades.parquet")
ctx.register("trades", lf)

# Register all DataFrames/LazyFrames in global namespace
ctx.register_globals()
```

### Eager vs Lazy Execution

```python
# Lazy execution (default) - returns LazyFrame
ctx = pl.SQLContext(trades=df)
result = ctx.execute("SELECT * FROM trades WHERE price > 150")
# result is LazyFrame - call .collect() to materialize

# Eager execution - returns DataFrame directly
ctx = pl.SQLContext(trades=df, eager_execution=True)
result = ctx.execute("SELECT * FROM trades WHERE price > 150")
# result is DataFrame

# Per-query eager execution
result = ctx.execute("SELECT * FROM trades", eager=True)
```

## Query Patterns

### Basic SELECT with Aggregations

```python
ctx.execute("""
    SELECT
        symbol,
        AVG(price) as avg_price,
        SUM(volume) as total_volume,
        COUNT(*) as trade_count
    FROM trades
    GROUP BY symbol
    ORDER BY avg_price DESC
""").collect()
```

### Financial Data Patterns

```python
# VWAP calculation
ctx.execute("""
    SELECT
        symbol,
        SUM(price * volume) / SUM(volume) as vwap
    FROM trades
    GROUP BY symbol
""").collect()

# Price change analysis
ctx.execute("""
    SELECT
        symbol,
        price,
        LAG(price, 1) OVER (PARTITION BY symbol ORDER BY timestamp) as prev_price,
        price - LAG(price, 1) OVER (PARTITION BY symbol ORDER BY timestamp) as price_change
    FROM trades
""").collect()
```

### JOINs

```python
quotes = pl.DataFrame({
    "symbol": ["AAPL", "MSFT"],
    "bid": [149.5, 279.5],
    "ask": [150.5, 280.5]
})

ctx.register("quotes", quotes)

# Inner join
ctx.execute("""
    SELECT
        t.symbol,
        t.price,
        q.bid,
        q.ask,
        t.price - (q.bid + q.ask) / 2 as mid_deviation
    FROM trades t
    INNER JOIN quotes q ON t.symbol = q.symbol
""").collect()
```

### Common Table Expressions (CTEs)

```python
ctx.execute("""
    WITH daily_stats AS (
        SELECT
            symbol,
            DATE_TRUNC('day', timestamp) as date,
            MAX(price) as high,
            MIN(price) as low,
            FIRST_VALUE(price) OVER (PARTITION BY symbol, DATE_TRUNC('day', timestamp) ORDER BY timestamp) as open,
            LAST_VALUE(price) OVER (PARTITION BY symbol, DATE_TRUNC('day', timestamp) ORDER BY timestamp) as close
        FROM trades
        GROUP BY symbol, DATE_TRUNC('day', timestamp)
    ),
    with_returns AS (
        SELECT
            *,
            (close - open) / open * 100 as daily_return
        FROM daily_stats
    )
    SELECT * FROM with_returns
    WHERE daily_return > 1.0
    ORDER BY daily_return DESC
""").collect()
```

### Table Functions - Direct File Reading

```python
# Read directly from files in SQL
ctx.execute("""
    SELECT *
    FROM read_parquet('trades/*.parquet')
    WHERE date >= '2024-01-01'
""").collect()

# Join files
ctx.execute("""
    SELECT t.*, r.reference_price
    FROM read_csv('trades.csv') t
    JOIN read_parquet('reference.parquet') r
    ON t.symbol = r.symbol
""").collect()
```

### CREATE TABLE

```python
# Create derived tables
ctx.execute("""
    CREATE TABLE high_volume_trades AS
    SELECT *
    FROM trades
    WHERE volume > 1000000
""")

# Query created table
ctx.execute("SELECT * FROM high_volume_trades").collect()

# Show registered tables
ctx.execute("SHOW TABLES").collect()
```

## Supported SQL Features

### Statements

| Statement | Support |
|-----------|---------|
| SELECT | Full support |
| CREATE TABLE AS | Full support |
| DROP TABLE | Full support |
| TRUNCATE TABLE | Full support |
| EXPLAIN | Full support |
| SHOW TABLES | Full support |
| INSERT/UPDATE/DELETE | Not supported |

### Clauses

| Clause | Support |
|--------|---------|
| WHERE | Full support |
| GROUP BY | Full support |
| HAVING | Full support |
| ORDER BY | Full support |
| LIMIT/OFFSET | Full support |
| JOIN (INNER, LEFT, RIGHT, FULL, CROSS) | Full support |
| UNION/UNION ALL | Full support |
| WITH (CTE) | Full support |

### Functions

| Category | Examples |
|----------|----------|
| Aggregation | SUM, AVG, MIN, MAX, COUNT, STDDEV, VARIANCE, FIRST, LAST |
| Window | ROW_NUMBER, RANK, DENSE_RANK, LAG, LEAD, FIRST_VALUE, LAST_VALUE |
| Math | ABS, CEIL, FLOOR, ROUND, EXP, LN, LOG, POWER, SQRT |
| String | UPPER, LOWER, LENGTH, TRIM, SUBSTR, CONCAT, REPLACE, STARTS_WITH, ENDS_WITH |
| Date/Time | DATE_TRUNC, DATE_PART, EXTRACT, NOW, CURRENT_DATE |
| Array | EXPLODE, UNNEST, ARRAY_LENGTH, ARRAY_SUM |
| Conditional | CASE WHEN, COALESCE, NULLIF, IIF |

## Best Practices

### 1. Use LazyFrames for Large Data

```python
# Good - lazy reading with SQL optimization
lf = pl.scan_parquet("large_dataset.parquet")
ctx = pl.SQLContext(data=lf)
result = ctx.execute("""
    SELECT symbol, AVG(price)
    FROM data
    WHERE date >= '2024-01-01'
    GROUP BY symbol
""").collect()
# Predicate and projection pushdown applied

# Bad - eager reading wastes memory
df = pl.read_parquet("large_dataset.parquet")  # Loads everything
ctx = pl.SQLContext(data=df)
```

### 2. Combine SQL with Expression API

```python
# SQL for initial query
lf = ctx.execute("""
    SELECT symbol, date, price, volume
    FROM trades
    WHERE volume > 100000
""")

# Expression API for complex transformations
result = (
    lf.with_columns(
        pl.col("price").rolling_mean(20).over("symbol").alias("ma_20"),
        pl.col("volume").rank("ordinal").over("date").alias("volume_rank")
    )
    .collect()
)
```

### 3. EXPLAIN for Query Debugging

```python
# View query plan
print(ctx.execute("EXPLAIN SELECT * FROM trades WHERE price > 150"))
```

## Rust SQL Support

Enable the `sql` feature in Cargo.toml:

```toml
[dependencies]
polars = { version = "0.46", features = ["sql"] }
```

```rust
use polars::prelude::*;
use polars::sql::SQLContext;

fn main() -> PolarsResult<()> {
    let df = df!(
        "symbol" => ["AAPL", "MSFT"],
        "price" => [150.0, 280.0]
    )?;

    let mut ctx = SQLContext::new();
    ctx.register("trades", df.lazy());

    let result = ctx.execute("SELECT * FROM trades WHERE price > 200")?
        .collect()?;

    println!("{}", result);
    Ok(())
}
```

## Limitations

1. **No DML**: INSERT, UPDATE, DELETE not supported - use expression API
2. **No DDL schema**: No column type definitions in CREATE TABLE
3. **PostgreSQL dialect**: Some vendor-specific syntax may not work
4. **Expression priority**: New features land in expression API first

For complex transformations not supported in SQL, use the expression API directly.
