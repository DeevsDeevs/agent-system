"""
Order types + OMS deep test: all order factory methods, NETTING vs HEDGING,
position flipping, order state machine, risk engine, cache queries, reports.
"""
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.dirname(__file__))

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig, StrategyConfig, RiskEngineConfig
from nautilus_trader.model.data import TradeTick, QuoteTick
from nautilus_trader.model.enums import (
    OmsType, AccountType, OrderSide, TimeInForce, OrderType,
    OrderStatus, PositionSide, TriggerType,
)
from nautilus_trader.model.identifiers import Venue, ExecAlgorithmId
from nautilus_trader.model.objects import Money, Currency, Price, Quantity
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider, TestDataProvider
from nautilus_trader.trading.strategy import Strategy

RESULTS = {}


def log(phase: str, msg: str, ok: bool = True):
    status = "OK" if ok else "FAIL"
    RESULTS[phase] = {"status": status, "detail": msg}
    print(f"  [{status}] {phase}: {msg}", flush=True)


class OrderTestConfig(StrategyConfig, frozen=True):
    pass


class OrderTestStrategy(Strategy):
    """Exercises all order types, cache queries, position management."""

    def __init__(self, config: OrderTestConfig) -> None:
        super().__init__(config)
        self.tick_count = 0
        self.instrument = None
        self.events = []
        self.test_done = False

    def on_start(self) -> None:
        self.instrument = self.cache.instruments()[0]
        self.subscribe_trade_ticks(self.instrument.id)

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.tick_count += 1
        if self.tick_count == 50 and not self.test_done:
            self.test_done = True
            self._run_all_order_tests(tick)

    def _run_all_order_tests(self, tick: TradeTick):
        inst = self.instrument
        mid_price = float(tick.price)

        # Test 1: Market order
        market_buy = self.order_factory.market(
            instrument_id=inst.id,
            order_side=OrderSide.BUY,
            quantity=inst.make_qty(Decimal("0.01")),
        )
        self.events.append(("market_buy_type", market_buy.order_type.name))
        self.submit_order(market_buy)

        # Test 2: Limit order (far from market)
        limit_buy = self.order_factory.limit(
            instrument_id=inst.id,
            order_side=OrderSide.BUY,
            quantity=inst.make_qty(Decimal("0.01")),
            price=inst.make_price(Decimal(str(mid_price * 0.8))),
            time_in_force=TimeInForce.GTC,
            post_only=True,
        )
        self.events.append(("limit_buy_type", limit_buy.order_type.name))
        self.submit_order(limit_buy)

        # Test 3: Stop market order
        try:
            stop = self.order_factory.stop_market(
                instrument_id=inst.id,
                order_side=OrderSide.SELL,
                quantity=inst.make_qty(Decimal("0.01")),
                trigger_price=inst.make_price(Decimal(str(mid_price * 0.9))),
                trigger_type=TriggerType.LAST_PRICE,
            )
            self.events.append(("stop_market_type", stop.order_type.name))
            self.submit_order(stop)
        except Exception as e:
            self.events.append(("stop_market_error", str(e)))

        # Test 4: Stop limit order
        try:
            stop_limit = self.order_factory.stop_limit(
                instrument_id=inst.id,
                order_side=OrderSide.SELL,
                quantity=inst.make_qty(Decimal("0.01")),
                price=inst.make_price(Decimal(str(mid_price * 0.89))),
                trigger_price=inst.make_price(Decimal(str(mid_price * 0.9))),
                trigger_type=TriggerType.LAST_PRICE,
            )
            self.events.append(("stop_limit_type", stop_limit.order_type.name))
            self.submit_order(stop_limit)
        except Exception as e:
            self.events.append(("stop_limit_error", str(e)))

        # Test 5: Market-to-limit
        try:
            mtl = self.order_factory.market_to_limit(
                instrument_id=inst.id,
                order_side=OrderSide.BUY,
                quantity=inst.make_qty(Decimal("0.01")),
            )
            self.events.append(("market_to_limit_type", mtl.order_type.name))
            self.submit_order(mtl)
        except Exception as e:
            self.events.append(("market_to_limit_error", str(e)))

        # Test 6: Instrument properties
        self.events.append(("price_precision", inst.price_precision))
        self.events.append(("size_precision", inst.size_precision))
        self.events.append(("min_quantity", str(inst.min_quantity) if inst.min_quantity else "None"))
        self.events.append(("max_quantity", str(inst.max_quantity) if inst.max_quantity else "None"))
        self.events.append(("price_increment", str(inst.price_increment)))
        self.events.append(("size_increment", str(inst.size_increment)))
        self.events.append(("maker_fee", str(inst.maker_fee)))
        self.events.append(("taker_fee", str(inst.taker_fee)))

        # Test 7: Cache queries
        all_orders = self.cache.orders()
        open_orders = self.cache.orders_open()
        self.events.append(("cache_all_orders", len(all_orders)))
        self.events.append(("cache_open_orders", len(open_orders)))

        # Test 8: Cancel the limit order
        if limit_buy.status in (OrderStatus.ACCEPTED, OrderStatus.SUBMITTED):
            self.cancel_order(limit_buy)
            self.events.append(("cancel_submitted", True))

    def on_order_filled(self, event) -> None:
        self.events.append(("filled", f"side={event.order_side.name}, qty={event.last_qty}, px={event.last_px}"))

        # Check position after fill
        positions = self.cache.positions_open(instrument_id=self.instrument.id)
        pos = positions[0] if positions else None
        if pos:
            self.events.append(("position", f"side={pos.side.name}, qty={pos.quantity}, avg_px={pos.avg_px_open}"))

    def on_order_rejected(self, event) -> None:
        self.events.append(("rejected", event.reason))

    def on_order_denied(self, event) -> None:
        self.events.append(("denied", event.reason))

    def on_order_canceled(self, event) -> None:
        self.events.append(("canceled", str(event.client_order_id)))

    def on_order_accepted(self, event) -> None:
        self.events.append(("accepted", str(event.client_order_id)))

    def on_stop(self) -> None:
        self.cancel_all_orders(self.instrument.id)
        self.close_all_positions(self.instrument.id)


