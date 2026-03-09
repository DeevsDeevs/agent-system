"""
BacktestEngine deep test: low-level API with venue, instruments, strategy, indicators.
Validates: engine lifecycle, venue setup, data ingestion, strategy execution, indicator flow, results.
"""
import sys
import os
import shutil
from pathlib import Path
from decimal import Decimal
from datetime import timedelta

sys.path.insert(0, os.path.dirname(__file__))

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig, StrategyConfig
from nautilus_trader.indicators import ExponentialMovingAverage, RelativeStrengthIndex, BollingerBands
from nautilus_trader.model.data import TradeTick, Bar, BarType
from nautilus_trader.model.enums import OmsType, AccountType, OrderSide, TimeInForce, BookType
from nautilus_trader.model.identifiers import Venue, TraderId
from nautilus_trader.model.objects import Money, Currency
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider, TestDataProvider
from nautilus_trader.trading.strategy import Strategy

RESULTS = {}


def log(phase: str, msg: str, ok: bool = True):
    status = "OK" if ok else "FAIL"
    RESULTS[phase] = {"status": status, "detail": msg}
    print(f"  [{status}] {phase}: {msg}", flush=True)


class IndicatorStrategyConfig(StrategyConfig, frozen=True):
    ema_period: int = 20
    rsi_period: int = 14
    bb_period: int = 20


class IndicatorStrategy(Strategy):
    """Strategy that registers indicators and tracks fills."""

    def __init__(self, config: IndicatorStrategyConfig) -> None:
        super().__init__(config)
        self.ema = ExponentialMovingAverage(config.ema_period)
        self.rsi = RelativeStrengthIndex(config.rsi_period)
        self.bb = BollingerBands(config.bb_period, 2.0)
        self.bar_count = 0
        self.trade_tick_count = 0
        self.orders_submitted = 0
        self.fills = 0
        self.indicators_initialized_at = None

    def on_start(self) -> None:
        instrument = self.cache.instruments()[0]
        self.instrument = instrument
        bar_type = BarType.from_str(f"{instrument.id}-1-MINUTE-LAST-INTERNAL")
        self.register_indicator_for_bars(bar_type, self.ema)
        self.register_indicator_for_bars(bar_type, self.rsi)
        self.register_indicator_for_bars(bar_type, self.bb)
        self.subscribe_bars(bar_type)
        self.subscribe_trade_ticks(instrument.id)

    def on_bar(self, bar: Bar) -> None:
        self.bar_count += 1
        if not self.indicators_initialized():
            return
        if self.indicators_initialized_at is None:
            self.indicators_initialized_at = self.bar_count
        if self.bar_count % 50 == 0:
            side = OrderSide.BUY if self.rsi.value < 50 else OrderSide.SELL
            order = self.order_factory.market(
                instrument_id=self.instrument.id,
                order_side=side,
                quantity=self.instrument.make_qty(Decimal("0.01")),
            )
            self.submit_order(order)
            self.orders_submitted += 1

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.trade_tick_count += 1

    def on_order_filled(self, event) -> None:
        self.fills += 1

    def on_stop(self) -> None:
        pass


def test_backtest_engine():
    print("\n" + "=" * 60)
    print("TEST: BacktestEngine (low-level API)")
    print("=" * 60)

    # Phase 1: Engine creation
    config = BacktestEngineConfig(
        trader_id=TraderId("BACKTEST-001"),
        logging=LoggingConfig(log_level="ERROR"),
    )
    engine = BacktestEngine(config=config)
    log("engine_create", f"BacktestEngine created, trader_id={config.trader_id}")

    # Phase 2: Add venue
    venue = Venue("BINANCE")
    engine.add_venue(
        venue=venue,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=None,
        starting_balances=[Money(100_000.0, Currency.from_str("USDT"))],
    )
    log("add_venue", f"Venue {venue} added, OMS=NETTING, MARGIN, 100k USDT")

    # Phase 3: Add instrument
    ethusdt = TestInstrumentProvider.ethusdt_binance()
    engine.add_instrument(ethusdt)
    log("add_instrument", f"Instrument {ethusdt.id}, price_prec={ethusdt.price_precision}, size_prec={ethusdt.size_precision}")

    # Phase 4: Load and add data
    dp = TestDataProvider()
    df = dp.read_csv_ticks("binance/ethusdt-trades.csv")
    wrangler = TradeTickDataWrangler(instrument=ethusdt)
    ticks = wrangler.process(df)
    engine.add_data(ticks)
    log("add_data", f"{len(ticks)} trade ticks loaded, first_ts={ticks[0].ts_event}")

    # Phase 5: Add strategy with indicators
    strategy = IndicatorStrategy(IndicatorStrategyConfig())
    engine.add_strategy(strategy)
    log("add_strategy", "IndicatorStrategy with EMA(20), RSI(14), BB(20)")

    # Phase 6: Run backtest
    engine.run()
    log("run", f"Backtest completed")

    # Phase 7: Validate results
    bars = strategy.bar_count
    trades = strategy.trade_tick_count
    orders = strategy.orders_submitted
    fills = strategy.fills
    init_at = strategy.indicators_initialized_at

    log("bars_processed", f"{bars} bars processed")
    log("trade_ticks_processed", f"{trades} trade ticks received")
    log("indicator_init", f"Indicators initialized at bar {init_at}" if init_at else "Indicators never initialized", ok=init_at is not None)

    ema_val = strategy.ema.value
    rsi_val = strategy.rsi.value
    bb_upper = strategy.bb.upper
    bb_lower = strategy.bb.lower
    log("indicator_values", f"EMA={ema_val:.4f}, RSI={rsi_val:.2f}, BB=[{bb_lower:.4f}, {bb_upper:.4f}]",
        ok=ema_val > 0 and 0 < rsi_val < 100)

    log("orders_fills", f"{orders} orders submitted, {fills} fills", ok=fills > 0)

    # Phase 8: Account state
    accounts = engine.cache.accounts()
    if accounts:
        acc = accounts[0]
        bals = acc.balances()
        bal_str = ", ".join(f"{b.currency}: {b.total}" for b in bals.values())
        log("account_state", f"Post-backtest balance: {bal_str}")

    # Phase 9: Positions
    positions = engine.cache.positions()
    closed = engine.cache.positions_closed()
    log("positions", f"{len(positions)} total, {len(closed)} closed")

    # Phase 10: Engine dispose
    engine.dispose()
    log("dispose", "Engine disposed cleanly")

    print("\n" + "-" * 40)
    ok_count = sum(1 for v in RESULTS.values() if v["status"] == "OK")
    fail_count = sum(1 for v in RESULTS.values() if v["status"] == "FAIL")
    print(f"BacktestEngine: {ok_count} passed, {fail_count} failed")
    print("-" * 40)
    return fail_count == 0


if __name__ == "__main__":
    success = test_backtest_engine()
    sys.exit(0 if success else 1)
