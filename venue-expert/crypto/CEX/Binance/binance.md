# Binance Exchange Mechanics

Binance-specific market microstructure. Assumes familiarity with CEX concepts from `cex.md`.

## Overview and Role

### Binance as Operator

Binance operates multiple platforms:

| Platform        | Description                    | API Base                             |
|-----------------|--------------------------------|--------------------------------------|
| Binance Global  | Main platform (non-US)         | api.binance.com                      |
| Binance.US      | US-regulated entity            | api.binance.us                       |
| Binance Futures | USDT-M and COIN-M derivatives  | fapi.binance.com / dapi.binance.com  |
| Binance Options | European-style options         | eapi.binance.com                     |

**Critical:** Binance.US has separate API with different rate limits, symbols, and features.

### Market Position

- Largest crypto exchange by volume (spot and derivatives)
- Primary price discovery venue for many pairs
- BNB native token for fee discounts

## Data Characteristics

### Update Frequency

WebSocket depth streams support configurable intervals:

| Stream Suffix | Frequency                          |
|---------------|------------------------------------|
| `@100ms`      | 100 milliseconds                   |
| `@1000ms`     | 1 second (default, no suffix)      |

> **Unofficial/undocumented intervals:** `@0ms`, `@250ms`, `@500ms` are not listed in official Binance API docs. Use at your own risk — behavior may change without notice.

### Order Book Depth

| Endpoint/Stream     | Max Levels          |
|---------------------|---------------------|
| REST snapshot       | 5000 per side       |
| WebSocket diff      | Incremental updates |
| Partial book stream | 5, 10, 20 levels    |

**Gotcha:** Depth beyond 5000 levels not visible without reconstructing from diffs.

### Timestamps

- Unix milliseconds (server time)
- Sync client clock via `GET /api/v3/time`
- Server time in response headers: `Date` and custom headers

### Connection Limits

| Limit Type             | Value                        |
|------------------------|------------------------------|
| Streams per connection | 1024 (Spot), 200 (Futures)   |
| Connections per 5 min  | 300 per IP                   |
| Inbound messages       | 5/sec (Spot), 10/sec (Futures) |

## Order Book Mechanics

### Matching Engine

**Price-Time Priority:**
Standard CLOB - price first, then time at same price level.

### Order Types

**Basic Types:**

| Type               | API Value            | Behavior                               |
|--------------------|----------------------|----------------------------------------|
| Limit              | `LIMIT`              | Execute at limit or better             |
| Market             | `MARKET`             | Immediate execution                    |
| Stop-Limit         | `STOP_LOSS_LIMIT`    | Trigger limit at stop price            |
| Stop-Market        | `STOP_LOSS`          | Trigger market at stop price           |
| Take-Profit-Limit  | `TAKE_PROFIT_LIMIT`  | Limit order triggered by profit target |
| Take-Profit-Market | `TAKE_PROFIT`        | Market order triggered by profit target |

**Time-in-Force:**

| TIF | Behavior                      |
|-----|-------------------------------|
| GTC | Good-Til-Canceled (default)   |
| IOC | Immediate-or-Cancel           |
| FOK | Fill-or-Kill                  |
| GTX | Post-Only (Good-Til-Crossing) |

**Advanced Types (Futures):**

| Type          | Description                            |
|---------------|----------------------------------------|
| Trailing Stop | Dynamic stop that follows price        |
| TWAP          | Time-weighted execution (institutional) |

### Self-Trade Prevention (STP)

STP prevents execution between orders of the same user (or users sharing a `tradeGroupId`). Behavior is determined by the **taker order's** STP mode; maker's mode is ignored.

**Parameter:** `selfTradePreventionMode` (optional, default: `EXPIRE_MAKER`)

**Spot modes (6):**

| Mode | Behavior |
|------|----------|
| `NONE` | STP disabled; self-trades allowed |
| `EXPIRE_TAKER` | Cancel remaining taker quantity |
| `EXPIRE_MAKER` | Cancel remaining maker quantity **(default)** |
| `EXPIRE_BOTH` | Cancel both orders |
| `DECREMENT` | Reduce both by prevented qty; smaller order expires |
| `TRANSFER` | Like DECREMENT; cross-account transfer within same `tradeGroupId` |

**Futures modes (3):** `EXPIRE_TAKER`, `EXPIRE_MAKER` (default), `EXPIRE_BOTH`. No `NONE`/`DECREMENT`/`TRANSFER`.

