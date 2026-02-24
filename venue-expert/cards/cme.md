# CME Group — Quick Reference Card

## Exchanges

| Exchange | MIC | Products | Fee Model | Matching | Co-Location |
|----------|-----|----------|-----------|----------|-------------|
| CME | XCME | Equity index (ES, NQ), FX (6E, 6J), SOFR (SR3) | Per-contract tiered | FIFO/Allocation/Pro-Rata | Aurora, IL (CyrusOne) |
| CBOT | XCBT | Treasuries (ZN, ZB, ZT), Grains (ZC, ZS, ZW) | Per-contract tiered | FIFO/Configurable | Aurora, IL (CyrusOne) |
| NYMEX | XNYM | Energy (CL, NG) | Per-contract tiered | FIFO | Aurora, IL (CyrusOne) |
| COMEX | XCEC | Metals (GC, SI) | Per-contract tiered | FIFO | Aurora, IL (CyrusOne) |

## Key Parameters

| Parameter | Value |
|-----------|-------|
| Market data protocol | MDP 3.0 (SBE/UDP multicast) |
| Outright book depth | 10 levels (instrument-dependent; some get 5) |
| Implied book depth | **2 levels** (best 2 bid + best 2 ask; NOT 10) |
| Timestamp precision | uint64 nanoseconds since Unix epoch (UTC); microsecond accuracy |
| Margin framework | SPAN 2 (VaR-based, replacing classic 16-scenario SPAN) |
| Performance bond levels | Non-HRP: 100% maintenance; HRP (retail): 110% maintenance |
| Recovery layers | Feed A/B arbitration → UDP snapshot loop → TCP Replay (max 2,000 pkt) → Instrument Recovery → Channel Reset |
| Sequence numbers | Per-channel, reset weekly |

## Top Products

| Product | Code | Tick | Multiplier | Algorithm | Settlement Window (CT) |
|---------|------|------|------------|-----------|----------------------|
| E-mini S&P 500 | ES | 0.25 pts ($12.50) | $50 | FIFO (F) | 14:59:30–15:00:00 |
| E-mini Nasdaq | NQ | 0.25 pts ($5.00) | $20 | FIFO (F) | 14:59:30–15:00:00 |
| WTI Crude Oil | CL | $0.01 ($10.00) | $1,000 | FIFO (F) | 13:28:00–13:30:00 |
| Gold | GC | $0.10 ($10.00) | $100 | FIFO (F) | 12:29:00–12:30:00 |
| 10-Year T-Note | ZN | 1/64 ($15.625) | $1,000 | FIFO (F) | 13:59:30–14:00:00 |
| Treasury Bond | ZB | 1/32 ($31.25) | $1,000 | FIFO (F) | 13:59:30–14:00:00 |
| 2-Year T-Note | ZT | 1/128 ($7.8125) | $2,000 | Configurable (K) | 13:59:30–14:00:00 |
| 3-Month SOFR | SR3 | 0.0025 ($6.25) | $2,500 | Allocation (A) | 13:59:00–14:00:00 |

## Session Schedule (CT)

| Session | Hours | Products |
|---------|-------|----------|
| Sunday open | 17:00 CT Sunday | All Globex products |
| Globex overnight | 17:00–08:30 CT | Most products |
| RTH (equities/FX) | 08:30–15:15 CT | ES, NQ, 6E, etc. |
| RTH (rates) | 07:00–14:00 CT | ZN, ZB, ZT, SR3 |
| RTH (energy) | 08:00–13:30 CT | CL, NG |
| RTH (metals) | 07:20–12:30 CT | GC, SI |
| Daily maintenance | 16:00–17:00 CT (M–Th); 16:00 Fri close | All |

## Data Feed

| Feed | Book Type | Content |
|------|-----------|---------|
| MBP (Market By Price) | Aggregated, configurable depth (typically 10) | Bid/ask levels + implied (2 levels); incremental + snapshot recovery |
| MBOFD (Market By Order Full Depth) | Individual orders, unlimited depth | Every visible order; no implied data |
| MBOLD (Market By Order Limited Depth) | Individual orders, top 10 | Top 10 bid/ask individual orders |
| Snapshot Recovery | UDP loop | Full book snapshots for splice with incremental cache |
| TCP Replay | FIX-ASCII logon → SBE response | Max 2,000 packets/request; 24-hour window; not for primary recovery |

## Matching Algorithms

| Algorithm | Code | Products |
|-----------|------|----------|
| FIFO | F | ES, NQ, CL, NG, GC, SI, ZN, ZB outrights |
| Configurable (Split FIFO/Pro-Rata) | K | ZT (split), ZC/ZS/ZW (40% FIFO / 60% Pro-Rata) |
| Allocation (TOP → Pro-Rata → FIFO) | A | SR3, SR1 (inherited from Eurodollar) |
| Pro-Rata (spreads) | C | 6E, 6J spreads |
| Threshold Pro-Rata + LMM | Q | ZN, ZB, ZT options; SR3 options |
| Threshold Pro-Rata (no LMM) | O | ZC, ZS, ZW options |

## SPAN 2 Migration

| Asset Class | Status |
|-------------|--------|
| NYMEX Energy | Completed — July 21, 2023 |
| Equity Products | Completed — October 2024 |
| Interest Rate & FX | Pending — originally planned H2 2024, delayed |
| Agriculture & Remaining | Pending — originally planned H2 2025, delayed |

## Modify Semantics (FIFO)

| Action | Queue Position |
|--------|---------------|
| Decrease quantity | Retained |
| Increase quantity | Lost (re-queued to back) |
| Change price | Lost |
| Change account | Lost |
| GTC across sessions | Retained (absent priority-losing mods) |
| Iceberg display refresh | Lost |

## Deep Docs
- [[futures/amer/cme.md|cme.md]]
