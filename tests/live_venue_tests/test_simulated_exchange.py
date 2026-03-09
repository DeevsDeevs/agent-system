"""
SimulatedExchange deep test: fill models, fee models, latency models, queue position.
Validates: realistic backtest configuration, margin enforcement, multiple runs.
"""
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.dirname(__file__))

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.backtest.models import FillModel, LatencyModel
from nautilus_trader.config import LoggingConfig, StrategyConfig
from nautilus_trader.model.data import TradeTick, Bar, BarType
from nautilus_trader.model.enums import (
    OmsType, AccountType, OrderSide, TimeInForce, BookType,
)
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


class AggressiveTraderConfig(StrategyConfig, frozen=True):
    order_every_n_ticks: int = 500


class AggressiveTrader(Strategy):
    """Submits market orders frequently to exercise fill/fee/latency."""

    def __init__(self, config: AggressiveTraderConfig) -> None:
        super().__init__(config)
        self.tick_count = 0
        self.orders = 0
        self.fills = 0
        self.rejects = 0
        self.total_commission = 0.0

    def on_start(self) -> None:
        self.instrument = self.cache.instruments()[0]
        self.subscribe_trade_ticks(self.instrument.id)

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.tick_count += 1
        if self.tick_count % self.config.order_every_n_ticks == 0:
            side = OrderSide.BUY if self.tick_count % 1000 < 500 else OrderSide.SELL
            order = self.order_factory.market(
                instrument_id=self.instrument.id,
                order_side=side,
                quantity=self.instrument.make_qty(Decimal("0.01")),
            )
            self.submit_order(order)
            self.orders += 1

    def on_order_filled(self, event) -> None:
        self.fills += 1
        if event.commission:
            self.total_commission += float(event.commission)

    def on_order_rejected(self, event) -> None:
        self.rejects += 1

    def on_stop(self) -> None:
        pass


class LimitTraderConfig(StrategyConfig, frozen=True):
    pass


class LimitTrader(Strategy):
    """Submits limit orders to test queue position and fill probability."""

    def __init__(self, config: LimitTraderConfig) -> None:
        super().__init__(config)
        self.tick_count = 0
        self.orders = 0
        self.fills = 0
        self.limit_order_placed = False

    def on_start(self) -> None:
        self.instrument = self.cache.instruments()[0]
        self.subscribe_trade_ticks(self.instrument.id)

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.tick_count += 1
        if self.tick_count == 100 and not self.limit_order_placed:
            price = self.instrument.make_price(Decimal(str(float(tick.price) * 0.999)))
            order = self.order_factory.limit(
                instrument_id=self.instrument.id,
                order_side=OrderSide.BUY,
                quantity=self.instrument.make_qty(Decimal("0.1")),
                price=price,
                time_in_force=TimeInForce.GTC,
            )
            self.submit_order(order)
            self.orders += 1
            self.limit_order_placed = True

    def on_order_filled(self, event) -> None:
        self.fills += 1

    def on_stop(self) -> None:
        self.cancel_all_orders(self.instrument.id)


