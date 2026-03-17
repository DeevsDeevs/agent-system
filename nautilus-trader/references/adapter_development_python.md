# Python Adapter Development

| Component | Base Class | Purpose |
|-----------|-----------|---------|
| InstrumentProvider | `InstrumentProvider` | Load/parse venue instruments |
| Data Client | `LiveMarketDataClient` | Market data subscriptions |
| Execution Client | `LiveExecutionClient` | Order management |
| Config | `msgspec.Struct` | Configuration classes |
| Factories | `LiveDataClientFactory` / `LiveExecClientFactory` | TradingNode registration |

## InstrumentProvider

```python
from nautilus_trader.common.providers import InstrumentProvider
from nautilus_trader.model.instruments import CryptoPerpetual

class MyExchangeInstrumentProvider(InstrumentProvider):
    def __init__(self, http_client, clock, config=None):
        super().__init__(config=config)
        self._http_client = http_client
        self._clock = clock

    async def load_all_async(self, filters=None) -> None:
        for raw in await self._http_client.get_instruments():
            self._add_instrument(self._parse_instrument(raw))

    async def load_ids_async(self, instrument_ids, filters=None) -> None:
        for iid in instrument_ids:
            raw = await self._http_client.get_instrument(iid.symbol.value)
            self._add_instrument(self._parse_instrument(raw))

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

Config: `InstrumentProviderConfig(load_all=True)` or `InstrumentProviderConfig(load_ids=["BTCUSDT-PERP.MYEXCH"])`

## LiveMarketDataClient

```python
from nautilus_trader.live.data_client import LiveMarketDataClient

class MyExchangeDataClient(LiveMarketDataClient):
    def __init__(self, loop, client_id, venue, msgbus, cache, clock, config):
        super().__init__(loop=loop, client_id=client_id, venue=venue,
            msgbus=msgbus, cache=cache, clock=clock)
        self._config = config
        self._ws_client = None
        self._http_client = None
        self._subscriptions: set[str] = set()

    async def _connect(self) -> None:
        self._http_client = MyExchangeHttpClient(self._config)
        self._ws_client = MyExchangeWebSocketClient(
            url=self._config.ws_url, handler=self._handle_ws_message,
            on_reconnect=self._on_reconnect)
        await self._ws_client.connect()

    async def _disconnect(self) -> None:
        await self._ws_client.disconnect()
        self._subscriptions.clear()

    async def _on_reconnect(self) -> None:
        for sub in self._subscriptions:
            await self._ws_client.subscribe(sub)

    async def _subscribe_order_book_deltas(self, command) -> None:
        channel = f"orderbook.{command.instrument_id.symbol.value}"
        self._subscriptions.add(channel)
        await self._ws_client.subscribe(channel)

    def _handle_ws_message(self, raw: bytes) -> None:
        msg = orjson.loads(raw)
        channel = msg.get("channel", "")
        if channel.startswith("orderbook."):
            self._process_order_book_update(msg)
        elif channel.startswith("trades."):
            self._process_trade(msg)
        elif channel.startswith("ticker."):
            self._process_quote(msg)

    def _process_order_book_update(self, msg: dict) -> None:
        instrument_id = self._get_instrument_id(msg["symbol"])
        for i, update in enumerate(msg["data"]):
            flags = RecordFlag.F_LAST if i == len(msg["data"]) - 1 else 0
            delta = OrderBookDelta(
                instrument_id=instrument_id,
                action=BookAction.UPDATE if Quantity.from_str(update["size"]).raw > 0 else BookAction.DELETE,
                order=BookOrder(
                    side=OrderSide.BUY if update["side"] == "Buy" else OrderSide.SELL,
                    price=Price.from_str(update["price"]),
                    size=Quantity.from_str(update["size"]), order_id=0),
                flags=flags, sequence=msg.get("sequence", 0),
                ts_event=millis_to_nanos(msg["timestamp"]),
                ts_init=self._clock.timestamp_ns(),
            )
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
```

Other data methods: `_subscribe_bars`, `_subscribe_trade_ticks`, `_subscribe_quote_ticks`. REST: `_request_order_book_snapshot` (CLEAR+ADD+F_LAST).

## LiveExecutionClient

```python
from nautilus_trader.live.execution_client import LiveExecutionClient

