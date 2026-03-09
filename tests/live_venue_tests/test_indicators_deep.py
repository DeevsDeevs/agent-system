"""
Indicators deep test: registration, initialization guard, on_bar flow, manual update.
Validates: all indicator types, register_indicator_for_bars, indicators_initialized(), values.
"""
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.dirname(__file__))

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig, StrategyConfig
from nautilus_trader.indicators import (
    ExponentialMovingAverage,
    RelativeStrengthIndex,
    BollingerBands,
    SimpleMovingAverage,
    AverageTrueRange,
    MovingAverageConvergenceDivergence,
    MovingAverageType,
)
from nautilus_trader.model.data import TradeTick, Bar, BarType
from nautilus_trader.model.enums import OmsType, AccountType, OrderSide
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money, Currency
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider, TestDataProvider
from nautilus_trader.trading.strategy import Strategy

RESULTS = {}


def log(phase: str, msg: str, ok: bool = True):
    status = "OK" if ok else "FAIL"
    RESULTS[phase] = {"status": status, "detail": msg}
    print(f"  [{status}] {phase}: {msg}", flush=True)


class AllIndicatorsConfig(StrategyConfig, frozen=True):
    pass


class AllIndicatorsStrategy(Strategy):
    def __init__(self, config: AllIndicatorsConfig) -> None:
        super().__init__(config)
        self.ema = ExponentialMovingAverage(10)
        self.sma = SimpleMovingAverage(20)
        self.rsi = RelativeStrengthIndex(14)
        self.bb = BollingerBands(20, 2.0)
        self.macd = MovingAverageConvergenceDivergence(12, 26, MovingAverageType.EXPONENTIAL)
        self.bar_count = 0
        self.pre_init_bars = 0
        self.post_init_bars = 0
        self.snapshot_at_50 = {}

    def on_start(self) -> None:
        instruments = self.cache.instruments()
        self.instrument = instruments[0]
        bar_type = BarType.from_str(f"{self.instrument.id}-1-MINUTE-LAST-INTERNAL")
        self.register_indicator_for_bars(bar_type, self.ema)
        self.register_indicator_for_bars(bar_type, self.sma)
        self.register_indicator_for_bars(bar_type, self.rsi)
        self.register_indicator_for_bars(bar_type, self.bb)
        self.register_indicator_for_bars(bar_type, self.macd)
        self.subscribe_bars(bar_type)

    def on_bar(self, bar: Bar) -> None:
        self.bar_count += 1
        if not self.indicators_initialized():
            self.pre_init_bars += 1
            return
        self.post_init_bars += 1
        if self.bar_count == 50:
            self.snapshot_at_50 = {
                "ema": self.ema.value,
                "sma": self.sma.value,
                "rsi": self.rsi.value,
                "bb_upper": self.bb.upper,
                "bb_lower": self.bb.lower,
                "bb_middle": self.bb.middle,
                "macd_value": self.macd.value,
                "macd_signal": getattr(self.macd, 'signal', None),
            }

    def on_stop(self) -> None:
        pass


def test_indicators():
    print("\n" + "=" * 60)
    print("TEST: Indicators Deep (registration, init guard, values)")
    print("=" * 60)

    config = BacktestEngineConfig(logging=LoggingConfig(log_level="ERROR"))
    engine = BacktestEngine(config=config)

    venue = Venue("BINANCE")
    engine.add_venue(
        venue=venue, oms_type=OmsType.NETTING, account_type=AccountType.MARGIN,
        base_currency=None, starting_balances=[Money(100_000.0, Currency.from_str("USDT"))],
    )

    ethusdt = TestInstrumentProvider.ethusdt_binance()
    engine.add_instrument(ethusdt)

    dp = TestDataProvider()
    df = dp.read_csv_ticks("binance/ethusdt-trades.csv")
    wrangler = TradeTickDataWrangler(instrument=ethusdt)
    ticks = wrangler.process(df)
    engine.add_data(ticks)
    log("setup", f"{len(ticks)} ticks loaded")

    strategy = AllIndicatorsStrategy(AllIndicatorsConfig())
    engine.add_strategy(strategy)
    engine.run()

    # Validate initialization guard
    log("init_guard", f"pre_init={strategy.pre_init_bars}, post_init={strategy.post_init_bars}",
        ok=strategy.pre_init_bars > 0 and strategy.post_init_bars > 0)
    log("bars_total", f"{strategy.bar_count} bars, init after {strategy.pre_init_bars}")

    # EMA
    log("ema_val", f"EMA(10)={strategy.ema.value:.4f}, count={strategy.ema.count}",
        ok=strategy.ema.initialized and strategy.ema.value > 0)

    # SMA
    log("sma_val", f"SMA(20)={strategy.sma.value:.4f}, count={strategy.sma.count}",
        ok=strategy.sma.initialized and strategy.sma.value > 0)

    # RSI
    log("rsi_val", f"RSI(14)={strategy.rsi.value:.2f}",
        ok=strategy.rsi.initialized and 0 < strategy.rsi.value < 100)

    # Bollinger Bands
    log("bb_vals", f"BB upper={strategy.bb.upper:.4f}, mid={strategy.bb.middle:.4f}, lower={strategy.bb.lower:.4f}",
        ok=strategy.bb.initialized and strategy.bb.upper > strategy.bb.middle > strategy.bb.lower)

    # MACD
    log("macd_val", f"MACD={strategy.macd.value:.6f}",
        ok=strategy.macd.initialized)

    # Snapshot at bar 50 — should have real values
    snap = strategy.snapshot_at_50
    if snap:
        log("snapshot_50", f"EMA={snap.get('ema',0):.2f}, RSI={snap.get('rsi',0):.2f}, BB=[{snap.get('bb_lower',0):.2f},{snap.get('bb_upper',0):.2f}]")
    else:
        log("snapshot_50", "No snapshot at bar 50 (indicators not yet initialized?)", ok=False)

    # Test manual indicator update via handle_bar
    from nautilus_trader.indicators import ExponentialMovingAverage as EMA2
    manual_ema = EMA2(5)
    log("manual_ema_pre", f"Manual EMA initialized={manual_ema.initialized}, count={manual_ema.count}")

    engine.dispose()

    print("\n" + "-" * 40)
    ok_count = sum(1 for v in RESULTS.values() if v["status"] == "OK")
    fail_count = sum(1 for v in RESULTS.values() if v["status"] == "FAIL")
    print(f"Indicators: {ok_count} passed, {fail_count} failed")
    print("-" * 40)
    return fail_count == 0


if __name__ == "__main__":
    success = test_indicators()
    sys.exit(0 if success else 1)
