# Execution

## Full Execution Flow

`Strategy.submit_order()` → OrderInitialized → Cache → MessageBus → (OrderEmulator?) → (ExecAlgorithm?) → RiskEngine → ExecutionEngine → ExecutionClient → Venue → Accepted/Filled/Rejected. RiskEngine fail → OrderDenied (terminal).

## Order State Machine

**Terminal states**: DENIED, REJECTED, CANCELED, EXPIRED, FILLED

- **Market**: submit → Submitted → Accepted → Filled (possibly multiple partial fills)
- **Limit**: submit → Submitted → Accepted → PendingUpdate → Updated → PendingCancel → Canceled

From ACCEPTED: CANCELED, EXPIRED (GTD), TRIGGERED (stop), PENDING_UPDATE (modify), PENDING_CANCEL (cancel), PARTIALLY_FILLED, FILLED. PARTIALLY_FILLED can → CANCELED, FILLED, PENDING_UPDATE, PENDING_CANCEL.

## OMS Types

**NETTING** (standard for crypto): One position per `InstrumentId`. Opposite-side fills reduce/flip. Position ID = `InstrumentId`.

```python
# BUY 1.0 → LONG 1.0 → BUY 0.5 → LONG 1.5 → SELL 2.0 → SHORT 0.5
```

**HEDGING**: Multiple independent positions per `InstrumentId`, each with unique `PositionId`.

```python
class MyConfig(StrategyConfig, frozen=True):
    oms_type: OmsType = OmsType.HEDGING  # override venue default
```

When strategy `oms_type` differs from venue:
- **Strategy=HEDGING, Venue=NETTING**: Engine assigns virtual `position_id`
- **Strategy=NETTING, Venue=HEDGING**: Engine overrides to single netting position

## RiskEngine

Checks: price precision, price > 0 (except options), quantity bounds, notional bounds, `reduce_only` validation, trading state.

| State | Behavior |
|-------|----------|
| `ACTIVE` | All commands accepted |
| `HALTED` | No new orders; cancels allowed |
| `REDUCING` | Only cancels and position-reducing orders |

```python
config = RiskEngineConfig(
    bypass=False,  # NEVER bypass in production
    max_order_submit_rate="100/00:00:01",
    max_order_modify_rate="100/00:00:01",
    max_notional_per_order={"BTCUSDT-PERP.BINANCE": 1_000_000},
)
```

## Order Emulator

| Type | Action |
|------|--------|
| `STOP_MARKET` | Submits MARKET on trigger |
| `STOP_LIMIT` | Submits LIMIT on trigger |
| `TRAILING_STOP_MARKET` | Trails trigger, submits MARKET |
| `MARKET_IF_TOUCHED` / `LIMIT_IF_TOUCHED` | Submits MARKET/LIMIT on touch |

```python
order = self.order_factory.stop_market(
    instrument_id=instrument_id, order_side=OrderSide.SELL,
    quantity=Quantity.from_int(1), trigger_price=Price.from_int(50000),
    trigger_type=TriggerType.LAST_PRICE,
    emulation_trigger=TriggerType.LAST_PRICE,  # emulate locally
)
```

## Execution Algorithms

```python
# TWAP (built-in)
order = self.order_factory.market(
    instrument_id=instrument_id, order_side=OrderSide.BUY,
    quantity=Quantity.from_int(100),
    exec_algorithm_id=ExecAlgorithmId("TWAP"),
    exec_algorithm_params={"horizon_secs": 300, "interval_secs": 30},
)
self.submit_order(order)
```

```python
# Custom
class IcebergAlgorithm(ExecAlgorithm):
    def on_order(self, order: Order) -> None:
        display_qty = order.exec_algorithm_params.get("display_qty", 10)
        child = self.spawn_order(primary=order, quantity=Quantity.from_int(display_qty))
        self.submit_order(child)
```

Cache: `cache.orders_for_exec_algorithm(id)`, `cache.orders_for_exec_spawn(spawn_id)`.

## Contingent Orders

```python
entry = self.order_factory.limit(...)
stop = self.order_factory.stop_market(..., reduce_only=True)
take = self.order_factory.limit(..., reduce_only=True)
order_list = OrderList(
    order_list_id=OrderListId("BRACKET-001"),
    orders=[entry, stop, take], contingency_type=ContingencyType.OTO,
)
self.submit_order_list(order_list)
```

Use `order_factory.bracket()` for standard entry+SL+TP. Orders use `order.side`, events use `event.order_side`.

- **OCO**: One fills/cancels → other canceled
- **OUO**: Filling one updates the other's quantity

## Order Events

ExecutionClient methods: `generate_order_accepted()`, `generate_order_rejected()`, `generate_order_filled()`, `generate_order_canceled()`, `generate_order_expired()`, `generate_order_triggered()`, `generate_order_updated()`, `generate_order_modify_rejected()`, `generate_order_cancel_rejected()`.

Event flow: specific handler → `on_order_event()` → `on_event()`.

