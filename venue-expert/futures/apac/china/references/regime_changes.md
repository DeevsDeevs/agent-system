# Chinese Futures Regime Change Database

**WARNING: This database contains both CONFIRMED and UNCERTAIN information. Treat as hypothesis until independently verified. Dates from secondary sources require primary source validation before use in backtests.**

Status: DRAFT - January 2026
Confidence levels: HIGH (primary source), MEDIUM (secondary/multiple sources), LOW (single source/hearsay), UNCERTAIN (conflicting info)

---

## 1. Master Timeline Table

| Date | Exchange | Event | Impact | Confidence | Source | Backtesting Implication |
|------|----------|-------|--------|------------|--------|------------------------|
| 2010-04-16 | CFFEX | IF (CSI 300) launched | First stock index future | HIGH | Exchange | No index futures data before this |
| 2013-07-05 | SHFE | Night session: AU, AG | First night trading in China | MEDIUM | Multiple secondary | Pre-date data lacks night session |
| 2013-10-18 | DCE | Iron Ore (I) launched | New product | HIGH | Exchange | No iron ore data before this |
| 2013-12/2014-01 | SHFE | Night session: CU, AL, ZN, PB | Metals added | LOW | Unverified | Exact dates unclear |
| 2014-07-04 | DCE | Night session: P, M, Y, A, JM, J | DCE first night | MEDIUM | Secondary | |
| 2014-12-12 | CZCE | Night session: TA, SR, CF, MA, glass | CZCE first night | MEDIUM | Secondary | |
| 2015-03-27 | SHFE | Night session: NI, SN | Additional metals | LOW | Secondary | |
| 2015-04-16 | CFFEX | IC (CSI 500), IH (SSE 50) launched | Index futures expansion | HIGH | Exchange | |
| **2015-09-02** | **CFFEX** | **Stock index restrictions Round 0** | Margin 40%, fee 23/10000 (100x), 10 lot/day | **HIGH** | Exchange announcement | **CRITICAL: Pre-Sept 2015 CFFEX data incomparable** |
| **2015-09-07** | **CFFEX** | **Restrictions enforced** | Maximum restrictions in effect | HIGH | | Data structure fundamentally different |
| 2016-01-01 | CFFEX | Circuit breaker implemented | 5%/7% thresholds | HIGH | Exchange | |
| 2016-01-04 | CFFEX | Circuit breaker triggered | Both thresholds hit | HIGH | News | |
| 2016-01-07 | CFFEX | Circuit breaker triggered 2nd time | 7% within 15min of open | HIGH | News | |
| **2016-01-08** | **CFFEX** | **Circuit breaker suspended** | Indefinite suspension after 4 days | **HIGH** | Exchange | Circuit breaker period data anomalous |
| 2017-02-17 | CFFEX | Restrictions relaxed Round 1 | 20 lots, 20-30% margin, 0.092% fee | HIGH | Exchange | Regime shift |
| 2017-09-18 | CFFEX | Restrictions relaxed Round 2 | 15% margin (IF/IH), 0.069% fee | HIGH | Exchange | |
| 2018-03-26 | INE | Crude Oil (SC) launched | Internationalized, night session | HIGH | Exchange | INE crude data starts here |
| 2018-12-03 | CFFEX | Restrictions relaxed Round 3 | 50 lots, 10-15% margin, 0.046% fee | HIGH | Exchange | |
| **2019-04-22** | **CFFEX** | **Restrictions relaxed Round 4** | 500 lots, 12% IC, 0.0345% fee | **HIGH** | Exchange | **Post-Apr 2019 = "normal" CFFEX** |
| **2019-06-14** | **ALL** | **看穿式监管 enforcement** | CTP v6.3.15+ required, AppID mandatory | **HIGH** | CFMMC | Pre-June 2019 CTP versions not comparable |
| 2022-07-22 | CFFEX | CSI 1000 (IM) launched | New index future | HIGH | Exchange | |
| **2022-08-01** | **ALL** | **Futures and Derivatives Law effective** | Comprehensive regulatory overhaul | **HIGH** | CSRC | Legal framework change |
| 2023-05-25 | SHFE/DCE/INE | Day session pre-market call auction added | 08:55-09:00 for night products | MEDIUM | Secondary | |
| UNCERTAIN | CZCE | Symbol format: 3-digit to 4-digit year? | CF501 to CF2501 | **UNCERTAIN** | **CONFLICTING** | **See Section 6** |

