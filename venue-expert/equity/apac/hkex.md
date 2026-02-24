# HKEX Equity Mechanics

Broker queue visibility — virtually unique among major developed-market exchanges. Equities focus; derivatives (OMD-D) documented separately.

## 1. Identity

| Attribute | Value |
|-----------|-------|
| MIC | **XHKG** |
| Location | Hong Kong |
| Operator | Hong Kong Exchanges and Clearing (HKEX) |
| Market | SEHK (Stock Exchange of Hong Kong) |
| Products | Equities, ETFs, REITs, warrants, CBBCs, inline warrants, debt |
| Key feature | **Real-time broker queue identification** |

## 2. Broker Queue — Unique Feature

### What Is Visible

Real-time **4-digit HKEX Exchange Participant (broker) numbers** at each price level, per side.

| Attribute | Value |
|-----------|-------|
| Identifier | 4-digit Exchange Participant number |
| Granularity | **Per-order** — same broker appears multiple times if multiple orders |
| Max per side | **40 brokers** across ~5–10 spread levels |
| Max total | **80 entries** per security (40 bid + 40 ask) |
| Scope | **Equities ONLY** — derivatives OMD-D has NO broker identification |
| Update mode | **Real-time but conflated** (not streaming tick-by-tick) |
| Delay | **None** — no artificial delay |

### What "Per-Order" Means

Unlike aggregated broker statistics (e.g., "Broker 1234 has 50,000 shares at $100"), HKEX shows each individual order separately. If Broker 1234 has three orders at $100.00, the broker queue shows:

```
Bid $100.00: [1234] [1234] [1234] [5678] [9012] ...
```

This enables tracking of order additions, modifications, and cancellations by broker.

### Coverage

| Security Type | Broker Queue Available |
|---------------|----------------------|
| Equities | **Yes** |
| ETFs | **Yes** |
| REITs | **Yes** |
| Warrants | **Yes** |
| CBBCs | **Yes** |
| Inline warrants | **Yes** |
| Debt securities | **Yes** |
| **Derivatives** | **NO** |

## 3. Feed Products

### Product Comparison

| Product | Code | Broker Queue | Update Mode | Notes |
|---------|------|-------------|-------------|-------|
| Securities Standard | **SS** | **Included natively** | Conflated (~2,000 spu/s) | Base-level product |
| Securities Premium | **SP** | Via free **CBQ** add-on | CBQ conflated; orders streaming | Streaming order data + conflated broker queue |
| Securities FullTick | **SF** | Implicit via per-order data | **Streaming** | Full order-by-order; broker ID implicit in each order |

### CBQ (Continuous Broker Queue)

| Attribute | Value |
|-----------|-------|
| Availability | **Complimentary** add-on with SP subscription |
| Update mode | Conflated (not streaming) |
| Content | Same broker queue as SS but as separate add-on channel |

### Cost

| Category | Cost |
|----------|------|
| Display usage | Included in SS/SP/SF subscription |
| **Non-display** (automated trading) | **HK$20,000/firm/month** |

## 4. Limitations

| Limitation | Detail |
|------------|--------|
| **Conflated updates** | Multiple changes within conflation interval merged; cannot see every individual change |
| **40-broker cap** | Deep books truncated beyond 40 brokers per side |
| **Broker ID ≠ ultimate client** | ID identifies the Exchange Participant, not the end investor |
| **Multiple IDs per broker** | Large brokers use multiple 4-digit IDs (e.g., Goldman Sachs, Morgan Stanley appear under **8+ IDs** each) |
| **No derivatives** | OMD-D products (DS, DP, DF) include MBP/MBO but NO broker identification |

### Conflation Detail

SS operates at ~2,000 snapshots per second (spu/s). At this rate, events within ~500μs windows are merged. SF (FullTick) provides streaming per-order data where broker identification is implicit — each order carries the broker ID.

## 5. Stock Connect

HKEX operates Stock Connect with mainland China, creating unique broker queue dynamics.

| Direction | Description | Broker Queue Visibility |
|-----------|-------------|------------------------|
| **Northbound** | HK/international investors → Shanghai/Shenzhen stocks | N/A (trading on SSE/SZSE) |
| **Southbound** | Mainland investors → HKEX stocks | **Specific Connect broker IDs** visible in HKEX broker queue |

### Connect Broker IDs

Stock Connect mainland investor orders route through specific designated Exchange Participant IDs. These are **distinct from regular HK broker IDs**, enabling identification of mainland Chinese investor flow in HKEX-listed securities.

| Observation | Implication |
|-------------|------------|
| Surge in Connect broker IDs at a price level | Mainland buying/selling interest |
| Connect IDs appearing ahead of institutional IDs | Mainland flow leading |
| Connect IDs absent in names usually popular with mainland | Potential regime change |

## 6. Analytical Applications

### Flow Detection

| Application | Method |
|-------------|--------|
| **Institutional flow** | Identify investment bank Exchange Participant IDs (Goldman, Morgan Stanley, etc.) |
| **Retail flow** | Identify retail-focused broker IDs |
| **Stock Connect flow** | Track specific Connect broker IDs for mainland investor activity |
| **Accumulation detection** | Same broker ID repeatedly appearing at multiple price levels |
| **Distribution detection** | Institutional broker IDs appearing on ask side across price levels |

### Alpha Signal Generation

| Signal | Description |
|--------|-------------|
| Broker composition change | New institutional brokers appearing at a price → potential informed flow |
| Queue position shift | Broker moving from deep to aggressive levels → urgency signal |
| Connect flow divergence | Mainland vs HK institutional flow disagreement → potential reversion |
| Broker count concentration | Few brokers dominating a level → potentially informed large orders |

## 7. Historical Timeline

| Date | Event |
|------|-------|
| 1986 | AMS (Automatic Matching System) launch — broker visibility available |
| Successive upgrades | AMS → AMS/3 → various iterations |
| **Sep 30, 2013** | **OMD-C** (Orion Market Data - Cash) launch — modern delivery mechanism |
| 2014 | Stock Connect (Shanghai) launch |
| 2016 | Stock Connect (Shenzhen) launch |

Real-time broker queue also available at IDX (Indonesia) and SET (Thailand). No equivalent at NYSE, Nasdaq, CME, LSE, JPX, or Chinese exchanges.

## 8. Gotchas Checklist

1. **Conflated, not streaming** — multiple changes within ~500μs interval merged; use SF for tick-by-tick
2. **40-broker cap per side** truncates deep books — you may miss brokers beyond top 40
3. **Broker ID ≠ ultimate client** — EP number identifies the brokerage, not the end investor
4. **Derivatives (OMD-D) has NO broker queue** — equities only feature
5. **Large brokers split across multiple 4-digit IDs** — e.g., Goldman Sachs uses 8+ IDs; must maintain mapping table
6. **Stock Connect broker IDs are distinct** from regular HK brokers — must know which IDs are Connect
7. **Non-display fee HK$20,000/firm/month** — separate cost for automated trading use
8. **CBQ is complimentary with SP** — no extra charge but requires SP subscription
9. **No equivalent at NYSE/Nasdaq/CME/LSE/JPX** — cannot replicate this analysis methodology elsewhere
