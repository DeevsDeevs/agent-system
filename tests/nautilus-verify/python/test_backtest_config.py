"""Tests backtest configuration patterns from battle_tested.md."""


def test_venue_setup_full_pattern():
    """Verify the full venue setup from battle_tested compiles."""
    from nautilus_trader.model.enums import AccountType, OmsType
    from nautilus_trader.model.identifiers import Venue
    from nautilus_trader.model.objects import Currency, Money
    from nautilus_trader.backtest.models import FillModel

    venue = Venue("BINANCE")
    oms_type = OmsType.NETTING
    account_type = AccountType.MARGIN
    usdt = Currency.from_str("USDT")
    starting_balances = [Money(10_000, usdt)]
    fill_model = FillModel(
        prob_fill_on_limit=0.3,
        prob_slippage=0.5,
        random_seed=42,
    )

    assert venue is not None
    assert account_type == AccountType.MARGIN
    assert len(starting_balances) == 1
    assert fill_model is not None


def test_bar_data_wrangler_ts_init_delta():
    """Verify BarDataWrangler accepts ts_init_delta for timestamp correction."""
    import inspect
    from nautilus_trader.persistence.wranglers import BarDataWrangler

    sig = inspect.signature(BarDataWrangler.process)
    assert "ts_init_delta" in sig.parameters


def test_multi_currency_base_currency_none():
    """Verify base_currency=None is valid for multi-currency accounts."""
    import inspect
    from nautilus_trader.backtest.engine import BacktestEngine

    sig = inspect.signature(BacktestEngine.add_venue)
    assert "base_currency" in sig.parameters
