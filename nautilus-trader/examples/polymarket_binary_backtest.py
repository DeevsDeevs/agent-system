"""Polymarket binary option backtest example."""

from decimal import Decimal

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.config import LoggingConfig, StrategyConfig
from nautilus_trader.model.data import QuoteTick
from nautilus_trader.model.enums import (
    AccountType,
    AssetClass,
    OmsType,
    OrderSide,
    TimeInForce,
)
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue
from nautilus_trader.model.instruments import BinaryOption
from nautilus_trader.model.objects import Currency, Money, Price, Quantity
from nautilus_trader.trading.strategy import Strategy


POLYMARKET = Venue("POLYMARKET")


def build_binary_option(outcome: str, token_id: str) -> BinaryOption:
    return BinaryOption(
        instrument_id=InstrumentId.from_str(f"{token_id}.POLYMARKET"),
        raw_symbol=Symbol(token_id),
        asset_class=AssetClass.ALTERNATIVE,
        currency=Currency.from_str("USDC"),
        price_precision=3,
        size_precision=2,
        price_increment=Price.from_str("0.001"),
        size_increment=Quantity.from_str("0.01"),
        activation_ns=0,
        expiration_ns=1743148800_000_000_000,
        ts_event=0,
        ts_init=0,
        outcome=outcome,
        description="Will BTC exceed $100k by March 2025?",
    )


class BinaryStrategyConfig(StrategyConfig, frozen=True):
    yes_id: InstrumentId = InstrumentId.from_str("YES-21742.POLYMARKET")
    no_id: InstrumentId = InstrumentId.from_str("NO-21742.POLYMARKET")
    order_size: Decimal = Decimal("10.0")


class BinaryStrategy(Strategy):
    def __init__(self, config: BinaryStrategyConfig) -> None:
        super().__init__(config)

    def on_start(self) -> None:
        self.yes_inst = self.cache.instrument(self.config.yes_id)
        self.no_inst = self.cache.instrument(self.config.no_id)
        if not self.yes_inst or not self.no_inst:
            self.log.error("Instruments not found")
            return

        self.subscribe_quote_ticks(self.config.yes_id)

    def on_quote_tick(self, tick: QuoteTick) -> None:
        if not self.portfolio.is_flat(self.config.yes_id):
            return

        # Buy YES at 0.55 (55% implied probability)
        order = self.order_factory.limit(
            instrument_id=self.config.yes_id,
            order_side=OrderSide.BUY,
            quantity=Quantity.from_str(str(self.config.order_size)),
            price=Price.from_str("0.550"),
            time_in_force=TimeInForce.GTC,
        )
        self.submit_order(order)
        self.log.info(f"Submitted limit BUY YES @ 0.550 x {self.config.order_size}")

    def on_stop(self) -> None:
        self.cancel_all_orders(self.config.yes_id)
        self.close_all_positions(self.config.yes_id)


def main():
    engine = BacktestEngine(
        config=BacktestEngineConfig(
            logging=LoggingConfig(log_level="INFO"),
        ),
    )

    engine.add_venue(
        venue=POLYMARKET,
        oms_type=OmsType.NETTING,
        account_type=AccountType.CASH,
        starting_balances=[Money.from_str("1000 USDC")],
        base_currency=Currency.from_str("USDC"),
    )

    yes_option = build_binary_option("Yes", "YES-21742")
    no_option = build_binary_option("No", "NO-21742")
    engine.add_instrument(yes_option)
    engine.add_instrument(no_option)

    engine.add_strategy(BinaryStrategy(BinaryStrategyConfig()))
    engine.run()
    engine.dispose()
    print("Binary backtest setup validated (no data loaded).")


if __name__ == "__main__":
    main()
