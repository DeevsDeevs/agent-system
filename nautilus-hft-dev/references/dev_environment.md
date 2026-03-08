# Development Environment & Toolchain

Complete setup guide for NautilusTrader development: build system, testing, CI/CD, code quality.

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| Rust (stable) | Core engine | `rustup` |
| Python 3.12–3.14 | Strategy/orchestration layer | System or pyenv |
| uv | Python package management | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| clang | C compilation for FFI | `sudo apt-get install clang` |
| Cap'n Proto | Serialization (optional) | System package manager |
| pre-commit | Git hooks for linting/formatting | `pip install pre-commit` |
| cargo-nextest | Rust test runner | `cargo install cargo-nextest` |

## Setup from Scratch

```bash
# 1. Clone (develop branch for latest)
git clone --branch develop --depth 1 https://github.com/nautechsystems/nautilus_trader
cd nautilus_trader

# 2. Install Python deps + compile Rust
uv sync --active --all-groups --all-extras
# OR
make install          # release mode (slow build, fast runtime)
make install-debug    # debug mode (fast build, slower runtime) — USE THIS FOR DEV

# 3. PyO3 environment variables (Linux/macOS)
export LD_LIBRARY_PATH=$(python -c "import sysconfig; print(sysconfig.get_config_var('LIBDIR'))")
export PYO3_PYTHON=$(which python)
export PYTHONHOME=$(python -c "import sys; print(sys.prefix)")

# 4. Pre-commit hooks
pre-commit install

# 5. Verify
python -c "import nautilus_trader; print(nautilus_trader.__version__)"
```

## Build System

### Multi-Stage Pipeline

```
build.py (orchestrator)
    ├── cargo build (Rust crates → native libraries)
    ├── maturin develop (Rust → Python extension module)
    │   └── Produces: nautilus_trader/_libnautilus.so
    └── Python package assembly
```

### Makefile Targets

| Target | Description |
|--------|-------------|
| `make install` | Full release build with all deps |
| `make install-debug` | Debug build — significantly faster for dev iteration |
| `make cargo-test` | Run Rust tests via cargo-nextest |
| `make format` | Run all formatters (rustfmt, ruff) |
| `make pre-commit` | Run all pre-commit hooks |
| `make clean` | Clean build artifacts |

### Cargo Workspace

```
nautilus_trader/
├── Cargo.toml (workspace root)
└── crates/
    ├── core/          # Fundamental types, datetime, UUID
    ├── common/        # Logging, clock, runtime, config
    ├── model/         # Domain types: instruments, orders, data
    ├── data/          # DataEngine, bar aggregation
    ├── execution/     # ExecutionEngine, algorithms
    ├── trading/       # Strategy, Actor traits
    ├── persistence/   # Parquet, database adapters
    ├── infrastructure/# Redis, PostgreSQL backends
    └── adapters/
        ├── binance/
        ├── bybit/
        ├── dydx/
        ├── databento/
        ├── tardis/
        ├── okx/
        └── ...
```

### Adding a New Adapter Crate

1. Create `crates/adapters/myexchange/`
2. Add `Cargo.toml` with workspace dependencies
3. Register in workspace `Cargo.toml`: `members = ["crates/adapters/myexchange"]`
4. Add PyO3 module registration in the main Python binding crate
5. Create Python package: `nautilus_trader/adapters/myexchange/`

## Testing

### Rust Tests

```bash
# All Rust tests (isolated per process via nextest)
make cargo-test
# OR
cargo nextest run

# Specific crate
cargo nextest run -p nautilus-myexchange

# Specific test
cargo nextest run -p nautilus-myexchange test_parse_order_book

# With output
cargo nextest run -p nautilus-myexchange -- --nocapture
```

### Python Tests

```bash
# All Python tests
pytest

# Specific adapter tests
pytest tests/integration_tests/adapters/myexchange/

# Unit tests only
pytest tests/unit_tests/

# Acceptance tests (full system)
pytest tests/acceptance_tests/
```

### Test Organization

```
tests/
├── unit_tests/           # Isolated component tests
│   ├── data/
│   ├── execution/
│   ├── model/
│   └── adapters/
├── integration_tests/    # Component interaction tests
│   └── adapters/
│       ├── binance/
│       ├── bybit/
│       └── myexchange/
└── acceptance_tests/     # Full system backtests
    └── test_backtest.py
```

### Test Patterns

