"""
Signal pipeline: Actor publishes EMA signal → Strategy trades on crossover.
Runs out of the box with TestInstrumentProvider — no external data needed.
Demonstrates the native publish_signal/subscribe_signal/on_signal API.
"""

from decimal import Decimal

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.common.actor import Actor
from nautilus_trader.config import ActorConfig, StrategyConfig
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide
from nautilus_trader.model.identifiers import InstrumentId, TraderId, Venue
from nautilus_trader.model.objects import Currency, Money
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler
from nautilus_trader.test_kit.providers import TestDataProvider, TestInstrumentProvider
from nautilus_trader.trading.strategy import Strategy


class MomentumActorConfig(ActorConfig, frozen=True):
    fast_period: int = 10
    slow_period: int = 30
    emit_interval: int = 50  # publish every N ticks


class MomentumActor(Actor):
    """Computes EMA fast/slow difference and publishes as signal."""

    def __init__(self, config: MomentumActorConfig) -> None:
        super().__init__(config)
        self.ema_fast = ExponentialMovingAverage(config.fast_period)
        self.ema_slow = ExponentialMovingAverage(config.slow_period)
        self.count = 0
        self.signals_published = 0

    def on_start(self) -> None:
        inst = self.cache.instruments()[0]
        self.subscribe_trade_ticks(inst.id)

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.count += 1
        self.ema_fast.handle_trade_tick(tick)
        self.ema_slow.handle_trade_tick(tick)

        if not self.ema_slow.initialized:
            return

        if self.count % self.config.emit_interval == 0:
            momentum = self.ema_fast.value - self.ema_slow.value
            self.publish_signal(name="momentum", value=momentum, ts_event=tick.ts_event)
            self.signals_published += 1


class MomentumTraderConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    trade_size: Decimal = Decimal("0.10")
    entry_threshold: float = 0.0  # go long when momentum > threshold


class MomentumTrader(Strategy):
    """Trades based on momentum signal from MomentumActor."""

    def __init__(self, config: MomentumTraderConfig) -> None:
        super().__init__(config)
        self.instrument = None
        self.signals_received = 0
        self._prev_momentum = None

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        self.subscribe_signal(name="momentum")

    def on_signal(self, signal) -> None:
        self.signals_received += 1
        momentum = signal.value
        is_long = bool(self.cache.positions_open(instrument_id=self.config.instrument_id))

        if self._prev_momentum is not None:
            crossed_up = self._prev_momentum <= self.config.entry_threshold < momentum
            crossed_down = self._prev_momentum >= self.config.entry_threshold > momentum

            if crossed_up and not is_long:
                order = self.order_factory.market(
                    instrument_id=self.config.instrument_id,
                    order_side=OrderSide.BUY,
                    quantity=self.instrument.make_qty(self.config.trade_size),
                )
                self.submit_order(order)

            elif crossed_down and is_long:
                self.close_all_positions(self.config.instrument_id)

        self._prev_momentum = momentum

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

    actor = MomentumActor(MomentumActorConfig(fast_period=10, slow_period=30, emit_interval=50))
    engine.add_actor(actor)

    strategy = MomentumTrader(MomentumTraderConfig(instrument_id=instrument.id))
    engine.add_strategy(strategy)
    engine.run()

    print(f"\nActor: {actor.count} ticks → {actor.signals_published} signals published")
    print(f"Strategy: {strategy.signals_received} signals received")
    print()
    print(engine.trader.generate_order_fills_report())
    print(engine.trader.generate_positions_report())