## Overfill and Duplicate Detection

`LiveExecEngineConfig(allow_overfills=True)` — default False (rejects), True (logs warning, applies, tracks in `order.overfill_qty`). Duplicate detection: `LiveExecutionEngine` pre-filters on `trade_id`, then `Order.is_duplicate_fill()` compares `trade_id + side + price + qty`.

## Position Management

Events: PositionOpened → PositionChanged → PositionClosed.

| Property | Description |
|----------|-------------|
| `position.avg_px_open` | Average entry price |
| `position.avg_px_close` | Average exit price |
| `position.realized_pnl` | From fill history |
| `position.unrealized_pnl(last_price)` | Current vs entry |

Position flipping (NETTING): fill through zero closes current, opens new with remaining qty. Both events atomic.

## Portfolio API

```python
account = self.portfolio.account(Venue("BINANCE"))
account.balance_total(Currency.from_str("USDT"))
account.balance_free(Currency.from_str("USDT"))
account.balance_locked(Currency.from_str("USDT"))
self.portfolio.is_flat(instrument_id)
self.portfolio.net_position(instrument_id)
self.portfolio.unrealized_pnls(Venue("BINANCE"))
```

## TradingNode Setup

```python
import os
from nautilus_trader.config import *
from nautilus_trader.live.node import TradingNode
from nautilus_trader.adapters.binance import (
    BINANCE, BinanceAccountType, BinanceDataClientConfig, BinanceExecClientConfig,
    BinanceLiveDataClientFactory, BinanceLiveExecClientFactory,
)
from nautilus_trader.adapters.binance.common.enums import BinanceKeyType

config = TradingNodeConfig(
    trader_id="CRYPTO-HFT-001",
    logging=LoggingConfig(log_level="INFO"),
    cache=CacheConfig(database=DatabaseConfig(type="redis", host="localhost", port=6379)),
    message_bus=MessageBusConfig(
        database=DatabaseConfig(type="redis", host="localhost", port=6379),
        use_instance_id=True, streams_prefix="trader",
    ),
    exec_engine=LiveExecEngineConfig(reconciliation=True, reconciliation_lookback_mins=1440),
    data_clients={BINANCE: BinanceDataClientConfig(
        api_key=os.environ["BINANCE_API_KEY"], api_secret=os.environ["BINANCE_API_SECRET"],
        key_type=BinanceKeyType.ED25519, account_type=BinanceAccountType.USDT_FUTURES,
    )},
    exec_clients={BINANCE: BinanceExecClientConfig(
        api_key=os.environ["BINANCE_API_KEY"], api_secret=os.environ["BINANCE_API_SECRET"],
        key_type=BinanceKeyType.ED25519, account_type=BinanceAccountType.USDT_FUTURES,
    )},
    timeout_connection=30.0, timeout_reconciliation=10.0,
    timeout_portfolio=10.0, timeout_disconnection=10.0, timeout_post_stop=5.0,
)
node = TradingNode(config=config)
node.add_data_client_factory(BINANCE, BinanceLiveDataClientFactory)
node.add_exec_client_factory(BINANCE, BinanceLiveExecClientFactory)
node.trader.add_strategy(MyStrategy(my_config))
node.build()
node.run()
```

**Data-only node**: Omit `exec_clients`. Warnings are harmless.

| Aspect | TradingNode | BacktestNode |
|--------|-------------|--------------|
| Clock | `LiveClock` | `TestClock` |
| Data | Real venue streams | Historical |
| Execution | Real venue APIs | `SimulatedExchange` |
| Event loop | Async | Synchronous |
| Constraint | One per process | Sequential OK |

Same `Strategy` class works in both.

## State Persistence

Redis (`DatabaseConfig(type="redis")`) for state recovery, Postgres for audit trail. Persisted: orders, positions, accounts, custom state via `on_save()`/`on_load()`.

## Reconciliation

After restart/disconnection: connects → `generate_mass_status()` → compares venue vs cache → applies missing fills, corrects mismatches.

```python
LiveExecEngineConfig(
    reconciliation=True, reconciliation_lookback_mins=1440,
    inflight_check_interval_ms=2000, open_check_interval_secs=10,
    open_check_lookback_mins=60, position_check_interval_secs=30,
    reconciliation_startup_delay_secs=10,  # DO NOT reduce below 10
    open_check_threshold_ms=5000, max_single_order_queries_per_cycle=10,
    single_order_query_delay_ms=100,
)
```

Order resolution on max retries: `SUBMITTED` → `REJECTED`, `PENDING_UPDATE`/`PENDING_CANCEL` → `CANCELED`.

Required ExecutionClient methods: `generate_order_status_report()`, `generate_order_status_reports()`, `generate_fill_reports()`, `generate_position_status_reports()`, `generate_mass_status()`.

Gotchas: `reconciliation_startup_delay_secs < 10` causes premature reconciliation. `open_check_lookback_mins` too short → false resolutions. Flatten positions before restart. External orders during lookback cause mismatches.

