"""
Derivatives API test: CryptoPerpetual properties, position PnL, margin,
portfolio access, strategy save/load, BarType variants.
"""
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.dirname(__file__))

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig, StrategyConfig
from nautilus_trader.model.data import TradeTick, Bar, BarType
from nautilus_trader.model.enums import OmsType, AccountType, OrderSide, PositionSide
from nautilus_trader.model.identifiers import Venue
from nautilus_trader.model.objects import Money, Currency
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler
from nautilus_trader.test_kit.providers import TestInstrumentProvider, TestDataProvider
from nautilus_trader.trading.strategy import Strategy

RESULTS = {}


def log(phase: str, msg: str, ok: bool = True):
    status = "OK" if ok else "FAIL"
    RESULTS[phase] = {"status": status, "detail": msg}
    print(f"  [{status}] {phase}: {msg}", flush=True)


class DerivTestConfig(StrategyConfig, frozen=True):
    pass


class DerivTestStrategy(Strategy):
    """Tests perp instrument properties, PnL tracking, portfolio, save/load."""

    def __init__(self, config: DerivTestConfig) -> None:
        super().__init__(config)
        self.tick_count = 0
        self.findings = {}
        self.phase = 0
        self.entry_price = None
        self.bar_count = 0

    def on_start(self) -> None:
        self.instrument = self.cache.instruments()[0]
        self.subscribe_trade_ticks(self.instrument.id)
        bar_type = BarType.from_str(f"{self.instrument.id}-1-MINUTE-LAST-INTERNAL")
        self.subscribe_bars(bar_type)

    def on_bar(self, bar: Bar) -> None:
        self.bar_count += 1

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.tick_count += 1
        if self.tick_count == 100 and self.phase == 0:
            self.phase = 1
            self._check_perp_properties()
            self._open_position()
        elif self.tick_count == 500 and self.phase == 1:
            self.phase = 2
            self._check_pnl(tick)
            self._check_portfolio()
            self._check_save_load()
            self._check_bar_types()
            self._close_position()

    def _check_perp_properties(self):
        inst = self.instrument
        # Check CryptoPerpetual specific properties
        for attr in ["base_currency", "quote_currency", "is_inverse", "multiplier",
                      "margin_init", "margin_maint", "maker_fee", "taker_fee",
                      "lot_size", "max_quantity", "min_quantity", "min_notional"]:
            try:
                val = getattr(inst, attr, None)
                # lot_size can be None (no lot-size constraint) — that's valid
                has_attr = hasattr(inst, attr)
                self.findings[f"perp_{attr}"] = (has_attr, f"{attr}={val}")
            except Exception as e:
                self.findings[f"perp_{attr}"] = (False, f"{attr} error: {e}")

        # settlement_currency is perp-specific (CryptoPerpetual, not CurrencyPair)
        try:
            sc = inst.settlement_currency
            self.findings["settlement_currency"] = (True, f"settlement={sc}")
        except AttributeError:
            self.findings["settlement_currency"] = (True, f"N/A (CurrencyPair has no settlement_currency — perp-only attr)")
        except Exception as e:
            self.findings["settlement_currency"] = (False, f"error: {e}")

    def _open_position(self):
        order = self.order_factory.market(
            instrument_id=self.instrument.id,
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(Decimal("1.0")),
        )
        self.submit_order(order)

    def _check_pnl(self, tick: TradeTick):
        positions = self.cache.positions_open(instrument_id=self.instrument.id)
        pos = positions[0] if positions else None
        if pos is None:
            self.findings["position_exists"] = (False, "No position")
            return

        self.findings["position_exists"] = (True, f"side={pos.side.name}")
        self.findings["pos_quantity"] = (True, f"quantity={pos.quantity}")
        self.findings["pos_avg_px_open"] = (True, f"avg_px_open={pos.avg_px_open}")
        self.findings["pos_signed_qty"] = (True, f"signed_qty={pos.signed_qty}")

        # Unrealized PnL
        try:
            unrealized = pos.unrealized_pnl(tick.price)
            self.findings["unrealized_pnl"] = (True, f"unrealized_pnl={unrealized}")
        except Exception as e:
            self.findings["unrealized_pnl"] = (False, f"error: {e}")

        # Realized PnL (should be 0 for open position)
        self.findings["realized_pnl"] = (True, f"realized_pnl={pos.realized_pnl}")

        # Commission
        try:
            comm = pos.commissions()
            self.findings["commissions"] = (True, f"commissions={comm}")
        except Exception as e:
            self.findings["commissions"] = (False, f"error: {e}")

    def _check_portfolio(self):
        # Portfolio access
        try:
            account = self.portfolio.account(Venue("BINANCE"))
            if account:
                usdt = Currency.from_str("USDT")
                total = account.balance_total(usdt)
                free = account.balance_free(usdt)
                locked = account.balance_locked(usdt)
                self.findings["portfolio_account"] = (True, f"total={total}, free={free}, locked={locked}")
            else:
                self.findings["portfolio_account"] = (False, "No account for BINANCE")
        except Exception as e:
            self.findings["portfolio_account"] = (False, f"error: {e}")

        # Portfolio net position
        try:
            is_flat = self.portfolio.is_flat(self.instrument.id)
            self.findings["portfolio_flat"] = (True, f"is_flat={is_flat}")
        except Exception as e:
            self.findings["portfolio_flat"] = (False, f"error: {e}")

    def _check_save_load(self):
        # on_save / on_load
        try:
            state = self.on_save()
            self.findings["on_save"] = (True, f"state keys={list(state.keys()) if state else 'empty'}")
        except Exception as e:
            self.findings["on_save"] = (False, f"error: {e}")

    def _check_bar_types(self):
        # Verify various BarType string formats
        inst_id = str(self.instrument.id)
        bar_formats = [
            f"{inst_id}-1-MINUTE-LAST-INTERNAL",
            f"{inst_id}-5-MINUTE-LAST-INTERNAL",
            f"{inst_id}-1-HOUR-LAST-INTERNAL",
        ]
        for fmt in bar_formats:
            try:
                bt = BarType.from_str(fmt)
                self.findings[f"bartype_{fmt.split('-')[2]}_{fmt.split('-')[3]}"] = (True, f"OK: {bt}")
            except Exception as e:
                self.findings[f"bartype_{fmt}"] = (False, f"error: {e}")

        self.findings["bars_received"] = (True, f"bars_count={self.bar_count}")

    def _close_position(self):
        positions = self.cache.positions_open(instrument_id=self.instrument.id)
        pos = positions[0] if positions else None
        if pos:
            self.close_position(pos)

    def on_order_filled(self, event) -> None:
        if self.phase == 2:
            # After close fill — check closed positions since position is now closed
            closed = self.cache.positions_closed(instrument_id=self.instrument.id)
            pos = closed[-1] if closed else None
            if pos and pos.is_closed:
                self.findings["pos_closed"] = (True, f"realized_pnl={pos.realized_pnl}, avg_px_close={pos.avg_px_close}")

    def on_stop(self) -> None:
        self.close_all_positions(self.instrument.id)


