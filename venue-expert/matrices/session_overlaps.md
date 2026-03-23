# Session Overlaps — Cross-Venue Matrix

## Session Hours (UTC)

| Exchange | Pre-Open | Main Session | Break | Evening/Night | Notes |
|----------|----------|-------------|-------|---------------|-------|
| CME Globex (ES/NQ) | — | 13:30–20:15 (RTH) | 21:00–22:00 (maintenance) | 22:00–13:30+1 (overnight) | Sunday open 22:00 UTC |
| CME Globex (CL) | — | 13:00–18:30 (RTH) | — | 22:00–13:00+1 | — |
| CME Globex (ZN/ZB) | — | 12:00–19:00 (RTH) | — | 22:00–12:00+1 | — |
| ICE (Brent B) | — | 01:00–23:00 London (00:00–22:00 UTC) | — | — | ~22 hrs continuous |
| Eurex (FGBL/FESX) | 00:00 | 00:15–21:00 | — | — | Asian hours since Dec 2018 |
| SGX (FEF) | — | 23:25–11:55 (T session) | 11:55–12:15 | 12:15–21:15 (T+1) | ~21.5 hrs total |
| HKEX (equities) | 01:00 | 01:30–04:00 / 05:00–08:00 | 04:00–05:00 (lunch) | — | CAS 08:00–08:10 |
| SHFE/INE (night tier 3) | 12:55 | 01:00–02:15 / 02:30–03:30 / 05:30–07:00 | 02:15–02:30 / 03:30–05:30 | 13:00–18:30 (au,ag,sc) | Night = 21:00–02:30 Beijing |
| SHFE/INE (night tier 2) | 12:55 | Same day session | Same | 13:00–17:00 (cu,al,zn) | Night = 21:00–01:00 Beijing |
| SHFE/DCE/CZCE (night tier 1) | 12:55 | Same day session | Same | 13:00–15:00 (rb,i,TA,m) | Night = 21:00–23:00 Beijing |
| CFFEX (index) | 01:25 | 01:30–03:30 / 05:00–07:00 | 03:30–05:00 | — | No night session, no mid-morning break |
| CFFEX (treasury) | 01:10 | 01:15–03:30 / 05:00–07:15 | 03:30–05:00 | — | No night session |
| GFEX | 00:55 | 01:00–02:15 / 02:30–03:30 / 05:30–07:00 | 02:15–02:30 / 03:30–05:30 | — | No night session |

## Overlap Windows

| Window (UTC) | Active Venues | Significance |
|-------------|---------------|-------------|
| 00:00–01:00 | Eurex, ICE, CME Globex, SGX T+1 | Europe opens; Asia T+1 still active |
| 01:00–04:00 | Eurex, ICE, CME Globex, HKEX, Chinese day (01:00–07:00), SGX | Full Asia-Europe overlap; Chinese day session active |
| 05:30–07:00 | Chinese afternoon, HKEX (post-lunch), Eurex, ICE, CME Globex, SGX | Chinese PM + Europe continuous |
| 12:00–15:00 | CME RTH, ICE, Eurex, Chinese night (tier 1) | US open + Europe close + China night open (21:00–23:00 Beijing) |
| 13:00–17:00 | CME RTH, ICE, Chinese night (tier 2 metals) | US session + China metals night |
| 13:00–18:30 | CME RTH, ICE, Chinese night (tier 3 au/ag/sc) | US session + China precious metals/crude night |
| 13:30–20:15 | CME RTH (ES/NQ), ICE | US equity index RTH; peak global liquidity |
| 20:15–22:00 | CME pre-maintenance, ICE (until 22:00) | US post-RTH wind-down |
| 22:00–23:25 | CME Globex resumes | Gap: SGX not yet open; thin liquidity |
| 23:25–00:00 | CME Globex, SGX T session opens | Asia-US overnight overlap begins |

## Key Cross-Venue Arbitrage Windows

| Pair | Overlap Window (UTC) | Duration |
|------|---------------------|----------|
| DCE iron ore ↔ SGX FEF | 01:00–07:00 (Chinese day) + 13:00–15:00 (Chinese night / SGX T+1) | ~8 hrs |
| SHFE metals ↔ LME | 01:00–07:00 (Chinese day) + 13:00–17:00 (Chinese night) | ~10 hrs |
| SHFE au ↔ COMEX GC | 01:00–07:00 (Chinese day) + 12:00–18:30 (Chinese night + CME RTH) | ~12.5 hrs |
| INE sc ↔ ICE Brent | 01:00–07:00 (Chinese day) + 13:00–18:30 (Chinese night) | ~11.5 hrs |
| Eurex FGBL ↔ CME ZN | 00:15–19:00 (Eurex) overlaps 12:00–19:00 (CME RTH) | 7 hrs |
| ES/NQ ↔ FESX/FDAX | 13:30–20:15 (CME RTH) overlaps 00:15–21:00 (Eurex) | 6.75 hrs |

## Per-Venue Details
- [[futures/amer/cme.md|cme.md]] §8 Session Schedule
- [[futures/emea/ice.md|ice.md]] §9 Session Schedule
- [[futures/emea/eurex.md|eurex.md]] §6 Session Schedule