class HedgingTestConfig(StrategyConfig, frozen=True):
    oms_type: str = "HEDGING"


class HedgingStrategy(Strategy):
    """Tests HEDGING OMS: multiple positions per instrument."""

    def __init__(self, config: HedgingTestConfig) -> None:
        super().__init__(config)
        self.tick_count = 0
        self.positions_opened = 0
        self.test_done = False
        self.events = []

    def on_start(self) -> None:
        self.instrument = self.cache.instruments()[0]
        self.subscribe_trade_ticks(self.instrument.id)

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.tick_count += 1
        if self.tick_count == 20 and not self.test_done:
            self.test_done = True
            inst = self.instrument
            # Open two separate BUY positions
            o1 = self.order_factory.market(
                instrument_id=inst.id, order_side=OrderSide.BUY,
                quantity=inst.make_qty(Decimal("0.01")),
            )
            self.submit_order(o1)
            o2 = self.order_factory.market(
                instrument_id=inst.id, order_side=OrderSide.BUY,
                quantity=inst.make_qty(Decimal("0.02")),
            )
            self.submit_order(o2)

    def on_order_filled(self, event) -> None:
        self.positions_opened += 1
        positions = self.cache.positions()
        self.events.append(("fill", f"total_positions={len(positions)}"))

    def on_stop(self) -> None:
        self.close_all_positions(self.instrument.id)


class NettingFlipConfig(StrategyConfig, frozen=True):
    pass


class NettingFlipStrategy(Strategy):
    """Tests NETTING: position flipping from LONG to SHORT."""

    def __init__(self, config: NettingFlipConfig) -> None:
        super().__init__(config)
        self.tick_count = 0
        self.phase = 0
        self.events = []

    def on_start(self) -> None:
        self.instrument = self.cache.instruments()[0]
        self.subscribe_trade_ticks(self.instrument.id)

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.tick_count += 1
        inst = self.instrument
        if self.tick_count == 20 and self.phase == 0:
            self.phase = 1
            o = self.order_factory.market(
                instrument_id=inst.id, order_side=OrderSide.BUY,
                quantity=inst.make_qty(Decimal("0.05")),
            )
            self.submit_order(o)
        elif self.tick_count == 40 and self.phase == 1:
            self.phase = 2
            # Sell more than we have → should flip to SHORT
            o = self.order_factory.market(
                instrument_id=inst.id, order_side=OrderSide.SELL,
                quantity=inst.make_qty(Decimal("0.10")),
            )
            self.submit_order(o)

    def on_order_filled(self, event) -> None:
        positions = self.cache.positions_open(instrument_id=self.instrument.id)
        pos = positions[0] if positions else None
        if pos:
            self.events.append(("fill_pos", f"side={pos.side.name}, qty={pos.quantity}, realized_pnl={pos.realized_pnl}"))
        else:
            self.events.append(("fill_pos", "no position"))

    def on_stop(self) -> None:
        self.close_all_positions(self.instrument.id)


