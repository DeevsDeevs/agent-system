---
name: venue-expert
description: >
  This skill should be used when the user asks about "market microstructure",
  "exchange mechanics", "order book", "auction", "NBBO", "Reg NMS", "trading venue",
  "halt", "LULD", "tick size", "maker-taker", "price-time priority", "SIP", "direct feed",
  "TRF", "wholesaler", "PFOF", "best execution", "trade-through", "ISO", "opening cross",
  "closing cross", "NOII", "ITCH", "OUCH", or mentions specific exchanges (Nasdaq, NYSE,
  CME, Binance, SHFE, DCE, CZCE, CFFEX, INE, etc.).

  For Chinese futures: "CTP", "综合交易平台", "夜盘", "night session", "看穿式监管",
  "position limits", "持仓限额", queue position in Chinese markets, or Chinese product
  codes (rb, cu, sc, if, ic, i, j, ta, ma, etc.).

  Provides hierarchical venue expertise for research and debugging trading systems.
---

# Venue Expert

3-layer microstructure knowledge base for trading venues.

## Layer Navigation

| Layer | Dir | Purpose | When to Use |
|-------|-----|---------|-------------|
| L1 Cards | `cards/` | 30-sec venue overview | Quick lookup, orientation |
| L2 Matrices | `matrices/` | Cross-venue comparison | Comparing venues, finding arb |
| L3 Deep Docs | existing hierarchy | Full venue documentation | Deep research, debugging |

## L1 Card Index

| Card | Path | Coverage |
|------|------|----------|
| US Equity | `cards/us_equity.md` | 16 exchanges, SIPs, fee models, LULD, auctions, co-lo |
| Chinese Futures | `cards/chinese_futures.md` | 6 exchanges (SHFE/DCE/CZCE/CFFEX/INE/GFEX), CTP, sessions, fees, spreads |
| CME Group | `cards/cme.md` | 4 exchanges (CME/CBOT/NYMEX/COMEX), MDP 3.0, matching algos, SPAN 2 |
| Global Venues | `cards/global_venues.md` | ICE, Eurex, SGX, HKEX, GFEX overview |

## L2 Matrix Index

| Matrix | Path | Coverage |
|--------|------|----------|
| Matching Algorithms | `matrices/matching_algorithms.md` | FIFO/Pro-Rata/Allocation across all venues; modify semantics; LMM/DMM |
| Latency | `matrices/latency.md` | Cross-venue fiber/microwave; within-DC; exchange matching latency |
| Session Overlaps | `matrices/session_overlaps.md` | All venues in UTC; overlap windows; cross-venue arb timing |
| Transaction Cost | `matrices/tcost_comparison.md` | Spreads, impact, fill rates, cancel rates, recovery across venues |
| Data Characteristics | `matrices/data_characteristics.md` | Feed protocols, encoding, depth, timestamps, quirks per venue |

## Context Detection

