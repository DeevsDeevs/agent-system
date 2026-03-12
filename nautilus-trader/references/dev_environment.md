# Development Environment

NautilusTrader build system, testing, code quality, and toolchain setup.

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| Rust (stable) | Core engine | `rustup` |
| Python 3.12–3.14 | Strategy/orchestration | System or pyenv |
| uv | Python packages | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| clang | C compilation for FFI | `sudo apt-get install clang` |
| cargo-nextest | Rust test runner | `cargo install cargo-nextest` |
| pre-commit | Git hooks | `pip install pre-commit` |

## Setup from Scratch

```bash
# 1. Clone (develop branch for latest)
git clone --branch develop --depth 1 https://github.com/nautechsystems/nautilus_trader
cd nautilus_trader

# 2. Install
uv sync --active --all-groups --all-extras
# OR
make install          # release mode (slow build, fast runtime)
make install-debug    # debug mode (fast build) — USE THIS FOR DEV

# 3. PyO3 environment variables
export LD_LIBRARY_PATH=$(python -c "import sysconfig; print(sysconfig.get_config_var('LIBDIR'))")
export PYO3_PYTHON=$(which python)
export PYTHONHOME=$(python -c "import sys; print(sys.prefix)")

# 4. Pre-commit hooks
pre-commit install

# 5. Verify
python -c "import nautilus_trader; print(nautilus_trader.__version__)"
```

## Build System

### Pipeline

```mermaid
flowchart LR
    A["build.py<br/>(orchestrator)"] --> B["cargo build<br/>Rust crates → native libs"]
    A --> C["maturin develop<br/>Rust → Python extension"]
    C --> D["nautilus_trader/_libnautilus.so"]
    A --> E["Python package assembly"]
```

### Makefile Targets

| Target | Description |
|--------|-------------|
| `make install` | Full release build |
| `make install-debug` | Debug build — faster for dev iteration |
| `make cargo-test` | Rust tests via cargo-nextest |
| `make format` | All formatters (rustfmt, ruff) |
| `make pre-commit` | All pre-commit hooks |
| `make clean` | Clean build artifacts |

### Cargo Workspace

```
nautilus_trader/
├── Cargo.toml (workspace root)
└── crates/
    ├── core/           # Types, datetime, UUID
    ├── common/         # Logging, clock, runtime
    ├── model/          # Instruments, orders, data
    ├── data/           # DataEngine, bar aggregation
    ├── execution/      # ExecutionEngine, algorithms
    ├── trading/        # Strategy, Actor traits
    ├── persistence/    # Parquet, database adapters
    ├── infrastructure/ # Redis, PostgreSQL
    └── adapters/
        ├── binance/
        ├── bybit/
        ├── dydx/
        ├── databento/
        ├── tardis/
        └── okx/
```

### Adding a New Adapter Crate

1. Create `crates/adapters/myexchange/`
2. Add `Cargo.toml` with workspace dependencies
3. Register in workspace root: `members = ["crates/adapters/myexchange"]`
4. Add PyO3 module registration in main binding crate
5. Create Python package: `nautilus_trader/adapters/myexchange/`

## Testing

### Rust Tests

```bash
cargo nextest run                                    # all
cargo nextest run -p nautilus-myexchange              # specific crate
cargo nextest run -p nautilus-myexchange test_parse   # specific test
cargo nextest run -p nautilus-myexchange -- --nocapture  # with output
```

### Python Tests

```bash
pytest                                              # all
pytest tests/unit_tests/                            # unit only
pytest tests/integration_tests/adapters/myexchange/ # specific adapter
pytest tests/acceptance_tests/                      # full system
```

### Test Organization

```
tests/
├── unit_tests/           # Isolated component tests
│   ├── data/
│   ├── execution/
│   ├── model/
│   └── adapters/
├── integration_tests/    # Component interaction
│   └── adapters/
│       ├── binance/
│       └── myexchange/
└── acceptance_tests/     # Full system backtests
```

### Test Datasets

```python
from nautilus_trader.test_kit.providers import TestInstrumentProvider, TestDataProvider

btcusdt = TestInstrumentProvider.btcusdt_binance()
ethusdt = TestInstrumentProvider.ethusdt_binance()
xrpusdt = TestInstrumentProvider.xrpusdt_linear_bybit()
dp = TestDataProvider()
ticks_df = dp.read_csv_ticks("binance/ethusdt-trades.csv")
bars_df = dp.read_csv_bars("binance/ethusdt-1-MINUTE-LAST-2021.csv")
```

## Code Quality

### Formatting

- **Rust**: `rustfmt` (enforced via CI)
- **Python**: `ruff format` (enforced via CI)

### Linting

- **Rust**: `clippy` — catches common mistakes, performance issues
- **Python**: `ruff check`

### Rust Style

- `thiserror` for error types
- `tracing` for structured logging (not `println!` or `log`)
- `tokio` for async runtime
- Documentation: `///` on all public items
- Never panic in library code — return `Result`
- `extern "C"` functions wrapped in `abort_on_panic`

## Cython → PyO3 Migration

NautilusTrader is transitioning from Cython to pure PyO3:

- **Legacy**: `.pyx` → C via Cython → Rust via C ABI
- **New (v2)**: `python/` directory → PyO3 directly → Rust

**For new adapters: always use PyO3 directly. Do not create `.pyx` files.**

```
python/
└── nautilus_trader/
    ├── __init__.py     # imports from _libnautilus.so
    └── adapters/
        └── myexchange/ # re-exports PyO3 classes
```

## CI/CD Pipeline

1. **Lint**: ruff check, clippy, rustfmt check
2. **Build**: `maturin develop` (debug)
3. **Test**: `cargo nextest run` + `pytest`
4. **Security**: `cargo-deny` (license/vulnerability), `cargo-vet` (supply chain)
5. **Benchmark**: `criterion` / `divan` for regression detection

## Benchmarking

```rust
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
cargo bench -p nautilus-myexchange
```