**Timeline:**

| Date | Event |
|------|-------|
| 2023-01-26 | STP launched for Spot API (optional) |
| 2023-09-06 | STP launched for Futures API |
| 2023-10-26 | Mandatory for all Spot/Margin users |
| 2024-12-10 | Mandatory for all Futures users |

**Gotchas:**
- Cancelled orders get status `EXPIRED_IN_MATCH`
- Futures: order modification resets STP to `NONE`
- Futures: STP only applies with `GTC`, `IOC`, `GTD` (not `FOK`/`GTX`)
- Per-symbol allowed modes queryable via `exchangeInfo` (`allowedSelfTradePreventionModes`)
- Prevented matches queryable: `GET /api/v3/preventedMatches` (Spot only)

## Rate Limiting

### Weight-Based System

Each endpoint has an assigned weight. Total weight is limited per time window.

**Spot API limits:**

| Limit          | Window     | Weight         |
|----------------|------------|----------------|
| Request weight | 1 minute   | 6000            |
| Orders         | 10 seconds | 100            |
| Orders         | 24 hours   | 200,000        |

**Headers to monitor:**
- `X-MBX-USED-WEIGHT-1M` - Current weight used
- `X-MBX-ORDER-COUNT-10S` - Orders in 10s window
- `X-MBX-ORDER-COUNT-1D` - Orders in 24h window

### Ban Escalation

| Violation       | Consequence                              |
|-----------------|------------------------------------------|
| 429 response    | Temporary block, backoff required        |
| Repeated 429s   | 2 minute IP ban                          |
| Continued abuse | Escalating bans up to 3 days             |
| 418 response    | IP banned - check `Retry-After` header   |

**Recovery:** Wait duration from `Retry-After` header. Do not retry during ban.

## Market Data Feeds

### WebSocket Streams

**Depth Streams:**

| Stream                 | Content                            |
|------------------------|------------------------------------|
| `<symbol>@depth`       | Diff depth stream (1000ms default) |
| `<symbol>@depth@100ms` | Diff depth stream (100ms)          |
| `<symbol>@depth5`      | Partial book (5 levels)            |
| `<symbol>@depth10`     | Partial book (10 levels)           |
| `<symbol>@depth20`     | Partial book (20 levels)           |

**Trade Streams:**

| Stream              | Content           |
|---------------------|-------------------|
| `<symbol>@trade`    | Real-time trades  |
| `<symbol>@aggTrade` | Aggregated trades |

**Ticker Streams:**

| Stream               | Content                 |
|----------------------|-------------------------|
| `<symbol>@ticker`    | 24h rolling window stats |
| `<symbol>@miniTicker`| Simplified ticker       |
| `<symbol>@bookTicker`| Best bid/ask updates    |

### Book Reconstruction

**Diff Depth Protocol:**

1. Open WebSocket to `<symbol>@depth@100ms`
2. Buffer incoming events
3. Get REST snapshot: `GET /api/v3/depth?symbol=X&limit=5000`
4. Drop buffered events where `u` <= `lastUpdateId` from snapshot
5. First processed event: `U` <= `lastUpdateId+1` AND `u` >= `lastUpdateId+1`
6. Each subsequent event: `U` = previous `u` + 1

**Fields:**
- `U` - First update ID in event
- `u` - Final update ID in event
- `lastUpdateId` - Snapshot's last update ID

**Gotcha:** Sequence gap = corrupted book. Must re-snapshot.

### No Built-in Checksum

Unlike some exchanges (Kraken, OKX, Bitfinex), Binance does not provide order book checksums.

**Validation alternatives:**
- Periodic REST snapshot comparison
- Cross-venue price sanity check
- Spread reasonableness check

## Fee Structure

### Spot Fees

**Standard rates:**

| Role  | Fee     |
|-------|---------|
| Maker | 0.1000% |
| Taker | 0.1000% |

**BNB discount:** 25% off when paying fees in BNB (subject to change; verify current rate via `GET /api/v3/account/commission`).

**VIP tiers:** Volume-based discounts:

