# Development Environment

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
git clone --branch develop --depth 1 https://github.com/nautechsystems/nautilus_trader
cd nautilus_trader

uv sync --active --all-groups --all-extras
# OR
make install          # release mode (slow build, fast runtime)
make install-debug    # debug mode (fast build) — USE THIS FOR DEV

# PyO3 environment variables
export LD_LIBRARY_PATH=$(python -c "import sysconfig; print(sysconfig.get_config_var('LIBDIR'))")
export PYO3_PYTHON=$(which python)
export PYTHONHOME=$(python -c "import sys; print(sys.prefix)")

pre-commit install
python -c "import nautilus_trader; print(nautilus_trader.__version__)"
```

## Build System

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

## Testing

```bash
# Rust
cargo nextest run                                    # all
cargo nextest run -p nautilus-myexchange              # specific crate
cargo nextest run -p nautilus-myexchange test_parse   # specific test
cargo nextest run -p nautilus-myexchange -- --nocapture  # with output

# Python
pytest                                              # all
pytest tests/unit_tests/                            # unit only
pytest tests/integration_tests/adapters/myexchange/ # specific adapter
pytest tests/acceptance_tests/                      # full system
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

| Tool | Language | Purpose |
|------|----------|---------|
| `rustfmt` | Rust | Formatting (CI-enforced) |
| `ruff format` | Python | Formatting (CI-enforced) |
| `clippy` | Rust | Linting |
| `ruff check` | Python | Linting |

### Rust Style

- `thiserror` for error types
- `tracing` for structured logging (not `println!` or `log`)
- `tokio` for async runtime
- `///` on all public items
- Never panic in library code — return `Result`
- `extern "C"` functions wrapped in `abort_on_panic`

## Cython to PyO3 Migration

**For new adapters: always use PyO3 directly. Do not create `.pyx` files.**

| Path | Approach |
|------|----------|
| Legacy `.pyx` | C via Cython → Rust via C ABI |
| New (v2) `python/` | PyO3 directly → Rust |

## Benchmarking

```bash
cargo bench -p nautilus-myexchange
```
