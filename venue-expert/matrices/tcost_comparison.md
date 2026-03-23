# Transaction Cost — Cross-Venue Matrix

## Spread Comparison

| Product/Venue | Tick Size | Median Spread (ticks) | Half-Spread (bps) | Source |
|---------------|-----------|----------------------|-------------------|--------|
| rb (rebar) / SHFE | 1 CNY/ton | 1 | ~1.4 | Indriawan et al. 2019 |
| cu (copper) / SHFE | 10 CNY/ton | 1 | ~0.7 | Indriawan et al. 2019 |
| al (aluminum) / SHFE | 5 CNY/ton | 1 | ~1.2 | Indriawan et al. 2019 |
| au (gold) / SHFE | 0.02 CNY/g | 1–2 | ~0.2–0.3 | Liu et al. 2016 |
| i (iron ore) / DCE | 0.5 CNY/ton | 1–2 | ~3–6 | Indriawan et al. 2019 |
| m (soybean meal) / DCE | 1 CNY/ton | 1 | ~1.6 | Estimate (very liquid) |
| TA (PTA) / CZCE | 2 CNY/ton | 1 | ~1.8 | Xiong & Li 2024 |
| IF (CSI 300) / CFFEX | 0.2 pts | 1–3 | ~0.3–0.8 | arXiv:2501.03171 |
| sc (crude oil) / INE | 0.1 CNY/bbl | 1–2 | ~0.9–1.8 | Estimate |
| Mega-cap US equity (top 50) | $0.01 | 1 | 1–3 | SEC MIDAS, Hagstromer 2021 |
| Large-cap US equity (S&P 500) | $0.01 | 1 | 2–7 | Hagstromer 2021: mean 3.2 bps |
| Mid-cap US equity (S&P 400) | $0.01 | 1–3 | 5–15 | SEC MIDAS |
| Small-cap US equity (R2000) | $0.01 | 2–5+ | 10–30 | Tick Pilot data |
| ES (E-mini S&P) / CME | 0.25 pts ($12.50) | 1 | ~0.3–0.5 | Practitioner estimates |
| B (Brent Crude) / ICE | $0.01/bbl ($10) | 1 | ~0.5–1.0 | Practitioner estimates |

## Market Impact

| Venue/Asset | Model | Key Parameters | Source |
|-------------|-------|---------------|--------|
| Universal (all) | Square-root law: G = sigma * sqrt(Q/V) * theta | theta ~ 1; beta ~ 0.5 | Toth et al. 2011; Bouchaud 2024 |
| US equity (S&P 500) | Almgren-Chriss calibration | gamma=0.314 (permanent), eta=0.142 (temporary), beta=0.6 | Almgren et al. 2005 (Citigroup data) |
| US equity large-cap <1% ADV | Implementation shortfall | 3–8 bps one-way | ITG/Virtu ACE |
| US equity large-cap 1–5% ADV | Implementation shortfall | 8–20 bps one-way | Frazzini et al.: mean 11.2 bps |
| US equity small-cap >5% ADV | Implementation shortfall | 50–110+ bps one-way | ITG estimates |
| CME ES ($33M, COVID 2020) | CME sqrt model | ~10 bps | CME analysis |
| CME ES ($59M, Apr 2025) | CME sqrt model | ~5.4 bps | CME analysis |
| Chinese base metals (cu, al) | Sqrt law (no calibration) | Estimated alpha: 0.3–0.8 | Proxy from international |
| Chinese ferrous (rb, i, j, jm) | Sqrt law (no calibration) | Estimated alpha: 0.8–1.5 | Higher retail participation |
| Chinese financial (IF, T) | Sqrt law (no calibration) | Estimated alpha: 0.3–0.6 | Higher institutional, deeper books |

## Fill Rate Comparison

| Venue | Back-of-Queue 1s | Back-of-Queue 1min | Front-of-Queue | Source |
|-------|-------------------|--------------------|--------------------|--------|
| US equity (large-tick) | ~1–5% | ~10–30% | >90% within seconds | Moallemi & Yuan 2017; Maglaras et al. 2022 |
| CME ES | Low (queue 500–2,000+ contracts) | 10s often insufficient | >90% | BestEx Research |
| Chinese futures (rb) | — (no published data) | Est. 2–10 min back-of-queue | — | Practitioner estimates; CTP snapshot limits study |
| Chinese futures (cu) | — | Est. 1–5 min back-of-queue | — | Practitioner estimates |
| Chinese futures (IF) | — | Est. 0.5–3 min back-of-queue | — | Practitioner estimates |

## Impact Decay Profile

| Horizon | Behavior | Mechanism | Source |
|---------|----------|-----------|--------|
| 1 second | Largely persistent | Single-trade bare impact | Eisler et al. 2012 |
| 5 seconds | Mild continuation | Book refilling, information absorption | Bonart & Gould 2015 |
| 30 seconds | Inflection point | Uninformed sweeps revert; informed continue | — |
| 5 minutes | Significant reversion signal | 31% of extreme 1-min returns reverse in next minute | Nasdaq100 data |
| End of day | ~2/3 of peak retained | Standard decay | Bucci et al. 2019 (8M+ metaorders) |
| ~50 days | ~1/2 of day-1 impact | Power-law convergence | Bucci et al. 2019 |

## Cancel Rate

| Venue | Cancel Rate | Regulatory Threshold | Source |
|-------|------------|---------------------|--------|
| Chinese exchanges (SHFE/INE) | Est. 20–40% | ≥500 cancels/contract/day; ≥50 large cancels (≥300 lots) | KaiYuan Securities 2024; SHFE rules |
| Chinese exchanges (DCE) | Est. 20–40% | ≥500 cancels/contract/day; ≥50 large cancels (≥80% max size) | DCE Abnormal Trading Rules |
| Chinese exchanges (CZCE) | Est. 20–40% | ≥500 cancels/contract/day; ≥50 large cancels (≥800 lots) | CZCE rules |
| Chinese exchanges (CFFEX index) | Est. 20–40% | ≥400 cancels/contract/day; ≥100 large cancels | CFFEX Monitoring Guidelines |
| US equity | ~94% | No hard limit; SEC scrutiny for spoofing | Moallemi & Yuan 2017 |
| CME | High (no published rate) | No explicit cancel threshold; self-match prevention available | CME rules |

## Post-Sweep Recovery

| Venue | 50% Depth Recovery | Full Recovery | Spread Normalization | Source |
|-------|-------------------|--------------|---------------------|--------|
| US equity (liquid) | ~2–5 seconds | ~5–10 seconds | 5–10 seconds (but intensity: ~30 min) | Bonart & Gould 2015; Xu et al. 2016 |
| CME ES (RTH) | Fast (10K–20K contract depth) | Seconds for normal orders | — | BestEx Research |
| CME ES (Asian session) | Slow (500–800 contracts/side) | Minutes | — | Practitioner estimates |
| Chinese futures | Est. 2–5x slower than US | — | — | Lower HFT participation, regulatory constraints |

## Per-Venue Details
- [[futures/apac/china/references/models/queue_position.md|queue_position.md]] Queue Position Model
- [[futures/apac/china/references/models/spreads.md|spreads.md]] Spread Model