---

## 2. Night Session Introduction Timeline

**CRITICAL FOR BACKTESTING: Data before night session introduction CANNOT be compared to data after. Night sessions fundamentally change price discovery, volatility patterns, and information incorporation.**

### SHFE Night Sessions

| Product | Launch Date | Trading Hours | Confidence | Source Notes |
|---------|-------------|---------------|------------|--------------|
| Gold (AU) | **2013-07-05** | 21:00-02:30 | MEDIUM | Multiple secondary sources cite this |
| Silver (AG) | **2013-07-05** | 21:00-02:30 | MEDIUM | Same as gold |
| Copper (CU) | Dec 2013 or Jan 2014 | 21:00-01:00 | **LOW** | Exact date unverified |
| Aluminum (AL) | Dec 2013 or Jan 2014 | 21:00-01:00 | **LOW** | |
| Zinc (ZN) | Dec 2013 or Jan 2014 | 21:00-01:00 | **LOW** | |
| Lead (PB) | Dec 2013 or Jan 2014 | 21:00-01:00 | **LOW** | |
| Nickel (NI) | 2015-03-27 | 21:00-01:00 | LOW | After NI launched (Apr 2014?) |
| Tin (SN) | 2015-03-27 | 21:00-01:00 | LOW | |
| Rubber (RU) | Unknown | 21:00-23:00 | **UNCERTAIN** | Date unknown |
| Rebar (RB) | Unknown | 21:00-23:00 | **UNCERTAIN** | Date unknown |
| Hot-rolled Coil (HC) | Unknown | 21:00-23:00 | **UNCERTAIN** | Date unknown |

**WHAT I DON'T TRUST**: The exact dates for SHFE metals (Dec 2013/Jan 2014) appear in multiple sources but I cannot find a primary exchange announcement. Treat as approximate.

### DCE Night Sessions

| Product | Launch Date | Trading Hours | Confidence |
|---------|-------------|---------------|------------|
| Palm Oil (P) | **2014-07-04** | 21:00-23:00 | MEDIUM |
| Soybean Meal (M) | **2014-07-04** | 21:00-23:00 | MEDIUM |
| Soybean Oil (Y) | **2014-07-04** | 21:00-23:00 | MEDIUM |
| Soybean No.1 (A) | **2014-07-04** | 21:00-23:00 | MEDIUM |
| Coking Coal (JM) | **2014-07-04** | 21:00-23:00 | MEDIUM |
| Coke (J) | **2014-07-04** | 21:00-23:00 | MEDIUM |
| Iron Ore (I) | Unknown (later) | 21:00-23:00 | **UNCERTAIN** | Was not in initial batch |
| Corn (C) | Unknown | 21:00-23:00 | **UNCERTAIN** | |

**SUSPICIOUS**: Iron Ore night session introduction date is not documented. Major liquid product - this is a significant gap.

### CZCE Night Sessions

| Product | Launch Date | Trading Hours | Confidence |
|---------|-------------|---------------|------------|
| PTA (TA) | **2014-12-12** | 21:00-23:30 | MEDIUM |
| Sugar (SR) | **2014-12-12** | 21:00-23:30 | MEDIUM |
| Cotton (CF) | **2014-12-12** | 21:00-23:30 | MEDIUM |
| Methanol (MA) | **2014-12-12** | 21:00-23:30 | MEDIUM |
| Glass (FG) | **2014-12-12** | 21:00-23:30 | MEDIUM |

### INE Night Sessions

| Product | Launch Date | Trading Hours | Confidence |
|---------|-------------|---------------|------------|
| Crude Oil (SC) | **2018-03-26** | 21:00-02:30 | HIGH |
| Low Sulfur Fuel Oil (LU) | Unknown | 21:00-23:00 | UNCERTAIN |
| Bonded Copper (BC) | Unknown | 21:00-01:00 | UNCERTAIN |

### Products WITHOUT Night Session

- **CFFEX**: ALL products (IF, IC, IM, IH, T, TF, TS, TL) - NO night session
- **CZCE Apple (AP)**: NO night session (special product)
- Others: Unknown - need verification

