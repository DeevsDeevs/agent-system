# Derivatives & Synthetic Instruments

> **Options**: See [options_and_greeks.md](options_and_greeks.md) for CryptoOption, OptionContract, greeks, Black-Scholes.

## Instrument Types

### CryptoPerpetual

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

```python
future = cache.instrument(InstrumentId.from_str("BTCUSDT-250328.BINANCE"))
future.expiration         # Expiration datetime
future.activation         # When contract becomes tradeable
```

### PerpetualContract

Any asset class (FX, equities, commodities, indexes, crypto). `underlying` is `str` (not `Currency`), `asset_class` is configurable.

```python
from nautilus_trader.model.instruments import PerpetualContract
from nautilus_trader.model.enums import AssetClass

perp = PerpetualContract(
    instrument_id=InstrumentId.from_str("EURUSD-PERP.VENUE"),
    raw_symbol=Symbol("EURUSD-PERP"),
    underlying="EURUSD",                       # str, not Currency
    asset_class=AssetClass.FX,
    quote_currency=Currency.from_str("USD"),
    settlement_currency=Currency.from_str("USD"),
    is_inverse=False,
    price_precision=5,
    size_precision=0,
    price_increment=Price.from_str("0.00001"),
    size_increment=Quantity.from_int(1),
    ts_event=0,
    ts_init=0,
)
```

Use `CryptoPerpetual` for crypto venues. Use `PerpetualContract` when underlying is non-crypto.

### SyntheticInstrument

```python
from nautilus_trader.model.instruments import SyntheticInstrument
from nautilus_trader.model.identifiers import InstrumentId, Symbol

synth = SyntheticInstrument(
    symbol=Symbol("BTC-ETH-SPREAD"),
    price_precision=2,                      # max 9
    components=[                            # minimum 2 required
        InstrumentId.from_str("BTCUSDT-PERP.BINANCE"),
        InstrumentId.from_str("ETHUSDT-PERP.BINANCE"),
    ],
    formula="BTCUSDT-PERP.BINANCE - ETHUSDT-PERP.BINANCE * 20",
    ts_event=0,
    ts_init=0,
)
```

6 required args: `symbol`, `price_precision` (0-9), `components` (min 2), `formula`, `ts_event`, `ts_init`. ID format: `{symbol}.SYNTH`. Hyphens in IDs converted to underscores internally.

```python
formula = "BTCUSDT-PERP.BINANCE - ETHUSDT-PERP.BINANCE * 20"  # spread
formula = "BTCUSDT-PERP.BINANCE / ETHUSDT-PERP.BINANCE"        # ratio
formula = "A.X * 0.5 + B.X * 0.5"                              # weighted basket
```

`synth.calculate([95000.0, 3200.0])` — raises `ValueError` if inputs empty, NaN, or wrong length. `synth.change_formula("A.X / B.X")` — no validation until `calculate()`. All components must exist in cache first.

```python
def on_start(self) -> None:
    btc = self.cache.instrument(InstrumentId.from_str("BTCUSDT-PERP.BINANCE"))
    eth = self.cache.instrument(InstrumentId.from_str("ETHUSDT-PERP.BINANCE"))
    synth = SyntheticInstrument(
        symbol=Symbol("BTC-ETH"), price_precision=2,
        components=[btc.id, eth.id],
        formula="BTCUSDT-PERP.BINANCE - ETHUSDT-PERP.BINANCE * 20",
        ts_event=self.clock.timestamp_ns(), ts_init=self.clock.timestamp_ns(),
    )
    self.subscribe_quote_ticks(btc.id)
    self.subscribe_quote_ticks(eth.id)
```

> See SKILL.md for common hallucination guards.

### CryptoOption

See [options_and_greeks.md](options_and_greeks.md). Key fields: `underlying` (Currency), `option_kind` (CALL/PUT), `strike_price`, `is_inverse`.

### Comparison

| Feature | CryptoPerpetual | CryptoFuture | CryptoOption |
|---------|----------------|--------------|-------------|
| Expiry | None | Fixed settlement | Fixed expiry |
| Funding | Every 8h (typically) | None | None |
| Price anchor | Funding rate | Convergence at expiry | Black-Scholes |
| Greeks | delta=1 | delta=1 | Full greeks via GreeksCalculator |