| VIP Level | 30d Volume (BTC) | Maker   | Taker   |
|-----------|------------------|---------|---------|
| VIP 0     | < 250            | 0.1000% | 0.1000% |
| VIP 1     | >= 250           | 0.0900% | 0.1000% |
| VIP 2     | >= 1,000         | 0.0800% | 0.1000% |
| ...       | ...              | ...     | ...     |
| VIP 9     | >= 150,000       | 0.0200% | 0.0400% |

### Futures Fees

Lower than spot:

| Role  | USDT-M  | COIN-M  |
|-------|---------|---------|
| Maker | 0.0200% | 0.0100% |
| Taker | 0.0400% | 0.0500% |

## Data Quality Concerns

### Dynamic Frequency Degradation

`@0ms` is not documented in official Binance API docs (may be unofficial). Even `@100ms` and `@1000ms` (the only official intervals) may be throttled during high load.

### Symbol Renames

Historical continuity breaks on renames:
- `LUNA` → `LUNC` (May 2022)
- Various rebrandings

**Mitigation:** Track symbol changes via exchange announcements.

### Depth Snapshot Limitations

REST snapshot limited to 5000 levels. Deep book beyond this requires:
- Continuous diff accumulation
- Accepting incomplete view

### Delisting Impact

24-48 hours before delisting:
- Liquidity decreases
- Spreads widen
- Data may become unreliable

## Futures-Specific Mechanics

### Funding Rate

**Settlement:** Every 8 hours (00:00, 08:00, 16:00 UTC)

**Calculation:**
```
Funding Rate = Premium Index + clamp(Interest Rate - Premium Index, -0.05%, 0.05%)
```

**Impact:**
- Positive rate: longs pay shorts
- Negative rate: shorts pay longs
- Creates predictable flow near settlement

### Mark Price

Used for liquidations and unrealized PnL:
- Based on index price + funding basis
- Prevents manipulation via spot price spikes
- Different from last traded price

### Liquidation

**Tiers:** Position size determines maintenance margin requirement.

**Insurance Fund:** Absorbs losses from bankrupt positions.

**ADL (Auto-Deleveraging):** When insurance fund insufficient, profitable positions force-closed.

## API Endpoints Reference

### Key REST Endpoints

| Endpoint             | Method | Description          |
|----------------------|--------|----------------------|
| `/api/v3/depth`      | GET    | Order book snapshot  |
| `/api/v3/trades`     | GET    | Recent trades        |
| `/api/v3/klines`     | GET    | Candlestick data     |
| `/api/v3/ticker/24hr`| GET    | 24h statistics       |
| `/api/v3/order`      | POST   | Place order          |
| `/api/v3/openOrders` | GET    | Current open orders  |

### WebSocket Base URLs

| Environment    | URL                                |
|----------------|------------------------------------|
| Spot           | `wss://stream.binance.com:9443/ws` |
| Spot (backup)  | `wss://stream.binance.com:443/ws`  |
| Futures USDT-M | `wss://fstream.binance.com/ws`     |
| Futures COIN-M | `wss://dstream.binance.com/ws`     |

## Gotchas Checklist

1. **Sequence gaps** - Require full resync; no recovery mechanism
2. **No checksum** - Must validate via REST snapshots
3. **Weight limits** - Shared between REST and WebSocket API calls
4. **Binance.US ≠ Binance** - Completely separate API
5. **Testnet quality** - Data differs significantly from production
6. **Delisting window** - Data unreliable 24-48h before removal
7. **Status 418** - IP banned; must wait `Retry-After` duration
8. **Symbol case** - REST API expects uppercase (`BTCUSDT`), WebSocket streams expect lowercase (`btcusdt@depth`)
9. **Timestamp sync** - Required for signed requests; use server time
10. **Funding settlements** - Predictable flow every 8h
11. **Stream limits** - 1024 streams max per connection
12. **Connection limits** - 300 new connections per 5 min per IP
13. **Message rate** - 5 inbound msg/sec limit (Spot)
14. **Order book depth** - Max 5000 levels via REST

## Implementation Notes

### Connection Management

**Recommended pattern:**
```
1. Maintain persistent WebSocket connections
2. Implement heartbeat monitoring (no activity = potential disconnect)
3. Use multiple connections for many symbols
4. Implement exponential backoff for reconnection
5. Always resync book state after reconnect
```

### Order Book Maintenance

**Recommended pattern:**
```
1. Subscribe to depth@100ms stream
2. Buffer events
3. Fetch REST snapshot
4. Apply buffered events with sequence validation
5. Continue applying real-time events
6. Periodically validate against REST snapshot
7. On sequence gap: full resync
```

