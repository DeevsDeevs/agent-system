"""
Multi-venue live test: Binance Futures + OKX in single TradingNode.
Validates: multi-venue data streaming, cross-venue cache, multi-instrument subscriptions.
"""
import sys
import os
import signal
from decimal import Decimal
from datetime import timedelta

sys.path.insert(0, os.path.dirname(__file__))

from conftest import get_env, TestReport
from nautilus_trader.adapters.binance import (
    BINANCE, BinanceAccountType, BinanceDataClientConfig,
    BinanceLiveDataClientFactory,
)
from nautilus_trader.adapters.okx import OKX, OKXDataClientConfig
from nautilus_trader.adapters.okx.factories import OKXLiveDataClientFactory
from nautilus_trader.config import (
    InstrumentProviderConfig, LiveExecEngineConfig, LoggingConfig,
    StrategyConfig, TradingNodeConfig,
)
from nautilus_trader.core.nautilus_pyo3 import OKXContractType, OKXInstrumentType
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.data import OrderBookDeltas, TradeTick, QuoteTick
from nautilus_trader.model.enums import BookType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.trading.strategy import Strategy

BN_INSTRUMENT = InstrumentId.from_str("BTCUSDT-PERP.BINANCE")
OKX_INSTRUMENT = InstrumentId.from_str("BTC-USDT-SWAP.OKX")
BN_PROVIDER = InstrumentProviderConfig(load_all=False, load_ids=frozenset({BN_INSTRUMENT}))
OKX_PROVIDER = InstrumentProviderConfig(load_all=False, load_ids=frozenset({OKX_INSTRUMENT}))


class MultiVenueConfig(StrategyConfig, frozen=True):
    data_phase_secs: int = 15
    max_run_secs: int = 30


class MultiVenueStrategy(Strategy):
    def __init__(self, config: MultiVenueConfig, report: TestReport) -> None:
        super().__init__(config)
        self.report = report
        self.counts = {
            "bn_deltas": 0, "bn_trades": 0, "bn_quotes": 0,
            "okx_deltas": 0, "okx_trades": 0, "okx_quotes": 0,
        }
        self._done = False

    def on_start(self) -> None:
        print("[MULTI] on_start", flush=True)
        instruments = self.cache.instruments()
        self.report.instruments_loaded = len(instruments)
        self.report.sample_instruments = [str(i.id) for i in instruments]
        print(f"[MULTI] Instruments loaded: {[str(i.id) for i in instruments]}", flush=True)

        bn_inst = self.cache.instrument(BN_INSTRUMENT)
        okx_inst = self.cache.instrument(OKX_INSTRUMENT)

        if bn_inst:
            self.subscribe_order_book_deltas(BN_INSTRUMENT, book_type=BookType.L2_MBP)
            self.subscribe_trade_ticks(BN_INSTRUMENT)
            self.subscribe_quote_ticks(BN_INSTRUMENT)
            self.report.phase_ok("binance_instrument", f"{BN_INSTRUMENT} found")
        else:
            self.report.phase_fail("binance_instrument", f"{BN_INSTRUMENT} not found")

        if okx_inst:
            self.subscribe_order_book_deltas(OKX_INSTRUMENT, book_type=BookType.L2_MBP)
            self.subscribe_trade_ticks(OKX_INSTRUMENT)
            self.subscribe_quote_ticks(OKX_INSTRUMENT)
            self.report.phase_ok("okx_instrument", f"{OKX_INSTRUMENT} found")
        else:
            self.report.phase_fail("okx_instrument", f"{OKX_INSTRUMENT} not found")

        self.clock.set_timer("data_summary", interval=timedelta(seconds=self.config.data_phase_secs),
                             callback=self._on_data_summary)
        self.clock.set_timer("hard_stop", interval=timedelta(seconds=self.config.max_run_secs),
                             callback=self._on_hard_stop)

    def _on_data_summary(self, event) -> None:
        if self._done:
            return
        self._done = True
        self.clock.cancel_timer("data_summary")
        print(f"[MULTI] Data counts: {self.counts}", flush=True)
        self.report.data_counts = self.counts

        bn_total = self.counts["bn_deltas"] + self.counts["bn_trades"] + self.counts["bn_quotes"]
        okx_total = self.counts["okx_deltas"] + self.counts["okx_trades"] + self.counts["okx_quotes"]

        if bn_total > 0:
            self.report.phase_ok("binance_data", f"deltas={self.counts['bn_deltas']}, trades={self.counts['bn_trades']}, quotes={self.counts['bn_quotes']}")
        else:
            self.report.phase_fail("binance_data", "No data received")

        if okx_total > 0:
            self.report.phase_ok("okx_data", f"deltas={self.counts['okx_deltas']}, trades={self.counts['okx_trades']}, quotes={self.counts['okx_quotes']}")
        else:
            self.report.phase_fail("okx_data", "No data received")

        # Cross-venue cache check
        bn_book = self.cache.order_book(BN_INSTRUMENT)
        okx_book = self.cache.order_book(OKX_INSTRUMENT)
        bn_bid = float(bn_book.best_bid_price()) if bn_book and bn_book.best_bid_price() else None
        okx_bid = float(okx_book.best_bid_price()) if okx_book and okx_book.best_bid_price() else None
        if bn_bid and okx_bid:
            spread_bps = abs(bn_bid - okx_bid) / ((bn_bid + okx_bid) / 2) * 10000
            self.report.phase_ok("cross_venue_books", f"BN bid={bn_bid:.2f}, OKX bid={okx_bid:.2f}, diff={spread_bps:.1f}bps")
        else:
            self.report.phase_fail("cross_venue_books", f"BN bid={bn_bid}, OKX bid={okx_bid}")

        self.report.save()
        self.clock.set_time_alert("kill", alert_time=self.clock.utc_now() + timedelta(seconds=2),
                                  callback=lambda _: os.kill(os.getpid(), signal.SIGINT))

    def _on_hard_stop(self, event) -> None:
        self.clock.cancel_timer("hard_stop")
        if not self._done:
            self._on_data_summary(event)

    def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
        if deltas.instrument_id == BN_INSTRUMENT:
            self.counts["bn_deltas"] += 1
        elif deltas.instrument_id == OKX_INSTRUMENT:
            self.counts["okx_deltas"] += 1

    def on_trade_tick(self, tick: TradeTick) -> None:
        if tick.instrument_id == BN_INSTRUMENT:
            self.counts["bn_trades"] += 1
        elif tick.instrument_id == OKX_INSTRUMENT:
            self.counts["okx_trades"] += 1

    def on_quote_tick(self, tick: QuoteTick) -> None:
        if tick.instrument_id == BN_INSTRUMENT:
            self.counts["bn_quotes"] += 1
        elif tick.instrument_id == OKX_INSTRUMENT:
            self.counts["okx_quotes"] += 1

    def on_stop(self) -> None:
        pass


