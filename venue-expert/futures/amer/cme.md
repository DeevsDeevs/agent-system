# CME Group Mechanics

4 exchanges on Globex. MDP 3.0 market data. 9 matching algorithms. SPAN/SPAN 2 margin. Aurora IL (CyrusOne).

## 1. Overview and Role

| Exchange | MIC | Products | Founded |
|----------|-----|----------|---------|
| CME | XCME | Equity index (ES, NQ), FX (6E, 6J), Livestock (LE, HE) | 1898 |
| CBOT | XCBT | Treasuries (ZN, ZB, ZF, ZT), Grains (ZC, ZS, ZW), SOFR (SR3) | 1848 |
| NYMEX | XNYM | Energy (CL, NG), Metals (GC, SI) | 1882 |
| COMEX | XCEC | Gold (GC), Silver (SI), Copper (HG) | 1933 |

All trade on **Globex** electronic platform at **CyrusOne CHI1, Aurora, Illinois**.

## 2. Market Data: MDP 3.0

### Encoding

| Attribute | Value |
|-----------|-------|
| Format | **SBE (Simple Binary Encoding)** |
| Byte order | **Little-endian** (native x86, zero-copy) |
| Transport | **UDP multicast** |
| Price encoding | int64 mantissa × 10⁻⁹ (fixed exponent -9) |
| Schema file | `templates_FixBinary.xml` (versioned) |
| Performance | Delivers trade messages ahead of legacy FIX/FAST **>95%** of the time |

### Message Types

| Category | Key Messages | Template IDs (approx v9+) |
|----------|-------------|---------------------------|
| Incremental Refresh | Book (bid/ask/implied), TradeSummary, DailyStatistics, SessionStatistics, LimitsBanding, Volume | 46, 48, 49, 51, 50, varies |
| Snapshot | SnapshotFullRefresh (MBP), SnapshotFullRefreshOrderBook (MBO) | 52, 53 |
| Security Definition | Future, Option, Spread, FixedIncome, Repo, FX | 54, 55, 56, 58, 59, varies |
| Security Status | SecurityStatus, SecurityStatusWorkup | 30, 60 |
| Admin | Heartbeat, ChannelReset, QuoteRequest | 12, 4, 39 |

Template IDs shift between schema versions — always reference the current `templates_FixBinary.xml`.

### Book Depth

| Book Type | Depth | Content | Implied Data |
|-----------|-------|---------|-------------|
| **MBP** (Market By Price) | Variable per instrument (typically **10**) | Aggregated per price | **Yes** — implied entries use MDEntryType E/F |
| **MBOFD** (Market By Order Full Depth) | **No limit** | Every individual order | No |
| **MBOLD** (Market By Order Limited Depth) | **Top 10** bid/ask | Individual orders | No |

**Implied depth = 2 levels (best 2 bid + best 2 ask), NOT 10.** Implied entries use distinct MDEntryType values: **E = Implied Bid, F = Implied Offer** (vs 0/1 for direct). Implied and direct books are maintained separately by the client and must be consolidated. NumberOfOrders (tag 346) is **NULL** for implied entries.

### Timestamps

| Field | Format | Location |
|-------|--------|----------|
| SendingTime | **uint64 ns since Unix epoch (UTC)** | Packet header (8 bytes) |
| MsgSeqNum | uint32 | Packet header (4 bytes) |
| TransactTime (tag 60) | uint64 ns | Message body — start of event processing time |

All messages from a single order action share the same TransactTime. CME synchronizes to a master clock at **microsecond accuracy** — nanosecond encoding provides ordering precision but not absolute ns accuracy.

### AggressorSide (Tag 5797)

Present in MDIncrementalRefreshTradeSummary.

| Value | Meaning | When Used |
|-------|---------|-----------|
| 0 | NoAggressor | Implied trades; market open/re-open after Velocity Logic |
| 1 | Buy | Standard continuous trading — buyer is aggressor |
| 2 | Sell | Standard continuous trading — seller is aggressor |

NoAggressor (0) for: (a) trades involving implied orders, (b) **market open or re-open after Velocity Logic events** (SecurityTradingStatus=15 or 21). First Order Detail entry for AggressorSide=1/2 is the aggressor order.

### SecurityTradingStatus (Tag 326)

