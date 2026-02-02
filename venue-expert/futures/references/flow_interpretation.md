# Flow Interpretation Reference

**Default stance:** Assume large futures flow is non-directional until proven otherwise.

---

## 1. The Paradigm Shift

**In equities:** $1B purchase of Surgut Nefte Gas Pref implies directional conviction. Someone believes SNGSP will go up. Period.

**In futures:** $1B short in AUDc1 almost never means bearish on AUD beyond a few hours.

Why? Futures exist primarily to TRANSFER RISK, not express views:
- Australian miner shorts AUD to lock USD revenue — bullish on their business
- Pension fund sells ES to reduce equity beta — rebalancing, not bearish
- Treasury basis trader shorts ZN — actually LONG duration via cash
- Oil producer shorts CL 12 months out — hedging production, not calling top

**The mental model:**
> When you see someone selling futures, first question: what are they BUYING?
> The short is often the hedge, not the bet.

**Burden of proof** is on directional interpretation. You must actively disprove non-directional explanations.

---

## 2. Who Trades Futures and Why

| Participant | Why They Trade | Directional? | Approx Share |
|-------------|---------------|--------------|--------------|
| **Commercial hedgers** | Lock production/consumption prices | No | 40-60% (cmdty) |
| **Basis/arb traders** | Exploit cash-futures pricing gaps | No | 20-40% (rates) |
| **Index funds/ETFs** | Track benchmark, roll mechanically | No | 10-15% |
| **Delta hedgers** | Neutralize options gamma | No (reactive) | 5-15% |
| **Speculators** | Directional view | **Yes** | 15-30% |

**Implication:** Only 15-30% of futures flow represents directional views. The rest is mechanical, hedging, or arbitrage.

### Commercial Hedging by Sector

| Sector | Products | Typical Hedge Tenor |
|--------|----------|---------------------|
| Oil producers | WTI, Brent | 12-24 months |
| Refiners | Crack spreads | 1-12 months |
| Miners | Base metals | 6-18 months |
| Ag processors | Grains, oilseeds | Crop year |
| Corporates | FX futures | Quarterly |

---

## 3. Liquid Hours ≠ Open Hours

ES trades 23 hours/day. Signal quality is NOT equal across those 23 hours.

**Why it matters:**
- Thin markets = noise, false breakouts, wider spreads
- Institutional flow concentrates in specific windows
- 10,000 contracts at 3am means something different than at 10am

**The distinction:**
- **Open hours:** Exchange accepts orders
- **Liquid hours:** Tight spreads, institutional participation, reliable fills
- **Primary discovery:** When underlying cash market actually trades

### US Products

| Product | Exchange | Open Hours | Liquid Window (CT) | Primary Discovery |
|---------|----------|------------|-------------------|-------------------|
| ES | CME | Sun 5pm-Fri 4pm | 8:30am-3:15pm | US RTH |
| CL | NYMEX | Sun 5pm-Fri 4pm | 8:00am-2:30pm | US/London overlap |
| GC | COMEX | Sun 5pm-Fri 4pm | 7:20am-1:30pm | London/NY overlap |
| ZB/ZN | CBOT | Sun 5pm-Fri 4pm | 7:00am-2:00pm | US RTH |

### Chinese Products

**Chinese venues are NOT "Asian overnight noise" — they ARE primary price discovery for their products. Full weight.**

| Product | Exchange | Day Session | Night Session | Primary Volume |
|---------|----------|-------------|---------------|----------------|
| cu (copper) | SHFE | 9:00-15:00 | 21:00-01:00 | Night (LME overlap) |
| i (iron ore) | DCE | 9:00-15:00 | 21:00-23:00 | Day session |
| IF (CSI 300) | CFFEX | 9:15-15:00 | None | **This IS the signal** |

### European Products

| Product | Exchange | Core Hours (CET) | Primary Discovery |
|---------|----------|------------------|-------------------|
| FESX | Eurex | 8:00-22:00 | 9:00-17:30 |
| FGBL | Eurex | 8:00-22:00 | 8:30-17:15 |
| Brent | ICE | 1:00-23:00 | 8:00-18:30 |

### Session Quality Weights (ES-centric)

| Session | Time (CT) | Signal Weight | Why |
|---------|-----------|---------------|-----|
| US RTH | 8:30am-3:15pm | 1.0 | Highest institutional participation |
| US Open | 8:30am-10:00am | 1.0-1.2 | Incorporates overnight info |
| European Overlap | 2:00am-8:30am | 0.6-0.8 | Quality flow, thinner |
| Asian | 5:00pm-2:00am | 0.3-0.5 | Thin, more false breakouts |

**Caveat:** Weights are for US equity futures. For SHFE copper or DCE iron ore, Chinese sessions deserve FULL weight.

---

## 4. Non-Directional Mechanisms

| Motivation | Mechanism | Observable Signature |
|------------|-----------|---------------------|
| **Rolling hedges** | Producers extending protection | Calendar spread volume, OI migration |
| **Basis trading** | Long cash + short futures | Repo spike, CTD concentration |
| **Calendar spreads** | Term structure plays | Spread vol > outright, minimal net delta |
| **Delta hedging** | Options MM neutralizing gamma | Reactive to spot, opposite direction, OpEx timing |
| **ETF arbitrage** | AP premium/discount arb | EOD clustering, simultaneous ETF/futures |
| **Index rebalancing** | Reconstitution flows | Pre-announced dates (Russell June, quarterly) |
| **Position limits** | Forced exits near limits | Spot month approach |

