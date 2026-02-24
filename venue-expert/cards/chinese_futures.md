# Chinese Futures Markets — Quick Reference Card

## Exchanges

| Exchange | Code | Products | Night Session | Fee Model | Matching | CTP ExchangeID |
|----------|------|----------|---------------|-----------|----------|----------------|
| SHFE | 上海期货交易所 | Metals, energy, rubber (~20) | Yes (21:00–02:30 max) | Mixed (per-lot + per-turnover) | Price-time | SHFE |
| DCE | 大连商品交易所 | Ferrous, agricultural, chemicals (~20) | Yes (21:00–23:00) | Mixed (per-lot + per-turnover) | Price-time | DCE |
| CZCE | 郑州商品交易所 | Agricultural, chemicals (~20) | Yes (21:00–23:00) | Mixed (per-lot + per-turnover) | Price-time | CZCE |
| CFFEX | 中国金融期货交易所 | Index futures, treasury bonds (~8) | No | Per-turnover | Price-time | CFFEX |
| INE | 上海国际能源交易中心 | Internationalized products (~5) | Yes (21:00–02:30 max) | Mixed | Price-time | INE |
| GFEX | 广州期货交易所 | Silicon, lithium, platinum, palladium (5) | No | Per-turnover only | Price-time | GFEX |

## Key Parameters

| Parameter | Value |
|-----------|-------|
| CTP snapshot frequency | 500ms (2 snapshots/sec); L2 at 250ms for SHFE/DCE/CZCE |
| Standard depth levels | 1 (CTP TCP); 5 (L2 paid/co-lo) |
| Tick conventions | Per-product: 1 CNY/ton (rb), 10 CNY/ton (cu), 0.02 CNY/g (au), 0.5 CNY/ton (i) |
| Lot conventions | Per-product: 10 tons/lot (rb), 5 tons/lot (cu), 1000g/lot (au), 100 tons/lot (i) |
| Price limits | ±4–6% of previous settlement (exchange/product-dependent) |
| Position limit framework | Three-phase: general month → pre-delivery → delivery month; tightens near expiry |
| Mandatory open/close flags | All exchanges require Open/Close specification on every order |
| CloseToday/CloseYesterday | SHFE/INE only; must specify 平今(3) vs 平昨(4). DCE/CZCE/CFFEX/GFEX use FIFO |
| Invalid value sentinel | DBL_MAX (1.7976931348623157e+308), not zero |
| Contract code format | SHFE/DCE/INE/GFEX: lowercase+YYMM; CFFEX: UPPERCASE+YYMM; CZCE: UPPERCASE+YMM (3-digit) |
| Order modification | Not supported; cancel-replace only (loses queue priority) |

## Session Schedule (Beijing Time)

| Session | Hours | Exchanges |
|---------|-------|-----------|
| Night call auction | 20:55–21:00 | SHFE, INE, DCE, CZCE |
| Night continuous (tier 1) | 21:00–23:00 | Most night products (rb, i, m, TA, SR, all DCE/CZCE night) |
| Night continuous (tier 2) | 21:00–01:00 | Base metals (cu, al, zn, pb, ni, sn, ss, bc) |
| Night continuous (tier 3) | 21:00–02:30 | Precious metals (au, ag), crude oil (sc) |
| Day call auction | 08:55–09:00 (CFFEX: 09:25–09:30) | All exchanges |
| Morning session 1 | 09:00–10:15 | All |
| Break | 10:15–10:30 | All commodity exchanges |
| Morning session 2 | 10:30–11:30 | All |
| Lunch | 11:30–13:30 | All |
| Afternoon session | 13:30–15:00 (CFFEX: 15:00/15:15) | All |

## Data Feed

| Feed | Type | Latency | Content |
|------|------|---------|---------|
| CTP standard (TCP) | Snapshot | ~500ms intervals | 1-level depth, last price, OHLC, volume, OI |
| CTP multicast (co-lo) | Snapshot | 250ms (SHFE/INE) | 5-level depth |
| Exchange direct (DCE 飞创, CZCE 易盛) | Snapshot | 250ms | 5-level depth, exchange-specific API |
| Exchange matching engine | Continuous | ~500μs order-to-ack | Not externally accessible; 500ms snapshot is deliberate downsampling |

## Fee Models

