# Chinese Futures Data Quality Checklist

**For**: Any agent performing research on CTP market data
**Philosophy**: All data is contaminated until proven otherwise

---

## Pre-Analysis Validation (MANDATORY)

### 1. DBL_MAX Sentinel Detection
- [ ] **Scan ALL price fields for 1.7976931348623157e+308** - this is CTP's invalid value, not zero
- [ ] Replace with NaN, never with 0 or forward-fill without documentation
- [ ] Fields commonly affected: ClosePrice, SettlementPrice (always during trading), OHLC (before first trade), BidPrice2-5/AskPrice2-5 (without L2)

### 2. Timestamp Integrity
- [ ] **CZCE: UpdateMillisec is ALWAYS 0** - sub-second ordering is impossible without interpolation
- [ ] **DCE night session: ActionDay is WRONG** (shows next biz day, not actual calendar)
- [ ] **Jitter tolerance**: Accept 300ms, 800ms instead of expected 000ms, 500ms
- [ ] **Stale data detection**: Compare tick timestamp vs collection wall-clock; >3min stale = night replay

### 3. TradingDay vs ActionDay Semantics
- [ ] **Night session (21:00+)**: TradingDay = next business day, ActionDay = actual calendar (except DCE)
- [ ] **Friday night**: TradingDay = Monday (or next trading day after holiday)
- [ ] **CZCE exception**: TradingDay = same calendar date during night session

### 4. Volume Monotonicity
- [ ] **Volume is CUMULATIVE** - must increase within session
- [ ] **Decreases indicate**: session boundary (expected) or data corruption (investigate)
- [ ] **Session boundaries**: 21:00 start, 23:00/01:00/02:30 night end (product-dependent), 09:00 day open, 15:00/15:15 close

### 5. Turnover Cross-Validation
- [ ] **Formula**: Turnover_delta ≈ LastPrice × Volume_delta × ContractMultiplier
- [ ] **>1% deviation** = suspicious, investigate
- [ ] **Requires knowing contract multiplier** - obtain from exchange specs

### 6. AveragePrice Exchange Correction
- [ ] **CZCE**: AveragePrice is true VWAP (use directly)
- [ ] **ALL OTHERS**: AveragePrice = VWAP × Multiplier (divide to get true value)
- [ ] **Cross-validate** against Turnover/Volume/Multiplier

### 7. Spread Sanity
- [ ] **BidPrice1 > AskPrice1** (negative spread) = auction state OR corruption
- [ ] **Auction windows**: 08:55-09:00, 20:55-21:00 (opening), 14:57-15:00 CFFEX only (closing)
- [ ] **One-sided market**: BidPrice1 or AskPrice1 = DBL_MAX is valid (thin market)

### 8. Depth Level Consistency
- [ ] **Bid prices descending**: Bid1 > Bid2 > Bid3 > Bid4 > Bid5
- [ ] **Ask prices ascending**: Ask1 < Ask2 < Ask3 < Ask4 < Ask5
- [ ] **Volume > 0 where price valid** (zero volume with valid price = error)
- [ ] **Levels 2-5 = DBL_MAX without Level-2 subscription** (expected, not error)

### 9. OHLC Relationship
- [ ] **LowestPrice <= LastPrice <= HighestPrice** (always)
- [ ] **LowestPrice <= OpenPrice <= HighestPrice** (always)
- [ ] **Violations** = data corruption, do not use

### 10. Open Interest Sanity
- [ ] **OI change magnitude** should be <= 2× volume change
- [ ] **Larger changes** suggest data issue or need investigation
- [ ] **OI is double type** (can have fractional values in aggregated data)

---

## Session-Specific Checks

### 11. Night Session Replay Filtering
- [ ] **Day session connect (09:00) may replay night ticks**
- [ ] **Detection**: Tick timestamp significantly behind wall clock
- [ ] **Action**: Filter and document, do not silently include

