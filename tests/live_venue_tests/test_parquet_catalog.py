"""
ParquetDataCatalog deep test: write data, read back, use in BacktestNode.
Validates: catalog creation, data persistence, data retrieval, BacktestNode high-level API.
"""
import sys
import os
import shutil
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, os.path.dirname(__file__))

from nautilus_trader.backtest.engine import BacktestEngineConfig
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.config import (
    BacktestDataConfig,
    BacktestRunConfig,
    BacktestVenueConfig,
    LoggingConfig,
    StrategyConfig,
)
from nautilus_trader.model.data import TradeTick, Bar, BarType
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider, TestDataProvider
from nautilus_trader.trading.strategy import Strategy

CATALOG_PATH = Path(__file__).parent / "test_catalog"
RESULTS = {}


def log(phase: str, msg: str, ok: bool = True):
    status = "OK" if ok else "FAIL"
    RESULTS[phase] = {"status": status, "detail": msg}
    print(f"  [{status}] {phase}: {msg}", flush=True)


class SimpleCounterConfig(StrategyConfig, frozen=True):
    pass


class SimpleCounter(Strategy):
    """Minimal strategy that counts events for verification."""

    def __init__(self, config: SimpleCounterConfig) -> None:
        super().__init__(config)
        self.tick_count = 0
        self.bar_count = 0
        self.orders = 0
        self.fills = 0

    def on_start(self) -> None:
        instruments = self.cache.instruments()
        if instruments:
            self.instrument = instruments[0]
            self.subscribe_trade_ticks(self.instrument.id)

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.tick_count += 1
        if self.tick_count == 100:
            order = self.order_factory.market(
                instrument_id=self.instrument.id,
                order_side=OrderSide.BUY,
                quantity=self.instrument.make_qty(Decimal("0.01")),
            )
            self.submit_order(order)
            self.orders += 1

    def on_order_filled(self, event) -> None:
        self.fills += 1

    def on_stop(self) -> None:
        pass


def test_parquet_catalog():
    print("\n" + "=" * 60)
    print("TEST: ParquetDataCatalog + BacktestNode")
    print("=" * 60)

    # Phase 1: Create catalog
    if CATALOG_PATH.exists():
        shutil.rmtree(CATALOG_PATH)
    CATALOG_PATH.mkdir(parents=True)
    catalog = ParquetDataCatalog(CATALOG_PATH)
    log("catalog_create", f"Created at {CATALOG_PATH}")

    # Phase 2: Prepare instrument and data
    ethusdt = TestInstrumentProvider.ethusdt_binance()
    dp = TestDataProvider()
    df = dp.read_csv_ticks("binance/ethusdt-trades.csv")
    wrangler = TradeTickDataWrangler(instrument=ethusdt)
    ticks = wrangler.process(df)
    log("data_prepare", f"{len(ticks)} trade ticks wrangled for {ethusdt.id}")

    # Phase 3: Write instrument to catalog
    catalog.write_data([ethusdt])
    log("write_instrument", f"Instrument {ethusdt.id} written to catalog")

    # Phase 4: Write trade ticks to catalog
    catalog.write_data(ticks)
    log("write_ticks", f"{len(ticks)} trade ticks written to catalog")

    # Phase 5: Read back from catalog
    cat_instruments = catalog.instruments()
    log("read_instruments", f"{len(cat_instruments)} instruments in catalog", ok=len(cat_instruments) > 0)

    cat_ticks = catalog.trade_ticks(instrument_ids=[str(ethusdt.id)])
    tick_count = len(cat_ticks) if cat_ticks is not None else 0
    log("read_ticks", f"{tick_count} trade ticks read back", ok=tick_count > 0)

    # Phase 6: Check other catalog query methods
    try:
        data_types = catalog.list_data_types()
        log("list_data_types", f"Available types: {data_types}")
    except Exception as e:
        log("list_data_types", f"list_data_types() failed: {e}", ok=False)

    # Phase 7: BacktestNode with catalog data
    engine_config = BacktestEngineConfig(
        logging=LoggingConfig(log_level="ERROR"),
    )

    venue_config = BacktestVenueConfig(
        name="BINANCE",
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=None,
        starting_balances=["100000 USDT"],
    )

    data_config = BacktestDataConfig(
        catalog_path=str(CATALOG_PATH),
        data_cls=TradeTick,
        instrument_id=str(ethusdt.id),
    )

    run_config = BacktestRunConfig(
        engine=engine_config,
        venues=[venue_config],
        data=[data_config],
    )
    log("backtest_config", "BacktestRunConfig created with catalog data")

    # Phase 8: Run via BacktestNode
    node = BacktestNode(configs=[run_config])
    node.build()

    # Add strategy to the engine after build
    strategy = SimpleCounter(SimpleCounterConfig())
    engine = node.get_engine(run_config.id)
    engine.add_strategy(strategy)

    results = node.run()
    log("backtest_run", f"BacktestNode returned {len(results)} result(s)")

    if results:
        r = results[0]
        log("result_details", f"instance_id={r.instance_id}, trader_id={r.trader_id}")

    log("strategy_counts", f"ticks={strategy.tick_count}, orders={strategy.orders}, fills={strategy.fills}",
        ok=strategy.tick_count > 0)

    # Phase 9: Cleanup
    if CATALOG_PATH.exists():
        shutil.rmtree(CATALOG_PATH)
    log("cleanup", "Catalog cleaned up")

    print("\n" + "-" * 40)
    ok_count = sum(1 for v in RESULTS.values() if v["status"] == "OK")
    fail_count = sum(1 for v in RESULTS.values() if v["status"] == "FAIL")
    print(f"ParquetCatalog: {ok_count} passed, {fail_count} failed")
    print("-" * 40)
    return fail_count == 0


if __name__ == "__main__":
    success = test_parquet_catalog()
    sys.exit(0 if success else 1)
