# ITCH Protocol Specification

Nasdaq TotalView-ITCH 5.0 - binary protocol for disseminating full depth-of-book market data.

## Overview

ITCH is a high-performance, low-latency protocol for market data dissemination. Provides:
- Full order book depth
- Order-level event stream
- Auction imbalance data
- System and stock reference data

**Official specification:** https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHSpecification.pdf

## Version History

| Version | Spec Date | Key Changes | Compat |
|---------|-----------|-------------|--------|
| ITCH 1.00 | Jan 19, 2000 | Session mgmt to higher protocol; Broken Trade; timestamps hundredths of sec | Breaking |
| ITCH 2.00 | Nov 5, 2001 | Price 6+4 implied digits; timestamps → ms; shares 9→6 digits | Breaking |
| ITCH 2.0a | Feb 24, 2006 | References INET→NASDAQ; attributed Add Order (F); Halt/Resume | Additive |
| ITCH 3.00 | Jul 11, 2006 | Separate Seconds/Milliseconds msgs; Stock Directory, NOII, Type C/D/Q | Breaking |
| ITCH 3.10 | Oct 20, 2008 | Order Ref/Match ID expanded to 12B; Order Replace added | Additive |
| ITCH 4.00 | Oct 21, 2008 | All numerics → binary (from ASCII); ns timestamps (Seconds+ns field); SoupBinTCP | Breaking |
| ITCH 4.10 | Jan 26, 2010 | Symbol 6→8 chars; NYSE/MKT/Arca Market Category; Reg SHO (Jul 2010); RPI (Nov 2012) | Breaking (widths) |
| ITCH 5.00 | Jul 10, 2013 | Unified 6B ns timestamp; Stock Locate (2B) + Tracking Number (2B) all msgs; MWCB/IPO/LULD msgs | Breaking (all offsets) |

**Version detection:** Encoded in directory path (`ITCHFiles_v5`, `ITCHFiles_v41`) and filename (`SMMDDYY-v#.txt.gz`). BinaryFILE format (2-byte big-endian length + payload) is version-agnostic — no header indicates ITCH version.

**ITCH 5.0 historical data available from April 8, 2014** in Nasdaq Data Store. Exact ITCH 4.1 sunset undocumented but falls between Jul 2013 spec and early 2014.

**FPGA feed:** MoldUDP64 only (10Gb/40Gb at Carteret). Software and FPGA carry identical ITCH 5.0 payloads in guaranteed identical order.

## Protocol Characteristics

### Message Format

- **Fixed-length messages** - Each message type has defined length
- **Binary encoding** - No delimiters, position-based fields
- **Big-endian** - Network byte order
- **Message type first** - First byte identifies message type

### Transport

**Primary:** MoldUDP64 (UDP multicast)
- Sequenced delivery
- Gap detection via sequence numbers
- Downstream recovery mechanism

**Recovery:** SoupBinTCP (TCP)
- Reliable delivery
- Session-based
- Used for gap fill and replay

## Message Types

### System Messages

| Type | Name | Purpose |
|------|------|---------|
| S | System Event | Market open/close, start/end of day |
| R | Stock Directory | Symbol reference data |
| H | Stock Trading Action | Halt/resume status |
| Y | Reg SHO Restriction | Short sale restriction |
| L | Market Participant Position | Market maker registration |

### Order Messages

| Type | Name | Description |
|------|------|-------------|
| A | Add Order (No MPID) | New order added to book |
| F | Add Order (with MPID) | New order with market participant ID |
| E | Order Executed | Shares executed from order |
| C | Order Executed with Price | Executed at different price |
| X | Order Cancel | Partial cancellation |
| D | Order Delete | Full order removal |
| U | Order Replace | Modify existing order |

### Trade Messages

| Type | Name | Description |
|------|------|-------------|
| P | Non-Cross Trade | Trade not from cross |
| Q | Cross Trade | Opening/closing/halt cross |
| B | Broken Trade | Trade break notification |

### Auction Messages

| Type | Name | Description |
|------|------|-------------|
| I | NOII | Net Order Imbalance Indicator |

### Administrative Messages

| Type | Name | Description |
|------|------|-------------|
| J | LULD Auction Collar | Price bands |
| K | IPO Quoting Period | IPO release time |
| h | Operational Halt | Halt status |

## Key Message Structures

### Add Order (Type A/F)

