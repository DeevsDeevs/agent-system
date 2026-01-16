# Polars Operations Reference

This reference covers all common Polars operations with comprehensive examples.

**Contents:** Selection | Filtering | Grouping/Aggregation | Window Functions | Sorting | Conditional | String | Date/Time | List | Struct | Unique/Duplicate | Sampling | Renaming

## Selection Operations

### Select Columns

**Basic selection:**
```python
# Select specific columns
df.select("name", "age", "city")

# Using expressions
df.select(pl.col("name"), pl.col("age"))
```

**Pattern-based selection:**
```python
# All columns starting with "sales_"
df.select(pl.col("^sales_.*$"))

# All numeric columns
df.select(pl.col(pl.NUMERIC_DTYPES))

# All columns except specific ones
df.select(pl.all().exclude("id", "timestamp"))
```

**Computed columns:**
```python
df.select(
    "name",
    (pl.col("age") * 12).alias("age_in_months"),
    (pl.col("salary") * 1.1).alias("salary_after_raise")
)
```

### With Columns (Add/Modify)

Add new columns or modify existing ones while preserving all other columns:

```python
# Add new columns
df.with_columns(
    (pl.col("age") * 2).alias("age_doubled"),
    (pl.col("first_name") + " " + pl.col("last_name")).alias("full_name")
)

# Modify existing columns
df.with_columns(
    pl.col("name").str.to_uppercase().alias("name"),
    pl.col("salary").cast(pl.Float64).alias("salary")
)

# Multiple operations in parallel
df.with_columns(
    pl.col("value") * 10,
    pl.col("value") * 100,
    pl.col("value") * 1000,
)
```

## Filtering Operations

### Basic Filtering

```python
# Single condition
df.filter(pl.col("age") > 25)

# Multiple conditions (AND)
df.filter(
    pl.col("age") > 25,
    pl.col("city") == "NY"
)

# OR conditions
df.filter(
    (pl.col("age") > 30) | (pl.col("salary") > 100000)
)

# NOT condition
df.filter(~pl.col("active"))
df.filter(pl.col("city") != "NY")
```

### Advanced Filtering

**String operations:**
```python
# Contains substring
df.filter(pl.col("name").str.contains("John"))

# Starts with
df.filter(pl.col("email").str.starts_with("admin"))

# Regex match
df.filter(pl.col("phone").str.contains(r"^\d{3}-\d{3}-\d{4}$"))
```

**Membership checks:**
```python
# In list
df.filter(pl.col("city").is_in(["NY", "LA", "SF"]))

# Not in list
df.filter(~pl.col("status").is_in(["inactive", "deleted"]))
```

**Range filters:**
```python
# Between values
df.filter(pl.col("age").is_between(25, 35))

# Date range
df.filter(
    pl.col("date") >= pl.date(2023, 1, 1),
    pl.col("date") <= pl.date(2023, 12, 31)
)
```

**Null filtering:**
```python
# Filter out nulls
df.filter(pl.col("value").is_not_null())

# Keep only nulls
df.filter(pl.col("value").is_null())
```

## Grouping and Aggregation

### Basic Group By

```python
# Group by single column
df.group_by("department").agg(
    pl.col("salary").mean().alias("avg_salary"),
    pl.len().alias("employee_count")
)

# Group by multiple columns
df.group_by("department", "location").agg(
    pl.col("salary").sum()
)

# Maintain order
df.group_by("category", maintain_order=True).agg(
    pl.col("value").sum()
)
```

### Aggregation Functions

**Count and length:**
```python
df.group_by("category").agg(
    pl.len().alias("count"),
    pl.col("id").count().alias("non_null_count"),
    pl.col("id").n_unique().alias("unique_count")
)
```

**Statistical aggregations:**
```python
df.group_by("group").agg(
    pl.col("value").sum().alias("total"),
    pl.col("value").mean().alias("average"),
    pl.col("value").median().alias("median"),
    pl.col("value").std().alias("std_dev"),
    pl.col("value").var().alias("variance"),
    pl.col("value").min().alias("minimum"),
    pl.col("value").max().alias("maximum"),
    pl.col("value").quantile(0.95).alias("p95")
)
```

**First and last:**
```python
df.group_by("user_id").agg(
    pl.col("timestamp").first().alias("first_seen"),
    pl.col("timestamp").last().alias("last_seen"),
    pl.col("event").first().alias("first_event")
)
```

**List aggregation:**
```python
# Collect values into lists
df.group_by("category").agg(
    pl.col("item").alias("all_items")  # Creates list column
)
```

### Conditional Aggregations

Filter within aggregations:

