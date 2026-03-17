# Options & Greeks

> Python only — `GreeksCalculator`, Black-Scholes functions, and greeks data types are PyO3 bindings. Instrument types exist in `nautilus-model` but greeks calculation is Python/PyO3 only.

## Option Instrument Types

| Type | Use Case | `underlying` | `size_precision` | Key Difference |
|------|----------|-------------|-------------------|----------------|
| `CryptoOption` | Crypto (Deribit, Bybit) | `Currency` object | Configurable | `settlement_currency`, `is_inverse` |
| `OptionContract` | TradFi (IB) | `str` | Hardcoded `0` | `exchange` (MIC), whole contracts only |
| `OptionSpread` | Multi-leg (IB combos) | `str` | Hardcoded `0` | `strategy_type`, `legs()` method |
| `BinaryOption` | Prediction (Polymarket) | None | Configurable | `outcome`, `description`, `margin_init=0` |

All share: `activation_ns`, `expiration_ns`, `activation_utc` (property), `expiration_utc` (property).

### CryptoOption

```python
from nautilus_trader.model.instruments import CryptoOption
from nautilus_trader.model.identifiers import InstrumentId, Symbol
from nautilus_trader.model.objects import Currency, Price, Quantity
from nautilus_trader.model.enums import OptionKind

option = CryptoOption(
    instrument_id=InstrumentId.from_str("BTC-28MAR25-100000-C.DERIBIT"),
    raw_symbol=Symbol("BTC-28MAR25-100000-C"),
    underlying=Currency.from_str("BTC"),              # Currency object, not str
    quote_currency=Currency.from_str("BTC"),
    settlement_currency=Currency.from_str("BTC"),
    is_inverse=True,                                   # Deribit options are inverse
    option_kind=OptionKind.CALL,                       # OptionKind.CALL=1, OptionKind.PUT=2
    strike_price=Price.from_str("100000.0"),
    activation_ns=0,
    expiration_ns=1743148800000000000,
    price_precision=4, size_precision=1,
    price_increment=Price.from_str("0.0001"),
    size_increment=Quantity.from_str("0.1"),
    ts_event=0, ts_init=0,
)
```

### OptionContract

```python
from nautilus_trader.model.instruments import OptionContract
from nautilus_trader.model.enums import AssetClass, OptionKind

contract = OptionContract(
    instrument_id=InstrumentId.from_str("AAPL230616C00150000.CBOE"),
    raw_symbol=Symbol("AAPL230616C00150000"),
    asset_class=AssetClass.EQUITY,
    currency=Currency.from_str("USD"),
    price_precision=2,
    price_increment=Price.from_str("0.01"),
    multiplier=Quantity.from_int(100),
    lot_size=Quantity.from_int(1),
    underlying="AAPL",                                 # str, not Currency
    option_kind=OptionKind.CALL,
    strike_price=Price.from_str("150.00"),
    activation_ns=0, expiration_ns=1686902400000000000,
    ts_event=0, ts_init=0,
    exchange="CBOE",                                   # ISO 10383 MIC (optional)
)
# Hardcoded: size_precision=0, size_increment=1, min_quantity=1
```

### OptionSpread

```python
from nautilus_trader.model.instruments import OptionSpread

spread = OptionSpread(
    instrument_id=InstrumentId.from_str("SPX_BULL_CALL.CBOE"),
    raw_symbol=Symbol("SPX_BULL_CALL"),
    asset_class=AssetClass.INDEX,
    currency=Currency.from_str("USD"),
    price_precision=2,
    price_increment=Price.from_str("0.05"),
    multiplier=Quantity.from_int(100),
    lot_size=Quantity.from_int(1),
    underlying="SPX",
    strategy_type="BULL_CALL_SPREAD",                  # required, non-empty str
    activation_ns=0, expiration_ns=1686902400000000000,
    ts_event=0, ts_init=0,
    exchange="CBOE",
)
# legs() returns list[tuple[InstrumentId, int]] (instrument_id, ratio)
```

### BinaryOption

