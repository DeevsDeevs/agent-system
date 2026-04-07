# Battle-Tested Patterns & Tricks

Non-obvious knowledge from live testing NautilusTrader v1.224.0. **Only patterns not covered in official docs.** For anything below marked with a doc link, read the doc first — it has more detail.

## Covered in Official Docs (read these first)

| Gotcha | Where |
|--------|-------|
| `on_start()` must be: cache → indicators → subscribe | [strategies.md](docs/concepts/strategies.md) |
| `sort=False` + `sort_data()` for multi-instrument backtest | [backtesting.md](docs/concepts/backtesting.md) |
| `ts_init_delta` for bar open→close timestamps (look-ahead bias) | [backtesting.md](docs/concepts/backtesting.md), [data.md](docs/concepts/data.md) |
| `F_LAST` flag mandatory on last delta in batch | [data.md](docs/concepts/data.md) |
| FillModel: only `prob_fill_on_limit`, `prob_slippage`, `random_seed` | [backtesting.md](docs/concepts/backtesting.md) |
| Binance `-PERP` suffix for futures | [binance.md](docs/integrations/binance.md) |
| dYdX: `is_testnet=True`, no `modify_order`, IOC limit orders | [dydx.md](docs/integrations/dydx.md) |
| Deribit: `is_testnet=True` | [deribit.md](docs/integrations/deribit.md) |
| Polymarket: no `modify_order`, binary outcomes | [polymarket.md](docs/integrations/polymarket.md) |
| Log rotation: `LoggingConfig(log_directory=, log_file_format=)` | [logging.md](docs/concepts/logging.md) |

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

Note: the official docs say "differentiate using `signal.value`" — this is misleading. `type(signal).__name__` works and is more precise when publishing multiple distinct signal types. The `name` param to `publish_signal` is not stored as `.name` on the object, but it IS baked into the generated class name.

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

- Market orders implemented as aggressive limit (IOC): buy at `oracle_price × 1.05`, sell at `× 0.95` (5% buffer, `DEFAULT_MARKET_ORDER_SLIPPAGE = 0.05`). Unfilled slippage not consumed.
- Config: `is_testnet=True` (NOT `testnet=True`)
- No `modify_order` support

### Deribit

- Config: `is_testnet=True` (NOT `testnet=True`)
- `CryptoOption.underlying` is `Currency`, `OptionContract.underlying` is `str` — different types

### Polymarket

- No `modify_order` support
- Binary outcomes only — `YES`/`NO` tokens

## Debugging Live Issues

### Step 1: Read the actual error

Most wasted debugging time comes from treating errors as opaque. The server is almost always telling you exactly what's wrong.

```bash
# HTTP errors: ALWAYS read the response body, not just the status code
curl -v 'https://fapi.binance.com/fapi/v1/...' -H 'X-MBX-APIKEY: ...' 2>&1

# Nautilus logs: grep ERROR first
grep "ERROR" logs/trader.log | head -20

# Rust: use {:?} (Debug), not {} (Display) — Debug includes inner error chain
log::error!("Failed: {error:?}");  # shows full chain
log::error!("Failed: {error}");    # may hide root cause
```

If a Nautilus error says "400 Bad Request" — **that is not enough information to debug**. Get the response body. One `curl -v` is worth 10 rounds of guessing.

### Step 2: Venue-specific API key rules

Binance has **per-product API keys**. A futures Ed25519 key is NOT valid for spot. Check:
- Spot key → spot endpoints only
- Futures/Linear key → futures endpoints only
- You may have separate keys in `.env`: `BINANCE_SPOT_API_KEY`, `BINANCE_LINEAR_API_KEY`

