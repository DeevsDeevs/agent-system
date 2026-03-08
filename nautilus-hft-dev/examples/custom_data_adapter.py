"""
Complete LiveMarketDataClient for a hypothetical crypto exchange.

Demonstrates:
- WebSocket connection with reconnection
- Order book delta processing with RecordFlag.F_LAST
- Trade tick and quote tick parsing
- Snapshot-to-delta conversion
- Sequence gap detection
- Subscription management
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from nautilus_trader.core.datetime import millis_to_nanos
from nautilus_trader.data.messages import (
    RequestBars,
    RequestData,
    RequestInstrument,
    RequestInstruments,
    RequestOrderBookDeltas,
    RequestOrderBookDepth,
    RequestOrderBookSnapshot,
    RequestQuoteTicks,
    RequestTradeTicks,
    SubscribeBars,
    SubscribeData,
    SubscribeFundingRates,
    SubscribeIndexPrices,
    SubscribeInstrument,
    SubscribeInstrumentClose,
    SubscribeInstruments,
    SubscribeInstrumentStatus,
    SubscribeMarkPrices,
    SubscribeOrderBook,
    SubscribeQuoteTicks,
    SubscribeTradeTicks,
    UnsubscribeBars,
    UnsubscribeData,
    UnsubscribeFundingRates,
    UnsubscribeIndexPrices,
    UnsubscribeInstrument,
    UnsubscribeInstrumentClose,
    UnsubscribeInstruments,
    UnsubscribeInstrumentStatus,
    UnsubscribeMarkPrices,
    UnsubscribeOrderBook,
    UnsubscribeQuoteTicks,
    UnsubscribeTradeTicks,
)
from nautilus_trader.live.data_client import LiveMarketDataClient
from nautilus_trader.model.data import BookOrder, OrderBookDelta, QuoteTick, TradeTick
from nautilus_trader.model.enums import (
    AggressorSide,
    BookAction,
    OrderSide,
    RecordFlag,
)
from nautilus_trader.model.identifiers import InstrumentId, Symbol, TradeId, Venue
from nautilus_trader.model.objects import Price, Quantity


class CryptoExchangeDataClient(LiveMarketDataClient):
    """
    Live market data client for a hypothetical crypto exchange.

    Handles order book deltas, trades, and quotes via WebSocket,
    with REST fallback for snapshots and historical data.
    """

    VENUE = Venue("CRYPTOEX")

    def __init__(self, loop, client_id, venue, msgbus, cache, clock, config):
        super().__init__(
            loop=loop,
            client_id=client_id,
            venue=venue,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
        )
        self._config = config
        self._ws = None
        self._subscriptions: set[str] = set()
        self._last_sequence: dict[InstrumentId, int] = {}

    # ── Connection lifecycle ──────────────────────────────────────

    async def _connect(self) -> None:
        self._ws = await self._create_ws_connection()
        self._log.info("Connected to CryptoExchange WebSocket")

    async def _disconnect(self) -> None:
        if self._ws:
            await self._ws.close()
        self._subscriptions.clear()
        self._last_sequence.clear()
        self._log.info("Disconnected from CryptoExchange WebSocket")

    async def _create_ws_connection(self):
        """Create WebSocket connection with message routing."""
        # In production, use the Rust WebSocketClient for performance:
        #   from nautilus_trader.network import WebSocketClient
        #   return WebSocketClient(url=..., handler=self._handle_ws_message)
        pass

    async def _on_reconnect(self) -> None:
        """Re-subscribe to all channels after reconnection."""
        self._log.info("Reconnecting — re-subscribing to all channels")
        for channel in list(self._subscriptions):
            await self._ws_subscribe(channel)
        # Request fresh snapshots for all subscribed order books
        for iid in list(self._last_sequence.keys()):
            await self._resync_book(iid)

    # ── WebSocket message routing ─────────────────────────────────

    def _handle_ws_message(self, raw: bytes) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            self._log.error(f"Failed to parse WS message: {raw[:100]}")
            return

        topic = msg.get("topic", "")
        if "orderbook" in topic:
            self._process_order_book_update(msg)
        elif "trade" in topic:
            self._process_trades(msg)
        elif "ticker" in topic:
            self._process_quote(msg)
        elif msg.get("op") == "pong":
            pass  # heartbeat response

    # ── Order Book Processing ─────────────────────────────────────

    def _process_order_book_update(self, msg: dict) -> None:
        data = msg["data"]
        symbol = data["s"]
        instrument_id = InstrumentId(Symbol(symbol), self.VENUE)

        # Sequence gap detection
        sequence = data["u"]
        last_seq = self._last_sequence.get(instrument_id)
        if last_seq is not None and sequence != last_seq + 1:
            self._log.warning(
                f"Sequence gap for {instrument_id}: "
                f"expected {last_seq + 1}, got {sequence}"
            )
            asyncio.ensure_future(self._resync_book(instrument_id))
            return
        self._last_sequence[instrument_id] = sequence

        ts_event = millis_to_nanos(data["T"])
        ts_init = self._clock.timestamp_ns()

        bids = data.get("b", [])
        asks = data.get("a", [])
        total = len(bids) + len(asks)

        if total == 0:
            return

        # Process all deltas with F_LAST on the final one
        for i, (price_str, size_str) in enumerate(bids):
            is_last = len(asks) == 0 and i == len(bids) - 1
            self._emit_delta(
                instrument_id=instrument_id,
                side=OrderSide.BUY,
                price_str=price_str,
                size_str=size_str,
                flags=RecordFlag.F_LAST if is_last else 0,
                sequence=sequence,
                ts_event=ts_event,
                ts_init=ts_init,
            )

        for i, (price_str, size_str) in enumerate(asks):
            is_last = i == len(asks) - 1
            self._emit_delta(
                instrument_id=instrument_id,
                side=OrderSide.SELL,
                price_str=price_str,
                size_str=size_str,
                flags=RecordFlag.F_LAST if is_last else 0,
                sequence=sequence,
                ts_event=ts_event,
                ts_init=ts_init,
            )

    def _emit_delta(
        self,
        instrument_id: InstrumentId,
        side: OrderSide,
        price_str: str,
        size_str: str,
        flags: int,
        sequence: int,
        ts_event: int,
        ts_init: int,
    ) -> None:
        size = Quantity.from_str(size_str)
        action = BookAction.DELETE if size.raw == 0 else BookAction.UPDATE

        delta = OrderBookDelta(
            instrument_id=instrument_id,
            action=action,
            order=BookOrder(
                price=Price.from_str(price_str),
                size=size,
                side=side,
            ),
            flags=flags,
            sequence=sequence,
            ts_event=ts_event,
            ts_init=ts_init,
        )
        self._handle_data(delta)

    async def _resync_book(self, instrument_id: InstrumentId) -> None:
        """Request fresh snapshot and re-establish incremental feed."""
        self._log.info(f"Resyncing order book for {instrument_id}")
        # 1. Clear the book
        clear_delta = OrderBookDelta(
            instrument_id=instrument_id,
            action=BookAction.CLEAR,
            order=None,
            flags=0,
            sequence=0,
            ts_event=self._clock.timestamp_ns(),
            ts_init=self._clock.timestamp_ns(),
        )
        self._handle_data(clear_delta)

        # 2. Fetch snapshot via REST
        # snapshot = await self._http_client.get_order_book(instrument_id.symbol.value)
        # 3. Apply snapshot as ADD deltas with F_LAST on last
        # 4. Update self._last_sequence[instrument_id] = snapshot["lastUpdateId"]

    # ── Trade Processing ──────────────────────────────────────────

    def _process_trades(self, msg: dict) -> None:
        data_list = msg.get("data", [])
        for data in data_list:
            symbol = data["s"]
            instrument_id = InstrumentId(Symbol(symbol), self.VENUE)

            trade = TradeTick(
                instrument_id=instrument_id,
                price=Price.from_str(data["p"]),
                size=Quantity.from_str(data["v"]),
                aggressor_side=(
                    AggressorSide.SELLER if data["S"] == "Sell" else AggressorSide.BUYER
                ),
                trade_id=TradeId(data["i"]),
                ts_event=millis_to_nanos(data["T"]),
                ts_init=self._clock.timestamp_ns(),
            )
            self._handle_data(trade)

    # ── Quote Processing ──────────────────────────────────────────

    def _process_quote(self, msg: dict) -> None:
        data = msg["data"]
        symbol = data["s"]
        instrument_id = InstrumentId(Symbol(symbol), self.VENUE)

        quote = QuoteTick(
            instrument_id=instrument_id,
            bid_price=Price.from_str(data["b"]),
            ask_price=Price.from_str(data["a"]),
            bid_size=Quantity.from_str(data["B"]),
            ask_size=Quantity.from_str(data["A"]),
            ts_event=millis_to_nanos(data["T"]),
            ts_init=self._clock.timestamp_ns(),
        )
        self._handle_data(quote)

    # ── Subscription Methods ──────────────────────────────────────

    async def _ws_subscribe(self, channel: str) -> None:
        """Send subscription message to WebSocket."""
        msg = json.dumps({"op": "subscribe", "args": [channel]})
        if self._ws:
            await self._ws.send(msg)

    async def _ws_unsubscribe(self, channel: str) -> None:
        """Send unsubscription message to WebSocket."""
        msg = json.dumps({"op": "unsubscribe", "args": [channel]})
        if self._ws:
            await self._ws.send(msg)

    async def _subscribe_order_book_deltas(self, command: SubscribeOrderBook) -> None:
        symbol = command.instrument_id.symbol.value
        channel = f"orderbook.50.{symbol}"
        self._subscriptions.add(channel)
        await self._ws_subscribe(channel)

    async def _unsubscribe_order_book_deltas(self, command: UnsubscribeOrderBook) -> None:
        symbol = command.instrument_id.symbol.value
        channel = f"orderbook.50.{symbol}"
        self._subscriptions.discard(channel)
        await self._ws_unsubscribe(channel)

    async def _subscribe_trade_ticks(self, command: SubscribeTradeTicks) -> None:
        symbol = command.instrument_id.symbol.value
        channel = f"publicTrade.{symbol}"
        self._subscriptions.add(channel)
        await self._ws_subscribe(channel)

    async def _unsubscribe_trade_ticks(self, command: UnsubscribeTradeTicks) -> None:
        symbol = command.instrument_id.symbol.value
        channel = f"publicTrade.{symbol}"
        self._subscriptions.discard(channel)
        await self._ws_unsubscribe(channel)

    async def _subscribe_quote_ticks(self, command: SubscribeQuoteTicks) -> None:
        symbol = command.instrument_id.symbol.value
        channel = f"tickers.{symbol}"
        self._subscriptions.add(channel)
        await self._ws_subscribe(channel)

    async def _unsubscribe_quote_ticks(self, command: UnsubscribeQuoteTicks) -> None:
        symbol = command.instrument_id.symbol.value
        channel = f"tickers.{symbol}"
        self._subscriptions.discard(channel)
        await self._ws_unsubscribe(channel)

    # ── Remaining required overrides (no-ops for this example) ────

    async def _subscribe_bars(self, command: SubscribeBars) -> None:
        pass

    async def _unsubscribe_bars(self, command: UnsubscribeBars) -> None:
        pass

    async def _subscribe_mark_prices(self, command: SubscribeMarkPrices) -> None:
        pass

    async def _unsubscribe_mark_prices(self, command: UnsubscribeMarkPrices) -> None:
        pass

    async def _subscribe_funding_rates(self, command: SubscribeFundingRates) -> None:
        pass

    async def _unsubscribe_funding_rates(self, command: UnsubscribeFundingRates) -> None:
        pass

    async def _subscribe_instrument(self, command: SubscribeInstrument) -> None:
        pass

    async def _unsubscribe_instrument(self, command: UnsubscribeInstrument) -> None:
        pass

    async def _subscribe_instruments(self, command: SubscribeInstruments) -> None:
        pass

    async def _unsubscribe_instruments(self, command: UnsubscribeInstruments) -> None:
        pass

    async def _subscribe_instrument_status(self, command: SubscribeInstrumentStatus) -> None:
        pass

    async def _unsubscribe_instrument_status(self, command: UnsubscribeInstrumentStatus) -> None:
        pass

    async def _subscribe_instrument_close(self, command: SubscribeInstrumentClose) -> None:
        pass

    async def _unsubscribe_instrument_close(self, command: UnsubscribeInstrumentClose) -> None:
        pass

    async def _subscribe_index_prices(self, command: SubscribeIndexPrices) -> None:
        pass

    async def _unsubscribe_index_prices(self, command: UnsubscribeIndexPrices) -> None:
        pass

    async def _subscribe(self, command: SubscribeData) -> None:
        pass

    async def _unsubscribe(self, command: UnsubscribeData) -> None:
        pass

    async def _request_order_book_snapshot(self, command: RequestOrderBookSnapshot) -> None:
        pass

    async def _request_trade_ticks(self, command: RequestTradeTicks) -> None:
        pass

    async def _request_bars(self, command: RequestBars) -> None:
        pass

    async def _request_instrument(self, command: RequestInstrument) -> None:
        pass

    async def _request_instruments(self, command: RequestInstruments) -> None:
        pass

    async def _request_quote_ticks(self, command: RequestQuoteTicks) -> None:
        pass

    async def _request(self, command: RequestData) -> None:
        pass

    async def _request_order_book_deltas(self, command: RequestOrderBookDeltas) -> None:
        pass

    async def _request_order_book_depth(self, command: RequestOrderBookDepth) -> None:
        pass
