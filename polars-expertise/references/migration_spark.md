# PySpark to Polars Migration Guide

This guide helps you migrate from PySpark to Polars, covering fundamental differences and common operation mappings.

## Core Architectural Differences

### Row-Based vs Column-Based

**Spark**: DataFrame is a collection of rows - operations preserve row relationships
**Polars**: DataFrame is a collection of columns - columns can be computed independently

```python
# Polars: Independent column operations
df.select(
    pl.col("foo").sort().head(2),           # Sorts foo, takes first 2
    pl.col("bar").filter(pl.col("x") > 0).sum()  # Filters bar, sums
)
# Result: 2 rows with foo values paired with single bar sum (broadcast)

# Spark: Operations must maintain row alignment
# Requires separate computations and explicit joins
```

### Execution Model

| Aspect | Spark | Polars |
|--------|-------|--------|
| Execution | Distributed across cluster | Single-machine, parallel threads |
| Lazy by default | Yes (transformations) | No (use LazyFrame explicitly) |
| Memory | Spills to disk | In-memory (streaming for large data) |
| Partitioning | Explicit partition management | Automatic parallelism |
| Fault tolerance | Checkpoint/recompute | None (single machine) |

### When to Use Which

**Use Polars when:**
- Data fits on a single machine (even with streaming)
- Need lowest latency
- Don't need cluster infrastructure
- Interactive analysis

**Use Spark when:**
- Data is truly distributed (multiple TB)
- Need fault tolerance
- Existing Spark infrastructure
- Complex distributed operations

## Operation Mappings

### Reading Data

| Operation | PySpark | Polars |
|-----------|---------|--------|
| Read CSV | `spark.read.csv("file.csv")` | `pl.read_csv("file.csv")` |
| Read CSV lazy | `spark.read.csv("file.csv")` | `pl.scan_csv("file.csv")` |
| Read Parquet | `spark.read.parquet("file.parquet")` | `pl.read_parquet("file.parquet")` |
| Read Parquet lazy | `spark.read.parquet("file.parquet")` | `pl.scan_parquet("file.parquet")` |
| Read multiple files | `spark.read.parquet("path/*.parquet")` | `pl.scan_parquet("path/*.parquet")` |

### Column Selection

| Operation | PySpark | Polars |
|-----------|---------|--------|
| Select columns | `df.select("a", "b")` | `df.select("a", "b")` |
| Select with expr | `df.select(col("a"), col("b") * 2)` | `df.select(pl.col("a"), pl.col("b") * 2)` |
| Rename | `df.withColumnRenamed("old", "new")` | `df.rename({"old": "new"})` |
| Drop columns | `df.drop("a", "b")` | `df.drop("a", "b")` |

### Filtering

| Operation | PySpark | Polars |
|-----------|---------|--------|
| Filter | `df.filter(col("a") > 5)` | `df.filter(pl.col("a") > 5)` |
| Where (alias) | `df.where(col("a") > 5)` | `df.filter(pl.col("a") > 5)` |
| Multiple conditions | `df.filter((col("a") > 5) & (col("b") < 10))` | `df.filter((pl.col("a") > 5) & (pl.col("b") < 10))` |
| Is in | `df.filter(col("a").isin([1,2,3]))` | `df.filter(pl.col("a").is_in([1,2,3]))` |
| Is null | `df.filter(col("a").isNull())` | `df.filter(pl.col("a").is_null())` |

### Adding/Modifying Columns

| Operation | PySpark | Polars |
|-----------|---------|--------|
| Add column | `df.withColumn("new", col("a") * 2)` | `df.with_columns((pl.col("a") * 2).alias("new"))` |
| Multiple columns | `df.withColumn("a", ...).withColumn("b", ...)` | `df.with_columns(a=..., b=...)` |
| Conditional | `df.withColumn("x", when(cond, a).otherwise(b))` | `df.with_columns(pl.when(cond).then(a).otherwise(b).alias("x"))` |

### Aggregation

| Operation | PySpark | Polars |
|-----------|---------|--------|
| Group by | `df.groupBy("a")` | `df.group_by("a")` |
| Agg single | `df.groupBy("a").agg({"b": "sum"})` | `df.group_by("a").agg(pl.col("b").sum())` |
| Agg multiple | `df.groupBy("a").agg(sum("b"), avg("c"))` | `df.group_by("a").agg(pl.col("b").sum(), pl.col("c").mean())` |
| Count | `df.groupBy("a").count()` | `df.group_by("a").len()` |

### Window Functions

**Spark** requires explicit window specification:

```python
from pyspark.sql import Window
from pyspark.sql.functions import row_number, lag, mean

window = Window.partitionBy("symbol").orderBy("date")
rolling_window = window.rowsBetween(-6, 0)

df = (
    df
    .withColumn("rank", row_number().over(window))
    .withColumn("prev_price", lag("price", 1).over(window))
    .withColumn("rolling_mean", mean("price").over(rolling_window))
)
```

**Polars** uses `.over()` for partitioning:

```python
df = df.with_columns(
    pl.col("price").rank().over("symbol").alias("rank"),
    pl.col("price").shift(1).over("symbol").alias("prev_price"),
    pl.col("price").rolling_mean(7).over("symbol").alias("rolling_mean")
)
```

### Composing Window Expressions

**Spark limitation**: Cannot compose window functions

