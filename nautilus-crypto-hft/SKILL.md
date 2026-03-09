---
name: nautilus-crypto-hft
description: >
  NautilusTrader for crypto HFT and market making. Triggers: "nautilus_trader",
  "NautilusTrader", "BacktestEngine", "BacktestNode", "TradingNode",
  "SimulatedExchange", "StrategyConfig", "ExecAlgorithm", "OrderEmulator",
  "DataEngine", "ExecutionEngine", "RiskEngine", "MessageBus", "NautilusKernel",
  "ParquetDataCatalog", "LiveDataClient", "LiveExecutionClient",
  "InstrumentProvider", "OrderBookDelta", "QuoteTick", "TradeTick", "BarType",
  "submit_order", "modify_order", "OmsType", "NETTING", "HEDGING",
  "venue adapter", "Binance adapter", "Bybit adapter", "dYdX adapter",
  "OKX adapter", "Tardis adapter", "Databento adapter", "Rust adapter",
  "PyO3 bindings nautilus", "nautilus crate", "nautilus FFI", "CVec nautilus",
  "maturin nautilus", "RecordFlag F_LAST", "OMS internals", "reconciliation",
  "order book delta processing", "L2 L3 order book", "market making nautilus",
  "HFT order book strategy", "microprice", "adverse selection", "VPIN",
  "breakeven spread", "anti-fingerprinting", "CryptoPerpetual", "CryptoFuture",
  "funding rate", "mark price", "liquidation", "fill model", "fee model",
  "latency model", "queue position", "custom adapter crypto".
---

# NautilusTrader — Crypto HFT

High-performance algorithmic trading platform. Hybrid Python/Rust/Cython architecture for backtesting and live deployment. Single-threaded event-driven kernel for determinism.

## Quick Start: Compact Market Maker

```python
from decimal import Decimal
from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import OrderBookDeltas
from nautilus_trader.model.enums import BookType, OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy

class MMConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    trade_size: Decimal
    max_size: Decimal = Decimal("10")
    half_spread: Decimal = Decimal("0.0005")  # must exceed breakeven
    skew_factor: Decimal = Decimal("0.5")

class MM(Strategy):
    def __init__(self, config: MMConfig) -> None:
        super().__init__(config)
        self.instrument = None
        self._bid_id = None
        self._ask_id = None

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.instrument_id)
        self.subscribe_order_book_deltas(
            self.config.instrument_id, book_type=BookType.L2_MBP,
        )

    def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
        book = self.cache.order_book(self.config.instrument_id)
        if not book.best_bid_price() or not book.best_ask_price():
            return
        # Microprice: volume-weighted mid
        bv = float(book.best_bid_size())
        av = float(book.best_ask_size())
        mid = (float(book.best_bid_price()) * av + float(book.best_ask_price()) * bv) / (bv + av)
        self._requote(Decimal(str(mid)))

    def _requote(self, mid: Decimal) -> None:
        pos = self.cache.position_for_instrument(self.config.instrument_id)
        skew = Decimal(0) if pos is None else -(pos.signed_qty / self.config.max_size) * self.config.skew_factor
        bid_px = self.instrument.make_price(mid * (1 - self.config.half_spread + skew))
        ask_px = self.instrument.make_price(mid * (1 + self.config.half_spread + skew))
        qty = self.instrument.make_qty(self.config.trade_size)

        # modify_order is primary — fewer messages, less fingerprinting
        bid_order = self.cache.order(self._bid_id) if self._bid_id else None
        ask_order = self.cache.order(self._ask_id) if self._ask_id else None

        if bid_order and bid_order.is_open:
            self.modify_order(bid_order, quantity=qty, price=bid_px)
        else:
            bid = self.order_factory.limit(
                instrument_id=self.config.instrument_id,
                order_side=OrderSide.BUY, quantity=qty, price=bid_px,
                time_in_force=TimeInForce.GTC, post_only=True,
            )
            self.submit_order(bid)
            self._bid_id = bid.client_order_id

        if ask_order and ask_order.is_open:
            self.modify_order(ask_order, quantity=qty, price=ask_px)
        else:
            ask = self.order_factory.limit(
                instrument_id=self.config.instrument_id,
                order_side=OrderSide.SELL, quantity=qty, price=ask_px,
                time_in_force=TimeInForce.GTC, post_only=True,
            )
            self.submit_order(ask)
            self._ask_id = ask.client_order_id

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.instrument_id)
        self.close_all_positions(self.config.instrument_id)
```