```python
df.group_by("department").agg(
    # Count high earners
    (pl.col("salary") > 100000).sum().alias("high_earners"),

    # Average of filtered values
    pl.col("salary").filter(pl.col("bonus") > 0).mean().alias("avg_with_bonus"),

    # Conditional sum
    pl.when(pl.col("active"))
      .then(pl.col("sales"))
      .otherwise(0)
      .sum()
      .alias("active_sales")
)
```

### Multiple Aggregations

Combine multiple aggregations efficiently:

```python
df.group_by("store_id").agg(
    pl.col("transaction_id").count().alias("num_transactions"),
    pl.col("amount").sum().alias("total_sales"),
    pl.col("amount").mean().alias("avg_transaction"),
    pl.col("customer_id").n_unique().alias("unique_customers"),
    pl.col("amount").max().alias("largest_transaction"),
    pl.col("timestamp").min().alias("first_transaction_date"),
    pl.col("timestamp").max().alias("last_transaction_date")
)
```

## Window Functions

Window functions apply aggregations while preserving the original row count.

### Basic Window Operations

**Group statistics:**
```python
# Add group mean to each row
df.with_columns(
    pl.col("age").mean().over("department").alias("avg_age_by_dept")
)

# Multiple group columns
df.with_columns(
    pl.col("value").mean().over("category", "region").alias("group_avg")
)
```

**Ranking:**
```python
df.with_columns(
    # Rank within groups
    pl.col("score").rank().over("team").alias("rank"),

    # Dense rank (no gaps)
    pl.col("score").rank(method="dense").over("team").alias("dense_rank"),

    # Row number
    pl.col("timestamp").sort().rank(method="ordinal").over("user_id").alias("row_num")
)
```

### Window Mapping Strategies

**group_to_rows (default):**
Preserves original row order:
```python
df.with_columns(
    pl.col("value").mean().over("category", mapping_strategy="group_to_rows").alias("group_mean")
)
```

**explode:**
Faster, groups rows together:
```python
df.with_columns(
    pl.col("value").mean().over("category", mapping_strategy="explode").alias("group_mean")
)
```

**join:**
Creates list columns:
```python
df.with_columns(
    pl.col("value").over("category", mapping_strategy="join").alias("group_values")
)
```

### Rolling Windows

**Time-based rolling:**
```python
df.with_columns(
    pl.col("value").rolling_mean(
        window_size="7d",
        by="date"
    ).alias("rolling_avg")
)
```

**Row-based rolling:**
```python
df.with_columns(
    pl.col("value").rolling_sum(window_size=3).alias("rolling_sum"),
    pl.col("value").rolling_max(window_size=5).alias("rolling_max")
)
```

### Cumulative Operations

```python
df.with_columns(
    pl.col("value").cum_sum().over("group").alias("cumsum"),
    pl.col("value").cum_max().over("group").alias("cummax"),
    pl.col("value").cum_min().over("group").alias("cummin"),
    pl.col("value").cum_prod().over("group").alias("cumprod")
)
```

### Shift and Lag/Lead

```python
df.with_columns(
    # Previous value (lag)
    pl.col("value").shift(1).over("user_id").alias("prev_value"),

    # Next value (lead)
    pl.col("value").shift(-1).over("user_id").alias("next_value"),

    # Calculate difference from previous
    (pl.col("value") - pl.col("value").shift(1).over("user_id")).alias("diff")
)
```

## Sorting

### Basic Sorting

```python
# Sort by single column
df.sort("age")

# Sort descending
df.sort("age", descending=True)

# Sort by multiple columns
df.sort("department", "age")

# Mixed sorting order
df.sort(["department", "salary"], descending=[False, True])
```

### Advanced Sorting

**Null handling:**
```python
# Nulls first
df.sort("value", nulls_last=False)

# Nulls last
df.sort("value", nulls_last=True)
```

**Sort by expression:**
```python
# Sort by computed value
df.sort(pl.col("first_name").str.len())

# Sort by multiple expressions
df.sort(
    pl.col("last_name").str.to_lowercase(),
    pl.col("age").abs()
)
```

## Conditional Operations

### When/Then/Otherwise

```python
# Basic conditional
df.with_columns(
    pl.when(pl.col("age") >= 18)
        .then("adult")
        .otherwise("minor")
        .alias("status")
)

# Multiple conditions
df.with_columns(
    pl.when(pl.col("score") >= 90)
        .then("A")
        .when(pl.col("score") >= 80)
        .then("B")
        .when(pl.col("score") >= 70)
        .then("C")
        .otherwise("F")
        .alias("category")
)

# Conditional computation
df.with_columns(
    pl.when(pl.col("is_member"))
        .then(pl.col("price") * 0.9)
        .otherwise(pl.col("price"))
        .alias("adjusted_price")
)
```

