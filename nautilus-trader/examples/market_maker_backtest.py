"""
Market maker backtest using trade tick data as price source.
Runs out of the box with TestInstrumentProvider — no external data needed.

For L2-based MM (preferred for production), load OrderBookDelta data
from Tardis/Databento and use subscribe_order_book_deltas() instead.
"""

from decimal import Decimal

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import TradeTick
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId, TraderId, Venue
from nautilus_trader.model.objects import Currency, Money
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler
from nautilus_trader.test_kit.providers import TestDataProvider, TestInstrumentProvider
from nautilus_trader.trading.strategy import Strategy


class MMConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    trade_size: Decimal = Decimal("0.01")
    max_size: Decimal = Decimal("0.1")
    half_spread: Decimal = Decimal("0.0005")
    skew_factor: Decimal = Decimal("0.5")


class SimpleMarketMaker(Strategy):
    def __init__(self, config: MMConfig) -> None:
        super().__init__(config)
        self.instrument = None
        self._bid_id = None
        self._ask_id = None

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        self.subscribe_trade_ticks(self.config.instrument_id)

    def on_trade_tick(self, tick: TradeTick) -> None:
        mid = Decimal(str(tick.price))
        self._requote(mid)

    def _requote(self, mid: Decimal) -> None:
        positions = self.cache.positions_open(instrument_id=self.config.instrument_id)
        pos = positions[0] if positions else None
        skew = Decimal(0) if not pos else -(Decimal(str(pos.signed_qty)) / self.config.max_size) * self.config.skew_factor

        bid_px = self.instrument.make_price(mid * (1 - self.config.half_spread + skew))
        ask_px = self.instrument.make_price(mid * (1 + self.config.half_spread + skew))
        qty = self.instrument.make_qty(self.config.trade_size)

        bid_order = self.cache.order(self._bid_id) if self._bid_id else None
        if bid_order and bid_order.is_open:
            self.modify_order(bid_order, quantity=qty, price=bid_px)
        else:
            bid = self.order_factory.limit(
                instrument_id=self.config.instrument_id,
                order_side=OrderSide.BUY, quantity=qty, price=bid_px,
                time_in_force=TimeInForce.GTC, post_only=True,
            )
            self.submit_order(bid)
            self._bid_id = bid.client_order_id

        ask_order = self.cache.order(self._ask_id) if self._ask_id else None
        if ask_order and ask_order.is_open:
            self.modify_order(ask_order, quantity=qty, price=ask_px)
        else:
            ask = self.order_factory.limit(
                instrument_id=self.config.instrument_id,
                order_side=OrderSide.SELL, quantity=qty, price=ask_px,
                time_in_force=TimeInForce.GTC, post_only=True,
            )
            self.submit_order(ask)
            self._ask_id = ask.client_order_id

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

    strategy = SimpleMarketMaker(MMConfig(instrument_id=instrument.id))
    engine.add_strategy(strategy)
    engine.run()

    print(f"Total orders: {len(engine.cache.orders())}")
    print(f"Total closed: {len(engine.cache.orders_closed())}")
    print(f"Total positions: {len(engine.cache.positions())}")
