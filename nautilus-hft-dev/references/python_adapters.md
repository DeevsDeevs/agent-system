# Python Adapter Development

Complete guide to building custom NautilusTrader adapters in Python.

## Adapter Components

Every adapter has up to 5 components:

| Component | Base Class | Purpose |
|-----------|-----------|---------|
| InstrumentProvider | `InstrumentProvider` | Load/parse venue instruments |
| Data Client | `LiveMarketDataClient` | Market data subscriptions |
| General Data Client | `LiveDataClient` | Non-market data (news, custom) |
| Execution Client | `LiveExecutionClient` | Order management |
| Config | `msgspec.Struct` | Configuration classes |

## InstrumentProvider

Loads instrument definitions from venue API and converts to Nautilus `Instrument` types.

```python
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.model.instruments import CryptoPerpetual, CurrencyPair

class MyExchangeInstrumentProvider(InstrumentProvider):
    def __init__(self, http_client, clock, config=None):
        super().__init__(config=config)
        self._http_client = http_client
        self._clock = clock

    async def load_all_async(self, filters=None) -> None:
        raw_instruments = await self._http_client.get_instruments()
        for raw in raw_instruments:
            instrument = self._parse_instrument(raw)
            self._add_instrument(instrument)

    async def load_ids_async(self, instrument_ids, filters=None) -> None:
        for iid in instrument_ids:
            raw = await self._http_client.get_instrument(iid.symbol.value)
            instrument = self._parse_instrument(raw)
            self._add_instrument(instrument)

    def _parse_instrument(self, raw: dict) -> CryptoPerpetual:
        return CryptoPerpetual(
            instrument_id=InstrumentId(Symbol(raw["symbol"]), Venue("MYEXCH")),
            raw_symbol=Symbol(raw["symbol"]),
            base_currency=Currency.from_str(raw["baseCurrency"]),
            quote_currency=Currency.from_str(raw["quoteCurrency"]),
            settlement_currency=Currency.from_str(raw["settleCurrency"]),
            is_inverse=raw.get("isInverse", False),
            price_precision=raw["pricePrecision"],
            size_precision=raw["sizePrecision"],
            price_increment=Price.from_str(raw["tickSize"]),
            size_increment=Quantity.from_str(raw["lotSize"]),
            max_quantity=Quantity.from_str(raw["maxOrderQty"]),
            min_quantity=Quantity.from_str(raw["minOrderQty"]),
            max_notional=Money.from_str(f"{raw['maxNotional']} {raw['quoteCurrency']}"),
            min_notional=Money.from_str(f"{raw['minNotional']} {raw['quoteCurrency']}"),
            max_price=Price.from_str(raw["maxPrice"]),
            min_price=Price.from_str(raw["minPrice"]),
            margin_init=Decimal(str(raw["initialMargin"])),
            margin_maint=Decimal(str(raw["maintenanceMargin"])),
            maker_fee=Decimal(str(raw["makerFee"])),
            taker_fee=Decimal(str(raw["takerFee"])),
            ts_event=self._clock.timestamp_ns(),
            ts_init=self._clock.timestamp_ns(),
        )
```

### InstrumentProvider Config

```python
from nautilus_trader.config import InstrumentProviderConfig

# Load everything on startup
config = InstrumentProviderConfig(load_all=True)

# Load specific instruments only
config = InstrumentProviderConfig(
    load_ids=["BTCUSDT-PERP.MYEXCH", "ETHUSDT-PERP.MYEXCH"],
)
```

## LiveMarketDataClient — Full Template

