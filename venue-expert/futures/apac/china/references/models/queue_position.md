# Queue Position Estimation Models for Chinese Futures

Structural approaches under 500ms snapshot constraints. FIFO matching assumed throughout.

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

**Chinese adaptation** (~5% cancel rate): Attribute ΔQ < 0 primarily to fills (front of queue), not cancels (back of queue).

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

**Chinese simplification** (λ_c ≈ 0.05 × total rate):
```
dQ ≈ λ_a dt - dN(t)    (M/M/1 approximation)
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
Where r ≈ 0.05 (cancel rate), p = log(1+V)/log(1+Q).

Fill probability:
```
P(fill | V, T) ≈ [1 - exp(-λμT/V)] × k
```
Where λ = trade rate, μ = mean size, k = Weibull shape (adjustment for non-Poisson).

---

## 7. Calibration Notes

| Parameter | Estimation |
|-----------|------------|
| μ (trade size) | Mean of volume deltas when ΔV > 0 |
| λ (trade rate) | Fraction of snapshots with ΔV > 0 |
| r (cancel rate) | ~0.05 (market-wide), or fit residual |
| k (Weibull) | Fit to inter-trade intervals, expect k ∈ (0.7, 0.9) |

**Session effects**: Models invalid during auctions, lock-limit, thin markets.

---

## References

1. Rigtorp (blog) - Queue position heuristic
2. Moallemi-Yuan (2017) - Exponential trade size closed-form
3. Cont-Stoikov-Talreja (2010) - Birth-death LOB dynamics, Operations Research
4. PBFJ (2025) - Weibull arrivals in Chinese futures
5. Obizhaeva-Wang (2013) - Optimal execution, transient impact
