"""
Actor + Custom Data deep test: Actor publishes custom data, Strategy consumes it.
Validates: Actor lifecycle, custom Data class, MessageBus pub/sub, on_data handler.
"""
import sys
import os
from decimal import Decimal
from datetime import timedelta

sys.path.insert(0, os.path.dirname(__file__))

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.common.actor import Actor
from nautilus_trader.config import ActorConfig, LoggingConfig, StrategyConfig
from nautilus_trader.core.data import Data
from nautilus_trader.indicators import ExponentialMovingAverage
from nautilus_trader.model.data import TradeTick, DataType, BarType
from nautilus_trader.model.enums import OmsType, AccountType, OrderSide
from nautilus_trader.model.identifiers import Venue, ClientId
from nautilus_trader.model.objects import Money, Currency
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider, TestDataProvider
from nautilus_trader.trading.strategy import Strategy

RESULTS = {}


def log(phase: str, msg: str, ok: bool = True):
    status = "OK" if ok else "FAIL"
    RESULTS[phase] = {"status": status, "detail": msg}
    print(f"  [{status}] {phase}: {msg}", flush=True)


# Custom data type: a signal from an Actor
class SignalData(Data):
    def __init__(self, name: str, value: float, ts_event: int, ts_init: int) -> None:
        self.name = name
        self.value = value
        self._ts_event = ts_event
        self._ts_init = ts_init

    @property
    def ts_event(self) -> int:
        return self._ts_event

    @property
    def ts_init(self) -> int:
        return self._ts_init

    def __repr__(self):
        return f"SignalData(name={self.name}, value={self.value:.4f})"


class SignalActorConfig(ActorConfig, frozen=True):
    ema_period: int = 10


class SignalActor(Actor):
    """Actor that computes EMA on trade ticks and publishes as custom data."""

    def __init__(self, config: SignalActorConfig) -> None:
        super().__init__(config)
        self.ema = ExponentialMovingAverage(config.ema_period)
        self.tick_count = 0
        self.signals_published = 0

    def on_start(self) -> None:
        instruments = self.cache.instruments()
        if instruments:
            self.instrument = instruments[0]
            self.subscribe_trade_ticks(self.instrument.id)

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.tick_count += 1
        self.ema.handle_trade_tick(tick)
        if self.ema.initialized and self.tick_count % 100 == 0:
            signal = SignalData(
                name="ema_signal",
                value=self.ema.value,
                ts_event=tick.ts_event,
                ts_init=tick.ts_init,
            )
            self.publish_data(
                data_type=DataType(SignalData, metadata={"name": "ema_signal"}),
                data=signal,
            )
            self.signals_published += 1

    def on_stop(self) -> None:
        pass


class SignalConsumerConfig(StrategyConfig, frozen=True):
    pass


class SignalConsumer(Strategy):
    """Strategy that subscribes to custom SignalData from the Actor."""

    def __init__(self, config: SignalConsumerConfig) -> None:
        super().__init__(config)
        self.signals_received = 0
        self.last_signal_value = None
        self.trade_count = 0
        self.orders = 0
        self.fills = 0

    def on_start(self) -> None:
        instruments = self.cache.instruments()
        if instruments:
            self.instrument = instruments[0]
            self.subscribe_trade_ticks(self.instrument.id)
        self.subscribe_data(
            data_type=DataType(SignalData, metadata={"name": "ema_signal"}),
        )

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.trade_count += 1

    def on_data(self, data) -> None:
        if isinstance(data, SignalData):
            self.signals_received += 1
            self.last_signal_value = data.value
            if self.signals_received == 1 and self.instrument:
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


def test_actors_custom_data():
    print("\n" + "=" * 60)
    print("TEST: Actors + Custom Data (MessageBus pub/sub)")
    print("=" * 60)

    # Setup engine
    config = BacktestEngineConfig(logging=LoggingConfig(log_level="ERROR"))
    engine = BacktestEngine(config=config)

    venue = Venue("BINANCE")
    engine.add_venue(
        venue=venue,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=None,
        starting_balances=[Money(100_000.0, Currency.from_str("USDT"))],
    )

    ethusdt = TestInstrumentProvider.ethusdt_binance()
    engine.add_instrument(ethusdt)

    dp = TestDataProvider()
    df = dp.read_csv_ticks("binance/ethusdt-trades.csv")
    wrangler = TradeTickDataWrangler(instrument=ethusdt)
    ticks = wrangler.process(df)
    engine.add_data(ticks)
    log("setup", f"Engine ready: {len(ticks)} ticks, venue={venue}")

    # Add actor
    actor = SignalActor(SignalActorConfig(ema_period=10))
    engine.add_actor(actor)
    log("add_actor", "SignalActor added (EMA(10), publishes SignalData every 100 ticks)")

    # Add strategy
    strategy = SignalConsumer(SignalConsumerConfig())
    engine.add_strategy(strategy)
    log("add_strategy", "SignalConsumer added (subscribes to SignalData)")

    # Run
    engine.run()
    log("run", "Backtest completed")

    # Validate actor
    log("actor_ticks", f"Actor processed {actor.tick_count} trade ticks", ok=actor.tick_count > 0)
    log("actor_ema", f"Actor EMA initialized, final={actor.ema.value:.4f}", ok=actor.ema.initialized)
    log("actor_signals", f"Actor published {actor.signals_published} signals", ok=actor.signals_published > 0)

    # Validate strategy received custom data
    log("strategy_signals", f"Strategy received {strategy.signals_received} signals",
        ok=strategy.signals_received > 0)
    log("strategy_last_val", f"Last signal value: {strategy.last_signal_value:.4f}" if strategy.last_signal_value else "No signals",
        ok=strategy.last_signal_value is not None)
    log("signal_match", f"Published={actor.signals_published}, Received={strategy.signals_received}",
        ok=actor.signals_published == strategy.signals_received)

    # Validate order triggered by signal
    log("signal_order", f"Orders={strategy.orders}, Fills={strategy.fills}", ok=strategy.fills > 0)

    engine.dispose()
    log("dispose", "Engine disposed")

    print("\n" + "-" * 40)
    ok_count = sum(1 for v in RESULTS.values() if v["status"] == "OK")
    fail_count = sum(1 for v in RESULTS.values() if v["status"] == "FAIL")
    print(f"Actors+CustomData: {ok_count} passed, {fail_count} failed")
    print("-" * 40)
    return fail_count == 0


if __name__ == "__main__":
    success = test_actors_custom_data()
    sys.exit(0 if success else 1)
