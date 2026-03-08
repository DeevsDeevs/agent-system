"""
Market maker strategy with L2 order book and inventory-based skew.

Demonstrates:
- OrderBook management (L2_MBP)
- Midpoint tracking and two-sided quote placement
- Inventory-based skew adjustment
- Cancel-all + re-quote pattern
- Position event handling
- BacktestEngine setup with L2 book type
"""

from decimal import Decimal

from nautilus_trader.backtest.engine import BacktestEngine
from nautilus_trader.config import BacktestEngineConfig, StrategyConfig
from nautilus_trader.model.book import OrderBook
from nautilus_trader.model.currencies import USDT
from nautilus_trader.model.data import OrderBookDeltas
from nautilus_trader.model.enums import (
    AccountType,
    BookType,
    OmsType,
    OrderSide,
    TimeInForce,
)
from nautilus_trader.model.identifiers import InstrumentId, TraderId, Venue
from nautilus_trader.model.objects import Money
from nautilus_trader.trading.strategy import Strategy


class MarketMakerConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    trade_size: Decimal
    max_size: Decimal = Decimal("10")
    spread: Decimal = Decimal("0.001")
    skew_factor: Decimal = Decimal("0.5")
    order_id_tag: str = "MM"


class MarketMaker(Strategy):
    def __init__(self, config: MarketMakerConfig) -> None:
        super().__init__(config)
        self.instrument = None
        self.book = None
        self._last_mid = None

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.log.error(f"Instrument not found: {self.config.instrument_id}")
            self.stop()
            return

        self.book = OrderBook(self.config.instrument_id, BookType.L2_MBP)
        self.subscribe_order_book_deltas(self.config.instrument_id)

    def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
        self.book.apply_deltas(deltas)

        best_bid = self.book.best_bid_price()
        best_ask = self.book.best_ask_price()
        if not best_bid or not best_ask:
            return

        mid = (best_bid + best_ask) / 2
        if mid != self._last_mid:
            self._last_mid = mid
            self._requote(mid)

    def _requote(self, mid: Decimal) -> None:
        self.cancel_all_orders(self.config.instrument_id)

        if not self._should_quote():
            return

        skew = self._inventory_skew()
        half_spread = self.config.spread / 2

        bid_price = mid * (1 - half_spread + skew)
        ask_price = mid * (1 + half_spread + skew)

        bid = self.order_factory.limit(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(self.config.trade_size),
            price=self.instrument.make_price(bid_price),
            time_in_force=TimeInForce.GTC,
            post_only=True,
        )
        ask = self.order_factory.limit(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.SELL,
            quantity=self.instrument.make_qty(self.config.trade_size),
            price=self.instrument.make_price(ask_price),
            time_in_force=TimeInForce.GTC,
            post_only=True,
        )
        self.submit_order(bid)
        self.submit_order(ask)

    def _inventory_skew(self) -> Decimal:
        """Shift quotes to discourage inventory accumulation."""
        position = self.cache.position_for_instrument(self.config.instrument_id)
        if position is None:
            return Decimal(0)
        signed_qty = position.signed_qty
        return -(signed_qty / self.config.max_size) * self.config.skew_factor

    def _should_quote(self) -> bool:
        """Stop quoting if inventory exceeds max size."""
        position = self.cache.position_for_instrument(self.config.instrument_id)
        if position and abs(position.signed_qty) >= float(self.config.max_size):
            return False
        return True

    def on_order_filled(self, event) -> None:
        self.log.info(f"Filled: {event.client_order_id} side={event.order_side} @ {event.last_px}")

    def on_position_changed(self, event) -> None:
        self.log.info(f"Position: {event.position.signed_qty}")

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
        account_type=AccountType.MARGIN,
        base_currency=USDT,
        starting_balances=[Money(100_000, USDT)],
        book_type=BookType.L2_MBP,
    )

    # Load your instrument and L2 OrderBookDelta data here:
    # engine.add_instrument(instrument)
    # engine.add_data(deltas)  # list[OrderBookDelta] with F_LAST flags

    strategy_config = MarketMakerConfig(
        instrument_id=InstrumentId.from_str("BTCUSDT-PERP.SIM"),
        trade_size=Decimal("0.01"),
        max_size=Decimal("0.5"),
        spread=Decimal("0.0005"),
        skew_factor=Decimal("0.5"),
    )

    strategy = MarketMaker(config=strategy_config)
    engine.add_strategy(strategy)
    engine.run()

    print(engine.trader.generate_order_fills_report())
    print(engine.trader.generate_positions_report())
    print(engine.trader.generate_account_report(SIM))

    engine.dispose()


if __name__ == "__main__":
    run_backtest()
