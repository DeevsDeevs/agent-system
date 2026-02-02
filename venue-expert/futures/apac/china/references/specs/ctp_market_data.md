# CTP Market Data Specification: CThostFtdcDepthMarketDataField

**Status**: PARANOID REFERENCE - Trust nothing, validate everything

---

## 1. Structure Overview (44 Fields, 440 Bytes)

### Identity Fields
| Field | Type | Size | Notes |
|-------|------|------|-------|
| TradingDay | char[9] | 9 | Settlement date YYYYMMDD |
| InstrumentID | char[81] | 81 | Contract code (was char[31] pre-v6.5!) |
| ExchangeID | char[9] | 9 | SHFE/DCE/CZCE/CFFEX/INE/GFEX |
| ExchangeInstID | char[81] | 81 | Exchange-specific ID |

### Price Fields (ALL use DBL_MAX = 1.7976931348623157e+308 as invalid sentinel)
| Field | Type | Notes |
|-------|------|-------|
| LastPrice | double | Last traded price |
| PreSettlementPrice | double | Previous settlement |
| PreClosePrice | double | Previous close |
| OpenPrice | double | DBL_MAX before first trade |
| HighestPrice | double | DBL_MAX before first trade |
| LowestPrice | double | DBL_MAX before first trade |
| ClosePrice | double | **ALWAYS DBL_MAX during trading** |
| SettlementPrice | double | **ALWAYS DBL_MAX until ~17:00** |
| UpperLimitPrice | double | Daily limit up |
| LowerLimitPrice | double | Daily limit down |

### Volume/Turnover (CUMULATIVE within day, not incremental)
| Field | Type | Notes |
|-------|------|-------|
| Volume | int | Cumulative contracts |
| Turnover | double | Cumulative CNY |
| OpenInterest | double | Current OI |
| PreOpenInterest | double | Previous OI |

### 5-Level Depth
| Field | Type | Notes |
|-------|------|-------|
| BidPrice1-5 | double×5 | DBL_MAX if no level/no L2 |
| BidVolume1-5 | int×5 | 0 if no level |
| AskPrice1-5 | double×5 | DBL_MAX if no level/no L2 |
| AskVolume1-5 | int×5 | 0 if no level |

### Timestamps (UNRELIABLE - see Section 4)
| Field | Type | Notes |
|-------|------|-------|
| UpdateTime | char[9] | HH:MM:SS |
| UpdateMillisec | int | 0-999 (**CZCE: ALWAYS 0**) |
| ActionDay | char[9] | Calendar date (exchange-dependent!) |

### Options/Derived
| Field | Type | Notes |
|-------|------|-------|
| PreDelta | double | DBL_MAX for futures |
| CurrDelta | double | DBL_MAX for futures |
| AveragePrice | double | **EXCHANGE-DEPENDENT** (see Section 5) |

---

## 2. Type Definitions

```cpp
typedef double TThostFtdcPriceType;           // 8 bytes
typedef int    TThostFtdcVolumeType;          // 4 bytes
typedef double TThostFtdcMoneyType;           // 8 bytes
typedef double TThostFtdcLargeVolumeType;     // 8 bytes
typedef char   TThostFtdcDateType[9];         // YYYYMMDD\0
typedef char   TThostFtdcTimeType[9];         // HH:MM:SS\0
typedef char   TThostFtdcInstrumentIDType[81];// Was char[31] pre-v6.5!
typedef int    TThostFtdcMillisecType;        // 0-999
```

**SDK VERSION DRIFT**: Pre-v6.5.x used `char[31]` for InstrumentID. Verify `sizeof() == 440`.

---

## 3. DBL_MAX Invalid Value Handling

**DBL_MAX = 1.7976931348623157e+308** - Official sentinel. NOT zero.

### When Fields Return DBL_MAX

| Condition | Fields Affected |
|-----------|-----------------|
| No trades yet today | LastPrice, OpenPrice, HighestPrice, LowestPrice |
| During trading hours | ClosePrice, SettlementPrice (ALWAYS) |
| Non-options contract | PreDelta, CurrDelta |
| No bid/ask in market | BidPrice1, AskPrice1 |
| No Level-2 subscription | BidPrice2-5, AskPrice2-5 |

### Validation Pattern
```python
def is_valid_price(p): return p is not None and 0 < p < 1e308 and not math.isnan(p)
```

---

## 4. Exchange-Specific Timestamp Behavior

**CRITICAL TABLE**

