# Derivatives

CryptoPerpetual, CryptoFuture, mark price, funding rates, liquidation, and circuit breakers in NautilusTrader.

> **Options**: For CryptoOption, OptionContract, OptionSpread, BinaryOption, greeks calculation, and Black-Scholes functions, see [options_and_greeks.md](options_and_greeks.md).

## Instrument Types

### CryptoPerpetual

No expiry. Funding rate anchors price to spot.

```python
perp = cache.instrument(InstrumentId.from_str("BTCUSDT-PERP.BINANCE"))

perp.base_currency       # BTC
perp.quote_currency      # USDT
perp.settlement_currency # USDT
perp.is_inverse          # False (linear), True (coin-margined)
perp.multiplier          # Contract multiplier
perp.margin_init          # Initial margin rate (e.g., 0.01 = 100x)
perp.margin_maint         # Maintenance margin rate
perp.maker_fee           # Maker fee rate
perp.taker_fee           # Taker fee rate
```

### CryptoFuture

Expiring futures with settlement date.

```python
future = cache.instrument(InstrumentId.from_str("BTCUSDT-250328.BINANCE"))
future.expiration         # Expiration datetime
future.activation         # When contract becomes tradeable
```

### PerpetualContract

General-purpose perpetual for **any asset class** — FX, equities, commodities, indexes, crypto. Unlike `CryptoPerpetual` (crypto-specific), `underlying` is a `str` and `asset_class` is configurable.

```python
from nautilus_trader.model.instruments import PerpetualContract
from nautilus_trader.model.enums import AssetClass

perp = PerpetualContract(
    instrument_id=InstrumentId.from_str("EURUSD-PERP.VENUE"),
    raw_symbol=Symbol("EURUSD-PERP"),
    underlying="EURUSD",                       # str, not Currency
    asset_class=AssetClass.FX,                 # any asset class
    quote_currency=Currency.from_str("USD"),
    settlement_currency=Currency.from_str("USD"),
    is_inverse=False,
    price_precision=5,
    size_precision=0,
    price_increment=Price.from_str("0.00001"),
    size_increment=Quantity.from_int(1),
    ts_event=0,
    ts_init=0,
)

perp.underlying              # "EURUSD"
perp.asset_class             # AssetClass.FX
```

Use `CryptoPerpetual` for crypto venues (Binance, Bybit, etc.). Use `PerpetualContract` when the underlying is non-crypto or when the adapter provides it.

### CryptoOption

Crypto options (Deribit, Bybit). Settlement in crypto. See [options_and_greeks.md](options_and_greeks.md) for full details.

```python
from nautilus_trader.model.instruments import CryptoOption
# CryptoOption(instrument_id, raw_symbol, underlying=Currency, quote_currency, settlement_currency,
#              is_inverse, option_kind, strike_price, activation_ns, expiration_ns, ...)
```

Key fields: `underlying` (Currency), `settlement_currency`, `option_kind` (OptionKind.CALL/PUT), `strike_price`, `is_inverse`.

### Comparison

| Feature | CryptoPerpetual | CryptoFuture | CryptoOption |
|---------|----------------|--------------|-------------|
| Expiry | None | Fixed settlement | Fixed expiry |
| Funding | Every 8h (typically) | None | None |
| Price anchor | Funding rate | Convergence at expiry | Black-Scholes |
| Basis | Funding premium | Contango/backwardation | Time value + vol |
| Greeks | delta=1 | delta=1 | Full greeks via GreeksCalculator |

## Mark Price

Mark price is used for **liquidation** and **unrealized PnL**, not for order matching.

### Formula

Mark price calculation **varies by exchange**. One common approach (e.g. Binance):

```
mark_price = median(price_1, price_2, price_3)
where:
  price_1 = (best_bid + best_ask) / 2
  price_2 = index_price * (1 + funding_basis)
  price_3 = index_price
```

Other exchanges may use different formulas (weighted averages, EMA-smoothed index, etc.). **Always check your exchange's documentation** for the exact mark price methodology — it directly affects liquidation prices.

### Subscription

```python
from nautilus_trader.model.data import MarkPriceUpdate

def on_start(self) -> None:
    self.subscribe_data(
        data_type=DataType(MarkPriceUpdate, metadata={"instrument_id": self.config.instrument_id}),
    )

def on_data(self, data) -> None:
    if isinstance(data, MarkPriceUpdate):
        mark = data.value
```

