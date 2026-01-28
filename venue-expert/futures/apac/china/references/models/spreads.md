# Chinese Futures Spread Mechanics

Spread execution via CTP across SHFE/INE/DCE/CZCE/CFFEX. NO listed spread instruments **except** DCE/CZCE/GFEX native spread orders which provide atomic execution.

---

## 1. Atomic vs Synthetic Execution

| Exchange | Native Spread Orders | Atomic Execution | Synthetic Required |
|----------|---------------------|------------------|-------------------|
| **DCE** | SP (calendar), SPC (inter-commodity) | YES | No |
| **CZCE** | SPD (calendar), IPS (inter-commodity) | YES | No |
| **GFEX** | SP (calendar) | YES | No |
| **SHFE/INE** | None | NO | Yes |
| **CFFEX** | None | NO | Yes |

**Native spread order syntax:**
- DCE: `SP m2505&m2509` (calendar), `SPC y2505&p2505` (inter-commodity)
- CZCE: `SPD CF505&CF509` (calendar), `IPS SF505&SM505` (inter-commodity)

Access via CTP: Subscribe to combination codes (`ProductClass = THOST_FTDC_PC_Combination`). Exchange guarantees simultaneous leg execution at specified spread or better.

---

## 2. CTP Order Types per Exchange

| Exchange | Limit | FAK | FOK | GFD | Stop | Market |
|----------|:-----:|:---:|:---:|:---:|:----:|:------:|
| SHFE/INE | Y | Y | Y | Y | Local | N |
| DCE | Y | Y | Y | Y | Native | Y |
| CZCE | Y | Y | **N futures** | Y | N | Y |
| CFFEX | Y | Y | Y | Y | N | Near only |

**Critical: CZCE FOK unavailable for futures.** `VolumeCondition='3'` (THOST_FTDC_VC_CV) only works for CZCE options. Use FAK with explicit partial-fill handling.

CTP field mappings:
- Limit: `OrderPriceType = THOST_FTDC_OPT_LimitPrice ('2')`
- FAK: `TimeCondition = THOST_FTDC_TC_IOC ('1')` + `VolumeCondition = THOST_FTDC_VC_AV ('1')`
- FOK: `TimeCondition = THOST_FTDC_TC_IOC ('1')` + `VolumeCondition = THOST_FTDC_VC_CV ('3')`
- GFD: `TimeCondition = THOST_FTDC_TC_GFD ('3')`

---

## 3. CloseToday/CloseYesterday Handling

### SHFE/INE (Mandatory)

```
'0' = Open (开仓)
'3' = CloseToday (平今) - positions opened today
'4' = CloseYesterday (平昨) - positions opened before today
'1' = Close (平仓) - REJECTED
```

**Errors**: 50 (平今仓位不足), 51 (平昨仓位不足)

Query via `ReqQryInvestorPosition()`: `YesterdayPosition = Position - TodayPosition`

### DCE/CZCE (FIFO)

Generic Close ('1') accepted. DCE: today first, then yesterday.
CZCE priority: Speculation Single -> Combination -> Hedge; yesterday before today within each.

### CFFEX

All positions treated as "today" after opening.

---

## 4. Position Limits (Single-Side)

All exchanges: **100-lot spread = 100 lots consumed**, not 200 gross.

| Exchange | Basis | Enhancement |
|----------|-------|-------------|
| All | Single-side | 套利交易头寸 (arbitrage position quota) |
| CFFEX | Approved arb accounts | **No position limit** for registered spreads |

**Note:** Arbitrage position quota is for position limits only, not margin relief. Apply through futures company.

---

## 5. Margin Offset (~50% Automatic)

| Exchange | Same-Commodity | Cross-Commodity | Auto | Notes |
|----------|---------------|-----------------|------|-------|
| CFFEX | ~50% (larger side) | ~50% | Yes | None required |
| SHFE/INE | ~50% (larger side) | **None** | Yes | None required |
| DCE | ~50% (larger side) | ~50% | Yes | Optional enhancement |
| CZCE | ~50% spread orders | Limited | Yes | Required for single-leg |

