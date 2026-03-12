"""
Bracket order (entry + stop-loss + take-profit) backtest.
Runs out of the box with TestInstrumentProvider — no external data needed.
Uses order_factory.bracket() to create OTO-linked OrderList.
"""

from decimal import Decimal

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide
from nautilus_trader.model.identifiers import InstrumentId, TraderId, Venue
from nautilus_trader.model.objects import Currency, Money
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler
from nautilus_trader.test_kit.providers import TestDataProvider, TestInstrumentProvider
from nautilus_trader.trading.strategy import Strategy


class BracketConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    trade_size: Decimal = Decimal("0.01")
    tp_pct: Decimal = Decimal("0.02")   # 2% take-profit
    sl_pct: Decimal = Decimal("0.01")   # 1% stop-loss


class BracketStrategy(Strategy):
    def __init__(self, config: BracketConfig) -> None:
        super().__init__(config)
        self.instrument = None
        self._bracket_submitted = False

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        self.subscribe_trade_ticks(self.config.instrument_id)

    def on_trade_tick(self, tick: TradeTick) -> None:
        if self._bracket_submitted:
            return

        mid = float(tick.price)
        tp_price = self.instrument.make_price(Decimal(str(mid * (1 + float(self.config.tp_pct)))))
        sl_price = self.instrument.make_price(Decimal(str(mid * (1 - float(self.config.sl_pct)))))

        bracket = self.order_factory.bracket(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(self.config.trade_size),
            tp_price=tp_price,
            sl_trigger_price=sl_price,
            # Entry defaults to MARKET order
            # SL defaults to STOP_MARKET with DEFAULT trigger
            # TP defaults to LIMIT with post_only=True
            # Contingency: entry=OTO triggers children, SL/TP=OUO (linked)
        )
        self.submit_order_list(bracket)
        self._bracket_submitted = True

    def on_order_filled(self, event) -> None:
        order = self.cache.order(event.client_order_id)
        tags = order.tags if order else None
        print(f"  FILLED: {event.order_side.name} {event.last_qty} @ {event.last_px} tags={tags}")

    def on_order_canceled(self, event) -> None:
        order = self.cache.order(event.client_order_id)
        tags = order.tags if order else None
        print(f"  CANCELED: {event.client_order_id} tags={tags}")

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
        support_contingent_orders=True,  # required for bracket orders
    )
    engine.add_instrument(instrument)

    dp = TestDataProvider()
    df = dp.read_csv_ticks("binance/ethusdt-trades.csv")
    wrangler = TradeTickDataWrangler(instrument=instrument)
    ticks = wrangler.process(df)
    engine.add_data(ticks)

    strategy = BracketStrategy(BracketConfig(instrument_id=instrument.id))
    engine.add_strategy(strategy)
    engine.run()

    print(engine.trader.generate_order_fills_report())
    print(engine.trader.generate_positions_report())
