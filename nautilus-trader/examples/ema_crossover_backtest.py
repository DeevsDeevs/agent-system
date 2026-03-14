"""
EMA crossover strategy backtest.
Runs out of the box with TestInstrumentProvider — no external data needed.
Goes long on golden cross (fast > slow), flat on death cross (fast < slow).

Rust counterpart: ema_crossover_backtest.rs (same directory)
"""

from decimal import Decimal

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import StrategyConfig
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide
from nautilus_trader.model.identifiers import InstrumentId, TraderId, Venue
from nautilus_trader.model.objects import Currency, Money
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler
from nautilus_trader.test_kit.providers import TestDataProvider, TestInstrumentProvider
from nautilus_trader.trading.strategy import Strategy


class CrossoverConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    trade_size: Decimal = Decimal("0.10")
    fast_period: int = 10
    slow_period: int = 30


class EmaCrossover(Strategy):
    def __init__(self, config: CrossoverConfig) -> None:
        super().__init__(config)
        self.ema_fast = ExponentialMovingAverage(config.fast_period)
        self.ema_slow = ExponentialMovingAverage(config.slow_period)
        self.instrument = None
        self._prev_fast_above = None

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        bar_type = BarType.from_str(f"{self.config.instrument_id}-1-MINUTE-LAST-INTERNAL")
        self.register_indicator_for_bars(bar_type, self.ema_fast)
        self.register_indicator_for_bars(bar_type, self.ema_slow)
        self.subscribe_bars(bar_type)

    def on_bar(self, bar: Bar) -> None:
        if not self.indicators_initialized():
            return

        fast_above = self.ema_fast.value > self.ema_slow.value
        if self._prev_fast_above is None:
            self._prev_fast_above = fast_above
            return

        is_long = bool(self.cache.positions_open(instrument_id=self.config.instrument_id))

        if fast_above and not self._prev_fast_above and not is_long:
            order = self.order_factory.market(
                instrument_id=self.config.instrument_id,
                order_side=OrderSide.BUY,
                quantity=self.instrument.make_qty(self.config.trade_size),
            )
            self.submit_order(order)

        elif not fast_above and self._prev_fast_above and is_long:
            self.close_all_positions(self.config.instrument_id)

        self._prev_fast_above = fast_above

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)
        self.close_all_positions(self.config.instrument_id)


if __name__ == "__main__":
    USDT = Currency.from_str("USDT")
    instrument = TestInstrumentProvider.ethusdt_binance()
    engine = BacktestEngine(config=BacktestEngineConfig(trader_id=TraderId("BACKTESTER-001")))

    engine.add_venue(
        venue=Venue("BINANCE"),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=None,
        starting_balances=[Money(100_000, USDT)],
    )
    engine.add_instrument(instrument)

    dp = TestDataProvider()
    df = dp.read_csv_ticks("binance/ethusdt-trades.csv")
    wrangler = TradeTickDataWrangler(instrument=instrument)
    ticks = wrangler.process(df)
    engine.add_data(ticks)

    strategy = EmaCrossover(CrossoverConfig(
        instrument_id=instrument.id,
        fast_period=10,
        slow_period=30,
        trade_size=Decimal("0.10"),
    ))
    engine.add_strategy(strategy)
    engine.run()

    print(engine.trader.generate_order_fills_report())
    print(engine.trader.generate_positions_report())
