# Prediction & Betting Markets

BinaryOption (Polymarket), BettingInstrument (Betfair), and event market patterns in NautilusTrader v1.224.0.

> *Python only — Polymarket and Betfair adapters are Python/Cython only. No Rust equivalents exist.*

## BinaryOption Instrument

Used for prediction markets like Polymarket. A binary outcome (YES/NO) that resolves to 0 or 1.

```python
from nautilus_trader.model.instruments import BinaryOption
from nautilus_trader.model.identifiers import InstrumentId, Symbol
from nautilus_trader.model.objects import Currency, Price, Quantity
from nautilus_trader.model.enums import AssetClass

binary = BinaryOption(
    instrument_id=InstrumentId.from_str("YES-21742.POLYMARKET"),
    raw_symbol=Symbol("YES-21742"),
    asset_class=AssetClass.ALTERNATIVE,         # prediction markets
    currency=Currency.from_str("USDC"),          # settlement currency
    price_precision=3,                           # 0.001 ticks
    size_precision=2,
    price_increment=Price.from_str("0.001"),
    size_increment=Quantity.from_str("0.01"),
    activation_ns=0,
    expiration_ns=1743148800_000_000_000,
    ts_event=0,
    ts_init=0,
    outcome="Yes",                               # optional — "Yes", "No", or custom
    description="Will BTC reach $100k by March?", # optional, must be non-empty if provided
)
```

### Constructor Details

| Parameter | Type | Required | Notes |
|-----------|------|----------|-------|
| `instrument_id` | `InstrumentId` | Yes | |
| `raw_symbol` | `Symbol` | Yes | |
| `asset_class` | `AssetClass` | Yes | Typically `ALTERNATIVE` |
| `currency` | `Currency` | Yes | Quote/settlement currency (USDC for Polymarket) |
| `price_precision` | `int` | Yes | |
| `size_precision` | `int` | Yes | |
| `price_increment` | `Price` | Yes | |
| `size_increment` | `Quantity` | Yes | |
| `activation_ns` | `uint64` | Yes | Contract activation timestamp |
| `expiration_ns` | `uint64` | Yes | Contract expiration timestamp |
| `ts_event` | `uint64` | Yes | |
| `ts_init` | `uint64` | Yes | |
| `outcome` | `str` | No | Binary outcome label |
| `description` | `str` | No | Market description (must be non-empty if set) |

**Hardcoded in constructor**: `margin_init=0`, `margin_maint=0`, `multiplier=1`, `is_inverse=False`, `instrument_class=BINARY_OPTION`.

### Fields

```python
binary.outcome                  # "Yes"
binary.description              # "Will BTC reach $100k by March?"
binary.activation_utc           # pd.Timestamp (tz-aware UTC)
binary.expiration_utc           # pd.Timestamp (tz-aware UTC)
binary.margin_init              # Decimal(0) — always 0, no margin
binary.quote_currency           # Currency("USDC")
```

## Polymarket Deep Dive

### Instrument Loading

Polymarket has 151k+ instruments. Never use `load_all=True` without filters.

```python
from nautilus_trader.adapters.polymarket.providers import PolymarketInstrumentProviderConfig

instrument_config = PolymarketInstrumentProviderConfig(
    # Use filters to load specific markets
    load_all=False,
    load_ids=frozenset({
        InstrumentId.from_str("YES-21742.POLYMARKET"),
    }),
)
```

### Execution Constraints

| Feature | Supported | Notes |
|---------|-----------|-------|
| Limit orders | Yes | Standard limit orders |
| Market orders | Partial | Market BUY may need `quote_quantity=True` |
| `post_only` | **No** | Not available |
| `reduce_only` | **No** | Not available |
| Stop orders | **No** | Not available |
| `modify_order` | **No** | Cancel + replace only |
| Order signing | ~1s latency | On-chain signature required |

### Price Range

Prices represent probabilities: `0.001` to `0.999`. Buying YES at 0.60 means paying $0.60 for a contract that pays $1.00 if the outcome is "Yes".

### WebSocket Limits

`ws_max_subscriptions_per_connection=200` (default). Polymarket hard limit is 500. Multiple connections are created automatically when subscriptions exceed the per-connection limit.

### Quantity Semantics (Critical)

| Order Type | Quantity Meaning |
|-----------|-----------------|
| LIMIT (buy/sell) | Conditional tokens (base units) |
| MARKET SELL | Conditional tokens (base units) |
| MARKET BUY | **USDC.e notional** (quote units) |

Market BUY requires special config:

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

### Historical Data Loading

```python
from nautilus_trader.adapters.polymarket import PolymarketDataLoader

loader = await PolymarketDataLoader.from_market_slug(
    "gta-vi-released-before-june-2026"
)
trades = await loader.load_trades()

# Event-based (multiple markets)
loaders = await PolymarketDataLoader.from_event_slug(
    "highest-temperature-in-nyc-on-january-26"
)
```

