# Rebuilding the nautilus-docs Skill

Prompt and checklist for regenerating SKILL.md when NautilusTrader's API changes.

## When to Rebuild

- NautilusTrader version bump (check `nautilus_trader.__version__` or workspace `Cargo.toml`)
- New adapter added or removed
- Rust crate renamed, split, or merged
- Breaking API changes (trait signatures, config structs, builder patterns)
- New docs added to the official `docs/` folder

## Step 1: Update the Docs

Docs are fetched on install into `nautilus-docs/references/docs/` (gitignored). To refresh:

```bash
rm -rf nautilus-docs/references/docs
# Re-run install.sh or manually:
temp=$(mktemp -d)
git clone --filter=blob:none --sparse --depth 1 \
  https://github.com/nautechsystems/nautilus_trader.git "$temp"
git -C "$temp" sparse-checkout set docs/
mv "$temp/docs" nautilus-docs/references/docs
rm -rf "$temp"
```

Check for:
- New files (new concepts, new adapters, new tutorials)
- Removed files (deprecated features)
- Changed files (API changes, renamed types)

## Step 2: Rebuild the Doc Navigator

For every new `.md` or `.py` file in `docs/`, add a row to the appropriate navigator table in SKILL.md (Concepts, Venue Integrations, Dev/Setup, or Tutorials).

For removed files, delete the row. For renamed files, update the path.

## Step 3: Rebuild the Rust Crate Map

The crate map is the most fragile part — it breaks on every workspace restructure.

**Source of truth**: The workspace `Cargo.toml` at the root of the nautilus_trader repo.

```bash
# After pulling the latest nautilus_trader git dep:
CHECKOUT=$(find ~/.cargo/git/checkouts/nautilus_trader-* -maxdepth 1 -type d | sort | tail -1)

# List all crate package names
find "$CHECKOUT/crates" -name "Cargo.toml" -maxdepth 3 -exec grep -H '^name' {} \;

# List all adapter crates
ls "$CHECKOUT/crates/adapters/"

# Check MSRV
grep 'rust-version' "$CHECKOUT/Cargo.toml"
```

For each crate, verify:
- Package name matches SKILL.md crate map
- Key re-exports haven't moved (especially `DataActor`, `Strategy`, `InstrumentId`)
- Feature flags still work as documented

**Critical re-exports to verify**:

```bash
# DataActor location
grep -r "pub use.*DataActor" "$CHECKOUT/crates/common/src/"

# Strategy location
grep -r "pub use.*Strategy" "$CHECKOUT/crates/trading/src/"

# InstrumentId location
grep -r "pub struct InstrumentId" "$CHECKOUT/crates/model/src/"

# LiveNode builder
grep -r "pub fn builder" "$CHECKOUT/crates/live/src/"

# BinanceDataClientConfig fields
grep -A 20 "pub struct BinanceDataClientConfig" "$CHECKOUT/crates/adapters/binance/src/config.rs"
```

## Step 4: Rebuild Anti-Hallucination Tables

This is the highest-value part of the skill. Each row prevents a specific mistake Claude makes repeatedly.

**How to maintain**:

1. **Test existing rows** — for each hallucination, verify the "Reality" column is still correct:
   ```python
   # Python hallucinations — test in a venv with nautilus_trader installed
   from nautilus_trader.common.actor import Actor  # still correct?
   from nautilus_trader.indicators import ExponentialMovingAverage  # still correct?
   ```

2. **Discover new hallucinations** — ask Claude to write code for common tasks WITHOUT the skill, then diff against what actually compiles/runs. Common sources:
   - New config struct fields that Claude will guess wrong
   - Renamed enums or moved types
   - Changed method signatures (added/removed args)
   - New features that Claude will confuse with old patterns

3. **Remove stale rows** — if a hallucinated API now exists (e.g., a missing method was added), remove the row.

4. **Rust hallucinations** — rebuild by attempting to compile a standalone binary:
   ```bash
   cd my_trading_system && cargo build 2>&1 | grep "error\[E"
   ```
   Every compilation error that comes from a wrong import path, missing trait, or wrong struct field is a hallucination row candidate.

## Step 5: Verify Working Patterns

The DataActor pattern and LiveNode wiring in SKILL.md must compile. Test:

```bash
cd my_trading_system && cargo build --release 2>&1
```

