# venue-expert

3-layer microstructure knowledge base for trading venues.

## Why

Centralizes venue mechanics that otherwise get re-researched per engineer and silently differ across backtests.

## Layers

| Layer | Dir | Speed | Use Case |
|-------|-----|-------|----------|
| L1 Cards | `cards/` | 30 sec | Quick lookup, orientation, onboarding |
| L2 Matrices | `matrices/` | 2 min | Cross-venue comparison, strategy-to-venue fit |
| L3 Deep Docs | `{asset_class}/{region}/` | 10+ min | Deep research, debugging |

Query-pattern routing in `SKILL.md` maps keywords to the cheapest sufficient layer.

## Key Files

| File | Purpose |
|------|---------|
| [`SKILL.md`](SKILL.md) | Routing table — maps query patterns to L1/L2/L3 files |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | How to add a new venue (template, research questions, checklist) |
| `cards/*.md` | L1 quick-reference cards |
| `matrices/*.md` | L2 cross-venue comparison tables |

## Coverage

| Asset Class | Venues |
|-------------|--------|
| US Equity | 16 exchanges across 6 operators (NYSE, Nasdaq, Cboe, IEX, MEMX, LTSE, MIAX Pearl) |
| Chinese Futures | SHFE, DCE, CZCE, CFFEX, INE, GFEX |
| Americas Futures | CME Group (CME, CBOT, NYMEX, COMEX) |
| EMEA Futures | ICE Futures Europe, Eurex |
| APAC Futures | SGX |
| APAC Equity | HKEX |
