# ICE Futures Europe Mechanics

Brent crude flagship, softs, European utilities. Matching engine at Basildon, NOT LD4.

## 1. Identity

| Attribute | Value |
|-----------|-------|
| Operator | Intercontinental Exchange |
| MIC | **IFEU** |
| Matching engine | **Basildon, Essex — European Liquidity Centre** |
| Flagship | Brent Crude (B) |
| Other products | Gasoil, UK Natural Gas, Dutch TTF, European Power, Robusta Coffee, Cocoa, Sugar |
| Matching | **Pure price-time priority (FIFO)** |

## 2. Brent Crude Contract Specifications

| Field | Value |
|-------|-------|
| Symbol | **B** |
| Contract size | **1,000 barrels** |
| Tick size | **$0.01/barrel** ($10/contract/tick) |
| Currency | USD |
| Contract months | Up to **96 consecutive months** (~8 years) |
| Settlement type | EFP-deliverable with option to **cash settle** against ICE Brent Index |
| Position limit | 7,000 contracts in last 5 business days |
| Trading hours | **01:00–23:00 London time** (~22 hrs) |

### Key Differentiators vs CME WTI

| Attribute | ICE Brent (B) | CME WTI (CL) |
|-----------|---------------|---------------|
| Contract size | 1,000 bbl | 1,000 bbl |
| Settlement | Cash (ICE Brent Index) | Physical (Cushing, OK) |
| Forward curve | 96 months | 9 years (~108 months) |
| Matching engine | Basildon, Essex | Aurora, IL |
| Matching algorithm | FIFO | FIFO |
| Trading hours | ~22 hrs | ~23 hrs |
| Benchmark role | International seaborne crude | North American crude |

## 3. Order Book Mechanics

Pure price-time priority (FIFO) for all products.

### Modify Semantics

| Action | Queue Position |
|--------|---------------|
| Decrease quantity (price unchanged) | **Retained** |
| Increase quantity | **Lost** (re-queued to back) |
| Change price | **Lost** (re-queued to back) |

Same pattern as CME FIFO and Eurex Time matching.

## 4. Market Data: iMpact Protocol

Proprietary binary multicast protocol.

### Book Types

| Type | Depth | Granularity | Use Case |
|------|-------|-------------|----------|
| **FOD** (Full Order Depth) | **Unlimited** | Individual order level | Full book reconstruction |
| **Price Level** | **Top 5** | Aggregated per price | Lightweight BBO + near depth |

### Timestamp Precision

| Component | Precision | Notes |
|-----------|-----------|-------|
| Primary timestamp | **Millisecond** | Not nanosecond — major difference from CME/Eurex |
| `SequenceWithinMillis` | Sub-ms ordering | Integer counter for ordering within same millisecond |
| MiFID II compliance | **Microsecond** granularity | For regulated market obligations |

### Recovery Architecture

| Mechanism | Description |
|-----------|-------------|
| Snapshot channels | Dedicated multicast feeds for full book state |
| Bundle markers | Message type **'T'** delineates atomic update boundaries |

Bundle markers (Type 'T') define atomic update boundaries — all messages between two Type T markers must be applied together. Partial application produces inconsistent book state.

## 5. Settlement Methodology

### Daily Settlement

VWAP during a **2-minute window: 19:28:00–19:30:00 London time**.

### Final Settlement: ICE Brent Index

| Component | Description |
|-----------|-------------|
| Methodology | Average of three components across **5 intraday sampling points** |
| Sampling times | 10:30, 12:30, 14:30, 16:30, 19:30 London |
| Components | Trade-based + assessment-based + cash cargo |
| Reference crude | **BFOETM** (Brent-Forties-Oseberg-Ekofisk-Troll-Midland) |
| Minimum cargo size | **700,000 barrels** (full cargo only) |
| PRA data source | **ICIS** (since 2015) |

### Settlement vs CME

| Attribute | ICE Brent | CME WTI |
|-----------|-----------|---------|
| Daily method | VWAP 19:28-19:30 London | VWAP 13:28-13:30 CT |
| Final | Cash (ICE Brent Index) | Physical delivery at Cushing |
| Index complexity | 5-point sampling, 3 components | N/A (physical) |
| Expiry basis | BFOETM basket | WTI at Cushing |

## 6. Co-Location