**BACKTESTING IMPLICATION**: Any strategy spanning day/night sessions cannot be backtested before the night session introduction date for that product. Overnight position dynamics fundamentally different.

---

## 3. CFFEX Stock Index Futures Restriction Timeline

**THIS IS THE MOST IMPORTANT REGIME CHANGE FOR FINANCIAL FUTURES. Data before/after September 2015 is NOT comparable.**

### Pre-Restriction Parameters (Before 2015-09-02)

| Parameter | Value | Notes |
|-----------|-------|-------|
| Daily position limit | No tight limit | Normal trading |
| Non-hedging margin | ~10-12% | Standard |
| Intraday close fee | Standard | Not penalized |
| Market maker activity | Active | Normal liquidity |

### Restriction Phase (2015-09-02 to 2019-04-22)

| Date | Daily Limit | Non-Hedging Margin | Intraday Fee | Confidence |
|------|-------------|-------------------|--------------|------------|
| **2015-09-07** | **10 contracts** | **40%** | **0.23% (23/10000)** | HIGH |
| 2017-02-17 | 20 contracts | 20-30% | 0.092% | HIGH |
| 2017-09-18 | 20 contracts | 15% (IF/IH), 30% (IC) | 0.069% | HIGH |
| 2018-12-03 | 50 contracts | 10-15% | 0.046% | HIGH |
| **2019-04-22** | **500 contracts** | **12% (IC), 10% (IF/IH)** | **0.0345%** | HIGH |

### What Broke in Backtests

1. **Volume**: Daily volume collapsed >90% after Sep 2015
2. **Spread**: Bid-ask spreads widened dramatically
3. **Volatility**: Market maker withdrawal changed volatility structure
4. **Intraday patterns**: Fee penalty eliminated most day trading
5. **Arbitrage**: ETF-futures basis widened and became stickier
6. **Queue dynamics**: Completely different with 10-lot daily limit

**RECOMMENDATION**: For CFFEX index futures:
- Pre-Sep 2015 data: Historical interest only, not valid for strategy backtest
- Sep 2015 - Apr 2019: Severe restriction regime, different market structure
- Post-Apr 2019: "Normal" regime begins, but still not pre-2015 comparable

---

## 4. Circuit Breaker History (January 2016)

**The shortest-lived major regulation in Chinese market history.**

| Date | Event | Time | Outcome |
|------|-------|------|---------|
| 2016-01-01 | Implementation | - | 5% = 15min halt, 7% = day halt |
| 2016-01-04 | First trigger (Mon) | Morning | Both thresholds hit, day terminated early |
| 2016-01-05 | No trigger (Tue) | - | Normal trading |
| 2016-01-06 | No trigger (Wed) | - | Normal trading |
| **2016-01-07** | **Second trigger (Thu)** | **13min after open** | 7% hit within minutes, day terminated ~9:43 |
| **2016-01-08** | **Suspension announced (Fri)** | Before open | Circuit breaker suspended indefinitely |

**Total duration: 4 trading days (3 actual trading days, 2 with triggers)**

### Mechanism Details

- Applied to: CSI 300 INDEX (not the futures directly)
- 5% threshold: 15-minute trading halt
- 7% threshold: Trading halted for remainder of day
- "Magnet effect": Approaching threshold accelerated selling

### What Broke

1. **Magnet effect**: Traders rushed to sell before halt, causing halt
2. **Price discovery**: Halts prevented markets from finding equilibrium
3. **Panic amplification**: Retail traders panicked during halts
4. **Cross-market effects**: A-shares and futures both affected

**BACKTESTING IMPLICATION**: 
- January 4-7, 2016 data is anomalous
- Cannot use this period for model training
- Interesting for academic study of circuit breaker effects

---

## 5. 看穿式监管 (Look-Through Supervision) Implementation

**CRITICAL FOR CTP SYSTEMS: Pre-June 2019 CTP code may not work**

### Timeline

| Date | Event | Impact |
|------|-------|--------|
| 2018 | Regulation announced | |
| 2019-06-14 21:00 | **Full enforcement** | Older CTP versions rejected |

### Technical Requirements (Post-2019-06-14)

