# Options & Greeks

Option instrument types, greeks calculation, and Black-Scholes functions in NautilusTrader v1.224.0.

> *Python only — `GreeksCalculator`, Black-Scholes functions (`black_scholes_greeks`, `imply_vol_and_greeks`, `refine_vol_and_greeks`), and greeks data types are exposed via PyO3 bindings. Not available in pure-Rust mode. Instrument types (`CryptoOption`, `OptionContract`, etc.) exist in `nautilus-model` but the greeks calculation layer is Python/PyO3 only.*

## Option Instrument Types

Four option instrument types cover crypto, tradfi, spreads, and prediction markets:

| Type | Use Case | `underlying` | `size_precision` | Key Difference |
|------|----------|-------------|-------------------|----------------|
| `CryptoOption` | Crypto options (Deribit, Bybit) | `Currency` object | Configurable | `settlement_currency`, `is_inverse` |
| `OptionContract` | TradFi options (IB) | `str` | Hardcoded `0` | `exchange` (MIC), whole contracts only |
| `OptionSpread` | Multi-leg strategies (IB combos) | `str` | Hardcoded `0` | `strategy_type`, `legs()` method |
| `BinaryOption` | Prediction markets (Polymarket) | None | Configurable | `outcome`, `description`, `margin_init=0` |

All option types share: `activation_ns`, `expiration_ns`, `activation_utc` (property), `expiration_utc` (property).

### CryptoOption

For crypto exchanges (Deribit, Bybit options). Underlying is a `Currency` object.

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
    expiration_ns=1743148800000000000,                 # 2025-03-28 08:00 UTC
    price_precision=4,
    size_precision=1,
    price_increment=Price.from_str("0.0001"),
    size_increment=Quantity.from_str("0.1"),
    ts_event=0,
    ts_init=0,
    multiplier=Quantity.from_int(1),                   # default
    lot_size=Quantity.from_int(1),                     # default
)

# Key properties
option.underlying              # Currency("BTC")
option.settlement_currency     # Currency("BTC")
option.option_kind             # OptionKind.CALL
option.strike_price            # Price("100000.0")
option.expiration_utc          # pd.Timestamp (tz-aware UTC)
option.activation_utc          # pd.Timestamp (tz-aware UTC)
option.is_inverse              # True (Deribit)
```

### OptionContract

For traditional finance options (IB). Underlying is a plain string. `size_precision` hardcoded to `0` (whole contracts).

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
    multiplier=Quantity.from_int(100),                 # standard equity option
    lot_size=Quantity.from_int(1),
    underlying="AAPL",                                 # str, not Currency
    option_kind=OptionKind.CALL,
    strike_price=Price.from_str("150.00"),
    activation_ns=0,
    expiration_ns=1686902400000000000,
    ts_event=0,
    ts_init=0,
    exchange="CBOE",                                   # ISO 10383 MIC (optional)
)

# Hardcoded: size_precision=0, size_increment=1, min_quantity=1
contract.exchange               # "CBOE"
contract.underlying             # "AAPL"
```

### OptionSpread

Multi-leg option strategies. Has `legs()` method returning component instruments.

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
    activation_ns=0,
    expiration_ns=1686902400000000000,
    ts_event=0,
    ts_init=0,
    exchange="CBOE",
)

# legs() returns list[tuple[InstrumentId, int]] (instrument_id, ratio)
# Parses from generic spread ID format if applicable, else [(self.id, 1)]
spread.legs()
spread.strategy_type            # "BULL_CALL_SPREAD"
```

### BinaryOption

For prediction markets (Polymarket). No strike price, no option_kind.

```python
from nautilus_trader.model.instruments import BinaryOption
from nautilus_trader.model.enums import AssetClass

binary = BinaryOption(
    instrument_id=InstrumentId.from_str("YES-21742-WILL-X-HAPPEN.POLYMARKET"),
    raw_symbol=Symbol("YES-21742-WILL-X-HAPPEN"),
    asset_class=AssetClass.ALTERNATIVE,
    currency=Currency.from_str("USDC"),
    price_precision=3,
    size_precision=2,
    price_increment=Price.from_str("0.001"),
    size_increment=Quantity.from_str("0.01"),
    activation_ns=0,
    expiration_ns=1743148800000000000,
    ts_event=0,
    ts_init=0,
    outcome="Yes",                                     # optional
    description="Will X happen before March 2025?",    # optional, must be non-empty if provided
)

# Hardcoded in constructor: margin_init=0, margin_maint=0, multiplier=1, is_inverse=False
binary.outcome                  # "Yes"
binary.description              # "Will X happen before March 2025?"
```

See [prediction_and_betting.md](prediction_and_betting.md) for Polymarket/Betfair deep dives.

## Greeks Calculator

`GreeksCalculator` computes instrument and portfolio greeks using Black-Scholes. Accessible from any Strategy or Actor via the cache and clock.

```python
from nautilus_trader.model.greeks import GreeksCalculator

