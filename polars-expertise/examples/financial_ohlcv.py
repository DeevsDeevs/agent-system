"""
Financial OHLCV resampling with Polars.

Demonstrates:
- group_by_dynamic for time-based resampling
- Rolling statistics (SMA, volatility)
- As-of joins for market data alignment
"""

import polars as pl
from datetime import datetime, timedelta
import random

# Generate sample tick data
def generate_tick_data(n_ticks: int = 10000) -> pl.DataFrame:
    base_time = datetime(2024, 1, 15, 9, 30, 0)
    symbols = ["AAPL", "GOOG", "MSFT"]

    data = []
    for i in range(n_ticks):
        symbol = random.choice(symbols)
        base_price = {"AAPL": 150.0, "GOOG": 140.0, "MSFT": 380.0}[symbol]
        data.append({
            "timestamp": base_time + timedelta(seconds=i * 0.5),
            "symbol": symbol,
            "price": base_price + random.gauss(0, 1),
            "volume": random.randint(100, 1000),
        })

    return pl.DataFrame(data).sort("timestamp")


def resample_to_ohlcv(df: pl.LazyFrame, interval: str = "1m") -> pl.LazyFrame:
    """Resample tick data to OHLCV bars."""
    return (
        df.sort("timestamp")
        .group_by_dynamic("timestamp", every=interval, group_by="symbol")
        .agg(
            pl.col("price").first().alias("open"),
            pl.col("price").max().alias("high"),
            pl.col("price").min().alias("low"),
            pl.col("price").last().alias("close"),
            pl.col("volume").sum().alias("volume"),
            pl.len().alias("tick_count"),
        )
    )


def add_technical_indicators(df: pl.LazyFrame) -> pl.LazyFrame:
    """Add common technical indicators."""
    return df.with_columns(
        # Simple Moving Averages
        pl.col("close").rolling_mean(window_size=5).over("symbol").alias("sma_5"),
        pl.col("close").rolling_mean(window_size=20).over("symbol").alias("sma_20"),

        # Volatility (rolling std of returns)
        pl.col("close")
        .pct_change()
        .over("symbol")
        .rolling_std(window_size=20)
        .over("symbol")
        .alias("volatility_20"),

        # VWAP
        (
            (pl.col("close") * pl.col("volume")).cum_sum().over("symbol")
            / pl.col("volume").cum_sum().over("symbol")
        ).alias("vwap"),
    )


def main():
    # Generate tick data
    print("Generating tick data...")
    ticks = generate_tick_data(10000)
    print(f"Generated {len(ticks)} ticks")
    print(ticks.head(5))

    # Resample to 1-minute OHLCV (lazy)
    print("\nResampling to 1-minute OHLCV bars...")
    ohlcv = resample_to_ohlcv(ticks.lazy(), "1m")

    # Add technical indicators
    print("Adding technical indicators...")
    result = add_technical_indicators(ohlcv).collect()

    print(f"\nResult: {len(result)} bars")
    print(result.head(10))

    # Filter example: high volatility periods
    high_vol = result.filter(pl.col("volatility_20") > 0.01)
    print(f"\nHigh volatility periods: {len(high_vol)} bars")


if __name__ == "__main__":
    main()