| Requirement | Detail |
|-------------|--------|
| CTP minimum version | v6.3.15 |
| AppID | Required, format: vendor_software_version |
| AuthCode | 16-char code from broker after registration |
| ClientSystemInfo | BASE64 hardware fingerprint (MAC, HDD, CPU, OS) |
| Authentication sequence | ReqAuthenticate BEFORE ReqUserLogin |

### What Changed

1. **Anonymous trading ended**: All orders traceable to individual
2. **CTP upgrade required**: Old SDKs stopped working
3. **VM/cloud trading complicated**: Hardware fingerprint collection difficult
4. **Audit trail mandatory**: 20-year retention requirement

**BACKTESTING IMPLICATION**:
- Strategy behavior data pre/post June 2019 not directly comparable
- Pre-2019: More anonymous, potentially more manipulation
- Post-2019: All activity monitored, behavioral changes likely

---

## 6. CZCE Symbol Format Changes

**THIS IS A DATA CONTINUITY NIGHTMARE**

### The Problem

CZCE uses 3-digit year codes: CF501 (Cotton May 2015 or 2025?)

### Current Understanding (UNCERTAIN)

| Claim | Status | Evidence |
|-------|--------|----------|
| CZCE uses 3-digit years | CONFIRMED | Current contracts show CF501, not CF2501 |
| CZCE "changed" to 4-digit | **UNCERTAIN** | Compass artifact says CF2501, but exchange shows CF501 |
| Transition date | **UNKNOWN** | No documented transition date found |
| Historical data mapping | **UNCLEAR** | How do vendors handle this? |

### Possible Scenarios

1. **CZCE never changed**: Always 3-digit, ambiguity every 10 years
2. **CTP layer conversion**: CTP returns 4-digit, exchange uses 3-digit
3. **Partial change**: Some products changed, others didn't
4. **Vendor-specific**: Different data vendors handle differently

### Resolution Required

- [ ] Primary source: Current CZCE contract spec
- [ ] Historical check: What did CF501 mean in 2015 vs 2025?
- [ ] CTP SDK check: What does InstrumentID field actually contain?
- [ ] Vendor comparison: How do Wind/TqSdk/etc handle this?

**BACKTESTING IMPLICATION**: 
- CZCE historical data may have symbol ambiguity
- Must verify which decade data represents
- Continuous contract construction requires careful symbol mapping

---

## 7. Fee Change History

**Fees change frequently. This section requires ongoing updates.**

### Known Significant Fee Changes

| Date | Exchange | Product | Change | Confidence |
|------|----------|---------|--------|------------|
| 2015-09 | CFFEX | IF/IC/IH | Intraday fee 100x increase | HIGH |
| Unknown | SHFE | Various | Periodic adjustments | - |
| Unknown | DCE | Various | Periodic adjustments | - |
| Unknown | CZCE | Various | Periodic adjustments | - |

### Current Fee Structures (Reference Only - May Be Outdated)

| Exchange | Product | Standard Fee | Intraday Fee | Notes |
|----------|---------|--------------|--------------|-------|
| SHFE | Gold (AU) | 10 CNY/lot | **FREE** | Day trading encouraged |
| SHFE | Silver (AG) | 0.01% | **0.25%** | 25x penalty |
| SHFE | Copper (CU) | 0.5/10000 | 1/10000 | |
| CFFEX | IF/IC/IM | 0.023% | **0.231%** | 10x penalty |
| CZCE | Apple (AP) | 5 CNY/lot | **20 CNY/lot** | Anti-speculation |
| CZCE | PTA/Cotton/Sugar | 3-5 CNY/lot | **FREE** | Day trading encouraged |

**BACKTESTING IMPLICATION**:
- Backtest P&L requires historical fee schedule
- Fee changes can make strategies non-viable
- Must track announcement dates for fee changes

---

## 8. Position Limit Adjustments

**Position limits change frequently, especially around:**
- Delivery month approach
- High volatility periods
- Pre-holiday
- After speculation concerns

### Known Limit Changes

| Date | Exchange | Product | Old Limit | New Limit | Confidence |
|------|----------|---------|-----------|-----------|------------|
| 2015-09 | CFFEX | IF/IC/IH | Normal | 10 lots/day | HIGH |
| 2019-04 | CFFEX | IF/IC/IH | 50 lots/day | 500 lots/day | HIGH |
| Various | CZCE | Apple (AP) | Normal | Severely restricted | MEDIUM |

