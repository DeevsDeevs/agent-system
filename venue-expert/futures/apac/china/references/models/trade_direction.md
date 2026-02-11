# Trade Direction Inference for Chinese Futures

CTP provides no trade direction indicator. Must infer from price/quote relationship and OI dynamics.

---

## 1. Lee-Ready Adaptation

### Standard Algorithm

```
if LastPrice >= AskPrice1:  BUY (外盘)
elif LastPrice <= BidPrice1: SELL (内盘)
else: BUY if LastPrice > mid else SELL
```

Where mid = (BidPrice1 + AskPrice1) / 2.

### 500ms Limitations

- Quote may have moved between trade and snapshot
- Multiple trades aggregated in single snapshot
- Misclassification rate: ~15-25% (empirical)

### Tick Test Fallback

When trade at mid: sign(LastPrice - LastPrice_prev)
- Uptick → BUY
- Downtick → SELL
- Zero-tick → use prior classification

---

## 2. OI-Based Decomposition

CTP provides cumulative OI. Decompose trade flow:

```
现手 (trade vol) = V(t) - V(t-1)
增仓 (OI change) = OI(t) - OI(t-1)
开仓 (new positions) = (现手 + 增仓) / 2
平仓 (closed positions) = (现手 - 增仓) / 2
```

### Four-Way Classification

| 增仓 > 0 | 增仓 < 0 | Interpretation |
|----------|----------|----------------|
| Price ↑ | - | 多开 (long entry, bullish) |
| Price ↓ | - | 空开 (short entry, bearish) |
| - | Price ↑ | 空平 (short cover, bullish) |
| - | Price ↓ | 多平 (long liquidation, bearish) |

### Information Content

- 多开 + 空开 (both opening): Directional conviction divergence
- 多平 + 空平 (both closing): Position reduction, volatility often follows
- OI ↑ with volume: New interest, trend continuation signal
- OI ↓ with volume: Profit-taking/stopping, potential reversal

---

## 3. Structural Interpretation

### Kyle (1985) Framework

Informed trader order flow:
```
x = β(v - p)
```
Where v = fundamental value, p = current price, β = intensity.

**OI change as signal**: New position opening suggests trader has view on v ≠ p.

### Adverse Selection

| Flow Type | Adverse Selection |
|-----------|-------------------|
| 开仓 (opening) | Higher - trader initiating position |
| 平仓 (closing) | Lower - trader exiting, less informed |

Implication: Weight OI-increasing trades more heavily in flow toxicity measures.

---

## 4. Aggregate Flow Metrics

### Order Flow Imbalance (OFI)

```
OFI = Σ sign(trade) × size
```

Where sign from Lee-Ready. Predicts short-term price moves (Cont et al. 2014).

### Toxic Flow Proxy

```
VPIN_approx = |BuyVol - SellVol| / TotalVol
```

Computed over rolling window. Higher values suggest informed trading.

### OI-Weighted Flow

```
OFI_weighted = Σ sign(trade) × size × (1 + |ΔOI|/size)
```

Upweights trades with OI impact (position-establishing flow).

---

## 5. Validation

Cannot directly validate without broker fill data. Indirect checks:

1. **Price prediction**: Does inferred direction predict next-tick price move?
2. **Spread response**: Does inferred buy pressure widen ask, narrow bid?
3. **OI consistency**: Does 开仓 accumulation precede trends?

Expected accuracy: 75-85% for large-tick contracts, lower for thin markets.

---

## References

1. Lee & Ready (1991) - Trade classification algorithm
2. Easley et al. (2012) - VPIN and flow toxicity
3. Cont, Kukanov, Stoikov (2014) - OFI and price dynamics
4. Kyle (1985) - Continuous auction equilibrium
