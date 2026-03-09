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

### Formula (FIXED)

```
mark_price = median(price_1, price_2, price_3)
where:
  price_1 = (best_bid + best_ask) / 2
  price_2 = index_price * (1 + funding_basis)
  price_3 = index_price
```

> Note: `price_1 = (best_bid + best_ask) / 2` — parentheses are critical. Without them, operator precedence yields `best_bid + (best_ask / 2)` which is wrong.

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

```python
from nautilus_trader.model.data import FundingRateUpdate

def on_start(self) -> None:
    self.subscribe_data(
        data_type=DataType(FundingRateUpdate, metadata={"instrument_id": self.config.instrument_id}),
    )

def on_data(self, data) -> None:
    if isinstance(data, FundingRateUpdate):
        rate = data.value  # e.g., 0.0001 = 1 bp per period
```

### Mechanics

| Parameter | Typical Value |
|-----------|---------------|
| Payment interval | Every 8 hours (00:00, 08:00, 16:00 UTC) |
| Rate range | -0.75% to +0.75% per period |
| Direction | Positive: longs pay shorts. Negative: shorts pay longs. |

```
funding_payment = position_notional * funding_rate
position_notional = abs(position_size) * mark_price
```

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
            if data.value > self.config.min_rate:
                # Short perp (receive funding), long spot (hedge)
                if self.portfolio.is_flat(self.config.perp_id):
                    self._short_perp()
                    self._long_spot()
```

### Basis Arbitrage

Trade futures vs spot, expecting convergence at expiry:
- **Contango** (futures > spot): Short futures, long spot
- **Backwardation** (futures < spot): Long futures, short spot

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

```python
from nautilus_trader.model.data import InstrumentStatus
from nautilus_trader.model.enums import MarketStatusAction

def on_start(self) -> None:
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
position = self.cache.position_for_instrument(self.config.instrument_id)

if position:
    initial_margin = float(position.quantity) * float(position.avg_px_open) * perp.margin_init
    maint_margin = float(position.quantity) * float(position.avg_px_open) * perp.margin_maint

account.balance_total(USDT)
account.balance_free(USDT)      # available for new positions
account.balance_locked(USDT)    # locked as margin
```

## Funding Rate in Backtest

```python
from nautilus_trader.persistence.wranglers import GenericDataWrangler

wrangler = GenericDataWrangler(FundingRateUpdate)
funding_data = wrangler.process(funding_df)
engine.add_data(funding_data)
```

Funding events process in timestamp order alongside market data.