```python
from nautilus_trader.live.data_client import LiveMarketDataClient
from nautilus_trader.data.messages import (
    RequestBars, RequestData, RequestInstrument, RequestInstruments,
    RequestOrderBookDeltas, RequestOrderBookDepth, RequestOrderBookSnapshot,
    RequestQuoteTicks, RequestTradeTicks,
    SubscribeBars, SubscribeData, SubscribeFundingRates, SubscribeIndexPrices,
    SubscribeInstrument, SubscribeInstrumentClose, SubscribeInstruments,
    SubscribeInstrumentStatus, SubscribeMarkPrices, SubscribeOrderBook,
    SubscribeQuoteTicks, SubscribeTradeTicks,
    UnsubscribeBars, UnsubscribeData, UnsubscribeFundingRates,
    UnsubscribeIndexPrices, UnsubscribeInstrument, UnsubscribeInstrumentClose,
    UnsubscribeInstruments, UnsubscribeInstrumentStatus, UnsubscribeMarkPrices,
    UnsubscribeOrderBook, UnsubscribeQuoteTicks, UnsubscribeTradeTicks,
)


class MyExchangeLiveDataClient(LiveMarketDataClient):
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
        self._ws_client = None  # Your WS client
        self._http_client = None  # Your HTTP client
        self._subscriptions: set[str] = set()

    # ── Connection lifecycle ──────────────────────────────────

    async def _connect(self) -> None:
        self._http_client = MyExchangeHttpClient(self._config)
        self._ws_client = MyExchangeWebSocketClient(
            url=self._config.ws_url,
            handler=self._handle_ws_message,
            on_reconnect=self._on_reconnect,
        )
        await self._ws_client.connect()

    async def _disconnect(self) -> None:
        await self._ws_client.disconnect()
        self._subscriptions.clear()

    async def _on_reconnect(self) -> None:
        # Re-subscribe to all active subscriptions after reconnection
        for sub in self._subscriptions:
            await self._ws_client.subscribe(sub)

    # ── Subscription methods (market data) ────────────────────

    async def _subscribe_order_book_deltas(self, command: SubscribeOrderBook) -> None:
        symbol = command.instrument_id.symbol.value
        channel = f"orderbook.{symbol}"
        self._subscriptions.add(channel)
        await self._ws_client.subscribe(channel)

    async def _unsubscribe_order_book_deltas(self, command: UnsubscribeOrderBook) -> None:
        symbol = command.instrument_id.symbol.value
        channel = f"orderbook.{symbol}"
        self._subscriptions.discard(channel)
        await self._ws_client.unsubscribe(channel)

    async def _subscribe_trade_ticks(self, command: SubscribeTradeTicks) -> None:
        symbol = command.instrument_id.symbol.value
        channel = f"trades.{symbol}"
        self._subscriptions.add(channel)
        await self._ws_client.subscribe(channel)

    async def _unsubscribe_trade_ticks(self, command: UnsubscribeTradeTicks) -> None:
        symbol = command.instrument_id.symbol.value
        channel = f"trades.{symbol}"
        self._subscriptions.discard(channel)
        await self._ws_client.unsubscribe(channel)

    async def _subscribe_quote_ticks(self, command: SubscribeQuoteTicks) -> None:
        symbol = command.instrument_id.symbol.value
        channel = f"ticker.{symbol}"
        self._subscriptions.add(channel)
        await self._ws_client.subscribe(channel)

    async def _unsubscribe_quote_ticks(self, command: UnsubscribeQuoteTicks) -> None:
        symbol = command.instrument_id.symbol.value
        channel = f"ticker.{symbol}"
        self._subscriptions.discard(channel)
        await self._ws_client.unsubscribe(channel)

    async def _subscribe_bars(self, command: SubscribeBars) -> None:
        # Only for EXTERNAL bars from venue API
        symbol = command.bar_type.instrument_id.symbol.value
        interval = self._map_bar_interval(command.bar_type)
        channel = f"kline.{interval}.{symbol}"
        self._subscriptions.add(channel)
        await self._ws_client.subscribe(channel)

    async def _unsubscribe_bars(self, command: UnsubscribeBars) -> None:
        symbol = command.bar_type.instrument_id.symbol.value
        interval = self._map_bar_interval(command.bar_type)
        channel = f"kline.{interval}.{symbol}"
        self._subscriptions.discard(channel)
        await self._ws_client.unsubscribe(channel)

    async def _subscribe_mark_prices(self, command: SubscribeMarkPrices) -> None:
        symbol = command.instrument_id.symbol.value
        channel = f"markPrice.{symbol}"
        self._subscriptions.add(channel)
        await self._ws_client.subscribe(channel)

    async def _unsubscribe_mark_prices(self, command: UnsubscribeMarkPrices) -> None:
        symbol = command.instrument_id.symbol.value
        channel = f"markPrice.{symbol}"
        self._subscriptions.discard(channel)
        await self._ws_client.unsubscribe(channel)

    async def _subscribe_funding_rates(self, command: SubscribeFundingRates) -> None:
        symbol = command.instrument_id.symbol.value
        channel = f"funding.{symbol}"
        self._subscriptions.add(channel)
        await self._ws_client.subscribe(channel)

    async def _unsubscribe_funding_rates(self, command: UnsubscribeFundingRates) -> None:
        symbol = command.instrument_id.symbol.value
        channel = f"funding.{symbol}"
        self._subscriptions.discard(channel)
        await self._ws_client.unsubscribe(channel)

    async def _subscribe_instrument(self, command: SubscribeInstrument) -> None:
        pass  # Usually a no-op; instruments loaded via InstrumentProvider

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
        pass  # Generic custom data subscription

    async def _unsubscribe(self, command: UnsubscribeData) -> None:
        pass

    # ── Request methods (historical / snapshot) ───────────────

    async def _request_order_book_snapshot(self, request: RequestOrderBookSnapshot) -> None:
        symbol = request.instrument_id.symbol.value
        raw = await self._http_client.get_order_book(symbol, depth=request.depth)
        # Parse raw into OrderBookDeltas and handle via self._handle_data
        deltas = self._parse_snapshot_to_deltas(request.instrument_id, raw)
        self._handle_order_book_deltas(deltas)

    async def _request_trade_ticks(self, request: RequestTradeTicks) -> None:
        symbol = request.instrument_id.symbol.value
        raw = await self._http_client.get_recent_trades(symbol)
        ticks = [self._parse_trade(request.instrument_id, t) for t in raw]
        self._handle_trade_ticks(request.instrument_id, ticks)

    async def _request_bars(self, request: RequestBars) -> None:
        symbol = request.bar_type.instrument_id.symbol.value
        interval = self._map_bar_interval(request.bar_type)
        raw = await self._http_client.get_klines(symbol, interval)
        bars = [self._parse_bar(request.bar_type, k) for k in raw]
        self._handle_bars(request.bar_type, bars)

    async def _request_instrument(self, request: RequestInstrument) -> None:
        pass

    async def _request_instruments(self, request: RequestInstruments) -> None:
        pass

    async def _request_quote_ticks(self, request: RequestQuoteTicks) -> None:
        pass

    async def _request(self, request: RequestData) -> None:
        pass

    async def _request_order_book_deltas(self, request: RequestOrderBookDeltas) -> None:
        pass

    async def _request_order_book_depth(self, request: RequestOrderBookDepth) -> None:
        pass

    # ── WebSocket message handler ─────────────────────────────

    def _handle_ws_message(self, raw: bytes) -> None:
        msg = self._parse_ws_message(raw)
        channel = msg.get("channel", "")

        if channel.startswith("orderbook."):
            self._process_order_book_update(msg)
        elif channel.startswith("trades."):
            self._process_trade(msg)
        elif channel.startswith("ticker."):
            self._process_quote(msg)
        elif channel.startswith("kline."):
            self._process_bar(msg)

    def _process_order_book_update(self, msg: dict) -> None:
        instrument_id = self._get_instrument_id(msg["symbol"])
        updates = msg["data"]
        deltas = []
        for i, update in enumerate(updates):
            flags = RecordFlag.F_LAST if i == len(updates) - 1 else 0
            delta = OrderBookDelta(
                instrument_id=instrument_id,
                action=self._map_action(update["type"]),
                order=BookOrder(
                    price=Price.from_str(update["price"]),
                    size=Quantity.from_str(update["size"]),
                    side=OrderSide.BUY if update["side"] == "Buy" else OrderSide.SELL,
                ),
                flags=flags,
                sequence=msg.get("sequence", 0),
                ts_event=millis_to_nanos(msg["timestamp"]),
                ts_init=self._clock.timestamp_ns(),
            )
            deltas.append(delta)
        # Publish each delta - DataEngine handles buffering via F_LAST flag
        for delta in deltas:
            self._handle_data(delta)

    def _process_trade(self, msg: dict) -> None:
        instrument_id = self._get_instrument_id(msg["symbol"])
        trade = TradeTick(
            instrument_id=instrument_id,
            price=Price.from_str(msg["price"]),
            size=Quantity.from_str(msg["size"]),
            aggressor_side=AggressorSide.BUYER if msg["side"] == "Buy" else AggressorSide.SELLER,
            trade_id=TradeId(msg["tradeId"]),
            ts_event=millis_to_nanos(msg["timestamp"]),
            ts_init=self._clock.timestamp_ns(),
        )
        self._handle_data(trade)

    def _process_quote(self, msg: dict) -> None:
        instrument_id = self._get_instrument_id(msg["symbol"])
        quote = QuoteTick(
            instrument_id=instrument_id,
            bid_price=Price.from_str(msg["bestBid"]),
            ask_price=Price.from_str(msg["bestAsk"]),
            bid_size=Quantity.from_str(msg["bestBidSize"]),
            ask_size=Quantity.from_str(msg["bestAskSize"]),
            ts_event=millis_to_nanos(msg["timestamp"]),
            ts_init=self._clock.timestamp_ns(),
        )
        self._handle_data(quote)
```

