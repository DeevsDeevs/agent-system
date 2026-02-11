# OUCH Protocol Specification

Nasdaq OUCH - binary protocol for order entry and execution reporting.

## Overview

OUCH allows Nasdaq participants to:
- Enter orders
- Replace orders
- Cancel orders
- Receive execution reports

Two versions in use:
- **OUCH 4.2** - Fixed-length messages (legacy)
- **OUCH 5.0** - Tag-based variable-length (current)

## OUCH 4.2

**Official specification:** https://www.nasdaqtrader.com/content/technicalsupport/specifications/TradingProducts/OUCH4.2.pdf

### Message Types

**Inbound (client to Nasdaq):**

| Type | Name | Description |
|------|------|-------------|
| O | Enter Order | New order submission |
| U | Replace Order | Modify existing order |
| X | Cancel Order | Cancel existing order |
| M | Modify Order | Modify order attributes |

**Outbound (Nasdaq to client):**

| Type | Name | Description |
|------|------|-------------|
| A | Accepted | Order accepted |
| U | Replaced | Order replaced |
| C | Canceled | Order canceled |
| D | AIQ Canceled | Atomically canceled |
| E | Executed | Partial/full execution |
| B | Broken Trade | Trade broken |
| J | Rejected | Order rejected |
| S | System Event | Market status |
| P | Priority Update | Priority changed |

### Enter Order Message (Type O)

| Field | Offset | Length | Description |
|-------|--------|--------|-------------|
| Type | 0 | 1 | 'O' |
| Order Token | 1 | 14 | Client order ID |
| Buy/Sell | 15 | 1 | 'B' or 'S' |
| Shares | 16 | 4 | Order quantity |
| Stock | 20 | 8 | Symbol |
| Price | 28 | 4 | Limit price |
| Time in Force | 32 | 4 | TIF code |
| Firm | 36 | 4 | Firm identifier |
| Display | 40 | 1 | Display instruction |
| Capacity | 41 | 1 | Agency/Principal |
| Intermarket Sweep | 42 | 1 | ISO flag |
| Minimum Quantity | 43 | 4 | Min fill size |
| Cross Type | 47 | 1 | Cross participation |
| Customer Type | 48 | 1 | Customer indicator |

### Order Token

- 14 alphanumeric characters
- Must be unique per day per OUCH port
- Used for all subsequent operations
- Client-assigned

### Time in Force Codes

| Code | Meaning |
|------|---------|
| 0 | Immediate or Cancel (IOC) |
| 99998 | Market hours only |
| 99999 | System hours |
| Other | Seconds after midnight |

### Display Instructions

| Code | Meaning |
|------|---------|
| Y | Displayed |
| N | Non-displayed |
| P | Post-only |
| I | Imbalance-only |
| M | Midpoint peg |
| O | Opening cross only |
| C | Closing cross only |
| H | Halt cross only |

### Accepted Message (Type A)

| Field | Offset | Length | Description |
|-------|--------|--------|-------------|
| Type | 0 | 1 | 'A' |
| Timestamp | 1 | 8 | Nasdaq timestamp |
| Order Token | 9 | 14 | Client order ID |
| Buy/Sell | 23 | 1 | Side |
| Shares | 24 | 4 | Accepted quantity |
| Stock | 28 | 8 | Symbol |
| Price | 36 | 4 | Accepted price |
| Time in Force | 40 | 4 | TIF |
| Firm | 44 | 4 | Firm ID |
| Display | 48 | 1 | Display |
| Order Reference | 49 | 8 | Nasdaq order ID |
| Capacity | 57 | 1 | Capacity |
| Intermarket Sweep | 58 | 1 | ISO flag |
| Minimum Quantity | 59 | 4 | Min qty |
| Cross Type | 63 | 1 | Cross type |
| Order State | 64 | 1 | State |
| BBO Weight | 65 | 1 | BBO indicator |

### Executed Message (Type E)

| Field | Offset | Length | Description |
|-------|--------|--------|-------------|
| Type | 0 | 1 | 'E' |
| Timestamp | 1 | 8 | Execution time |
| Order Token | 9 | 14 | Client order ID |
| Executed Shares | 23 | 4 | Fill quantity |
| Execution Price | 27 | 4 | Fill price |
| Liquidity Flag | 31 | 1 | Add/Remove |
| Match Number | 32 | 8 | Match ID |

### Liquidity Flags