def main():
    report = TestReport("MULTI_VENUE")
    try:
        bn_key = get_env("BINANCE_LINEAR_API_KEY")
        bn_secret = get_env("BINANCE_LINEAR_API_SECRET")
        okx_key = get_env("OKX_API_KEY")
        okx_secret = get_env("OKX_API_SECRET")
        okx_pass = get_env("OKX_API_PASSPHRASE")
    except EnvironmentError as e:
        report.phase_fail("credentials", str(e))
        report.save()
        return
    report.phase_ok("credentials", "Both venues keyed")

    config = TradingNodeConfig(
        trader_id="TEST-MULTI-001",
        logging=LoggingConfig(log_level="INFO"),
        exec_engine=LiveExecEngineConfig(reconciliation=False),
        data_clients={
            BINANCE: BinanceDataClientConfig(
                api_key=bn_key, api_secret=bn_secret,
                account_type=BinanceAccountType.USDT_FUTURES,
                instrument_provider=BN_PROVIDER,
            ),
            OKX: OKXDataClientConfig(
                api_key=okx_key, api_secret=okx_secret, api_passphrase=okx_pass,
                instrument_types=(OKXInstrumentType.SWAP,),
                contract_types=(OKXContractType.LINEAR,),
                instrument_provider=OKX_PROVIDER,
                is_demo=False,
            ),
        },
        exec_clients={},
        timeout_connection=25.0, timeout_reconciliation=5.0,
        timeout_portfolio=5.0, timeout_disconnection=3.0, timeout_post_stop=2.0,
    )

    node = TradingNode(config=config)
    node.add_data_client_factory(BINANCE, BinanceLiveDataClientFactory)
    node.add_data_client_factory(OKX, OKXLiveDataClientFactory)

    strategy = MultiVenueStrategy(MultiVenueConfig(), report=report)
    node.trader.add_strategy(strategy)
    node.build()
    report.phase_ok("node_build", "Multi-venue node built")

    try:
        node.run()
    except KeyboardInterrupt:
        node.stop()
    except Exception as e:
        report.phase_fail("runtime", str(e))
        report.save()


if __name__ == "__main__":
    main()
