# Polars Operations (Rust)

## Table of Contents
- [Selection and Filtering](#selection-and-filtering)
- [Aggregations](#aggregations)
- [Window Functions](#window-functions)
- [Joins](#joins)
- [Sorting](#sorting)
- [Transformations](#transformations)

## Selection and Filtering

### Column Selection

```rust
use polars::prelude::*;

fn select_columns(df: DataFrame) -> PolarsResult<DataFrame> {
    // Select specific columns
    let selected = df.lazy()
        .select([col("a"), col("b"), col("c")])
        .collect()?;

    // Select by pattern (requires "regex" feature)
    let by_pattern = df.lazy()
        .select([col("^sales_.*$")])  // All columns starting with "sales_"
        .collect()?;

    // Select all except some
    let excluded = df.lazy()
        .select([all().exclude(["id", "timestamp"])])
        .collect()?;

    // Select by dtype
    let numeric = df.lazy()
        .select([dtype_cols([DataType::Float64, DataType::Int64])])
        .collect()?;

    Ok(selected)
}
```

### Row Filtering

```rust
use polars::prelude::*;

fn filter_rows(df: DataFrame) -> PolarsResult<DataFrame> {
    let lf = df.lazy();

    // Single condition
    let filtered = lf.clone()
        .filter(col("age").gt(lit(25)))
        .collect()?;

    // Multiple conditions (AND)
    let multi = lf.clone()
        .filter(
            col("age").gt(lit(25))
            .and(col("city").eq(lit("NY")))
        )
        .collect()?;

    // OR condition
    let or_cond = lf.clone()
        .filter(
            col("age").gt(lit(30))
            .or(col("salary").gt(lit(100000)))
        )
        .collect()?;

    // NOT condition
    let not_cond = lf.clone()
        .filter(col("active").not())
        .collect()?;

    // Membership
    let in_list = lf.clone()
        .filter(col("city").is_in(lit(Series::new("".into(), ["NY", "LA", "SF"]))))
        .collect()?;

    // Range
    let in_range = lf.clone()
        .filter(col("age").is_between(lit(25), lit(35), ClosedInterval::Both))
        .collect()?;

    // Null checks
    let not_null = lf.clone()
        .filter(col("value").is_not_null())
        .collect()?;

    Ok(filtered)
}
```

### Add/Modify Columns

```rust
use polars::prelude::*;

fn add_columns(df: DataFrame) -> PolarsResult<DataFrame> {
    df.lazy()
        .with_columns([
            // Arithmetic
            (col("price") * col("quantity")).alias("total"),

            // Conditional
            when(col("age").gt(lit(18)))
                .then(lit("adult"))
                .otherwise(lit("minor"))
                .alias("status"),

            // String operations
            col("name").str().to_uppercase().alias("name_upper"),

            // Cast types
            col("id").cast(DataType::String).alias("id_str"),
        ])
        .collect()
}
```

## Aggregations

### Group By

```rust
use polars::prelude::*;

fn group_by_operations(df: DataFrame) -> PolarsResult<DataFrame> {
    // Basic group by
    let grouped = df.clone().lazy()
        .group_by([col("category")])
        .agg([
            col("value").sum().alias("total"),
            col("value").mean().alias("average"),
            col("value").count().alias("count"),
        ])
        .collect()?;

    // Multiple group columns
    let multi_group = df.clone().lazy()
        .group_by([col("category"), col("region")])
        .agg([col("value").sum()])
        .collect()?;

    // Maintain order
    let ordered = df.clone().lazy()
        .group_by([col("category")])
        .agg([col("value").sum()])
        .sort([col("category")], Default::default())
        .collect()?;

    Ok(grouped)
}
```

### Aggregation Functions

```rust
use polars::prelude::*;

fn aggregation_functions(df: DataFrame) -> PolarsResult<DataFrame> {
    df.lazy()
        .group_by([col("group")])
        .agg([
            // Count
            len().alias("count"),
            col("id").n_unique().alias("unique_count"),

            // Statistics
            col("value").sum().alias("total"),
            col("value").mean().alias("average"),
            col("value").median().alias("median"),
            col("value").std(1).alias("std_dev"),
            col("value").var(1).alias("variance"),
            col("value").min().alias("minimum"),
            col("value").max().alias("maximum"),
            col("value").quantile(lit(0.95), QuantileMethod::Linear).alias("p95"),

            // First/Last
            col("timestamp").first().alias("first_ts"),
            col("timestamp").last().alias("last_ts"),

            // List aggregation
            col("item").alias("all_items"),  // Collects into list
        ])
        .collect()
}
```

### Conditional Aggregations

```rust
use polars::prelude::*;

fn conditional_aggregations(df: DataFrame) -> PolarsResult<DataFrame> {
    df.lazy()
        .group_by([col("category")])
        .agg([
            // Count by condition
            col("value").filter(col("value").gt(lit(100))).count().alias("high_count"),

            // Sum by condition
            col("value").filter(col("active")).sum().alias("active_total"),

            // Conditional expression
            when(col("type").eq(lit("A")))
                .then(col("value"))
                .otherwise(lit(0))
                .sum()
                .alias("type_a_total"),
        ])
        .collect()
}
```

## Window Functions

### Basic Window Operations

```rust
use polars::prelude::*;

fn window_functions(df: DataFrame) -> PolarsResult<DataFrame> {
    df.lazy()
        .with_columns([
            // Group statistics (preserves row count)
            col("value").mean().over([col("category")]).alias("group_mean"),
            col("value").sum().over([col("category")]).alias("group_total"),

            // Ranking
            col("value").rank(RankOptions::default(), None).over([col("category")]).alias("rank"),

            // Cumulative
            col("value").cum_sum(false).over([col("category")]).alias("cumsum"),

            // Lag/Lead
            col("value").shift(lit(1)).over([col("category")]).alias("prev_value"),
            col("value").shift(lit(-1)).over([col("category")]).alias("next_value"),

            // Difference from previous
            (col("value") - col("value").shift(lit(1))).over([col("category")]).alias("diff"),
        ])
        .collect()
}
```

### Rolling Windows

```rust
use polars::prelude::*;

fn rolling_windows(df: DataFrame) -> PolarsResult<DataFrame> {
    df.lazy()
        .with_columns([
            // Row-based rolling
            col("value").rolling_mean(RollingOptionsFixedWindow {
                window_size: 20,
                min_periods: 20,
                ..Default::default()
            }).alias("rolling_mean"),

            col("value").rolling_std(RollingOptionsFixedWindow {
                window_size: 20,
                min_periods: 20,
                ..Default::default()
            }).alias("rolling_std"),

            col("value").rolling_sum(RollingOptionsFixedWindow {
                window_size: 10,
                min_periods: 1,  // Allow partial windows
                ..Default::default()
            }).alias("rolling_sum"),
        ])
        .collect()
}
```

## Joins

### Basic Joins

```rust
use polars::prelude::*;

fn join_operations(df1: DataFrame, df2: DataFrame) -> PolarsResult<()> {
    let lf1 = df1.clone().lazy();
    let lf2 = df2.clone().lazy();

    // Inner join
    let inner = lf1.clone()
        .inner_join(lf2.clone(), col("id"), col("id"))
        .collect()?;

    // Left join
    let left = lf1.clone()
        .left_join(lf2.clone(), col("id"), col("id"))
        .collect()?;

    // Full outer join
    let outer = lf1.clone()
        .full_join(lf2.clone(), col("id"), col("id"))
        .collect()?;

    // Multiple keys
    let multi_key = lf1.clone()
        .join(
            lf2.clone(),
            [col("id"), col("date")],
            [col("id"), col("date")],
            JoinArgs::new(JoinType::Inner),
        )
        .collect()?;

    // Different column names
    let diff_names = lf1.clone()
        .join(
            lf2.clone(),
            [col("user_id")],
            [col("id")],
            JoinArgs::new(JoinType::Left),
        )
        .collect()?;

    Ok(())
}
```

### Semi and Anti Joins

```rust
use polars::prelude::*;

fn semi_anti_joins(df1: DataFrame, df2: DataFrame) -> PolarsResult<()> {
    let lf1 = df1.lazy();
    let lf2 = df2.lazy();

    // Semi join: keep left rows that have a match in right
    let semi = lf1.clone()
        .join(lf2.clone(), [col("id")], [col("id")], JoinArgs::new(JoinType::Semi))
        .collect()?;

    // Anti join: keep left rows that don't have a match in right
    let anti = lf1.clone()
        .join(lf2.clone(), [col("id")], [col("id")], JoinArgs::new(JoinType::Anti))
        .collect()?;

    Ok(())
}
```

### As-Of Joins

**Feature:** `asof_join`

```rust
use polars::prelude::*;

fn asof_join(trades: DataFrame, quotes: DataFrame) -> PolarsResult<DataFrame> {
    // Join to nearest earlier timestamp
    trades.lazy()
        .join_asof_by(
            quotes.lazy(),
            col("timestamp"),
            col("timestamp"),
            [col("symbol")],  // Match by symbol first
            [col("symbol")],
            AsofStrategy::Backward,  // Nearest earlier
            None,  // No tolerance
        )
        .collect()
}
```

## Sorting

```rust
use polars::prelude::*;

fn sort_operations(df: DataFrame) -> PolarsResult<DataFrame> {
    // Single column
    let sorted = df.clone().lazy()
        .sort([col("value")], Default::default())
        .collect()?;

    // Descending
    let desc = df.clone().lazy()
        .sort(
            [col("value")],
            SortMultipleOptions::default().with_order_descending(true),
        )
        .collect()?;

    // Multiple columns
    let multi = df.clone().lazy()
        .sort_by_exprs(
            vec![col("category"), col("value")],
            SortMultipleOptions::default()
                .with_order_descending_multi([false, true]),  // category asc, value desc
        )
        .collect()?;

    // Nulls last
    let nulls_last = df.clone().lazy()
        .sort(
            [col("value")],
            SortMultipleOptions::default().with_nulls_last(true),
        )
        .collect()?;

    Ok(sorted)
}
```

## Transformations

### Concatenation

```rust
use polars::prelude::*;

fn concat_operations(df1: DataFrame, df2: DataFrame) -> PolarsResult<DataFrame> {
    // Vertical (stack rows)
    let stacked = concat(
        [df1.clone().lazy(), df2.clone().lazy()],
        UnionArgs::default(),
    )?.collect()?;

    // Horizontal (stack columns)
    let horizontal = concat(
        [df1.lazy(), df2.lazy()],
        UnionArgs {
            how: JoinType::Cross,  // Cross join for horizontal
            ..Default::default()
        },
    )?.collect()?;

    Ok(stacked)
}
```

### Pivot and Unpivot

```rust
use polars::prelude::*;

fn pivot_operations(df: DataFrame) -> PolarsResult<()> {
    // Pivot (wide format) - requires "pivot" feature
    let pivoted = pivot::pivot(
        &df,
        [PlSmallStr::from_static("date")],           // index
        Some([PlSmallStr::from_static("product")]),  // columns
        Some([PlSmallStr::from_static("sales")]),    // values
        false,
        Some(first()),  // Aggregation function
        None,
    )?;

    // Unpivot (long format)
    let unpivoted = df.unpivot(
        [PlSmallStr::from_static("date")],           // id columns
        [PlSmallStr::from_static("A"), PlSmallStr::from_static("B")],  // value columns
    )?;

    Ok(())
}
```

### Explode

```rust
use polars::prelude::*;

fn explode_operation(df: DataFrame) -> PolarsResult<DataFrame> {
    // Explode list column into rows
    df.explode([PlSmallStr::from("items")])
}
```
