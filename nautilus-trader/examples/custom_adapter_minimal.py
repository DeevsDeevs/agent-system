"""
Minimal combined data+exec adapter skeleton.
Shows the essential methods without 30+ no-op stubs.
Replace MyExchangeHttpClient/WebSocketClient with your venue's API.
"""

import msgspec
from nautilus_trader.core.datetime import millis_to_nanos
from nautilus_trader.live.data_client import LiveMarketDataClient
from nautilus_trader.live.execution_client import LiveExecutionClient
from nautilus_trader.live.factories import LiveDataClientFactory, LiveExecClientFactory
from nautilus_trader.model.data import BookOrder, OrderBookDelta, TradeTick
from nautilus_trader.model.enums import (
    AccountType, AggressorSide, BookAction,
    OmsType, OrderSide, RecordFlag,
)
from nautilus_trader.model.identifiers import ClientId, TradeId, Venue, VenueOrderId
from nautilus_trader.model.objects import Money, Price, Quantity


class MyExchangeConfig(msgspec.Struct, frozen=True):
    api_key: str = ""
    api_secret: str = ""
    ws_url: str = "wss://stream.example.com/v1/public"
    testnet: bool = False


class MyExchangeDataClient(LiveMarketDataClient):
    def __init__(self, loop, client_id, venue, msgbus, cache, clock, config):
        super().__init__(loop=loop, client_id=client_id, venue=venue,
                         msgbus=msgbus, cache=cache, clock=clock)
        self._config = config
        self._subscriptions: set[str] = set()

    async def _connect(self) -> None:
        pass  # Initialize HTTP + WS clients, authenticate

    async def _disconnect(self) -> None:
        self._subscriptions.clear()

    async def _subscribe_order_book_deltas(self, command) -> None:
        channel = f"orderbook.{command.instrument_id.symbol.value}"
        self._subscriptions.add(channel)

    async def _subscribe_trade_ticks(self, command) -> None:
        channel = f"trades.{command.instrument_id.symbol.value}"
        self._subscriptions.add(channel)

    def _on_book_message(self, instrument_id, updates: list[dict]) -> None:
        for i, u in enumerate(updates):
            size = Quantity.from_str(u["size"])
            delta = OrderBookDelta(
                instrument_id=instrument_id,
                action=BookAction.DELETE if size.raw == 0 else BookAction.UPDATE,
                order=BookOrder(
                    side=OrderSide.BUY if u["side"] == "Buy" else OrderSide.SELL,
                    price=Price.from_str(u["price"]),
                    size=size,
                    order_id=0,
                ),
                flags=RecordFlag.F_LAST if i == len(updates) - 1 else 0,
                sequence=u.get("seq", 0),
                ts_event=millis_to_nanos(u["ts"]),
                ts_init=self._clock.timestamp_ns(),
            )
            self._handle_data(delta)

    def _on_trade_message(self, instrument_id, msg: dict) -> None:
        trade = TradeTick(
            instrument_id=instrument_id,
            price=Price.from_str(msg["price"]),
            size=Quantity.from_str(msg["size"]),
            aggressor_side=AggressorSide.BUYER if msg["side"] == "Buy" else AggressorSide.SELLER,
            trade_id=TradeId(msg["id"]),
            ts_event=millis_to_nanos(msg["ts"]),
            ts_init=self._clock.timestamp_ns(),
        )
        self._handle_data(trade)


class MyExchangeExecClient(LiveExecutionClient):
    def __init__(self, loop, client_id, venue, msgbus, cache, clock, config):
        super().__init__(loop=loop, client_id=client_id, venue=venue,
                         oms_type=OmsType.NETTING, account_type=AccountType.MARGIN,
                         base_currency=None, msgbus=msgbus, cache=cache, clock=clock)
        self._config = config

    async def _connect(self) -> None:
        pass  # Initialize HTTP + private WS, subscribe execution stream

    async def _disconnect(self) -> None:
        pass

    async def _submit_order(self, command) -> None:
        order = command.order
        try:
            # response = await self._http.place_order(...)
            venue_order_id = "VENUE-123"  # from response
            self.generate_order_accepted(
                strategy_id=order.strategy_id, instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                venue_order_id=VenueOrderId(venue_order_id),
                ts_event=self._clock.timestamp_ns(),
            )
        except Exception as e:
            self.generate_order_rejected(
                strategy_id=order.strategy_id, instrument_id=order.instrument_id,
                client_order_id=order.client_order_id, reason=str(e),
                ts_event=self._clock.timestamp_ns(),
            )

    async def _cancel_order(self, command) -> None:
        pass  # await self._http.cancel_order(command.venue_order_id.value)

    async def _modify_order(self, command) -> None:
        pass  # await self._http.amend_order(...)


class MyDataFactory(LiveDataClientFactory):
    @staticmethod
    def create(loop, name, config, msgbus, cache, clock):
        return MyExchangeDataClient(
            loop=loop, client_id=ClientId(name), venue=Venue(name),
            msgbus=msgbus, cache=cache, clock=clock, config=config,
        )


class MyExecFactory(LiveExecClientFactory):
    @staticmethod
    def create(loop, name, config, msgbus, cache, clock):
        return MyExchangeExecClient(
            loop=loop, client_id=ClientId(name), venue=Venue(name),
            msgbus=msgbus, cache=cache, clock=clock, config=config,
        )