## Mark Price

Used for **liquidation** and **unrealized PnL**, not order matching. Last = most recent trade. Mark = fair value. Index = weighted spot average.

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

## Funding Rate

`subscribe_funding_rates()` not implemented on all adapters. **Binance**: funding embedded in mark price WebSocket (`@markPrice`):

```python
from nautilus_trader.adapters.binance.futures.types import BinanceFuturesMarkPriceUpdate

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

### Mechanics

| Parameter | Common Values | Notes |
|-----------|--------------|-------|
| Payment interval | 8h, 4h, 1h | Binance/Bybit default 8h, dYdX uses 1h |
| Direction | Positive: longs pay shorts | Universal |

```
funding_payment = abs(position_size) * mark_price * funding_rate
```

### Funding as Inventory Carrying Cost

```python
funding_cost = float(pos.signed_qty) * mark_price * self._current_funding_rate
```

Positive funding + long = cost. Negative funding + long = income.

### Funding Arbitrage

When funding rate > threshold: short perp, long spot (delta-neutral). Monitor via `on_data` with `FundingRateUpdate`. **Basis arb**: contango (futures > spot) → short futures, long spot; backwardation → reverse.

## Open Interest

OI = total outstanding contracts. Rising OI + rising price = strong uptrend. Rising OI + flat price = squeeze risk. Falling OI + falling price = liquidation cascade. Availability varies by exchange — poll via `HttpClient`. See [exchange_adapters.md](exchange_adapters.md). Custom data: subclass `nautilus_trader.core.data.Data`, implement `ts_event`/`ts_init` properties.

## Liquidation Mechanics

Triggered by **mark price**, not last trade price. Margin ratio = maintenance_margin / margin_balance >= 100% → liquidation. Exchange takes over, attempts market close. Closed above bankruptcy price → insurance fund; cannot close → **ADL**.

```
# Long: liquidation_price ≈ entry * (1 - initial_margin + maintenance_margin)
# Short: liquidation_price ≈ entry * (1 + initial_margin - maintenance_margin)
```

> Simplified. Actual depends on cross/isolated margin, funding, tiered rates. **Use the exchange's calculator.**

ADL: when insurance fund depletes, exchange forcibly closes profitable opposing positions. Not simulated in backtest. `frozen_account=False` enforces margin checks (False = checks active).

## Circuit Breakers & Market Halts

Binance does NOT implement `subscribe_instrument_status()`. Use `subscribe_instrument_status(id)` → `on_instrument_status(status)` → check `status.action` for `HALT`/`PAUSE`/`TRADING`. `RESUME` does not exist — use `TRADING`. See [traditional_finance.md](traditional_finance.md#market-session--instrument-status) for full pattern.

## Position Margin

`initial_margin = qty * avg_px_open * perp.margin_init`, `maint_margin = qty * avg_px_open * perp.margin_maint`. Account balances: `account.balance_total(USDT)`, `balance_free(USDT)` (available), `balance_locked(USDT)` (margin). See [execution.md](execution.md#portfolio-api) for portfolio API.

## Funding Rate in Backtest

`GenericDataWrangler` does NOT exist in v1.224.0. Construct `FundingRateUpdate(instrument_id, rate, ts_event, ts_init)` directly, pass list to `engine.add_data()`. Available wranglers: `TradeTickDataWrangler`, `QuoteTickDataWrangler`, `OrderBookDeltaDataWrangler`, `BarDataWrangler`.

## DEX Trading

| Venue Type | Config Field |
|------------|-------------|
| DEX (Hyperliquid, dYdX) | `private_key` |
| Hybrid (Polymarket) | `private_key` + `api_key/secret/passphrase` |
| CEX (Binance, Bybit, OKX) | `api_key` + `api_secret` |

On-chain: trades final on block confirmation (vs CEX immediate), gas/protocol fees apply, signature adds latency.

| Venue | Testnet | Config |
|-------|---------|--------|
| Hyperliquid | Yes | `testnet=True` |
| dYdX | Yes | `is_testnet=True` |
| Polymarket | No | — |