```python
# Spark: NOT ALLOWED - lag is a window function
F.mean(F.lag("price", 1)).over(window)  # Error

# Spark workaround: Multiple windows
df = (
    df
    .withColumn("lagged_price", F.lag("price", 7).over(window))
    .withColumn("feature", F.mean("lagged_price").over(rolling_window))
)
```

**Polars**: Window expressions can be composed freely

```python
# Polars: This works - compose shift and rolling_mean
df = df.with_columns(
    pl.col("price").shift(7).rolling_mean(7).over("symbol", order_by="date").alias("feature")
)
```

### Joins

| Operation | PySpark | Polars |
|-----------|---------|--------|
| Inner join | `df1.join(df2, on="id", how="inner")` | `df1.join(df2, on="id", how="inner")` |
| Left join | `df1.join(df2, on="id", how="left")` | `df1.join(df2, on="id", how="left")` |
| Different keys | `df1.join(df2, df1.a == df2.b)` | `df1.join(df2, left_on="a", right_on="b")` |

### Sorting

| Operation | PySpark | Polars |
|-----------|---------|--------|
| Sort ascending | `df.orderBy("a")` | `df.sort("a")` |
| Sort descending | `df.orderBy(col("a").desc())` | `df.sort("a", descending=True)` |
| Multiple columns | `df.orderBy("a", col("b").desc())` | `df.sort("a", pl.col("b").sort(descending=True))` |

### SQL Interface

**Spark:**
```python
df.createOrReplaceTempView("trades")
result = spark.sql("SELECT symbol, AVG(price) FROM trades GROUP BY symbol")
```

**Polars:**
```python
ctx = pl.SQLContext(trades=df)
result = ctx.execute("SELECT symbol, AVG(price) FROM trades GROUP BY symbol").collect()
```

## Common Migration Patterns

### Pattern 1: Feature Engineering Pipeline

**Spark:**
```python
from pyspark.sql.functions import col, lag, avg
from pyspark.sql import Window

window = Window.partitionBy("symbol").orderBy("date")
rolling = window.rowsBetween(-19, 0)

result = (
    df
    .withColumn("returns", (col("close") - lag("close", 1).over(window)) / lag("close", 1).over(window))
    .withColumn("ma_20", avg("close").over(rolling))
    .withColumn("signal", when(col("close") > col("ma_20"), 1).otherwise(-1))
)
```

**Polars:**
```python
result = df.with_columns(
    pl.col("close").pct_change().over("symbol").alias("returns"),
    pl.col("close").rolling_mean(20).over("symbol").alias("ma_20"),
).with_columns(
    pl.when(pl.col("close") > pl.col("ma_20")).then(1).otherwise(-1).alias("signal")
)
```

### Pattern 2: Large File Processing

**Spark:**
```python
# Spark partitions automatically, uses cluster
df = spark.read.parquet("s3://bucket/data/")
result = df.filter(col("date") >= "2024-01-01").groupBy("symbol").agg(...)
```

**Polars:**
```python
# Polars uses lazy eval + streaming for single-machine large data
lf = pl.scan_parquet("s3://bucket/data/**/*.parquet")
result = (
    lf
    .filter(pl.col("date") >= "2024-01-01")
    .group_by("symbol")
    .agg(...)
    .collect(engine="streaming")  # Streaming for large data
)
```

### Pattern 3: UDFs

**Spark:**
```python
from pyspark.sql.functions import udf
from pyspark.sql.types import DoubleType

@udf(returnType=DoubleType())
def custom_calc(x):
    return x * 1.1

df = df.withColumn("result", custom_calc(col("value")))
```

**Polars** - prefer expressions, avoid map_elements:
```python
# Good: Use native expressions when possible
df = df.with_columns((pl.col("value") * 1.1).alias("result"))

# If UDF truly needed (performance penalty):
df = df.with_columns(
    pl.col("value").map_elements(lambda x: x * 1.1, return_dtype=pl.Float64).alias("result")
)
```

## Performance Comparison

| Scenario | Spark | Polars |
|----------|-------|--------|
| Small-medium data (<100GB) | Overhead from distribution | Faster - no distribution overhead |
| Large data (100GB-1TB) | Scales with cluster | Fast with streaming |
| Very large data (>1TB) | Native territory | May need data partitioning strategy |
| Complex joins | Shuffle-heavy | Very fast on single machine |
| Simple aggregations | Good | Often 10-100x faster |

## Migration Checklist

1. **Replace SparkSession** with Polars imports
2. **Change `col()` import** to `pl.col()`
3. **Replace `withColumn`** with `with_columns`
4. **Replace `orderBy`** with `sort`
5. **Replace `groupBy`** with `group_by`
6. **Simplify window functions** - use `.over()` directly
7. **Replace UDFs** with native expressions where possible
8. **Add `.collect()`** after lazy operations
9. **Use `scan_*`** for large files instead of `read_*`
10. **Remove partition management** - Polars handles parallelism automatically

## What You Lose from Spark

- Distributed execution across cluster
- Fault tolerance and checkpointing
- Spark ecosystem (MLlib, Spark Streaming, GraphX)
- Delta Lake / Iceberg native integration
- Cluster resource management

## What You Gain with Polars

- No cluster setup/maintenance
- Lower latency (no network overhead)
- Simpler code (no explicit windows for most operations)
- Better single-machine performance
- Composable expressions
- Smaller memory footprint