| Exchange | UpdateMillisec | TradingDay (Night) | ActionDay (Night) |
|----------|----------------|--------------------|--------------------|
| SHFE | 0 or 500 | Next biz day | Actual calendar |
| INE | 0 or 500 | Next biz day | Actual calendar |
| DCE | Actual 0-999 | Next biz day | **NEXT BIZ DAY** (wrong!) |
| **CZCE** | **ALWAYS 0** | **Same calendar** | Actual calendar |
| CFFEX | 0 or 500 | Next biz day | Actual calendar |

### CZCE Millisecond Problem
UpdateMillisec is always zero. Sub-second ordering impossible. VNPY interpolates (0, 500, 750, 875...) for same-second ticks - document this assumption.

### DCE ActionDay Problem
Night session ActionDay = next business day, not actual calendar. Derive actual date from TradingDay.

### Timestamp Jitter
Expected: {0, 500}ms at 500ms intervals
Observed: {0, 300, 500, 800}ms with variable gaps
Sources: Exchange snapshot timing, network delays, CTP front clock drift

---

## 5. AveragePrice Interpretation

**THIS FIELD LIES BY EXCHANGE**

| Exchange | AveragePrice Contains | To Get True VWAP |
|----------|----------------------|------------------|
| **CZCE** | True average price | Use directly |
| SHFE/INE/DCE/CFFEX | Price × Multiplier | Divide by contract multiplier |

Cross-validate: `Turnover / Volume / multiplier` should approximate AveragePrice (after correction).

---

## 6. Volume/Turnover Validation

### Cumulative Nature
Volume and Turnover reset at session boundaries only. Within session: strictly monotonic increasing.

### Validation Rules
1. `Volume[t] >= Volume[t-1]` within session (violation = corruption or boundary)
2. `Turnover_delta ≈ LastPrice × Volume_delta × Multiplier` (>1% error = suspicious)
3. `|OI_change| <= 2 × Volume_change` (larger = suspicious)

---

## 7. Night Session Replay Detection

Day session connect (09:00) may replay historical night ticks. Filter by comparing tick timestamp vs wall clock. Threshold: 3 minutes stale = replay.

Deduplication key: `(InstrumentID, UpdateTime, UpdateMillisec, Volume)`

---

## 8. Bid-Ask Validation

### Negative Spread
`BidPrice1 > AskPrice1` = either auction state or corruption

Auction windows (no explicit flag - must infer):
- Opening: 08:55-09:00, 20:55-21:00
- Closing: 14:57-15:00 (CFFEX only)

### Depth Consistency Rules
- Bids must be descending: Bid1 > Bid2 > Bid3...
- Asks must be ascending: Ask1 < Ask2 < Ask3...
- Valid price with zero volume = error

---

## 9. Edge Cases Catalog

| Case | Symptoms | Danger |
|------|----------|--------|
| **First tick of day** | OHLC = DBL_MAX | Corrupts OHLC calcs if used |
| **Limit-locked** | LastPrice = Limit, one side empty | Spread/mid calcs fail |
| **Trading halt** | No ticks, stale timestamp | No explicit notification |
| **Night→Day rollover** | TradingDay advances, Volume resets | Position limits use TradingDay |
| **Reconnection gap** | Volume jumps, no replay | Permanent data loss |
| **Duplicate ticks** | Identical tick twice | CTP retry or broker middleware |
| **CZCE code ambiguity** | CF501 = 2015 or 2025? | Check trading calendar |
| **Holiday edge** | Saturday trading (make-up days) | Maintain Chinese calendar |

---

## 10. String Encoding

All CTP strings use **GB2312/GBK**, not UTF-8. InstrumentID/ExchangeID are ASCII-safe.

---

## 11. Validation Checklist (Quick Reference)

```
[ ] Price < 1e308 and not NaN
[ ] Volume monotonic within session
[ ] Turnover consistent with Price × Volume × Multiplier
[ ] Spread non-negative (or in auction window)
[ ] Depth levels monotonic
[ ] Timestamp not stale (vs wall clock)
[ ] CZCE millisec = 0 (if not, anomaly)
[ ] DCE ActionDay corrected for night session
[ ] AveragePrice scaled correctly by exchange
[ ] OI change reasonable vs volume change
```

---

## References

- CTP SDK headers: `ThostFtdcUserApiStruct.h`, `ThostFtdcUserApiDataType.h`
- VNPY CTP Gateway: github.com/vnpy/vnpy_ctp
- OpenCTP: openctp.cn