```python
from nautilus_trader.model.instruments import BinaryOption
from nautilus_trader.model.enums import AssetClass

binary = BinaryOption(
    instrument_id=InstrumentId.from_str("YES-21742-WILL-X-HAPPEN.POLYMARKET"),
    raw_symbol=Symbol("YES-21742-WILL-X-HAPPEN"),
    asset_class=AssetClass.ALTERNATIVE,
    currency=Currency.from_str("USDC"),
    price_precision=3, size_precision=2,
    price_increment=Price.from_str("0.001"),
    size_increment=Quantity.from_str("0.01"),
    activation_ns=0, expiration_ns=1743148800000000000,
    ts_event=0, ts_init=0,
    outcome="Yes",                                     # optional
    description="Will X happen before March 2025?",    # optional, non-empty if provided
)
# Hardcoded: margin_init=0, margin_maint=0, multiplier=1, is_inverse=False
```

See [prediction_and_betting.md](prediction_and_betting.md) for Polymarket/Betfair.

## Greeks Calculator

Constructor: `GreeksCalculator(cache: CacheFacade, clock: Clock)`

```python
from nautilus_trader.model.greeks import GreeksCalculator
self.greeks_calc = GreeksCalculator(cache=self.cache, clock=self.clock)
```

### instrument_greeks()

Returns `GreeksData | None`. Requires instrument and underlying prices in cache (`cache.price(id, PriceType.MID)`, fallback `PriceType.LAST`). Non-option instruments: delta=1, gamma/vega/theta=0.

```python
greeks = self.greeks_calc.instrument_greeks(
    instrument_id=InstrumentId.from_str("BTC-28MAR25-100000-C.DERIBIT"),
    flat_interest_rate=0.0425,     # used if no yield curve in cache
    flat_dividend_yield=None,       # used if no dividend curve in cache
    spot_shock=0.0,                 # absolute shock to underlying price
    vol_shock=0.0,                  # absolute shock to implied vol
    time_to_expiry_shock=0.0,       # shock in years
    use_cached_greeks=False,        # use cache.greeks() if available
    update_vol=False,               # refine vol from cached greeks
    cache_greeks=False,             # store result in cache.add_greeks()
    percent_greeks=False,           # greeks as % of underlying price
    index_instrument_id=None,       # for beta-weighted greeks
    beta_weights=None,              # dict[InstrumentId, float]
    vega_time_weight_base=None,     # time-weight vega by sqrt(base/expiry_days)
)
```

### portfolio_greeks()

Returns `PortfolioGreeks` (aggregated pnl, price, delta, gamma, vega, theta).

```python
portfolio = self.greeks_calc.portfolio_greeks(
    underlyings=["BTC"],            # filter by underlying prefix
    venue=Venue("DERIBIT"),         # filter by venue
    instrument_id=None, strategy_id=None,
    side=PositionSide.NO_POSITION_SIDE,
    flat_interest_rate=0.0425,
    spot_shock=0.0, vol_shock=0.0, time_to_expiry_shock=0.0,
    percent_greeks=False,
    index_instrument_id=None, beta_weights=None,
    greeks_filter=None,             # callable to filter individual greeks
)
```

### Shock Scenarios

```python
stressed = self.greeks_calc.portfolio_greeks(
    underlyings=["BTC"],
    spot_shock=5000.0,              # absolute shock to underlying
    vol_shock=0.02,                 # absolute shock (2 vol points)
    time_to_expiry_shock=1/365.25,  # 1 day forward in years
)
```

### Beta-Weighted Greeks

```python
index_id = InstrumentId.from_str("SPX.CBOE")
betas = {
    InstrumentId.from_str("AAPL.XNAS"): 1.2,
    InstrumentId.from_str("MSFT.XNAS"): 0.9,
}
portfolio = self.greeks_calc.portfolio_greeks(
    underlyings=["AAPL", "MSFT"],
    index_instrument_id=index_id,
    beta_weights=betas,
)
# portfolio.delta is now beta-weighted to SPX
```