| Flag | Meaning |
|------|---------|
| A | Added liquidity |
| R | Removed liquidity |
| X | Routed to another venue |
| O | Opening cross |
| C | Closing cross |
| H | Halt cross |

## OUCH 5.0

**Official specification:** https://nasdaqtrader.com/content/technicalsupport/specifications/TradingProducts/Ouch5.0.pdf

### Key Differences from 4.2

| Aspect | OUCH 4.2 | OUCH 5.0 |
|--------|----------|----------|
| Message format | Fixed-length | Tag-based (variable) |
| Order types | Basic | Extended (peg, discretion, reserve) |
| Field encoding | Position-based | Tag-value pairs |
| Extensibility | Limited | Easier to extend |

### Tag-Based Format

Messages use tag-length-value encoding:
```
[Tag (2 bytes)][Length (2 bytes)][Value (variable)]
```

### New Order Types in 5.0

- **Pegged orders** - Track midpoint, primary, market
- **Discretionary orders** - Hidden price improvement
- **Reserve orders** - Display size, hidden reserve
- **Retail orders** - Retail liquidity provider interaction

### Migration

Nasdaq encouraging migration to OUCH 5.0 for:
- Access to new order types
- Future feature support
- Streamlined message handling

## Transport Layer

### SoupBinTCP

TCP-based session protocol:

**Session establishment:**
1. Client connects to Nasdaq
2. Login message with credentials
3. Server accepts or rejects
4. Heartbeats maintain connection

**Message framing:**
- Length-prefixed messages
- Sequenced delivery
- Heartbeat/debug messages

### Port Assignment

Each firm gets:
- Unique OUCH port(s)
- Order token namespace per port
- Separate session credentials

## Order Lifecycle

### Typical Flow

```
Client                    Nasdaq
   |                         |
   |-- Enter Order (O) ----->|
   |                         |
   |<---- Accepted (A) ------|
   |                         |
   |<---- Executed (E) ------|  (partial fill)
   |                         |
   |<---- Executed (E) ------|  (remaining fill)
```

### Replace Flow

```
Client                    Nasdaq
   |                         |
   |-- Replace Order (U) --->|
   |                         |
   |<---- Replaced (U) ------|
```

Replace is atomic - old order removed, new order inserted.

### Cancel Flow

```
Client                    Nasdaq
   |                         |
   |-- Cancel Order (X) ---->|
   |                         |
   |<---- Canceled (C) ------|
```

Duplicate cancels are ignored.

## Error Handling

### Rejection Reasons

| Code | Reason |
|------|--------|
| T | Test mode |
| H | Halted |
| Z | Invalid symbol |
| N | Invalid minimum quantity |
| S | Invalid display type |
| D | Missing credentials |
| L | Invalid lot size |
| P | Invalid price |
| R | Risk check failed |

### Broken Trade

If execution is broken:
1. Receive Broken Trade (B) message
2. Match number identifies execution
3. Reverse any fill accounting
4. Order may remain open

## Implementation Notes

### Order Token Management

- Generate unique tokens per day
- Track all outstanding tokens
- Map token to order state
- Handle duplicate detection

### State Machine

Track order states:
- Pending (sent, not acked)
- Accepted (on book)
- Partially filled
- Fully filled
- Canceled
- Rejected

### Sequence Number Handling

- Track expected sequence
- Detect gaps
- Request replay if needed
- Handle session restarts

### Testing

**Nasdaq provides:**
- UAT environment
- Test symbols
- Certification process

## Latency Optimization

### Wire Protocol

- Minimize message size
- Pre-serialize where possible
- Batch where supported

### Session Management

- Persistent connections
- Quick reconnect
- Heartbeat tuning

### Co-location

- Carteret data center
- Cross-connects to matching engine
- Microsecond-level latency possible

## Official Resources

- **OUCH 4.2:** https://www.nasdaqtrader.com/content/technicalsupport/specifications/TradingProducts/OUCH4.2.pdf
- **OUCH 5.0:** https://nasdaqtrader.com/content/technicalsupport/specifications/TradingProducts/Ouch5.0.pdf
- **OUCH 5.0 FAQ:** https://nasdaqtrader.com/content/productsservices/trading/OUCH_5.0_FAQ.pdf
- **Portal:** https://www.nasdaqtrader.com/Trader.aspx?id=OUCH

## Support

Technical questions: tradingservices@nasdaq.com

Updates announced via:
- Nasdaq Head Trader Alerts
- Technical Updates
