# Nasdaq TotalView

Premium full depth-of-book product. Uses ITCH 5.0 protocol (see [[equity/amer/nasdaq/references/specs/itch_protocol.md|itch_protocol.md]]).

## Product Tiers

| Tier | Content |
|------|---------|
| TotalView-ITCH | Full depth, all orders, all levels, NOII |
| Nasdaq Level 2 | Aggregated depth, no order-level detail |
| Nasdaq Basic | Top-of-book only |

## NOII Dissemination Schedule

| Cross | Start | End | Frequency |
|-------|-------|-----|-----------|
| Opening | 9:25 | 9:30 | Every 5 sec (to 9:28), 1 sec (9:28-9:30) |
| Closing | 3:50 | 4:00 | Every 1 second |
| Halt | Halt start | Reopen | Every 1 second |

## Delivery

| Method | Latency | Use Case |
|--------|---------|----------|
| Direct (Carteret, NJ co-lo) | ~10-50 μs | MoldUDP64 multicast |
| SoupBinTCP | Higher | Recovery, replay |
| Nasdaq Cloud | ms-range | Lower infrastructure cost |

## Capacity Planning

| Metric | Normal | Peak |
|--------|--------|------|
| Bandwidth | 50-200 Mbps | 1+ Gbps burst |
| Message rate | 1-5M msg/sec | 10+ M msg/sec |

## Cross-Venue Comparison

| Feature | TotalView | NYSE ArcaBook | Cboe Depth |
|---------|-----------|---------------|------------|
| Protocol | ITCH 5.0 | XDP | Cboe proprietary |
| Coverage | Nasdaq | NYSE Arca | Cboe exchanges |
| Auctions | NOII | Auction imbalance | Limited |
| Attribution | Partial (Type F) | No | No |
