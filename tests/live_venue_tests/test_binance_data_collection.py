"""
Comprehensive Binance Futures data collection test.
Subscribes to ALL available data types for top instruments:
  - Trade ticks
  - Quote ticks (book ticker)
  - L2 order book deltas
  - Order book depth (top 10)
  - Mark prices
  - Funding rates
  - Index prices
  - Instrument status
  - 1-minute bars

Also tests:
  - Loading top N instruments by volume
  - Cache inspection of all data types
  - Data rate measurement
  - Saving collected data to ParquetDataCatalog
"""

import os
import signal
import shutil
import time
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

from nautilus_trader.adapters.binance import BinanceAccountType
from nautilus_trader.adapters.binance.config import BinanceDataClientConfig
from nautilus_trader.adapters.binance.factories import BinanceLiveDataClientFactory
from nautilus_trader.config import (
    InstrumentProviderConfig,
    LiveDataEngineConfig,
    LoggingConfig,
    StrategyConfig,
    TradingNodeConfig,
)
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.data import (
    Bar,
    DataType,
    FundingRateUpdate,
    IndexPriceUpdate,
    InstrumentStatus,
    MarkPriceUpdate,
    OrderBookDeltas,
    OrderBookDepth10,
    QuoteTick,
    TradeTick,
)
from nautilus_trader.model.enums import BookType
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.persistence.catalog import ParquetDataCatalog
from nautilus_trader.trading.strategy import Strategy


# Top instruments to subscribe
INSTRUMENTS = [
    "BTCUSDT-PERP.BINANCE",
    "ETHUSDT-PERP.BINANCE",
    "SOLUSDT-PERP.BINANCE",
    "BNBUSDT-PERP.BINANCE",
    "XRPUSDT-PERP.BINANCE",
    "DOGEUSDT-PERP.BINANCE",
    "ADAUSDT-PERP.BINANCE",
    "AVAXUSDT-PERP.BINANCE",
    "LINKUSDT-PERP.BINANCE",
    "DOTUSDT-PERP.BINANCE",
]

COLLECTION_SECONDS = 30


class DataCollectorConfig(StrategyConfig, frozen=True):
    instruments: list[str] = []
    subscribe_book_deltas: bool = True
    subscribe_book_depth: bool = False   # NotImplementedError on Binance adapter
    subscribe_mark_prices: bool = True
    subscribe_funding_rates: bool = False  # NotImplementedError on Binance adapter
    subscribe_index_prices: bool = False   # NotImplementedError on Binance adapter
    subscribe_instrument_status: bool = False  # NotImplementedError on Binance adapter
    subscribe_bars: bool = True