**Mark vs Last vs Index**:
- **Last**: Most recent trade execution price
- **Mark**: Fair value estimate, resistant to manipulation
- **Index**: Weighted average of spot prices across major exchanges

## Funding Rate

Perpetual contracts use funding to keep price aligned with spot index.

### Subscription

`subscribe_funding_rates()` is not implemented on all adapters. Funding data may be available through other channels depending on the exchange:

**Binance example**: Funding data is embedded in the mark price WebSocket stream (`@markPrice`). The adapter emits `BinanceFuturesMarkPriceUpdate`:

```python
from nautilus_trader.adapters.binance.futures.types import BinanceFuturesMarkPriceUpdate
from nautilus_trader.model.data import DataType

def on_start(self) -> None:
    self.subscribe_data(
        data_type=DataType(BinanceFuturesMarkPriceUpdate, metadata={"instrument_id": self.config.instrument_id}),
    )

def on_data(self, data) -> None:
    if isinstance(data, BinanceFuturesMarkPriceUpdate):
        data.mark            # Price — mark price
        data.index           # Price — index price
        data.funding_rate    # Decimal — current funding rate
        data.next_funding_ns # int — next funding timestamp (nanoseconds)
```

**Other adapters** may provide funding through different data types or require REST polling. Check each adapter's available custom data types.

> For an example of extracting funding rates into standard `FundingRateUpdate` objects via
> an Actor (custom data type pattern), see `examples/binance_enrichment_actor.py`.

### Mechanics

Funding parameters **vary by exchange and instrument**:

| Parameter | Common Values | Notes |
|-----------|--------------|-------|
| Payment interval | 8h, 4h, 1h | Binance/Bybit default 8h, dYdX uses 1h, some instruments differ |
| Rate range | Exchange-specific | Capped differently per venue |
| Direction | Positive: longs pay shorts. Negative: shorts pay longs. | Universal |

```
funding_payment = position_notional * funding_rate
position_notional = abs(position_size) * mark_price
```

**Always verify** your exchange's funding schedule for each instrument — some exchanges allow variable intervals per pair.

### Funding as Inventory Carrying Cost

For MM strategies holding perp positions, funding is an additional cost/benefit that should factor into the reservation price:

```python
# In Avellaneda-Stoikov context:
# reservation_price -= inventory * funding_rate * time_fraction
funding_cost = float(pos.signed_qty) * mark_price * self._current_funding_rate
```

Positive funding + long position = cost. Negative funding + long position = income. Factor this into whether to carry inventory through the next funding window.

### Funding Arbitrage

```python
class FundingArbitrageConfig(StrategyConfig, frozen=True):
    perp_id: InstrumentId    # BTCUSDT-PERP.BINANCE
    spot_id: InstrumentId    # BTCUSDT.BINANCE
    trade_size: Decimal
    min_rate: float = 0.0003  # 3 bps minimum to enter

class FundingArbitrage(Strategy):
    def on_data(self, data) -> None:
        if isinstance(data, FundingRateUpdate):
            if data.rate > self.config.min_rate:
                # Short perp (receive funding), long spot (hedge)
                if self.portfolio.is_flat(self.config.perp_id):
                    self._short_perp()
                    self._long_spot()
```

### Basis Arbitrage

Trade futures vs spot, expecting convergence at expiry:
- **Contango** (futures > spot): Short futures, long spot
- **Backwardation** (futures < spot): Long futures, short spot

## Open Interest

Open Interest (OI) = total outstanding contracts. Key signal for:
- Trend strength (rising OI + rising price = strong uptrend)
- Leverage buildup (rising OI + flat price = squeeze risk)
- Position unwind (falling OI + falling price = long liquidation cascade)

### Open Interest Access

OI availability varies by exchange — some provide WebSocket streams, others are REST-only. Poll via timer-based REST requests when WS is unavailable.

**Example (Binance REST)**: `GET /fapi/v1/openInterest` with `symbol` param.

Check [exchange_adapters.md](exchange_adapters.md) for per-venue REST endpoints and rate limits.

### Custom Data Example: OpenInterestData

