# Derivatives

## Instrument Types

### CryptoPerpetual

Perpetual futures with no expiry. Funding rate mechanism anchors price to spot.

```python
from nautilus_trader.model.instruments import CryptoPerpetual

# Loaded from venue adapter, not constructed manually
perp = cache.instrument(InstrumentId.from_str("BTCUSDT-PERP.BINANCE"))

# Key properties
perp.base_currency       # BTC
perp.quote_currency      # USDT
perp.settlement_currency # USDT
perp.is_inverse          # False for linear, True for inverse (coin-margined)
perp.multiplier          # Contract multiplier
perp.lot_size            # Minimum order size increment
perp.max_quantity         # Maximum order size
perp.min_quantity         # Minimum order size
perp.margin_init          # Initial margin rate (e.g., 0.01 = 100x max leverage)
perp.margin_maint         # Maintenance margin rate
```

### CryptoFuture

Expiring futures contracts with settlement date.

```python
from nautilus_trader.model.instruments import CryptoFuture

future = cache.instrument(InstrumentId.from_str("BTCUSDT-250328.BINANCE"))

# Additional properties vs perpetual
future.expiration           # Expiration datetime
future.activation           # When contract becomes tradeable
```

### Key Differences

| Feature | CryptoPerpetual | CryptoFuture |
|---------|----------------|--------------|
| Expiry | None (perpetual) | Fixed settlement date |
| Funding | Every 8h (typically) | None |
| Price anchor | Funding rate | Convergence to spot at expiry |
| Basis | Funding rate premium | Contango/backwardation |

## Mark Price

Mark price is used for liquidation calculations and unrealized PnL, not for order matching.

### MarkPriceUpdate

```python
from nautilus_trader.model.data import MarkPriceUpdate

# Received via data subscription
def on_start(self) -> None:
    self.subscribe_data(
        data_type=DataType(MarkPriceUpdate, metadata={"instrument_id": self.config.instrument_id}),
    )

def on_data(self, data) -> None:
    if isinstance(data, MarkPriceUpdate):
        mark_price = data.value
        self.log.info(f"Mark price: {mark_price}")
```

**Mark price formula** (typical):
```
mark_price = median(price_1, price_2, price_3)
where:
  price_1 = best_bid + best_ask / 2
  price_2 = index_price * (1 + funding_basis)
  price_3 = index_price
```

Mark price vs last price:
- **Last price**: Most recent trade execution price
- **Mark price**: Fair value estimate, resistant to manipulation
- **Index price**: Weighted average of spot prices across major exchanges

## Funding Rate

Perpetual contracts use funding payments to keep price aligned with spot index.

### FundingRateUpdate

```python
from nautilus_trader.model.data import FundingRateUpdate

def on_start(self) -> None:
    self.subscribe_data(
        data_type=DataType(FundingRateUpdate, metadata={"instrument_id": self.config.instrument_id}),
    )

def on_data(self, data) -> None:
    if isinstance(data, FundingRateUpdate):
        rate = data.value   # e.g., 0.0001 = 1 bp per period
        self.log.info(f"Funding rate: {rate}")
```

### Funding Mechanics

| Parameter | Typical Value |
|-----------|---------------|
| Payment interval | Every 8 hours (00:00, 08:00, 16:00 UTC) |
| Rate range | -0.75% to +0.75% per period |
| Settlement | Deducted/credited to margin balance |
| Direction | Positive rate: longs pay shorts. Negative: shorts pay longs. |

**Payment calculation**:
```
funding_payment = position_notional * funding_rate
position_notional = abs(position_size) * mark_price
```

### Funding Arbitrage Pattern

Harvest funding payments while hedging directional risk:

```python
class FundingArbitrageConfig(StrategyConfig, frozen=True):
    perp_instrument_id: InstrumentId   # BTCUSDT-PERP.BINANCE
    spot_instrument_id: InstrumentId   # BTCUSDT.BINANCE
    trade_size: Decimal
    min_funding_rate: float = 0.0003   # minimum rate to enter (3 bps)

class FundingArbitrage(Strategy):
    def on_data(self, data) -> None:
        if isinstance(data, FundingRateUpdate):
            rate = data.value
            if rate > self.config.min_funding_rate:
                # Positive funding: short perp (receive funding), long spot (hedge)
                if self.portfolio.is_flat(self.config.perp_instrument_id):
                    self._short_perp()
                    self._long_spot()
            elif rate < -self.config.min_funding_rate:
                # Negative funding: long perp (receive funding), short spot (hedge)
                if self.portfolio.is_flat(self.config.perp_instrument_id):
                    self._long_perp()
                    self._short_spot()
```

