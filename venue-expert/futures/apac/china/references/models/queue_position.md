# Queue Position Estimation Models for Chinese Futures

Structural approaches under 500ms snapshot constraints. FIFO matching assumed throughout.

**Causal status**: All estimates below are model-dependent, not identified from data. No order-by-order data exists for Chinese futures. Use pessimistic parameters for execution planning, median for capacity estimation.

---

## 1. Problem Statement

**Observable**: P_b, P_a, Q_b, Q_a (5 levels), cumulative V_t, OI_t at 500ms intervals.

**Unobservable**: Order arrivals/cancellations, exact queue position, trade direction.

**Goal**: P(fill | position, horizon) for limit orders.

---

## 2. Rigtorp Baseline

Queue position update:
```
V(t+1) = max(V(t) - p(t) × |ΔQ(t)|, 0)   when ΔQ < 0
```

Probability function (volume decrease affects orders ahead):
```
p = log(1 + V) / log(1 + Q)
```

**Chinese adaptation**: The ~5% aggregate cancel rate cited in earlier versions does not match authoritative sources. Available evidence: SSE ~23%, SZSE ~29% (ScienceDirect 2021), 开源证券 ~30% full + ~10% partial. Chinese futures likely 20-40% due to no native order modification (cancel-replace inflates rate). With r ≈ 0.20-0.40, a larger fraction of ΔQ < 0 must be attributed to cancellations, reducing estimated fill progression.

---

## 3. Moallemi-Yuan Closed-Form (2017)

**Assumptions**: Exponential trade sizes (rate μ), no cancellations, static book.

Fill probability for position n in queue Q:
```
P(fill | n, Q) ≈ exp(-n/μ)    for Q >> μ
```

Where μ = mean trade size (lots). Estimate from trade volume distribution.

---

## 4. Cont-Stoikov-Talreja Birth-Death (2010)

Queue dynamics:
```
dQ = λ_a dt - λ_c dt - dN(t)
```

Laplace transform of hitting time τ (queue → 0):
```
E[e^(-sτ) | Q_0] = (r₁/r₂)^Q₀
```

Where r₁, r₂ solve: λ_a r² - (λ_a + λ_c + λ_m + s)r + λ_m = 0

**Chinese simplification** (λ_c ≈ 0.20-0.40 × total rate; see research-4.1 Q7):
```
dQ ≈ λ_a dt - λ_c dt - dN(t)    (cancellation term non-negligible)
```

---

## 5. Weibull Arrival Extension (PBFJ 2025)

Chinese order arrivals follow Weibull, not Poisson:
```
λ(t) = (k/θ)(t/θ)^(k-1)
```

Empirical finding: k < 1 (decreasing hazard - clustering then quiet).

Expected time to fill n orders:
```
E[T_n] = n × θ × Γ(1 + 1/k)
```

**Implication**: Standard Poisson models underestimate fill times.

---

## 6. Integrated Model

Position update (per snapshot):
```
V ← max(V - p × (1-r) × |ΔQ|, 0)    when ΔQ < 0
```
Where r ≈ 0.20-0.40 (cancel rate; see research-4.1 Q7), p = log(1+V)/log(1+Q).

Fill probability:
```
P(fill | V, T) ≈ [1 - exp(-λμT/V)] × k
```
Where λ = trade rate, μ = mean size, k = Weibull shape (adjustment for non-Poisson).

The higher cancel rate (vs previously assumed ~5%) materially reduces estimated fill progression per snapshot.

---

## 6a. Per-Product CST Parameters

Scaled from Cont-Stoikov-Talreja (2010) benchmarks using observable Chinese futures characteristics. No direct calibration exists.

| Parameter | rb (Rebar) | cu (Copper) | i (Iron Ore) | IF (CSI 300) | sc (Crude Oil) | TA (PTA) |
|-----------|-----------|-------------|--------------|-------------|---------------|----------|
| θ(1) limit orders/sec at L1 | 5-15 | 2-6 | 4-12 | 3-8 | 2-5 | 3-10 |
| μ market orders/sec | 2-6 | 0.5-2 | 1.5-5 | 1-3 | 0.5-1.5 | 1-4 |
| α(1) cancel rate/order/sec | 0.05-0.15 | 0.03-0.10 | 0.05-0.12 | 0.05-0.15 | 0.03-0.08 | 0.04-0.10 |
| λ/θ at L1 | 0.2-0.5 | 0.15-0.35 | 0.2-0.45 | 0.2-0.4 | 0.15-0.30 | 0.2-0.4 |

λ/θ < 1 required for non-degenerate book formation. All estimates from international proxies scaled to Chinese market characteristics.

---

## 6b. Fill Probability by Queue Position

| Queue Position | Estimated Fill Probability | Adverse Selection Cost |
|----------------|--------------------------|----------------------|
| Front 10% | 70-90% (conditional on price not moving away) | Highest |
| Middle 10-50% | 30-60% | Moderate |
| Back 50-100% | 5-25% | Lowest |

**L1 queue depth and turnover**:

| Product | Typical L1 Queue (lots) | L1 Queue (CNY notional) | Trade Freq (trades/sec) | Est. Queue Half-Life (sec) |
|---------|------------------------|------------------------|------------------------|---------------------------|
| rb | 100-500 | ¥0.3-2.0M | 2-6 | 5-15 |
| cu | 20-80 | ¥7-32M | 0.5-2 | 10-30 |
| i | 50-300 | ¥3.5-27M | 1.5-5 | 5-15 |
| IF | 10-50 | ¥10.5-60M | 1-3 | 3-10 |
| sc | 10-50 | ¥5-30M | 0.5-1.5 | 15-45 |
| TA | 50-200 | ¥0.25-1.2M | 1-4 | 5-15 |

Queue depths from practitioner estimates consistent with BBO volume in CTP snapshots.

---

## 6c. Volatility Regime Sensitivity

Parameters shift materially between regimes.

| Regime | Queue Depth | Trade Rate | Queue Half-Life |
|--------|------------|-----------|-----------------|
| High vol (realized > 1.5× 20-day avg) | -30-50% | +50-100% | 2-5s |
| Low vol (realized < 0.7× avg) | +20-40% | -30-50% | 15-60s |
| Night session | ~50-70% of daytime | -30-60% volume | Proportionally longer |

Night session (21:00-23:00/01:00/02:30): volume -30-60%, queue depths ~50-70% of daytime. Cancel rates may be proportionally higher at night due to more aggressive quote management with thinner books.

---

## 7. Calibration Notes

| Parameter | Estimation |
|-----------|------------|
| μ (trade size) | Mean of volume deltas when ΔV > 0 |
| λ (trade rate) | Fraction of snapshots with ΔV > 0 |
| r (cancel rate) | ~0.20-0.40 (research-4.1 Q7), or fit residual |
| k (Weibull) | Fit to inter-trade intervals, expect k ∈ (0.7, 0.9) |

**Session effects**: Models invalid during auctions, lock-limit, thin markets.

---

## References

1. Rigtorp (blog) - Queue position heuristic
2. Moallemi-Yuan (2017) - Exponential trade size closed-form
3. Cont-Stoikov-Talreja (2010) - Birth-death LOB dynamics, Operations Research
4. PBFJ (2025) - Weibull arrivals in Chinese futures
5. Obizhaeva-Wang (2013) - Optimal execution, transient impact