## String Operations

### Common String Methods

```python
df.with_columns(
    # Case conversion
    pl.col("name").str.to_uppercase().alias("upper"),
    pl.col("name").str.to_lowercase().alias("lower"),
    pl.col("name").str.to_titlecase().alias("title"),

    # Trimming
    pl.col("text").str.strip_chars().alias("trimmed"),

    # Substring
    pl.col("name").str.slice(0, 3).alias("first_3"),

    # Replace
    pl.col("text").str.replace("old", "new").alias("cleaned"),
    pl.col("text").str.replace_all("old", "new").alias("cleaned_all"),

    # Split
    pl.col("full_name").str.split(" ").alias("parts"),

    # Length
    pl.col("name").str.len_chars().alias("name_length")
)
```

### String Filtering

```python
# Contains
df.filter(pl.col("email").str.contains("@gmail.com"))

# Starts/ends with
df.filter(pl.col("name").str.starts_with("A"))
df.filter(pl.col("file").str.ends_with(".csv"))

# Regex matching
df.filter(pl.col("phone").str.contains(r"^\d{3}-\d{4}$"))
```

## Date and Time Operations

### Date Parsing

```python
# Parse strings to dates
df.with_columns(
    pl.col("date_str").str.strptime(pl.Date, "%Y-%m-%d").alias("date"),
    pl.col("dt_str").str.strptime(pl.Datetime, "%Y-%m-%d %H:%M:%S").alias("datetime")
)
```

### Date Components

```python
df.with_columns(
    pl.col("date").dt.year().alias("year"),
    pl.col("date").dt.month().alias("month"),
    pl.col("date").dt.day().alias("day"),
    pl.col("date").dt.weekday().alias("weekday"),
    pl.col("datetime").dt.hour().alias("hour"),
    pl.col("datetime").dt.minute().alias("minute")
)
```

### Date Arithmetic

```python
# Add duration
df.with_columns(
    (pl.col("date") + pl.duration(weeks=1)).alias("next_week"),
    (pl.col("date") + pl.duration(months=1)).alias("next_month")
)

# Difference between dates
df.with_columns(
    days_diff=(pl.col("end_date") - pl.col("start_date")).dt.total_days()
)
```

### Date Filtering

```python
# Filter by date range
df.filter(
    pl.col("date").is_between(pl.date(2023, 1, 1), pl.date(2023, 12, 31))
)

# Filter by year
df.filter(pl.col("date").dt.year() == 2023)

# Filter by month
df.filter(pl.col("date").dt.month().is_in([6, 7, 8]))  # Summer months
```

## List Operations

### Working with List Columns

```python
# Create list column
df.with_columns(
    pl.col("item1", "item2", "item3").to_list().alias("items_list")
)

# List operations
df.with_columns(
    pl.col("items").list.len().alias("list_len"),
    pl.col("items").list.first().alias("first_item"),
    pl.col("items").list.last().alias("last_item"),
    pl.col("items").list.unique().alias("unique_items"),
    pl.col("items").list.sort().alias("sorted_items")
)

# Explode lists to rows
df.explode("items")

# Filter list elements
df.with_columns(
    pl.col("items").list.eval(pl.element() > 10).alias("filtered")
)
```

## Struct Operations

### Working with Nested Structures

```python
# Create struct column
df.with_columns(
    address=pl.struct(["street", "city", "zip"])
)

# Access struct fields
df.with_columns(
    pl.col("address").struct.field("city").alias("city")
)

# Unnest struct to columns
df.unnest("address")
```

## Unique and Duplicate Operations

```python
# Get unique rows
df.unique()

# Unique on specific columns
df.unique(subset=["name", "email"])

# Keep first/last duplicate
df.unique(subset=["id"], keep="first")
df.unique(subset=["id"], keep="last")

# Identify duplicates
df.with_columns(
    pl.col("id").is_duplicated().alias("is_duplicate")
)

# Count duplicates
df.group_by("email").agg(
    pl.len().alias("count")
).filter(pl.col("count") > 1)
```

## Sampling

```python
# Random sample
df.sample(n=100)

# Sample fraction
df.sample(fraction=0.1)

# Sample with seed for reproducibility
df.sample(n=100, seed=42)
```

## Column Renaming

```python
# Rename specific columns
df.rename({"old_name": "new_name", "age": "years"})

# Rename with expression
df.select(pl.col("*").name.suffix("_renamed"))
df.select(pl.col("*").name.prefix("data_"))
df.select(pl.col("*").name.to_uppercase())
```