def load_data():
    ethusdt = TestInstrumentProvider.ethusdt_binance()
    dp = TestDataProvider()
    df = dp.read_csv_ticks("binance/ethusdt-trades.csv")
    wrangler = TradeTickDataWrangler(instrument=ethusdt)
    ticks = wrangler.process(df)
    return ethusdt, ticks


def test_order_types():
    print("\n" + "=" * 60)
    print("TEST: Order Types + Cache Queries")
    print("=" * 60)

    ethusdt, ticks = load_data()
    config = BacktestEngineConfig(logging=LoggingConfig(log_level="ERROR"))
    engine = BacktestEngine(config=config)
    engine.add_venue(
        venue=Venue("BINANCE"), oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN, base_currency=None,
        starting_balances=[Money(100_000.0, Currency.from_str("USDT"))],
    )
    engine.add_instrument(ethusdt)
    engine.add_data(ticks)

    strategy = OrderTestStrategy(OrderTestConfig())
    engine.add_strategy(strategy)
    engine.run()

    for name, val in strategy.events:
        is_ok = "error" not in name.lower() and "denied" not in name.lower()
        log(name, str(val), ok=is_ok)

    # Check reports
    try:
        fills_report = engine.trader.generate_order_fills_report()
        log("fills_report", f"Type={type(fills_report).__name__}, rows={len(fills_report) if hasattr(fills_report, '__len__') else 'N/A'}")
    except Exception as e:
        log("fills_report", f"Error: {e}", ok=False)

    try:
        positions_report = engine.trader.generate_positions_report()
        log("positions_report", f"Type={type(positions_report).__name__}, rows={len(positions_report) if hasattr(positions_report, '__len__') else 'N/A'}")
    except Exception as e:
        log("positions_report", f"Error: {e}", ok=False)

    engine.dispose()


def test_netting_flip():
    print("\n" + "=" * 60)
    print("TEST: NETTING Position Flip (LONG→SHORT)")
    print("=" * 60)

    ethusdt, ticks = load_data()
    config = BacktestEngineConfig(logging=LoggingConfig(log_level="ERROR"))
    engine = BacktestEngine(config=config)
    engine.add_venue(
        venue=Venue("BINANCE"), oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN, base_currency=None,
        starting_balances=[Money(100_000.0, Currency.from_str("USDT"))],
    )
    engine.add_instrument(ethusdt)
    engine.add_data(ticks)

    strategy = NettingFlipStrategy(NettingFlipConfig())
    engine.add_strategy(strategy)
    engine.run()

    for name, val in strategy.events:
        log(f"netting_{name}", val)

    # Verify position flip happened (strategy events already captured side=SHORT)
    # Position is closed by on_stop, so check events for SHORT side confirmation
    flip_confirmed = any("side=SHORT" in val for name, val in strategy.events if name == "fill_pos")
    log("netting_flip_to_short", f"flip_confirmed={flip_confirmed}", ok=flip_confirmed)

    # Check closed positions (on_stop closes them)
    closed = engine.cache.positions_closed()
    log("closed_positions", f"{len(closed)} closed positions")

    engine.dispose()


def test_hedging():
    print("\n" + "=" * 60)
    print("TEST: HEDGING OMS (multiple positions)")
    print("=" * 60)

    ethusdt, ticks = load_data()
    config = BacktestEngineConfig(logging=LoggingConfig(log_level="ERROR"))
    engine = BacktestEngine(config=config)
    engine.add_venue(
        venue=Venue("BINANCE"), oms_type=OmsType.HEDGING,
        account_type=AccountType.MARGIN, base_currency=None,
        starting_balances=[Money(100_000.0, Currency.from_str("USDT"))],
    )
    engine.add_instrument(ethusdt)
    engine.add_data(ticks)

    strategy = HedgingStrategy(HedgingTestConfig())
    engine.add_strategy(strategy)
    engine.run()

    for name, val in strategy.events:
        log(f"hedging_{name}", val)

    positions = engine.cache.positions()
    log("hedging_total_positions", f"{len(positions)} positions", ok=len(positions) >= 2)
    engine.dispose()


def main():
    test_order_types()
    print()
    test_netting_flip()
    print()
    test_hedging()

    print("\n" + "=" * 60)
    ok_count = sum(1 for v in RESULTS.values() if v["status"] == "OK")
    fail_count = sum(1 for v in RESULTS.values() if v["status"] == "FAIL")
    print(f"OrderTypes+OMS: {ok_count} passed, {fail_count} failed")
    print("=" * 60)
    return fail_count == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