class MyExchangeExecClient(LiveExecutionClient):
    def __init__(self, loop, client_id, venue, msgbus, cache, clock, config):
        super().__init__(loop=loop, client_id=client_id, venue=venue,
            oms_type=OmsType.NETTING, account_type=AccountType.MARGIN,
            base_currency=None, msgbus=msgbus, cache=cache, clock=clock)
        self._config = config

    async def _connect(self) -> None:
        self._http_client = MyExchangeHttpClient(self._config)
        self._ws_client = MyExchangeWebSocketClient(
            url=self._config.ws_private_url, handler=self._handle_execution_message)
        await self._ws_client.connect()
        await self._ws_client.subscribe("execution")

    async def _submit_order(self, command) -> None:
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
                strategy_id=order.strategy_id, instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                venue_order_id=VenueOrderId(response["orderId"]),
                ts_event=self._clock.timestamp_ns(),
            )
        except Exception as e:
            self.generate_order_rejected(
                strategy_id=order.strategy_id, instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                reason=str(e), ts_event=self._clock.timestamp_ns(),
            )

    async def _modify_order(self, command) -> None:
        try:
            await self._http_client.amend_order(
                order_id=command.venue_order_id.value,
                qty=str(command.quantity) if command.quantity else None,
                price=str(command.price) if command.price else None)
        except Exception as e:
            self.generate_order_modify_rejected(
                strategy_id=command.strategy_id, instrument_id=command.instrument_id,
                client_order_id=command.client_order_id,
                venue_order_id=command.venue_order_id,
                reason=str(e), ts_event=self._clock.timestamp_ns())

    async def _cancel_order(self, command) -> None:
        try:
            await self._http_client.cancel_order(order_id=command.venue_order_id.value)
        except Exception as e:
            self.generate_order_cancel_rejected(
                strategy_id=command.strategy_id, instrument_id=command.instrument_id,
                client_order_id=command.client_order_id,
                venue_order_id=command.venue_order_id,
                reason=str(e), ts_event=self._clock.timestamp_ns())

    async def _cancel_all_orders(self, command) -> None:
        await self._http_client.cancel_all_orders(
            symbol=command.instrument_id.symbol.value if command.instrument_id else None)

    def _handle_execution_message(self, raw: bytes) -> None:
        msg = orjson.loads(raw)
        topic = msg.get("topic", "")
        if topic == "execution":
            self._process_fill(msg["data"])
        elif topic == "order":
            self._process_order_update(msg["data"])

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

    async def generate_mass_status(self, lookback_mins=None) -> ExecutionMassStatus | None:
        orders = await self._http_client.get_open_orders()
        fills = await self._http_client.get_recent_trades_user(lookback_mins=lookback_mins)
        positions = await self._http_client.get_positions()
        return ExecutionMassStatus(
            client_id=self.id, account_id=self.account_id, venue=self.venue,
            order_reports={VenueOrderId(o["orderId"]): self._build_order_report(o) for o in orders},
            fill_reports={TradeId(f["execId"]): self._build_fill_report(f) for f in fills},
            position_reports={self._get_instrument_id(p["symbol"]): [self._build_position_report(p)] for p in positions},
            ts_init=self._clock.timestamp_ns(), report_id=UUID4(),
        )
```

## Configuration

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
    ws_private_url: str = "wss://stream.myexchange.com/v5/private"
    rest_url: str = "https://api.myexchange.com"
    testnet: bool = False
    max_retries: int = 3
```

## Factory Registration

```python
from nautilus_trader.live.factories import LiveDataClientFactory, LiveExecClientFactory

class MyDataClientFactory(LiveDataClientFactory):
    @staticmethod
    def create(loop, name, config, msgbus, cache, clock):
        return MyExchangeDataClient(loop=loop, client_id=ClientId(name),
            venue=Venue(name), msgbus=msgbus, cache=cache, clock=clock, config=config)

class MyExecClientFactory(LiveExecClientFactory):
    @staticmethod
    def create(loop, name, config, msgbus, cache, clock):
        return MyExchangeExecClient(loop=loop, client_id=ClientId(name),
            venue=Venue(name), msgbus=msgbus, cache=cache, clock=clock, config=config)

node.add_data_client_factory("MYEXCH", MyDataClientFactory)
node.add_exec_client_factory("MYEXCH", MyExecClientFactory)
```

Utility: `from nautilus_trader.core.datetime import millis_to_nanos, secs_to_nanos`.
