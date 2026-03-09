"""
Data wranglers test: all wrangler types, data round-trip through catalog.
Validates: TradeTickDataWrangler, BarDataWrangler, catalog write/read consistency.
"""
import sys
import os
import shutil
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from nautilus_trader.persistence.wranglers import (
    TradeTickDataWrangler,
    BarDataWrangler,
)
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.model.data import TradeTick, Bar, BarType
from nautilus_trader.test_kit.providers import TestInstrumentProvider, TestDataProvider

CATALOG_PATH = Path(__file__).parent / "test_wrangler_catalog"
RESULTS = {}


def log(phase: str, msg: str, ok: bool = True):
    status = "OK" if ok else "FAIL"
    RESULTS[phase] = {"status": status, "detail": msg}
    print(f"  [{status}] {phase}: {msg}", flush=True)


def test_data_wranglers():
    print("\n" + "=" * 60)
    print("TEST: Data Wranglers + Catalog Round-Trip")
    print("=" * 60)

    ethusdt = TestInstrumentProvider.ethusdt_binance()
    dp = TestDataProvider()

    # Trade tick wrangler
    df_ticks = dp.read_csv_ticks("binance/ethusdt-trades.csv")
    log("read_csv_ticks", f"DataFrame shape: {df_ticks.shape}, columns: {list(df_ticks.columns)}")

    wrangler_tt = TradeTickDataWrangler(instrument=ethusdt)
    trade_ticks = wrangler_tt.process(df_ticks)
    log("wrangle_trade_ticks", f"{len(trade_ticks)} TradeTick objects, type={type(trade_ticks[0]).__name__}",
        ok=len(trade_ticks) > 0 and isinstance(trade_ticks[0], TradeTick))

    tick0 = trade_ticks[0]
    log("trade_tick_fields", f"price={tick0.price}, size={tick0.size}, aggressor={tick0.aggressor_side}, ts_event={tick0.ts_event}")

    # Bar wrangler
    try:
        df_bars = dp.read_csv_bars("binance/BTCUSDT-1m-2024-01-01-2024-01-02.csv")
        log("read_csv_bars", f"DataFrame shape: {df_bars.shape}, columns: {list(df_bars.columns)}")

        btcusdt = TestInstrumentProvider.btcusdt_binance()
        bar_type = BarType.from_str(f"{btcusdt.id}-1-MINUTE-LAST-EXTERNAL")
        wrangler_bar = BarDataWrangler(bar_type=bar_type, instrument=btcusdt)
        bars = wrangler_bar.process(df_bars)
        log("wrangle_bars", f"{len(bars)} Bar objects, type={type(bars[0]).__name__}",
            ok=len(bars) > 0 and isinstance(bars[0], Bar))

        bar0 = bars[0]
        log("bar_fields", f"open={bar0.open}, high={bar0.high}, low={bar0.low}, close={bar0.close}, vol={bar0.volume}")
    except Exception as e:
        log("bar_wrangler", f"Bar wrangler error: {e}", ok=False)

    # Catalog round-trip for trade ticks
    if CATALOG_PATH.exists():
        shutil.rmtree(CATALOG_PATH)
    CATALOG_PATH.mkdir(parents=True)

    catalog = ParquetDataCatalog(CATALOG_PATH)
    catalog.write_data([ethusdt])
    catalog.write_data(trade_ticks)
    log("catalog_write", f"Wrote {len(trade_ticks)} trade ticks to catalog")

    # Read back and verify count matches
    read_back = catalog.trade_ticks(instrument_ids=[str(ethusdt.id)])
    read_count = len(read_back) if read_back is not None else 0
    log("catalog_read", f"Read back {read_count} trade ticks", ok=read_count == len(trade_ticks))

    # Check timestamps preserved
    if read_count > 0:
        first_orig = trade_ticks[0].ts_event
        first_read = read_back[0].ts_event
        log("timestamp_match", f"Original first ts={first_orig}, Read first ts={first_read}",
            ok=first_orig == first_read)

    # Query with time range
    try:
        types = catalog.list_data_types()
        log("catalog_types", f"Types in catalog: {types}")

        # query_first/last_timestamp needs identifier= param, else returns None
        first_ts = catalog.query_first_timestamp(TradeTick, identifier=str(ethusdt.id))
        last_ts = catalog.query_last_timestamp(TradeTick, identifier=str(ethusdt.id))
        log("catalog_timestamps", f"First: {first_ts}, Last: {last_ts}",
            ok=first_ts is not None and last_ts is not None)
    except Exception as e:
        log("catalog_query", f"Query error: {e}", ok=False)

    # Cleanup
    if CATALOG_PATH.exists():
        shutil.rmtree(CATALOG_PATH)
    log("cleanup", "Done")

    print("\n" + "-" * 40)
    ok_count = sum(1 for v in RESULTS.values() if v["status"] == "OK")
    fail_count = sum(1 for v in RESULTS.values() if v["status"] == "FAIL")
    print(f"DataWranglers: {ok_count} passed, {fail_count} failed")
    print("-" * 40)
    return fail_count == 0


if __name__ == "__main__":
    success = test_data_wranglers()
    sys.exit(0 if success else 1)
