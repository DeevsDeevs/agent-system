# OMS Internals

Deep dive into NautilusTrader's Order Management System: execution flow, state machine, reconciliation, and risk controls.

## Execution Flow (Full Path)

```
Strategy.submit_order(order)
  │
  ├─ OrderInitialized event created
  ├─ Cache: order stored
  ├─ MessageBus: OrderInitialized published
  │
  ▼
OrderEmulator (if order.emulation_trigger != NO_TRIGGER)
  │ Holds order locally, monitors market data
  │ On trigger condition met → OrderReleased event
  │ Transforms to MARKET or LIMIT order
  │
  ▼
ExecAlgorithm (if order.exec_algorithm_id set)
  │ e.g., TWAP splits large order into child orders
  │ Child IDs: {exec_spawn_id}-E{spawn_sequence}
  │ Each child follows same path from here
  │
  ▼
RiskEngine (MANDATORY — always runs)
  │ Pre-trade checks:
  │   ├─ Price precision matches instrument
  │   ├─ Price > 0
  │   ├─ Quantity precision matches instrument
  │   ├─ Quantity within min/max bounds
  │   ├─ Notional within min/max bounds
  │   ├─ reduce_only validation (position exists, correct side)
  │   └─ Trading state check (ACTIVE / HALTED / REDUCING)
  │
  │ On failure → OrderDenied event (terminal)
  │
  ▼
ExecutionEngine
  │ Routes to correct ExecutionClient by venue
  │ Handles OMS type reconciliation (strategy vs venue)
  │ Assigns/overrides position_id on fills
  │
  ▼
ExecutionClient._submit_order(command)
  │ Translates to venue API call
  │
  ▼ (Venue Response)
  │
  ├─ ACK → generate_order_accepted()
  ├─ FILL → generate_order_filled()
  ├─ REJECT → generate_order_rejected()
  └─ ERROR → generate_order_rejected()
```

## Order State Machine

```
INITIALIZED ──┬──→ DENIED (terminal: risk check failed)
              ├──→ EMULATED (held by OrderEmulator)
              │       ├──→ RELEASED → SUBMITTED
              │       └──→ CANCELED (terminal)
              └──→ SUBMITTED ──→ REJECTED (terminal: venue rejected)
                       │
                       └──→ ACCEPTED ──┬──→ CANCELED (terminal)
                                       ├──→ EXPIRED (terminal: GTD)
                                       ├──→ TRIGGERED (stop price hit)
                                       │       └──→ same states as ACCEPTED
                                       ├──→ PENDING_UPDATE
                                       │       ├──→ ACCEPTED (update confirmed)
                                       │       └──→ OrderModifyRejected
                                       ├──→ PENDING_CANCEL
                                       │       ├──→ CANCELED (terminal)
                                       │       └──→ OrderCancelRejected
                                       ├──→ PARTIALLY_FILLED
                                       │       └──→ same states as ACCEPTED
                                       └──→ FILLED (terminal)
```

Terminal states: `DENIED`, `REJECTED`, `CANCELED`, `EXPIRED`, `FILLED`

## OMS Types

### NETTING (standard for crypto)

- One position per `InstrumentId`
- All fills aggregate into single position
- Opposite-side fills reduce/flip position
- Position ID = `InstrumentId` value

```python
# Example: NETTING behavior
# Fill 1: BUY 1.0 BTCUSDT → Position LONG 1.0
# Fill 2: BUY 0.5 BTCUSDT → Position LONG 1.5
# Fill 3: SELL 2.0 BTCUSDT → Position SHORT 0.5
# Fill 4: SELL 0.5 BTCUSDT → Position FLAT (closed)
```

### HEDGING

- Multiple independent positions per `InstrumentId`
- Each position has unique `PositionId`
- Fills don't automatically offset other positions
- Used when strategy needs isolated P&L per trade

```python
# Example: HEDGING behavior
# Fill 1: BUY 1.0 BTCUSDT → Position A: LONG 1.0
# Fill 2: BUY 0.5 BTCUSDT → Position B: LONG 0.5
# Fill 3: SELL 1.0 BTCUSDT (pos A) → Position A: FLAT (closed)
# Position B: LONG 0.5 (unaffected)
```

### OMS Type Mismatch Resolution

When strategy `oms_type` differs from venue `oms_type`, ExecutionEngine reconciles:

- **Strategy=HEDGING, Venue=NETTING**: Engine assigns virtual `position_id` to fills, creating "virtual positions" within Nautilus. The venue sees one net position; Nautilus tracks multiple.
- **Strategy=NETTING, Venue=HEDGING**: Engine overrides `position_id` on fill events to use the single netting position.

Configure per-strategy:

```python
class MyConfig(StrategyConfig, frozen=True):
    oms_type: OmsType = OmsType.HEDGING  # override venue default
```

## RiskEngine Details

### Trading States

| State | Behavior |
|-------|----------|
| `ACTIVE` | All commands accepted |
| `HALTED` | No new order commands accepted; cancels allowed |
| `REDUCING` | Only cancels and position-reducing orders accepted |

### Configuration

```python
from nautilus_trader.config import RiskEngineConfig

config = RiskEngineConfig(
    bypass=False,  # NEVER bypass in production
    max_order_submit_rate="100/00:00:01",  # 100 orders per second
    max_order_modify_rate="100/00:00:01",
    max_notional_per_order={"BTCUSDT-PERP.BINANCE": 1_000_000},
)
```

### Position Risk Validation

For `reduce_only` orders:
- Validates existing position exists
- Validates order side is opposite to position side
- If position closes while reduce_only order is open → order canceled
- Quantity reduced as position size decreases (venue-dependent)

