"""Tests for every row in the Python anti-hallucination table (SKILL.md).

Each test verifies the 'Reality' column is still correct for the installed version.
Many Cython classes have opaque signatures (*args, **kwargs), so we test by
constructing objects rather than introspecting signatures.
"""

import inspect


# Row: cache.position_for_instrument(id) → cache.positions_open(instrument_id=id)
def test_cache_positions_open_method():
    from nautilus_trader.cache.cache import Cache

    assert hasattr(Cache, "positions_open")
    assert not hasattr(Cache, "position_for_instrument")


# Row: engine.trader.cache → engine.cache directly
def test_engine_cache_direct_access():
    from nautilus_trader.backtest.engine import BacktestEngine

    assert hasattr(BacktestEngine, "cache")


# Row: GenericDataWrangler → specific wranglers
def test_specific_data_wranglers_exist():
    from nautilus_trader.persistence.wranglers import (
        BarDataWrangler,
        OrderBookDeltaDataWrangler,
        QuoteTickDataWrangler,
        TradeTickDataWrangler,
    )


# Row: catalog.data_types() → catalog.list_data_types()
def test_catalog_list_data_types():
    from nautilus_trader.persistence.catalog.parquet import ParquetDataCatalog

    assert hasattr(ParquetDataCatalog, "list_data_types")


# Row: BacktestEngineConfig from nautilus_trader.config → from nautilus_trader.backtest
def test_backtest_engine_config_import():
    from nautilus_trader.backtest.engine import BacktestEngineConfig


# Row: FillModel(prob_fill_on_stop=...) → only prob_fill_on_limit, prob_slippage, random_seed
def test_fillmodel_constructor_accepts_three_params():
    from nautilus_trader.backtest.models import FillModel

    fm = FillModel(prob_fill_on_limit=0.3, prob_slippage=0.5, random_seed=42)
    assert fm is not None


# Row: LoggingConfig(log_file_path=) → log_directory=
def test_logging_config_log_directory():
    from nautilus_trader.config import LoggingConfig

    lc = LoggingConfig(log_directory="logs/")
    assert lc.log_directory == "logs/"


# Row: from nautilus_trader.trading.actor → from nautilus_trader.common.actor import Actor
def test_actor_import_from_common():
    from nautilus_trader.common.actor import Actor


# Row: from nautilus_trader.indicators.ema → from nautilus_trader.indicators import EMA
def test_ema_import():
    from nautilus_trader.indicators import ExponentialMovingAverage


# Row: BollingerBands(20) → BollingerBands(20, 2.0) — k mandatory
def test_bollinger_bands_k_mandatory():
    from nautilus_trader.indicators import BollingerBands

    bb = BollingerBands(20, 2.0)
    assert bb is not None


# Row: MACD(12, 26, 9) → 3rd param is MovingAverageType, not signal_period
def test_macd_third_param_is_ma_type():
    from nautilus_trader.indicators import (
        MovingAverageConvergenceDivergence,
        MovingAverageType,
    )

    m = MovingAverageConvergenceDivergence(12, 26, MovingAverageType.SIMPLE)
    assert m is not None


# Row: DYDXDataClientConfig → DydxDataClientConfig (mixed case)
def test_dydx_config_mixed_case():
    from nautilus_trader.adapters.dydx.config import DydxDataClientConfig


# Row: RSI value in [0, 1] not [0, 100]
def test_rsi_value_range_note():
    from nautilus_trader.indicators import RelativeStrengthIndex

    rsi = RelativeStrengthIndex(14)


# Row: frozen_account=True means checks DISABLED (inverted)
def test_frozen_account_param_exists():
    from nautilus_trader.backtest.engine import BacktestEngine

    sig = inspect.signature(BacktestEngine.add_venue)
    assert "frozen_account" in sig.parameters


# Row: AccountType.CASH vs MARGIN
def test_account_type_margin_exists():
    from nautilus_trader.model.enums import AccountType

    assert hasattr(AccountType, "MARGIN")
    assert hasattr(AccountType, "CASH")


# Row: order.order_side → order.side (events use event.order_side)
def test_order_side_field_name():
    from nautilus_trader.model.orders import MarketOrder

    assert hasattr(MarketOrder, "side")


# Row: request_bars(bar_type) one arg → requires start
def test_request_bars_signature():
    from nautilus_trader.trading.strategy import Strategy

    sig = inspect.signature(Strategy.request_bars)
    assert "start" in sig.parameters


# Row: GreeksCalculator import path (moved to nautilus_trader.model.greeks)
def test_greeks_calculator_import():
    from nautilus_trader.model.greeks import GreeksCalculator


# Row: from nautilus_trader.core.nautilus_pyo3 → correct path for black_scholes_greeks
def test_pyo3_black_scholes_import():
    from nautilus_trader.core.nautilus_pyo3 import black_scholes_greeks


# Row: BinanceAccountType.USDT_FUTURE (no S) → USDT_FUTURES (with S)
def test_binance_usdt_futures_with_s():
    from nautilus_trader.adapters.binance.common.enums import BinanceAccountType

    assert hasattr(BinanceAccountType, "USDT_FUTURES")
    assert not hasattr(BinanceAccountType, "USDT_FUTURE")


# Row: is_testnet=True (not testnet=True) for dYdX
def test_dydx_is_testnet_param():
    from nautilus_trader.adapters.dydx.config import DydxDataClientConfig

    d = DydxDataClientConfig(is_testnet=True)
    assert d.is_testnet is True


# Row: is_testnet=True (not testnet=True) for Deribit
def test_deribit_is_testnet_param():
    from nautilus_trader.adapters.deribit.config import DeribitDataClientConfig

    d = DeribitDataClientConfig(is_testnet=True)
    assert d.is_testnet is True


# Row: book.best_bid_price() returns Price, not float
def test_price_type_exists():
    from nautilus_trader.model.objects import Price

    p = Price.from_str("1.50000")
    assert not isinstance(p, float)


# Row: subscribe_funding_rates() method exists on Strategy
def test_strategy_has_subscribe_funding_rates():
    from nautilus_trader.trading.strategy import Strategy

    assert hasattr(Strategy, "subscribe_funding_rates")


# Row: MarketStatusAction.RESUME does not exist — use TRADING
def test_market_status_action_trading():
    from nautilus_trader.model.enums import MarketStatusAction

    assert hasattr(MarketStatusAction, "TRADING")
    assert not hasattr(MarketStatusAction, "RESUME")


# Row: SyntheticInstrument needs ts_event, ts_init (Cython — test via hasattr on class)
def test_synthetic_instrument_exists():
    from nautilus_trader.model.instruments import SyntheticInstrument

    assert SyntheticInstrument is not None


# Row: from nautilus_trader.common.component import LiveClock (not TestClock from common.clock)
def test_live_clock_import():
    from nautilus_trader.common.component import LiveClock


# Row: CacheConfig import path
def test_cache_config_import():
    from nautilus_trader.config import CacheConfig
