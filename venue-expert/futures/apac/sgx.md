# SGX Exchange Mechanics

Assumes familiarity with DCE iron ore from [[futures/apac/china/dce.md|dce.md]].

Iron ore derivatives #2 globally (DCE #1 at ~18× volume). International seaborne benchmark for BHP, Rio Tinto, Vale physical pricing.

## 1. Identity

| Attribute | Value |
|-----------|-------|
| MIC | **XSES** |
| Location | Singapore |
| Platform | **TITAN** (Nasdaq Genium INET technology) |
| Matching | **Price-time priority** |
| Market data | **ITCH** (MoldUDP64 multicast) |
| Order entry | **OUCH** protocol |
| Co-location | **25 Serangoon North Ave 5, Singapore** |

## 2. Iron Ore Contract Specifications (FEF)

| Field | Value |
|-------|-------|
| Symbol | **FEF** (TSI Iron Ore CFR China 62% Fe Fines) |
| Contract size | **100 metric tonnes** |
| Tick size | **$0.01/dmt** ($1.00/contract) |
| Currency | USD |
| Contract months | Up to **36 consecutive months** |
| Settlement | **Cash-settled** against Platts IODEX 62% Fe CFR China |
| Index transition | TSI → **Platts IODEX** (January 2026) |

### Settlement Index

| Attribute | Value |
|-----------|-------|
| Index | Platts IODEX 62% Fe CFR China |
| Prior index | TSI Iron Ore (transitioned Jan 2026) |
| Methodology | Daily assessment of seaborne iron ore fines |
| Grade | 62% Fe content |
| Delivery basis | CFR China (cost + freight to Chinese port) |

## 3. Session Hours (SGT, UTC+8)

| Session | Hours | Duration |
|---------|-------|----------|
| T Session (Day) | **07:25–19:55** | 12.5 hrs |
| Break | 19:55–20:15 | 20 min |
| T+1 Session (Night) | **20:15–05:15** | 9 hrs |
| **Total** | | **~21.5 hrs/day** |

### Session vs DCE

| Attribute | SGX | DCE |
|-----------|-----|-----|
| Total hours | ~21.5 hrs | ~7.5 hrs |
| Night session | 20:15–05:15 SGT | 21:00–23:00 CST |
| Overlap with European trading | Full | Minimal |
| Overlap with US trading | Partial | None |

## 4. TITAN Platform

### Technology Stack

| Component | Technology |
|-----------|-----------|
| Matching engine | **Nasdaq Genium INET** |
| Market data | **ITCH** protocol (MoldUDP64 multicast) |
| Order entry | **OUCH** protocol |
| Book depth | **Full order-by-order** |
| Timestamp precision | **Nanosecond** |

### Recovery Architecture

| Method | Transport | Use Case |
|--------|-----------|----------|
| **Rewinder** | UDP unicast | Small gaps (recent missed packets) |
| **GLIMPSE** | TCP snapshot | Full book recovery (join mid-session) |

### Co-Location Latency

| Metric | Value |
|--------|-------|
| Exchange-stated round-trip | **<100 μs** |
| Tier-1 firm wire-to-wire | **Sub-15 μs** |
| Location | 25 Serangoon North Ave 5, Singapore |

### ITCH Compatibility

SGX ITCH uses MoldUDP64 framing — structurally similar to Nasdaq ITCH but different message types and product definitions. Firms with Nasdaq ITCH parsers can adapt with moderate effort. Key differences:

| Aspect | SGX ITCH | Nasdaq ITCH 5.0 |
|--------|----------|-----------------|
| Transport | MoldUDP64 | MoldUDP64 |
| Products | Futures, options | Equities |
| Timestamps | Nanosecond | Nanosecond |
| Order entry | OUCH | OUCH |
| Recovery | Rewinder + GLIMPSE | MoldUDP64 retransmit |

## 5. SGX vs DCE Iron Ore Comparison

| Metric | SGX FEF | DCE Iron Ore (i) |
|--------|---------|-------------------|
| Daily volume | ~100K–120K contracts | **~2 million contracts** (~18× SGX) |
| Contract size | 100 mt | 100 t |
| Currency | **USD** | CNY |
| Settlement | **Cash** (Platts IODEX) | **Physical delivery** |
| Daily price limit | **None** | **±4%** |
| Trading hours | ~21.5 hrs | ~7.5 hrs |
| Foreign access | **Fully open** | QFII/intermediary required (since May 2018) |
| Position limits | Less restrictive | Aggressive (frequently 500 lots/day near-month) |
| Tick value | $1.00 | ~7 CNY |
| Benchmark role | **International seaborne** | **Chinese domestic** |

### Price Discovery Dynamics

| Period | Leader | Mechanism |
|--------|--------|-----------|
| Chinese trading hours (09:00–15:00 CST) | **DCE** | Dominates on volume (~18×) |
| Non-Chinese hours | **SGX** | Only liquid iron ore venue |
| Expiry convergence | Both | Prices converge after adjustments |

### Adjusted Spread

Persistent arbitrage opportunity exists between SGX and DCE after adjusting for:

| Adjustment | Typical Value |
|------------|---------------|
| China VAT | **~13%** |
| Port charges | Variable by port |
| USD/CNY exchange rate | Spot rate |

The adjusted spread reflects structural differences (cash vs physical, currency, access) rather than pure mispricing.

## 6. Other Key Products

| Product | Description |
|---------|-------------|
| Nikkei 225 | Japanese equity index futures |
| MSCI Asia | Asian equity index suite |
| Rubber (RSS3) | Physical delivery |
| Freight | Dry bulk freight derivatives |

SGX's primary HFT-relevant product is iron ore (FEF). Equity index products are significant but lower-frequency.

## 7. Gotchas Checklist

1. **DCE dominates volume (~18×)** but SGX sets the international seaborne benchmark price
2. **Platts IODEX transition from TSI** completed January 2026 — verify settlement index in production
3. **Cash-settled vs DCE physical delivery** — fundamentally different dynamics at expiry
4. **No daily price limits** (vs DCE ±4%) — SGX can gap freely on overnight news
5. **ITCH protocol** — similar parser to Nasdaq but different product definitions and message types
6. **21.5-hour trading** — captures European/US hours where DCE is closed
7. **USD-denominated** — FX risk for CNY-based traders; basis to DCE includes FX component
8. **Rewinder vs GLIMPSE** — use Rewinder for small gaps, GLIMPSE for full recovery; do not mix
9. **Sub-15 μs Tier-1 latency** — exchange quotes <100 μs but best firms achieve much less
