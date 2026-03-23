# GFEX - Guangzhou Futures Exchange (广州期货交易所)

China's 6th futures exchange, first mixed-ownership (混合所有制). Green development focus (绿色发展), serving Greater Bay Area (粤港澳大湾区). Assumes familiarity with `futures_china.md`.

## 1. Identity & Products

| Attribute | Value |
|-----------|-------|
| Timezone | **CST (UTC+8)** |
| Focus | Green/strategic materials |
| Night session | **No** |
| Ownership | Mixed (混合所有制) — HKEX stake |
| Established | **2021-04-19** |
| CTP close direction | Generic Close (不区分平今/平昨) |

### Products

| Code | Product | Unit | Tick Size | Margin | Night | Launch |
|------|---------|------|-----------|--------|-------|--------|
| SI | Industrial Silicon (工业硅) | 5 t/lot | 5 CNY/ton | 10% spec / 9% hedge | No | 2022-12-22 |
| LC | Lithium Carbonate (碳酸锂) | 1 t/lot | 20 CNY/ton | ~8-12% (varies) | No | 2023-07-21 |
| PS | Polysilicon (多晶硅) | 3 t/lot | 5 CNY/ton | 15% | No | 2024-12-26 |
| PT | Platinum (铂) | 1000 g/lot | 0.05 CNY/g | 22% (elevated) | No | 2025-11-27 |
| PD | Palladium (钯) | 1000 g/lot | 0.05 CNY/g | 22% (elevated) | No | 2025-11-27 |

All products have corresponding **American-style options**. LC designated as **境内特定品种** (specified domestic product) on January 26, 2026 -- open to overseas traders. Pipeline: **carbon emission futures** (碳排放期货), lithium hydroxide (氢氧化锂).


## 2. Data Characteristics

| Field | Behavior |
|-------|----------|
| L2 availability | Since 2022 launch |
| L2 update rate | **~250ms** (estimated) |
| L2 depth | 5 levels |
| L2 cost | **Paid** (~600 CNY/yr) |
| L1 (CTP) | Standard 500ms snapshots |
| Contract format | Lowercase + YYMM (e.g., `si2501`) |
| DBL_MAX sentinel | Fields not yet populated use `DBL_MAX` (~1.7976e+308) |

CTP timestamp provenance identical to other exchanges -- exchange-generated, CTP passthrough. UpdateMillisec behavior not independently characterized due to short operating history; likely follows SHFE/CFFEX binary pattern (0/500) given shared CTP infrastructure.


## 3. Data Validation Checklist

| Check | Rule | Failure indicates |
|-------|------|-------------------|
| DBL_MAX sentinel | Filter fields ~1.7976e+308 | Field not yet populated for session |
| CTP close direction | Generic Close -- position tracking must account | SHFE/INE logic will mismatch |
| No night session | TradingDay always equals ActionDay | Night-session date anomalies N/A |
| Contract code | Lowercase letters + 4-digit YYMM | Wrong exchange or format error |
| Price vs tick | `(price - basePrice) % tickSize == 0` | Off-tick price, data corruption |
| Margin parameters | Cross-check against exchange notices frequently | Parameters change multiple times/month |

No night session simplifies TradingDay logic -- no ActionDay/TradingDay divergence to handle.

## 4. Order Book Mechanics

### Call Auction Schedule

| Session | Time | Behavior |
|---------|------|----------|
| Opening auction | **08:55-09:00** | Full call auction (same as commodity exchanges) |
| Night opening | **N/A** | No night session |
| Closing auction | **None** | No closing call auction |

Price-time priority. Maximum Volume Principle (最大成交量原则) for auction price determination -- identical algorithm to all other Chinese futures exchanges. Market orders excluded from auction.


### Close Position Handling

