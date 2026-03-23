# Data Characteristics — Cross-Venue Matrix

## Feed Comparison

| Venue | Protocol | Encoding | Depth | Timestamp | Update Freq | Recovery |
|-------|----------|----------|-------|-----------|------------|----------|
| CME | MDP 3.0 | SBE (fixed-length, little-endian) | 10 outright / **2 implied** | uint64 ns (UTC) | Real-time incremental (UDP multicast) | Feed A/B arb → UDP snapshot loop → TCP Replay (max 2K pkt, 24h) |
| Nasdaq | ITCH 5.0 | Binary (fixed-length) | Full order-by-order (unlimited) | ns | Real-time per-order | MoldUDP64 + Glimpse (TCP snapshot) |
| NYSE | XDP | Binary | Full order-by-order | ns | Real-time per-order | XDP retransmission |
| Cboe | PITCH | Binary | Full order-by-order | ns | Real-time per-order | PITCH retransmission |
| ICE | iMpact | Binary (proprietary multicast) | FOD (full order depth) + PL (top 5) | ms + MiFID μs | Real-time per-order | Snapshot channels + bundle markers (Type 'T') |
| Eurex | EOBI | Binary (T7) | Full L3 order-by-order, no depth limit | ns | Real-time per-order | Snapshot channels; co-lo only (10 Gbit/s) |
| SGX | ITCH (MoldUDP64) | Binary | Full order-by-order | ns | Real-time per-order | Rewinder (UDP unicast) + GLIMPSE (TCP snapshot) |
| CTA/UTP SIP | SIP | Binary | NBBO only (L1) | μs | Consolidated, conflated | N/A (consolidated output) |
| Chinese CTP (standard) | CTP TCP | Struct-based (440–580 bytes) | **1 level** | HH:MM:SS + ms (exchange-generated) | **500ms snapshots** | **No replay; reconnection gaps are permanent data loss** |
| Chinese CTP (co-lo L2) | CTP multicast / exchange direct | Struct-based | **5 levels** | Same | **250ms** (SHFE/INE/DCE/CZCE/GFEX); 500ms (CFFEX) | No replay |
| HKEX OMD-C (SS) | OMD-C | Binary | BBO + broker queue (up to 40/side) | Conflated (~2,000 spu/s) | Conflated | OMD-C recovery |
| HKEX OMD-C (SF) | OMD-C | Binary | Full order-by-order | Streaming | Real-time | OMD-C recovery |

## Data Quirks

| Venue | Quirk | Impact |
|-------|-------|--------|
| Chinese CTP | **No replay mechanism** | Reconnection gaps = permanent data loss; no way to recover missed snapshots |
| CZCE | **UpdateMillisec always = 0** | Cannot order events within same second; must interpolate (000, 500, 750, 875ms) |
| DCE | **ActionDay = TradingDay during night session** (wrong) | Night session ActionDay shows next business day, not actual calendar date; never trust DCE ActionDay |
| CZCE | **TradingDay = current date during night session** (wrong) | Does not advance to next trading day at night; never trust CZCE TradingDay at night |
| CZCE | **3-digit contract codes** (YMM not YYMM) | CF501 = 2025 or 2015? Disambiguate by context; CTP passes through as-is |
| CME MDP 3.0 | **Implied depth = 2 levels, NOT 10** | Book builders assuming 10-level implied are wrong; implied uses MDEntryType E/F |
| CME MDP 3.0 | NumberOfOrders = NULL for implied entries | Cannot count orders at implied price levels |
| ICE | Matching engine at **Basildon, not LD4** | Routing via LD4 adds unnecessary latency for ICE energy trading |
| HKEX | **Broker queue visibility** (unique globally) | 4-digit broker IDs per order; up to 40/side; equities only (not derivatives) |
| HKEX | Broker queue is **conflated, not streaming** | Multiple changes within interval merged; real-time but not tick-by-tick |
| SHFE/INE | UpdateMillisec only 0 or 500 | Binary pattern confirms exchange-generated timestamps, not CTP-generated |
| CFFEX | UpdateMillisec only 0 or 500 | Same binary pattern as SHFE |
| DCE | UpdateMillisec has variable real ms values | Different from SHFE/CFFEX pattern; confirms per-exchange timestamp generation |
| Eurex EOBI | No implied price labels | Implied/synthetic prices must be reconstructed from visible orders; EMDI publishes implied separately |
| Eurex EOBI | Auction: only BBO or clearing price, no depth | Depth information not published during volatility auctions |
| GFEX | Close flag always generic Close ('1') | Like DCE/CZCE/CFFEX; does NOT preserve CloseToday/CloseYesterday (unlike SHFE/INE) |
| Chinese CTP | AveragePrice scaling inconsistent | Divide by multiplier for SHFE/INE/DCE/CFFEX; CZCE AveragePrice is direct |
| Chinese CTP | Volume is cumulative | Must compute delta: Volume[t] - Volume[t-1]; decreases only at session boundaries |
| Chinese CTP | Night replay on reconnect | Duplicate/old data on reconnect; filter by comparing tick time to wall clock |
| CTP v6.5.1 | InstrumentID char[31]→char[81] | Binary-breaking struct change (Sep 2020); all code must recompile |
| Nasdaq ITCH | Stateless across days | All orders cancelled overnight; no persistent IDs; no corporate action messages |
| Bloomberg | Bar timestamps = bar open time (not close) | Off-by-one-period errors if not adjusted |
| Wind (万得) | A-share "tick" data = 3-second snapshots | Not true tick-by-tick; intra-snapshot dynamics invisible |
| VNPY | Truncates UpdateMillisec to 100ms precision | Deliberate loss of precision in `int(data['UpdateMillisec']/100)` |

## Timestamp Reliability by Exchange (Chinese Futures)

| Exchange | UpdateTime | UpdateMillisec | ActionDay (Night) | TradingDay (Night) |
|----------|-----------|---------------|-------------------|-------------------|
| SHFE | Reliable | 0 or 500 only | Correct (actual date) | Correct (next trading day) |
| INE | Reliable | 0 or 500 only | Correct | Correct |
| DCE | Reliable | Variable real ms | **Wrong** (= TradingDay) | Correct |
| CZCE | Reliable | **Always 0** | Correct | **Wrong** (= current date) |
| CFFEX | Reliable | 0 or 500 only | N/A (no night) | N/A |
| GFEX | Reliable | Variable (DCE pattern) | N/A (no night) | N/A |

## Per-Venue Details
- [[equity/amer/nasdaq/references/specs/itch_protocol.md|itch_protocol.md]] ITCH 5.0 Specification
- [[futures/amer/cme.md|cme.md]] §2 MDP 3.0
- [[futures/emea/eurex.md|eurex.md]] §2 EOBI
- [[equity/apac/hkex.md|hkex.md]] §3 Feed Products
