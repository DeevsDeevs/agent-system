# Nasdaq TotalView

Nasdaq's premium market data product providing full depth-of-book visibility.

## Overview

TotalView provides:
- Complete order book depth (all price levels)
- Order-level event stream
- Auction imbalance indicators (NOII)
- Real-time updates via ITCH protocol

**Product page:** https://www.nasdaqtrader.com/Trader.aspx?id=TotalView

## Product Tiers

### TotalView-ITCH

Full depth-of-book for Nasdaq:
- All orders at all price levels
- Order add/modify/cancel/execute events
- Opening, closing, halt cross data
- NOII (Net Order Imbalance Indicator)

**Coverage:** Nasdaq Stock Market only

### Nasdaq Basic

Entry-level product:
- Top-of-book quotes
- Last sale
- No depth

**Use case:** Basic displays, compliance

### Nasdaq Level 2

Intermediate depth:
- Aggregated book depth
- No order-level detail
- Lower cost than TotalView

## Data Content

### Order Book Data

| Data Element | Availability |
|--------------|--------------|
| Full depth (all levels) | Yes |
| Individual order details | Yes |
| Order reference numbers | Yes |
| Market participant IDs | Attributed orders |
| Hidden order size | No (by definition) |

### Auction Data

| Data Element | Availability |
|--------------|--------------|
| NOII (imbalance indicator) | Yes |
| Paired shares | Yes |
| Imbalance size/direction | Yes |
| Indicative prices (near/far) | Yes |
| Cross trade results | Yes |

### Administrative Data

| Data Element | Availability |
|--------------|--------------|
| Stock directory | Yes |
| Trading action (halt/resume) | Yes |
| Reg SHO restriction | Yes |
| LULD price bands | Yes |
| IPO release time | Yes |

## NOII Details

Net Order Imbalance Indicator disseminated for:
- Opening Cross (9:25-9:30 AM ET)
- Closing Cross (3:50-4:00 PM ET)
- Halt Cross (during halt)
- IPO Cross

### NOII Fields

| Field | Description |
|-------|-------------|
| Paired Shares | Shares that can be matched |
| Imbalance Shares | Unmatched shares |
| Imbalance Direction | Buy (B), Sell (S), None (N), No Imbalance (O) |
| Current Reference Price | Inside midpoint |
| Near Indicative Price | Max paired shares price |
| Far Indicative Price | With imbalance consideration |
| Cross Type | Opening (O), Closing (C), Halt (H), IPO (I) |

### Dissemination Schedule

| Cross | Start | End | Frequency |
|-------|-------|-----|-----------|
| Opening | 9:25 | 9:30 | Every 5 sec (to 9:28), 1 sec (9:28-9:30) |
| Closing | 3:50 | 4:00 | Every 1 second |
| Halt | Halt start | Reopen | Every 1 second |

## Delivery Methods

### Direct Connect

- Co-location at Carteret, NJ
- MoldUDP64 multicast
- Lowest latency (~10-50 microseconds)
- Highest cost

### Nasdaq Cloud Data Service

- Cloud delivery
- Multiple cloud providers
- Higher latency (milliseconds)
- Lower infrastructure cost

### Redistributors

Third-party vendors:
- Bloomberg
- Refinitiv
- ICE
- Various specialists

Variable latency, bundled services.

## Technical Specifications

### Protocol

ITCH 5.0 (see `itch_protocol.md` for details)

### Transport

| Method | Use Case |
|--------|----------|
| MoldUDP64 | Primary multicast |
| SoupBinTCP | Recovery, replay |
| Nasdaq Cloud | Cloud delivery |

### Bandwidth Requirements

| Scenario | Bandwidth |
|----------|-----------|
| Normal | 50-200 Mbps |
| Peak | 500+ Mbps |
| Burst | 1+ Gbps |

### Message Rates

| Period | Rate |
|--------|------|
| Average | 1-5 million msg/sec |
| Peak | 10+ million msg/sec |
| Opening/closing | Higher concentration |

## Use Cases

### Quantitative Trading

- Full book reconstruction
- Queue position modeling
- Order flow analysis
- Market making signals

### Execution Algorithms

- Real-time book state
- Liquidity detection
- Smart order routing input
- Execution quality monitoring

### Research

- Historical book analysis
- Microstructure research
- Auction dynamics study
- Market quality analysis

### Surveillance

- Manipulation detection
- Spoofing/layering detection
- Best execution monitoring
- Trade reconstruction

## Comparison with Competitors

| Feature | TotalView | NYSE ArcaBook | Cboe Depth |
|---------|-----------|---------------|------------|
| Protocol | ITCH | Pillar | Cboe proprietary |
| Coverage | Nasdaq | NYSE Arca | Cboe exchanges |
| Auctions | NOII | Auction imbalance | Limited |
| Attribution | Partial | No | No |

## Historical Data

### Nasdaq Data Store

Historical TotalView data available:
- ITCH files by date
- Full day reconstruction
- Research licensing

### Academic Access

University programs may have access through:
- WRDS (Wharton Research Data Services)
- TAQ (Trades and Quotes)
- Direct academic licensing

## Pricing

Pricing varies by:
- Usage type (display, non-display, derived data)
- Distribution (internal, external)
- Geographic scope
- Platform (professional, non-professional)

Contact Nasdaq for current pricing.

## Getting Started

### Certification

1. Obtain Nasdaq connectivity
2. Develop feed handler
3. Complete Nasdaq certification
4. Production go-live

### Development Resources

- ITCH specification PDF
- Sample data files
- Test environment access
- Technical support

### Support

- Technical: Nasdaq Global Data Services
- Sales: Nasdaq sales team
- Email: dataservices@nasdaq.com

## Official Resources

- **TotalView overview:** https://www.nasdaqtrader.com/Trader.aspx?id=TotalView
- **ITCH specification:** https://www.nasdaqtrader.com/content/technicalsupport/specifications/dataproducts/NQTVITCHSpecification.pdf
- **Auction/Cross resources:** https://www.nasdaqtrader.com/Trader.aspx?id=AuctionCrosses
- **Nasdaq Trader portal:** https://www.nasdaqtrader.com/