```python
# Adapter parsing test
def test_parse_order_book_delta():
    raw = {"s": "BTCUSDT", "b": [["50000.00", "1.5"]], "a": [], "u": 42, "ts": 1700000000000}
    instrument_id = InstrumentId.from_str("BTCUSDT-PERP.MYEXCH")
    deltas = parse_order_book_deltas(instrument_id, raw)
    assert len(deltas) == 1
    assert deltas[0].action == BookAction.UPDATE
    assert deltas[0].order.price == Price.from_str("50000.00")
    assert deltas[0].flags == RecordFlag.F_LAST

# Adapter integration test
async def test_data_client_subscribes():
    client = MyExchangeDataClient(...)
    await client._connect()
    await client._subscribe_order_book_deltas(SubscribeOrderBook(...))
    assert "orderbook.BTCUSDT" in client._subscriptions
```

### Test Datasets

NautilusTrader provides test datasets via `TestInstrumentProvider` and `TestDataProvider`:

```python
from nautilus_trader.test_kit.providers import TestInstrumentProvider, TestDataProvider

# Standard test instruments
btcusdt = TestInstrumentProvider.btcusdt_binance()
ethusdt = TestInstrumentProvider.ethusdt_binance()
xrpusdt = TestInstrumentProvider.xrpusdt_linear_bybit()

# Test data
quotes = TestDataProvider.audusd_ticks()
bars = TestDataProvider.audusd_1min_bar()
```

## Code Quality

### Formatting

- **Rust**: `rustfmt` (enforced via CI)
- **Python**: `ruff format` (enforced via CI)
- **Linting**: `ruff check` for Python, `clippy` for Rust

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml hooks include:
- rustfmt
- ruff (format + lint)
- cargo clippy
- trailing whitespace / end-of-file
```

### Rust Style Guidelines

- Follow workspace `Cargo.toml` for dependency versions
- Use `thiserror` for error types
- Use `tracing` for structured logging (not `println!` or `log`)
- Async: prefer `tokio` runtime
- Documentation: `///` doc comments on all public items
- Never panic in library code — return `Result` or use `anyhow`
- `extern "C"` functions wrapped in `abort_on_panic`

## FFI Memory Contract

### CVec (Legacy Cython Bridge)

```
Lifecycle:
1. Rust: Vec<T> → CVec (leaks memory, transfers ownership)
2. Foreign: Use data, never modify ptr/len/cap
3. Foreign: Call drop helper EXACTLY ONCE

Violations → UB:
- Forget step 3 → memory leak
- Call step 3 twice → double-free crash
- Modify ptr/len/cap → corruption
```

### PyO3 (New Code)

```rust
// Heap values to Python:
PyCapsule::new_with_destructor(value, name, destructor)
// Destructor reconstructs Box<T>/Vec<T> and drops

// Panics must NOT cross extern "C":
pub fn abort_on_panic<F, R>(f: F) -> R
where F: FnOnce() -> R {
    match std::panic::catch_unwind(std::panic::AssertUnwindSafe(f)) {
        Ok(result) => result,
        Err(_) => std::process::abort(),
    }
}
```

## CI/CD Pipeline

1. **Lint**: ruff check, clippy, rustfmt check
2. **Build**: `maturin develop` (debug mode)
3. **Test**: `cargo nextest run` + `pytest`
4. **Security**: `cargo-deny` (license/vulnerability checks), `cargo-vet` (supply chain)
5. **Benchmark**: `criterion` / `divan` for Rust performance regression detection

## Benchmarking

```rust
// Using criterion for Rust benchmarks
use criterion::{criterion_group, criterion_main, Criterion};

fn bench_parse_order_book(c: &mut Criterion) {
    let raw = load_test_data();
    c.bench_function("parse_ob_delta", |b| {
        b.iter(|| parse_order_book_deltas(&raw))
    });
}

criterion_group!(benches, bench_parse_order_book);
criterion_main!(benches);
```

```bash
# Run benchmarks
cargo bench -p nautilus-myexchange
```

## Cython → PyO3 Migration

NautilusTrader is transitioning from Cython to pure PyO3:

- **Legacy**: `nautilus_trader/**/*.pyx` → C via Cython → Rust via C ABI (cbindgen headers)
- **New (v2)**: `python/` directory → PyO3 directly → Rust (no Cython intermediate)

For new adapters: always use PyO3 directly. Do not create `.pyx` files.

The `python/` directory structure mirrors `nautilus_trader/` but uses PyO3 bindings exclusively:
```
python/
└── nautilus_trader/
    ├── __init__.py    # imports from _libnautilus.so
    └── adapters/
        └── myexchange/  # re-exports PyO3 classes
```