## Greeks Data Types

### GreeksData

`@customdataclass` — positional `ts_event`, `ts_init`, then keyword fields:

```python
from nautilus_trader.model.greeks_data import GreeksData

greeks = GreeksData(
    ts_event, ts_init,              # int (nanoseconds)
    instrument_id=instrument_id,
    is_call=True, strike=100000.0,
    expiry=20250328,                # int YYYYMMDD
    expiry_in_days=30, expiry_in_years=0.082,
    multiplier=1.0, quantity=1.0,
    underlying_price=95000.0,
    interest_rate=0.0425, cost_of_carry=0.0,
    vol=0.65,                       # decimal, not %
    pnl=0.0, price=5200.0,
    delta=0.45, gamma=0.002, vega=150.0, theta=-25.0,
    itm_prob=0.42,
)

GreeksData.from_delta(instrument_id, delta=1.0, multiplier=50.0, ts_event=0)
greeks.to_portfolio_greeks()  # multiplied by instrument multiplier
5.0 * greeks                  # quantity * greeks → PortfolioGreeks
```

### PortfolioGreeks

```python
from nautilus_trader.model.greeks_data import PortfolioGreeks

pg = PortfolioGreeks(ts_event, ts_init, pnl=0.0, price=0.0, delta=0.0, gamma=0.0, vega=0.0, theta=0.0)
total = pg1 + pg2               # aggregates all fields
scaled = 2.0 * pg               # scales all fields
```

### YieldCurveData

```python
from nautilus_trader.model.greeks_data import YieldCurveData
import numpy as np

curve = YieldCurveData(
    ts_event=0, ts_init=0,
    curve_name="USD",
    tenors=np.array([0.25, 0.5, 1.0, 2.0, 5.0]),
    interest_rates=np.array([0.045, 0.044, 0.043, 0.041, 0.039]),
)
rate = curve(1.5)               # quadratic interpolation → ~0.042
```

## Cache Integration

| Method | Purpose |
|--------|---------|
| `cache.greeks(instrument_id)` | Retrieve cached GreeksData |
| `cache.add_greeks(greeks_data)` | Store GreeksData in cache |
| `cache.yield_curve(name)` | Retrieve YieldCurveData by currency/name |
| `cache.index_price(instrument_id)` | Get index price for index instruments |

Yield curve lookup: `cache.yield_curve(currency)` for interest rates, `cache.yield_curve(str(underlying_instrument_id))` for dividend yields. Falls back to `flat_interest_rate` / `flat_dividend_yield`.

## Black-Scholes Functions (Rust)

```python
from nautilus_trader.core.nautilus_pyo3 import (
    black_scholes_greeks, imply_vol_and_greeks, refine_vol_and_greeks,
)
```

### black_scholes_greeks

```python
result = black_scholes_greeks(
    spot=100.0, interest_rate=0.05, cost_of_carry=0.05,
    vol=0.20, is_call=True, strike=100.0, time_to_expiry=1.0,
)
# BlackScholesGreeksResult fields:
result.price      # theoretical option price
result.delta      # 0.637
result.gamma      # 0.019
result.vega       # per 1% vol change / 100
result.theta      # per year / 365.25
result.itm_prob   # P(finish ITM)
result.vol        # same as input
```

### imply_vol_and_greeks

```python
result = imply_vol_and_greeks(
    spot=100.0, interest_rate=0.05, cost_of_carry=0.05,
    is_call=True, strike=100.0, time_to_expiry=1.0,
    option_price=10.45,             # market price → solve for vol
)
result.vol        # implied volatility
result.delta      # greeks computed at implied vol
```

### refine_vol_and_greeks

```python
result = refine_vol_and_greeks(
    spot=100.0, interest_rate=0.05, cost_of_carry=0.05,
    is_call=True, strike=100.0, time_to_expiry=1.0,
    option_price=10.50, initial_vol=0.20,
)
# Returns None if refinement fails — fall back to imply_vol_and_greeks
```

> See SKILL.md for common hallucination guards.