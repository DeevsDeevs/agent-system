---
name: venue-expert
description: >
  This skill should be used when the user asks about "market microstructure",
  "exchange mechanics", "order book", "auction", "NBBO", "Reg NMS", "trading venue",
  "halt", "LULD", "tick size", "maker-taker", "price-time priority", "SIP", "direct feed",
  "TRF", "wholesaler", "PFOF", "best execution", "trade-through", "ISO", "opening cross",
  "closing cross", "NOII", "ITCH", "OUCH", or mentions specific exchanges (Nasdaq, NYSE,
  CME, Binance, etc.). Provides hierarchical venue expertise for research and debugging
  trading systems.
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

### Drill-Down Behavior

Start at the most specific applicable level. Reference parent concepts without repeating them. For example, when discussing Nasdaq auctions, assume familiarity with US equity auction concepts from `equity_amer.md`.

## Reference Organization

Each level has a `references/` directory with subdirectories:

- `regulatory/` - Rules, regulations, compliance guidance
- `specs/` - Protocol specifications, data formats
- `academic/` - Research papers, theoretical models

Reference files provide deep detail on specific topics. Load them when queries require specification-level precision.

## Debugging Checklist

When debugging trading system issues:

1. **Feed issues** - Check sequence gaps, timestamp alignment, halt state handling
2. **Auction issues** - Verify order type eligibility, cutoff times, NOII parsing
3. **Execution issues** - Validate tick/lot compliance, fee tier, priority rules
4. **Regulatory issues** - Confirm trade-through protection, best execution logic

## File Index

### Content Files

- `equity/equity.md` - Equity market fundamentals
- `equity/amer/equity_amer.md` - US equity market structure
- `equity/amer/nasdaq/nasdaq.md` - Nasdaq exchange mechanics

### Reference Files

**US Equity References:**
- `equity/amer/references/regulatory/sec_reg_nms.md` - Reg NMS overview
- `equity/amer/references/regulatory/finra_rules.md` - FINRA rules
- `equity/amer/references/regulatory/rule_605_606.md` - Disclosure rules
- `equity/amer/references/specs/sip_specs.md` - SIP specifications
- `equity/amer/references/academic/spread_models.md` - Spread theory
- `equity/amer/references/academic/market_impact.md` - Impact models

**Nasdaq References:**
- `equity/amer/nasdaq/references/specs/itch_protocol.md` - ITCH 5.0 spec
- `equity/amer/nasdaq/references/specs/ouch_protocol.md` - OUCH 4.2/5.0 spec
- `equity/amer/nasdaq/references/specs/totalview.md` - TotalView product
- `equity/amer/nasdaq/references/regulatory/nasdaq_rules.md` - Nasdaq rulebook
- `equity/amer/nasdaq/references/academic/auction_theory.md` - Auction research