| Type | Description | Exchanges |
|------|-------------|-----------|
| Per-lot (元/手) | Fixed fee per contract traded | SHFE (au, al, zn, ru), DCE (m, y, c), CZCE (TA, SR, CF) |
| Per-turnover (万分之X) | Percentage of trade value | SHFE (rb, cu, ag), DCE (i, j, jm), CZCE (SA), CFFEX (all), INE (sc, bc), GFEX (all) |
| Intraday close surcharge (平今) | Elevated close-today fee on select products | CFFEX IF/IH/IC/IM: 万分之2.3 (10× open); SHFE ag: up to 5× |
| 申报费 (order submission fee) | Tiered by order-to-trade ratio; since May 2024 | All exchanges |

## Spread by Product

| Product | Exchange | Tick | Median Spread (ticks) | Half-Spread (bps) |
|---------|----------|------|-----------------------|-------------------|
| rb (rebar) | SHFE | 1 CNY/ton | 1 | ~1.4 |
| cu (copper) | SHFE | 10 CNY/ton | 1 | ~0.7 |
| al (aluminum) | SHFE | 5 CNY/ton | 1 | ~1.2 |
| au (gold) | SHFE | 0.02 CNY/g | 1–2 | ~0.2–0.3 |
| i (iron ore) | DCE | 0.5 CNY/ton | 1–2 | ~3–6 |
| m (soybean meal) | DCE | 1 CNY/ton | 1 | ~1.6 |
| p (palm oil) | DCE | 2 CNY/ton | 1 | ~1.2 |
| TA (PTA) | CZCE | 2 CNY/ton | 1 | ~1.8 |
| IF (CSI 300) | CFFEX | 0.2 pts | 1–3 | ~0.3–0.8 |
| sc (crude oil) | INE | 0.1 CNY/bbl | 1–2 | ~0.9–1.8 |

## Regulatory Timeline

| Date | Event | Impact |
|------|-------|--------|
| 2013-07-05 | First night session (SHFE: au, ag) | Structural break in intraday vol patterns |
| 2015-09-07 | CFFEX maximum restrictions (10 lots/day, 40% margin, 万分之23 平今) | Index futures market effectively frozen |
| 2016-01-04 | Circuit breaker triggered (5% and 7% CSI300); suspended Jan 8 | 4 days total; magnet effect observed |
| 2018-03-26 | INE crude oil (sc) launches — first internationalized product | Foreign access via overseas intermediary |
| 2019-04-22 | CFFEX 4th relaxation (500 lots/day, 万分之3.45 平今) | Most impactful easing — 10× daily limit increase |
| 2019-06-14 | 看穿式监管 enforced (CTP ≥6.3.15, AppID/AuthCode mandatory) | VM/cloud environments fail; physical machine required |
| 2020-09-08 | CTP v6.5.1: InstrumentID char[31]→char[81] | Binary-breaking struct change; recompilation mandatory |
| 2022-08-01 | Futures and Derivatives Law effective | Registration-based listing → accelerated product launches |
| 2022-09-02 | QFI access launched: 41 products opened to foreign investors | New participant type in order flow |
| 2022-12-22 | GFEX launches (Industrial Silicon SI) | 6th exchange operational |
| 2023-03-20 | CFFEX 平今 fee reduced to 万分之2.3 | Latest fee change for index futures |
| 2024-09-30 | State Council 国办发47号: HFT fee rebates cancelled, mandatory algo reporting | Most consequential regime change for quant firms since 2015 |
| 2025-10-09 | CSRC Programmatic Trading Management Rules effective | ≥5 orders within 1 second ×5 instances = programme trading |
| 2025 Q1 | QFI expansion to ~91+ products; GFEX products included | First GFEX foreign access |

## Co-Location Map

| DC | Exchanges | Location |
|----|-----------|----------|
| Shanghai Zhangjiang | SHFE, INE | SHFE data center (CTP multicast co-lo) |
| Dalian | DCE | DCE co-lo (飞创 DFIT L2 feed) |
| Zhengzhou | CZCE | CZCE co-lo (易盛 Esunny L2 feed) |
| Shanghai | CFFEX | CFFEX co-lo |
| Guangzhou | GFEX | GFEX co-lo |

## Deep Docs
- [[futures/apac/china/futures_china.md|futures_china.md]]
- [[futures/apac/china/shfe.md|shfe.md]]
- [[futures/apac/china/dce.md|dce.md]]
- [[futures/apac/china/czce.md|czce.md]]
- [[futures/apac/china/cffex.md|cffex.md]]
- [[futures/apac/china/ine.md|ine.md]]
- [[futures/apac/china/gfex.md|gfex.md]]
