# Latency — Cross-Venue Matrix

## Cross-Venue Latency

| Route | Distance (km GC) | Fiber OW (ms) | Microwave OW (ms) | Source |
|-------|-------------------|---------------|-------------------|--------|
| Carteret NJ ↔ Aurora IL | ~1,180 | 6.49 (Spread Networks) | **3.982** | McKay/Quincy 2016 |
| Mahwah NJ ↔ Aurora IL | ~1,190 | ~6.5 | **3.986** | McKay/Quincy 2016 |
| Secaucus NJ ↔ Aurora IL | ~1,170 | ~6.5 | **4.015** | McKay/Quincy 2016 |
| Mahwah ↔ Carteret NJ | ~48 | ~0.25–0.35 | ~0.17–0.20 | mmWave estimates |
| Secaucus ↔ Carteret NJ | ~32 | ~0.20 | **0.091** | McKay 2016 (182 μs RTT) |
| London LD4 ↔ Aurora IL | ~6,300 | ~36 (Hibernia) | ~33–35 (hybrid) | Quincy 2014: 35.39 ms |
| London LD4 ↔ Frankfurt FR2 | ~600 | ~4–5 | **2.32** | McKay 2015 (4.64 ms RTT) |
| Tokyo ↔ Singapore SGX | ~5,300 | ~32.5 | ~32.5 (hybrid) | NTT ASE: 65 ms RTD |
| Tokyo ↔ Shanghai | ~1,760 | ~15–18 | **11.43** | McKay 2022 (22.86 ms RTT) |
| Shanghai ↔ Singapore | ~3,800 | ~25–35 | est. 22–30 | Limited data |

## Within-DC Latency

| Location | Latency | Notes |
|----------|---------|-------|
| Aurora CyrusOne rack-to-rack | ~5 μs one-way | McKay 2014 |
| Aurora Equinix CH4 → CyrusOne | **287 μs** one-way | Databento; inter-building same campus |
| Aurora → 350 E. Cermak (Chicago) | **185 μs** one-way | McKay/Quincy 2013 |
| NJ cross-connect same building | 1–5 μs | Industry standard |
| Per meter of fiber | ~4–5 ns | Physics (refractive index ~1.47) |

## Exchange Matching Latency

| Exchange | Matching Latency | Wire-to-Wire | Notes |
|----------|-----------------|-------------|-------|
| CME Globex | Sub-millisecond (~1 μs order book) | ~1–5 μs (co-lo rack-to-rack) | Aurora IL; ns timestamps |
| ICE Futures Europe | <1 ms average | **~6 μs** (FPGA optimized) | Basildon, Essex (NOT LD4) |
| Eurex (T7) | Sub-millisecond | — | FR2 Frankfurt; ns timestamps |
| SGX (TITAN) | <100 μs (exchange-stated) | Sub-15 μs (Tier-1 co-lo) | 25 Serangoon North, Singapore |
| Nasdaq | Sub-80 μs | <10 μs (co-lo) | Carteret NJ |
| NYSE | Sub-millisecond | — | Mahwah NJ |
| Chinese futures (SHFE/INE) | ~500 μs order-to-ack | — | +300 μs added Jul 2024 (fiber extension) |
| Chinese futures (CFFEX) | Sub-millisecond | — | +30 μs added Jul 2024 |
| Chinese futures (DCE/CZCE) | ~1–2 ms (co-lo) | — | Inferred from co-lo data |
| Chinese futures (GFEX) | ~1–2 ms (estimated) | — | Limited data |

## Key Providers

| Provider | Coverage | Notes |
|----------|----------|-------|
| McKay Brothers / Quincy Data | US, EU, Asia routes | Carteret–Aurora: 3.982 ms (1.1% above speed-of-light) |
| Anova Financial Networks | US (expanding) | Competing microwave network |
| New Line Networks | US | Jump/Virtu JV |
| DRW / Vigilant Global | US, EU | Proprietary microwave infra |
| Hibernia Express | Transatlantic subsea | NJ–London LD4: 29.28 ms one-way |

## Per-Venue Details
- [[futures/amer/cme.md|cme.md]] §8 Session Schedule / §1 Co-Location
- [[futures/emea/ice.md|ice.md]] §6 Co-Location
- [[futures/apac/sgx.md|sgx.md]] §4 TITAN Platform
- [[futures/apac/china/futures_china.md|futures_china.md]] §10 Matching Engine Latency