**Generic Close** (不区分平今/平昨) -- same as DCE, CZCE, CFFEX. Unlike SHFE/INE, GFEX accepts `THOST_FTDC_OF_Close` for all closing regardless of position vintage. CTP reports all closes as generic Close in OnRtnTrade regardless of what was specified. Position tracking systems designed for SHFE/INE must adapt.

### Order Types

All orders are limit orders. FOK (Fill-or-Kill) and FAK (Fill-and-Kill / IOC) supported. No native order modification -- cancel + reinsert required.

## 5. Transaction Costs

### Fee Structure

All GFEX fees are **per-turnover** (按成交额/万分之X) -- unlike SHFE/INE which use primarily per-lot.

| Code | Product | Open/Close | Close-Today | Notes |
|------|---------|-----------|-------------|-------|
| SI | Industrial Silicon | 万分之一 (0.01%) | **Free** (general months) | Close-today free for non-delivery months |
| LC | Lithium Carbonate | 万分之三点二 (0.032%) | Same rate | No close-today discount |
| PS | Polysilicon | 万分之五 (0.05%) | Varies | Higher rate reflecting newer product |

Per-turnover fees scale with price level. During LC's extreme volatility periods, absolute fee costs varied significantly despite constant percentage rate.


## 6. Position Limits & Margin

### Daily Opening Limits

GFEX uses **tight daily opening limits** (单日开仓量限制) as primary anti-speculation tool -- notably more aggressive than other exchanges.

| Product | General Month Position Limit | Daily Opening Limit (Speculative) | Notes |
|---------|----------------------------|----------------------------------|-------|
| SI | 30,000 lots | 2,000-5,000 lots/day | — |
| LC | Similar scale | **400 lots/day** | Extremely tight for an actively traded contract |
| PS | — | 50-500 lots/day | Minimum opening: **10 lots** |

Limits adjusted **frequently** -- sometimes weekly during volatile periods. Hedging and market making exempt. PS requires **10 lots minimum opening** -- rare among Chinese exchanges.

### Margin Rates

| Product | Current Effective | Note |
|---------|-------------------|------|
| SI | 10% spec / 9% hedge | Standard |
| LC | 8-12% | Varies frequently |
| PS | 15% | Higher for newer product |
| PT | **22%** | Elevated -- high uncertainty, new product |
| PD | **22%** | Elevated -- high uncertainty, new product |

Delivery month margin escalation follows commodity exchange standard pattern. Holiday escalation applies (+5-10% before Spring Festival). Typical broker margins add 3-5% above exchange rates.


## 7. Regulatory Framework

### Ownership Structure

| Shareholder | Stake |
|-------------|-------|
| SHFE | 15% |
| DCE | 15% |
| CZCE | 15% |
| CFFEX | 15% |
| Ping An Insurance | Minority |
| Guangzhou Financial Holdings | Minority |
| Guangdong Pearl River Investment | Minority |
| **HKEX** | Minority |

HKEX is the **only non-mainland shareholder** of any Chinese futures exchange. Under CSRC supervision with same regulatory framework as other exchanges.

### Abnormal Trading Thresholds

Same framework as other commodity exchanges. Specific thresholds published in GFEX trading rules. Frequent quote/cancel by designated market makers exempt.

### Programme Trading

Subject to CSRC Programmatic Trading Management Rules (effective Oct 9, 2025). Same mandatory registration/reporting requirements as all other exchanges.


## 8. Regime Change Database

| Date | Event | Impact |
|------|-------|--------|
| **2021-04-19** | GFEX established | 6th Chinese futures exchange created |
| **2022-12-22** | SI (Industrial Silicon) + options launch | GFEX becomes operational; new data feed required |
| **2023-07-21** | LC (Lithium Carbonate) launch | Global first physically-delivered lithium futures; extreme volatility |
| **2024-07** | LC options launch | Options chain added |
| **2024-12-26** | PS (Polysilicon) + options launch | 3rd GFEX product; no night session |
| **2025-01** | QFI access | First GFEX products opened to foreign investors |
| **2025-11-27** | PT/PD (Platinum/Palladium) launch | Industrial-form delivery (sponge/powder) -- global first |
| **2026-01-26** | LC designated 境内特定品种 | Overseas trader access via QFI/QFII |
| Pipeline | Carbon emission futures (碳排放期货) | Under development; not yet launched |