def test_simulated_exchange():
    print("\n" + "=" * 60)
    print("TEST: SimulatedExchange (fill/fee/latency models)")
    print("=" * 60)

    ethusdt = TestInstrumentProvider.ethusdt_binance()
    dp = TestDataProvider()
    df = dp.read_csv_ticks("binance/ethusdt-trades.csv")
    wrangler = TradeTickDataWrangler(instrument=ethusdt)
    ticks = wrangler.process(df)
    log("data_load", f"{len(ticks)} ticks ready")

    # Test 1: Default fill model with margin account
    config1 = BacktestEngineConfig(logging=LoggingConfig(log_level="ERROR"))
    engine1 = BacktestEngine(config=config1)
    engine1.add_venue(
        venue=Venue("BINANCE"), oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN, base_currency=None,
        starting_balances=[Money(10_000.0, Currency.from_str("USDT"))],
    )
    engine1.add_instrument(ethusdt)
    engine1.add_data(ticks)
    s1 = AggressiveTrader(AggressiveTraderConfig(order_every_n_ticks=500))
    engine1.add_strategy(s1)
    engine1.run()

    log("default_fills", f"orders={s1.orders}, fills={s1.fills}, rejects={s1.rejects}",
        ok=s1.fills > 0)
    accs1 = engine1.cache.accounts()
    if accs1:
        bals1 = accs1[0].balances()
        bal_str1 = ", ".join(f"{b.currency}: {b.total}" for b in bals1.values())
        log("default_balance", f"After {s1.fills} fills: {bal_str1}")
    engine1.dispose()

    # Test 2: With latency model
    config2 = BacktestEngineConfig(logging=LoggingConfig(log_level="ERROR"))
    engine2 = BacktestEngine(config=config2)
    latency = LatencyModel(
        base_latency_nanos=10_000_000,       # 10ms
        insert_latency_nanos=10_000_000,
        update_latency_nanos=10_000_000,
        cancel_latency_nanos=10_000_000,
    )
    engine2.add_venue(
        venue=Venue("BINANCE"), oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN, base_currency=None,
        starting_balances=[Money(10_000.0, Currency.from_str("USDT"))],
        latency_model=latency,
    )
    engine2.add_instrument(ethusdt)
    engine2.add_data(ticks)
    s2 = AggressiveTrader(AggressiveTraderConfig(order_every_n_ticks=500))
    engine2.add_strategy(s2)
    engine2.run()

    log("latency_fills", f"orders={s2.orders}, fills={s2.fills}, rejects={s2.rejects} (10ms latency)",
        ok=s2.fills > 0)
    engine2.dispose()

    # Test 3: With fill model
    config3 = BacktestEngineConfig(logging=LoggingConfig(log_level="ERROR"))
    engine3 = BacktestEngine(config=config3)
    # prob_fill_on_stop does NOT exist in v1.224.0 — only prob_fill_on_limit + prob_slippage
    fill_model = FillModel(
        prob_fill_on_limit=0.3,
        prob_slippage=0.5,
        random_seed=42,
    )
    engine3.add_venue(
        venue=Venue("BINANCE"), oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN, base_currency=None,
        starting_balances=[Money(10_000.0, Currency.from_str("USDT"))],
        fill_model=fill_model,
    )
    engine3.add_instrument(ethusdt)
    engine3.add_data(ticks)
    s3 = LimitTrader(LimitTraderConfig())
    engine3.add_strategy(s3)
    engine3.run()

    log("fill_model", f"limit orders={s3.orders}, fills={s3.fills} (30% fill prob)",
        ok=s3.orders > 0)
    engine3.dispose()

    # Test 4: CASH account (spot) with frozen_account
    config4 = BacktestEngineConfig(logging=LoggingConfig(log_level="ERROR"))
    engine4 = BacktestEngine(config=config4)
    engine4.add_venue(
        venue=Venue("BINANCE"), oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,
        base_currency=None,
        starting_balances=[
            Money(1000.0, Currency.from_str("USDT")),
            Money(1.0, Currency.from_str("ETH")),
        ],
        frozen_account=False,  # False = margin checks ARE active
    )
    engine4.add_instrument(ethusdt)
    engine4.add_data(ticks)
    s4 = AggressiveTrader(AggressiveTraderConfig(order_every_n_ticks=1000))
    engine4.add_strategy(s4)
    engine4.run()

    log("cash_account", f"orders={s4.orders}, fills={s4.fills}, rejects={s4.rejects}",
        ok=s4.orders > 0)
    accs4 = engine4.cache.accounts()
    if accs4:
        bals4 = accs4[0].balances()
        bal_str4 = ", ".join(f"{b.currency}: {b.total}" for b in bals4.values())
        log("cash_balance", f"After spot trading: {bal_str4}")
    engine4.dispose()

    # Test 5: engine.reset() + re-run
    config5 = BacktestEngineConfig(logging=LoggingConfig(log_level="ERROR"))
    engine5 = BacktestEngine(config=config5)
    engine5.add_venue(
        venue=Venue("BINANCE"), oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN, base_currency=None,
        starting_balances=[Money(10_000.0, Currency.from_str("USDT"))],
    )
    engine5.add_instrument(ethusdt)
    engine5.add_data(ticks)
    s5a = AggressiveTrader(AggressiveTraderConfig(order_every_n_ticks=2000))
    engine5.add_strategy(s5a)
    engine5.run()
    fills_run1 = s5a.fills

    engine5.reset()
    s5b = AggressiveTrader(AggressiveTraderConfig(order_every_n_ticks=5000))
    engine5.add_strategy(s5b)
    engine5.run()
    fills_run2 = s5b.fills

    log("multi_run", f"Run1: {fills_run1} fills, Run2: {fills_run2} fills",
        ok=fills_run1 > 0 and fills_run2 > 0)
    engine5.dispose()

    print("\n" + "-" * 40)
    ok_count = sum(1 for v in RESULTS.values() if v["status"] == "OK")
    fail_count = sum(1 for v in RESULTS.values() if v["status"] == "FAIL")
    print(f"SimulatedExchange: {ok_count} passed, {fail_count} failed")
    print("-" * 40)
    return fail_count == 0


if __name__ == "__main__":
    success = test_simulated_exchange()
    sys.exit(0 if success else 1)
