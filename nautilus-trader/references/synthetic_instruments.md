# Synthetic Instruments

Formula-based derived instruments from components in NautilusTrader v1.224.0.

## SyntheticInstrument

Prices derived from component instruments using a mathematical formula. Implemented in Rust.

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
    ts_event=0,                             # required
    ts_init=0,                              # required
)
```

### Constructor (6 required args)

| Parameter | Type | Notes |
|-----------|------|-------|
| `symbol` | `Symbol` | Name for the synthetic |
| `price_precision` | `uint8` | 0-9, decimal places for price |
| `components` | `list[InstrumentId]` | Minimum 2 components |
| `formula` | `str` | Expression using component instrument ID values |
| `ts_event` | `uint64` | Nanosecond timestamp |
| `ts_init` | `uint64` | Nanosecond timestamp |

### ID Format

`{symbol}.SYNTH` — the venue is always `SYNTH`.

```python
synth.id                    # InstrumentId("BTC-ETH-SPREAD.SYNTH")
```

### Formula Notation

Components are referenced by their **instrument ID values** in the formula. Hyphens in IDs are converted to underscores internally:

```python
# Components:
components = [
    InstrumentId.from_str("BTCUSDT-PERP.BINANCE"),
    InstrumentId.from_str("ETHUSDT-PERP.BINANCE"),
]

# Spread: BTC - 20*ETH
formula = "BTCUSDT-PERP.BINANCE - ETHUSDT-PERP.BINANCE * 20"

# Ratio: BTC/ETH
formula = "BTCUSDT-PERP.BINANCE / ETHUSDT-PERP.BINANCE"

# Simple components work too:
components = [InstrumentId.from_str("A.X"), InstrumentId.from_str("B.X")]
formula = "A.X + B.X"
formula = "A.X * 0.5 + B.X * 0.5"     # weighted basket
```

Standard arithmetic operators: `+`, `-`, `*`, `/`, parentheses.

**Important**: Use the full `symbol.venue` format in formulas. Internally, `-` in IDs becomes `_` (e.g., `BTCUSDT-PERP.BINANCE` → `BTCUSDT_PERP.BINANCE` in the stored formula), but you pass the original ID format to the constructor.

### calculate()

Compute the synthetic price from component prices:

```python
# inputs correspond to component order: [BTC_price, ETH_price]
price = synth.calculate([95000.0, 3200.0])
# result: Price("31000.00") — (95000 - 3200 * 20)
```

**Raises**:
- `ValueError` if inputs is empty, contains NaN, or length != components count
- `RuntimeError` on internal calculation error

### change_formula()

Update the formula at runtime:

```python
synth.change_formula("BTCUSDT-PERP.BINANCE / ETHUSDT-PERP.BINANCE")
new_price = synth.calculate([95000.0, 3200.0])  # Price("29.69")
```

**Raises**: `ValueError` if formula is invalid.

### Properties

```python
synth.id                    # InstrumentId("BTC-ETH-SPREAD.SYNTH")
synth.price_precision       # 2
synth.price_increment       # Price derived from precision
synth.components            # [InstrumentId("BTCUSDT-PERP.BINANCE"), ...]
synth.formula               # "BTCUSDT_PERP.BINANCE - ETHUSDT_PERP.BINANCE * 20"
                            # note: hyphens converted to underscores in stored formula
synth.ts_event              # 0
synth.ts_init               # 0
```

### Use Cases

- **Spread instruments**: `A.X - B.X` for basis, calendar spreads
- **Ratios**: `A.X / B.X` for relative value
- **Custom baskets**: `A.X * 0.5 + B.X * 0.3 + C.Y * 0.2`
- **Cross-exchange spreads**: Components from different venues

### Integration

All component instruments must exist in the cache before defining a synthetic. The synthetic itself is added to the cache separately.

```python
# In strategy on_start():
# 1. Verify components are cached
btc = self.cache.instrument(InstrumentId.from_str("BTCUSDT-PERP.BINANCE"))
eth = self.cache.instrument(InstrumentId.from_str("ETHUSDT-PERP.BINANCE"))

# 2. Create synthetic
synth = SyntheticInstrument(
    symbol=Symbol("BTC-ETH"),
    price_precision=2,
    components=[btc.id, eth.id],
    formula="BTCUSDT-PERP.BINANCE - ETHUSDT-PERP.BINANCE * 20",
    ts_event=self.clock.timestamp_ns(),
    ts_init=self.clock.timestamp_ns(),
)

# 3. Subscribe to component data to feed calculate()
self.subscribe_quote_ticks(btc.id)
self.subscribe_quote_ticks(eth.id)
```

### Anti-Hallucination Notes

| Hallucination | Reality |
|--------------|---------|
| `formula="(c0 - c1 * 20)"` | Use instrument ID values: `formula="A.X - B.X * 20"` |
| `SyntheticInstrument(symbol, precision, components, formula)` | Also requires `ts_event` and `ts_init` (6 args total) |
| Single component | Minimum 2 components required (raises ValueError) |
| `price_precision > 9` | Max is 9 (raises ValueError) |
| Pickling/serialization | Currently NOT safe to pickle synthetic instruments |