### Structural Limit Patterns

| Exchange | Product | General Month | Near-Delivery | Delivery Month |
|----------|---------|---------------|---------------|----------------|
| SHFE | Copper | 8K or 10% OI | 3K | 1K |
| DCE | Iron Ore | 15K | 6K-10K staged | 2K |
| CFFEX | IF/IC/IM | 1,200 (all months) | Same | Same |
| CZCE | Apple | 1,000 | 500 | 200 |

**BACKTESTING IMPLICATION**:
- Historical position limits may differ from current
- Strategy sizing must account for historical limits
- Near-delivery limits tighten - historical patterns matter

---

## 9. Margin Rate Changes

**Margins change frequently based on:**
- Volatility
- Holiday periods
- Delivery month approach
- Regulatory concern

### Historical Margin Events

| Period | Product | Exchange Min | Notes |
|--------|---------|--------------|-------|
| Normal | Gold (AU) | 4-5% | Base rate |
| Current (2026) | Gold (AU) | **15-17%** | Elevated |
| 2015-09 | IF/IC/IH | **40%** | Emergency increase |
| Current | IF | 12% | Post-relaxation |
| Current | IC | 14% | Higher than IF |
| Current | IM | 15% | Highest |

### Holiday Margin Pattern

| Holiday | Typical Increase | Timing |
|---------|------------------|--------|
| Chinese New Year | +5-15% | ~7-10 days before |
| National Day | +5-15% | ~7-10 days before |
| Other holidays | +3-5% | ~3-5 days before |

**BACKTESTING IMPLICATION**:
- Capital requirements vary over time
- Margin changes affect strategy sizing
- Pre-holiday periods have different dynamics

---

## 10. Trading Hour Modifications

| Date | Exchange | Change | Confidence |
|------|----------|--------|------------|
| 2013-07-05 | SHFE | Night session started | MEDIUM |
| 2014-07-04 | DCE | Night session started | MEDIUM |
| 2014-12-12 | CZCE | Night session started | MEDIUM |
| **2023-05-25** | SHFE/DCE/INE | Day session call auction 08:55-09:00 for night products | MEDIUM |

### Current Sessions (Reference)

| Exchange | Night Session | Day Session |
|----------|---------------|-------------|
| SHFE commodities | 21:00 - 01:00/02:30/23:00 | 09:00-15:00 |
| DCE commodities | 21:00 - 23:00 | 09:00-15:00 |
| CZCE commodities | 21:00 - 23:30 | 09:00-15:00 |
| INE | 21:00 - varies | 09:00-15:00 |
| CFFEX index | **NONE** | 09:30-15:00 |
| CFFEX treasury | **NONE** | 09:15-15:15 |

---

## 11. Backtesting Boundary Summary

**Where regime changes invalidate analysis:**

| Boundary | Products | Reason |
|----------|----------|--------|
| Pre-2013-07-05 | SHFE metals | No night session |
| Pre-2014-07-04 | DCE grains/ferrous | No night session |
| Pre-2014-12-12 | CZCE products | No night session |
| **Pre-2015-09-02** | **CFFEX index futures** | **Pre-restriction not comparable** |
| 2016-01-04 to 2016-01-07 | All | Circuit breaker period |
| **Pre-2019-04-22** | **CFFEX index futures** | **Restriction regime** |
| Pre-2019-06-14 | All | Pre-看穿式监管 |
| Pre-2022-08-01 | All | Pre-Futures Law |

### Safe Backtesting Periods

| Product Class | Safe Start Date | Notes |
|---------------|-----------------|-------|
| SHFE metals with night | Mid-2014 earliest | After night session confirmed |
| DCE grains/ferrous | Mid-2014 earliest | After night session |
| CZCE products | Early 2015 earliest | After night session |
| **CFFEX index futures** | **2019-04-22** | Post-restriction only |
| INE crude | 2018-03-26 | Product launch |
| CFFEX treasury | Varies | Less affected by restrictions |

---

## 12. Unresolved Questions & Research Gaps