### Instrument Discovery

```python
from nautilus_trader.adapters.polymarket import PolymarketInstrumentProviderConfig

# Use event slug builder for dynamic market discovery
instrument_config = PolymarketInstrumentProviderConfig(
    event_slug_builder="myproject.slugs:build_slugs",  # callable returning list[str]
)
```

### Fees

Fee structure varies by market type — some markets have zero fees, others (e.g., short-duration crypto markets) have tiered maker/taker fees. Check the Polymarket docs for current fee schedules.

### Trade Status Lifecycle

`MATCHED` → `MINED` → `CONFIRMED`. May `RETRY` on failure.

### Config Options

| Config | Default | Purpose |
|--------|---------|---------|
| `compute_effective_deltas` | `False` | Compute deltas from snapshots (~1ms overhead) |
| `drop_quotes_missing_side` | `True` | Drop QuoteTicks with missing bid/ask (near resolution) |
| `generate_order_history_from_trades` | `False` | Experimental: reconstruct order history from trades |
| `use_data_api` | `False` | Use Data API instead of CLOB API for positions |

## BettingInstrument (Betfair)

Full event hierarchy instrument for sports betting markets.

```python
from nautilus_trader.model.instruments.betting import BettingInstrument

# BettingInstrument has a deep hierarchy:
# event_type (Sport) → competition → event → market → selection

# Constructor requires many fields:
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
    price_precision=2,
    size_precision=2,
    ts_event=0,
    ts_init=0,
)
```

### Hierarchy Fields

| Level | Fields |
|-------|--------|
| Event Type | `event_type_id`, `event_type_name` (e.g., Horse Racing, Football) |
| Competition | `competition_id`, `competition_name` (e.g., Premier League) |
| Event | `event_id`, `event_name`, `event_country_code`, `event_open_date` |
| Market | `market_id`, `market_name`, `market_type`, `market_start_time`, `betting_type` |
| Selection | `selection_id`, `selection_name`, `selection_handicap` |

### Instrument ID Format

`{market_id}-{selection_id}-{handicap}.BETFAIR`

The symbol is auto-generated from `market_id`, `selection_id`, and `selection_handicap`.

### Back/Lay Model

| NautilusTrader | Betfair | Meaning |
|---------------|---------|---------|
| `OrderSide.BUY` | Back | Bet for the outcome |
| `OrderSide.SELL` | Lay | Bet against the outcome |

Prices are decimal odds (e.g., 3.5 means "3.5 to 1"). Your liability differs for back vs lay:
- **Back**: Risk = stake. Profit = stake × (odds - 1)
- **Lay**: Risk = stake × (odds - 1). Profit = stake

### Market Version (Price Protection)

```python
exec_config = BetfairExecClientConfig(
    account_currency="GBP",
    use_market_version=True,    # attach market version to orders
)
```

When enabled, orders include the latest market version. If the market has moved (version advanced beyond the one sent), Betfair lapses the order rather than matching against changed prices.

### Race Data (GPS Tracking)

```python
data_config = BetfairDataClientConfig(
    account_currency="GBP",
    subscribe_race_data=True,       # Race Change Messages with GPS data
    stream_conflate_ms=0,           # no conflation for full tick stream
)
```

### Custom Data Types

- `BetfairTicker` — market-level tick data
- `BetfairStartingPrice` — BSP (Betfair Starting Price) data
- `BSPOrderBookDelta` — BSP-specific book updates

## Event Market Patterns

### Position Sizing for Binary Markets

Binary options have a max payoff of 1.0. Position size is denominated in contracts, where each contract pays $1.00 at resolution:

```python
# Risk management for binary markets
price = 0.60                        # 60% probability
max_loss_per_contract = price       # $0.60 if resolves NO
max_gain_per_contract = 1 - price   # $0.40 if resolves YES

# Kelly-style sizing
edge = expected_prob - price
kelly_fraction = edge / (1 - price) if edge > 0 else 0
```

### Resolution Handling

Binary options resolve to exactly `0` or `1`. Near resolution:
- Spreads widen significantly
- Liquidity drops
- Quote ticks may have missing sides (`drop_quotes_missing_side=True` handles this)

Monitor `expiration_utc` and reduce/close positions before resolution if the strategy isn't designed to hold through resolution.

## Anti-Hallucination Notes

| Hallucination | Reality |
|--------------|---------|
| `load_all=True` for Polymarket | Dangerous — 151k+ instruments. Always use filters (`load_ids`, `load_conditions`) |
| `post_only` on Polymarket | Not available |
| `reduce_only` on Polymarket | Not available |
| Stop orders on Polymarket | Not available |
| `modify_order` on Polymarket | Not supported — cancel + replace only |
| `BinaryOption.margin_init` matters | Always `Decimal(0)` — no margin on binary options |
