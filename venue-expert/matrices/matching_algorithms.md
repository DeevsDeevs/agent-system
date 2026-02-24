# Matching Algorithms — Cross-Venue Matrix

## Main Matrix

| Venue | Product | Default Algo | Spread Algo | Options Algo | Modify: Qty Down | Modify: Qty Up/Price |
|-------|---------|-------------|-------------|-------------|-------------------|---------------------|
| CME | ES (E-mini S&P) | FIFO (F) | FIFO (F) | FIFO (F) | Retain | Lose |
| CME | NQ (E-mini Nasdaq) | FIFO (F) | FIFO (F) | FIFO (F) | Retain | Lose |
| CME | CL (WTI Crude) | FIFO (F) | FIFO (F) | Threshold (Q) or FIFO | Retain | Lose |
| CME | GC (Gold) | FIFO (F) | FIFO (F) | Threshold (Q) or FIFO | Retain | Lose |
| CME | ZN (10Y T-Note) | FIFO (F) | Configurable (20/80) | Threshold + LMM (Q) | Retain | Lose |
| CME | ZB (Treasury Bond) | FIFO (F) | Configurable (K) | Threshold + LMM (Q) | Retain | Lose |
| CME | ZT (2Y T-Note) | Configurable (K) | Configurable (20/80) | Threshold + LMM (Q) | Retain | Lose |
| CME | ZC (Corn) | Configurable (40/60) | Configurable (40/60) | Threshold (O) | Retain | Lose |
| CME | SR3 (3M SOFR) | Allocation (A): TOP→PR→FIFO | FIFO (packs/bundles) | Threshold + LMM (Q) | Retain | Lose |
| CME | 6E (Euro FX) | FIFO (F) | Pro-Rata (C) | Threshold (Q) or (O) | Retain | Lose |
| ICE | B (Brent Crude) | Price-time (FIFO) | — | — | Retain | Lose |
| Eurex | FGBL/FESX/FDAX | Time (FIFO) | — | Time (FIFO, default) | Retain | Lose |
| Eurex | FEU3 (Euribor) | Pro-Rata | — | Pro-Rata (select) | — | — |
| SGX | FEF (Iron Ore) | Price-time | — | — | Retain (assumed) | Lose (assumed) |
| HKEX | Equities | Price-time | — | — | — | — |
| SHFE | All products (rb, cu, au, etc.) | Price-time (价格优先、时间优先) | — | — | N/A (no modify) | N/A (cancel-replace only; always lose) |
| DCE | All products (i, m, j, etc.) | Price-time | — | — | N/A (no modify) | N/A (cancel-replace only; always lose) |
| CZCE | All products (TA, MA, SR, etc.) | Price-time | — | — | N/A (no modify) | N/A (cancel-replace only; always lose) |
| CFFEX | All products (IF, IH, IC, IM, T) | Price-time | — | Closing call auction (options only, 14:57–15:00) | N/A (no modify) | N/A (cancel-replace only; always lose) |
| INE | All products (sc, lu, bc) | Price-time | — | — | N/A (no modify) | N/A (cancel-replace only; always lose) |
| GFEX | All products (SI, LC, PS, PT, PD) | Price-time | — | — | N/A (no modify) | N/A (cancel-replace only; always lose) |
| NYSE | Equities | Price-time + **parity allocation** (DMMs, floor brokers share at same price) | — | — | Retain | Lose |
| Nasdaq | Equities | Price-time (strict FIFO) | — | — | Retain | Lose |

## Call Auction Algorithms (Chinese Exchanges)

| Feature | SHFE/INE | DCE | CZCE | CFFEX | GFEX |
|---------|----------|-----|------|-------|------|
| Core algorithm | Maximum Volume Principle | Maximum Volume Principle | Maximum Volume Principle | Maximum Volume Principle | Maximum Volume Principle |
| Tie-breaking | Closest to prev settlement | Closest to prev settlement | Closest to prev settlement | Closest to prev settlement | Closest to prev settlement |
| Day auction for night products | Yes (since 2023/5) | Yes (since 2023/5) | **Cancel only** (no new matching) | N/A | Yes (since 2023/5) |
| Closing call auction | No | No | No | **Yes** (options only) | No |
| Market orders in auction | Not supported | Excluded | Excluded | Auto-cancelled | Excluded |

## LMM / DMM Allocation

| Venue | Market Maker Type | Allocation % | Applies To |
|-------|-------------------|-------------|------------|
| CME | LMM (Lead Market Maker) | <50% total (proprietary per product) | Options only (not futures) |
| NYSE | DMM (Designated Market Maker) | Parity allocation at same price | Listed equities |
| NYSE Arca | LMM | Enhanced allocation | ETFs |
| Eurex | Designated MM | Fee discounts, obligation-based | Select products |
| Chinese exchanges (all 6) | 做市商 (Market Maker) | Fee discounts, position limit exemption | Bilateral agreements; obligations not public |

## Per-Venue Details
- [[futures/amer/cme.md|cme.md]] §4 Matching Algorithms
- [[futures/emea/eurex.md|eurex.md]] §3 Matching Algorithms
- [[futures/emea/ice.md|ice.md]] §3 Order Book Mechanics
- [[equity/amer/nyse/nyse.md|nyse.md]] Parity Allocation Model