| Value | Meaning |
|-------|---------|
| 2 | Trading Halt |
| 4 | Close |
| 15 | New Price Indication (pre-open auction) |
| 17 | Ready To Trade (Open) |
| 18 | Not Available For Trading |
| 21 | Pre-Open |
| 24 | Pre-Cross |
| 25 | Cross |
| 26 | Post Close |

SecurityTradingEvent (tag 1174): value 5 = Implied ON, value 6 = Implied OFF.

### Channel Structure

| Attribute | Value |
|-----------|-------|
| Channel IDs | 3-digit numbers |
| Feeds per channel | ~8 (Incremental A/B, MBP Recovery A/B, MBO Recovery A/B, Instrument Def A/B, TCP Replay) |
| Grouping | By asset class and exchange (CME, CBOT, NYMEX, COMEX) |
| Config | `config.xml` on CME SFTP site |
| Config update | **Weekly** |
| Sequence numbers | Per-channel, **reset weekly** |

### MatchEventIndicator (Tag 5799)

uint8 bitmap:

| Bit | Mask | Meaning |
|-----|------|---------|
| 7 | 0x80 | **End of Event** |
| 0 | 0x01 | Last trade summary in event |
| 4 | 0x10 | Last implied quote in event |

Within a single matching event, implied updates arrive last (flagged by bit 4).

## 3. Sequence Recovery

5-layer architecture in escalating order:

| Layer | Method | Transport | Constraints |
|-------|--------|-----------|-------------|
| 1 | **Feed A/B arbitration** | UDP | Dual-cast all incremental data; process both, arbitrate |
| 2 | **Market Recovery** | UDP snapshot loop | Continuous full book snapshots; **CME's recommended primary recovery** |
| 3 | **TCP Replay** | TCP | FIX-ASCII logon → SBE response; **max 2,000 packets; 24-hour window; one request per session** |
| 4 | **Instrument Recovery** | UDP loop | Continuous security definition messages |
| 5 | **Channel Reset** | UDP | Emergency: MDEntryType=J signals all books corrupted; RptSeq resets to 1 |

### Market Recovery Splice

Use `LastMsgSeqNumProcessed` (tag 369) and `TransactTime` from snapshot to splice with cached incremental data. Incremental messages with sequence ≤ LastMsgSeqNumProcessed are already reflected in the snapshot.

### TCP Replay Constraints

| Constraint | Value |
|-----------|-------|
| Max packets | **2,000 per request** |
| Data window | **24 hours** |
| Sessions | **One request per TCP session** |
| Protocol | FIX-ASCII logon → SBE response |
| Performance | Not optimized — small-scale recovery only |

TCP Replay is NOT for primary recovery. Use Market Recovery (layer 2) as the primary mechanism.

## 4. Matching Algorithms

9 algorithms identified by FIX tag 1142-MatchAlgorithm.

### Product-to-Algorithm Mapping

| Product | Code | Outright | Spread | Options |
|---------|------|----------|--------|---------|
| E-mini S&P 500 | ES | **FIFO (F)** | FIFO (F) | FIFO (F) |
| E-mini Nasdaq-100 | NQ | **FIFO (F)** | FIFO (F) | FIFO (F) |
| WTI Crude Oil | CL | **FIFO (F)** | FIFO (F) | Q or F |
| Natural Gas | NG | **FIFO (F)** | FIFO (F) | Q or F |
| Gold | GC | **FIFO (F)** | FIFO (F) | Q or F |
| Silver | SI | **FIFO (F)** | FIFO (F) | Q |
| 10-Year T-Note | ZN | **FIFO (F)** | K (20% FIFO / 80% PR) | **Q** |
| 5-Year T-Note | ZF | **FIFO (F)** | K (20/80) | **Q** |
| Treasury Bond | ZB | **FIFO (F)** | K | **Q** |
| Ultra T-Bond | UB | **FIFO (F)** | K | **Q** |
| 2-Year T-Note | ZT | **K** (Split FIFO/PR) | K (20/80) | **Q** |
| 30-Day Fed Funds | ZQ | **K** | K | **Q** |
| 3-Month SOFR | SR3 | **A** (Allocation) | FIFO (packs/bundles) | **Q** |
| 1-Month SOFR | SR1 | **A** (Allocation) | — | — |
| Corn | ZC | **K** (40% FIFO / 60% PR) | K (40/60) | **O** |
| Soybeans | ZS | **K** (40/60) | K (40/60) | **O** |
| Wheat | ZW | **K** (40/60) | K (40/60) | **O** |
| Live Cattle | LE | **FIFO (F)** | K (40/60) | **O** |
| Lean Hogs | HE | **FIFO (F)** | K (40/60) | **O** |
| Euro FX | 6E | **FIFO (F)** | **C** (Pro-Rata) | Q or O |
| Japanese Yen | 6J | **FIFO (F)** | **C** (Pro-Rata) | Q or O |

