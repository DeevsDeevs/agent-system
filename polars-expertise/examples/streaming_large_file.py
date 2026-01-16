"""
Streaming large files with Polars.

Demonstrates processing files larger than available RAM using:
- scan_csv / scan_parquet (lazy scanning)
- Streaming execution engine
- Sink operations for streaming writes

Run with: uv run python streaming_large_file.py
"""

import polars as pl
from pathlib import Path
import tempfile


def create_sample_data(path: Path, n_rows: int = 100000):
    """Create a sample CSV file for demonstration."""
    import random

    with open(path, "w") as f:
        f.write("id,category,value,timestamp\n")
        categories = ["A", "B", "C", "D", "E"]
        for i in range(n_rows):
            cat = random.choice(categories)
            val = random.gauss(100, 20)
            ts = f"2024-01-{(i % 28) + 1:02d} {(i % 24):02d}:00:00"
            f.write(f"{i},{cat},{val:.2f},{ts}\n")

    print(f"Created {path} with {n_rows} rows")


def streaming_aggregation(input_path: Path):
    """
    Aggregate large file using streaming.

    Key pattern: scan_* + lazy operations + collect(engine="streaming")
    """
    print("\n=== Streaming Aggregation ===\n")

    # scan_csv returns LazyFrame - no data loaded yet
    lf = pl.scan_csv(input_path)

    # Build query plan
    result = (
        lf.filter(pl.col("value") > 80)  # Predicate pushdown
        .group_by("category")
        .agg(
            pl.col("value").mean().alias("avg_value"),
            pl.col("value").std().alias("std_value"),
            pl.len().alias("count"),
        )
        .sort("avg_value", descending=True)
    )

    # Show optimized plan
    print("Query plan:")
    print(result.explain())

    # Execute with streaming engine
    # For truly large files, this processes in chunks
    df = result.collect(engine="streaming")
    print("\nResult:")
    print(df)

    return df


def streaming_sink(input_path: Path, output_path: Path):
    """
    Stream data directly to output file without loading into memory.

    Key pattern: scan_* + transformations + sink_*
    """
    print("\n=== Streaming Sink (File to File) ===\n")

    lf = pl.scan_csv(input_path)

    # Transform and sink directly to parquet
    # Data flows through without full materialization
    (
        lf.filter(pl.col("value") > 90)
        .with_columns(
            pl.col("value").alias("original_value"),
            (pl.col("value") * 1.1).alias("adjusted_value"),
        )
        .select("id", "category", "original_value", "adjusted_value", "timestamp")
        .sink_parquet(output_path)
    )

    print(f"Streamed filtered data to {output_path}")

    # Verify output
    result = pl.scan_parquet(output_path).collect()
    print(f"Output contains {len(result)} rows")
    print(result.head(5))


def check_streaming_compatibility(input_path: Path):
    """
    Check if a query can be streamed.

    Some operations break streaming:
    - Sorts on large data (may need to buffer)
    - Certain join types
    - Some aggregations
    """
    print("\n=== Streaming Compatibility Check ===\n")

    lf = pl.scan_csv(input_path)

    # This query streams well
    streamable = (
        lf.filter(pl.col("value") > 80)
        .group_by("category")
        .agg(pl.col("value").sum())
    )

    print("Streamable query plan:")
    print(streamable.explain(streaming=True))

    # This may not stream fully (sort requires buffering)
    maybe_not_streamable = (
        lf.sort("value", descending=True)
        .head(1000)
    )

    print("\nQuery with sort (may buffer):")
    print(maybe_not_streamable.explain(streaming=True))


def projection_pushdown_demo(input_path: Path):
    """
    Demonstrate projection pushdown - only read needed columns.
    """
    print("\n=== Projection Pushdown ===\n")

    # Only reads 'category' and 'value' columns from disk
    lf = pl.scan_csv(input_path)

    result = (
        lf.select("category", "value")  # Projection pushdown
        .filter(pl.col("value") > 100)   # Predicate pushdown
        .group_by("category")
        .agg(pl.col("value").mean())
    )

    print("Optimized plan (note: only needed columns read):")
    print(result.explain())

    df = result.collect()
    print("\nResult:")
    print(df)


def main():
    # Create temp directory for demo files
    with tempfile.TemporaryDirectory() as tmpdir:
        input_csv = Path(tmpdir) / "large_data.csv"
        output_parquet = Path(tmpdir) / "filtered_data.parquet"

        # Create sample data
        create_sample_data(input_csv, n_rows=100000)

        # Run demos
        streaming_aggregation(input_csv)
        streaming_sink(input_csv, output_parquet)
        check_streaming_compatibility(input_csv)
        projection_pushdown_demo(input_csv)

        print("\n=== Summary ===")
        print("Key patterns for large files:")
        print("1. Use scan_csv / scan_parquet (not read_*)")
        print("2. Build lazy query with .filter(), .select(), .group_by()")
        print("3. Execute with .collect(engine='streaming')")
        print("4. For file-to-file: use .sink_parquet() / .sink_csv()")
        print("5. Put filters and projections early in pipeline")


if __name__ == "__main__":
    main()