## Execution Algorithms

### TWAP (Built-in)

```python
from nautilus_trader.config import ExecAlgorithmConfig

order = self.order_factory.limit(
    instrument_id=instrument_id,
    order_side=OrderSide.BUY,
    quantity=Quantity.from_int(100),
    price=Price.from_str("50000.00"),
    exec_algorithm_id=ExecAlgorithmId("TWAP"),
    exec_algorithm_params={"horizon_secs": 300, "interval_secs": 30},
)
self.submit_order(order)
# TWAP splits into ~10 child orders, one every 30s over 5 minutes
```

### Custom ExecAlgorithm

```python
from nautilus_trader.execution.algorithm import ExecAlgorithm

class IcebergAlgorithm(ExecAlgorithm):
    def on_order(self, order: Order) -> None:
        # Received primary order addressed to this algorithm
        display_qty = order.exec_algorithm_params.get("display_qty", 10)
        total = order.quantity

        while remaining > 0:
            child_qty = min(display_qty, remaining)
            child = self.spawn_order(
                primary=order,
                quantity=Quantity.from_int(child_qty),
                # Spawn as LIMIT, MARKET, or MARKET_TO_LIMIT
            )
            self.submit_order(child)
            remaining -= child_qty

    def on_order_filled(self, event: OrderFilled) -> None:
        # Child filled — spawn next slice if primary not complete
        pass
```

Cache queries for exec algorithms:
- `self.cache.orders_for_exec_algorithm(exec_algorithm_id)`
- `self.cache.orders_for_exec_spawn(exec_spawn_id)`

## Reconciliation

### Purpose

After restart or disconnection, reconcile internal state with venue state to catch:
- Orders accepted/filled/canceled while disconnected
- Position changes from fills during downtime
- Account balance changes

### Configuration

```python
from nautilus_trader.config import LiveExecEngineConfig

config = LiveExecEngineConfig(
    reconciliation=True,
    reconciliation_lookback_mins=1440,  # look back 24 hours
    reconciliation_instrument_ids=None,  # all instruments, or specify list
    filtered_client_order_ids=[],  # exclude specific orders
)
```

### Reconciliation Flow

1. `TradingNode` starts → connects to venue
2. `LiveExecutionEngine` calls `generate_mass_status()` on each `ExecutionClient`
3. Engine compares venue state vs cache state
4. Discrepancies resolved:
   - Missing fills → generate `OrderFilled` events
   - Status mismatches → generate appropriate events
   - Unknown orders → logged and optionally tracked

### Required Client Methods

Every `LiveExecutionClient` MUST implement these for reconciliation:

```python
async def generate_order_status_report(self, command) -> OrderStatusReport | None
async def generate_order_status_reports(self, command) -> list[OrderStatusReport]
async def generate_fill_reports(self, command) -> list[FillReport]
async def generate_position_status_reports(self, command) -> list[PositionStatusReport]
async def generate_mass_status(self, lookback_mins=None) -> ExecutionMassStatus | None
```

## Overfill Handling

Overfills: cumulative filled qty exceeds original order qty. Common in crypto due to:
- Race conditions in matching engines
- Minimum lot size constraints
- DEX/AMM mechanics
- WebSocket replay duplicates
- Reconciliation race conditions (real-time fill + polling fill with different trade_ids)

### Configuration

```python
LiveExecEngineConfig(allow_overfills=True)  # default: False

# False: logs error, rejects fill
# True: logs warning, applies fill, tracks excess in order.overfill_qty
```

### Duplicate Fill Detection

Two-level detection:
1. **LiveExecutionEngine**: Pre-filters on `trade_id` alone before generating events
2. **Order model**: `is_duplicate_fill()` compares `trade_id + side + price + qty`

Exact duplicates → skipped with warning. Noisy duplicates (same trade_id, different data) → error log, fill rejected, no crash.

## Position Management

### Position Lifecycle

```
OPENING → (first fill)
OPEN → (subsequent fills adjust qty/avg_price)
  ├─ LONG (positive net qty)
  └─ SHORT (negative net qty)
CLOSING → (net qty approaching zero)
CLOSED → (net qty == 0, realized PnL computed)
```

### PnL Tracking

- **Unrealized PnL**: Calculated from current market price vs average entry price
- **Realized PnL**: Computed on position close from fill history
- **Commission tracking**: Accumulated from all fills
- Position provides: `avg_px_open`, `avg_px_close`, `realized_pnl`, `unrealized_pnl(last_price)`

### Position Flipping (NETTING)

When a fill takes position through zero to opposite side:
1. Current position closed → realized PnL computed
2. New position opened with remaining fill qty
3. Both events generated atomically

## Order Events Generated by ExecutionClient

| Method | Event | When |
|--------|-------|------|
| `generate_order_accepted()` | `OrderAccepted` | Venue acknowledges order |
| `generate_order_rejected()` | `OrderRejected` | Venue rejects order |
| `generate_order_canceled()` | `OrderCanceled` | Venue confirms cancellation |
| `generate_order_expired()` | `OrderExpired` | GTD order expired |
| `generate_order_triggered()` | `OrderTriggered` | Stop price triggered |
| `generate_order_updated()` | `OrderUpdated` | Venue confirms modification |
| `generate_order_filled()` | `OrderFilled` | Trade executed |
| `generate_order_modify_rejected()` | `OrderModifyRejected` | Venue rejects amendment |
| `generate_order_cancel_rejected()` | `OrderCancelRejected` | Venue rejects cancellation |

All events flow through: specific handler → `on_order_event()` → `on_event()` in strategy.