# In Strategy.on_start():
self.greeks_calc = GreeksCalculator(
    cache=self.cache,
    clock=self.clock,
)
```

**Constructor**: `GreeksCalculator(cache: CacheFacade, clock: Clock)` — only two required args.

### instrument_greeks()

Computes greeks for a single instrument (quantity=1).

```python
greeks = self.greeks_calc.instrument_greeks(
    instrument_id=InstrumentId.from_str("BTC-28MAR25-100000-C.DERIBIT"),
    flat_interest_rate=0.0425,     # default, used if no yield curve in cache
    flat_dividend_yield=None,       # used if no dividend curve in cache
    spot_shock=0.0,                 # shock to underlying price
    vol_shock=0.0,                  # shock to implied volatility
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

**Returns**: `GreeksData | None` (None if instrument or prices not found in cache).

**Requirements**: The instrument and its underlying must have prices in cache (via subscriptions). The calculator uses `cache.price(id, PriceType.MID)` first, falling back to `PriceType.LAST`.

**For non-option instruments** (futures, equities): returns a `GreeksData` with delta=1 (or beta-adjusted), gamma=0, vega=0, theta=0.

### portfolio_greeks()

Aggregates greeks across all open positions matching filter criteria.

```python
portfolio = self.greeks_calc.portfolio_greeks(
    underlyings=["BTC"],            # filter by underlying prefix
    venue=Venue("DERIBIT"),         # filter by venue
    instrument_id=None,             # filter by specific instrument
    strategy_id=None,               # filter by strategy
    side=PositionSide.NO_POSITION_SIDE,  # filter by side
    flat_interest_rate=0.0425,
    spot_shock=0.0,                 # apply to all positions
    vol_shock=0.0,
    time_to_expiry_shock=0.0,
    percent_greeks=False,
    index_instrument_id=None,
    beta_weights=None,
    greeks_filter=None,             # callable to filter individual greeks
)
```

**Returns**: `PortfolioGreeks` with aggregated pnl, price, delta, gamma, vega, theta.

### Shock Scenarios

Apply shocks to stress-test positions:

```python
# +5% spot shock, +2% vol shock
stressed = self.greeks_calc.portfolio_greeks(
    underlyings=["BTC"],
    spot_shock=5000.0,              # absolute shock to underlying
    vol_shock=0.02,                 # absolute shock to vol (2 vol points)
    time_to_expiry_shock=1/365.25,  # 1 day forward in years
)
```

### Beta-Weighted Greeks

Normalize delta/gamma to an index:

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

Per-instrument greeks result. Uses `@customdataclass` decorator.

```python
from nautilus_trader.model.greeks_data import GreeksData

# Constructor (positional ts_event, ts_init, then keyword fields):
greeks = GreeksData(
    ts_event,                       # int — nanoseconds
    ts_init,                        # int — nanoseconds
    instrument_id=instrument_id,
    is_call=True,
    strike=100000.0,
    expiry=20250328,                # int YYYYMMDD format
    expiry_in_days=30,
    expiry_in_years=0.082,
    multiplier=1.0,
    quantity=1.0,
    underlying_price=95000.0,
    interest_rate=0.0425,
    cost_of_carry=0.0,
    vol=0.65,                       # implied volatility (decimal, not %)
    pnl=0.0,
    price=5200.0,                   # option theoretical price
    delta=0.45,
    gamma=0.002,
    vega=150.0,
    theta=-25.0,
    itm_prob=0.42,                  # P(phi * S_T > phi * K)
)

# Helper: create from delta only (for non-option instruments)
GreeksData.from_delta(instrument_id, delta=1.0, multiplier=50.0, ts_event=0)

# Convert to portfolio-scaled greeks (multiplied by instrument multiplier)
portfolio_greeks = greeks.to_portfolio_greeks()  # → PortfolioGreeks

# Multiply by quantity: quantity * greeks → PortfolioGreeks
position_greeks = 5.0 * greeks
```

### PortfolioGreeks

Aggregated portfolio-level greeks. Supports addition and scalar multiplication.

```python
from nautilus_trader.model.greeks_data import PortfolioGreeks

pg = PortfolioGreeks(
    ts_event, ts_init,
    pnl=0.0,
    price=0.0,
    delta=0.0,
    gamma=0.0,
    vega=0.0,
    theta=0.0,
)

# Arithmetic:
total = pg1 + pg2               # aggregates all fields
scaled = 2.0 * pg               # scales all fields
```

### YieldCurveData

Interest rate curve for accurate greeks calculation. Stored in cache.

```python
from nautilus_trader.model.greeks_data import YieldCurveData
import numpy as np

curve = YieldCurveData(
    ts_event=0,
    ts_init=0,
    curve_name="USD",
    tenors=np.array([0.25, 0.5, 1.0, 2.0, 5.0]),
    interest_rates=np.array([0.045, 0.044, 0.043, 0.041, 0.039]),
)

# Callable — interpolates rate for given tenor:
rate = curve(1.5)               # quadratic interpolation → ~0.042

# Add to cache (used by GreeksCalculator automatically):
# cache.add_yield_curve(curve)  — keyed by curve_name (e.g., "USD")
```

The `GreeksCalculator` automatically looks up yield curves from cache:
- `cache.yield_curve(currency)` for interest rates
- `cache.yield_curve(str(underlying_instrument_id))` for dividend yields

## Black-Scholes Functions (Rust)

Three Rust-implemented BS functions exposed via `nautilus_pyo3`:

```python
from nautilus_trader.core.nautilus_pyo3 import (
    black_scholes_greeks,
    imply_vol_and_greeks,
    refine_vol_and_greeks,
)
```

### black_scholes_greeks

Compute greeks from known volatility:

```python
result = black_scholes_greeks(
    spot=100.0,                     # underlying price
    interest_rate=0.05,             # risk-free rate
    cost_of_carry=0.05,             # r - dividend_yield (0 for options on futures)
    vol=0.20,                       # implied volatility
    is_call=True,                   # True=call, False=put
    strike=100.0,
    time_to_expiry=1.0,             # in years
)
# Returns BlackScholesGreeksResult with fields:
result.price      # 10.45 — theoretical option price
result.delta      # 0.637
result.gamma      # 0.019
result.vega       # 0.375 — per 1% vol change / 100
result.theta      # -0.018 — per year / 365.25
result.itm_prob   # P(finish ITM)
result.vol        # 0.20 — same as input
```

### imply_vol_and_greeks

Compute implied volatility from market price, then greeks:

```python
result = imply_vol_and_greeks(
    spot=100.0,
    interest_rate=0.05,
    cost_of_carry=0.05,
    is_call=True,
    strike=100.0,
    time_to_expiry=1.0,
    option_price=10.45,             # market price → solve for vol
)
result.vol        # implied volatility
result.delta      # greeks computed at implied vol
```

### refine_vol_and_greeks

Update implied vol from a previous estimate (faster convergence):

```python
result = refine_vol_and_greeks(
    spot=100.0,
    interest_rate=0.05,
    cost_of_carry=0.05,
    is_call=True,
    strike=100.0,
    time_to_expiry=1.0,
    option_price=10.50,             # new market price
    initial_vol=0.20,               # previous vol estimate
)
# Returns None if refinement fails — fall back to imply_vol_and_greeks
```

## Cache Integration

The greeks system integrates with the NautilusTrader cache:

| Method | Purpose |
|--------|---------|
| `cache.greeks(instrument_id)` | Retrieve cached GreeksData |
| `cache.add_greeks(greeks_data)` | Store GreeksData in cache |
| `cache.yield_curve(name)` | Retrieve YieldCurveData by currency/name |
| `cache.index_price(instrument_id)` | Get index price for index instruments |

The `GreeksCalculator` uses these automatically:
- Checks `yield_curve(currency)` for interest rates before falling back to `flat_interest_rate`
- Checks `yield_curve(underlying_id)` for dividend yields before falling back to `flat_dividend_yield`
- Uses `cache_greeks=True` / `use_cached_greeks=True` for caching greeks between calculations

## Anti-Hallucination Notes

These do **NOT** exist in v1.224.0:

| Hallucination | Reality |
|--------------|---------|
| `subscribe_option_greeks()` | Does not exist on Strategy — use `GreeksCalculator` manually |
| `subscribe_option_chain()` | Does not exist — load options via `InstrumentProviderConfig(load_all=True)` |
| `OptionChainSlice` / `StrikeRange` | Do not exist |
| `on_option_greeks()` handler | Does not exist |
| `GreeksCalculator(cache, clock, logger)` | Only 2 args: `GreeksCalculator(cache, clock)` — logger created internally |
| `OptionGreeks` data type | Named `GreeksData` (from `nautilus_trader.model.greeks_data`) |
| `GreeksData.delta` as property | It's a plain field on a `@customdataclass` |
| `black_scholes_greeks(..., vol, is_call)` order | Correct order: `spot, rate, cost_of_carry, vol, is_call, strike, time` |
| `vol=65` (percentage) | Must be decimal: `vol=0.65` — not percentage |
| `CryptoOption.underlying` is `str` | It's `Currency` object: `Currency.from_str("BTC")` |
| `OptionContract.underlying` is `Currency` | It's `str`: `underlying="AAPL"` |

## Import Paths

```python
# Instruments
from nautilus_trader.model.instruments import CryptoOption, OptionContract, OptionSpread, BinaryOption

# Enums
from nautilus_trader.model.enums import OptionKind, AssetClass

# Greeks calculator
from nautilus_trader.model.greeks import GreeksCalculator

# Data types
from nautilus_trader.model.greeks_data import GreeksData, PortfolioGreeks, YieldCurveData

# BS functions
from nautilus_trader.core.nautilus_pyo3 import black_scholes_greeks, imply_vol_and_greeks, refine_vol_and_greeks
```