| Attribute | Value |
|-----------|-------|
| Location | **Basildon, Essex — European Liquidity Centre** |
| Round-trip latency | **<1 ms** average |
| FPGA wire-to-wire | **~6 μs** tick-to-trade |
| Network topology | **Spine-and-leaf** (LCN) for consistent latency |
| Time sync | **PTP IEEE 1588** sub-1μs precision |
| Connection speed | **10 Gbps** |

### Routing Implications

The matching engine is at Basildon, NOT Equinix LD4 in Slough. Firms co-located at LD4 for Eurex/LME must route to Basildon for ICE — adds latency vs direct Basildon co-location. This is a common architectural mistake for multi-venue European trading systems.

## 7. Cross-Venue Latency Context

### Basildon Connectivity

| Route | Distance | Estimated One-Way |
|-------|----------|-------------------|
| Basildon ↔ LD4 (Slough) | ~60 km | ~300–500 μs fiber |
| Basildon ↔ FR2 (Frankfurt) | ~600 km | ~4–5 ms fiber; **~2.3 ms microwave** |
| Basildon ↔ Aurora (CME) | ~6,300 km | ~33–35 ms (hybrid MW+subsea) |

For multi-venue energy trading (ICE Brent + CME WTI), the Basildon–Aurora path is critical. McKay Brothers provides microwave for LD4–FR2 at ~2.3 ms one-way; the transatlantic leg uses Hibernia Express subsea.

### Latency Architecture Decision

| Strategy | Co-lo Location | Tradeoff |
|----------|---------------|----------|
| ICE-first | Basildon | Best ICE latency; worse CME + Eurex |
| Eurex-first | FR2 Frankfurt | Best Eurex latency; ~300–500 μs penalty to ICE |
| CME-first | Aurora, IL | Best CME latency; ~33 ms to ICE |
| Multi-venue (UK hub) | LD4 Slough | Compromise; ~300–500 μs to ICE, ~4 ms to Eurex |

## 8. iMpact Protocol Details

### Message Structure

iMpact uses a proprietary binary encoding (not SBE like CME, not EOBI like Eurex). Key characteristics:

| Attribute | Value |
|-----------|-------|
| Transport | UDP multicast |
| Encoding | Proprietary binary |
| Byte order | Little-endian |
| Book update model | Incremental updates + snapshot recovery |

### Book Update Types

| Update | Description |
|--------|-------------|
| Add | New order added to book |
| Modify | Order quantity/price changed |
| Delete | Order removed |
| Trade | Execution occurred |

### FOD vs Price Level Selection Guide

| Requirement | Recommended Feed |
|-------------|-----------------|
| Full book reconstruction | **FOD** (unlimited depth, per-order) |
| BBO monitoring | **Price Level** (top 5, lighter bandwidth) |
| Queue position tracking | **FOD** (per-order detail required) |
| Multi-instrument monitoring | **Price Level** (lower bandwidth per instrument) |

## 9. Session Schedule

### Trading Hours (London Time)

| Product | Open | Close | Duration |
|---------|------|-------|----------|
| Brent Crude (B) | **01:00** | **23:00** | ~22 hrs |
| Gasoil (G) | 01:00 | 23:00 | ~22 hrs |
| UK Nat Gas (M) | 07:00 | 17:00 | 10 hrs |
| Dutch TTF (TFM) | 07:00 | 17:00 | 10 hrs |
| Robusta Coffee (RC) | 09:00 | 17:30 | 8.5 hrs |
| Cocoa (C) | 09:30 | 16:50 | 7.3 hrs |
| Sugar #5 (W) | 08:45 | 17:55 | 9.2 hrs |

Energy products trade nearly 24 hours; softs and power follow European business hours.

## 10. Gotchas Checklist

1. **Matching engine at Basildon, NOT LD4** — routing via LD4 adds unnecessary latency for ICE
2. **iMpact timestamps are millisecond primary** — not nanosecond like CME MDP 3.0 or Eurex EOBI
3. **FOD vs Price Level** — different depth and granularity; choose based on use case
4. **Bundle markers (Type T)** define atomic update boundaries — partial application corrupts book state
5. **96-month forward curve** — very long-dated liquidity; most volume in front months
6. **Settlement via 5-point sampling** — not a simple closing price or single VWAP
7. **BFOETM basket** — six crudes, not just Brent; quality differentials affect index
8. **EFP settlement** — deliverable via Exchange of Futures for Physical, not pure cash
9. **MiFID II microsecond requirement** — feed provides ms primary, compliance timestamps are μs