```python
from nautilus_trader.core.data import Data

class OpenInterestData(Data):
    def __init__(self, instrument_id, open_interest: float, ts_event: int, ts_init: int):
        self.instrument_id = instrument_id
        self.open_interest = open_interest
        self._ts_event = ts_event
        self._ts_init = ts_init

    @property
    def ts_event(self) -> int:
        return self._ts_event

    @property
    def ts_init(self) -> int:
        return self._ts_init
```

> See `examples/binance_enrichment_actor.py` for a complete example of custom data types with
> timer-based REST polling and WebSocket data extraction via Actor.

## Liquidation Mechanics

Triggered by **mark price**, not last trade price.

### Process

1. Mark price moves against position
2. Margin ratio = maintenance_margin / margin_balance
3. When margin ratio >= 100% → **liquidation triggers**
4. Exchange takes over position, attempts market close
5. If closed above bankruptcy price → excess to **insurance fund**
6. If cannot close above bankruptcy → **ADL** (auto-deleveraging)

### Estimation Formula

```
# Long: liquidation_price ≈ entry * (1 - initial_margin + maintenance_margin)
# Short: liquidation_price ≈ entry * (1 + initial_margin - maintenance_margin)
```

> **Disclaimer**: This is a simplified estimation. Actual liquidation prices depend on: cross-margin vs isolated margin mode, accumulated funding payments, tiered maintenance margin rates (higher tiers have higher maintenance requirements), and insurance fund deductions. **Always use the exchange's liquidation price calculator for production systems.**

### ADL (Auto-Deleveraging)

When insurance fund depletes, the exchange forcibly closes profitable opposing positions ordered by profit ratio and leverage. NautilusTrader does **not** simulate ADL in backtest.

### Backtest Margin Enforcement

`frozen_account=False` enforces margin checks — orders exceeding margin are rejected. Remember: False = checks active (confusing naming).

## Circuit Breakers & Market Halts

Exchanges can halt/pause trading for various reasons (price limits, volatility, maintenance). NautilusTrader provides `InstrumentStatus` events for this, but **adapter support varies** — Binance does NOT implement `subscribe_instrument_status()`. See [traditional_finance.md](traditional_finance.md#market-session--instrument-status) for the full `MarketStatusAction` / `TradingState` system.

```python
from nautilus_trader.model.data import InstrumentStatus
from nautilus_trader.model.enums import MarketStatusAction

def on_start(self) -> None:
    # Not all adapters support this — check adapter docs
    self.subscribe_instrument_status(self.config.instrument_id)
    self._halted = False

def on_instrument_status(self, status: InstrumentStatus) -> None:
    if status.action in (MarketStatusAction.HALT, MarketStatusAction.PAUSE):
        self._halted = True
        self.cancel_all_orders(self.config.instrument_id)
    elif status.action == MarketStatusAction.TRADING:
        self._halted = False
```

**Note**: `MarketStatusAction.RESUME` does not exist — use `TRADING` to detect resumption. HALT, PAUSE, and SUSPEND are functionally equivalent in v1.224.0 — the backtest matching engine does not enforce them. Your strategy must implement halt logic manually.

## Position Margin

```python
account = self.portfolio.account(Venue("BINANCE"))
# cache.position_for_instrument() does NOT exist — use positions_open() filtered by instrument
positions = self.cache.positions_open(instrument_id=self.config.instrument_id)
position = positions[0] if positions else None

if position:
    initial_margin = float(position.quantity) * float(position.avg_px_open) * perp.margin_init
    maint_margin = float(position.quantity) * float(position.avg_px_open) * perp.margin_maint

account.balance_total(USDT)
account.balance_free(USDT)      # available for new positions
account.balance_locked(USDT)    # locked as margin
```

## Funding Rate in Backtest

```python
# GenericDataWrangler does NOT exist in v1.224.0
# Available wranglers: TradeTickDataWrangler, QuoteTickDataWrangler,
#   OrderBookDeltaDataWrangler, BarDataWrangler
# For custom data like FundingRateUpdate, construct objects directly:
funding_events = [
    FundingRateUpdate(instrument_id=inst_id, rate=rate, ts_event=ts, ts_init=ts)
    for rate, ts in funding_df.itertuples(index=False)
]
engine.add_data(funding_events)
```

Funding events process in timestamp order alongside market data.
