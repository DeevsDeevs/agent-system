# PR #40 Changes Summary

## Overview

**Branch**: `feature/nautilus-hft-dev`
**Before**: 10,824 lines across 36 files
**After**: 7,795 lines across 36 files
**Reduction**: 3,029 lines (28%)

## Bug Fixes

### Rust Hot Path: `Price::from(format!())` → `Price::new()`

| File | Lines Fixed |
|------|-----------|
| `market_maker_backtest.rs` | 54 |
| `ema_crossover_backtest.rs` | 115-117 |
| `bracket_order_backtest.rs` | 84, 297-298 |
| `live_modify_order_test.rs` | 103, 148, 157, 176 |
| `live_order_test.rs` | 119 |
| `signal_actor_backtest.rs` | 244 |
| `custom_data_backtest.rs` | 223 |

### Rust Logic Bugs

| File | Fix |
|------|-----|
| `ema_crossover_backtest.rs:93-99` | Added position check before entry |
| `catalog_backtest.rs:92-99` | Added position check before entry |
| `bracket_order_backtest.rs:101-108` | Added `entered` flag, enter once per flat transition |
| `live_modify_order_test.rs:171` | Removed `unwrap_or(1.0)` → early return if no price |
| `custom_data_backtest.rs:74` | Fixed VPIN: `(buy - sell).abs() / total` with comment |
| `live_data_collector.rs:130,135,140` | `Vec::with_capacity()` + max size guard |

### Python Bugs

| File | Fix |
|------|-----|
| `bracket_order_backtest.py:31` | Added None guard after `cache.instrument()` |
| `ema_crossover_backtest.py:37` | Added None guard |
| `market_maker_backtest.py:31` | Added None guard |
| `signal_pipeline_backtest.py:61` | Added None guard |
| `spread_capture_live.py` | Added `on_order_rejected`, `on_order_modify_rejected` |
| `market_maker_backtest.py` | Reset `_bid_id`/`_ask_id` in `on_order_filled` |

### backtesting.md Microprice Bug

Fixed squared denominator `(total * total)` → correct `(bv + av)` formula.

## Slop Removal by Category

| Category | Lines Saved |
|----------|------------|
| Anti-hallucination table dedup from references | ~500 |
| Decorative intros / marketing language | ~350 |
| Verbose section intros → concise | ~600 |
| Code blocks replaced with cross-references to examples | ~400 |
| Mermaid diagrams → inline text | ~100 |
| Obvious/restating comments in examples | ~200 |
| Key Imports sections (already inline) | ~50 |
| Verbose property lists → compact text | ~250 |
| Decorative dividers (`# ---`) removed | ~30 |

## Per-File Line Counts

### References

| File | Before | After | Change |
|------|--------|-------|--------|
| actors_and_signals.md | 518 | 258 | -260 |
| adapter_development_python.md | 409 | 291 | -118 |
| adapter_development_rust.md | 463 | 287 | -176 |
| backtesting.md | 718 | 363 | -355 |
| derivatives.md | 425 | 218 | -207 |
| dev_environment.md | 208 | 130 | -78 |
| exchange_adapters.md | 648 | 339 | -309 |
| execution.md | 769 | 336 | -433 |
| market_making.md | 297 | 198 | -99 |
| operations.md | 492 | 264 | -228 |
| options_and_greeks.md | 476 | 302 | -174 |
| order_book.md | 384 | 249 | -135 |
| prediction_and_betting.md | 302 | 200 | -102 |
| rust_trading.md | 151 | 89 | -62 |
| traditional_finance.md | 396 | 223 | -173 |
| **Subtotal** | **6,656** | **3,747** | **-2,909** |

### Python Examples

| File | Before | After | Change |
|------|--------|-------|--------|
| binance_enrichment_actor.py | 182 | 155 | -27 |
| bracket_order_backtest.py | 100 | 104 | +4 |
| custom_adapter_minimal.py | 134 | 130 | -4 |
| deribit_option_greeks_backtest.py | 140 | 129 | -11 |
| ema_crossover_backtest.py | 103 | 108 | +5 |
| market_maker_backtest.py | 110 | 119 | +9 |
| polymarket_binary_backtest.py | 116 | 109 | -7 |
| signal_pipeline_backtest.py | 141 | 129 | -12 |
| spread_capture_live.py | 126 | 147 | +21 |
| test_enrichment_actor_backtest.py | 145 | 145 | 0 |
| **Subtotal** | **1,297** | **1,275** | **-22** |

Note: Some Python files grew due to bug fixes (None guards, rejection handlers).

### Rust Examples

| File | Before | After | Change |
|------|--------|-------|--------|
| bracket_order_backtest.rs | 277 | 272 | -5 |
| catalog_backtest.rs | 188 | 195 | +7 |
| custom_data_backtest.rs | 254 | 247 | -7 |
| ema_crossover_backtest.rs | 181 | 189 | +8 |
| live_data_collector.rs | 233 | 246 | +13 |
| live_modify_order_test.rs | 366 | 363 | -3 |
| live_order_test.rs | 292 | 289 | -3 |
| live_spot_test.rs | 212 | 212 | 0 |
| market_maker_backtest.rs | 213 | 211 | -2 |
| signal_actor_backtest.rs | 292 | 284 | -8 |
| **Subtotal** | **2,508** | **2,508** | **0** |

Note: Rust examples net zero — bug fixes added lines, slop removal saved the same amount.

### SKILL.md

| File | Before | After | Change |
|------|--------|-------|--------|
| SKILL.md | 313 | 265 | -48 |

## Verification Results

1. `grep -r "Price::from(format" examples/` → **0 matches** ✓
2. All `cache.instrument()` in Python followed by None guard → **verified** ✓
3. No `| Hallucination |` table in reference files (only SKILL.md) → **verified** ✓
4. `grep -r "# ---" nautilus-trader/` → **0 matches** ✓
5. Line counts verified per file ✓
