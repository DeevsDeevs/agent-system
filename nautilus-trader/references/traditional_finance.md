# Traditional Finance

Equity, FuturesContract, FuturesSpread, CFD, Commodity, IndexInstrument, and IB adapter (v1.224.0).

> *Python only — IB adapters are Python/Cython. Instrument types exist in `nautilus-model` (Rust), but no Rust IB adapter.*

## TradFi Instrument Types

### Equity

```python
from nautilus_trader.model.instruments import Equity
from nautilus_trader.model.identifiers import InstrumentId, Symbol
from nautilus_trader.model.objects import Currency, Price, Quantity

equity = Equity(
    instrument_id=InstrumentId.from_str("AAPL.XNAS"),
    raw_symbol=Symbol("AAPL"),
    currency=Currency.from_str("USD"),
    price_precision=2,
    price_increment=Price.from_str("0.01"),
    lot_size=Quantity.from_int(1),
    ts_event=0, ts_init=0,
    isin="US0378331005",                # optional
)
# Hardcoded: size_precision=0, size_increment=1, multiplier=1, asset_class=EQUITY
```

### FuturesContract

```python
from nautilus_trader.model.instruments import FuturesContract
from nautilus_trader.model.enums import AssetClass

future = FuturesContract(
    instrument_id=InstrumentId.from_str("ESH25.GLBX"),
    raw_symbol=Symbol("ESH25"),
    asset_class=AssetClass.INDEX,
    currency=Currency.from_str("USD"),
    price_precision=2,
    price_increment=Price.from_str("0.25"),
    multiplier=Quantity.from_int(50),       # ES = $50 per point
    lot_size=Quantity.from_int(1),
    underlying="ES",
    activation_ns=0,
    expiration_ns=1742515200_000_000_000,
    ts_event=0, ts_init=0,
    exchange="GLBX",                        # ISO 10383 MIC
)
# Hardcoded: size_precision=0, size_increment=1
# Properties: .exchange, .underlying, .activation_utc, .expiration_utc (pd.Timestamp UTC)
```

### FuturesSpread

```python
from nautilus_trader.model.instruments import FuturesSpread

spread = FuturesSpread(
    instrument_id=InstrumentId.from_str("ESH25-ESM25.GLBX"),
    raw_symbol=Symbol("ESH25-ESM25"),
    asset_class=AssetClass.INDEX,
    currency=Currency.from_str("USD"),
    price_precision=2,
    price_increment=Price.from_str("0.05"),
    multiplier=Quantity.from_int(50),
    lot_size=Quantity.from_int(1),
    underlying="ES",
    strategy_type="CALENDAR",               # required, non-empty str
    activation_ns=0,
    expiration_ns=1742515200_000_000_000,
    ts_event=0, ts_init=0,
    exchange="GLBX",
)
# .legs() -> list[tuple[InstrumentId, int]]
```

### Other TradFi Instruments

| Type | Import |
|------|--------|
| `Cfd` | `from nautilus_trader.model.instruments import Cfd` |
| `Commodity` | `from nautilus_trader.model.instruments import Commodity` |
| `IndexInstrument` | `from nautilus_trader.model.instruments import IndexInstrument` |

## Interactive Brokers Adapter

Requires: `pip install nautilus_trader[ib]`

Strategy ↔ NautilusTrader ↔ IB Gateway/TWS (localhost) ↔ IB Servers

### DockerizedIBGateway

```python
from nautilus_trader.adapters.interactive_brokers.config import DockerizedIBGatewayConfig

gateway_config = DockerizedIBGatewayConfig(
    username="...", password="...",
    trading_mode="paper",                   # "paper" or "live"
    read_only_api=True,                     # True = no order execution
    timeout=300,
    container_image="ghcr.io/gnzsnz/ib-gateway:stable",
)
```

### Data Client Config

```python
from nautilus_trader.adapters.interactive_brokers.config import (
    InteractiveBrokersDataClientConfig,
    InteractiveBrokersInstrumentProviderConfig,
    SymbologyMethod,
)

data_config = InteractiveBrokersDataClientConfig(
    ibg_host="127.0.0.1",
    ibg_port=None,                          # paper: IBG=4002/TWS=7497, live: IBG=4001/TWS=7496
    ibg_client_id=1,
    use_regular_trading_hours=True,         # RTH only for bar data (not ticks)
    market_data_type=1,                     # 1=REALTIME, 4=DELAYED_FROZEN (no sub needed)
    dockerized_gateway=gateway_config,
    instrument_provider=InteractiveBrokersInstrumentProviderConfig(
        symbology_method=SymbologyMethod.IB_SIMPLIFIED,
    ),
)
```

