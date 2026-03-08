# Architecture

## Design Principles

- **Domain-driven design (DDD)** — trading domain modeled as first-class concepts
- **Event-driven architecture** — all state changes propagated as events
- **Hexagonal architecture** (Ports & Adapters) — venue-agnostic core
- **Crash-only design** — unified recovery path, externalized state, fast restart, idempotent operations
- **Fail-fast policy** — data integrity over availability. Fails immediately on: arithmetic overflow/underflow, invalid deserialization (NaN, Infinity), type conversion failures, malformed input

**Rationale**: "Corrupt data is worse than no data" in trading systems.

## Quality Priorities (ordered)

1. Reliability
2. Performance
3. Modularity
4. Testability
5. Maintainability
6. Deployability

## Hybrid Python/Rust Architecture

- **Rust crates** in `crates/` — core logic, performance-critical paths
- **Python/Cython** in `nautilus_trader/` — user-facing API, strategy definitions
- **PyO3 bindings** — statically-linked Rust libraries exposed to Python

### Crate Categories

| Category | Crates |
|----------|--------|
| Foundation | core, model, common, system, trading |
| Engines | data, execution, portfolio, risk |
| Infrastructure | serialization, network, cryptography, persistence |
| Runtime | live, backtest |
| External | adapters |
| Bindings | pyo3 |

**Feature flags**: `streaming`, `cloud`, `python`, `defi`

## Core Components

### NautilusKernel

Central orchestration: initialization, messaging infrastructure, environment-specific behaviors, lifecycle management.

### MessageBus

| Pattern | Use |
|---------|-----|
| Pub/Subscribe | Data distribution, event broadcasting |
| Request/Response | Data requests, queries |
| Command/Event | Order commands, execution events |
| Point-to-point | Direct component communication |

Optional Redis-based state persistence for external streaming.

### Cache

High-performance in-memory storage:

```python
# Market data
self.cache.bars(bar_type)
self.cache.quote_tick(instrument_id)
self.cache.trade_ticks(instrument_id)
self.cache.order_book(instrument_id)

# Trading objects
self.cache.order(client_order_id)
self.cache.position(position_id)
self.cache.account(account_id)
self.cache.instrument(instrument_id)

# Queries
self.cache.orders_open(instrument_id=instrument_id)
self.cache.orders_closed()
self.cache.orders_emulated()
self.cache.orders_inflight()
self.cache.positions_open()
self.cache.positions_closed()
self.cache.orders_for_position(position_id)
```

Configuration:

```python
from nautilus_trader.config import CacheConfig

CacheConfig(
    tick_capacity=10_000,    # max ticks per instrument
    bar_capacity=10_000,     # max bars per bar-type
    database="redis",        # optional persistent backend
    encoding="msgpack",
)
```

**Cache vs. Portfolio**: Cache = historical perspective, complete trading history. Portfolio = current real-time aggregated state.

### DataEngine

Processes and routes market data: quotes, trades, bars, order books, custom data. Manages subscriptions, request routing, bar aggregation.

### ExecutionEngine

Order lifecycle management: routing commands to adapters, state tracking, reconciliation.

### RiskEngine

Pre-trade checks: precision, bounds, notional limits, position validation. Configurable risk rules.

### Portfolio

Real-time aggregated portfolio state: positions, P&L, exposure, margin.

## Component State Machine

**Stable states**: PRE_INITIALIZED → READY → RUNNING → STOPPED → DISPOSED

**Degraded states**: DEGRADED, FAULTED

**Transitional states**: STARTING, STOPPING, RESUMING, RESETTING, DISPOSING, DEGRADING, FAULTING

## Threading Model

**Single-threaded kernel** encompasses:
- MessageBus
- Strategy logic
- Risk engine
- Cache

**Background threads** for:
- Network I/O
- Persistence
- Adapter connections
- Communication via MessageBus channels

This provides deterministic execution in the core loop while allowing async I/O.

## Environment Contexts

| Context | Data Source | Execution |
|---------|-----------|-----------|
| Backtest | Historical | Simulated venues |
| Sandbox | Real-time | Simulated venues |
| Live | Real-time | Live venues (paper or real) |

## Data Flow

```
External Ingestion → DataEngine Processing → Caching → Event Publishing → Consumer Delivery
```

## Execution Flow

```
Command Generation → MessageBus Publishing → Risk Validation → Execution Routing → External Submission → Event Flow Back → State Updates
```

## Process Constraints

**One TradingNode or BacktestNode per process** — global singleton state prevents concurrent instances. Sequential execution is supported.

## Identifiers

| Type | Format | Example |
|------|--------|---------|
| `TraderId` | `{name}-{tag}` | `TRADER-001` |
| `StrategyId` | `{name}-{tag}` | `EMACross-001` |
| `InstrumentId` | `{symbol}.{venue}` | `BTCUSDT-PERP.BINANCE` |
| `Venue` | `{name}` | `BINANCE`, `SIM` |
| `ClientOrderId` | Auto-generated | `O-20240101-001-000` |
| `PositionId` | Auto-generated | `P-001` |
| `AccountId` | `{venue}-{id}` | `BINANCE-001` |
