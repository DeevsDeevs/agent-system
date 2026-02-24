# US Equity Markets — Quick Reference Card

## Venues

| Venue | MIC | Tape | Fee Model | Key Characteristic |
|-------|-----|------|-----------|-------------------|
| NYSE | XNYS | A | Maker-taker | Physical floor; **parity allocation**; DMMs; D-Orders |
| NYSE Arca | ARCX | B/C | Maker-taker | Fully electronic; dominant ETF listing; LMMs; 4AM–8PM |
| NYSE American | XASE | A | Maker-taker | Smaller-cap equities; eDMMs; Early Open Auction 7AM |
| NYSE National | XCIS | A/B/C | **Taker-maker** | Inverted fee model; no auctions |
| NYSE Chicago/Texas | XCHI | A/B/C | Maker-taker | Low market share; no auctions |
| Nasdaq | XNAS | C | Maker-taker | ITCH 5.0; TotalView; M-ELO; Carteret NJ |
| Nasdaq BX | XBOS | B/C | **Taker-maker** | Inverted; targets price-sensitive flow |
| Nasdaq PSX | XPHL | A | Maker-taker | Pro-rata allocation for some securities |
| Cboe BZX | BATS | B/C | Maker-taker | Largest Cboe venue; Secaucus NJ |
| Cboe BYX | BATY | B/C | **Taker-maker** | Inverted Cboe venue |
| Cboe EDGX | EDGX | B/C | Maker-taker | MidPoint extended life orders |
| Cboe EDGA | EDGA | B/C | **Taker-maker** | Inverted; low-cost removing |
| IEX | IEXG | B/C | Maker-taker | 350μs speed bump; Crumbling Quote Indicator |
| MEMX | MEMX | B/C | Maker-taker | Member-owned; lowest latency claims |
| LTSE | LTSE | B/C | Maker-taker | Long-term focused listings |
| MIAX Pearl | EPRL | B/C | Maker-taker | Equity exchange (from options) |

## Key Parameters

| Parameter | Value |
|-----------|-------|
| Minimum tick (≥$1.00) | $0.01 (penny) |
| Minimum tick (<$1.00) | $0.0001 |
| Access fee cap | $0.003/share (Rule 610) |
| Sub-penny quoting | Prohibited ≥$1.00 (Rule 612) |
| LULD bands (Tier 1) | ±5% reference price (±10% open/close) |
| LULD bands (Tier 2) | ±10% reference price (±20% open/close) |
| MWCB Level 1 | −7% S&P 500 → 15-min halt (before 3:25 PM) |
| MWCB Level 2 | −13% S&P 500 → 15-min halt (before 3:25 PM) |
| MWCB Level 3 | −20% S&P 500 → market closed for day |
| Round lot (≤$250) | 100 shares |
| Round lot ($250–$1000) | 40 shares |
| Round lot ($1000–$10000) | 10 shares |
| Round lot (>$10000) | 1 share |

## Session Schedule (Eastern Time)

| Session | Hours | Venues |
|---------|-------|--------|
| Pre-market | 04:00–09:30 | Arca, Nasdaq, select ECNs |
| Regular | 09:30–16:00 | All exchanges |
| Post-market | 16:00–20:00 | Arca, Nasdaq, select ECNs |
| Opening auction | ~09:28–09:30 | NYSE (DMM), Nasdaq (cross) |
| Closing auction | ~15:50–16:00 | NYSE (MOC/LOC 3:50 cutoff), Nasdaq |

## Data Feeds

| Feed | Type | Latency | Content | Cost |
|------|------|---------|---------|------|
| CTA SIP (Tape A/B) | Consolidated | <17μs processing | NBBO + trades | Regulated fees |
| UTP SIP (Tape C) | Consolidated | ~13μs processing | NBBO + trades | Regulated fees |
| Nasdaq ITCH 5.0 | Direct/L3 | Sub-μs co-lo | Order-by-order, full depth, ns timestamps | ~$20K+/mo |
| NYSE XDP | Direct/L3 | Sub-μs co-lo | Order-by-order, full depth, ns timestamps, MPID attribution | ~$20K+/mo |
| Cboe PITCH | Direct/L3 | Sub-μs co-lo | Order-by-order, full depth | ~$15K+/mo |

## Fee Models

| Model | Add (make) | Remove (take) | Venues |
|-------|-----------|--------------|-------|
| Maker-taker | Rebate ~$0.002–0.0032 | Fee ~$0.003 | NYSE, Nasdaq, Arca, BZX, EDGX, IEX |
| Taker-maker (inverted) | Fee ~$0.0003–0.0014 | Rebate ~$0.001–0.002 | NYSE National, Nasdaq BX, BYX, EDGA |

## Effective Spread by Cap Tier

| Tier | Effective Spread (bps) |
|------|----------------------|
| Mega-cap (top 50) | 1–3 |
| Large-cap (S&P 500) | 2–7 |
| Mid-cap (S&P 400) | 5–15 |
| Small-cap (R2000) | 10–30 |
| Micro-cap | 30–200+ |

## Regulatory Timeline

| Date | Event | Impact |
|------|-------|--------|
| 2005-06 | Reg NMS adopted | Penny tick; $0.003 fee cap; sub-penny prohibition |
| 2007-02 | Reg NMS Phase 2 live | Full order protection (Rule 611) |
| 2010-02 | Alternative Uptick Rule (201) | 10% decline triggers short-sale restriction |
| 2010-05 | Flash Crash | Prompted LULD development |
| 2013-04 | LULD Phase I | Price bands replace SSCBs for S&P 500/R1000 |
| 2013-08 | LULD Phase II | All NMS securities; SSCBs retired |
| 2016-10 | Tick Size Pilot | $0.05 tick for ~1,200 small-caps |
| 2018-03 | M-ELO launches | 500ms midpoint holding period |
| 2018-09 | Tick Size Pilot ends | All stocks return to penny tick |
| 2020-03 | COVID MWCB triggers | 4× Level 1 triggers in 10 days |
| 2020-12 | MDI Rule adopted | Round lot redefinition; odd-lot transparency |
| 2023-09 | Dynamic M-ELO | AI-powered holding period (140+ factors) |
| 2024-09 | Tick/Fee reform adopted | Half-penny tick ~1,700 tickers; 10-mil fee cap |
| 2025-11 | New round lots live | Tiered by price: 100/40/10/1 |
| 2026-04 | Odd-lot quotes on SIPs | New BOLO message types |
| 2026-11 | Tick/fee compliance (delayed) | $0.005 tick + $0.001 fee cap |

## Co-Location Map

| DC | Venues | Location |
|----|--------|----------|
| Mahwah, NJ | NYSE, NYSE Arca, NYSE American | ICE campus |
| Carteret, NJ | Nasdaq, Nasdaq BX, Nasdaq PSX | Equinix NY5 |
| Secaucus, NJ | Cboe BZX/BYX/EDGX/EDGA | Equinix NY4/5 |
| Weehawken, NJ | IEX | IEX POP |

## Deep Docs
- [[equity/amer/equity_amer.md|equity_amer.md]]
- [[equity/amer/nasdaq/nasdaq.md|nasdaq.md]]
- [[equity/amer/nyse/nyse.md|nyse.md]]