### Clock Synchronization

For signed requests:
```
1. Fetch server time: GET /api/v3/time
2. Calculate offset: server_time - local_time
3. Apply offset to request timestamps
4. Re-sync periodically (drift occurs)
```

## Regime-Changing Events (Backtest Reference)

Events that create structural breaks in Binance data. Any backtest spanning these dates must account for changed market conditions.

### Chronological Timeline

| Date | Event | Impact on Data |
|------|-------|----------------|
| 2020-06-28 | Matching engine rewrite (~10x perf) | Fill latency, queue priority, throughput all changed. Microstructure properties differ pre/post |
| 2021-07-19 | New futures accounts capped at 20x leverage (extended to 60 days on Jul 27) | Liquidation cascades less severe per unit OI. Funding rate dynamics shifted |
| 2022-05-10 | LUNA/UST crash begins, Terra withdrawals halted | LUNA $80→$0.01 over ~8 days (May 5–13). Spreads 10-50%+. Cascading liquidations across all markets |
| 2022-05-28 | LUNA renamed to LUNC, new Terra 2.0 LUNA listed May 31 | Ticker continuity broken. LUNA pre-May 28 ≠ LUNA post-May 31 — completely different assets |
| 2022-07-08 | Zero-fee BTC trading starts (13 pairs) | Volume massively inflated by wash trading. BTC/USDT volume-based signals unreliable |
| 2022-11-06 | Binance announces FTT liquidation → FTX crisis | BTC ~-10% in first 48h, -25% over ~2 weeks. Extreme volatility ~4 weeks. Funding rates deeply negative. FTX volume permanently redistributed to Binance |
| 2023-01-26 | STP launched for Spot API (mandatory for all Oct 11) | Post-STP volume is "cleaner" — self-trades rejected. Volume pre/post not comparable |
| 2023-02-13 | NYDFS orders Paxos to stop BUSD minting | BUSD pairs progressively delisted through 2023. Liquidity migrated to USDT/FDUSD |
| 2023-03-22 | Zero-fee BTC trading ends (except BTC/TUSD) | BTC volume collapsed to 8-month lows immediately after fees reinstated |
| 2023-03-24 | Matching engine bug halts spot trading ~2h | 2h gap in all spot data. BTC dropped ~$700 via cross-venue arb during outage |
| 2023-08-25 | API rate limit 1,200→6,000 weight/min | HFT/MM strategies could poll and execute more aggressively. Backtests modeling API constraints must use correct regime |
| 2023-09-06 | STP launched for Futures API | Same volume-cleaning effect as spot STP |
| 2023-09-07 | BTC/TUSD zero taker fee ends | Last zero-fee pair reverts. Market share shifts again |
| 2023-10-12 | Funding rate changed to 4h for all ≤25x leverage perps | Funding P&L calcs must use 4h intervals. Carry-trade profitability reduced. Historical 8h data must be resampled |
| 2023-11-21 | CZ guilty plea, $4.3B DOJ settlement, Richard Teng becomes CEO | BTC rallied (uncertainty removed). Post-regulatory era: compliance monitor, geo restrictions, product changes |
| 2023-12-15 | BUSD support fully ends on Binance | Auto-conversion to FDUSD on Jan 2 2024. All BUSD historical data becomes forward-irrelevant |
| 2024-04-30 | CZ sentenced to 4 months prison | Market non-event |

### Key Backtest Warnings

1. **Volume discontinuities:** Zero-fee BTC promotion (Jul 2022 – Mar 2023) and STP introduction (Jan 2023+) make volume data non-stationary. Any volume-based signal (VWAP, OBV, volume profile) must account for these regime shifts.

2. **Ticker renames:** LUNA→LUNC (May 2022). Data pipelines that naively merge tickers across rename boundaries conflate different assets.

3. **Fee regime changes:** BNB discount 50%→25% (Jul 2018), zero-fee BTC (Jul 2022 – Mar 2023), STP rejection of self-trades. Net P&L backtests must use correct fee schedule per period.

4. **Funding rate structural break:** 8h→4h transition (Oct 2023). Basis trading strategies calibrated on 8h intervals overestimate returns post-change.

5. **API capability breaks:** Rate limit 1,200→6,000 (Aug 2023), order limit 50→100/10s (Nov 2023). Live execution feasibility differs across periods.