| Field | Offset | Length | Type | Description |
|-------|--------|--------|------|-------------|
| Message Type | 0 | 1 | Alpha | 'A' or 'F' |
| Stock Locate | 1 | 2 | Integer | Symbol identifier |
| Tracking Number | 3 | 2 | Integer | Nasdaq tracking |
| Timestamp | 5 | 6 | Timestamp | Nanoseconds since midnight |
| Order Reference Number | 11 | 8 | Integer | Unique order ID |
| Buy/Sell Indicator | 19 | 1 | Alpha | 'B' or 'S' |
| Shares | 20 | 4 | Integer | Order quantity |
| Stock | 24 | 8 | Alpha | Symbol (space padded) |
| Price | 32 | 4 | Price (4) | Limit price |
| Attribution | 36 | 4 | Alpha | MPID (F only) |

**Total length:** A=36 bytes, F=40 bytes

### Order Executed (Type E)

| Field | Offset | Length | Type | Description |
|-------|--------|--------|------|-------------|
| Message Type | 0 | 1 | Alpha | 'E' |
| Stock Locate | 1 | 2 | Integer | Symbol identifier |
| Tracking Number | 3 | 2 | Integer | Nasdaq tracking |
| Timestamp | 5 | 6 | Timestamp | Nanoseconds since midnight |
| Order Reference Number | 11 | 8 | Integer | Order being executed |
| Executed Shares | 19 | 4 | Integer | Shares executed |
| Match Number | 23 | 8 | Integer | Unique match ID |

**Total length:** 31 bytes

### NOII (Type I)

| Field | Offset | Length | Type | Description |
|-------|--------|--------|------|-------------|
| Message Type | 0 | 1 | Alpha | 'I' |
| Stock Locate | 1 | 2 | Integer | Symbol identifier |
| Tracking Number | 3 | 2 | Integer | Tracking |
| Timestamp | 5 | 6 | Timestamp | Nanoseconds |
| Paired Shares | 11 | 8 | Integer | Matched shares |
| Imbalance Shares | 19 | 8 | Integer | Imbalance size |
| Imbalance Direction | 27 | 1 | Alpha | B/S/N/O |
| Stock | 28 | 8 | Alpha | Symbol |
| Far Price | 36 | 4 | Price (4) | Far indicative |
| Near Price | 40 | 4 | Price (4) | Near indicative |
| Current Ref Price | 44 | 4 | Price (4) | Reference |
| Cross Type | 48 | 1 | Alpha | O/C/H/I |
| Price Variation | 49 | 1 | Alpha | Indicator |

**Total length:** 50 bytes

## Data Types

### Price Encoding

Prices stored as integers with implied decimal:
- **Price (4):** 4 bytes, divide by 10000 for dollars
- Example: 1234500 = $123.45

### Sub-Penny Price Encoding

**Price(4):** 4-byte unsigned big-endian, 4 implied decimal places (value = price x 10,000).

| Price | Integer | Hex | Context |
|-------|---------|-----|---------|
| $100.00 | 1,000,000 | 0x000F4240 | Standard penny |
| $100.005 | 1,000,050 | 0x000F4272 | Midpoint of $100.00/$100.01 |
| $100.0025 | 1,000,025 | 0x000F4259 | Under half-penny tick regime |
| $0.0001 | 1 | 0x00000001 | Minimum non-zero (sub-dollar) |
| $200,000.0000 | 2,000,000,000 | 0x77359400 | Maximum Price(4) |

**Price(8):** 8 implied decimals. Only in MWCB Decline Level Message (Type V) — Level 1/2/3 fields. All other message types use Price(4).

**Midpoint execution reporting:**
- Midpoint peg orders do NOT generate Add Order messages on ITCH
- Against displayed order: Type C (Executed with Price) contains sub-penny midpoint price
- Two non-displayed match: Type P (Trade Non-Cross) reports match price
- Both use Price(4), fully sub-penny capable to $0.0001

**Half-penny tick:** SEC Rule 612 amendment (Sep 2024) introduces $0.005 tick for liquid stocks, effective Nov 2025 (delayed to Nov 2026). Midpoint between half-penny levels (e.g., $100.0025 = integer 1,000,025) already representable in Price(4).

| Message | Price Field | Bytes | Sub-Penny | Notes |
|---------|-------------|-------|-----------|-------|
| A/F (Add) | Price | 4 | Yes (displayed at penny) | Rule 612 constrains displayed |
| E (Executed) | — | — | N/A | Uses original Add price |
| C (Exec w/ Price) | Execution Price | 4 | **Yes** | Midpoint/non-display |
| U (Replace) | Price | 4 | Yes | New price |
| P (Trade) | Price | 4 | **Yes** | Non-displayable matches |
| Q (Cross) | Cross Price | 4 | Typically penny | Auction clearing |
| I (NOII) | Near/Far/Ref | 4 each | Yes | Indicative |
| V (MWCB) | Levels | **8 each** | Yes | Only Price(8) in ITCH 5.0 |
| J (LULD) | Ref/Upper/Lower | 4 each | Yes | Collar prices |