## LiveExecutionClient — Full Template

```python
from nautilus_trader.live.execution_client import LiveExecutionClient
from nautilus_trader.execution.messages import (
    BatchCancelOrders, CancelAllOrders, CancelOrder,
    GenerateFillReports, GenerateOrderStatusReport,
    GenerateOrderStatusReports, GeneratePositionStatusReports,
    ModifyOrder, SubmitOrder, SubmitOrderList,
)
from nautilus_trader.execution.reports import (
    ExecutionMassStatus, FillReport, OrderStatusReport, PositionStatusReport,
)


class MyExchangeLiveExecClient(LiveExecutionClient):
    def __init__(self, loop, client_id, venue, msgbus, cache, clock, config):
        super().__init__(
            loop=loop,
            client_id=client_id,
            venue=venue,
            oms_type=OmsType.NETTING,  # or HEDGING
            account_type=AccountType.MARGIN,
            base_currency=None,  # multi-currency
            msgbus=msgbus,
            cache=cache,
            clock=clock,
        )
        self._config = config
        self._http_client = None
        self._ws_client = None

    async def _connect(self) -> None:
        self._http_client = MyExchangeHttpClient(self._config)
        self._ws_client = MyExchangeWebSocketClient(
            url=self._config.ws_url,
            handler=self._handle_execution_message,
        )
        await self._ws_client.connect()
        # Subscribe to user execution stream (orders, fills, positions)
        await self._ws_client.subscribe("execution")

    async def _disconnect(self) -> None:
        await self._ws_client.disconnect()

    # ── Order operations ──────────────────────────────────────

    async def _submit_order(self, command: SubmitOrder) -> None:
        order = command.order
        try:
            response = await self._http_client.place_order(
                symbol=order.instrument_id.symbol.value,
                side="Buy" if order.side == OrderSide.BUY else "Sell",
                order_type=self._map_order_type(order.order_type),
                qty=str(order.quantity),
                price=str(order.price) if hasattr(order, "price") and order.price else None,
                time_in_force=self._map_tif(order.time_in_force),
                reduce_only=order.is_reduce_only,
                post_only=order.is_post_only if hasattr(order, "is_post_only") else False,
                client_order_id=order.client_order_id.value,
            )
            self.generate_order_accepted(
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                venue_order_id=VenueOrderId(response["orderId"]),
                ts_event=self._clock.timestamp_ns(),
            )
        except Exception as e:
            self.generate_order_rejected(
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                reason=str(e),
                ts_event=self._clock.timestamp_ns(),
            )

    async def _submit_order_list(self, command: SubmitOrderList) -> None:
        for order in command.order_list.orders:
            await self._submit_order(SubmitOrder(
                trader_id=command.trader_id,
                strategy_id=command.strategy_id,
                order=order,
                command_id=command.id,
                ts_init=command.ts_init,
            ))

    async def _modify_order(self, command: ModifyOrder) -> None:
        try:
            await self._http_client.amend_order(
                order_id=command.venue_order_id.value,
                qty=str(command.quantity) if command.quantity else None,
                price=str(command.price) if command.price else None,
            )
            # Venue will confirm via WS execution stream
        except Exception as e:
            self.generate_order_modify_rejected(
                strategy_id=command.strategy_id,
                instrument_id=command.instrument_id,
                client_order_id=command.client_order_id,
                venue_order_id=command.venue_order_id,
                reason=str(e),
                ts_event=self._clock.timestamp_ns(),
            )

    async def _cancel_order(self, command: CancelOrder) -> None:
        try:
            await self._http_client.cancel_order(
                order_id=command.venue_order_id.value,
            )
            # Venue will confirm via WS execution stream
        except Exception as e:
            self.generate_order_cancel_rejected(
                strategy_id=command.strategy_id,
                instrument_id=command.instrument_id,
                client_order_id=command.client_order_id,
                venue_order_id=command.venue_order_id,
                reason=str(e),
                ts_event=self._clock.timestamp_ns(),
            )

    async def _cancel_all_orders(self, command: CancelAllOrders) -> None:
        await self._http_client.cancel_all_orders(
            symbol=command.instrument_id.symbol.value if command.instrument_id else None,
        )

    async def _batch_cancel_orders(self, command: BatchCancelOrders) -> None:
        for cancel in command.cancels:
            await self._cancel_order(cancel)

    # ── Reconciliation reports ────────────────────────────────

    async def generate_order_status_report(
        self, command: GenerateOrderStatusReport,
    ) -> OrderStatusReport | None:
        response = await self._http_client.get_order(
            order_id=command.venue_order_id.value,
        )
        if not response:
            return None
        return OrderStatusReport(
            account_id=self.account_id,
            instrument_id=self._get_instrument_id(response["symbol"]),
            client_order_id=ClientOrderId(response.get("clientOrderId", "")),
            venue_order_id=VenueOrderId(response["orderId"]),
            order_side=OrderSide.BUY if response["side"] == "Buy" else OrderSide.SELL,
            order_type=self._parse_order_type(response["orderType"]),
            time_in_force=self._parse_tif(response["timeInForce"]),
            order_status=self._parse_order_status(response["status"]),
            quantity=Quantity.from_str(response["qty"]),
            filled_qty=Quantity.from_str(response["filledQty"]),
            avg_px=Decimal(response["avgPrice"]) if response.get("avgPrice") else None,
            price=Price.from_str(response["price"]) if response.get("price") else None,
            trigger_price=Price.from_str(response["triggerPrice"]) if response.get("triggerPrice") else None,
            post_only=response.get("postOnly", False),
            reduce_only=response.get("reduceOnly", False),
            ts_accepted=millis_to_nanos(response["createdTime"]),
            ts_last=millis_to_nanos(response["updatedTime"]),
            ts_init=self._clock.timestamp_ns(),
            report_id=UUID4(),
        )

    async def generate_order_status_reports(
        self, command: GenerateOrderStatusReports,
    ) -> list[OrderStatusReport]:
        open_orders = await self._http_client.get_open_orders()
        return [await self._build_order_report(o) for o in open_orders]

    async def generate_fill_reports(
        self, command: GenerateFillReports,
    ) -> list[FillReport]:
        trades = await self._http_client.get_recent_trades_user(
            lookback_mins=command.lookback_mins,
        )
        return [self._build_fill_report(t) for t in trades]

    async def generate_position_status_reports(
        self, command: GeneratePositionStatusReports,
    ) -> list[PositionStatusReport]:
        positions = await self._http_client.get_positions()
        return [self._build_position_report(p) for p in positions]

    async def generate_mass_status(
        self, lookback_mins: int | None = None,
    ) -> ExecutionMassStatus | None:
        orders = await self.generate_order_status_reports(None)
        fills = await self.generate_fill_reports(None)
        positions = await self.generate_position_status_reports(None)
        return ExecutionMassStatus(
            client_id=self.id,
            account_id=self.account_id,
            venue=self.venue,
            order_reports={r.venue_order_id: r for r in orders},
            fill_reports={r.trade_id: r for r in fills},
            position_reports={r.instrument_id: [r] for r in positions},
            ts_init=self._clock.timestamp_ns(),
            report_id=UUID4(),
        )

    # ── WS execution handler ─────────────────────────────────

    def _handle_execution_message(self, raw: bytes) -> None:
        msg = self._parse_ws_message(raw)
        topic = msg.get("topic", "")

        if topic == "order":
            self._process_order_update(msg["data"])
        elif topic == "execution":
            self._process_fill(msg["data"])
        elif topic == "position":
            self._process_position_update(msg["data"])

    def _process_order_update(self, data: dict) -> None:
        client_order_id = ClientOrderId(data["clientOrderId"])
        venue_order_id = VenueOrderId(data["orderId"])
        status = data["status"]

        if status == "Cancelled":
            self.generate_order_canceled(
                strategy_id=self._get_strategy_id(client_order_id),
                instrument_id=self._get_instrument_id(data["symbol"]),
                client_order_id=client_order_id,
                venue_order_id=venue_order_id,
                ts_event=millis_to_nanos(data["updatedTime"]),
            )
        elif status == "Rejected":
            self.generate_order_rejected(
                strategy_id=self._get_strategy_id(client_order_id),
                instrument_id=self._get_instrument_id(data["symbol"]),
                client_order_id=client_order_id,
                reason=data.get("rejectReason", "Unknown"),
                ts_event=millis_to_nanos(data["updatedTime"]),
            )

    def _process_fill(self, data: dict) -> None:
        client_order_id = ClientOrderId(data["clientOrderId"])
        self.generate_order_filled(
            strategy_id=self._get_strategy_id(client_order_id),
            instrument_id=self._get_instrument_id(data["symbol"]),
            client_order_id=client_order_id,
            venue_order_id=VenueOrderId(data["orderId"]),
            venue_position_id=None,
            trade_id=TradeId(data["execId"]),
            order_side=OrderSide.BUY if data["side"] == "Buy" else OrderSide.SELL,
            order_type=self._parse_order_type(data["orderType"]),
            last_qty=Quantity.from_str(data["execQty"]),
            last_px=Price.from_str(data["execPrice"]),
            quote_currency=Currency.from_str(data["currency"]),
            commission=Money.from_str(f"{data['execFee']} {data['currency']}"),
            liquidity_side=LiquiditySide.MAKER if data["isMaker"] else LiquiditySide.TAKER,
            ts_event=millis_to_nanos(data["execTime"]),
        )
```