### Treasury Basis Trade (Why Shorts ≠ Bearish)

$1B Treasury futures short looks bearish. Usually isn't.

**Mechanics:**
1. Basis trader buys cash Treasury (funded via repo)
2. Shorts Treasury futures to hedge duration
3. Profits from futures rolling down to cash
4. Position is market-neutral (long cash, short futures)

**Scale:** Basis trades = ~50% of hedge fund Treasury positions at peak. $500B+ gross exposure.

**2018-2019:** Massive short futures buildup was primarily basis trades absorbing QT supply. Hedge funds bought $428B in Treasuries; 91% attributed to basis traders.

**Real-time identification problem:** You cannot distinguish basis from directional using futures data alone. Requires visibility into repo borrowing, Treasury holdings, CTD concentration. Post-hoc only.

---

## 5. When Flow IS Informative

Flow is potentially directional when ALL conditions hold:
- Position building over multiple sessions (not single-day spike)
- Low calendar spread ratio (<15%)
- >15 days to contract expiry
- Not within roll window or OpEx week
- OI change directionally aligned with price
- No visible paired cash/repo activity

### Decision Tree

```
Large flow observed
    |
    v
Within known roll window? --> YES --> Non-informative (roll)
    | NO
    v
Calendar spread ratio >25%? --> YES --> Non-informative (spread/hedge)
    | NO
    v
<7 days to expiry? --> YES --> Non-informative (gamma/delivery)
    | NO
    v
Simultaneous cash/repo activity? --> YES --> Non-informative (basis)
    | NO
    v
OpEx week + high gamma? --> YES --> Non-informative (delta hedge)
    | NO
    v
Persistence <15 min? --> YES --> Insufficient signal
    | NO
    v
Cumulative <2% ADV? --> YES --> Insufficient signal
    | NO
    v
OI-price aligned? --> YES --> POTENTIALLY INFORMATIVE (verify no news, check COT)
              --> NO --> Mixed signal, discount
```

**If any box fails:** High probability non-directional. Discount signal.

**If all boxes pass:** Investigate further. Still may be wrong.

### Quantitative Thresholds (Heuristics)

| Metric | Non-Informative | Ambiguous | Potentially Informative |
|--------|-----------------|-----------|------------------------|
| Calendar spread % | >30% | 15-30% | <15% |
| Days to expiry | <7 | 7-15 | >15 |
| Flow persistence | <15 min | 15-60 min | >60 min, multi-session |
| Cumulative flow/ADV | <2% | 2-5% | >5% |

**Warning:** These are practitioner heuristics, not empirically validated.

---

## 6. OI-Price Patterns

| OI | Price | Common Interpretation | Reality Check |
|----|-------|----------------------|---------------|
| Up | Up | New longs entering | Could be: hedgers, basis opens, forced covering |
| Up | Down | New shorts entering | Could be: hedgers, basis opens |
| Down | Up | Short covering | Could be: basis closes, both sides exiting |
| Down | Down | Long liquidation | Could be: basis closes, both sides exiting |

**These are correlations, not causation.** No predictive validity without lag analysis.

---

## 7. False Positive Case Studies

| Case | What It Looked Like | What It Was | Why Misread |
|------|---------------------|-------------|-------------|
| Treasury 2018-19 | HF shorts = rate bet | Basis trades (long cash, short futures) | Cash leg invisible |
| ES March 2020 | Heavy buying = conviction | ETF AP hedging during record flows | Mechanical |
| Gold 2016-17 | COMEX shorts = bearish | COMEX-SGE arbitrage | Shanghai premium invisible |
| WTI Apr 2020 | Negative price = panic | USO ETF forced roll + position limit breach | Structure, not sentiment |
| DCE iron ore 2016 | Volume explosion = speculation | Steel mill hedging + basis trades | Commercial vs spec unclear |

**Selection bias warning:** These are cases where non-directional interpretation was correct. Cases where flow WAS directional are not documented. No base rate available.

---

## 8. Caveats and Limitations

1. **Crisis regimes invalidate everything.** Basis trades blow up when convergence fails (2008, 2020 March). Framework assumes orderly markets.

2. **Thresholds are heuristics.** 5% ADV, 30-minute persistence, 30% spread ratio — practitioner rules-of-thumb, not validated cutoffs.

3. **Identification is weak.** Distinguishing hedging from speculation requires data not available to futures-only observers.

4. **Post-hoc bias.** Case studies selected for where non-directional interpretation was vindicated.

5. **US-centric calibration.** Chinese, European venues have different participant structures.

6. **Evolving patterns.** Roll front-running, session characteristics adapt as participants learn.

---

## Quick Reference Checklist

**Informative flow requires ALL:**
- [ ] Not in roll window
- [ ] Spread ratio <15%
- [ ] >15 days to expiry
- [ ] Persistence >60 min
- [ ] Multi-session accumulation
- [ ] OI-price aligned
- [ ] No OpEx gamma
- [ ] No visible paired activity

**When all boxes checked:** Investigate further.

**When any box fails:** Default non-directional.