## Architecture

| Component | Role |
|-----------|------|
| `NautilusKernel` | Single-threaded core: lifecycle, clock, event sequencing |
| `MessageBus` | Pub/Sub + Req/Rep message routing across all components |
| `Cache` | In-memory store for instruments, orders, positions, books |
| `DataEngine` | Market data ingestion, buffering (F_LAST rule), distribution |
| `ExecutionEngine` | Order routing, OMS reconciliation, position tracking |
| `RiskEngine` | Pre-trade checks: precision, notional, reduce_only, rate limits |
| `Portfolio` | Real-time aggregated P&L, margin, balances across venues |

**Constraint**: One `TradingNode` / `BacktestNode` per process. Background threads for network I/O communicate via MessageBus channels.

## Strategy Lifecycle

| Method | When |
|--------|------|
| `on_start()` | Subscribe data, cache instrument, register indicators |
| `on_stop()` | Cancel orders, close positions, cleanup |
| `on_resume()` / `on_reset()` | State management between runs |
| `on_save() → dict[str, bytes]` | Persist custom state |
| `on_load(state)` | Restore custom state |

## Data Handlers

| Handler | Data Type |
|---------|-----------|
| `on_order_book_deltas(deltas)` | `OrderBookDeltas` — L2/L3 incremental updates |
| `on_order_book_depth(depth)` | `OrderBookDepth10` — aggregated top 10 levels |
| `on_quote_tick(tick)` | `QuoteTick` — best bid/ask with sizes |
| `on_trade_tick(tick)` | `TradeTick` — individual trade events |
| `on_bar(bar)` | `Bar` — OHLCV candles |
| `on_data(data)` | Custom data: `MarkPriceUpdate`, `FundingRateUpdate` |

## Execution Methods

```python
self.submit_order(order)           # new order to venue
self.modify_order(order, quantity, price, trigger_price)  # amend in-place (preferred)
self.cancel_order(order)           # cancel single
self.cancel_all_orders(instrument_id)  # cancel all for instrument
self.close_position(position)      # market close
self.close_all_positions(instrument_id)
```

## Order Book: L2 for Crypto

L2_MBP (market-by-price) is the ceiling for crypto HFT. L3_MBO is **not available** on crypto venues — it requires per-order-ID feeds only found on traditional exchanges (Databento MBO, ITCH).

**F_LAST rule**: Every delta batch must end with `RecordFlag.F_LAST`. Without it, DataEngine buffers indefinitely and subscribers starve.

```python
book = self.cache.order_book(instrument_id)
best_bid = book.best_bid_price()
best_ask = book.best_ask_price()
spread = best_ask - best_bid
bids = book.bids()  # list[BookLevel] sorted best→worst
asks = book.asks()
```

## Crypto HFT Essentials

**Breakeven spread**: `breakeven = taker_fee + maker_fee`. You must quote wider than this.

| Venue | Maker | Taker | Breakeven (bps) |
|-------|-------|-------|-----------------|
| Binance VIP0 | 2.0 bps | 5.0 bps | 7.0 |
| Bybit VIP0 | 2.0 bps | 5.5 bps | 7.5 |
| dYdX | 2.0 bps | 5.0 bps | 7.0 |
| OKX VIP0 | 2.0 bps | 5.0 bps | 7.0 |

**Rate limits**: Binance 2400 req/min REST, 10 orders/sec WS. Bybit 120 req/min per-endpoint. dYdX 100 orders/10s per-subaccount.

**Funding carrying cost**: For perps held >8h, `funding_payment = position_notional * funding_rate`. Factor into inventory cost.