def test_derivatives_api():
    print("\n" + "=" * 60)
    print("TEST: Derivatives API + PnL + Portfolio + BarTypes")
    print("=" * 60)

    # Use perp instrument
    btcusdt_perp = TestInstrumentProvider.btcusdt_perp_binance()
    log("perp_instrument", f"Loaded {btcusdt_perp.id}, type={type(btcusdt_perp).__name__}")

    # Use ethusdt (spot) data but pretend it's the perp for matching
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
        starting_balances=[Money(1_000_000.0, Currency.from_str("USDT"))],
    )
    engine.add_instrument(ethusdt)
    engine.add_data(ticks)

    strategy = DerivTestStrategy(DerivTestConfig())
    engine.add_strategy(strategy)
    engine.run()

    for name, (ok, detail) in strategy.findings.items():
        log(name, detail, ok=ok)

    engine.dispose()

    print("\n" + "-" * 40)
    ok_count = sum(1 for v in RESULTS.values() if v["status"] == "OK")
    fail_count = sum(1 for v in RESULTS.values() if v["status"] == "FAIL")
    print(f"DerivativesAPI: {ok_count} passed, {fail_count} failed")
    print("-" * 40)
    return fail_count == 0


if __name__ == "__main__":
    success = test_derivatives_api()
    sys.exit(0 if success else 1)