## 9. Failure Modes & Gotchas

| Issue | Detail |
|-------|--------|
| No night session | No overnight gap management from Asian sessions; miss moves in correlated international markets |
| Parameter change frequency | **Extremely high** -- margins/fees/limits adjusted multiple times per month |
| Daily opening limits | LC at 400 lots/day can block strategy scaling; PS at 50-500 lots/day |
| Generic close direction | Position tracking from SHFE/INE must adapt; CTP reports all closes as generic Close |
| PT/PD elevated margins | 22% -- newer products with high uncertainty; capital requirements 2x typical |
| PS minimum order size | 10 lots minimum opening -- unusual among Chinese exchanges |
| LC extreme volatility | Price swings of 50%+ observed; combined with tight daily limits, can trap positions |
| Regime change frequency | New exchange with frequent rule updates -- monitor GFEX notices daily |
| No closing auction | Final price is last continuous trade, not auction-determined |
| Trading hours | Day session only: 09:00-10:15, 10:30-11:30, 13:30-15:00 |

GFEX trading rules framework *supports* night sessions ("开展夜盘交易的品种由交易所另行公布") but no products designated yet. Night session launch would be a major regime change.

## 10. Market Maker Programs

GFEX market maker rules published **June 2022**. Every new product launched with market maker programs from inception.

| Dimension | Requirement |
|-----------|-------------|
| Net asset | >= RMB 50M |
| Futures MM products | 5 (SI, LC, PS, PT, PD) |
| Options MM products | 3+ (SI, LC, PS options) |
| Quoting mode | Continuous + response quoting |

### Market Maker Benefits

| Benefit | Detail |
|---------|--------|
| Fee discounts | Reduced or waived exchange fees on MM activity |
| Position limit exemptions | Exempt from daily opening limits |
| Cancel threshold exemptions | Frequent quote/cancel not counted as abnormal trading |
| Tiered management | Performance-based tier assignment |


## 11. Empirical Parameters

Limited data -- GFEX products are new (oldest SI launched Dec 2022).

| Product | Tick Size | Typical Price (CNY) | Spread Estimate | Confidence | Notes |
|---------|-----------|--------------------|--------------------|------------|-------|
| SI | 5 CNY/ton | ~12,000 | 1-2 ticks | Low | Newer MM programs, lower liquidity than mature exchanges |
| LC | 20 CNY/ton | ~70,000-100,000 | 1-3 ticks | Low | Extreme volatility observed (50%+ swings) |
| PS | 5 CNY/ton | ~40,000 | Unknown | Very Low | Launched Dec 2024 |
| PT | 0.05 CNY/g | ~230-280 | Unknown | Very Low | Launched Nov 2025 |
| PD | 0.05 CNY/g | ~200-300 | Unknown | Very Low | Launched Nov 2025 |

LC exhibited extreme volatility -- noted in research alongside EC (1000->3600) and AO (+77%). No published academic calibrations for any GFEX product. Spreads likely wider than mature exchange products given lower liquidity and newer MM programs.

Session effects: day-only trading means no night-session spread widening to model, but L-shaped intraday pattern likely applies (widest at 09:00 open, narrowing through session).


## 12. Primary Sources

| Resource | URL |
|----------|-----|
| Rules | http://www.gfex.com.cn |
| Products | http://www.gfex.com.cn |
| Historical data | Available for download (basic, depth, delayed) |
| Market maker rules | GFEX Notice [2022]/6 |
| Fee schedules | Published on GFEX website; updated frequently |
| CSRC supervision | Same framework as all Chinese futures exchanges |