### Execution Client Config

`InteractiveBrokersExecClientConfig(ibg_host, ibg_port, ibg_client_id, account_id, dockerized_gateway, fetch_all_open_orders=False, track_option_exercise_from_position_update=False)`. `fetch_all_open_orders=True` gets all clients + TWS GUI orders.

### IBContract

```python
from nautilus_trader.adapters.interactive_brokers.common import IBContract

aapl = IBContract(secType="STK", symbol="AAPL", exchange="SMART",
                  primaryExchange="ARCA", currency="USD")
es = IBContract(secType="FUT", symbol="ES", exchange="CME",
                lastTradeDateOrContractMonth="202503")
es_cont = IBContract(secType="CONTFUT", symbol="ES", exchange="CME",
                     build_futures_chain=True)
aapl_call = IBContract(secType="OPT", symbol="AAPL", exchange="SMART",
                       currency="USD", lastTradeDateOrContractMonth="20250321",
                       strike=150.0, right="C")
eur_usd = IBContract(secType="CASH", exchange="IDEALPRO",
                     symbol="EUR", currency="USD")
btc = IBContract(secType="CRYPTO", symbol="BTC",
                 exchange="PAXOS", currency="USD")
spx = IBContract(secType="IND", symbol="SPX", exchange="CBOE")
gold = IBContract(secType="CMDTY", symbol="XAUUSD", exchange="SMART")
```

### Chain Building

Chain flags are on `IBContract`, not the provider config:

```python
instrument_provider = InteractiveBrokersInstrumentProviderConfig(
    load_contracts=frozenset({
        IBContract(secType="IND", symbol="SPX", exchange="CBOE",
                   build_options_chain=True, min_expiry_days=7, max_expiry_days=90),
        IBContract(secType="CONTFUT", symbol="ES", exchange="CME",
                   build_futures_chain=True),
    }),
)
```

### Symbology

| Method | Example |
|--------|---------|
| `IB_SIMPLIFIED` (default) | `ESZ28.CME`, `EUR/USD.IDEALPRO` |
| `IB_RAW` | `EUR.USD=CASH.IDEALPRO` |

### Market Data Types

| Value | Name | Notes |
|-------|------|-------|
| 1 | `REALTIME` | Requires market data subscription |
| 2 | `FROZEN` | Last available snapshot |
| 3 | `DELAYED` | 15-min delayed |
| 4 | `DELAYED_FROZEN` | No subscription needed |

`filter_sec_types=frozenset({"WAR", "IOPT"})` skips warrants/structured products. Port: if `ibg_port=None`, auto-selected from `DockerizedIBGatewayConfig.trading_mode`.

## Market Session & Instrument Status

### TradingState (Risk Engine)

System-wide: `TradingState.ACTIVE` (orders flow), `HALTED` (all rejected), `REDUCING` (only cancels/reducing).

### InstrumentStatus (Per-Instrument)

Does NOT automatically stop order flow — strategy must react. Session: `PRE_OPEN` → `TRADING` → `POST_CLOSE`. Interruptions: `HALT`, `PAUSE`, `SUSPEND`. v1.224.0: functionally equivalent.

```python
def on_instrument_status(self, status: InstrumentStatus) -> None:
    if status.action in (MarketStatusAction.HALT, MarketStatusAction.PAUSE,
                         MarketStatusAction.NOT_AVAILABLE_FOR_TRADING):
        self.cancel_all_orders(status.instrument_id)
```

Supported: Betfair, BitMEX, dYdX, Deribit, Databento, IB. Binance raises `NotImplementedError`. No automatic bridge to TradingState — call `set_trading_state()` manually if needed.

### InstrumentClose

`InstrumentClose`: `instrument_id`, `close_price`, `close_type` (`END_OF_SESSION` / `CONTRACT_EXPIRED`), `ts_event`, `ts_init`.

## Databento for TradFi

L3 MBO data for US equities/futures. See [exchange_adapters.md](exchange_adapters.md) for schema mappings.

| Schema | Use Case |
|--------|----------|
| `MBO` | L3 order book reconstruction |
| `MBP_1` | BBO quotes |
| `MBP_10` | Depth-of-book (10 levels) |
| `TRADES` | Time & sales |
| `OHLCV_*` | Bars at various intervals |
| `DEFINITION` | Instrument definitions |

> See SKILL.md for common hallucination guards.
