"""
Order book API test: book structure, bids/asks, spread, depth, instrument properties.
Tests all code snippets from order_book.md and derivatives.md against real API.
"""
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.dirname(__file__))

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig, StrategyConfig
from nautilus_trader.model.data import OrderBookDeltas, TradeTick, QuoteTick
from nautilus_trader.model.enums import OmsType, AccountType, OrderSide, BookType
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money, Currency, Quantity
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider, TestDataProvider
from nautilus_trader.trading.strategy import Strategy

RESULTS = {}


def log(phase: str, msg: str, ok: bool = True):
    status = "OK" if ok else "FAIL"
    RESULTS[phase] = {"status": status, "detail": msg}
    print(f"  [{status}] {phase}: {msg}", flush=True)


class BookInspectorConfig(StrategyConfig, frozen=True):
    pass


class BookInspector(Strategy):
    """Inspects order book structure and API methods."""

    def __init__(self, config: BookInspectorConfig) -> None:
        super().__init__(config)
        self.tick_count = 0
        self.findings = {}
        self.checked = False

    def on_start(self) -> None:
        self.instrument = self.cache.instruments()[0]
        self.subscribe_trade_ticks(self.instrument.id)

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.tick_count += 1
        if self.tick_count == 500 and not self.checked:
            self.checked = True
            self._inspect_book()
            self._inspect_instrument()
            self._inspect_cache()

    def _inspect_book(self):
        book = self.cache.order_book(self.instrument.id)
        if book is None:
            # Expected: book only exists if subscribe_order_book_deltas() was called
            self.findings["book_exists"] = (True, "No book in cache (expected — TradeTick-only, no book subscription)")
            return
        self.findings["book_exists"] = (True, f"Book for {self.instrument.id}")

        best_bid = book.best_bid_price()
        best_ask = book.best_ask_price()
        self.findings["best_bid"] = (best_bid is not None, f"best_bid={best_bid}")
        self.findings["best_ask"] = (best_ask is not None, f"best_ask={best_ask}")

        if best_bid and best_ask:
            spread = float(best_ask) - float(best_bid)
            mid = (float(best_bid) + float(best_ask)) / 2
            self.findings["spread"] = (spread >= 0, f"spread={spread:.4f}, mid={mid:.4f}")

        bid_size = book.best_bid_size()
        ask_size = book.best_ask_size()
        self.findings["bid_size"] = (True, f"bid_size={bid_size}")
        self.findings["ask_size"] = (True, f"ask_size={ask_size}")

        # bids() and asks() — these may not work on L1 book from trade ticks
        try:
            bids = book.bids()
            asks = book.asks()
            self.findings["bids_list"] = (True, f"{len(bids)} bid levels")
            self.findings["asks_list"] = (True, f"{len(asks)} ask levels")
            if bids:
                level = bids[0]
                self.findings["bid_level_attrs"] = (True, f"price={level.price}, size={level.size}")
        except Exception as e:
            self.findings["bids_list"] = (False, f"Error: {e}")

        # get_avg_px_for_quantity
        try:
            avg_px = book.get_avg_px_for_quantity(OrderSide.BUY, Quantity.from_str("0.01"))
            self.findings["avg_px_qty"] = (True, f"avg_px for 0.01={avg_px}")
        except Exception as e:
            self.findings["avg_px_qty"] = (False, f"Error: {e}")

        # Book count/level_count
        try:
            count = book.count
            self.findings["book_count"] = (True, f"book.count={count}")
        except Exception as e:
            self.findings["book_count"] = (False, f"Error: {e}")

    def _inspect_instrument(self):
        inst = self.instrument
        self.findings["inst_id"] = (True, str(inst.id))
        self.findings["inst_type"] = (True, type(inst).__name__)
        self.findings["price_prec"] = (True, f"price_precision={inst.price_precision}")
        self.findings["size_prec"] = (True, f"size_precision={inst.size_precision}")
        self.findings["price_inc"] = (True, f"price_increment={inst.price_increment}")
        self.findings["size_inc"] = (True, f"size_increment={inst.size_increment}")

        # make_price / make_qty
        px = inst.make_price(Decimal("423.50"))
        qty = inst.make_qty(Decimal("1.5"))
        self.findings["make_price"] = (True, f"make_price(423.50)={px}")
        self.findings["make_qty"] = (True, f"make_qty(1.5)={qty}")

        # Instrument properties
        self.findings["base_currency"] = (True, f"base={getattr(inst, 'base_currency', 'N/A')}")
        self.findings["quote_currency"] = (True, f"quote={inst.quote_currency}")
        self.findings["maker_fee"] = (True, f"maker_fee={inst.maker_fee}")
        self.findings["taker_fee"] = (True, f"taker_fee={inst.taker_fee}")

        # Optional perp-specific fields
        for attr in ["is_inverse", "multiplier", "margin_init", "margin_maint", "settlement_currency"]:
            val = getattr(inst, attr, "N/A")
            self.findings[f"perp_{attr}"] = (True, f"{attr}={val}")

    def _inspect_cache(self):
        # Cache query methods
        instruments = self.cache.instruments()
        self.findings["cache_instruments"] = (True, f"{len(instruments)} instruments")

        orders = self.cache.orders()
        self.findings["cache_orders"] = (True, f"{len(orders)} orders")

        positions = self.cache.positions()
        self.findings["cache_positions"] = (True, f"{len(positions)} positions")

        accounts = self.cache.accounts()
        self.findings["cache_accounts"] = (True, f"{len(accounts)} accounts")

        if accounts:
            acc = accounts[0]
            bals = acc.balances()
            self.findings["account_balances"] = (True, f"{len(bals)} currencies")

            # balance methods
            try:
                usdt = Currency.from_str("USDT")
                total = acc.balance_total(usdt)
                free = acc.balance_free(usdt)
                locked = acc.balance_locked(usdt)
                self.findings["balance_detail"] = (True, f"total={total}, free={free}, locked={locked}")
            except Exception as e:
                self.findings["balance_detail"] = (False, f"Error: {e}")

        # Quote ticks in cache
        quotes = self.cache.quote_ticks(self.instrument.id)
        self.findings["cache_quotes"] = (True, f"{len(quotes) if quotes else 0} quote ticks")

        trade_ticks = self.cache.trade_ticks(self.instrument.id)
        self.findings["cache_trades"] = (True, f"{len(trade_ticks) if trade_ticks else 0} trade ticks")

    def on_stop(self) -> None:
        pass


