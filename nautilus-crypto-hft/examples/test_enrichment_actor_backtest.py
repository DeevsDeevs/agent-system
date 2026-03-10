"""
Backtest test for the BinanceEnrichmentActor funding rate pipeline.

In backtest, the Binance adapter isn't running, so we simulate the flow:
- A mock actor publishes BinanceFuturesMarkPriceUpdate (simulating the adapter)
- BinanceEnrichmentActor receives it, extracts funding rate, publishes FundingRateUpdate
- A test strategy subscribes to FundingRateUpdate and counts received events

This validates the full pipeline: mark price WS → Actor → FundingRateUpdate → Strategy
"""

from decimal import Decimal

from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
from nautilus_trader.common.actor import Actor
from nautilus_trader.config import ActorConfig, StrategyConfig
from nautilus_trader.adapters.binance.futures.types import BinanceFuturesMarkPriceUpdate
from nautilus_trader.model.data import DataType, FundingRateUpdate, TradeTick
from nautilus_trader.model.enums import AccountType, OmsType, OrderSide
from nautilus_trader.model.identifiers import InstrumentId, TraderId, Venue
from nautilus_trader.model.objects import Currency, Money, Price
from nautilus_trader.persistence.wranglers import TradeTickDataWrangler
from nautilus_trader.test_kit.providers import TestDataProvider, TestInstrumentProvider
from nautilus_trader.trading.strategy import Strategy

from binance_enrichment_actor import (
    BinanceEnrichmentActor,
    BinanceEnrichmentActorConfig,
    OpenInterestData,
)


class MockMarkPriceActorConfig(ActorConfig, frozen=True):
    """Simulates Binance adapter emitting BinanceFuturesMarkPriceUpdate."""
    emit_every: int = 100


class MockMarkPriceActor(Actor):
    """Simulates the Binance adapter's mark price stream in backtest."""

    def __init__(self, config: MockMarkPriceActorConfig) -> None:
        super().__init__(config)
        self.count = 0
        self.published = 0

    def on_start(self) -> None:
        inst = self.cache.instruments()[0]
        self.subscribe_trade_ticks(inst.id)

    def on_trade_tick(self, tick: TradeTick) -> None:
        self.count += 1
        if self.count % self.config.emit_every != 0:
            return

        inst = self.cache.instruments()[0]
        mark_update = BinanceFuturesMarkPriceUpdate(
            instrument_id=inst.id,
            mark=Price.from_str(str(tick.price)),
            index=Price.from_str(str(tick.price)),
            estimated_settle=Price.from_str(str(tick.price)),
            funding_rate=Decimal("0.000125"),
            next_funding_ns=tick.ts_event + 28_800_000_000_000,
            ts_event=tick.ts_event,
            ts_init=tick.ts_init,
        )
        self.publish_data(
            data_type=DataType(BinanceFuturesMarkPriceUpdate, metadata={"instrument_id": inst.id}),
            data=mark_update,
        )
        self.published += 1


class FundingReceiverConfig(StrategyConfig, frozen=True):
    instrument_id: InstrumentId


class FundingReceiverStrategy(Strategy):
    """Test strategy that subscribes to FundingRateUpdate and OpenInterestData."""

    def __init__(self, config: FundingReceiverConfig) -> None:
        super().__init__(config)
        self.funding_updates = []
        self.oi_updates = []

    def on_start(self) -> None:
        self.subscribe_data(
            data_type=DataType(
                FundingRateUpdate,
                metadata={"instrument_id": self.config.instrument_id},
            ),
        )
        self.subscribe_data(
            data_type=DataType(
                OpenInterestData,
                metadata={"instrument_id": self.config.instrument_id},
            ),
        )

    def on_data(self, data) -> None:
        if isinstance(data, FundingRateUpdate):
            self.funding_updates.append(data)
        elif isinstance(data, OpenInterestData):
            self.oi_updates.append(data)


if __name__ == "__main__":
    USDT = Currency.from_str("USDT")
    instrument = TestInstrumentProvider.ethusdt_binance()
    engine = BacktestEngine(config=BacktestEngineConfig(trader_id=TraderId("BACKTESTER-001")))

    engine.add_venue(
        venue=Venue("BINANCE"),
        oms_type=OmsType.NETTING,
        account_type=AccountType.MARGIN,
        base_currency=None,
        starting_balances=[Money(100_000, USDT)],
    )
    engine.add_instrument(instrument)

    dp = TestDataProvider()
    df = dp.read_csv_ticks("binance/ethusdt-trades.csv")
    wrangler = TradeTickDataWrangler(instrument=instrument)
    ticks = wrangler.process(df)
    engine.add_data(ticks)

    # 1. Mock actor simulates adapter mark price stream
    mock_actor = MockMarkPriceActor(MockMarkPriceActorConfig(emit_every=100))
    engine.add_actor(mock_actor)

    # 2. Enrichment actor (OI disabled — no REST in backtest)
    enrichment = BinanceEnrichmentActor(BinanceEnrichmentActorConfig(
        instrument_id=instrument.id,
        oi_enabled=False,
        funding_enabled=True,
    ))
    engine.add_actor(enrichment)

    # 3. Strategy receives FundingRateUpdate
    strategy = FundingReceiverStrategy(FundingReceiverConfig(instrument_id=instrument.id))
    engine.add_strategy(strategy)

    engine.run()

    print(f"\nMock adapter: {mock_actor.count} ticks → {mock_actor.published} mark price updates")
    print(f"Enrichment actor: {enrichment.funding_count} funding rates published")
    print(f"Strategy: {len(strategy.funding_updates)} funding rate updates received")

    if strategy.funding_updates:
        last = strategy.funding_updates[-1]
        print(f"  Last rate: {last.rate}")
        print(f"  Last instrument: {last.instrument_id}")
        print(f"  Last next_funding_ns: {last.next_funding_ns}")

    assert len(strategy.funding_updates) > 0, "Strategy should receive funding updates!"
    assert len(strategy.funding_updates) == enrichment.funding_count, "All published should be received!"
    assert strategy.funding_updates[0].rate == Decimal("0.000125"), "Rate should match!"
    print("\nAll assertions passed!")