If it fails, the Rust section needs updating. Common breakage:
- `DataActor` trait method signatures changed
- `LiveNode::builder()` API changed
- `BinanceDataClientConfig` fields renamed
- New required fields added to configs (no more `..Default::default()`)

---

## Fundamental Questions the Skill Must Always Answer

These are the enduring questions any trading infrastructure user will ask. The skill must provide correct answers for ALL of these regardless of API version. If a section doesn't cover one, it's a gap.

### Data Ingestion
- How do I subscribe to trades, quotes, order book, bars?
- What's the difference between INTERNAL and EXTERNAL bars?
- How do I handle custom data types?
- What happens when I subscribe to data that doesn't exist? (silent failure)
- How does the DataEngine buffer and dispatch data?

### Order Lifecycle
- How do I submit, modify, cancel orders?
- What order types are available? (Market, Limit, StopMarket, StopLimit, TrailingStop)
- How do bracket orders work?
- What happens when modify_order isn't supported by the venue?
- How do I track order state changes? (callbacks: on_order_accepted, on_order_filled, etc.)

### Position Management
- How do I query open positions?
- NETTING vs HEDGING — when to use which?
- How do I compute unrealized PnL?
- How does signed_qty work? (float, not Decimal)

### Instrument Discovery
- How do I load instruments? (load_ids is REQUIRED)
- What's the InstrumentId format? ("SYMBOL.VENUE")
- What instrument types exist?
- How do venue-specific instrument IDs map?

### Actor / Strategy Architecture
- When to use Actor vs Strategy?
- What's the component lifecycle FSM?
- How do I publish/subscribe signals between actors?
- How do timers and alerts work?
- What's the correct on_start() ordering? (cache instrument → register indicators → subscribe)

### Backtesting
- How do I set up a BacktestEngine?
- How do I load historical data? (wranglers, catalog)
- How does the FillModel work?
- What's the difference between BacktestEngine (low-level) and BacktestRunConfig (high-level)?

### Live Deployment
- How do I configure a TradingNode (Python) / LiveNode (Rust)?
- What are the adapter config patterns for each venue?
- How do I handle shutdown gracefully?
- What are the expected warnings/errors at startup and shutdown?

### Venue Connectivity
- Which adapters exist and what markets do they support?
- What data subscriptions does each adapter support?
- What execution features does each adapter support? (modify_order, etc.)
- How do API keys and authentication work per venue?

### Rust-Specific
- Which crates do I need for my use case?
- How do I implement DataActor / Strategy traits?
- How do I build a standalone binary outside the workspace?
- What are the correct import paths? (nautilus_model vs nautilus_core)
- How does LiveNode builder work?
- What feature flags do I need?

### Performance & Operations
- Why must callbacks return fast? (single-threaded event loop)
- How do I avoid blocking the event loop?
- How do I use the clock for scheduling?
- What logging/monitoring is available?
- How do I handle degraded/faulted states?

---

## Meta-Prompt for Full Rebuild

Use this prompt to have Claude regenerate the entire SKILL.md from scratch:

```
You are rebuilding the nautilus-docs skill for NautilusTrader.

The official docs are in docs/ (read the full directory tree).
The current SKILL.md is your starting point — keep the structure but update all content.

Steps:
1. Read every file in docs/concepts/, docs/integrations/, docs/developer_guide/, docs/tutorials/, docs/getting_started/
2. Build the Doc Navigator tables from the actual files present
3. Check the Rust workspace Cargo.toml for current crate names and versions
4. Verify all anti-hallucination table entries by checking actual source code:
   - For Python: test imports in the installed nautilus_trader package
   - For Rust: check actual struct/trait definitions in the crate source
5. Update the Rust crate map from workspace members
6. Update the DataActor pattern and LiveNode wiring from actual working examples
7. Test that the Rust example compiles: cd my_trading_system && cargo build
8. Verify word count is under 2,000

For anti-hallucination entries, try to write code for each of the "Fundamental Questions"
listed in REBUILD.md WITHOUT looking at the skill, then compare what you generated
against what actually works. Every mistake you made is a hallucination row.

The skill must be self-sufficient — a user should be able to write correct
NautilusTrader code (Python or Rust) using ONLY this skill, without deepwiki or
context7. If they can't, the skill has gaps.
```

## Versioning

After rebuild, update the version line in SKILL.md:
```
**Tested against v1.XXX.0** — all code validated by running tests.
```

Track what version the anti-hallucination table was last verified against. Stale tables are worse than no table — they give false confidence.