### Timestamp Encoding

6-byte timestamp:
- Nanoseconds since midnight Eastern Time
- Reset at market open
- ~281 trillion max value

### Stock Locate

2-byte integer mapping symbol to locate code:
- Assigned daily via Stock Directory message
- Use for efficient symbol lookup
- Not persistent across days

## Book Reconstruction

### Algorithm

```
For each message in sequence:
  1. Parse message type
  2. Lookup stock locate
  3. Apply to order book:
     - A/F: Insert new order
     - E/C: Reduce order size
     - X: Reduce order size
     - D: Remove order
     - U: Remove old, insert new
  4. Update BBO if affected
```

### State Management

Maintain:
- Order map: reference number -> order details
- Book per symbol: price levels with queued orders
- Locate map: stock locate -> symbol

### Edge Cases

**Order replace (U):**
- Contains both old and new reference numbers
- Old order is removed, new order is inserted atomically
- May change price, size, or both
- **Gotcha:** If you miss the U message, you have orphaned old order AND missing new order

**Executed with price (C) vs regular execute (E):**
- Type E: Execution at order's limit price
- Type C: Execution at different price (e.g., midpoint, auction, hidden order)
- **Critical:** Use C's execution price, not the order's original limit price
- **Gotcha:** Failing to distinguish corrupts trade analytics and P&L

**Broken trade (B):**
- Trade was erroneous (clearly erroneous execution)
- Contains match number of broken trade
- **Recovery:** Remove trade from analytics, but do NOT restore order to book
- The order was already reduced/removed at execution time

**Cross trade (Q) attribution:**
- Type Q has no order reference number
- Cannot directly attribute auction volume to specific orders
- **Workaround:** Infer from orders marked for auction participation

**Out-of-order message delivery:**
- MoldUDP is unreliable; packets can arrive out of order
- Must buffer and reorder by sequence number before processing
- **Critical:** Processing out-of-order corrupts book state

**Phantom orders (execute before add):**
- If gap contains Add message, you may see Execute for unknown order
- Must handle gracefully: log warning, skip execution
- After gap recovery, replay will provide the Add

**Order reference number overflow:**
- 8-byte integer; theoretical wraparound at ~18 quintillion
- In practice, never wraps within a day
- Numbers reset each trading day

### Corporate Action Handling

ITCH order books are **stateless across days** — all orders cancelled overnight, reference numbers day-unique, Stock Locates assigned daily.

**Forward splits:** Invisible in ITCH. No split message exists. New Type R with post-split data at day start; all prior orders already cancelled. Stock opens via normal Opening Cross. Example: AAPL 4:1 (Aug 28, 2020) — fresh Stock Directory, new orders at ~$127 vs prior ~$500.

**Reverse splits:** Mandatory halt since Nov 2023 (Rule 4120(a)(14)).
1. Day before: Type H halt (M1 Corporate Action) ~7:50 PM
2. Effective date: Type R (post-split) → halted → NOII (Cross Type "H") → Quotation (State "Q") → Trading (State "T") at 9:00 AM → Cross Trade (Type Q)
- CUSIP changes (visible in Daily List, not ITCH)
- All orders cancelled per FINRA Rule 5330(b)

**Symbol changes:** No ITCH cross-reference. Old symbol absent from Type R; new symbol appears. Use Nasdaq Daily List for mapping. ITCH carries no CUSIP/ISIN (unlike Nasdaq Nordic ITCH which includes ISIN).

**IPOs:** Type K (IPO Quoting Period) → halt reason IPO1 → quotation-only (IPOQ) → NOII → Cross Type "H" (not "O"). Can occur any time during day.

**Spin-offs:** Zero ITCH indication. New entity appears as fresh Type R on first trading day. Parent ex-date price drop unexplained in protocol.

| Action | ITCH Messages | Orders | Detection |
|--------|--------------|--------|-----------|
| Forward split | Type R (new day) | Cancelled overnight | Daily List for ratios |
| Reverse split | Type H (M1), R, I, Q, H (resume) | Cancelled 8 PM; halt 7:50 PM; resume 9 AM | CUSIP change via Daily List |
| Symbol change | Type R (new symbol) | Old dead; new fresh | Daily List for mapping |
| IPO | Type R (IPO=Y), H (IPO1), K, I, Q | Accepted during quotation-only | Type K IPO Price |
| Spin-off | Type R (new entity) | Standard overnight cancel | No ITCH link; use Daily List + CRSP |

**LOBSTER:** Event Type 7 for halts (Price=-1 halt, 0 quote resume, 1 trade resume). No halt reason code. Unadjusted raw prices. Data from Jan 6, 2009.

### Timestamp Edge Cases