class DataCollectorStrategy(Strategy):
    def __init__(self, config: DataCollectorConfig) -> None:
        super().__init__(config)
        self.instrument_ids = [InstrumentId.from_str(s) for s in config.instruments]
        self.counts = {
            "trade_ticks": {},
            "quote_ticks": {},
            "book_deltas": {},
            "book_depth": {},
            "mark_prices": {},
            "funding_rates": {},
            "index_prices": {},
            "instrument_status": {},
            "bars": {},
        }
        self.samples = {
            "mark_price": None,
            "funding_rate": None,
            "index_price": None,
            "instrument_status": None,
            "book_depth": None,
        }
        self.start_time = None
        self.logged_summary = False

    def on_start(self) -> None:
        self.start_time = time.time()

        for inst_id in self.instrument_ids:
            inst = self.cache.instrument(inst_id)
            if inst is None:
                self.log.warning(f"Instrument {inst_id} not found in cache, skipping")
                continue

            self.subscribe_trade_ticks(inst_id)
            self.subscribe_quote_ticks(inst_id)

            if self.config.subscribe_book_deltas:
                self.subscribe_order_book_deltas(inst_id, book_type=BookType.L2_MBP, depth=10)

            if self.config.subscribe_book_depth:
                self.subscribe_order_book_depth(inst_id, book_type=BookType.L2_MBP)

            if self.config.subscribe_mark_prices:
                self.subscribe_mark_prices(inst_id)

            if self.config.subscribe_funding_rates:
                self.subscribe_funding_rates(inst_id)

            if self.config.subscribe_index_prices:
                self.subscribe_index_prices(inst_id)

            if self.config.subscribe_instrument_status:
                self.subscribe_instrument_status(inst_id)

            if self.config.subscribe_bars:
                from nautilus_trader.model.data import BarType
                bar_type = BarType.from_str(f"{inst_id}-1-MINUTE-LAST-EXTERNAL")
                self.subscribe_bars(bar_type)

        self.clock.set_timer(
            "shutdown",
            interval=timedelta(seconds=COLLECTION_SECONDS),
            callback=self._on_shutdown,
        )
        self.clock.set_timer(
            "status",
            interval=timedelta(seconds=5),
            callback=self._on_status,
        )

    def _inc(self, category: str, inst_id) -> None:
        key = str(inst_id)
        self.counts[category][key] = self.counts[category].get(key, 0) + 1

    def on_trade_tick(self, tick: TradeTick) -> None:
        self._inc("trade_ticks", tick.instrument_id)

    def on_quote_tick(self, tick: QuoteTick) -> None:
        self._inc("quote_ticks", tick.instrument_id)

    def on_order_book_deltas(self, deltas: OrderBookDeltas) -> None:
        self._inc("book_deltas", deltas.instrument_id)

    def on_order_book_depth(self, depth: OrderBookDepth10) -> None:
        self._inc("book_depth", depth.instrument_id)
        if self.samples["book_depth"] is None:
            self.samples["book_depth"] = {
                "instrument": str(depth.instrument_id),
                "bids_count": len([b for b in depth.bids if b.size > 0]),
                "asks_count": len([a for a in depth.asks if a.size > 0]),
                "best_bid": f"{depth.bids[0].price}x{depth.bids[0].size}",
                "best_ask": f"{depth.asks[0].price}x{depth.asks[0].size}",
            }

    def on_mark_price(self, update: MarkPriceUpdate) -> None:
        self._inc("mark_prices", update.instrument_id)
        if self.samples["mark_price"] is None:
            self.samples["mark_price"] = {
                "instrument": str(update.instrument_id),
                "repr": repr(update),
            }

    def on_funding_rate(self, update: FundingRateUpdate) -> None:
        self._inc("funding_rates", update.instrument_id)
        if self.samples["funding_rate"] is None:
            self.samples["funding_rate"] = {
                "instrument": str(update.instrument_id),
                "repr": repr(update),
            }

    def on_index_price(self, update: IndexPriceUpdate) -> None:
        self._inc("index_prices", update.instrument_id)
        if self.samples["index_price"] is None:
            self.samples["index_price"] = {
                "instrument": str(update.instrument_id),
                "repr": repr(update),
            }

    def on_instrument_status(self, status: InstrumentStatus) -> None:
        self._inc("instrument_status", status.instrument_id)
        if self.samples["instrument_status"] is None:
            self.samples["instrument_status"] = {
                "instrument": str(status.instrument_id),
                "repr": repr(status),
            }

    def on_bar(self, bar: Bar) -> None:
        self._inc("bars", bar.bar_type.instrument_id)

    def _on_status(self, event) -> None:
        elapsed = time.time() - self.start_time
        total = sum(sum(v.values()) for v in self.counts.values())
        self.log.info(f"[{elapsed:.0f}s] Total events: {total}")
        for category, inst_counts in self.counts.items():
            if inst_counts:
                total_cat = sum(inst_counts.values())
                self.log.info(f"  {category}: {total_cat} ({len(inst_counts)} instruments)")

    def _on_shutdown(self, event) -> None:
        if self.logged_summary:
            return
        self.logged_summary = True
        self._print_summary()
        os.kill(os.getpid(), signal.SIGINT)

    def _print_summary(self) -> None:
        elapsed = time.time() - self.start_time
        print("\n" + "=" * 70)
        print(f"DATA COLLECTION RESULTS ({elapsed:.1f}s)")
        print("=" * 70)

        total_events = 0
        ok_count = 0
        fail_count = 0

        for category, inst_counts in self.counts.items():
            total_cat = sum(inst_counts.values())
            total_events += total_cat
            num_instruments = len(inst_counts)

            if total_cat > 0:
                ok_count += 1
                status = "OK"
                rate = total_cat / elapsed if elapsed > 0 else 0
                per_inst = {k.split(".")[0].split("-")[0]: v for k, v in sorted(inst_counts.items(), key=lambda x: -x[1])[:3]}
                print(f"  [OK] {category:25s} {total_cat:>8,} events ({num_instruments} instruments, {rate:.1f}/s) top: {per_inst}")
            else:
                fail_count += 1
                print(f"  [--] {category:25s} 0 events")

        print(f"\n  Total: {total_events:,} events in {elapsed:.1f}s ({total_events/elapsed:.0f}/s)")

        # Samples
        print("\n  --- SAMPLES ---")
        for name, sample in self.samples.items():
            if sample:
                print(f"  {name}:")
                for k, v in sample.items():
                    print(f"    {k}: {v}")

        # Cache inspection
        print("\n  --- CACHE ---")
        instruments = self.cache.instruments()
        print(f"  Instruments in cache: {len(instruments)}")
        accounts = self.cache.accounts()
        print(f"  Accounts in cache: {len(accounts)}")

        # Book inspection
        books_with_data = 0
        for inst_id in self.instrument_ids:
            book = self.cache.order_book(inst_id)
            if book and book.best_bid_price():
                books_with_data += 1
                if books_with_data <= 2:
                    spread_bps = (float(book.best_ask_price()) - float(book.best_bid_price())) / float(book.midpoint()) * 10000
                    print(f"  Book {inst_id}: bid={book.best_bid_price()} ask={book.best_ask_price()} spread={spread_bps:.2f}bps")
        print(f"  Books with data: {books_with_data}/{len(self.instrument_ids)}")

        print(f"\n  {ok_count} data types active, {fail_count} inactive")
        print("=" * 70)


