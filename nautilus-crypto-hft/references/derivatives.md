# Derivatives

CryptoPerpetual, CryptoFuture, mark price, funding rates, liquidation, and circuit breakers in NautilusTrader.

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

### Comparison

| Feature | CryptoPerpetual | CryptoFuture |
|---------|----------------|--------------|
| Expiry | None | Fixed settlement date |
| Funding | Every 8h (typically) | None |
| Price anchor | Funding rate | Convergence at expiry |
| Basis | Funding premium | Contango/backwardation |

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

## Circuit Breakers

**NOTE**: `subscribe_instrument_status()` is NOT IMPLEMENTED on Binance adapter (v1.224.0).
The on_instrument_status callback will never fire. Monitor via REST or external feeds.

```python
from nautilus_trader.model.data import InstrumentStatus
from nautilus_trader.model.enums import MarketStatusAction

def on_start(self) -> None:
    # WARNING: NotImplementedError on Binance — won't receive events
    self.subscribe_instrument_status(self.config.instrument_id)
    self._halted = False

def on_instrument_status(self, status: InstrumentStatus) -> None:
    if status.action == MarketStatusAction.HALT:
        self._halted = True
        self.cancel_all_orders(self.config.instrument_id)
    elif status.action == MarketStatusAction.RESUME:
        self._halted = False
```

| Trigger | Description |
|---------|-------------|
| Price limit | Price moves beyond daily limit (±10%) |
| Volatility | Rapid movement triggers cooldown |
| Maintenance | Scheduled exchange maintenance |

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
