# APAC Futures Markets - Regional Overview

## Major Exchanges

### China

| Exchange | Focus | Key Products |
|----------|-------|--------------|
| SHFE | Metals, energy | Copper, aluminum, crude, rubber |
| DCE | Agricultural, industrial | Iron ore, soybeans, palm oil |
| CZCE | Agricultural, chemical | Cotton, sugar, methanol, PTA |
| CFFEX | Financial | Stock index, treasury futures |
| INE | International | Crude oil (Yuan-denominated) |

**Note:** China operates separate domestic (CNY) and international (INE) markets with different access rules.

### Japan

| Exchange | Focus | Key Products |
|----------|-------|--------------|
| OSE (JPX) | Financial, equity index | Nikkei 225, TOPIX, JGB |
| TOCOM | Commodities | Gold, rubber, energy |

### Other Major Venues

| Exchange | Location | Key Products |
|----------|----------|--------------|
| HKEX | Hong Kong | Hang Seng, H-shares, metals (LME) |
| SGX | Singapore | MSCI indices, iron ore, FX |
| ASX | Australia | SPI 200, interest rates, commodities |

## Trading Hours

| Region | Local Session | UTC (approx) |
|--------|---------------|--------------|
| China | 09:00-15:00 (with break) | 01:00-07:00 |
| Japan | 08:45-15:15 / 16:30-06:00 | 23:45-06:15 / 07:30-21:00 |
| Hong Kong | 09:15-16:30 | 01:15-08:30 |
| Singapore | 08:30-18:00+ | 00:30-10:00+ |
| Australia | 09:50-16:30 | 22:50-05:30 |

**Overlap windows:**
- China/Japan: ~09:00-11:30 local China time
- APAC/Europe: Japan night session, Singapore afternoon
- APAC/US: Australia morning, Japan night session

## Settlement Conventions

| Market | Settlement | Margin Timing |
|--------|------------|---------------|
| China | T+0 | Intraday + EOD |
| Japan | T+1 | EOD |
| Hong Kong | T+1 | EOD |
| Singapore | T+1 | EOD |
| Australia | T+1 | EOD |

**China T+0:** Variation margin settles same day. Creates tighter cash management requirements.

## Regulatory Landscape

| Regulator | Jurisdiction | Characteristics |
|-----------|--------------|-----------------|
| CSRC | China | Strict capital controls, position limits, foreign access restrictions |
| JFSA | Japan | Liberal access, high transparency requirements |
| SFC | Hong Kong | International standards, gateway to China |
| MAS | Singapore | Light-touch, international hub |
| ASIC | Australia | Mature framework, commodity-friendly |

### Foreign Access

| Market | Access Model |
|--------|--------------|
| China domestic | QFII/RQFII quotas, limited direct |
| INE (China intl) | Direct foreign participation |
| Japan/HK/SG/AU | Open access |

## APAC vs US/EU Characteristics

| Aspect | APAC | US/EU |
|--------|------|-------|
| Fragmentation | Single dominant exchange per product | Multiple venues, arbitrage |
| Market maker obligations | Varies; often informal | Formal programs common |
| Retail participation | High (especially China) | Lower proportion |
| Position limits | Strict (especially China) | More flexible |
| Data transparency | Improving; China limited | High |

## Quant Considerations

1. **Time zone arbitrage** - Same underlying trades across APAC venues with different hours
2. **China uniqueness** - Position limits, T+0 settlement, restricted access require specialized approach
3. **Currency hedging** - Multi-currency exposure across region
4. **Holiday calendars** - Lunar New Year, Golden Week create extended closures
5. **Liquidity fragmentation** - Regional vs global contracts (e.g., SGX vs CME indices)

See country-specific files for detailed venue coverage.
