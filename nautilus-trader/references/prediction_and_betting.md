# Prediction & Betting Markets

BinaryOption (Polymarket), BettingInstrument (Betfair) in v1.224.0. Python only.

## BinaryOption Instrument

```python
from nautilus_trader.model.instruments import BinaryOption
from nautilus_trader.model.identifiers import InstrumentId, Symbol
from nautilus_trader.model.objects import Currency, Price, Quantity
from nautilus_trader.model.enums import AssetClass

binary = BinaryOption(
    instrument_id=InstrumentId.from_str("YES-21742.POLYMARKET"),
    raw_symbol=Symbol("YES-21742"),
    asset_class=AssetClass.ALTERNATIVE,
    currency=Currency.from_str("USDC"),
    price_precision=3,
    size_precision=2,
    price_increment=Price.from_str("0.001"),
    size_increment=Quantity.from_str("0.01"),
    activation_ns=0,
    expiration_ns=1743148800_000_000_000,
    ts_event=0, ts_init=0,
    outcome="Yes",                               # optional
    description="Will BTC reach $100k by March?", # optional, non-empty if set
)
```

Hardcoded: `margin_init=0`, `margin_maint=0`, `multiplier=1`, `is_inverse=False`.

```python
binary.outcome                  # "Yes"
binary.description              # "Will BTC reach $100k by March?"
binary.activation_utc           # pd.Timestamp (tz-aware UTC)
binary.expiration_utc           # pd.Timestamp (tz-aware UTC)
```

## Polymarket

151k+ instruments. Never use `load_all=True` without filters.

```python
from nautilus_trader.adapters.polymarket.providers import PolymarketInstrumentProviderConfig

instrument_config = PolymarketInstrumentProviderConfig(
    load_all=False,
    load_ids=frozenset({
        InstrumentId.from_str("YES-21742.POLYMARKET"),
    }),
)
```

### Execution Constraints

| Feature | Supported | Notes |
|---------|-----------|-------|
| Limit orders | Yes | |
| Market orders | Partial | BUY needs `quote_quantity=True` |
| `post_only` | **No** | |
| `reduce_only` | **No** | |
| Stop orders | **No** | |
| `modify_order` | **No** | Cancel + replace only |
| Order signing | ~1s | On-chain signature |

Prices are probabilities: `0.001` to `0.999`. WS limit: `ws_max_subscriptions_per_connection=200` (hard limit 500, auto-splits).

### Quantity Semantics (Critical)

| Order Type | Quantity Meaning |
|-----------|-----------------|
| LIMIT (buy/sell) | Conditional tokens (base units) |
| MARKET SELL | Conditional tokens (base units) |
| MARKET BUY | **USDC.e notional** (quote units) |

```python
from nautilus_trader.execution.config import ExecEngineConfig
config = ExecEngineConfig(convert_quote_qty_to_base=False)

order = strategy.order_factory.market(
    instrument_id=instrument_id,
    order_side=OrderSide.BUY,
    quantity=instrument.make_qty(10.0),
    quote_quantity=True,              # USDC.e notional
)
```

### Historical Data

```python
from nautilus_trader.adapters.polymarket import PolymarketDataLoader

loader = await PolymarketDataLoader.from_market_slug("gta-vi-released-before-june-2026")
trades = await loader.load_trades()

loaders = await PolymarketDataLoader.from_event_slug("highest-temperature-in-nyc-on-january-26")
```

### Instrument Discovery

```python
from nautilus_trader.adapters.polymarket import PolymarketInstrumentProviderConfig

instrument_config = PolymarketInstrumentProviderConfig(
    event_slug_builder="myproject.slugs:build_slugs",  # callable returning list[str]
)
```

Trade status lifecycle: `MATCHED` -> `MINED` -> `CONFIRMED`. May `RETRY` on failure.

### Config Options

| Config | Default | Purpose |
|--------|---------|---------|
| `compute_effective_deltas` | `False` | Compute deltas from snapshots |
| `drop_quotes_missing_side` | `True` | Drop QuoteTicks with missing bid/ask |
| `generate_order_history_from_trades` | `False` | Reconstruct order history |
| `use_data_api` | `False` | Use Data API instead of CLOB API |

## BettingInstrument (Betfair)

Hierarchy: event_type -> competition -> event -> market -> selection

```python
from nautilus_trader.model.instruments.betting import BettingInstrument

instrument = BettingInstrument(
    venue_name="BETFAIR",
    event_type_id=7,
    event_type_name="Horse Racing",
    competition_id=12345,
    competition_name="UK Racing",
    event_id=67890,
    event_name="3:30 Ascot",
    event_country_code="GB",
    event_open_date=datetime(2025, 3, 28, 15, 30, tzinfo=timezone.utc),
    betting_type="ODDS",
    market_id="1.234567890",
    market_name="Win",
    market_start_time=datetime(2025, 3, 28, 15, 30, tzinfo=timezone.utc),
    market_type="WIN",
    selection_id=12345678,
    selection_name="Horse A",
    currency="GBP",
    selection_handicap=0.0,
    price_precision=2, size_precision=2,
    ts_event=0, ts_init=0,
)
```

ID format: `{market_id}-{selection_id}-{handicap}.BETFAIR`

### Back/Lay Model

| NautilusTrader | Betfair |
|---------------|---------|
| `OrderSide.BUY` | Back (bet for) |
| `OrderSide.SELL` | Lay (bet against) |

Prices are decimal odds. **Back**: risk = stake, profit = stake * (odds - 1). **Lay**: risk = stake * (odds - 1), profit = stake.

### Market Version (Price Protection)

```python
exec_config = BetfairExecClientConfig(
    account_currency="GBP",
    use_market_version=True,
)
```

Betfair lapses the order if market version has advanced.

### Race Data (GPS Tracking)

```python
data_config = BetfairDataClientConfig(
    account_currency="GBP",
    subscribe_race_data=True,
    stream_conflate_ms=0,
)
```

Custom data types: `BetfairTicker`, `BetfairStartingPrice`, `BSPOrderBookDelta`.

## Event Market Patterns

```python
price = 0.60                        # 60% probability
max_loss_per_contract = price       # $0.60 if resolves NO
max_gain_per_contract = 1 - price   # $0.40 if resolves YES

edge = expected_prob - price
kelly_fraction = edge / (1 - price) if edge > 0 else 0
```

Near resolution: spreads widen, liquidity drops, quote ticks may have missing sides (`drop_quotes_missing_side=True`). Monitor `expiration_utc` and close positions before resolution.

> See SKILL.md for common hallucination guards.

- [polymarket_binary_backtest.py](../examples/polymarket_binary_backtest.py)