### HIGH PRIORITY (Blocking Backtest Validity)

| Question | Why Critical | Status |
|----------|--------------|--------|
| Exact SHFE metals night session dates | Cannot determine pre/post night regime | Need primary source |
| Iron Ore (I) night session date | Major product, date unknown | Need primary source |
| CZCE symbol format transition | Data continuity | **Conflicting information** |
| Historical fee schedules | P&L accuracy | Scattered data |
| Historical margin schedules | Capital requirements | Scattered data |

### MEDIUM PRIORITY

| Question | Why Important | Status |
|----------|---------------|--------|
| Trading hour changes history | Data gap interpretation | Incomplete |
| Position limit change history | Strategy legality | Incomplete |
| Pre-2019 CTP version compatibility | Historical system reconstruction | Unknown |

### Assumptions That Might Be Wrong

| Assumption | Concern | Verification Needed |
|------------|---------|---------------------|
| Night sessions start at exactly 21:00 | Historical variation? | Primary source |
| Price limits always expanded D+1/D+2 | Were rules different before? | Historical rulebooks |
| FIFO matching always used | Any exchange use pro-rata? | Primary source per exchange |
| 500ms snapshot rate constant | Was it faster/slower before? | Historical CTP versions |

---

## 13. Data Sources for Verification

### PRIMARY SOURCES (Most Trustworthy)

| Source | URL | Content |
|--------|-----|---------|
| SHFE announcements | shfe.com.cn | Trading rules, circulars |
| DCE announcements | dce.com.cn | Trading rules, circulars |
| CZCE announcements | czce.com.cn | Trading rules, circulars |
| CFFEX announcements | cffex.com.cn | Trading rules, circulars |
| INE announcements | ine.cn | Trading rules, circulars |
| CSRC | csrc.gov.cn | Regulations |
| CFMMC | cfmmc.com | 看穿式监管 specs |

### SECONDARY SOURCES (Verify Against Primary)

| Source | Use For | Caution |
|--------|---------|---------|
| Wind Information | Historical data | May have gaps, vendor interpretation |
| Bloomberg | Cross-reference | Western bias, may miss China-specific |
| VNPY forum | Implementation details | Hearsay, verify all claims |
| CSDN blogs | Technical details | May be outdated or wrong |
| Broker documentation | Current rules | May differ from exchange |

### DO NOT TRUST WITHOUT VERIFICATION

- Single forum posts
- Undated documentation
- Assumed US market analogies
- "Everyone knows" assertions

---

## 14. Update Protocol

This database requires continuous maintenance:

1. **Exchange announcement monitoring**: Set alerts for shfe/dce/czce/cffex/ine announcements
2. **Quarterly review**: Verify all "current" values against exchange sources
3. **Post-incident update**: After any market event, check for rule changes
4. **Pre-backtest verification**: Before any backtest, verify regime for that period

### Change Log

| Date | Change | Source |
|------|--------|--------|
| 2026-01-26 | Initial creation | Compiled from existing documentation |

---

## Forensic Notes

### What We Believed That Might Be Wrong

1. **"SHFE has 6% intraday circuit breaker"**: Documentation said this. Actually FALSE. The 6% circuit breaker was CFFEX stock index futures only, and suspended after Jan 2016. SHFE uses daily limits only.

2. **"CZCE changed from 3-digit to 4-digit years (CF501->CF2501)"**: Conflicting evidence. Compass artifacts reference both formats. Need primary verification.

3. **"Night session introduction was Jan 2014 for SHFE metals"**: Multiple sources say "Dec 2013 or early 2014" - exact date not confirmed from primary source.

4. **"500ms is the guaranteed update rate"**: This is "approximate" per documentation. Actual interval varies, and timestamp jitter exists.

5. **"CTP timestamps come from exchanges"**: Documentation says exchange origin, but jitter patterns suggest CTP server layer involvement.

### What We Don't Know That We Should

1. When exactly did each product get night sessions?
2. What were historical fee schedules?
3. What were historical margin schedules?
4. What were historical position limits?
5. When did Level-2 data become available for each exchange?
6. When did market maker programs start for which products?

---

*This database is a living document. Every entry should be treated as a hypothesis until verified against primary sources. When in doubt, assume we're wrong.*