### Algorithm Descriptions

| Code | Name | Mechanism |
|------|------|-----------|
| F | FIFO | Pure time priority |
| K | Configurable | Split FIFO/Pro-Rata (ratios vary by product) |
| A | Allocation | TOP → Pro-Rata (min 2 lots) → FIFO residual |
| C | Pro-Rata (FX spreads) | Pro-rata for spread instruments |
| Q | Threshold Pro-Rata + LMM | Options: TOP + Pro-Rata + LMM allocation |
| O | Threshold Pro-Rata | Options: TOP + Pro-Rata (no LMM) |

### Volume Share (Databento Aug 2025)

| Algorithm | Share of CME Volume |
|-----------|-------------------|
| FIFO (F) | **~70.3%** |
| Configurable (K) | **~12.7%** |
| Allocation (A) | **~10.5%** |
| Others | ~6.5% |

### SOFR Matching Detail

SR3 (Three-Month SOFR) uses **Allocation (A)**:
1. **TOP order** fills entirely at 100% up to a maximum — first non-implied order to better the market
2. **Pro-rata** with **minimum 2 lots** among remaining resting orders
3. **FIFO residual** for remaining quantity

Inherited from Eurodollar (GE). SOFR packs and bundles use FIFO, not Allocation. SOFR options use Q (Threshold Pro-Rata + LMM).

Eurodollar fully delisted June 2023 (LIBOR cessation). 7.5M OI converted to SOFR April 14, 2023.

### LMM Rules

| Attribute | Value |
|-----------|-------|
| Scope | **Options only** (not futures) |
| Max allocation | **<50%** of total match quantity |
| Example | 10-Year Treasury Note options: LMM at 40% |
| Multiple LMMs | Possible per product; matched FIFO among themselves |

## 5. Modify Semantics

### FIFO Products

| Action | Queue Position |
|--------|---------------|
| Decrease quantity (price unchanged) | **Retained** |
| Increase quantity | **Lost** (re-queued to back) |
| Change price | **Lost** (re-queued to back) |
| Change account | **Lost** (re-queued to back) |
| GTC across sessions | **Retained** (absent priority-losing modifications) |

### Pro-Rata Products

| Attribute | Behavior |
|-----------|----------|
| Timestamp | Matters for TOP designation and FIFO residual allocation |
| Size changes | Directly affect pro-rata share (proportional to displayed qty / total at price) |
| FIFO component | Same re-queue rules as pure FIFO |

### Iceberg Orders

Display quantity refresh → **loses queue position** (re-queued to back upon each refresh).

## 6. Margin: SPAN and SPAN 2

### Classic SPAN (1988)

16-scenario parametric grid simulating worst-case one-day portfolio loss at 99% confidence.

### The 16 Scenario Grid

| Scenarios | Price Move (% of Scan Range) | Volatility | P&L Capture |
|-----------|------------------------------|------------|-------------|
| 1–2 | 0% (unchanged) | Up / Down | 100% |
| 3–6 | ±33% | Up / Down | 100% |
| 7–10 | ±67% | Up / Down | 100% |
| 11–14 | ±100% | Up / Down | 100% |
| **15–16** | **±300%** (extreme) | **Up only** | **33% only** |

Scenarios 15–16: ±3× scan range, capture only 33% of P&L — designed for deep OTM short option tail risk. **Scanning Risk** = maximum portfolio loss across all 16 scenarios.

Composite Delta computed using 7 price points with probability weights (0.270 at unchanged, tapering to 0.037 at ±100%).

### Scanning Range Calibration

| Parameter | Value |
|-----------|-------|
| Target | ≥**99th percentile** of historical daily price moves |
| Lookback | 1 month to 10 years |
| Review frequency | **Monthly** minimum |
| Volatility floors | Prevent margins from falling too low |
| Realized coverage | **99.97%** (Q3 2023) |
| Change notice | Minimum **24 hours** |

### Margin Components