## Memory Management

`LiveExecEngineConfig` purge options: `purge_closed_orders_interval_mins`, `purge_closed_orders_buffer_mins`, `purge_closed_positions_*`, `purge_account_events_*`, `purge_from_database=False`.

## External Order Claims

`StrategyConfig(external_order_claims=["BTCUSDT-PERP.BINANCE"])` — claim externally placed orders.

## Multi-Venue Trading

Multiple entries in `data_clients`/`exec_clients` dicts: `{"BINANCE": BinanceDataClientConfig(...), "BYBIT": BybitDataClientConfig(...)}`.

## Instrument Constraints

Key properties: `instrument.min_notional`, `min_quantity`, `min_price`, `maker_fee`, `taker_fee`. Leverage/transfers: use venue REST API directly.

## Timeouts

`TradingNodeConfig(timeout_connection=20.0, timeout_reconciliation=60.0, timeout_portfolio=120.0, timeout_disconnection=10.0, timeout_post_stop=10.0)`. Increase reconciliation for many open orders, portfolio for multi-venue.

## Deployment

Standard `if __name__ == "__main__":` entry point. `node.build()` then `node.run()` in `try/except KeyboardInterrupt`. **NO Jupyter notebooks** for live: event loop conflicts, no signal handling.

> See SKILL.md for common hallucination guards.

## Rust

| Concern | Python | Rust |
|---|---|---|
| `modify_order` arg | Order reference | `OrderAny` (owned — clone from cache) |
| `cancel_order` arg | `ClientOrderId` or order | `OrderAny` (owned) — use `cancel_all_orders` if not stored |
| `on_order_accepted` | `Actor`, returns `None` | `Strategy` trait, owned `OrderAccepted`, returns `()` |
| `on_order_filled` | Returns `None` | `DataActor`, `&OrderFilled`, returns `Result<()>` |
| Bracket return | `OrderList` | `Vec<OrderAny>` |
| Cancel from `on_stop` | Works | Channel closed — cancel from live callbacks |

### Order Event Callbacks

| Callback | Trait | Signature |
|---|---|---|
| `on_order_filled` | `DataActor` | `fn(&mut self, event: &OrderFilled) -> Result<()>` |
| `on_order_canceled` | `DataActor` | `fn(&mut self, event: &OrderCanceled) -> Result<()>` |
| `on_order_accepted` | `Strategy` | `fn(&mut self, event: OrderAccepted)` — owned, no Result |
| `on_order_rejected` | `Strategy` | `fn(&mut self, event: OrderRejected)` — owned, no Result |

### Order Cancellation

```rust
self.cancel_all_orders(instrument_id, None, None)?;

let order_opt = { cache.borrow().order(&id).cloned() };
if let Some(order) = order_opt {
    if order.is_open() { self.cancel_order(order, None)?; }
}
```

**`on_stop` cancels silently fail** — track `Instant::now()` in `on_order_accepted`, check elapsed in `on_trade`, cancel from there. See [live_order_test.rs](../examples/live_order_test.rs) for pattern.

### Margin Sequencing

Market buy + limit sell simultaneously fails on cross-margin netting. Submit second in `on_order_filled`:

```rust
fn on_order_filled(&mut self, event: &OrderFilled) -> Result<()> {
    if self.phase == Phase::EntrySubmitted && event.order_side == OrderSide::Buy {
        self.submit_order(limit_sell, None, None)?;
    }
    Ok(())
}
```

### Order Modification

```rust
fn requote(&mut self, order_id: ClientOrderId, new_price: Price) -> Result<()> {
    let order_opt = {
        let cache = self.cache_rc();
        cache.borrow().order(&order_id).cloned()
    };
    if let Some(order) = order_opt {
        if order.is_open() { self.modify_order(order, None, Some(new_price), None, None)?; }
    }
    Ok(())
}
```

### Bracket / OTO Orders

```rust
let orders = self.core.order_factory().bracket(
    self.instrument_id, OrderSide::Buy, self.trade_size,
    None, sl_price, None, tp_price,
    None, None, None, None,
    None,  // reduce_only: None — Some(true) applies to entry too
    None, None, None, None, None, None,
);
self.submit_order_list(orders, None, None)?;
```

BacktestEngine requires `support_contingent_orders = Some(true)` in `add_venue`.

**Known backtest bugs (v1.224.0)**:
1. `execution/src/engine/mod.rs:1520` — double `borrow_mut` on OTO children. Panics.
2. `matching_engine/engine.rs:3431` — `todo!()` for `StopMarket` + `L1_MBP`.

**Workaround** — submit entry, then on fill submit SL (StopLimit, NOT StopMarket) + TP (Limit), cancel survivor on SL/TP fill. See [bracket_order_backtest.rs](../examples/bracket_order_backtest.rs) for full implementation.

### Shutdown Errors

`channel closed` during shutdown — known race in nautilus-binance adapter. Harmless.
