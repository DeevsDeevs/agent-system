"""
Pandas to Polars migration examples.

Side-by-side comparison of common operations.
Run with: uv run python pandas_migration.py
"""

import polars as pl

# Sample data
data = {
    "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
    "department": ["Engineering", "Sales", "Engineering", "Sales", "Engineering"],
    "salary": [100000, 80000, 120000, 90000, 110000],
    "years": [5, 3, 8, 4, 6],
}


def basic_operations():
    """Basic DataFrame operations."""
    df = pl.DataFrame(data)
    print("=== Basic Operations ===\n")

    # Select columns
    # pandas: df[["name", "salary"]]
    selected = df.select("name", "salary")
    print("Select columns:")
    print(selected)

    # Filter rows
    # pandas: df[df["salary"] > 95000]
    filtered = df.filter(pl.col("salary") > 95000)
    print("\nFilter salary > 95000:")
    print(filtered)

    # Add computed column
    # pandas: df["bonus"] = df["salary"] * 0.1
    with_bonus = df.with_columns(
        (pl.col("salary") * 0.1).alias("bonus")
    )
    print("\nWith bonus column:")
    print(with_bonus)


def groupby_operations():
    """Group by and aggregation."""
    df = pl.DataFrame(data)
    print("\n=== Group By Operations ===\n")

    # Basic groupby
    # pandas: df.groupby("department")["salary"].mean()
    by_dept = df.group_by("department").agg(
        pl.col("salary").mean().alias("avg_salary"),
        pl.col("salary").max().alias("max_salary"),
        pl.len().alias("count"),
    )
    print("Group by department:")
    print(by_dept)

    # Window function (transform equivalent)
    # pandas: df["dept_avg"] = df.groupby("department")["salary"].transform("mean")
    with_dept_avg = df.with_columns(
        pl.col("salary").mean().over("department").alias("dept_avg"),
        pl.col("salary").rank().over("department").alias("salary_rank"),
    )
    print("\nWindow functions (dept avg and rank):")
    print(with_dept_avg)


def conditional_operations():
    """Conditional column creation."""
    df = pl.DataFrame(data)
    print("\n=== Conditional Operations ===\n")

    # pandas: np.where(df["salary"] > 100000, "high", "normal")
    with_tier = df.with_columns(
        pl.when(pl.col("salary") > 100000)
        .then(pl.lit("high"))
        .when(pl.col("salary") > 85000)
        .then(pl.lit("medium"))
        .otherwise(pl.lit("normal"))
        .alias("salary_tier")
    )
    print("Salary tiers:")
    print(with_tier)


def chained_operations():
    """Chained operations (method chaining)."""
    df = pl.DataFrame(data)
    print("\n=== Chained Operations ===\n")

    # Complex pipeline
    result = (
        df.filter(pl.col("years") >= 4)
        .with_columns(
            (pl.col("salary") * 1.1).alias("new_salary"),
            (pl.col("salary") / pl.col("years")).alias("salary_per_year"),
        )
        .group_by("department")
        .agg(
            pl.col("new_salary").mean().alias("avg_new_salary"),
            pl.col("salary_per_year").mean().alias("avg_salary_per_year"),
        )
        .sort("avg_new_salary", descending=True)
    )
    print("Complex pipeline result:")
    print(result)


def lazy_vs_eager():
    """Demonstrate lazy evaluation benefits."""
    df = pl.DataFrame(data)
    print("\n=== Lazy vs Eager ===\n")

    # Eager: executes immediately
    eager_result = df.filter(pl.col("salary") > 90000).select("name", "salary")
    print("Eager result:")
    print(eager_result)

    # Lazy: builds query plan, optimizes, then executes
    lazy_result = (
        df.lazy()
        .filter(pl.col("salary") > 90000)
        .select("name", "salary")
    )
    print("\nLazy query plan:")
    print(lazy_result.explain())

    print("\nLazy result (after .collect()):")
    print(lazy_result.collect())


def main():
    basic_operations()
    groupby_operations()
    conditional_operations()
    chained_operations()
    lazy_vs_eager()


if __name__ == "__main__":
    main()
