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

### Market maker: on_order_filled resets order IDs

```python
def on_order_filled(self, event) -> None:
    if event.client_order_id == self._bid_id:
        self._bid_id = None
    elif event.client_order_id == self._ask_id:
        self._ask_id = None
```

Without this: stale `_bid_id`/`_ask_id` → `cache.order(stale_id)` returns filled order → `is_open` is False → submits duplicate instead of modifying.

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
class ImbalanceData(Data):
    def __init__(self, imbalance: float, volume: float, ts_event: int, ts_init: int):
        self.imbalance = imbalance
        self.volume = volume
        self._ts_event = ts_event
        self._ts_init = ts_init

    @property
    def ts_event(self) -> int: return self._ts_event
    @property
    def ts_init(self) -> int: return self._ts_init
```

Actor: `self.publish_data(data_type=DataType(ImbalanceData), data=data)`
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

## Rust Live Trading

### Strategy pattern (for order management)

DataActor is data-only. For submitting orders, use `Strategy` from `nautilus-trading`:

```rust
use nautilus_common::actor::{DataActor, DataActorCore};
use nautilus_trading::strategy::{Strategy, StrategyConfig, StrategyCore};

#[derive(Debug)]
struct MyStrategy {
    core: StrategyCore,  // wraps DataActorCore internally
}

// CRITICAL: Deref target is DataActorCore, NOT StrategyCore.
// Strategy extends DataActor which requires Deref<Target = DataActorCore>.
// StrategyCore itself implements Deref<Target = DataActorCore>, so this chains through.
impl Deref for MyStrategy {
    type Target = DataActorCore;
    fn deref(&self) -> &Self::Target { &self.core }  // auto-derefs StrategyCore → DataActorCore
}
impl DerefMut for MyStrategy {
    fn deref_mut(&mut self) -> &mut Self::Target { &mut self.core }
}

// DataActor impl — data callbacks + order submission
impl DataActor for MyStrategy {
    fn on_start(&mut self) -> anyhow::Result<()> { Ok(()) }
    fn on_stop(&mut self) -> anyhow::Result<()> { Ok(()) }
}

impl Strategy for MyStrategy {
    fn core(&self) -> &StrategyCore { &self.core }
    fn core_mut(&mut self) -> &mut StrategyCore { &mut self.core }
}
```

Constructor: `StrategyCore::new(StrategyConfig { strategy_id: Some("MY-001".into()), ..Default::default() })`.

Key event fields:
- `PositionOpened`: `entry` (OrderSide), `side` (PositionSide), `quantity`, `last_px`, `avg_px_open`, `currency`
- `PositionClosed`: `realized_pnl` (Option<Money> — use `{:?}` format), `duration` (not `duration_ns`), `avg_px_open`, `avg_px_close`
- `OrderFilled`: `last_qty`, `last_px`, `commission`, `liquidity_side`, `trade_id`

Add to node: `node.add_strategy(my_strategy)?;` (not `add_actor`).

### Credential handling

Adapters using `SigningCredential` auto-detect key type:
1. Tries to strip PEM headers + base64 decode → Ed25519 if valid
2. Falls back to HMAC

**Gotcha**: HMAC secrets that happen to be valid base64 (≥32 bytes) get misdetected as Ed25519. Symptoms: signature validation errors on execution client connect. This affects any adapter using `SigningCredential`.

### Ed25519 HTTP signature encoding (v0.55.0)

Ed25519 signatures are base64 containing `+`, `/`, `=`. Some adapter HTTP clients insert signatures into query strings without URL-encoding. HMAC signatures are hex (URL-safe) so they work fine. If you see signature errors only with Ed25519 keys, check whether the adapter's HTTP client URL-encodes the signature. Most have a `percent_encode()` helper already.

### Patching Nautilus dependencies

Fork on GitHub, push fix to a branch, use Cargo `[patch]`:

```toml
[patch.'https://github.com/nautechsystems/nautilus_trader.git']
nautilus-{venue} = { git = "https://github.com/YOUR-USER/nautilus_trader.git", branch = "fix/my-fix" }
```

Only list the crate(s) you modified. Cargo resolves transitive deps automatically. Submit upstream PR when the fix is general.

### Rust adapter maturity gaps

The Rust adapters are newer than Python. Expect:
- Some WebSocket event types unhandled (fall to `Unknown`, log warnings) — usually harmless if the critical event path works
- Some config options existing in Python but missing in Rust (e.g. `use_trade_lite`)
- HTTP signing edge cases with non-HMAC key types
- Check the venue's adapter crate README and compare with Python adapter for feature parity

## Backtest → Live Checklist

1. `InstrumentProviderConfig(load_ids=frozenset({"BTCUSDT-PERP.BINANCE"}))` — backtest uses `engine.add_instrument()`, live requires `load_ids`
2. Replace `TestInstrumentProvider` instruments with real venue instruments
3. Add `exec_clients` config (backtest doesn't need it)
4. Add `reconciliation=True`, `reconciliation_lookback_mins=1440` to `LiveExecEngineConfig`
5. Add `on_order_rejected` / `on_order_modify_rejected` handlers — backtest rarely rejects
6. Handle `modify_order` unsupported — fall back to cancel+new
7. Set realistic `LoggingConfig(log_level="INFO", log_directory="logs/")`
8. Expect `fills > orders` (partials), `frozen_account` semantics differ
9. Test on venue testnet first (`testnet=True` or `is_testnet=True` depending on venue)
10. WebSocket shutdown lingers ~10s — use `tokio::time::timeout` (Rust) or KeyboardInterrupt (Python)

## Performance Checklist

1. **Rust hot path**: `Price::new(f64, u8)` — never `Price::from(format!("{:.prec$}", val, prec=p).as_str())` (heap alloc per tick)
2. Cache `self.instrument` in `on_start()` — avoid repeated `cache.instrument()` lookups in hot path
3. Keep `on_order_book_deltas` tight — fires at tick frequency
4. Never `time.sleep()` in callbacks — single-threaded event loop blocks everything
5. Use `modify_order` over cancel+replace where supported — single message, less latency
6. `sort=False` + `engine.sort_data()` for multi-instrument backtest loading
7. Order books are Rust-native — all operations execute as native code, no Python overhead
8. `indicators_initialized()` guard prevents acting on partial warmup values
9. `Vec::with_capacity(n)` for known-size collections in hot path — avoid reallocation
