# Execution System

## Execution Flow

```
Strategy → OrderEmulator → ExecAlgorithm → RiskEngine → ExecutionEngine → ExecutionClient → Venue
```

`OrderEmulator` and `ExecAlgorithm` are optional, activated by order parameters.

## RiskEngine

Every order passes through pre-trade checks (unless bypassed):

- Price precision correctness
- Positive prices (except options)
- Quantity precision compliance
- Maximum notional limits
- Quantity bounds verification
- Position reduction validation

Failed checks generate `OrderDenied` events.

### Trading State

| State | Behavior |
|-------|----------|
| `ACTIVE` | Normal operation |
| `HALTED` | No new orders processed |
| `REDUCING` | Only cancels or position-reducing orders |

```python
from nautilus_trader.config import RiskEngineConfig

risk_config = RiskEngineConfig(
    max_notional_per_order={"BINANCE": 100_000},
    max_order_submit_rate="10/00:00:01",  # 10 per second
    max_order_modify_rate="5/00:00:01",
)
```

## Order Emulator

Emulates complex order types locally when the venue doesn't support them natively:

- `STOP_MARKET` → emulated with market trigger
- `STOP_LIMIT` → emulated with limit trigger
- `TRAILING_STOP_MARKET` → emulated with trailing logic
- `MARKET_IF_TOUCHED` → emulated with touch trigger
- `LIMIT_IF_TOUCHED` → emulated with touch trigger

Orders with `emulation_trigger` parameter are held by the OrderEmulator until trigger conditions are met, then released as real orders.

```python
order = self.order_factory.stop_market(
    instrument_id=instrument_id,
    order_side=OrderSide.SELL,
    quantity=Quantity.from_int(1),
    trigger_price=Price.from_int(50000),
    trigger_type=TriggerType.LAST_PRICE,
    emulation_trigger=TriggerType.LAST_PRICE,  # emulate locally
)
```

## Execution Algorithms

Custom algorithms inherit from `ExecAlgorithm` (a type of `Actor`):

```python
from nautilus_trader.execution.algorithm import ExecAlgorithm

class MyAlgo(ExecAlgorithm):
    def on_order(self, order) -> None:
        # Split/schedule the primary order
        child = self.spawn_order(order)
        self.submit_order(child)
```

Capabilities:
- Request/subscribe to data
- Access Cache and Portfolio
- Set time alerts and timers
- Spawn secondary orders from primary orders

### TWAP (Time-Weighted Average Price)

Built-in algorithm that spreads orders evenly across a time horizon:

```python
from nautilus_trader.execution.algorithm import ExecAlgorithmSpecification

order = self.order_factory.market(
    instrument_id=instrument_id,
    order_side=OrderSide.BUY,
    quantity=Quantity.from_int(100),
    exec_algorithm_id=ExecAlgorithmId("TWAP"),
    exec_algorithm_params={
        "horizon_secs": 300,     # 5 minutes total
        "interval_secs": 30,     # order every 30 seconds
    },
)
```

First order submits immediately, final order at end of horizon.

### Spawned Orders

Child orders carry:
- `exec_spawn_id`: Parent order's `ClientOrderId`
- Naming: `{exec_spawn_id}-E{sequence}` (e.g., `O-20230404-001-000-E1`)

## Contingent Orders

### OTO (One-Triggers-Other)

Entry triggers dependent orders (stop-loss/take-profit):

```python
from nautilus_trader.model.orders import OrderList
from nautilus_trader.model.enums import ContingencyType

entry = self.order_factory.limit(...)
stop = self.order_factory.stop_market(..., reduce_only=True)
take = self.order_factory.limit(..., reduce_only=True)

order_list = OrderList(
    order_list_id=OrderListId("BRACKET-001"),
    orders=[entry, stop, take],
    contingency_type=ContingencyType.OTO,
)
self.submit_order_list(order_list)
```

### OCO (One-Cancels-Other)

When one fills/cancels, the other is automatically canceled:

```python
order_list = OrderList(
    order_list_id=OrderListId("OCO-001"),
    orders=[stop_loss, take_profit],
    contingency_type=ContingencyType.OCO,
)
```

### OUO (One-Updates-Other)

Linked bracket orders — filling one updates the other's quantity.

## Own Order Books

L3 books tracking your orders by price level:

- Monitor order states in real-time
- Validate placement by checking liquidity
- Prevent self-trading
- Support queue position strategies
- Reconcile venue vs. internal state

### Filtered Views

Subtract own orders from public book to reveal net liquidity:

```python
book = self.cache.order_book(instrument_id)
# filtered_view removes your orders from visible depth
```

## Overfills

Cumulative fill quantity exceeds original order quantity. Causes: duplicate fills, matching engine races, minimum lot constraints, DEX mechanics.

```python
from nautilus_trader.live.config import LiveExecEngineConfig

config = LiveExecEngineConfig(
    allow_overfills=True,  # default False — logs error and rejects
)
```

When `True`: logs warning, applies fill, tracks excess in `overfill_qty`.

## Duplicate Detection

`Order` model enforces one-time application per `trade_id`. ExecutionEngine checks `trade_id`, `order_side`, `last_px`, `last_qty`. Exact replays are skipped; differing fields trigger error.

## Safe Cancellation

Filter order status to exclude `PENDING_CANCEL` to avoid duplicate cancel attempts:

```python
open_orders = self.cache.orders_open(instrument_id=instrument_id)
for order in open_orders:
    if order.status != OrderStatus.PENDING_CANCEL:
        self.cancel_order(order)
```