### Basis Arbitrage Pattern

Trade the spread between futures and spot, expecting convergence at expiry:

```python
class BasisArbitrageConfig(StrategyConfig, frozen=True):
    future_instrument_id: InstrumentId   # BTCUSDT-250328.BINANCE
    spot_instrument_id: InstrumentId     # BTCUSDT.BINANCE
    trade_size: Decimal
    entry_basis_bps: float = 50.0        # enter when basis > 50 bps
    exit_basis_bps: float = 5.0          # exit when basis < 5 bps
```

**Contango** (futures > spot): Short futures, long spot → profit as basis narrows.
**Backwardation** (futures < spot): Long futures, short spot → profit as basis narrows.

## Liquidation Mechanics

Liquidation is triggered by mark price, not last trade price.

### How Liquidation Works

1. **Mark price** moves against position
2. **Margin ratio** = maintenance_margin / margin_balance
3. When margin ratio >= 100%, **liquidation triggers**
4. Exchange takes over position: attempts to close at market
5. If position closed above bankruptcy price → excess goes to **insurance fund**
6. If position cannot close above bankruptcy price → **auto-deleveraging (ADL)** kicks in

### Liquidation Price Estimation

```
# Long position
liquidation_price = entry_price * (1 - initial_margin_rate + maintenance_margin_rate)

# Short position
liquidation_price = entry_price * (1 + initial_margin_rate - maintenance_margin_rate)
```

### Auto-Deleveraging (ADL)

When insurance fund is depleted, the exchange forcibly closes positions of profitable traders on the opposite side, ordered by profit ratio and leverage.

In backtesting, NautilusTrader does not simulate ADL events. Account `frozen_account=False` enforces margin checks and will reject orders that would exceed margin.

## Circuit Breakers

### InstrumentStatus

Exchanges halt trading via status changes. Handle via `on_instrument_status`:

```python
from nautilus_trader.model.data import InstrumentStatus
from nautilus_trader.model.enums import MarketStatusAction

def on_start(self) -> None:
    self.subscribe_instrument_status(self.config.instrument_id)
    self._trading_halted = False

def on_instrument_status(self, status: InstrumentStatus) -> None:
    if status.action == MarketStatusAction.HALT:
        self._trading_halted = True
        self.cancel_all_orders(self.config.instrument_id)
        self.log.warning(f"Trading halted: {self.config.instrument_id}")
    elif status.action == MarketStatusAction.RESUME:
        self._trading_halted = False
        self.log.info(f"Trading resumed: {self.config.instrument_id}")

def _should_trade(self) -> bool:
    return not self._trading_halted
```

### Common Halt Triggers

| Trigger | Description |
|---------|-------------|
| Price limit | Price moves beyond daily limit (e.g., ±10%) |
| Volatility | Rapid price movement triggers cooldown |
| Market-wide | Exchange-level halt (e.g., LULD in US equities) |
| Maintenance | Scheduled exchange maintenance |

## Position Margin Tracking

```python
# Access margin info via account
account = self.portfolio.account(Venue("BINANCE"))

# Margin for specific position
position = self.cache.position_for_instrument(self.config.instrument_id)
if position:
    # Initial margin: required to open position
    initial_margin = float(position.quantity) * float(position.avg_px_open) * perp.margin_init

    # Maintenance margin: required to keep position
    maint_margin = float(position.quantity) * float(position.avg_px_open) * perp.margin_maint

# Account-level margin
account.balance_total(USDT)
account.balance_free(USDT)      # available for new positions
account.balance_locked(USDT)    # locked as margin
```

## Funding Rate in Backtest

To include funding in backtests, provide `FundingRateUpdate` data alongside market data:

```python
from nautilus_trader.persistence.wranglers import GenericDataWrangler

# Load funding rate data as custom data type
wrangler = GenericDataWrangler(FundingRateUpdate)
funding_data = wrangler.process(funding_df)
engine.add_data(funding_data)
```

The backtest engine processes funding events in timestamp order alongside market data, allowing strategies to react to funding rate changes.