**Ed25519 encrypted keys**: Binance Ed25519 private keys can be password-encrypted (PKCS#8). NautilusTrader's `SigningCredential` needs the unencrypted key. If your `.env` has a `_DECRYPTED` variant, use that.

### Step 3: Extending NautilusTrader without modifying source

When NautilusTrader is missing a feature or an adapter does not behave the way you need, follow this decision tree. The architecture smell to avoid is building on a private fork without upstreaming -- not cloning the repo itself. Cloning to read source, run tests, or prepare a PR is perfectly normal.

**Decision tree -- "I need something NautilusTrader does not provide":**

#### 1. Compose via DataActor or Strategy (first choice, 90% of cases)

NautilusTrader's extension surface is trait-based. `DataActor` and `Strategy` are traits you implement on your own structs. They give you lifecycle callbacks (`on_start`, `on_stop`), data callbacks (`on_trade`, `on_quote`, `on_mark_price`, `on_book_deltas`, `on_funding_rate`, `on_data`, ...), timer events, and the signal/custom-data pipeline. This is composition, not inheritance -- your struct owns a `DataActorCore` or `StrategyCore` and delegates via `Deref`.

Use this when:
- An adapter streams data you need to reshape (e.g., use `subscribe_funding_rates` / `on_funding_rate` for funding data — the adapter handles the underlying source format)
- You need to combine multiple data feeds into a derived signal
- You need periodic REST polling (timer + async HTTP in Python via `queue_for_executor`, or timer + `reqwest` in a spawned task in Rust)
- You want to publish custom data types for downstream consumers

Rust example -- subscribing to funding rates:

```rust
use nautilus_model::data::FundingRateUpdate;

impl DataActor for FundingRateCapture {
    fn on_start(&mut self) -> anyhow::Result<()> {
        self.subscribe_funding_rates(self.instrument_id, None, None);
        Ok(())
    }

    fn on_funding_rate(&mut self, update: &FundingRateUpdate) -> anyhow::Result<()> {
        // FundingRateUpdate has: instrument_id, rate (Decimal), interval, next_funding_ns
        log::info!("{} rate={}", update.instrument_id, update.rate);
        Ok(())
    }

    fn on_stop(&mut self) -> anyhow::Result<()> {
        self.unsubscribe_funding_rates(self.instrument_id, None, None);
        Ok(())
    }
}
```

Note: whether funding rate data actually arrives depends on adapter support. Binance embeds it in mark price stream at the adapter level — the DataActor callback fires if the adapter parses it out. If the adapter doesn't support it, subscribe to mark prices as a fallback and check what fields arrive.

This is idiomatic Rust composition: your struct implements the trait, the runtime calls your callbacks. No source modification needed.

#### 2. Cargo `[patch]` for adapter bugs (temporary fix while upstreaming)

If an adapter has an actual bug (wrong signature encoding, missing WebSocket message handling, incorrect field parsing), fork on GitHub, fix the bug on a branch, and point your `Cargo.toml` at your fork:

```toml
[patch.'https://github.com/nautechsystems/nautilus_trader.git']
nautilus-binance = { git = "https://github.com/YOUR-USER/nautilus_trader.git", branch = "fix/binance-sig-encoding" }
```

Only list the crate(s) you modified. Cargo resolves transitive deps automatically. This is not a private fork -- it is a temporary patch with a clear intent to upstream via PR.

Rules:
- The branch name should describe the fix (`fix/binance-ws-reconnect`, not `my-changes`)
- Open an upstream PR immediately or as soon as the fix is validated
- Remove the `[patch]` once the fix is merged and released
- Never use `[patch]` for feature additions -- that belongs in category 3

#### 3. Fork + modify for upstream contribution (the right way to add features)

When NautilusTrader genuinely lacks functionality that belongs in the core (new adapter message type, new data feed, new order type support), the correct path is:

1. Clone the repo
2. Implement the feature on a branch
3. Run the existing test suite, add tests for your change
4. Open a PR upstream
5. Use `[patch]` to consume your branch while the PR is in review

This is how open source works. The smell is NOT cloning or modifying source -- it is building on a local fork without upstreaming. A private fork with adapter modifications that you never PR diverges immediately and breaks on the next Nautilus update.

#### 4. Cloning to read source or run tests (always fine)

Cloning the NautilusTrader repo to read adapter source, understand internal behavior, run tests, or check trait signatures is completely normal development practice. The repo is the best documentation for edge cases.

#### What NOT to do

Do not clone the repo, modify adapter internals to add missing functionality, build locally, and treat that as your production dependency. This is the architecture smell. Concretely, the failure mode looks like:

1. "Binance does not stream funding rates" -- correct observation
2. Clone repo, add funding rate streaming to the Binance adapter -- wrong response
3. Build from local path, deploy -- unmaintainable; breaks on next Nautilus version

The correct response to step 1 is category 1 above: write a `DataActor` that subscribes to `MarkPriceUpdate` (which contains funding rate data) and extracts what you need. No source modification required.

### Common runtime traps

| Symptom | Cause | Fix |
|---------|-------|-----|
| "Invalid symbol" on subscribe | Symbol doesn't exist on that venue/product | Check symbol list — not all coins have futures (SHIB, PEPE, LEO) |
| "Invalid X-MBX-APIKEY header" | Wrong API key for the endpoint (spot key on futures) | Use the correct per-product key |
| WebSocket reconnecting repeatedly | Too many subscriptions per connection (Binance limit ~1024 streams) | Reduce symbols or split across connections |
| Signature validation error | Ed25519 key misdetected as HMAC, or encrypted key used | Check `SigningCredential` detection, use unencrypted key |
| SBE decode failure | Exchange upgraded schema version (e.g. v2→v3) | Check exchange API changelog, update Nautilus |
| 0 instruments loaded | Missing `load_ids` in `InstrumentProviderConfig` | Add `load_ids=frozenset({"SYMBOL.VENUE"})` |
| Catalog empty after run | Run too short for feather flush, or wrong catalog path | Run longer (>60s), check `catalog_path` in config |
| `subscribe_funding_rates()` no data | Not all adapters implement the feed (Binance doesn't stream it natively) | Use `MarkPriceUpdate` which contains funding_rate (see Step 3 above) |

### Binance funding rate

In Rust, `subscribe_funding_rates` / `on_funding_rate` is the first-class path — the Binance adapter parses funding from its mark price stream internally. In Python, funding arrives via `BinanceFuturesMarkPriceUpdate` (contains mark, index, AND funding_rate). As a fallback, poll the REST endpoint via a timer-based actor (`queue_for_executor` + async HTTP).

## Rust Live Trading

### Strategy pattern (for order management)

DataActor is data-only. For submitting orders, use `Strategy` from `nautilus-trading`:

```rust
use std::ops::{Deref, DerefMut};
use nautilus_common::actor::{DataActor, DataActorCore};
use nautilus_model::data::TradeTick;
use nautilus_model::identifiers::InstrumentId;
use nautilus_trading::strategy::{Strategy, StrategyConfig, StrategyCore};

#[derive(Debug)]
struct MyStrategy {
    core: StrategyCore,  // wraps DataActorCore internally
    instrument_id: InstrumentId,
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

impl DataActor for MyStrategy {
    fn on_start(&mut self) -> anyhow::Result<()> {
        self.subscribe_trades(self.instrument_id, None, None);
        Ok(())
    }
    fn on_trade(&mut self, trade: &TradeTick) -> anyhow::Result<()> {
        log::info!("trade px={}", trade.price.as_f64());
        Ok(())
    }
    fn on_stop(&mut self) -> anyhow::Result<()> {
        self.unsubscribe_trades(self.instrument_id, None, None);
        Ok(())
    }
}

impl Strategy for MyStrategy {
    fn core(&self) -> &StrategyCore { &self.core }
    fn core_mut(&mut self) -> &mut StrategyCore { &mut self.core }
}
```

Constructor: `MyStrategy { core: StrategyCore::new(StrategyConfig { strategy_id: Some("MY-001".into()), ..Default::default() }), instrument_id }`.

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

See "Step 3: Extending NautilusTrader without modifying source" above for the full decision tree. Quick reference for Cargo `[patch]`:

```toml
[patch.'https://github.com/nautechsystems/nautilus_trader.git']
nautilus-{venue} = { git = "https://github.com/YOUR-USER/nautilus_trader.git", branch = "fix/my-fix" }
```

Only list the crate(s) you modified. Cargo resolves transitive deps automatically. Open an upstream PR, then remove the `[patch]` once the fix is merged and released.

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

## State Persistence

### on_save / on_load for strategy restart

```python
def on_save(self) -> dict[str, bytes]:
    return {"position_state": msgspec.json.encode(self._state)}

def on_load(self, state: dict[str, bytes]) -> None:
    if "position_state" in state:
        self._state = msgspec.json.decode(state["position_state"])
```

State is saved on graceful shutdown and restored on restart. Keys are strategy-scoped.

### Redis for shared state

```python
ExecEngineConfig(
    cache_database=CacheDatabaseConfig(type="redis", host="localhost", port=6379),
)
```

Enables order/position state recovery across restarts. Without Redis, in-memory cache is lost on crash.

## Metrics

### Fill quality tracking

```python
def on_order_filled(self, event) -> None:
    expected = self._last_signal_price
    actual = float(event.last_px)
    slippage_bps = (actual - expected) / expected * 10_000
    self.log.info(f"Slippage: {slippage_bps:.1f} bps")
```

Track per-venue, per-side. Asymmetric slippage (buys worse than sells) indicates toxic flow detection.

### Latency measurement

```python
def on_order_filled(self, event) -> None:
    round_trip_ns = event.ts_init - self._order_submitted_ns
    self.log.info(f"Round-trip: {round_trip_ns / 1_000_000:.1f}ms")
```

`ts_init` on the fill event is when the exchange response arrived locally. Compare against submission timestamp for round-trip latency.

## Log Rotation

```python
LoggingConfig(
    log_level="INFO",
    log_directory="logs/",
    log_file_format="{trader_id}_{instance_id}",
    log_colors=False,
)
```

Nautilus creates one log file per run. For rotation, use external logrotate or cron. File names include trader_id for multi-strategy separation.

## Custom Indicator Development

```python
from nautilus_trader.indicators.base import Indicator

class SpreadEMA(Indicator):
    def __init__(self, period: int):
        super().__init__([])  # no input params for registration
        self.period = period
        self._values = []
        self.value = 0.0

    def handle_quote_tick(self, tick: QuoteTick) -> None:
        spread = float(tick.ask_price - tick.bid_price)
        self._values.append(spread)
        if len(self._values) > self.period:
            self._values.pop(0)
        self.value = sum(self._values) / len(self._values)
        # _set_initialized inherited from Cython Indicator base — do NOT override
        self._set_initialized(len(self._values) >= self.period)

    def reset(self) -> None:
        self._values.clear()
        self.value = 0.0
        self._set_initialized(False)
```

Register: `self.register_indicator_for_quote_ticks(instrument_id, spread_ema)` in `on_start`.

## Data Pipeline

### Gap detection in tick data

```python
def check_gaps(ticks, max_gap_ms=60_000):
    for i in range(1, len(ticks)):
        gap = (ticks[i].ts_event - ticks[i-1].ts_event) / 1_000_000
        if gap > max_gap_ms:
            print(f"Gap: {gap:.0f}ms at index {i}")
```

Run before backtesting. Gaps > 1 minute during trading hours = suspect data. Gaps during maintenance windows (Binance: Tue 06:00-06:30 UTC) are normal.

### Timestamp sanity

- `ts_event` should increase monotonically
- `ts_init >= ts_event` always (init is local receipt time)
- `ts_init - ts_event > 60s` = suspect clock skew or stale data

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