## Configuration Classes

```python
import msgspec

class MyExchangeDataClientConfig(msgspec.Struct, frozen=True):
    api_key: str = ""
    api_secret: str = ""
    ws_url: str = "wss://stream.myexchange.com/v5/public"
    rest_url: str = "https://api.myexchange.com"
    testnet: bool = False

class MyExchangeExecClientConfig(msgspec.Struct, frozen=True):
    api_key: str = ""
    api_secret: str = ""
    ws_url: str = "wss://stream.myexchange.com/v5/private"
    rest_url: str = "https://api.myexchange.com"
    testnet: bool = False
    max_retries: int = 3
    retry_delay_initial_ms: int = 500
    retry_delay_max_ms: int = 5000
```

## Data Flow Summary

```
Venue WS/REST → DataClient._handle_ws_message()
    → parse raw JSON to Nautilus types (OrderBookDelta, TradeTick, QuoteTick)
    → self._handle_data(nautilus_object)
        → DataEngine processes
            → Cache updated
            → MessageBus publishes
                → Strategy.on_order_book_deltas() / on_trade_tick() / on_quote_tick()
```

## Key Utilities

```python
from nautilus_trader.core.datetime import millis_to_nanos, secs_to_nanos
from nautilus_trader.model.identifiers import (
    ClientId, ClientOrderId, InstrumentId, Symbol, TradeId, Venue, VenueOrderId,
)
from nautilus_trader.model.enums import (
    AggressorSide, BookAction, LiquiditySide, OmsType, OrderSide,
    OrderStatus, OrderType, RecordFlag, TimeInForce, TriggerType,
)
from nautilus_trader.model.data import (
    Bar, BookOrder, OrderBookDelta, QuoteTick, TradeTick,
)
from nautilus_trader.model.objects import Price, Quantity, Money
```