| Component | Description |
|-----------|-------------|
| Scanning Risk | Max loss across 16 scenarios |
| **Intra-commodity spread charge** | Basis risk between contract months (assumed 0 by scenarios) |
| **Inter-commodity spread credit** | Reduction for correlated positions across products |
| **Short option minimum (SOM)** | Per-contract floor for deep OTM short options |

### Intra-Commodity Spread Charge

SPAN scenarios assume perfect correlation across months → $0 net P&L for calendar spreads. The intra-commodity charge captures basis risk. Example: Eurodollar Mar vs Apr spread charge = **$70** (the entire margin for that position).

### Inter-Commodity Spread Credit

| Example | Outright Total | Credit % | Net Margin |
|---------|---------------|----------|------------|
| 1 Long SP + 5 Short NQ | $68,000 | 75% | **$17,000** |

Credit percentages: exchange-determined, 60–85% typical for major pairs, based on historical correlations.

### Short Option Minimum (SOM)

Final requirement = MAX(SPAN calculation, SOM × max(short_calls, short_puts)). Example: S&P 500 SOM = **$240** (2019).

### Performance Bond Levels (Post-2021)

| Category | Initial Margin |
|----------|---------------|
| **Non-HRP** (Non-Heightened Risk Profile) | **100% of maintenance** |
| **HRP** (all retail) | **110% of maintenance** |

Replaced old Hedger/Speculator classification (1.25–1.50× multipliers).

### SPAN 2 Migration

| Asset Class | Status |
|-------------|--------|
| NYMEX Energy | **Completed** — July 21, 2023 |
| Equity Products | **Completed** — October 2024 |
| Interest Rate & FX | Pending — originally planned H2 2024, delayed |
| Agriculture & Remaining | Pending — originally planned H2 2025, delayed |

### SPAN 2 Methodology

| Attribute | SPAN 2 | Classic SPAN |
|-----------|--------|-------------|
| Scenarios | **Thousands** (filtered historical simulation) | 16 parametric |
| Methodology | **VaR-based** | Scenario-based |
| Risk components | HVaR + Stress + Liquidity + Concentration | Scanning + Spread + SOM |
| Formula | `Total = HVaR + max(0, Stress Risk − HVaR) + Liquidity + Concentration` | Max of 16 scenarios + adjustments |
| File size | **~20 GB** | Hundreds of MB |
| Replicability | Lower — approximation files available | Higher — standard 16-scenario grid |

## 7. Settlement Methodology

Tiered waterfall: VWAP → bid/ask midpoint → model/carry → staff discretion override.

### Per-Product Settlement Parameters

| Product | Code | Daily Method | Settlement Window (CT) | Duration | Final Settlement |
|---------|------|-------------|----------------------|----------|-----------------|
| E-mini S&P 500 | ES | VWAP lead month | **14:59:30–15:00:00** ⚠️ | 30 sec | SOQ of S&P 500 (3rd Fri) |
| E-mini Nasdaq-100 | NQ | VWAP lead month | **14:59:30–15:00:00** ⚠️ | 30 sec | SOQ via NOOP (3rd Fri) |
| WTI Crude Oil | CL | VWAP active month | 13:28:00–13:30:00 | 2 min | VWAP 30-min (13:00–13:30 CT) |
| Gold | GC | VWAP active month | 12:29:00–12:30:00 | 1 min | Non-active month (spread-based) |
| Treasury Bond | ZB | VWAP lead month | 13:59:30–14:00:00 | 30 sec | Physical delivery (invoice) |
| 3-Month SOFR | SR3 | Optimization | 13:59:00–14:00:00 | 60 sec | 100 − compounded SOFR |

### ES/NQ Settlement Window Discrepancy

⚠️ CME Confluence wiki (updated 2025) shows **14:59:30–15:00:00 CT**. Older education materials and CFTC filings show **15:14:30–15:15:00 CT**. The full-size SP contract delisting (September 2021) may have triggered a window change. **Verify with CME GCC at +1 800 438 8616 before production use.**

### CL Crude Oil Details

| Attribute | Value |
|-----------|-------|
| Active month window | **2-minute VWAP** (14:28:00–14:30:00 ET) |
| Back months | Calendar spread VWAPs in same window; spread volume / months between legs |
| Expiring contract | **30-minute window** (14:00:00–14:30:00 ET) |
| Bid/ask threshold | Minimum 200 contracts for consideration |

### SR3 SOFR Settlement