**Order sizing**: Never exceed 5–10% of best level depth. Larger orders leak information and increase adverse selection.

**Anti-fingerprinting**: Randomize order sizes (±5%), vary requote intervals, use `modify_order` (not cancel+replace).

## OMS Quick Reference

- **NETTING**: One position per instrument. All fills aggregate. Standard for crypto perps.
- **HEDGING**: Multiple positions per instrument. Isolated P&L per trade.

Strategy `oms_type` can differ from venue. ExecutionEngine reconciles via virtual position IDs.

## Anti-Patterns

```python
# Float prices — precision errors. Use from_str or instrument.make_price
Price(1.23456)  # WRONG

# Blocking the event loop in live trading
time.sleep(5)  # blocks entire kernel

# Missing F_LAST on final delta — subscribers starve
flags = 0  # WRONG on final/only delta

# cancel_all + resubmit as MM pattern (use modify_order instead)

# No indicator initialization check
def on_bar(self, bar):  # check self.indicators_initialized() first

# Multiple TradingNode per process

# Not implementing reconciliation in LiveExecutionClient

# frozen_account confusion: False = margin checks ARE active (not disabled)
```

## Performance Checklist

- [ ] `modify_order` as primary MM requote method (not cancel+replace)?
- [ ] L2_MBP book type (not L3 which doesn't exist on crypto)?
- [ ] `RecordFlag.F_LAST` on final delta in every batch?
- [ ] `instrument.make_price()` / `make_qty()` for precision?
- [ ] Spread > breakeven (maker + taker fee)?
- [ ] Microprice (not simple mid) for fairer quotes?
- [ ] ts_event from exchange timestamps (not local clock)?
- [ ] Reconciliation methods implemented in all exec clients?
- [ ] Memory purge configured for long-running live sessions?
- [ ] Rust core for adapter HTTP/WS parsing in production?

## Reference Navigator

| Topic | File | When to Load |
|-------|------|--------------|
| Adverse selection, microprice, VPIN, fee optimization | [microstructure.md](references/microstructure.md) | Building MM or analyzing fill quality |
| Order book processing, delta protocol, own order book | [order_book.md](references/order_book.md) | Book-based strategies, adapter data client |
| Market making patterns, A-S model, spread methods | [market_making.md](references/market_making.md) | MM strategy development |
| BacktestEngine, BacktestNode, fill/fee/latency models | [backtesting_and_simulation.md](references/backtesting_and_simulation.md) | Backtesting and simulation setup |
| Order state machine, risk engine, exec algorithms | [execution_and_oms.md](references/execution_and_oms.md) | Execution flow, OMS internals |
| Mark price, funding, liquidation, circuit breakers | [derivatives.md](references/derivatives.md) | Perps/futures trading |
| Binance, Bybit, dYdX, OKX, Tardis, Databento | [exchange_adapters.md](references/exchange_adapters.md) | Venue-specific configuration |
| Python LiveDataClient, LiveExecutionClient | [adapter_development_python.md](references/adapter_development_python.md) | Building Python adapters |
| Rust crate structure, PyO3, HTTP/WS clients | [adapter_development_rust.md](references/adapter_development_rust.md) | Building Rust adapters |
| TradingNode, persistence, reconciliation, deployment | [live_trading.md](references/live_trading.md) | Live trading operations |
| Build system, testing, CI/CD, FFI contract | [dev_environment.md](references/dev_environment.md) | NautilusTrader development |

## Runnable Examples

| Example | File | Purpose |
|---------|------|---------|
| MM Backtest | [market_maker_backtest.py](examples/market_maker_backtest.py) | L2 backtest with TestInstrumentProvider, runs out of the box |
| Spread Capture Live | [spread_capture_live.py](examples/spread_capture_live.py) | TradingNode setup for live MM (needs API keys only) |
| Custom Adapter | [custom_adapter_minimal.py](examples/custom_adapter_minimal.py) | Combined data+exec adapter skeleton (~100 lines) |
