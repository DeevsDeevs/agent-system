# Eurex Exchange Mechanics

T7 platform. Fixed income and equity index futures. EOBI co-location only. Assumes familiarity with CME matching concepts.

## 1. Identity

| Attribute | Value |
|-----------|-------|
| Platform | **T7** |
| MIC | **XEUR** |
| Co-location | **Equinix FR2, Frankfurt** |
| Matching | Price-time (FIFO) for most products; Pro-Rata for rates |

### Product Universe

| Category | Products | Codes |
|----------|----------|-------|
| FI futures | Euro-Bund, Euro-Bobl, Euro-Schatz, Euro-Buxl, Euro-OAT, Euro-BTP | FGBL, FGBM, FGBS, FGBX, FOAT, FBTP |
| Equity index futures | Euro Stoxx 50, DAX, Mini-DAX | FESX, FDAX, FDXM |
| Rate futures | 3-Month Euribor, Euro STR | FEU3, FST3 |
| Equity/index options | Options on above + ETF options | Various |

## 2. Market Data: EOBI

Enhanced Order Book Interface — full Level 3 order-by-order feed.

### Feed Characteristics

| Attribute | Value |
|-----------|-------|
| Depth | **No limit** — every visible order at every price level |
| Granularity | Individual order level (L3) |
| Timestamp precision | **Nanosecond** |
| Transport | UDP multicast |
| Availability | **Co-location only (10 Gbit/s)** — NOT available remotely |

### Message Types

| Message | Template ID | Description |
|---------|-------------|-------------|
| Order Add | 13100 | New visible order |
| Order Modify | 13101 | Modification with priority loss |
| Order Modify Same Priority | 13106 | Quantity decrease, priority retained |
| Order Delete | 13102 | Order removed |
| Partial Order Execution | 13105 | Individual resting order partial fill |
| Full Order Execution | 13104 | Individual resting order full fill |
| Execution Summary | 13202 | Aggregated match info (sent first) |
| Auction Best Bid/Offer | 13500 | Uncrossed book during auction |
| Auction Clearing Price | 13501 | Crossed book during auction |
| Product State Change | 13300 | Product-level trading phase transition |
| Instrument State Change | 13301 | Instrument-level trading phase transition |

### Product Coverage

EOBI available for select benchmark derivatives:
- **FI futures**: FGBL, FGBM, FGBS, FGBX, FOAT, FBTP
- **Equity index**: FESX, FDAX, FDXM
- **All Xetra cash products**

### Auction Depth Limitation

During auctions (opening, closing, volatility), EOBI publishes **only**:
- Auction BBO (Template 13500) — uncrossed book
- Auction Clearing Price (Template 13501) — crossed book

**No depth information during auctions.** Full order-by-order depth resumes only when continuous trading begins.

### Alternative Feeds

| Feed | Content | Availability |
|------|---------|-------------|
| EOBI | Full L3, no depth limit, ns timestamps | Co-lo only (10 Gbit/s) |
| EMDI | Aggregated depth + "Top Of Book Implied" | Wider availability |
| MDI | Basic market data | Remote access |

EMDI separately publishes implied/synthetic top-of-book for IPS matching opportunities — information not available in EOBI.

## 3. Matching Algorithms

### Per-Product Algorithm Table

| Product | Code | Algorithm | Notes |
|---------|------|-----------|-------|
| Euro-Bund | FGBL | **Time (FIFO)** | |
| Euro-Bobl | FGBM | **Time (FIFO)** | |
| Euro-Schatz | FGBS | **Time (FIFO)** | |
| Euro-Buxl | FGBX | **Time (FIFO)** | |
| Euro-OAT | FOAT | **Time (FIFO)** | |
| Euro-BTP | FBTP | **Time (FIFO)** | |
| Euro Stoxx 50 | FESX | **Time (FIFO)** | |
| DAX | FDAX | **Time (FIFO)** | |
| Mini-DAX | FDXM | **Time (FIFO)** | |
| 3-Month Euribor | FEU3 | **Pro-Rata** | Key difference from FI/equity |
| Euro STR | FST3 | **Pro-Rata** | |
| Most equity/index options | — | **Time (FIFO)** | Default |
| Select ETF options (iShares) | — | **Pro-Rata** | |

### Modify Semantics

| Action | Queue Position |
|--------|---------------|
| Decrease quantity (price unchanged) | **Retained** (Template 13106) |
| Increase quantity | **Lost** (Template 13101) |
| Change price | **Lost** (Template 13101) |
| Change account | **Lost** |