**Linear optimization** across multiple spread/butterfly instruments:
1. Front quarterly months seeded with VWAP
2. Adjusted within bid/ask ranges for 3/6/9/12-month calendar spreads + butterfly bids/asks
3. Solution minimizing spread violations and closest to VWAP seed values selected
4. Weighted toward nearer expirations

Final settlement: **100 − R**, where R = daily compounded SOFR over reference quarter (Actual/360 day count).

### Committee Override

All products: *"If CME Group staff, in its sole discretion, determines that anomalous activity produces results that are not representative of fair value, staff may determine an alternative settlement price."*

| Attribute | Value |
|-----------|-------|
| Authority | **GCC staff sole discretion** |
| Formal vote | Not required |
| Triggers | Insufficient data, system issues, price spikes, risk management |

## 8. Session Schedule

### Per-Product Session Hours (CT)

| Product | Sunday Open | Mon–Fri Open | RTH Open | RTH Close | Daily Maintenance |
|---------|------------|-------------|----------|-----------|-------------------|
| ES/NQ (Equity Index) | 17:00 Sun | 17:00 | 08:30 | 15:15 | 15:15–15:30; 16:00–17:00 |
| ZN/ZB/ZF/ZT (Treasuries) | 17:00 Sun | 17:00 | 07:20 | 14:00 | 16:00–17:00 |
| SR3 (SOFR) | 17:00 Sun | 17:00 | 07:20 | 14:00 | 16:00–17:00 |
| CL/NG (Energy) | 17:00 Sun | 17:00 | 08:00 | 13:30 | 16:00–17:00 |
| GC/SI (Metals) | 17:00 Sun | 17:00 | 07:20 | 12:30 | 16:00–17:00 |
| ZC/ZS/ZW (Grains) | 19:00 Sun | 19:00 | 08:30 | 13:20 | 07:45–08:30 |
| 6E/6J (FX) | 17:00 Sun | 17:00 | 07:20 | 14:00 | 16:00–17:00 |

Daily maintenance window: **16:00–17:00 CT** for most products (grains differ).

## 9. Outage Registry

| Date | Duration | Cause | Impact |
|------|----------|-------|--------|
| **Nov 28, 2025** | **~10–11 hours** | CyrusOne CHI1 cooling failure (chiller plant) | **All Globex markets** — equity index, Treasuries, crude, gold, silver, agriculture, FX, crypto |
| Aug 24, 2014 | ~4 hours | Planned software reconfiguration | All Globex (5:00–9:00 PM Chicago time) |
| ~2019 | ~3 hours | Unknown (limited public details) | Globex (partial) |

### Nov 28, 2025 Detail

| Attribute | Value |
|-----------|-------|
| Start | ~4:13 AM ET (post-Thanksgiving Friday) |
| Cause | Chiller plant failure at CyrusOne CHI1, Aurora |
| Failover | **CME chose NOT to failover to NY-area backup** |
| Duration | ~10–11 hours (3× previous record) |
| Restoration | All markets by 2:46 PM CT |
| Market impact | Gold erratic OTC moves; silver dropped $1 spot; $600B notional SPX options expiring could not be delta-hedged |

## 10. Gotchas Checklist

1. **Implied depth = 2, NOT 10** — only 2 best implied bid + 2 best implied ask levels published
2. **AggressorSide = 0** for implied trades and post-halt re-opens — cannot determine trade direction
3. **ES/NQ settlement window may have shifted** — verify 14:59:30 vs 15:14:30 with CME GCC before production
4. **Template IDs shift between schema versions** — always use current `templates_FixBinary.xml`
5. **TCP Replay: max 2K packets, 24h window, one request per session** — NOT for primary recovery
6. **Sequence numbers reset weekly** — handle wrap-around in feed handler
7. **SPAN 2 file size ~20 GB** — infrastructure must handle download/parse; classic SPAN was hundreds of MB
8. **Non-persistent orders deleted during auctions** — persistent orders preserved
9. **Channel assignments in config.xml** — updated weekly; must re-parse regularly
10. **Implied entries: NumberOfOrders = NULL** — check for NULL before accessing
11. **GCC Product Reference Sheet** — canonical source for per-instrument algorithm; tag 1142 in security definition
12. **SOFR packs/bundles use FIFO** — different from outright SR3 which uses Allocation (A)
13. **CyrusOne CHI1 single point of failure** — Nov 2025 outage showed no automatic failover
