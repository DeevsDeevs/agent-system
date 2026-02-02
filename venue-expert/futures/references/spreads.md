# Futures Spread Mechanics Reference

Generic spread mechanics for CME/ICE/global markets. Chinese-specific details in `apac/china/`.

## Calendar Spread Fundamentals

### Naming Conventions

| Format | Example | Meaning |
|--------|---------|---------|
| `{Product}c1-{Product}c2` | NGc1-NGc2 | Front month - Second month |
| `{Product}{MonthYear}-{Product}{MonthYear}` | CLZ24-CLH25 | Dec24 - Mar25 |
| `{Product}{Month}{Month}` | GCZ4G5 | Dec24 - Feb25 |

**Month codes:** F(Jan), G(Feb), H(Mar), J(Apr), K(May), M(Jun), N(Jul), Q(Aug), U(Sep), V(Oct), X(Nov), Z(Dec)

**Convention:** Long spread = buy front, sell back. Positive spread = front > back (backwardation).

### Spread Direction Semantics

```
Buy NGc1-NGc2:  Long front, Short back
Sell NGc1-NGc2: Short front, Long back

Spread widens:  Front outperforms back
Spread narrows: Back outperforms front
```

## CME/ICE Spread Execution

### Execution Mechanisms

| Method | Execution | Atomicity | Notes |
|--------|-----------|-----------|-------|
| Explicit spread order | Spread book + implied | Atomic per fill | Both legs or neither per fill |
| Implied-in | Derived from outrights | Atomic per fill | Exchange calculates |
| Implied-out | Spread creates outright liquidity | Atomic per fill | Reverse direction |
| Block trade | OTC negotiated, reported | Contractual | Off-book |
| EFRP | Off-exchange | Contractual | Simultaneous reporting |

**Critical distinction:** CME/ICE spreads are atomic **per fill**, not all-or-nothing. Partial fills are default behavior.

| Order Type | Behavior |
|------------|----------|
| Day/GTC | Partial fills over time |
| IOC | Fill what's available, cancel rest |
| FOK | All or nothing - truly atomic |

### Implied Matching

CME Globex simultaneously considers:
1. Explicit spread book
2. Implied prices from outright legs
3. Best available combination

No leg risk on any path. Spread price guaranteed per fill.

**Edge case:** Inter-commodity spreads with different tick sizes may have rounding slippage.

## Inter-Commodity Spreads

### Energy Spreads

| Spread | Formula | Exchange | Use Case |
|--------|---------|----------|----------|
| Crack (3-2-1) | 2×RBOB + 1×HO - 3×CL | NYMEX | Refinery margin |
| Crack (2-1-1) | 1×RBOB + 1×HO - 2×CL | NYMEX | Simplified refinery |
| Spark | Power - (Gas × Heat Rate) | Various | Generator margin |
| Frac | C3 (Propane) - NG | NYMEX | NGL economics |

### Agricultural Spreads

| Spread | Formula | Exchange | Use Case |
|--------|---------|----------|----------|
| Crush (Soy) | 11×SoyMeal + 2×SoyOil - Soy | CBOT | Processor margin |
| Wheat | KC-W or W-MW | CBOT/KC | Quality basis |
| Corn-Wheat | C-W | CBOT | Feed substitution |

### Metals Spreads

| Spread | Products | Exchange | Use Case |
|--------|----------|----------|----------|
| Gold-Silver | GC/SI ratio | COMEX | Relative value |
| Copper-Gold | HG/GC | COMEX | Macro indicator |

## Spread Margin Treatment

### CME SPAN Methodology

SPAN calculates spread margin via:
```
Net Margin = max(Long Scan Risk, Short Scan Risk) 
           - Intra-Commodity Spread Credit 
           - Inter-Commodity Spread Credit 
           + Delivery Month Charge
```

**Spread credit is NOT a fixed percentage.** It's a dollar amount based on spread volatility vs outright volatility.

| Spread Type | Typical Effective Reduction |
|-------------|---------------------------|
| Adjacent month calendar | 60-85% |
| Non-adjacent calendar | 40-70% |
| Near delivery | Credit degrades significantly |
| Inter-commodity | Less than intra-commodity |

**Delivery month:** Credit eliminated/reduced as near leg enters delivery phase.

### ICE Methodology

Similar risk-based approach. Product-specific spread credits.

### When Spread Margin Benefit Fails

1. **Cross-exchange positions** - No offset (e.g., NYMEX vs ICE)
2. **Delivery month** - Near leg margin escalates, offset reduced
3. **Non-recognized combinations** - Only approved spreads qualify
4. **Forced liquidation** - Legs liquidated independently

## Roll Dynamics