6. **Data gaps:** Matching engine outages (Mar 2023 ~2h, various maintenance windows). Cross-venue arb moved prices during gaps.

## Cascading Failure Analysis

### Matching Engine Failure

**Architecture:** Multiple matching engines with hourly snapshots. Hot-standby with automatic failover (~10 seconds for hardware failure, per Oct 2023 incident). Futures runs on a separate engine from Spot.

**When the engine goes down:**

| Component | Behavior |
|-----------|----------|
| Spot trading | Fully halted (no new orders, no fills) |
| Futures | Continues independently (separate engine) |
| WebSocket streams | Market data stops; connections may stay open but no new events |
| Open orders | Remain in engine state; trailing stops may expire |
| Deposits/withdrawals | Suspended (engine state needed for balance verification) |

**Recovery sequence (observed Mar 2023, ~2.5h outage):**
1. Engine restart and reconciliation against last hourly snapshot
2. Deposits re-enabled
3. Internal transfers re-enabled
4. **Cancel-only mode (~30 min)** — users can cancel but not place orders
5. Full trading resumes

**Cross-venue impact:** During Mar 2023 outage, BTC dropped ~$700 on other venues via cross-venue arb. Binance price was frozen; arbitrageurs sold on live venues anticipating Binance would gap down on reopen.

### WebSocket Feed Failure

**No graceful shutdown warning.** Binance does not send pre-disconnect notifications before maintenance.

**Detection:**
- Spot: pong timeout after 60 seconds (server pings every 20s)
- Futures: pong timeout after 10 minutes
- No message sequence numbers — impossible to detect missed messages or request replay

**Impact:** During disconnection, local order book state becomes stale. On reconnect, full resync required (REST snapshot + resubscribe). If REST API is also degraded (rate limited during volatility), reconstruction window extends.

**Mitigation:** Redundant WebSocket connections from different IPs/regions.

### REST API Under Load

**Depth endpoint weight scales with requested levels:**

| Levels | Weight |
|--------|--------|
| 1-100 | 5 |
| 101-500 | 25 |
| 501-1000 | 50 |
| 1001-5000 | 250 |

During high volatility, many participants request snapshots simultaneously. Rate limiting (HTTP 429) delays book reconstruction, creating a window where local state cannot be validated.

### Cascade Propagation Pattern

Observed during Oct 2025 crash ($19.3B liquidations across all venues):

```
Price drop → Maintenance margin breach → Liquidation engine activates
    → forceOrder events on WS → Liquidation orders hit order book
    → Further price drop → More margin breaches → Acceleration
    → Bid-side liquidity collapses (spreads widen 1000x+)
    → Insurance fund depletes → ADL triggers on profitable positions
```

**Quantitative markers from Oct 2025:**
- Liquidation rate accelerated from $0.12B/hour (baseline) to $10.39B/hour (86x)
- Bid-ask spread widened from 0.02 bps to 26.43 bps (1,321x)
- Order book depth collapsed from $103.64M to $0.17M (-99.8%)
- OI collapsed $19.2B in 40 minutes
- 83.9% of liquidations were longs (extreme one-sided)

