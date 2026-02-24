# Global Venues — Quick Reference Card

## Venues Overview

| Venue | Region | Asset | MIC | Matching | Co-Location | Data Feed |
|-------|--------|-------|-----|----------|-------------|-----------|
| ICE Futures Europe | EMEA | Energy, softs | IFEU | Price-time (FIFO) | Basildon, Essex (NOT LD4) | iMpact (binary multicast) |
| Eurex | EMEA | Fixed income, equity index | XEUR | FIFO (FI/equity); Pro-Rata (rates) | Equinix FR2, Frankfurt | EOBI (L3, full depth, ns) |
| SGX | APAC | Iron ore, equity index | XSES | Price-time | 25 Serangoon North Ave 5, Singapore | ITCH (MoldUDP64, ns) |
| HKEX | APAC | Equities, derivatives | XHKG | Price-time | Hong Kong | OMD-C (equities); OMD-D (derivatives) |
| GFEX | APAC | Silicon, lithium, PGMs | — | Price-time | Guangzhou | CTP (~500ms snapshots, 5-level) |

## ICE Brent

| Field | Value |
|-------|-------|
| Symbol | B (Brent Crude) |
| Contract size | 1,000 barrels |
| Tick size | $0.01/barrel ($10/contract/tick) |
| Trading hours | 01:00–23:00 London time (~22 hrs) |
| Settlement (daily) | VWAP 19:28–19:30 London time |
| Settlement (final) | Cash against ICE Brent Index (BFOETM; 5 intraday sampling points) |
| Co-location | Basildon, Essex — European Liquidity Centre |
| Matching latency | <1 ms average; ~6 μs wire-to-wire (FPGA) |
| Feed protocol | iMpact: FOD (full order depth) + Price Level (top 5); ms timestamps + MiFID μs |
| Modify: qty decrease | Retains queue position |
| Modify: qty increase or price change | Loses queue position |

## Eurex

| Field | Value |
|-------|-------|
| Key FI products | FGBL (Bund), FGBM (Bobl), FGBS (Schatz), FGBX (Buxl), FOAT (OAT), FBTP (BTP) |
| Key equity products | FESX (Euro STOXX 50), FDAX (DAX), FDXM (Mini-DAX) |
| Key rates products | FEU3 (Euribor), FST3 (Euro STR) |
| Matching (FI/equity) | Time (FIFO) |
| Matching (rates) | Pro-Rata (FEU3, FST3) |
| Feed protocol | EOBI: full L3 order-by-order, no depth limit, ns timestamps |
| EOBI availability | Co-location only (10 Gbit/s); select benchmarks + all Xetra cash |
| Co-location | Equinix FR2, Frankfurt |
| Session hours | 01:15–22:00 CET (continuous); pre-trading 01:00 |
| Volatility interruption | Dynamic trigger → auction with random end; non-persistent orders deleted |
| Self-trade prevention | Since T7 R12.1: Cancel Resting / Cancel Incoming / Cancel Both |
| Implied pricing | Supported (calendar spread ↔ outright); not labeled in EOBI |

## SGX

| Field | Value |
|-------|-------|
| Key product | FEF (TSI Iron Ore CFR China 62% Fe) |
| Contract size | 100 metric tonnes |
| Tick size | $0.01/dmt ($1.00/contract) |
| Settlement | Cash-settled against Platts IODEX 62% Fe CFR China |
| T Session (day) | 07:25–19:55 SGT |
| T+1 Session (night) | 20:15–05:15 SGT (~21.5 hrs total) |
| Platform | TITAN (Nasdaq Genium INET) |
| Feed protocol | ITCH (MoldUDP64); full order-by-order, ns timestamps |
| Order entry | OUCH protocol |
| Co-lo latency | <100 μs exchange-stated; sub-15 μs at Tier-1 |
| SGX vs DCE volume | SGX ~100–120K/day; DCE ~2M/day (~18× greater) |
| SGX vs DCE price discovery | DCE leads during Chinese hours; SGX leads non-Chinese hours |

## HKEX

| Field | Value |
|-------|-------|
| Unique feature | **Broker queue visibility** — real-time broker ID per order at each price level |
| Broker queue depth | Up to 40 brokers per side (bid/ask), ~5–10 spread levels |
| Coverage | All SEHK-listed securities (equities, ETFs, warrants, CBBCs, debt) |
| Derivatives broker queue | **Not available** (OMD-D has no broker identification) |
| Feed products | SS (Standard — broker queue included), SP (Premium + CBQ add-on), SF (FullTick) |
| VCM (Volatility Control) | Cooling-off mechanism for extreme moves |
| CAS (Closing Auction) | Closing auction session for price discovery |
| Stock Connect | Northbound/Southbound cross-border trading with mainland China |
| Non-display cost | HK$20,000/firm/month for automated trading use |
| OMD-C launch | September 30, 2013 |
| Comparable venues | Indonesia (IDX), Thailand (SET) also provide broker queue; NYSE/Nasdaq/CME do not |

## Deep Docs
- [[futures/emea/ice.md|ice.md]]
- [[futures/emea/eurex.md|eurex.md]]
- [[futures/apac/sgx.md|sgx.md]]
- [[equity/apac/hkex.md|hkex.md]]