**Midnight rollover:**
- Timestamp is nanoseconds since midnight ET
- Pre-market starts 4:00 AM ET (after midnight reset)
- No rollover issue within single trading day

**Daylight Saving Time:**
- Spring forward: 2:00 AM -> 3:00 AM (gap)
- Fall back: 2:00 AM -> 1:00 AM (overlap)
- Nasdaq uses ET throughout; adjust if storing in UTC

**Early close days:**
- Market closes 1:00 PM ET (not 4:00 PM)
- Closing cross at 1:00 PM
- Check holiday calendar

## Gap Detection and Recovery

### Sequence Numbers

MoldUDP64 provides:
- Session identifier
- Sequence number per message
- Messages numbered sequentially

### Gap Detection

If sequence number jumps:
1. Note gap range (first missing, last missing)
2. Continue processing new messages (don't block)
3. Mark affected symbols as "dirty" (untrusted)
4. Request retransmission or snapshot
5. After recovery, mark symbols clean only when gap filled

**Gap severity classification:**

| Gap Size | Impact | Recovery Strategy |
|----------|--------|-------------------|
| 1-100 messages | Minor | Retransmission |
| 100-10000 messages | Moderate | Retransmission or snapshot |
| 10000+ messages | Severe | Snapshot required |
| Multi-second gap | Critical | Full snapshot + audit |

### Recovery Options

**MoldUDP64 retransmission:**
- Request specific sequence range from retransmission server
- Fast for small gaps
- Max retransmission window: typically ~60 seconds of messages
- **Gotcha:** Retransmission server may not have very old messages

**SoupBinTCP replay:**
- Connect to replay server with session and sequence
- Reliable but higher latency
- Can request from any sequence number
- Full session replay available

**Snapshot:**
- Full book snapshot at point in time
- Reconcile with event stream at snapshot sequence
- Required for large gaps or cold start
- Nasdaq provides daily snapshots

### Recovery Validation

After gap recovery, validate book state:

```
1. Replay missed messages in sequence
2. Reconcile order counts with expected
3. Validate BBO against SIP
4. Check for orphaned orders (executes without adds)
5. Verify no negative quantities
6. Mark symbol clean only after all checks pass
```

**When is book trustworthy again?**
- All gap messages received AND processed
- No orphaned order references
- BBO matches external reference (SIP or other feed)
- No pending retransmission requests

## Performance Considerations

### Parsing Optimization

- Pre-allocate buffers
- Use lookup tables for message lengths
- Avoid string operations
- Memory-map where possible

### Latency Targets

| Environment | Target |
|-------------|--------|
| Co-located | < 10 microseconds |
| Remote | < 100 microseconds |

### Throughput

Peak message rates:
- Normal: 1-5 million/second
- Peak: 10+ million/second
- Size: 30-50 bytes average

## Implementation Checklist

1. [ ] Parse all message types
2. [ ] Handle stock locate mapping
3. [ ] Implement timestamp conversion
4. [ ] Build order book structure
5. [ ] Process add/execute/cancel/delete/replace
6. [ ] Handle NOII for auctions
7. [ ] Implement gap detection
8. [ ] Build recovery mechanism
9. [ ] Validate with known prints
10. [ ] Performance test at peak rates

## Validation Checklist Reference

Full 45-check validation architecture documented in `../../equity_amer.md` § Data Validation Checklist.

**Key checks for ITCH implementors:**

| Priority | Check | Severity |
|----------|-------|----------|
| 1 | Session ID constant for entire day | Critical |
| 2 | Sequence number strict monotonic, no gaps/duplicates | Critical |
| 3 | Timestamp non-decreasing (>1ms regression = corruption) | Critical |
| 4 | Every E/C/X/D/U references valid active Order Ref from prior A/F | Critical |
| 5 | No negative remaining quantities | Critical |
| 6 | No crossed book during continuous trading (State "T") | Critical |
| 7 | System Event ordering: O→S→Q→M→E→C exactly once each | Critical |
| 8 | Stock Directory complete before first trade | Critical |
| 9 | Order NOT restored after Type B (broken trade) | Critical |
| 10 | Gap retransmission verified before further processing | Critical |

**Processing order:** Transport → Timestamp → Reference Data → State Machine → Order Lifecycle → Auction → Trade Breaks → Volume → Corporate Actions → Best Practices.

Severity distribution: 13 Critical, 19 High, 13 Medium.

## Official Resources

- **Spec PDF:** https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHSpecification.pdf
- **Cloud overview:** https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/Totalview-ITCH-cloud.pdf
- **Sample data:** Available via Nasdaq

## Open Source Implementations

Reference implementations exist in:
- Python (github.com/bbalouki/itch)
- C++ (various)
- Rust (various)

Use for learning; production needs optimization.
