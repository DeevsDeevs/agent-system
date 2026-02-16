# ITCH Protocol Specification

Nasdaq TotalView-ITCH 5.0 - binary protocol for disseminating full depth-of-book market data.

## Overview

ITCH is a high-performance, low-latency protocol for market data dissemination. Provides:
- Full order book depth
- Order-level event stream
- Auction imbalance data
- System and stock reference data

**Official specification:** https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHSpecification.pdf

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