**Platform-specific failures during Oct 2025:**
- Asset transfer subsystem degraded for 33 minutes (database performance regression at 5-10x normal traffic)
- Index price oracle anomalies for 39 minutes (USDe, WBETH, BNSOL — oracle over-weighted Binance's own order book)

### Funding Settlement Delay

No publicly documented incident of Binance skipping or delaying a funding rate settlement. However, during the Oct 2025 cascade the asset transfer subsystem was degraded for 33 minutes — funding payments depend on the same balance infrastructure, so settlement accuracy during such events is uncertain.

**Risk scenario:** If settlement is delayed while positions change, the funding payment amount (based on mark price at settlement time) could be calculated against an incorrect or stale mark price.

### Listen Key Silent Expiry

Listen key expires after 60 minutes without keepalive. **No error event is sent** — the WebSocket connection simply stops receiving updates or drops silently.

**Failure mode:** If keepalive PUT request fails (rate limited, network issue) and goes undetected, the user data stream dies without notification. Orders continue executing on the engine but the client receives no updates.

**Detection:** Monitor time since last `executionReport` or `outboundAccountPosition`. If silent for longer than expected given trading activity, assume key expired. Spot sends `eventStreamTerminated` in some cases; Futures sends `listenKeyExpired`.

### Book Reconstruction Infinite Loop

The diff depth sync protocol (step 5) requires: first event where `U <= lastUpdateId+1 AND u >= lastUpdateId+1`. **No timeout is specified by Binance.**

**Pathological scenario:** If the REST snapshot is taken during a period of very rapid updates, and the buffered WS events don't contain one satisfying the sync condition (all events have `U > lastUpdateId+1`), the sync condition is never met. The implementation loops forever waiting for a qualifying event that already passed.

**Mitigation:** Implement a timeout (e.g., 5 seconds). If sync condition not met, discard snapshot and restart from step 1.

### Known Outage History

| Date | Type | Duration | Affected | Impact |
|------|------|----------|----------|--------|
| 2020-12-21 | Engine failure | ~1-2h | All spot, margin, deposits | Futures unaffected (separate engine) |
| 2021-05-19 | Overload during crash | ~50 min | Position management | Users unable to close positions; 775K+ accounts liquidated |
| 2023-03-24 | Trailing stop bug | ~2.5h | All spot, deposits/withdrawals | BTC -$700 on other venues |
| 2023-10-17 | Hardware failure | ~10s | Matching engine | Automatic failover to backup |
| 2025-10-10 | DB regression + oracle flaw | 33-39 min | Transfers, index prices | Part of $19.3B industry-wide cascade |

## Research Agent Guidance

### Data Validation

**Order book integrity:**
- Verify `U` (first update ID) = previous `u` + 1 on every depth event. Gap = corrupted book, resync required
- Check spread is non-negative (best_ask > best_bid). Negative spread = corrupted state
- Periodically compare local book top-of-book against REST snapshot (`GET /api/v3/depth?limit=5`)

**Stale data detection:**
- Spot `bookTicker` lacks `E`/`T` fields — cannot measure staleness from timestamps. Cross-reference with `depth` stream timing
- No depth updates for >3× expected frequency (>300ms for @100ms stream) = likely stale
- Cross-venue price divergence >0.5% from other major exchanges = potential feed issue

**Trade data sanity:**
- `aggTrade` aggregates per taker order at same price level, not per taker order total
- `m=true` means seller aggressed (buyer was maker), NOT a "buy trade"
- Compare `aggTrade` volume against kline `v` field for consistency

### Regime Awareness

Before analyzing any historical data, check the Regime-Changing Events timeline above. Key questions:

1. **Fee regime:** Is this period zero-fee BTC? Volume signals unreliable if so
2. **STP regime:** Pre-Oct 2023 volume includes self-trades; post-STP is cleaner
3. **Funding interval:** 8h before Oct 2023, 4h after (for ≤25x perps)
4. **API limits:** Pre-Aug 2023 = 1,200 weight/min; post = 6,000
5. **Ticker continuity:** LUNA ≠ LUNC; check for renames before merging data

### Microstructure Signals

**OBI from depth and trades:**
- Book OBI: `(Bid_Qty - Ask_Qty) / (Bid_Qty + Ask_Qty)` from `depth` stream top-N levels
- Trade OBI: `(Buy_Vol - Sell_Vol) / (Buy_Vol + Sell_Vol)` from `aggTrade` (`m=false` = buy, `m=true` = sell)
- Divergence (strong Trade OBI but weak Book OBI) may indicate momentum exhaustion

**Tick size regime classification:**
- BTCUSDT perp: $0.10 tick / ~$95K price = ~0.01 bps → small-tick (spread spans many ticks)
- CRVUSDT: ~38 bps tick → large-tick (spread = 1 tick >90% of time)
- Query via `exchangeInfo` → `PRICE_FILTER` → `tickSize`. Regime affects maker strategy viability

**Hidden liquidity detection:**
- Compare `trade` stream fill sizes against visible `depth` quantity at that level
- Multiple fills at same price with same resting-side order ID (`b`/`a` fields in `trade` stream) but visible qty was smaller → iceberg order

### Cross-Venue Context

**Price discovery leadership:**
- Binance leads on most major pairs due to volume dominance
- Academic evidence: sub-second lead-lag varies by pair and period; no single venue permanently leads
- Futures and spot show bidirectional predictability — neither consistently leads the other

**Timestamp alignment:**
- Binance depth: 100ms or 1000ms batched updates
- Other venues: different batch frequencies (OKX 100ms, Bybit 100ms, Kraken varies)
- For cross-venue signals, normalize to common time grid. Use event timestamps (`E` field), not local receive time

**Stablecoin basis adjustment:**
- USDT/USD normal: 0-5 bps. Stress: LUNA crash ~200 bps, FTX crash ~300 bps ($0.97)
- FDUSD: launched mid-2023, severe depeg Apr 2025 (~1300 bps, dropped to $0.87)
- Cross-venue arb P&L must account for stablecoin basis risk when comparing USDT-denominated prices across venues

### Signal Validation

**100ms resolution constraints:**
- At 100ms depth updates, you see a fraction of actual book changes (most updates batched away)
- 500-2000 trades/sec during active periods are batched into ~10 snapshots/sec
- Minimum viable signal horizon: ~300ms-1s. Sub-100ms alpha requires colocated infrastructure with raw feed access (not available on Binance)

**bookTicker vs depth for L1:**
- `bookTicker` updates on every BBO change (real-time). `depth` is batched (100ms minimum)
- For L1 (best bid/ask) signals, `bookTicker` is structurally faster
- But `bookTicker` ⊂ `depth` — depth provides L1 + full book. Using both creates redundancy

**Orthogonality warning:**
- `bookTicker` data is a subset of `depth` data (both contain BBO)
- Kline taker buy volume (`V` field) is a pre-computed aggregation of `aggTrade` data
- Treating these as independent signals double-counts the same information

### Arbitrage Operations

**Cross-exchange fee math (both legs):**
```
Net_PnL = Price_Diff - Fee_Venue_A(maker/taker) - Fee_Venue_B(maker/taker) - Withdrawal_Fee - Stablecoin_Basis_Risk
```

Cross-venue fee tables and withdrawal/deposit mechanics: → See `crypto.md` § Cross-Exchange Latency.

### Post-Hoc Analytics

**Fee attribution:**
- `executionReport` WS event fields: `n` (commission amount), `N` (commission asset)
- Commission varies by order: maker vs taker fill, BNB discount active or not
- For accurate backtest P&L, use actual `n`/`N` from fills, not assumed fee schedule

**Timestamp limitation:**
- Each fill produces a single timestamp `T` (transaction time). No separate timestamps for: order received, queued, matched, acknowledged
- Latency decomposition (queue time, matching time, wire time) is **not possible** from Binance data alone
- For latency analysis, compare local send time against `T` in `executionReport` — this gives only round-trip, not breakdown

**Liquidation cascade detection (post-hoc):**
- Combine: `forceOrder` frequency + OI drop velocity + depth asymmetry (bid depth << ask depth)
- Insurance fund balance history: `GET /fapi/v1/insuranceFund` (but only provides daily snapshots, not real-time)
- ADL indicator from `GET /fapi/v3/positionRisk` — rising ADL quantile = increasing risk of force-close

**Matching engine outage patterns:**
- Check for gaps in trade data (no `aggTrade` events for >1 second during active hours)
- Cross-reference with Binance status page announcements or `GET /api/v3/exchangeInfo` → `status` field
- During recovery: cancel-only mode produces order cancellations but no new fills — detectable as spike in `CANCELED` execution types with zero `TRADE` events

### Common Pitfalls

| Pitfall | Detection | Fix |
|---------|-----------|-----|
| Symbol case mismatch | REST returns 400 | REST: uppercase `BTCUSDT`; WS: lowercase `btcusdt@depth` |
| Book sequence gap | `U != prev_u + 1` | Full resync from REST snapshot |
| Stale bookTicker (Spot) | Cannot detect from timestamps alone | Cross-reference with depth stream |
| Rate limit during volatility | HTTP 429 on snapshot requests | Pre-fetch snapshots; reduce depth level (lower weight) |
| Funding rate regime mismatch | Wrong P&L calculations | Check symbol's funding interval via `GET /fapi/v1/fundingInfo` |
| Zero-quantity depth entry | Not a deletion bug | `quantity: "0.00"` means level removed — apply as removal, not as zero-size order |

## References

See `references/` directory:
- `specs/websocket_api.md` - WebSocket API specification
- `specs/rest_api.md` - REST API specification
- `specs/futures_api.md` - Futures-specific endpoints
- `regulatory/terms_of_service.md` - Platform rules
