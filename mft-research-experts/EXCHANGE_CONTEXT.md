# Exchange Context

All research agents **MUST** read this file first and ask the user which venue mode applies.

## Venue Modes

### Chinese Exchanges (SSE, SZSE)

**Data Characteristics:**
- Snapshot frequency: 500ms (not tick-by-tick)
- Order book depth: typically L5 or L10
- No individual trade data in real-time
- VWAP and last price provided per snapshot

**Structural Quirks:**
- T+1 settlement (no intraday round-trips for most instruments)
- Price limits: ±10% for main board, ±20% for ChiNext/STAR
- Trading halts: circuit breakers, lunch break (11:30-13:00)
- Call auction: 09:15-09:25 open, 14:57-15:00 close
- No short selling for most retail (limited stock lending)

**Data Quality Concerns:**
- Snapshot alignment across instruments (±100ms typical)
- VWAP vs last price inconsistency during volatility
- Partial halt handling (one instrument halted, others trading)
- Index vs constituent timing misalignment

**Known Gotchas:**
- Cross-boundary effects at 10% limit
- Lunch break creates discontinuity
- Close auction significantly different microstructure
- Holiday schedule differs from Western markets

---

### Crypto Spot (Binance, OKX, etc.)

**Data Characteristics:**
- Incremental order book updates (1-100ms depending on exchange)
- Full trade feed available
- Book depth varies by exchange (L20 to L100+)
- WebSocket-based, requires reconstruction

**Structural Quirks:**
- 24/7 trading (no session boundaries)
- No circuit breakers (unlimited price movement)
- Maker/taker fee structure affects order flow
- Cross-exchange arbitrage is active

**Data Quality Concerns:**
- WebSocket disconnection → missed updates → corrupted book
- Exchange-reported vs calculated volume discrepancy (wash trading)
- Timestamp accuracy varies by exchange
- API rate limits affect data completeness

**Known Gotchas:**
- Maintenance windows (often unannounced)
- Liquidation cascades create extreme microstructure
- Funding rate settlements (perpetuals) affect spot
- Stablecoin depegs contaminate "USD" pairs

---

### Crypto Derivatives (Perpetuals, Futures)

**Data Characteristics:**
- Similar to spot but with funding rate data
- Mark price vs last price distinction
- Open interest available
- Liquidation feed available on some exchanges

**Structural Quirks:**
- Funding rate settlements (typically 8h)
- Cross-margin vs isolated margin affects liquidations
- Insurance fund dynamics
- Basis between perp and spot

**Data Quality Concerns:**
- Mark price calculation methodology varies
- Liquidation data may be delayed or incomplete
- Funding rate prediction vs actual settlement

**Known Gotchas:**
- Funding rate settlement creates predictable flow
- Liquidation cascades are self-reinforcing
- Basis can go extremely negative in crashes
- ADL (auto-deleveraging) affects winning positions

---

### US Equities (NYSE, NASDAQ)

**Data Characteristics:**
- Tick-by-tick trades and quotes available
- Multiple competing venues (fragmented)
- SIP vs direct feeds latency differential
- Hidden liquidity (dark pools) not visible

**Structural Quirks:**
- Reg NMS price protection
- Odd lot handling
- Opening/closing auctions
- Halts (LULD, news, etc.)

**Data Quality Concerns:**
- SIP consolidation delays
- Trade-through detection
- Crossed NBBO situations
- Symbol changes, splits, corporate actions

**Known Gotchas:**
- Sub-penny pricing for <$1 stocks
- Retail flow internalization (off-exchange)
- ETF creation/redemption affects constituents
- Index rebalancing dates

---

## Questions Agents Should Ask

When starting any analysis, agents must ask:

1. **Which venue mode?** (from list above)
2. **What time period?** (affects data availability, market structure)
3. **What instruments?** (may have instrument-specific quirks)
4. **Any known data issues for this period?** (user may know of outages, etc.)
5. **What's the research context?** (affects acceptable assumptions)

## Adding New Venues

When encountering a new venue, document:
- Data characteristics (frequency, depth, fields)
- Structural quirks (trading hours, rules, limits)
- Data quality concerns (known issues, verification approaches)
- Gotchas (non-obvious things that break assumptions)
