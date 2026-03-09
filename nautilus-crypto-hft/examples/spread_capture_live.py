"""
Live spread capture market maker on Binance USDT-M futures.
Structurally complete — needs only API keys in environment variables.
"""

import os
from decimal import Decimal

from nautilus_trader.adapters.binance.common.enums import BinanceAccountType
from nautilus_trader.adapters.binance.config import BinanceDataClientConfig, BinanceExecClientConfig
from nautilus_trader.adapters.binance.factories import (
    BinanceLiveDataClientFactory,
    BinanceLiveExecClientFactory,
)
from nautilus_trader.config import (
    CacheConfig,
    DatabaseConfig,
    LiveExecEngineConfig,
    LoggingConfig,
    StrategyConfig,
    TradingNodeConfig,
)
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.data import OrderBookDeltas
from nautilus_trader.model.enums import BookType, OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy


class SpreadCaptureConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    trade_size: Decimal = Decimal("0.01")
    max_size: Decimal = Decimal("0.05")
    half_spread: Decimal = Decimal("0.0004")  # 4 bps each side
    skew_factor: Decimal = Decimal("0.6")


class SpreadCapture(Strategy):
    def __init__(self, config: SpreadCaptureConfig) -> None:
        super().__init__(config)
        self.instrument = None
        self._bid_id = None
        self._ask_id = None

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.log.error(f"Instrument not found: {self.config.instrument_id}")
            self.stop()
            return
        self.subscribe_order_book_deltas(
            self.config.instrument_id, book_type=BookType.L2_MBP,
        )

    def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
        book = self.cache.order_book(self.config.instrument_id)
        if not book.best_bid_price() or not book.best_ask_price():
            return

        bv, av = float(book.best_bid_size()), float(book.best_ask_size())
        if bv + av == 0:
            return
        mid = Decimal(str(
            (float(book.best_bid_price()) * av + float(book.best_ask_price()) * bv) / (bv + av)
        ))

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


def main():
    config = TradingNodeConfig(
        trader_id="SPREAD-001",
        logging=LoggingConfig(log_level="INFO", log_level_file="DEBUG", log_file_path="logs/"),
        exec_engine=LiveExecEngineConfig(reconciliation=True, reconciliation_lookback_mins=1440),
        data_clients={
            "BINANCE": BinanceDataClientConfig(
                api_key=os.environ["BINANCE_API_KEY"],
                api_secret=os.environ["BINANCE_API_SECRET"],
                account_type=BinanceAccountType.USDT_FUTURE,
            ),
        },
        exec_clients={
            "BINANCE": BinanceExecClientConfig(
                api_key=os.environ["BINANCE_API_KEY"],
                api_secret=os.environ["BINANCE_API_SECRET"],
                account_type=BinanceAccountType.USDT_FUTURE,
            ),
        },
    )

    node = TradingNode(config=config)
    node.add_data_client_factory("BINANCE", BinanceLiveDataClientFactory)
    node.add_exec_client_factory("BINANCE", BinanceLiveExecClientFactory)

    strategy = SpreadCapture(SpreadCaptureConfig(
        instrument_id=InstrumentId.from_str("BTCUSDT-PERP.BINANCE"),
    ))
    node.trader.add_strategy(strategy)
    node.build()

    try:
        node.run()
    except KeyboardInterrupt:
        node.stop()


if __name__ == "__main__":
    main()
