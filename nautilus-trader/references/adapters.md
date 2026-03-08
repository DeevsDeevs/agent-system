# Adapters

## Adapter Components

Every venue adapter includes:

| Component | Role |
|-----------|------|
| `HttpClient` | REST API communication |
| `WebSocketClient` | Real-time streaming |
| `InstrumentProvider` | Parses venue responses → Nautilus Instrument objects |
| `DataClient` | Market data subscriptions and requests |
| `ExecutionClient` | Order submission, modification, cancellation |

## Available Adapters

### Cryptocurrency Exchanges

| Adapter | Venue | Asset Types |
|---------|-------|-------------|
| Binance | `BINANCE` | Spot, USDT Futures, Coin Futures |
| Bybit | `BYBIT` | Spot, Linear, Inverse |
| OKX | `OKX` | Spot, Perpetual, Futures, Options |
| BitMEX | `BITMEX` | Perpetuals, Futures |
| dYdX | `DYDX` | Perpetuals |
| Polymarket | `POLYMARKET` | Binary options (prediction markets) |

### Traditional Brokers

| Adapter | Venue | Asset Types |
|---------|-------|-------------|
| Interactive Brokers | `IDEALPRO`, `NYMEX`, etc. | Equities, FX, Futures, Options |

### Data Providers

| Adapter | Role |
|---------|------|
| Databento | Ultra-fast DBN format, consolidated US equities/futures |
| Tardis | Historical crypto market data replay |

## Instrument Provider Configuration

```python
from nautilus_trader.config import InstrumentProviderConfig

# Load all instruments
InstrumentProviderConfig(load_all=True)

# Load specific instruments only
InstrumentProviderConfig(
    load_ids=["BTCUSDT-PERP.BINANCE", "ETHUSDT-PERP.BINANCE"]
)
```

### Discover Instruments Programmatically

```python
import asyncio
from nautilus_trader.adapters.binance.common.enums import BinanceAccountType
from nautilus_trader.adapters.binance import get_cached_binance_http_client
from nautilus_trader.adapters.binance.futures.providers import BinanceFuturesInstrumentProvider
from nautilus_trader.common.component import LiveClock

async def discover():
    clock = LiveClock()
    client = get_cached_binance_http_client(
        clock=clock,
        account_type=BinanceAccountType.USDT_FUTURES,
        api_key="your_key",
        api_secret="your_secret",
        is_testnet=True,
    )
    provider = BinanceFuturesInstrumentProvider(
        client=client,
        account_type=BinanceAccountType.USDT_FUTURES,
    )
    await provider.load_all_async()
    for instrument in provider.list_all():
        print(instrument.id)

asyncio.run(discover())
```

## Creating Custom Adapters

### Data Client

```python
from nautilus_trader.live.data_client import LiveMarketDataClient
from nautilus_trader.model.data import QuoteTick, TradeTick, Bar
from nautilus_trader.model.identifiers import InstrumentId


class MyDataClient(LiveMarketDataClient):
    def __init__(self, loop, client_id, venue, msgbus, cache, clock):
        super().__init__(
            loop=loop,
            client_id=client_id,
            venue=venue,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
        )

    async def _connect(self) -> None:
        # Connect to venue API, load instruments
        pass

    async def _disconnect(self) -> None:
        # Clean up connections
        pass

    async def _subscribe_quote_ticks(self, instrument_id: InstrumentId) -> None:
        # Subscribe to venue quote stream, call self._handle_data(tick) on updates
        pass

    async def _subscribe_trade_ticks(self, instrument_id: InstrumentId) -> None:
        pass

    async def _subscribe_bars(self, bar_type) -> None:
        pass

    def _handle_data(self, data) -> None:
        # Route data through the engine
        self._msgbus.send(endpoint="DataEngine.process", msg=data)
```

### Execution Client

```python
from nautilus_trader.live.execution_client import LiveExecutionClient
from nautilus_trader.model.commands import SubmitOrder, CancelOrder, ModifyOrder


class MyExecutionClient(LiveExecutionClient):
    async def _connect(self) -> None:
        pass

    async def _disconnect(self) -> None:
        pass

    async def _submit_order(self, command: SubmitOrder) -> None:
        # Convert Nautilus order to venue format, submit via API
        pass

    async def _cancel_order(self, command: CancelOrder) -> None:
        pass

    async def _modify_order(self, command: ModifyOrder) -> None:
        pass
```

### Client Factories

Register factories so TradingNode can instantiate your clients:

```python
from nautilus_trader.live.factories import LiveDataClientFactory, LiveExecClientFactory


class MyDataClientFactory(LiveDataClientFactory):
    @staticmethod
    def create(
        loop,
        name,
        config,
        msgbus,
        cache,
        clock,
    ):
        return MyDataClient(
            loop=loop,
            client_id=ClientId(name),
            venue=Venue(name),
            msgbus=msgbus,
            cache=cache,
            clock=clock,
        )


class MyExecClientFactory(LiveExecClientFactory):
    @staticmethod
    def create(
        loop,
        name,
        config,
        msgbus,
        cache,
        clock,
    ):
        return MyExecutionClient(
            loop=loop,
            client_id=ClientId(name),
            venue=Venue(name),
            msgbus=msgbus,
            cache=cache,
            clock=clock,
        )
```

## Binance Configuration Example

```python
from nautilus_trader.adapters.binance.config import BinanceDataClientConfig
from nautilus_trader.adapters.binance.config import BinanceExecClientConfig
from nautilus_trader.adapters.binance.common.enums import BinanceAccountType
from nautilus_trader.config import TradingNodeConfig, InstrumentProviderConfig

config = TradingNodeConfig(
    data_clients={
        "BINANCE": BinanceDataClientConfig(
            api_key="your_api_key",
            api_secret="your_api_secret",
            account_type=BinanceAccountType.USDT_FUTURES,
            instrument_provider=InstrumentProviderConfig(load_all=True),
        ),
    },
    exec_clients={
        "BINANCE": BinanceExecClientConfig(
            api_key="your_api_key",
            api_secret="your_api_secret",
            account_type=BinanceAccountType.USDT_FUTURES,
        ),
    },
)
```

## Symbology Conventions

| Venue | Format | Example |
|-------|--------|---------|
| Binance Spot | `{BASE}{QUOTE}.BINANCE` | `BTCUSDT.BINANCE` |
| Binance Perp | `{BASE}{QUOTE}-PERP.BINANCE` | `ETHUSDT-PERP.BINANCE` |
| OKX | `{BASE}-{QUOTE}.OKX` | `BTC-USDT.OKX` |
| Interactive Brokers | `{SYMBOL}.{EXCHANGE}` | `EUR/USD.IDEALPRO` |
| Databento | `{SYMBOL}.{DATASET}` | `ES.FUT.GLBX` |

The `-PERP` suffix is mandatory for Binance perpetuals to distinguish from spot pairs.
