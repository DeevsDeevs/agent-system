"""Deribit BTC option greeks calculation in backtest context."""

from decimal import Decimal

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig, StrategyConfig
from nautilus_trader.core.nautilus_pyo3 import black_scholes_greeks
from nautilus_trader.model.currencies import BTC
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.enums import AccountType, OmsType, OptionKind
from nautilus_trader.model.greeks import GreeksCalculator
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import CryptoOption
from nautilus_trader.model.objects import Currency, Money, Price, Quantity
from nautilus_trader.trading.strategy import Strategy


DERIBIT = Venue("DERIBIT")
OPTION_ID = InstrumentId.from_str("BTC-28MAR25-100000-C.DERIBIT")
UNDERLYING_ID = InstrumentId.from_str("BTC.DERIBIT")


def build_btc_call_option() -> CryptoOption:
    return CryptoOption(
        instrument_id=OPTION_ID,
        raw_symbol=Symbol("BTC-28MAR25-100000-C"),
        underlying=Currency.from_str("BTC"),
        quote_currency=Currency.from_str("BTC"),
        settlement_currency=Currency.from_str("BTC"),
        is_inverse=True,
        option_kind=OptionKind.CALL,
        strike_price=Price.from_str("100000.0"),
        activation_ns=0,
        expiration_ns=1743148800_000_000_000,
        price_precision=4,
        size_precision=1,
        price_increment=Price.from_str("0.0001"),
        size_increment=Quantity.from_str("0.1"),
        ts_event=0,
        ts_init=0,
        maker_fee=Decimal("0.0003"),
        taker_fee=Decimal("0.0005"),
    )


class GreeksStrategyConfig(StrategyConfig, frozen=True):
    option_id: InstrumentId = OPTION_ID
    bar_type: str = f"{OPTION_ID}-1-MINUTE-LAST-INTERNAL"


class GreeksStrategy(Strategy):
    def __init__(self, config: GreeksStrategyConfig) -> None:
        super().__init__(config)
        self.greeks_calc = None

    def on_start(self) -> None:
        self.instrument = self.cache.instrument(self.config.option_id)
        if self.instrument is None:
            self.log.error(f"Instrument not found: {self.config.option_id}")
            return

        self.greeks_calc = GreeksCalculator(
            cache=self.cache,
            clock=self.clock,
        )

        self.subscribe_quote_ticks(self.config.option_id)

    def on_quote_tick(self, tick: QuoteTick) -> None:
        if self.greeks_calc is None:
            return

        greeks = self.greeks_calc.instrument_greeks(
            instrument_id=self.config.option_id,
            flat_interest_rate=0.05,
            cache_greeks=True,
        )

        if greeks is not None:
            self.log.info(
                f"Greeks | delta={greeks.delta:.4f} gamma={greeks.gamma:.6f} "
                f"vega={greeks.vega:.4f} theta={greeks.theta:.4f} "
                f"vol={greeks.vol:.4f} price={greeks.price:.4f}"
            )

    def on_stop(self) -> None:
        pass


def main():
    result = black_scholes_greeks(
        95000.0,    # spot
        0.05,       # interest_rate
        0.0,        # cost_of_carry (0 for options on futures)
        0.65,       # vol
        True,       # is_call
        100000.0,   # strike
        0.25,       # time_to_expiry (3 months)
    )
    print("BTC 100k Call (3m, 65% vol):")
    print(f"  price={result.price:.2f} delta={result.delta:.4f} "
          f"gamma={result.gamma:.8f} vega={result.vega:.4f} theta={result.theta:.4f}")

    # Build engine
    engine = BacktestEngine(
        config=BacktestEngineConfig(
            logging=LoggingConfig(log_level="INFO"),
        ),
    )

    engine.add_venue(
        venue=DERIBIT,
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        starting_balances=[Money.from_str("10 BTC")],
        base_currency=BTC,
    )

    option = build_btc_call_option()
    engine.add_instrument(option)

    engine.add_strategy(GreeksStrategy(GreeksStrategyConfig()))
    engine.run()
    engine.dispose()
    print("Engine run complete (no data loaded — setup validated).")


if __name__ == "__main__":
    main()