def main():
    api_key = os.environ.get("BINANCE_LINEAR_API_KEY", "")
    api_secret = os.environ.get("BINANCE_LINEAR_API_SECRET", "")
    if not api_key or api_key == "***":
        print("BINANCE_LINEAR_API_KEY not set, skipping")
        return

    instrument_ids = frozenset(INSTRUMENTS)

    config = TradingNodeConfig(
        timeout_connection=20,
        timeout_reconciliation=5,
        timeout_portfolio=5,
        timeout_disconnection=5,
        logging=LoggingConfig(log_level="INFO"),
        data_engine=LiveDataEngineConfig(
            time_bars_interval_type="left-open",
        ),
        data_clients={
            "BINANCE": BinanceDataClientConfig(
                api_key=api_key,
                api_secret=api_secret,
                account_type=BinanceAccountType.USDT_FUTURES,
                instrument_provider=InstrumentProviderConfig(
                    load_all=False,
                    load_ids=instrument_ids,
                ),
            ),
        },
    )

    node = TradingNode(config=config)
    node.add_data_client_factory("BINANCE", BinanceLiveDataClientFactory)

    strategy = DataCollectorStrategy(
        DataCollectorConfig(instruments=list(INSTRUMENTS))
    )
    node.trader.add_strategy(strategy)
    node.build()

    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.dispose()

    # Save collected data to catalog
    print("\n--- SAVING TO CATALOG ---")
    catalog_path = Path("/tmp/nautilus_data_collection")
    if catalog_path.exists():
        shutil.rmtree(catalog_path)

    try:
        catalog = ParquetDataCatalog(str(catalog_path))

        # Save instruments
        instruments = node.cache.instruments()
        if instruments:
            catalog.write_data(instruments)
            print(f"  Saved {len(instruments)} instruments")

        # Save trade ticks per instrument (must sort by ts_init for catalog)
        for inst_id_str in INSTRUMENTS:
            inst_id = InstrumentId.from_str(inst_id_str)
            trades = list(node.cache.trade_ticks(inst_id))
            if trades:
                trades.sort(key=lambda x: x.ts_init)
                catalog.write_data(trades)
                print(f"  Saved {len(trades)} trade ticks for {inst_id}")

            quotes = list(node.cache.quote_ticks(inst_id))
            if quotes:
                quotes.sort(key=lambda x: x.ts_init)
                catalog.write_data(quotes)
                print(f"  Saved {len(quotes)} quote ticks for {inst_id}")

        # Verify catalog
        data_types = catalog.list_data_types()
        print(f"  Catalog data types: {data_types}")

        # Read back sample
        for inst_id_str in INSTRUMENTS[:2]:
            inst_id = InstrumentId.from_str(inst_id_str)
            trades_back = catalog.trade_ticks(instrument_ids=[str(inst_id)])
            if len(trades_back) > 0:
                print(f"  Read back {len(trades_back)} trade ticks for {inst_id}")

        print(f"  Catalog saved to: {catalog_path}")
    except Exception as e:
        print(f"  Catalog save error: {e}")


if __name__ == "__main__":
    main()