Same pattern as CME FIFO and ICE FIFO.

## 4. Volatility Interruptions

Dynamic circuit breaker mechanism — triggers when potential execution price exceeds configured thresholds.

### Trigger Mechanism

| Parameter | Description |
|-----------|-------------|
| Reference price | Last traded price or auction price |
| Max deviation | Exchange-configured per product |
| Lookback window | Exchange-configured per product |
| Trigger condition | Potential execution price exceeds reference ± max deviation within lookback |

### Sequence of Events

1. Triggering order enters the **auction book** (not executed)
2. Prior executions in the same matching cycle **remain valid** (not rolled back)
3. **Non-persistent orders and quotes deleted** from the book
4. **Persistent orders preserved** in the book
5. Instrument moves to **Volatility Auction** state
6. Call phase ends **randomly** after a minimum duration (anti-gaming)
7. If price remains outside extended range: **Market Supervision manually terminates**

### Order Handling During Volatility Interruption

| Order Type | Behavior |
|------------|----------|
| Non-persistent orders | **Deleted** |
| Non-persistent quotes | **Deleted** |
| Persistent orders | **Preserved** in auction book |
| New orders during auction | Accepted into auction book |

## 5. Self-Trade Prevention

Available since **T7 Release 12.1**.

### STP Modes

| Mode | Behavior |
|------|----------|
| Cancel Resting | Cancel the resting order; incoming executes |
| Cancel Incoming | Cancel the incoming order; resting preserved |
| Cancel Both | Cancel both orders; no execution |

### Restrictions

| Restriction | Detail |
|-------------|--------|
| Trading phase | **Continuous trading only** — NOT active during auctions |
| Pro-rata products | **Cancel Resting only** — Cancel Incoming and Cancel Both not accepted |
| Matching unit | STP operates within a single matching unit |

## 6. Session Schedule

### Trading Hours (CET)

| Phase | Time | Notes |
|-------|------|-------|
| Pre-trading | **01:00** | Order entry begins |
| Continuous trading start | **01:15** | Asian hours session (since Dec 2018) |
| Continuous trading end | **22:00** | |
| Closing auction | After 22:00 | **≥3 min call with random end** |
| Total continuous | ~20 hrs 45 min | |

### Timeline

| Date | Change |
|------|--------|
| Dec 2018 | Asian hours session introduced (01:15 start vs previous ~08:00) |

## 7. Implied Pricing

T7 supports synthetic matching between calendar spreads and outright legs.

### Mechanics

| Concept | Description |
|---------|-------------|
| Implied-in | Outright order legs fill as part of a spread execution |
| Implied-out | Spread order creates synthetic outright liquidity |
| Direction | Both implied-in and implied-out supported |

### Key Changes

| Date | Change |
|------|--------|
| Dec 2020 | **FDAX/FDXM synthetic matching decoupled** |

### Feed Visibility

| Feed | Implied Visibility |
|------|-------------------|
| EOBI | **NOT labeled** — implied/synthetic orders indistinguishable from direct; must reconstruct from visible orders |
| EMDI | Separately publishes **"Top Of Book Implied"** for IPS matching |

This is a critical difference from CME MDP 3.0, where implied entries use distinct MDEntryType values (E/F).

## 8. Designated Market Makers

| Attribute | Description |
|-----------|-------------|
| Incentive | Fee discounts |
| Obligations | Continuous quoting requirements |
| Structure | Product-specific bilateral agreements with Eurex |
| Coverage | Selected products (not all) |

## 9. Gotchas Checklist

1. **EOBI co-lo only (10 Gbit/s)** — no remote access; must be in Equinix FR2 Frankfurt
2. **Implied prices NOT labeled in EOBI** — must reconstruct from visible orders; use EMDI for implied TOB
3. **Auction depth invisible** — only BBO (13500) or clearing price (13501) published during auctions
4. **Volatility auction random end** — minimum duration + random extension; cannot predict exact timing
5. **Non-persistent orders deleted on volatility interruption** — only persistent orders survive
6. **STP not active during auctions** — self-trades possible during opening/closing/volatility auctions
7. **FDAX/FDXM synthetic decoupled since Dec 2020** — no implied matching between FDAX and FDXM
8. **Pro-rata products: only Cancel Resting STP** — Cancel Incoming and Cancel Both rejected
9. **Asian hours since Dec 2018** — 01:15 CET start captures Asian trading; pre-2018 data has different session structure
10. **EOBI Template IDs are fixed** — unlike CME where template IDs shift between schema versions
