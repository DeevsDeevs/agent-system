import os
import signal
from decimal import Decimal
from datetime import timedelta

from nautilus_trader.config import StrategyConfig
from nautilus_trader.model.data import OrderBookDeltas, TradeTick, QuoteTick, Bar, BarType
from nautilus_trader.model.enums import BookType, OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy

from conftest import TestReport


class VenueTestConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId
    data_phase_secs: int = 10
    max_run_secs: int = 25
    order_offset_pct: Decimal = Decimal("0.20")
    supports_modify: bool = True


class VenueTestStrategy(Strategy):
    def __init__(self, config: VenueTestConfig, report: TestReport) -> None:
        super().__init__(config)
        self.report = report
        self.instrument = None
        self._test_order_id = None
        self._order_accepted = False
        self._order_modified = False
        self._order_canceled = False
        self._order_phase_done = False
        self._data_phase_done = False

    def on_start(self) -> None:
        print(f"[STRATEGY] on_start: {self.config.instrument_id}", flush=True)
        self.instrument = self.cache.instrument(self.config.instrument_id)
        if self.instrument is None:
            self.report.phase_fail("instruments", f"Not found: {self.config.instrument_id}")
            self.report.save()
            self._kill_process(2)
            return

        instruments = self.cache.instruments()
        self.report.instruments_loaded = len(instruments)
        self.report.sample_instruments = [str(i.id) for i in instruments[:5]]
        self.report.phase_ok("instruments", f"{len(instruments)} loaded, target found")
        print(f"[STRATEGY] Instruments: {len(instruments)}", flush=True)

        self.subscribe_order_book_deltas(self.config.instrument_id, book_type=BookType.L2_MBP)
        self.subscribe_trade_ticks(self.config.instrument_id)
        self.subscribe_quote_ticks(self.config.instrument_id)
        bar_type = BarType.from_str(f"{self.config.instrument_id}-1-MINUTE-LAST-EXTERNAL")
        self.subscribe_bars(bar_type)

        # Use callbacks instead of on_timer (which doesn't exist on Strategy)
        self.clock.set_timer(
            "order_phase",
            interval=timedelta(seconds=self.config.data_phase_secs),
            callback=self._on_order_phase,
        )
        self.clock.set_timer(
            "hard_stop",
            interval=timedelta(seconds=self.config.max_run_secs),
            callback=self._on_hard_stop,
        )

    def _on_order_phase(self, event) -> None:
        if self._data_phase_done:
            return
        self._data_phase_done = True
        self.clock.cancel_timer("order_phase")
        self._log_data_summary()
        self._run_order_test()

    def _on_hard_stop(self, event) -> None:
        self.clock.cancel_timer("hard_stop")
        print("[STRATEGY] Hard stop triggered", flush=True)
        self._finalize_and_exit()

    def _log_data_summary(self):
        c = self.report.data_counts
        total = sum(c.values())
        print(f"[STRATEGY] Data summary: {c} (total={total})", flush=True)
        if total > 0:
            self.report.phase_ok("data_streaming", f"{c}")
        else:
            self.report.phase_fail("data_streaming", "No data received")

    def _run_order_test(self):
        print("[STRATEGY] Order test starting", flush=True)
        accounts = self.cache.accounts()
        if accounts:
            for acc in accounts:
                bals = acc.balances()
                if bals:
                    self.report.balance = ", ".join(f"{b.currency}: {b.total}" for b in bals.values())
                    print(f"[STRATEGY] Balance: {self.report.balance}", flush=True)
                    break

        book = self.cache.order_book(self.config.instrument_id)
        best_bid = book.best_bid_price() if book else None
        if not best_bid:
            quotes = self.cache.quote_ticks(self.config.instrument_id)
            if quotes:
                best_bid = quotes[0].bid_price
        if not best_bid:
            self.report.phase_fail("order_lifecycle", "No bid price available")
            print("[STRATEGY] No bid price, skipping order test", flush=True)
            return

        offset_price = self.instrument.make_price(
            Decimal(str(float(best_bid) * (1 - float(self.config.order_offset_pct))))
        )
        qty = self.instrument.make_qty(self.instrument.size_increment * 10)
        print(f"[STRATEGY] LIMIT BUY @ {offset_price} qty={qty} (bid={best_bid})", flush=True)

        order = self.order_factory.limit(
            instrument_id=self.config.instrument_id,
            order_side=OrderSide.BUY,
            quantity=qty,
            price=offset_price,
            time_in_force=TimeInForce.GTC,
            post_only=True,
        )
        self._test_order_id = order.client_order_id
        self.submit_order(order)

    def on_order_accepted(self, event) -> None:
        if self._test_order_id and event.client_order_id == self._test_order_id:
            self._order_accepted = True
            self.report.order_events.append(f"ACCEPTED:{event.venue_order_id}")
            print(f"[STRATEGY] Order ACCEPTED: {event.venue_order_id}", flush=True)
            if self.config.supports_modify:
                order = self.cache.order(self._test_order_id)
                if order and order.is_open:
                    new_price = self.instrument.make_price(Decimal(str(float(order.price) * 0.99)))
                    self.modify_order(order, price=new_price)
            else:
                self._cancel_test_order()

    def on_order_updated(self, event) -> None:
        if self._test_order_id and event.client_order_id == self._test_order_id:
            self._order_modified = True
            self.report.order_events.append(f"UPDATED:{event.price}")
            print(f"[STRATEGY] Order UPDATED: {event.price}", flush=True)
            self._cancel_test_order()

    def on_order_modify_rejected(self, event) -> None:
        if self._test_order_id and event.client_order_id == self._test_order_id:
            self.report.order_events.append(f"MODIFY_REJECTED:{event.reason}")
            print(f"[STRATEGY] Modify REJECTED: {event.reason}", flush=True)
            self._cancel_test_order()

    def on_order_canceled(self, event) -> None:
        if self._test_order_id and event.client_order_id == self._test_order_id:
            self._order_canceled = True
            self.report.order_events.append("CANCELED")
            detail = "accepted"
            if self.config.supports_modify and self._order_modified:
                detail += "→modified"
            detail += "→canceled"
            self.report.phase_ok("order_lifecycle", detail)
            print(f"[STRATEGY] Order CANCELED. Lifecycle: {detail}", flush=True)
            self._finalize_and_exit()

    def on_order_rejected(self, event) -> None:
        if self._test_order_id and event.client_order_id == self._test_order_id:
            self.report.order_events.append(f"REJECTED:{event.reason}")
            self.report.phase_fail("order_lifecycle", f"Rejected: {event.reason}")
            print(f"[STRATEGY] Order REJECTED: {event.reason}", flush=True)
            self._finalize_and_exit()

    def on_order_denied(self, event) -> None:
        if self._test_order_id and event.client_order_id == self._test_order_id:
            self.report.order_events.append(f"DENIED:{event.reason}")
            self.report.phase_fail("order_lifecycle", f"Denied: {event.reason}")
            print(f"[STRATEGY] Order DENIED: {event.reason}", flush=True)

    def on_order_cancel_rejected(self, event) -> None:
        if self._test_order_id and event.client_order_id == self._test_order_id:
            self.report.order_events.append(f"CANCEL_REJECTED:{event.reason}")
            print(f"[STRATEGY] Cancel REJECTED: {event.reason}", flush=True)

    def _cancel_test_order(self):
        order = self.cache.order(self._test_order_id)
        if order and order.is_open:
            self.cancel_order(order)

    def _finalize_and_exit(self):
        if self._order_phase_done:
            return
        self._order_phase_done = True
        print("[STRATEGY] Finalizing...", flush=True)
        if not self._data_phase_done:
            self._log_data_summary()
        try:
            self.cancel_all_orders(self.config.instrument_id)
            self.close_all_positions(self.config.instrument_id)
        except Exception as e:
            print(f"[STRATEGY] Cleanup error: {e}", flush=True)
        self.report.save()
        self._kill_process(2)

    def _kill_process(self, secs: float):
        self.clock.set_time_alert(
            "kill",
            alert_time=self.clock.utc_now() + timedelta(seconds=secs),
            callback=lambda _: os.kill(os.getpid(), signal.SIGINT),
        )

    def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
        self.report.data_counts["order_book_deltas"] += 1

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.report.data_counts["trade_ticks"] += 1

    def on_quote_tick(self, tick: QuoteTick) -> None:
        self.report.data_counts["quote_ticks"] += 1

    def on_bar(self, bar: Bar) -> None:
        self.report.data_counts["bars"] += 1

    def on_data(self, data) -> None:
        self.report.data_counts["custom_data"] += 1

    def on_stop(self) -> None:
        try:
            self.cancel_all_orders(self.config.instrument_id)
            self.close_all_positions(self.config.instrument_id)
        except Exception:
            pass
