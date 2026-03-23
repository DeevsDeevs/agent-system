# NYSE Exchange Mechanics

**Timezone:** ET (Eastern Time, UTC-5 / UTC-4 DST)

NYSE-specific market microstructure. Assumes familiarity with US equity concepts from `../equity_amer.md`.

## Overview and Role

### NYSE as Operator

| Venue | MIC | Tape | Fee Model | Characteristics |
|-------|-----|------|-----------|-----------------|
| NYSE | XNYS | A | Maker-taker | Physical floor; parity allocation; DMMs; D-Orders |
| NYSE Arca | ARCX | B&C | Maker-taker | Fully electronic; dominant ETF listing; LMMs; 4AM-8PM |
| NYSE American | XASE | — | Maker-taker | Smaller-cap; eDMMs; Early Open Auction 7AM |
| NYSE National | XCIS | — | Taker-maker (inverted) | Fully electronic; no auctions |
| NYSE Chicago/Texas | XCHI | — | Maker-taker | Rebranded NYSE Texas (2025); no auctions; low share |

### Listing vs Trading

NYSE is both:
- **Listing venue** for NYSE-listed securities (Tape A)
- **Trading venue** for all NMS stocks

NYSE-listed securities trade on all NMS exchanges. Consolidated data via CTA SIP (Tape A).

## Matching Engine — Pillar Platform

All NYSE Group equity markets run on **Pillar** from **Mahwah, NJ**.

NYSE Arca, American, National, and Texas use standard **price-time priority**. NYSE (Tape A) uses a unique **parity allocation model**.

### Parity Allocation Model

After market orders (time priority), displayed orders at the same price are allocated on **parity** among three participant types:

| Participant | Description |
|-------------|-------------|
| Floor Broker | Physical floor representatives |
| DMM | Designated Market Maker |
| Book Participant | All electronic limit orders (aggregated as one) |

**15% setter priority:** The participant who sets the best price receives 15% of the first execution before the parity wheel engages.

**Implication:** Floor brokers and DMMs can effectively trade ahead of earlier electronic limit orders. This invalidates standard price-time priority assumptions in microstructure models applied to NYSE Tape A data.

## DMM (Designated Market Maker)

### Obligations (Rule 104)

| Parameter | Tier 1 (S&P 500) | Tier 2 | Tier 3 |
|-----------|-------------------|--------|--------|
| Designated Percentage | 8% | 28% | 30% |
| NBBO quoting minimum (non-ETP) | ≥15% of day | ≥15% of day | ≥15% of day |
| NBBO quoting minimum (ETP) | ≥25% of day | ≥25% of day | ≥25% of day |
| Minimum depth | 1 round lot each side | 1 round lot | 1 round lot |

Must maintain continuous two-sided quotes. After Aggressing Transaction, must re-enter opposite side at or before applicable Price Participation Point (PPP).

### DMM Economics

| Revenue Source | Detail |
|----------------|--------|
| Adding credits | Up to $0.0035/share (tiered) |
| Monthly rebates | Flat rebates for less-active securities |
| Market data | Revenue sharing |
| Capital requirement | $125M base across all units + per-security add-ons |

### Facilities

DMMs facilitate openings, closings, and reopenings — receiving aggregate order information for price discovery. No algorithmic collars on opening — DMM selects opening price.

### Stress Behavior Evidence

**Flash Crash (May 6, 2010):** Buy-side depth fell to ~25% midday levels, sell-side ~15%. Market makers left stub quotes (1c bids) executed against. NYSE specialists who remained helped curtail turmoil (MacKenzie 2015).

**NYSE halt (Jul 8, 2015):** Anand et al. (2017, JFE) used this as natural experiment — removing DMMs caused liquidity to decrease market-wide across all exchanges. Removing voluntary EDGX providers had no measurable effect.

**COVID (Mar 2020):** NYSE floor closed Mar 23, fully electronic. NYSE-listed stocks experienced worse liquidity deterioration than Nasdaq-listed during this period, partly due to DMM inability to operate on floor.


## Opening and Closing Auctions

### Opening Auction

DMM-facilitated with no modification cutoffs.

| Time | Event |
|------|-------|
| 8:00 AM | Imbalance publication begins (90 min before open) |
| 9:30 AM | Opening auction executes |

No algorithmic collars — DMM selects opening price.

### Closing Auction

| Time | Event |
|------|-------|
| 3:50 PM | MOC/LOC entry cutoff; NOII begins (every 1 second) |
| 3:59:50 PM | D-Order entry cutoff |
| 4:00 PM | Closing auction executes |