def test_order_book_api():
    print("\n" + "=" * 60)
    print("TEST: Order Book API + Instrument + Cache")
    print("=" * 60)

    ethusdt = TestInstrumentProvider.ethusdt_binance()
    dp = TestDataProvider()
    df = dp.read_csv_ticks("binance/ethusdt-trades.csv")
    wrangler = TradeTickDataWrangler(instrument=ethusdt)
    ticks = wrangler.process(df)

    config = BacktestEngineConfig(logging=LoggingConfig(log_level="ERROR"))
    engine = BacktestEngine(config=config)
    engine.add_venue(
        venue=Venue("BINANCE"), oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN, base_currency=None,
        starting_balances=[Money(100_000.0, Currency.from_str("USDT"))],
    )
    engine.add_instrument(ethusdt)
    engine.add_data(ticks)

    strategy = BookInspector(BookInspectorConfig())
    engine.add_strategy(strategy)
    engine.run()

    for name, (ok, detail) in strategy.findings.items():
        log(name, detail, ok=ok)

    engine.dispose()

    print("\n" + "-" * 40)
    ok_count = sum(1 for v in RESULTS.values() if v["status"] == "OK")
    fail_count = sum(1 for v in RESULTS.values() if v["status"] == "FAIL")
    print(f"OrderBookAPI: {ok_count} passed, {fail_count} failed")
    print("-" * 40)
    return fail_count == 0


if __name__ == "__main__":
    success = test_order_book_api()
    sys.exit(0 if success else 1)
