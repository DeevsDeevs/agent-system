# Contributing a New Venue

## File Placement

```
venue-expert/{asset_class}/{region}/{venue}.md           # standalone (ice.md, eurex.md, hkex.md)
venue-expert/{asset_class}/{region}/{venue}/{venue}.md   # venue with reference docs (nyse/, nasdaq/)
venue-expert/{asset_class}/{region}/{country}/{venue}.md # country-grouped (china/shfe.md)
```

Use a subdirectory when the venue needs its own `references/` folder (specs, regulatory docs).

| Token | Values |
|-------|--------|
| `asset_class` | `equity`, `futures` |
| `region` | `amer`, `emea`, `apac` |
| `country` | only when region has multiple exchanges in one country (e.g. `china`) |
| `venue` | lowercase exchange name (`shfe`, `cme`, `ice`, `nyse`, `hkex`) |

## 12-Section Template

New venues should follow all 12 sections (exemplars: `shfe.md`, `gfex.md`). Older docs deviate. Omit sections only if genuinely N/A.

| # | Section | What Goes Here |
|---|---------|----------------|
| 1 | Identity & Products | MIC, timezone, product table (code/multiplier/tick/hours), operator |
| 2 | Data Characteristics | Feed protocol, encoding, tick timestamps, price encoding quirks, depth |
| 3 | Data Validation Checklist | Sentinel values, known bad fields, filtering rules |
| 4 | Order Book Mechanics | Matching algorithm, modify semantics (queue retain/loss), implied books |
| 5 | Transaction Costs | Fee tiers (maker/taker), exchange fees, clearing fees, spread norms |
| 6 | Position Limits & Margin | Limit tiers, margin model (SPAN/VaR/fixed), hedge exemptions |
| 7 | Regulatory Framework | Regulator, key rules, access restrictions, reporting obligations |
| 8 | Regime Change Database | Historical parameter changes with dates (fees, limits, hours, products) |
| 9 | Failure Modes & Gotchas | Known feed gaps, recovery behavior, common integration mistakes |
| 10 | Market Maker Programs | MM obligations, benefits, tiers, LMM/DMM specifics |
| 11 | Empirical Parameters | Fill rates, cancel rates, typical spreads, queue dynamics |
| 12 | Primary Sources | Official docs, spec PDFs, API references, regulatory filings |

## Research Questions

Answer these before writing. Tables over prose.

### Universal (all venues)

| # | Question |
|---|----------|
| 1 | What matching algorithm? FIFO, pro-rata, hybrid? Modify = queue loss? |
| 2 | What market data protocol? Encoding, transport, depth, implied books? |
| 3 | What are the session hours in UTC? Pre-open, continuous, auction, night? |
| 4 | What are the fee tiers? Maker-taker or flat? Rebate thresholds? |
| 5 | What margin model? SPAN, SPAN 2, VaR, fixed percentage? |
| 6 | What position limits? Per-contract, per-account, near-expiry tightening? |
| 7 | What are the known data quirks? Sentinel values, timestamp resolution, bad fields? |
| 8 | What happens on disconnect? Replay available? Gap recovery mechanism? |
| 9 | Where is the matching engine physically? Co-location options? |
| 10 | Who is the regulator? Key rules affecting electronic trading? |
| 11 | What products trade? Code, multiplier, tick size, contract size, hours? |
| 12 | What market maker programs exist? Obligations, tiers, benefits? |
| 13 | What historical regime changes? Fee/hour/limit changes with dates? |
| 14 | What empirical parameters? Typical spreads, fill rates, queue depths? |

### Futures-specific

| # | Question |
|---|----------|
| F1 | Settlement method? Daily mark, VWAP window, or closing price? |
| F2 | Spread instruments native or synthetic? Implied pricing? |

### Equity-specific

| # | Question |
|---|----------|
| E1 | Auction mechanics? Opening/closing cross, order types eligible? |
| E2 | Market maker obligations? DMM/LMM/eDMM? Parity or time priority? |

## Post-Write Checklist

After writing `{venue}.md`, update these files:

| # | File | Action |
|---|------|--------|
| 1 | `SKILL.md` — L3 File Index | Add row to equity or futures table |
| 2 | `SKILL.md` — Context Detection | Add query pattern → L1/L2/L3 routing row |
| 3 | `matrices/matching_algorithms.md` | Add venue's matching algo, modify semantics |
| 4 | `matrices/latency.md` | Add cross-venue fiber/mw latency; within-DC latency from co-lo specs |
| 5 | `matrices/session_overlaps.md` | Add session hours in UTC |
| 6 | `matrices/tcost_comparison.md` | Add spread/impact/fill-rate/fees |
| 7 | `matrices/data_characteristics.md` | Add feed protocol, encoding, depth, quirks |
| 8 | `cards/{appropriate_card}.md` | Add venue to existing L1 card or create new one |
| 9 | Parent region/country doc | Add venue reference (e.g. `futures_china.md`, `equity_amer.md`) |
| 10 | `SKILL.md` — Debugging Checklist | Add section if new asset class or region |

## Style Rules

- Default to tables; prose permitted for sequential logic (matching waterfalls, recovery sequences)
- First line after `#` title = one-sentence context blurb (what, where, assumes what)
- Use `**bold**` for values that surprise or contradict assumptions
- Link parent doc in blurb (e.g. "Assumes familiarity with `futures_china.md`")
- No filler, no hedging, no "it is worth noting"
