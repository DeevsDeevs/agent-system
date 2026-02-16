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

Hierarchical microstructure knowledge base for trading venues. Primary use cases: research, debugging, and building trading systems.

## Purpose

Provide deep venue-specific expertise for:
- Quants building execution models and alpha signals
- Developers implementing feed handlers and order entry
- Researchers studying market microstructure
- Debuggers diagnosing trading system issues

## Hierarchy Model

Knowledge is organized in an inheritance hierarchy:

```
Asset Class (equity, futures, crypto, fx)
    |
    v
Geography (amer, emea, apac)
    |
    v
Exchange (nasdaq, nyse, cme, binance)
```

Each level inherits concepts from its parent. Exchange-level files assume familiarity with geo-level and asset-class-level concepts.

## Current Coverage

**Implemented paths:**
- `equity/` - Equity market fundamentals
- `equity/amer/` - US equity market structure (Reg NMS, NBBO, SIP, TRF)
- `equity/amer/nasdaq/` - Nasdaq-specific mechanics (ITCH, OUCH, crosses)
- `futures/` - Futures market fundamentals
- `futures/apac/` - APAC futures overview
- `futures/apac/china/` - Chinese futures (CTP, 5 exchanges, regulatory)
- `futures/apac/china/shfe/` - SHFE metals/energy
- `futures/apac/china/dce/` - DCE ferrous/agricultural
- `futures/apac/china/czce/` - CZCE agricultural/chemicals
- `futures/apac/china/cffex/` - CFFEX financial futures
- `futures/apac/china/ine/` - INE internationalized products

**Planned paths:**
- `equity/amer/nyse/` - NYSE mechanics
- `equity/emea/lse/` - London Stock Exchange
- `futures/amer/cme/` - CME Group
- `crypto/binance/` - Binance exchange

## Navigation

### Context Detection

Route to appropriate depth based on query specificity:

| Query Pattern | Target File |
|---------------|-------------|
| Generic equity concepts | `equity/equity.md` |
| US market structure, Reg NMS, NBBO | `equity/amer/equity_amer.md` |
| Nasdaq-specific (ITCH, NOII, crosses) | `equity/amer/nasdaq/nasdaq.md` |
| Generic futures concepts | `futures/futures.md` |
| APAC futures overview | `futures/apac/futures_apac.md` |
| Chinese futures, CTP, 夜盘 | `futures/apac/china/futures_china.md` |
| SHFE-specific (metals, CloseToday) | `futures/apac/china/shfe/shfe.md` |
| DCE-specific (iron ore, stop orders) | `futures/apac/china/dce/dce.md` |
| CZCE-specific (3-digit years, UpdateMillisec=0) | `futures/apac/china/czce/czce.md` |
| CFFEX-specific (index futures, restrictions) | `futures/apac/china/cffex/cffex.md` |
| INE-specific (crude oil, foreign access) | `futures/apac/china/ine/ine.md` |

### Drill-Down Behavior

Start at the most specific applicable level. Reference parent concepts without repeating them. For example, when discussing Nasdaq auctions, assume familiarity with US equity auction concepts from `equity_amer.md`.

## Reference Organization

Each level has a `references/` directory with subdirectories:

- `regulatory/` - Rules, regulations, compliance guidance
- `specs/` - Protocol specifications, data formats

Reference files provide deep detail on specific topics. Load them when queries require specification-level precision.

## Debugging Checklist

When debugging trading system issues:

### US Equity
1. **Feed issues** - Check sequence gaps, timestamp alignment, halt state handling
2. **Auction issues** - Verify order type eligibility, cutoff times, NOII parsing
3. **Execution issues** - Validate tick/lot compliance, fee tier, priority rules
4. **Regulatory issues** - Confirm trade-through protection, best execution logic

### Chinese Futures (CTP)
1. **Data issues** - DBL_MAX validation (1.7976931348623157e+308), CZCE UpdateMillisec=0, night replay filtering
2. **Session issues** - TradingDay vs ActionDay semantics, 21:00 reset, trading breaks (10:15-10:30)
3. **Order issues** - CloseToday/CloseYesterday (SHFE/INE), cancel-replace queue loss, DCE stop orders
4. **Auth issues** - 看穿式监管 AppID/AuthCode, CTP version ≥6.3.15, physical machine required
5. **Gap issues** - CTP has NO replay; reconnection gaps are permanent data loss

## File Index

### Content Files

**Equity:**
- `equity/equity.md` - Equity market fundamentals
- `equity/amer/equity_amer.md` - US equity market structure
- `equity/amer/nasdaq/nasdaq.md` - Nasdaq exchange mechanics

**Futures:**
- `futures/futures.md` - Futures market fundamentals
- `futures/apac/futures_apac.md` - APAC futures overview
- `futures/apac/china/futures_china.md` - Chinese futures (main)
- `futures/apac/china/shfe/shfe.md` - SHFE specifics
- `futures/apac/china/dce/dce.md` - DCE specifics
- `futures/apac/china/czce/czce.md` - CZCE specifics
- `futures/apac/china/cffex/cffex.md` - CFFEX specifics
- `futures/apac/china/ine/ine.md` - INE specifics

### Reference Files

**US Equity References:**
- `equity/amer/references/regulatory/sec_reg_nms.md` - Reg NMS overview
- `equity/amer/references/regulatory/finra_rules.md` - FINRA rules
- `equity/amer/references/regulatory/rule_605_606.md` - Disclosure rules
- `equity/amer/references/specs/sip_specs.md` - SIP specifications

**Nasdaq References:**
- `equity/amer/nasdaq/references/specs/itch_protocol.md` - ITCH 5.0 spec
- `equity/amer/nasdaq/references/specs/ouch_protocol.md` - OUCH 4.2/5.0 spec
- `equity/amer/nasdaq/references/specs/totalview.md` - TotalView product
- `equity/amer/nasdaq/references/regulatory/nasdaq_rules.md` - Nasdaq rulebook

**Futures References:**
- `futures/references/spreads.md` - Calendar/inter-commodity spread mechanics (CME/ICE)
- `futures/references/flow_interpretation.md` - Flow analysis framework (when flow signals direction)

**Chinese Futures References:**
- `futures/apac/china/references/specs/ctp_market_data.md` - CTP struct specification
- `futures/apac/china/references/specs/data_quality_checklist.md` - Validation checklist
- `futures/apac/china/references/specs/failure_modes.md` - Failure mode catalog
- `futures/apac/china/references/models/queue_position.md` - Queue estimation models
- `futures/apac/china/references/models/trade_direction.md` - Trade direction inference
- `futures/apac/china/references/models/causal_analysis.md` - Causal identification framework
- `futures/apac/china/references/models/cross_product_analysis.md` - Cross-product patterns
- `futures/apac/china/references/models/spreads.md` - Chinese spread execution (CTP, legging risk)
- `futures/apac/china/references/regime_changes.md` - Regime change database