| Query Pattern | L1 Card | L2 Matrix | L3 Deep Doc |
|-------|---------|-----------|-------------|
| US equity overview, venues, fees | `cards/us_equity.md` | — | [[equity/amer/equity_amer.md\|equity_amer.md]] |
| Nasdaq ITCH, OUCH, crosses | `cards/us_equity.md` | `matrices/data_characteristics.md` | [[equity/amer/nasdaq/nasdaq.md\|nasdaq.md]] |
| NYSE, DMM, parity, XDP | `cards/us_equity.md` | `matrices/matching_algorithms.md` | [[equity/amer/nyse/nyse.md\|nyse.md]] |
| Chinese futures, CTP, 夜盘 | `cards/chinese_futures.md` | — | [[futures/apac/china/futures_china.md\|futures_china.md]] |
| SHFE metals, CloseToday | `cards/chinese_futures.md` | — | [[futures/apac/china/shfe.md\|shfe.md]] |
| DCE iron ore, stop orders | `cards/chinese_futures.md` | — | [[futures/apac/china/dce.md\|dce.md]] |
| CZCE 3-digit codes, UpdateMillisec=0 | `cards/chinese_futures.md` | `matrices/data_characteristics.md` | [[futures/apac/china/czce.md\|czce.md]] |
| CFFEX index futures, restrictions | `cards/chinese_futures.md` | — | [[futures/apac/china/cffex.md\|cffex.md]] |
| INE crude oil, foreign access | `cards/chinese_futures.md` | — | [[futures/apac/china/ine.md\|ine.md]] |
| GFEX silicon, lithium, palladium | `cards/chinese_futures.md` / `cards/global_venues.md` | — | [[futures/apac/china/gfex.md\|gfex.md]] |
| CME overview, MDP 3.0, SPAN | `cards/cme.md` | — | [[futures/amer/cme.md\|cme.md]] |
| CME matching, FIFO vs Pro-Rata | `cards/cme.md` | `matrices/matching_algorithms.md` | [[futures/amer/cme.md\|cme.md]] |
| CME settlement, VWAP window | `cards/cme.md` | — | [[futures/amer/cme.md\|cme.md]] |
| ICE Brent, Basildon | `cards/global_venues.md` | `matrices/latency.md` | [[futures/emea/ice.md\|ice.md]] |
| Eurex, EOBI, FGBL, FESX | `cards/global_venues.md` | `matrices/matching_algorithms.md` | [[futures/emea/eurex.md\|eurex.md]] |
| SGX iron ore, TITAN, ITCH | `cards/global_venues.md` | `matrices/latency.md` | [[futures/apac/sgx.md\|sgx.md]] |
| HKEX broker queue, OMD-C | `cards/global_venues.md` | `matrices/data_characteristics.md` | [[equity/apac/hkex.md\|hkex.md]] |
| Matching algorithm comparison | — | `matrices/matching_algorithms.md` | — |
| Latency, microwave, fiber | — | `matrices/latency.md` | — |
| Session overlaps, trading hours | — | `matrices/session_overlaps.md` | — |
| Spread, tcost, market impact | — | `matrices/tcost_comparison.md` | — |
| Data feed, protocol, quirks | — | `matrices/data_characteristics.md` | — |
| Queue position, fill rate | — | `matrices/tcost_comparison.md` | [[futures/apac/china/references/models/queue_position.md\|queue_position.md]] |
| Regime changes, regulatory | `cards/chinese_futures.md` / `cards/us_equity.md` | — | [[futures/apac/china/references/regime_changes.md\|regime_changes.md]] |
| Generic futures concepts | — | — | [[futures/futures.md\|futures.md]] |
| Generic equity concepts | — | — | [[equity/equity.md\|equity.md]] |
| Spread execution, calendar spreads | — | — | [[futures/references/spreads.md\|spreads.md]] |
| Flow interpretation, OI patterns | — | — | [[futures/references/flow_interpretation.md\|flow_interpretation.md]] |

## L3 File Index

### Equity

| Path | Description |
|------|-------------|
| [[equity/equity.md\|equity.md]] | Equity market fundamentals (CLOB, order types, sessions) |
| [[equity/amer/equity_amer.md\|equity_amer.md]] | US equity market structure (Reg NMS, NBBO, SIP, TRF) |
| [[equity/amer/nasdaq/nasdaq.md\|nasdaq.md]] | Nasdaq exchange mechanics (ITCH, OUCH, crosses) |
| [[equity/amer/nasdaq/references/specs/itch_protocol.md\|itch_protocol.md]] | ITCH 5.0 protocol specification |
| [[equity/amer/nasdaq/references/specs/ouch_protocol.md\|ouch_protocol.md]] | OUCH 4.2/5.0 order entry spec |
| [[equity/amer/nasdaq/references/specs/totalview.md\|totalview.md]] | TotalView product details |
| [[equity/amer/nasdaq/references/regulatory/nasdaq_rules.md\|nasdaq_rules.md]] | Nasdaq rulebook highlights |
| [[equity/amer/references/regulatory/sec_reg_nms.md\|sec_reg_nms.md]] | Reg NMS overview |
| [[equity/amer/references/regulatory/finra_rules.md\|finra_rules.md]] | FINRA rules reference |
| [[equity/amer/references/regulatory/rule_605_606.md\|rule_605_606.md]] | Disclosure rules (605/606) |
| [[equity/amer/references/specs/sip_specs.md\|sip_specs.md]] | SIP specifications |
| [[equity/amer/nyse/nyse.md\|nyse.md]] | NYSE mechanics (DMM, parity, XDP, auctions) |
| [[equity/apac/hkex.md\|hkex.md]] | HKEX equity mechanics (broker queue, OMD-C, Stock Connect) |
| `equity/emea/lse/` | London Stock Exchange — planned |

### Futures

