"""
EMA Crossover strategy with full backtest setup.

Demonstrates:
- StrategyConfig with frozen=True
- Indicator registration and auto-update
- Order factory usage
- BacktestEngine low-level API
- Venue and instrument configuration
"""

from decimal import Decimal

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, StrategyConfig
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId, TraderId, Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.trading.strategy import Strategy


class EMACrossConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    bar_type: BarType
    trade_size: Decimal
    fast_ema_period: int = 10
    slow_ema_period: int = 20


class EMACross(Strategy):
    def __init__(self, config: EMACrossConfig) -> None:
        super().__init__(config)
        self.instrument = None
        self.fast_ema = ExponentialMovingAverage(config.fast_ema_period)
        self.slow_ema = ExponentialMovingAverage(config.slow_ema_period)

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.log.error(f"Instrument not found: {self.config.instrument_id}")
            self.stop()
            return

        self.register_indicator_for_bars(self.config.bar_type, self.fast_ema)
        self.register_indicator_for_bars(self.config.bar_type, self.slow_ema)
        self.request_bars(self.config.bar_type)
        self.subscribe_bars(self.config.bar_type)

    def on_bar(self, bar: Bar) -> None:
        if not self.indicators_initialized():
            return

        if self.fast_ema.value >= self.slow_ema.value:
            if self.portfolio.is_flat(self.config.instrument_id):
                self._buy()
        elif self.fast_ema.value < self.slow_ema.value:
            if self.portfolio.is_net_long(self.config.instrument_id):
                self._sell()

    def _buy(self) -> None:
        order = self.order_factory.market(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(self.config.trade_size),
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)

    def _sell(self) -> None:
        order = self.order_factory.market(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.SELL,
            quantity=self.instrument.make_qty(self.config.trade_size),
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)
        self.close_all_positions(self.config.instrument_id)


def run_backtest():
    engine_config = BacktestEngineConfig(trader_id=TraderId("BACKTESTER-001"))
    engine = BacktestEngine(config=engine_config)

    SIM = Venue("SIM")
    engine.add_venue(
        venue=SIM,
        oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,
        base_currency=USD,
        starting_balances=[Money(100_000, USD)],
    )

    # Load your instrument and data here:
    # engine.add_instrument(instrument)
    # engine.add_data(bars)

    strategy_config = EMACrossConfig(
        instrument_id=InstrumentId.from_str("AAPL.SIM"),
        bar_type=BarType.from_str("AAPL.SIM-1-MINUTE-LAST-INTERNAL"),
        trade_size=Decimal("100"),
        fast_ema_period=10,
        slow_ema_period=20,
    )

    strategy = EMACross(config=strategy_config)
    engine.add_strategy(strategy)
    engine.run()

    # Results
    print(engine.trader.generate_order_fills_report())
    print(engine.trader.generate_positions_report())
    print(engine.trader.generate_account_report(SIM))

    engine.dispose()


if __name__ == "__main__":
    run_backtest()
