# Battle-Tested Patterns & Tricks

Non-obvious knowledge from live testing NautilusTrader v1.224.0. These patterns are verified against real exchanges and won't be found in official docs.

## Critical Ordering Rules

### on_start() must follow this exact sequence

```python
def on_start(self) -> None:
    # 1. Cache instrument FIRST — None if not loaded, crashes later
    self.instrument = self.cache.instrument(self.config.instrument_id)
    if self.instrument is None:
        self.log.error(f"Not found: {self.config.instrument_id}")
        return

    # 2. Register indicators BEFORE subscribing
    self.register_indicator_for_bars(bar_type, self.ema)

    # 3. Subscribe AFTER instrument + indicators ready
    self.subscribe_bars(bar_type)
```

Wrong order = silent failures: indicators never receive data, subscriptions produce 0 callbacks.

### Data loading order for backtest

```python
# Load multiple instruments with deferred sorting (faster)
engine.add_data(ticks_btc, sort=False)
engine.add_data(ticks_eth, sort=False)
engine.sort_data()  # single O(n log n) sort at the end
```

### Bar timestamp correction

If bar data uses opening timestamps (common in CSV exports), set `ts_init_delta` to bar duration:

```python
bars = BarDataWrangler(bar_type=bar_type, instrument=inst).process(
    data=df, ts_init_delta=60_000_000_000  # 1 minute in nanoseconds
)
```

Without this: look-ahead bias — strategy sees bar data before the bar closes.

## Execution Tricks

### modify_order > cancel+replace

- Single message, lower latency, less detectable
- But NOT supported everywhere: dYdX, Binance Spot, Polymarket don't support it
- Check venue support before using — adapter errors with no auto-fallback

### Bracket order pattern (manual)

```python
entry = self.order_factory.market(instrument_id, OrderSide.BUY, quantity)
self.submit_order(entry)

# In on_order_filled:
sl = self.order_factory.stop_market(instrument_id, OrderSide.SELL, quantity, trigger_price=sl_price)
tp = self.order_factory.limit(instrument_id, OrderSide.SELL, quantity, price=tp_price)
self.submit_order(sl)
self.submit_order(tp)
```

For Rust backtest: `support_contingent_orders = Some(true)` required in `add_venue`.

### Reconciliation delay

`reconciliation_startup_delay_secs >= 10` — lower values cause false positive "missing order" resolutions on startup.

## Actor Patterns

### Timer-based REST polling

```python
def on_start(self) -> None:
    self.clock.set_timer("poll_oi", interval=timedelta(seconds=5), callback=self._on_poll)

def _on_poll(self, event) -> None:
    self.queue_for_executor(self._fetch_open_interest)

async def _fetch_open_interest(self) -> None:
    # async HTTP call here — non-blocking
    pass
```

### Signal pipeline (Actor → Strategy)

**Actor publishes:**
```python
self.publish_signal(name="momentum", value=score, ts_event=tick.ts_event)
```

Name `"momentum"` auto-generates class `SignalMomentum` (capitalized). Values must be int/float/str — dict causes KeyError.

**Strategy receives:**
```python
def on_signal(self, signal) -> None:
    if type(signal).__name__ == "SignalMomentum":
        self.momentum = signal.value
```

### Custom data for structured payloads

When signal values need to be richer than a single number:

```python
class VPINData(Data):
    def __init__(self, vpin: float, volume: float, ts_event: int, ts_init: int):
        self.vpin = vpin
        self.volume = volume
        self._ts_event = ts_event
        self._ts_init = ts_init

    @property
    def ts_event(self) -> int: return self._ts_event
    @property
    def ts_init(self) -> int: return self._ts_init
```

Actor: `self.publish_data(data_type=DataType(VPINData), data=vpin_data)`
Strategy: subscribe in `on_start`, receive in `on_data`

## Backtest Configuration

### FillModel tuning

```python
FillModel(
    prob_fill_on_limit=0.3,   # 30% fill probability on limit orders
    prob_slippage=0.5,        # 50% chance of 1-tick slippage
    random_seed=42,           # reproducibility
)
```

No `prob_fill_on_stop` parameter exists.

### frozen_account naming is INVERTED

- `frozen_account=False` → margin checks ARE active (not frozen)
- `frozen_account=True` → margin checks DISABLED (frozen)

For realistic backtesting, use `frozen_account=False` (the confusing one).

### Multi-currency accounts

`base_currency=None` for multi-currency (standard for crypto). `Currency.from_str("USDT")` not bare constant.

### Venue setup (low-level API)

```python
engine.add_venue(
    venue=Venue("BINANCE"),
    oms_type=OmsType.NETTING,
    account_type=AccountType.MARGIN,  # MUST be MARGIN for perps/futures
    starting_balances=[Money(10_000, Currency.from_str("USDT"))],
    fill_model=fill_model,
)
```

`AccountType.CASH` + perps = 0 fills silently.

## Order Book

### F_LAST flag is mandatory

Every delta batch MUST end with `RecordFlag.F_LAST` or DataEngine buffers indefinitely — subscribers never receive data.

- Single delta: always set F_LAST
- Batch: set F_LAST only on last delta

### book.best_bid_price() returns Price, not float

Cast with `float(book.best_bid_price())` for arithmetic. Same for `best_ask_price()`, `spread()`, `midpoint()`.

### L2_MBP is the ceiling for crypto

L3_MBO not available on any crypto exchange. L2 is sufficient for all HFT strategies. L3 is only for traditional exchanges (equities).

### OrderBookDepth10 for lightweight signals

Pre-aggregated top 10 levels — lower overhead than full book subscription for signal generation.

## Venue-Specific Gotchas

### Binance

- `-PERP` suffix mandatory: `BTCUSDT-PERP.BINANCE` for futures, `BTCUSDT.BINANCE` for spot
- `BinanceAccountType.USDT_FUTURES` (with S) — `USDT_FUTURE` doesn't exist
- `BinanceFuturesMarkPriceUpdate` contains mark, index, AND funding_rate — don't subscribe separately
- Spot doesn't support `modify_order`
- High-supply tokens (SHIB, PEPE) need `high-precision` feature flag

### dYdX

- Market orders implemented as aggressive limit: buy at `oracle_price × 1.01`, sell at `× 0.99`
- Config: `is_testnet=True` (NOT `testnet=True`)
- No `modify_order` support

### Deribit

- Config: `is_testnet=True` (NOT `testnet=True`)
- `CryptoOption.underlying` is `Currency`, `OptionContract.underlying` is `str` — different types

### Polymarket

- No `modify_order` support
- Binary outcomes only — `YES`/`NO` tokens

## Performance Checklist

1. Cache `self.instrument` in `on_start()` — avoid repeated `cache.instrument()` lookups in hot path
2. Keep `on_order_book_deltas` tight — fires at tick frequency
3. Never `time.sleep()` in callbacks — single-threaded event loop blocks everything
4. Use `modify_order` over cancel+replace where supported — single message, less latency
5. `sort=False` + `engine.sort_data()` for multi-instrument backtest loading
6. Order books are Rust-native — all operations execute as native code, no Python overhead
7. `indicators_initialized()` guard prevents acting on partial warmup values