### 12. Trading Break Gaps (10:15-10:30)
- [ ] **All commodity exchanges pause** - no ticks expected
- [ ] **Mark explicitly as gap**, do not interpolate without documentation
- [ ] **CFFEX has no mid-morning break**

### 13. Reconnection Gap Detection
- [ ] **CTP provides NO REPLAY on reconnect** - gaps are permanent
- [ ] **Detection**: Volume jump, timestamp jump, missing expected ticks
- [ ] **Action**: Flag gap in data, note affected analysis periods

### 14. Duplicate Tick Detection
- [ ] **Key**: (InstrumentID, UpdateTime, UpdateMillisec, Volume)
- [ ] **Causes**: CTP retry, broker middleware, application replay
- [ ] **Action**: Deduplicate but LOG occurrences

---

## Contract-Specific Checks

### 15. CZCE Contract Code Ambiguity
- [ ] **Format**: YMM (3-digit year) not YYMM
- [ ] **CF501** = January 2015 OR January 2025 - verify against trading calendar
- [ ] **Historical data spanning decade** = AMBIGUOUS without external validation

### 16. Contract Multiplier Lookup
- [ ] **Required for**: Turnover validation, AveragePrice correction, position sizing
- [ ] **Source**: Exchange published specs (changes occasionally)
- [ ] **Do not hardcode** - maintain lookup table with effective dates

### 17. Limit Price Validation
- [ ] **UpperLimitPrice and LowerLimitPrice should be valid** (not DBL_MAX)
- [ ] **LastPrice should be within limits** (violations = data error)
- [ ] **Limit-locked detection**: LastPrice = Limit AND one-sided book

---

## Data Completeness

### 18. Expected Tick Rate
- [ ] **Standard CTP**: 2 ticks/second (500ms intervals)
- [ ] **Level-2 DCE/CZCE/GFEX**: 4 ticks/second (250ms intervals)
- [ ] **Significant deviation** from expected rate = gaps or feed issues

### 19. Instrument Coverage
- [ ] **Verify all expected contracts present** in dataset
- [ ] **Near-month vs far-month**: Liquidity differs dramatically
- [ ] **Newly listed / expiring contracts**: May have sparse data

### 20. Holiday Calendar Alignment
- [ ] **Chinese holidays differ from Western** - maintain separate calendar
- [ ] **Make-up trading days**: Saturday trading occurs (unusual)
- [ ] **Golden Week, Spring Festival**: Extended closures (1-2 weeks)

---

## Documentation Requirements

After validation, document:

```
Dataset: [identifier]
Period: [start] to [end]
Instruments: [count] contracts across [exchanges]

Validation Summary:
- DBL_MAX replacements: [count] across [fields]
- CZCE millisec interpolation: [applied/not applied]
- DCE ActionDay corrections: [count]
- Volume monotonicity violations: [count] ([X] at session boundaries, [Y] unexplained)
- Spread anomalies: [count] ([X] during auction, [Y] suspicious)
- Gaps detected: [count] totaling [duration]
- Duplicates removed: [count]

Known Limitations:
- [list any unresolved issues]
- [list any assumptions made]

Data released for analysis: YES / NO (blocked on [reason])
```

---

## Quick Reference: Exchange Quirks

| Exchange | Millisec | ActionDay (Night) | AveragePrice | Contract Format |
|----------|----------|-------------------|--------------|-----------------|
| SHFE | 0/500 | Correct | × Multiplier | lowercase+YYMM |
| INE | 0/500 | Correct | × Multiplier | lowercase+YYMM |
| DCE | 0-999 | **WRONG** | × Multiplier | lowercase+YYMM |
| CZCE | **ALWAYS 0** | Correct | Direct | UPPERCASE+YMM |
| CFFEX | 0/500 | Correct | × Multiplier | UPPERCASE+YYMM |

---

## See Also

- [CTP Market Data Specification](references/specs/ctp_market_data.md) - Full struct definition and edge cases
- [CURRENT_STATE.md](CURRENT_STATE.md) - Known facts about Chinese futures microstructure
