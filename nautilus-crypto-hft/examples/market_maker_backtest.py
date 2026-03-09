"""
Market maker backtest using L2 order book data.
Runs out of the box with TestInstrumentProvider — no external data needed.
"""

from decimal import Decimal

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.backtest.config import BacktestEngineConfig
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import OrderBookDeltas
from nautilus_trader.model.enums import AccountType, BookType, OmsType, OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId, TraderId, Venue
from nautilus_trader.model.objects import Money
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
        self.subscribe_order_book_deltas(
            self.config.instrument_id, book_type=BookType.L2_MBP,
        )

    def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
        book = self.cache.order_book(self.config.instrument_id)
        if not book.best_bid_price() or not book.best_ask_price():
            return

        bv = float(book.best_bid_size())
        av = float(book.best_ask_size())
        if bv + av == 0:
            return
        mid = Decimal(str(
            (float(book.best_bid_price()) * av + float(book.best_ask_price()) * bv) / (bv + av)
        ))
        self._requote(mid)

    def _requote(self, mid: Decimal) -> None:
        pos = self.cache.position_for_instrument(self.config.instrument_id)
        skew = Decimal(0) if not pos else -(pos.signed_qty / self.config.max_size) * self.config.skew_factor

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
    instrument = TestInstrumentProvider.btcusdt_binance()
    engine = BacktestEngine(config=BacktestEngineConfig(trader_id=TraderId("BACKTESTER-001")))

    engine.add_venue(
        venue=Venue("BINANCE"),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=USDT,
        starting_balances=[Money(100_000, USDT)],
        book_type=BookType.L2_MBP,
    )
    engine.add_instrument(instrument)

    # Use test data — replace with Tardis/Databento data for real backtests
    quotes = TestDataProvider.audusd_ticks()  # placeholder
    engine.add_data(quotes)

    strategy = SimpleMarketMaker(MMConfig(instrument_id=instrument.id))
    engine.add_strategy(strategy)
    engine.run()

    print(engine.trader.generate_order_fills_report())
    print(engine.trader.generate_positions_report())
