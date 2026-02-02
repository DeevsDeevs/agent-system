# Cross-Product Analysis Framework for Chinese Futures

**Statistical rigor for cross-product relationships in a single-venue-per-product market.**

---

## Why No Cross-Venue Arbitrage

Chinese futures differ fundamentally from US equities (16+ venues, NBBO arbitrage) or even US futures (CME vs ICE competition in some products).

| Product | Venue | Cross-Venue Alternative |
|---------|-------|------------------------|
| Copper CU | SHFE | None domestic |
| Crude Oil SC | INE | International Brent/WTI (time zone, currency barriers) |
| Iron Ore I | DCE | None domestic |
| Stock Index IF | CFFEX | None (no ETF arbitrage due to T+1 stocks) |

**Implications for Research**:
1. No venue fragmentation = no SIP/direct feed latency arb
2. Price discovery happens at single venue = cannot study information share across venues
3. Cross-product relationships replace cross-venue as primary research focus
4. International linkages exist but with friction (currency, access, timing)

---

## Cross-Product Basis Relationships

### Pre-Registered Hypothesis Framework

Before examining any data, explicitly state:

```
HYPOTHESIS TEMPLATE:

H0: [Product A] and [Product B] prices are cointegrated with 
    stable long-run relationship [specify mechanism]
    
H1: Basis [A - β×B] mean-reverts with half-life [X-Y] days

Predicted direction: [A leads B / B leads A / bidirectional]
Economic mechanism: [why this relationship exists]
```

### Candidate Relationships (Require Pre-Registration)

| Relationship | Mechanism | Expected Lead-Lag | Testable? |
|--------------|-----------|-------------------|-----------|
| SC (INE crude) ↔ Brent/WTI | Global crude price discovery | Brent leads SC (time zone) | Yes |
| BC (INE bonded copper) ↔ CU (SHFE domestic) | Same underlying, different tax treatment | Cointegrated, basis = tariff + logistics | Yes |
| RB (rebar) ↔ I (iron ore) + J (coke) | Production cost relationship | Iron ore/coke lead rebar | Yes |
| IF (index futures) ↔ CSI 300 constituent stocks | Arbitrage relationship | Futures should lead (T+0 vs T+1) | Yes, but friction |
| Night session ↔ Day session | Information accumulation | Night first 30min predicts | Ma et al. (2022) |

### Statistical Methodology for Basis Trading

**Cointegration Test Battery** (pre-specify before data):
1. Engle-Granger two-step (simple, assumes single cointegrating vector)
2. Johansen trace/eigenvalue (multiple vectors, but overfits small samples)
3. Phillips-Ouliaris (robust to serial correlation)

**Threshold**: 
- Recommend α = 0.01 for cointegration tests (avoid false discoveries)
- Require OOS validation: in-sample cointegration must hold out-of-sample

**Half-Life Estimation**:
```
Ornstein-Uhlenbeck: dS = θ(μ - S)dt + σdW
Half-life = ln(2) / θ

CRITICAL: Report confidence interval for θ, not just point estimate.
Bootstrap standard errors; θ̂ is biased in small samples.
```

---

## Night Session Lead-Lag Analysis

### The Ma et al. (2022) Finding

**Citation**: Ma, Lei, Chen, & Zheng (2022). SSRN #4282926.

**Finding**: First 30 minutes of night session returns predict subsequent returns, effect concentrated on high-volatility days.

### Pre-Registered Replication Protocol

```
HYPOTHESIS (Pre-Registered):
H0: E[R_{t+1} | R_{night,first30min}] = E[R_{t+1}]
H1: E[R_{t+1} | R_{night,first30min}] ≠ E[R_{t+1}]

Specification:
R_{day} = α + β × R_{night_first30} + ε

α = 0.05 (two-sided)
Multiple testing: 5 exchanges × 10 major products = 50 tests
Bonferroni-adjusted α = 0.001
BH-FDR target: q = 0.05

OOS requirement: Train on 2015-2020, test on 2021-2023
Minimum effect size: β > 0.05 to be economically meaningful
```

### Confounders to Control

1. **Overnight international returns**: Night session opens after US close
   - Control: Regress on S&P 500, Brent oil, LME metals as appropriate
   
2. **Volatility regime**: Effect may only exist in high-vol periods
   - Stratify by realized volatility quintiles
   
3. **Product-specific factors**: Inventory announcements, delivery month effects
   - Control: Day-of-week, contract roll, major announcement dummies

### Power Analysis

```
Given:
- Daily observations: ~250/year × 8 years = 2,000 in-sample
- Expected R² increment: 0.5% (small but tradeable if real)
- Required power: 0.8

Result: Detectable effect size β ≈ 0.03 at α = 0.001
If true β < 0.03, we cannot reliably detect it.
```

---

## CFFEX Index Futures vs Cash Market

### Unique Constraints