**CZCE single-leg spreads:** Apply through broker by 14:30 for same-day processing.

**DCE combination priority:** Futures lock -> calendar -> cross-commodity -> options. System recombines at daily settlement.

**Cross-exchange spreads (e.g., steel chain i+j+rb):** NO margin offset. Legs on different exchanges = 2x capital requirement.

---

## 6. Legged Risk Management

When atomic unavailable (SHFE/INE/CFFEX), prop shop strategies:

### Split Order Execution (拆单)
- Tranche size: ~100 lots
- Execute difficult leg first (short side, less liquid)
- Confirm first leg before proceeding

### Priority Leg Selection
- Less liquid leg first
- Higher price deviation leg last

### Chase Orders (追单)

| Mode | Trigger | Action |
|------|---------|--------|
| Aggressive | Immediate | Chase unfilled |
| Neutral | >N ticks deviation | Chase (N product-specific) |
| Conservative | N/A | Accept directional exposure |

**Tick tolerance is product-specific:** 3 ticks on rb = 3 CNY; 3 ticks on cu = 30 CNY.

### Limit-Lock (涨跌停) Defense
- Pre-emptive reduction at 80% risk ratio
- Reduce both legs proportionally
- If one leg locks, cannot close non-locked leg without directional exposure

---

## 7. Timestamp Alignment Issues

| Exchange | UpdateMillisec | ActionDay (Night) | Precision |
|----------|---------------|-------------------|-----------|
| SHFE/INE | 0 or 500 | Correct | 500ms |
| DCE | 0-999 | **Wrong** (tomorrow) | Real ms |
| CZCE | **Always 0** | Correct | 1000ms |
| CFFEX | 0 or 500 | N/A (no night) | 500ms |

**CZCE cross-exchange spread error: up to 1500ms worst-case.**

Stale-data threshold: 1000ms. Mark spread price stale if either leg exceeds.

**Execution sequence ambiguity:** Within single 500ms snapshot, cannot determine which leg filled first. Both legs trading in same snapshot = unknown execution order.

**DCE overnight position tracking:** ActionDay shows tomorrow during night session. Use UpdateTime for actual timestamp; adjust date logic for overnight spreads.

Impact at rb ~3,200 CNY/ton: 500ms movement = 1-5 ticks = **10-50 CNY spread error per lot**.

---

## 8. Major Spread Products

### Rebar-Hot Coil (卷螺差) rb-hc
- Both SHFE, same margin pool (~50% offset)
- Correlation: ~0.98 (steady-state; lower during regime change)
- Typical range: 200-300 CNY (hc above rb)
- Production cost anchor: 100-200 CNY
- Entry: long hc/short rb when <100; reverse when >350-400
- Seasonal: long hc Nov-Dec

### Steel Chain Profit (钢厂利润)
```
rb - 1.6*i - 0.5*j - processing_cost
```
- Cross-exchange: DCE (i, j) + SHFE (rb)
- **NO margin offset** (different exchanges) -> 2x capital required
- Typical profit: 100-200 CNY sustainable; >300 or <0 = mean reversion opportunity
- **Backtest claims require independent validation:** historical returns subject to transaction costs, slippage, regime changes

### Iron Ore Calendar (i 01-05)
- Months: 01, 05, 09
- Range: -20 to +60 CNY/ton
- Carry: ~105-110 CNY/4 months (delivery, warehouse, storage 0.5 CNY/day/ton, VAT)
- Usually backwardation (Australia/Brazil wet season shipping)

### Stock Index Roll (IF/IH/IC/IM)
- **10x intraday fee multiplier** -> overnight/roll strategies only
- Roll timing: T-2 (IF, IC) or T-3 (IH) before 3rd Friday
- IC/IM persistent discount (贴水) from hedging demand
- IC/IH ratio: 1.6-2.0 (sector rotation play)