### Roll Timing by Product Type

| Product | Typical Roll Window |
|---------|-------------------|
| Equity index (CME) | Monday before 3rd Friday quarterly |
| Energy (WTI/Brent) | ~5th-9th business day monthly |
| GSCI tracking | 5th-9th business day monthly |
| BCOM tracking | 6th-10th business day monthly |
| Agricultural | Varies by delivery schedule |

### Volume Migration Pattern

```
T-20: Near month dominant, spread thin
T-10: Volume begins shifting to deferred
T-5:  OI migration accelerates
T-2:  Spread volume peaks
T-0:  Expiry/last trade
```

**Mechanism:** Forced migration (position limits, fund mandates) creates concentrated flow during roll window.

**Caution:** Roll patterns are predictable in timing; profitability requires alpha above transaction costs and bid-ask capture.

### Contango vs Backwardation During Roll

| Structure | Roll Cost | Spread Behavior |
|-----------|-----------|-----------------|
| Contango | Long pays (negative roll yield) | Near < Far, buying spread to roll long |
| Backwardation | Long earns (positive roll yield) | Near > Far, selling spread to roll long |

## Major Spread Products

### CME Listed Calendar Spreads

| Product | Code | Tick | Comments |
|---------|------|------|----------|
| E-mini S&P | ES | 0.25 pts ($12.50) | Most liquid equity spread |
| Crude Oil | CL | $0.01 ($10) | High OI in front spreads |
| Natural Gas | NG | $0.001 ($10) | Seasonal term structure |
| Gold | GC | $0.10 ($10) | Cost of carry dominant |
| Euro | 6E | 0.00005 ($6.25) | Interest rate driven |
| Treasury | ZN, ZB | 1/32 varies | Yield curve plays |

### CME Listed Inter-Commodity Spreads

| Spread | Code | Legs |
|--------|------|------|
| NOB | ZN-ZB | 10Y Note vs 30Y Bond |
| TUT | ZT-ZN | 2Y vs 10Y |
| Crush | ZM+ZL-ZS | Soy complex |
| Crack | RB+HO-CL | Refined products |

### ICE Listed Spreads

| Product | Code | Comments |
|---------|------|----------|
| Brent | B | Deep calendar liquidity |
| WTI-Brent | CL-B | Cross-exchange listed |
| Gasoil | G | European heating oil |

## Position Limits for Spreads

### CME Approach

| Limit Type | Spread Treatment |
|------------|-----------------|
| Speculative limits | Generally net; spreads reduce consumption |
| Accountability levels | Separate from hard limits |
| Spot month | Step-down rules apply (CL: 6000→5000→4000) |
| Spread exemptions | Available via application |

### Reporting

CFTC Large Trader: Spreads reported separately. Commercial spreaders may qualify for hedge exemptions.

## Execution Considerations

### Spread vs Legging

| Approach | Pro | Con |
|----------|-----|-----|
| Spread order | No leg risk, guaranteed price | Less flexible, may miss better prices |
| Legging | Potential price improvement | Full leg risk, requires monitoring |

**Rule of thumb:** Use spread orders for execution efficiency; leg only when you have informational edge on individual leg timing.

### Liquidity Assessment

Check both:
1. **Spread book depth** - Direct spread liquidity
2. **Implied depth** - Available from outright legs

Illiquid spreads may have wide markets but good implied depth from liquid outrights.

## Chinese Futures Spreads (Summary)

Detailed coverage in `apac/china/references/`. Key differences:

| Exchange | Atomic Execution | Margin Offset |
|----------|-----------------|---------------|
| DCE | Yes (SP/SPC commands) | ~50% automatic |
| CZCE | Yes (SPD/IPS commands) | ~50%, application for single-leg |
| SHFE/INE/CFFEX | No - synthetic only | ~50% automatic |

**Cross-exchange (e.g., i-j-rb steel chain):** NO margin offset.

**Index futures (CFFEX):** Intraday close fee = 100x base rate. Day trading spreads cost-prohibitive; use T+1.

## Common Gotchas

1. **Spread direction confusion** - Know if your system uses buy=long-front or buy=long-back
2. **Settlement vs trade price** - Spread settles at official spread price, not trade price
3. **Roll date misalignment** - Front contract may stop trading before you expect
4. **Margin calls during roll** - Position restructuring may trigger margin spikes
5. **Delivery month transition** - Spread margin benefit degrades approaching delivery
6. **Block trade reporting** - OTC spreads need simultaneous leg reporting

## References

- CME SPAN methodology: cmegroup.com/clearing/risk-management
- ICE margin: theice.com/clear-us/risk-management
- Chinese: See `apac/china/` directory