| Constraint | Effect on Basis |
|------------|----------------|
| T+1 for stocks, T+0 for futures | Arbitrage is one-directional |
| Position limits: 1,200 contracts | Cannot scale arbitrage |
| Intraday close fees: 10x open | Discourages basis trading |
| QFI hedging-only restriction | Foreign flow constrained |

### The Persistent Discount Puzzle

Post-2015, CSI 300 futures traded at persistent discount to cash:
- Average basis: -0.3% to -0.8% (annualized -3% to -8%)
- Cause: Short selling constraints in cash market

**Testable Hypothesis**:
```
H0: Basis discount is constant over time
H1: Basis discount varies with:
    - Short-sale restriction intensity
    - Margin requirement changes
    - Position limit adjustments
    
Structural breaks: Test at known regulatory change dates
(Use Chow test or Bai-Perron, pre-specify change dates)
```

### Lead-Lag with Friction

Standard lead-lag tests (Granger causality) assume frictionless trading.
With T+1 stocks and T+0 futures:

```
METHODOLOGY:
1. Test: Futures returns → Stock returns (Granger)
   - Expect: Significant (futures lead)
   
2. Test: Stock returns → Futures returns (Granger)
   - Expect: Weak or none (cannot arbitrage)
   
3. Hasbrouck information share decomposition
   - Futures should have >90% information share
   
4. Validate: Cointegration error correction
   - ECM coefficient should be asymmetric
```

---

## Information Transmission Mechanisms

### Theoretical Framework

Information flows through:
1. **Common factor exposure**: SC and CU both respond to global growth
2. **Production linkage**: Iron ore → Coke → Rebar
3. **Substitution**: Soybean oil ↔ Palm oil ↔ Rapeseed oil
4. **Calendar structure**: Night session receives international news

### Testable Channels

| Channel | Products | Test |
|---------|----------|------|
| Global crude | SC ← Brent | Granger, impulse response |
| Metals complex | CU, AL, ZN correlation | DCC-GARCH dynamics |
| Agricultural | M, Y, P, OI (oils) | Volatility spillover |
| Ferrous chain | I → J → RB | Sequential Granger |

### Covariance Estimation Considerations

For cross-product analysis with many products:

**Problem**: Estimating Σ for N products with T observations
- N = 20 products, T = 500 days → N/T = 0.04 (OK)
- N = 50 products, T = 200 days → N/T = 0.25 (problematic)

**Solutions** (choose before analysis):
1. **Ledoit-Wolf shrinkage**: λ×I + (1-λ)×S, regularizes toward identity
2. **Factor model**: Assume k latent factors, estimate Σ = BΛB' + D
3. **RMT cleaning**: Remove eigenvalues below Marchenko-Pastur bound

**Factor Adequacy Tests** (run before factorization):
- Bartlett's sphericity: Is Σ ≠ I? (else no point in factor analysis)
- KMO measure: >0.6 required for meaningful factors
- Scree plot: Visual check for number of factors

---

## Multiple Testing Corrections

### The Problem

"Testing 50 product pairs for lead-lag at α=0.05 means you expect 2.5 false positives even under null."

### Correction Methods

| Method | Formula | When to Use |
|--------|---------|-------------|
| Bonferroni | α* = α/m | Conservative, independent tests OK |
| Šidák | α* = 1-(1-α)^(1/m) | Slightly less conservative |
| Holm | Sequential rejection | Uniformly more powerful than Bonferroni |
| Benjamini-Hochberg | Controls FDR at q | Many tests, some false positives OK |
| Romano-Wolf | Bootstrap stepdown | Accounts for dependence |

### Recommended Protocol

```
For M tests across Chinese futures products:

1. Pre-specify M before looking at data
2. Pre-specify correction method:
   - If M < 10: Bonferroni (simple, conservative)
   - If M ≥ 10: BH-FDR with q = 0.05
   - If tests are dependent: Romano-Wolf bootstrap

3. Report:
   - Raw p-values for all M tests
   - Adjusted p-values or FDR q-values
   - Which tests survive correction

4. NEVER:
   - Add tests after seeing data ("let's also try...")
   - Drop tests that didn't work ("we focus on...")
   - Report only significant results
```

### Example: Cross-Product Lead-Lag Battery

```
Pre-Registered Test Battery (M = 12):

1. SC → Brent (night returns)
2. Brent → SC (day returns)
3. BC → CU
4. CU → BC
5. I → RB
6. J → RB
7. IF → CSI 300 ETF
8. Night first 30min → Day returns (RB)
9. Night first 30min → Day returns (CU)
10. Night first 30min → Day returns (SC)
11. Soybean complex: M → Y
12. Oils: P → OI

α = 0.05, BH-FDR correction
Required adjusted p < 0.05 × (rank/12) for significance
```

---

## Out-of-Sample Validation Requirements

### Mandatory Before Any Claim

```
IN-SAMPLE SIGNIFICANCE IS OVERFITTING UNTIL OOS PROVES OTHERWISE.
```

### Validation Protocols