**D-Orders** (floor broker discretionary orders): enter until 3:59:50 PM, account for **>46% of NYSE closing auction volume**.

Closing auction captures ~9-10% of daily consolidated volume in NYSE-listed securities (2024), up from ~3% in 2010.


## Halts and Reopenings

NYSE-specific halt mechanics:
- DMM-facilitated reopenings with aggregate order information
- Floor operations during halts (when floor is open)
- Standard LULD and MWCB apply (see `../equity_amer.md` [[equity/amer/equity_amer.md|equity_amer.md]])

## Market Data: XDP

NYSE's **XDP Integrated Feed** provides:

| Feature | Detail |
|---------|--------|
| Depth | Full depth-of-book (every visible order individually, not aggregated) |
| Timestamps | Nanosecond precision |
| Timestamp method | Source Time Reference (1/sec, seconds) + nanosecond offset per message |
| Attribution | Firm MPID on Add Order messages |
| Symbol Indexes | Stable across days and markets |

### Key Message Types

| Type | Code | Description |
|------|------|-------------|
| Add Order | 100 | New order |
| Modify | 101 | Order modification |
| Delete | 103 | Order removal |
| Replace | 104 | Order replacement |
| Execution | 220 | Trade |
| Non-Displayed Trade | 221 | Hidden execution |
| Cross Trade | 222 | Auction print |
| Imbalance | 230 | Auction imbalance |

**Gotcha:** XDP timestamp reconstruction requires tracking Source Time Reference messages — missing one corrupts all subsequent timestamps.


## Fee Structure

### NYSE Maker-Taker

| Role | Typical Rate |
|------|-------------|
| DMM adding | Up to $0.0035/share |
| SLP adding | Up to ~$0.0032/share |
| Standard adding | ~$0.0020/share |
| Removing | ~$0.0030/share |

### NYSE National (Inverted)

Taker-maker model — removing receives rebate, adding pays fee. Creates different adverse selection dynamics.


## Parity Allocation Deep Dive

Standard price-time priority (used by all other US exchanges): first order at best price wins.

NYSE parity: after price priority, displayed orders split on **equal parity** among active participant types. Within each participant type, standard time priority applies.

### Practical Impact

1. A floor broker joining a price level late can receive equal allocation with the Book Participant (all prior electronic orders aggregated)
2. DMM always participates in parity alongside other types
3. Setter (15%) bonus rewards price improvement — incentivizes aggressive quoting
4. Depth-of-book analysis must account for parity — queue position models calibrated on price-time venues are biased for NYSE


## Pillar Migration Timeline

| Date | Event |
|------|-------|
| Q3 2015 | NYSE Arca Equities migrated to Pillar |
| Jan 24, 2022 | NYSE Tape A equities phased migration begins |
| Oct 2023 | NYSE American Options completes — all NYSE Group on Pillar |
| Jun 2, 2025 | FINRA/NYSE TRF migrated to Pillar |


## Empirical Notes

### Spread Recovery Asymmetry

After extreme intraday price changes, NYSE bid-ask spreads widen so much that the large widening eliminates most profits from a contrarian strategy. Nasdaq spreads stay almost constant, yielding significant short-term abnormal profits (Lillo & Farmer studies).


### DMM Behavior Under Stress

Menkveld (2013): HFT market makers earn ~EUR 0.88/trade gross but can withdraw rapidly during stress. DMMs (obligated) cannot — demonstrating structural value during Flash Crash and 2015 halt.


## Gotchas Checklist

1. **Parity model** — Invalidates price-time priority assumptions for NYSE Tape A
2. **D-Orders** — Invisible until near close but dominate auction volume (46%)
3. **XDP timestamp** — Must track Source Time Reference; missing one corrupts all subsequent
4. **National inverted** — Different adverse selection dynamics from standard maker-taker
5. **DMM obligation changes** — 2008 specialist->DMM, 2019 Aggressing Transaction redef, 2023 modernization
6. **Floor closure** — COVID Mar 23 2020 fully electronic; affects DMM contribution analysis
7. **Pillar migration** — Phased over years; pre-Pillar data has different characteristics
8. **Setter priority** — 15% bonus creates incentive structures absent at other venues

## References

See parent directory `../` for shared US equity references:
- `../equity_amer.md` — US equity market structure overview
- `../references/regulatory/sec_reg_nms.md` — Reg NMS rules
- `../references/specs/sip_specs.md` — SIP specifications