| Path                                                                                          | Description                                                   |
| --------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| [[futures/futures.md\|futures.md]]                                                            | Futures market fundamentals (margin, settlement, rolls)       |
| [[futures/references/spreads.md\|spreads.md]]                                                 | Calendar/inter-commodity spread mechanics (CME/ICE)           |
| [[futures/references/flow_interpretation.md\|flow_interpretation.md]]                         | Flow analysis framework                                       |
| [[futures/apac/futures_apac.md\|futures_apac.md]]                                             | APAC futures overview                                         |
| [[futures/apac/china/futures_china.md\|futures_china.md]]                                     | Chinese futures main doc (CTP, 6 exchanges, regulatory)       |
| [[futures/apac/china/shfe.md\|shfe.md]]                                                       | SHFE specifics (metals, CloseToday)                           |
| [[futures/apac/china/dce.md\|dce.md]]                                                         | DCE specifics (iron ore, stop orders)                         |
| [[futures/apac/china/czce.md\|czce.md]]                                                       | CZCE specifics (3-digit codes, UpdateMillisec=0)              |
| [[futures/apac/china/cffex.md\|cffex.md]]                                                     | CFFEX specifics (index futures, restrictions)                 |
| [[futures/apac/china/ine.md\|ine.md]]                                                         | INE specifics (crude oil, foreign access)                     |
| [[futures/apac/china/gfex.md\|gfex.md]]                                                       | GFEX specifics (silicon, lithium, palladium, mixed ownership) |
| [[futures/apac/china/references/specs/ctp_market_data.md\|ctp_market_data.md]]                | CTP struct specification                                      |
| [[futures/apac/china/references/specs/data_quality_checklist.md\|data_quality_checklist.md]]  | Validation checklist                                          |
| [[futures/apac/china/references/specs/ctp_versions.md\|ctp_versions.md]]                      | CTP SDK version history and breaking changes                  |
| [[futures/apac/china/references/specs/failure_modes.md\|failure_modes.md]]                    | Failure mode catalog                                          |
| [[futures/apac/china/references/models/queue_position.md\|queue_position.md]]                 | Queue estimation models                                       |
| [[futures/apac/china/references/models/trade_direction.md\|trade_direction.md]]               | Trade direction inference                                     |
| [[futures/apac/china/references/models/causal_analysis.md\|causal_analysis.md]]               | Causal identification framework                               |
| [[futures/apac/china/references/models/cross_product_analysis.md\|cross_product_analysis.md]] | Cross-product patterns                                        |
| [[futures/apac/china/references/models/spreads.md\|spreads.md]]                               | Chinese spread execution (CTP, legging risk)                  |
| [[futures/apac/china/references/regime_changes.md\|regime_changes.md]]                        | Regime change database                                        |
| [[futures/amer/cme.md\|cme.md]]                                                               | CME Group mechanics (MDP 3.0, matching, SPAN, settlement)     |
| [[futures/emea/ice.md\|ice.md]]                                                               | ICE Futures Europe mechanics (Brent, iMpact, Basildon)        |
| [[futures/emea/eurex.md\|eurex.md]]                                                           | Eurex mechanics (EOBI, T7, volatility interruptions)          |
| [[futures/apac/sgx.md\|sgx.md]]                                                               | SGX mechanics (iron ore, TITAN, ITCH)                         |
| `futures/apac/hkex/`                                                                          | HKEX derivatives — planned                                    |

## Debugging Checklist

### US Equity
1. **Feed issues** — Check sequence gaps, timestamp alignment, halt state handling
2. **Auction issues** — Verify order type eligibility, cutoff times, NOII parsing
3. **Execution issues** — Validate tick/lot compliance, fee tier, priority rules
4. **Regulatory issues** — Confirm trade-through protection, best execution logic

### Chinese Futures (CTP)
1. **Data issues** — DBL_MAX validation (1.7976931348623157e+308), CZCE UpdateMillisec=0, night replay filtering
2. **Session issues** — TradingDay vs ActionDay semantics, 21:00 reset, trading breaks (10:15–10:30)
3. **Order issues** — CloseToday/CloseYesterday (SHFE/INE), cancel-replace queue loss, DCE stop orders
4. **Auth issues** — 看穿式监管 AppID/AuthCode, CTP version >= 6.3.15, physical machine required
5. **Gap issues** — CTP has NO replay; reconnection gaps are permanent data loss

### CME Group
1. **Feed issues** — MDP 3.0 sequence gaps; use Feed A/B arbitration first, then UDP snapshot recovery
2. **Book issues** — Implied depth = 2 (not 10); consolidate direct + implied books separately
3. **Matching issues** — Check per-product algorithm (F/K/A/C/Q/O); FIFO qty-down retains priority
4. **Margin issues** — SPAN 2 migration in progress; energy already on VaR-based; check asset class status
5. **Settlement issues** — ES/NQ window may have shifted; verify with CME GCC before production