**Time-Series Split** (recommended for lead-lag):
```
Train: 2015-01-01 to 2020-12-31
Gap: 2021-01-01 to 2021-03-31 (avoid leakage)
Test: 2021-04-01 to 2023-12-31

Relationship must be:
1. Significant in-sample (after correction)
2. Same sign out-of-sample
3. Economically meaningful magnitude OOS
```

**Walk-Forward** (for trading strategy):
```
For each month t in test period:
1. Estimate model on data up to t-1
2. Generate prediction for month t
3. Record actual vs predicted
4. Aggregate OOS performance

Report: Sharpe ratio with deflation (Harvey et al.)
```

**Combinatorial Cross-Validation** (for small samples):
```
For relationship with N years of data:
1. Hold out each year sequentially
2. Train on N-1 years, test on held-out year
3. Aggregate across all folds

Stricter than single split, catches year-specific flukes.
```

---

## Effect Size Thresholds

### Minimum Tradeable Effect

"Statistical significance at p<0.01 with 1bp effect is economically irrelevant."

**For lead-lag strategies**:
```
Minimum: 2-3 bps per trade after costs
Chinese futures costs: ~0.5-2 bps each way (product-dependent)
Round-trip: ~1-4 bps

Therefore: Raw signal must generate ≥5 bps to be tradeable
```

**For basis trading**:
```
Half-life < 5 days: Potentially tradeable
Half-life 5-20 days: Marginal, holding costs matter
Half-life > 20 days: Too slow for active trading
```

**Deflated Sharpe Ratio** (Harvey, Liu, Zhu):
```
Given:
- N strategies tested
- Expected max Sharpe under null: E[max(SR)] ≈ √(2×ln(N))

For N = 50 tested relationships:
- Expected spurious max Sharpe ≈ 2.8

Requirement: OOS Sharpe > 2.8 to claim real edge
```

---

## Escalation Protocol

### When to Invoke Causal Analyst

Statistical relationship found → STOP → Escalate before claiming tradeable.

```
REQUIRED BEFORE TRADING CLAIM:

1. Statistical validation (this document):
   - Pre-registered hypothesis
   - Multiple testing correction applied
   - OOS validation passed
   - Effect size above minimum threshold

2. Causal validation (causal-analyst):
   - Mechanism identified
   - Alternative explanations ruled out
   - Persistence argument made
   - Regime change risk assessed

Only after BOTH: Claim tradeable to strategist
```

### Information to Provide Causal Analyst

```
Statistical Handoff Document:

Relationship: [A] leads [B] by [N] ticks/minutes
Statistical evidence:
  - Granger F-stat: X (p = Y, adjusted)
  - Information share: Z%
  - OOS R²: W%
  - Effect magnitude: V bps

NOT ESTABLISHED:
  - Why this relationship exists
  - Whether it will persist
  - Causal direction
  - Alternative explanations

REQUESTED: Mechanism validation before trading implementation
```

---

## Research Hypotheses Registry

### Template for Pre-Registration

```
Date: [YYYY-MM-DD]
Researcher: [name]
Hypothesis ID: [CHN-FUTURES-001]

Statement:
[Exact, falsifiable hypothesis]

Specification:
- Model: [regression/cointegration/Granger]
- Variables: [list with exact definitions]
- Sample: [date range, products]
- Frequency: [500ms/1min/daily]

Statistical Design:
- α: [0.01/0.05]
- Correction: [Bonferroni/BH-FDR/Romano-Wolf]
- OOS method: [time-split/walk-forward/CV]
- Minimum effect: [X bps]

Power Analysis:
- Sample size: [N]
- Detectable effect: [at 80% power]

Registered before data access: [YES/NO]
```

### Active Hypotheses (Examples)

| ID | Hypothesis | Status |
|----|------------|--------|
| CHN-F-001 | SC night return predicts SC day return | Pre-registered, not tested |
| CHN-F-002 | BC-CU basis mean-reverts, HL < 5 days | Pre-registered, not tested |
| CHN-F-003 | Iron ore leads rebar by 1-5 ticks | Pre-registered, not tested |
| CHN-F-004 | IF leads CSI 300 ETF by >1 minute | Pre-registered, not tested |

---

## Appendix: Chinese Terminology for Cross-Product

| English | Chinese | Pinyin |
|---------|---------|--------|
| Basis | 基差 | jīchā |
| Lead-lag | 领先滞后 | lǐngxiān zhìhòu |
| Cointegration | 协整 | xiézhěng |
| Price discovery | 价格发现 | jiàgé fāxiàn |
| Information share | 信息份额 | xìnxī fèn'é |
| Cross-product | 跨品种 | kuà pǐnzhǒng |
| Arbitrage | 套利 | tàolì |
| Spread trading | 价差交易 | jiàchā jiāoyì |
| Night session | 夜盘 | yèpán |
| Day session | 日盘 | rìpán |

---

**Document Version**: 1.0
**Last Updated**: 2025-01-26
**Requires Approval**: User sign-off on statistical methodology before execution