---

## 9. 10:15-10:30 Break Gap Risk

**During break: no order submission or cancellation.**

Working orders persist, participate in 10:30 reopening.

**Risk:** Leg A fills before 10:14, Leg B doesn't -> 15 min directional exposure, no hedge possible.

### Mitigation

**Break buffer zone:** Start at 10:10.
- Complete both legs before cutoff, OR
- Defer entire spread to 10:30

**FAK/FOK behavior:** Unfilled portion cancels immediately; filled portion is permanent. Natural protection against full partial-fills, but CZCE futures have no FOK.

---

## 10. Delivery Month Escalation

| Exchange | Natural Person Deadline | Delivery Margin |
|----------|------------------------|-----------------|
| SHFE | 3 days before last trading day | 20-40% |
| INE (SC/LU/NR) | 8 days before | Elevated |
| INE (BC) | 3 days before | Elevated |
| DCE/CZCE | Last trading day month before | 20% |
| CFFEX | None (cash settlement) | N/A |

**Spread legs calculated independently.** Near leg in delivery phase drives elevated margin. Offset reduced/eliminated when legs span different lifecycle phases.

---

## 11. Forced Liquidation

**Exchanges do NOT recognize spread positions during liquidation.**

Priority: Proprietary > brokerage, futures > options, larger > smaller, loss descending.

Legs liquidated independently. No special protection for registered spreads.

**Defense:** 30-50% excess margin, monitor exchange AND broker risk ratios separately, voluntary reduction at 80%. Pre-emptive action preserves spread integrity; forced liquidation destroys it.

---

## 12. Transaction Cost Warnings

| Product | Open | CloseToday | Multiplier |
|---------|------|------------|------------|
| ag | 0.1permil | 2.5permil | **25x** |
| IF/IH/IC/IM | 0.23permil | 2.3permil | **10x** |
| cu | 0.5permil | 1permil | 2x |
| rb | 0.1permil | 0.1permil | 1x |
| i | 1permil | 1permil | 1x |

**Stock index intraday spreads prohibitively expensive.** Overnight/roll strategies only.

Zero intraday close: au, ru, bu -> natural short-term spread advantage.

---

## 13. QFI Access

| Category | Access | Notes |
|----------|--------|-------|
| Commodity spreads | Fully permissible | No restrictions |
| Index spreads | Hedging only | Apply for code + quota |
| Treasury futures | Inaccessible | As of Jan 2026 |

Calendar spreads on index futures justifiable as rolling hedge. Pure arbitrage likely restricted. Approval: 5 trading days, 12-month validity.

---

## Chinese Terms

| English | Chinese |
|---------|---------|
| Calendar spread | 跨期套利 |
| Inter-commodity | 跨品种套利 |
| Margin offset | 套利保证金优惠 |
| Position limit | 持仓限额 |
| CloseToday | 平今 |
| CloseYesterday | 平昨 |
| Forced liquidation | 强制平仓 |
| Legged risk | 腿风险 |
| Limit-lock | 涨跌停 |
| Split order | 拆单 |
| Chase order | 追单 |
| Arbitrage quota | 套利交易头寸 |

---

## Implementation Checklist

- [ ] Native spread order routing for DCE/CZCE (ProductClass = Combination)
- [ ] Synthetic execution with leg priority for SHFE/INE/CFFEX
- [ ] CZCE FOK fallback to FAK + partial-fill handler
- [ ] CloseToday/CloseYesterday routing per exchange
- [ ] 1000ms stale-data threshold for cross-exchange spreads
- [ ] Execution sequence ambiguity within 500ms windows
- [ ] 10:10 break buffer zone implementation
- [ ] Delivery month phase tracking per leg
- [ ] Margin ratio monitoring (exchange + broker separately)
- [ ] DCE ActionDay correction for overnight position attribution
- [ ] Product-specific tick tolerance for chase orders
