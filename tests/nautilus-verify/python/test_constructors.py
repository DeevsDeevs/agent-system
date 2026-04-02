"""Tests for constructor patterns from battle_tested.md and SKILL.md."""

from nautilus_trader.model.enums import OrderSide
from nautilus_trader.model.objects import Price, Quantity


# BookOrder: 4 positional args, not keyword-style
def test_book_order_positional_args():
    from nautilus_trader.model.data import BookOrder

    order = BookOrder(
        OrderSide.BUY,
        Price.from_str("50000.00"),
        Quantity.from_str("1.000"),
        0,
    )
    assert order.side == OrderSide.BUY


# FillModel: only 3 params
def test_fillmodel_constructor():
    from nautilus_trader.backtest.models import FillModel

    fm = FillModel(
        prob_fill_on_limit=0.3,
        prob_slippage=0.5,
        random_seed=42,
    )
    assert fm is not None


# Venue setup with AccountType.MARGIN
def test_account_type_and_oms_type():
    from nautilus_trader.model.enums import AccountType, OmsType

    assert AccountType.MARGIN is not None
    assert OmsType.NETTING is not None


# Currency.from_str (not bare constant)
def test_currency_from_str():
    from nautilus_trader.model.objects import Currency

    usdt = Currency.from_str("USDT")
    assert usdt is not None


# Money constructor
def test_money_constructor():
    from nautilus_trader.model.objects import Currency
    from nautilus_trader.model.objects import Money

    usdt = Currency.from_str("USDT")
    m = Money(10_000, usdt)
    assert m is not None


# Price.from_str (not Price(float))
def test_price_from_str():
    from nautilus_trader.model.objects import Price

    p = Price.from_str("1.50000")
    assert float(p) == 1.5


# Venue constructor
def test_venue_constructor():
    from nautilus_trader.model.identifiers import Venue

    v = Venue("BINANCE")
    assert str(v) == "BINANCE"


# InstrumentId full format "SYMBOL.VENUE"
def test_instrument_id_format():
    from nautilus_trader.model.identifiers import InstrumentId

    iid = InstrumentId.from_str("BTCUSDT-PERP.BINANCE")
    assert str(iid) == "BTCUSDT-PERP.BINANCE"


# LoggingConfig with log_directory
def test_logging_config_constructor():
    from nautilus_trader.config import LoggingConfig

    lc = LoggingConfig(
        log_level="INFO",
        log_directory="logs/",
        log_colors=False,
    )
    assert lc.log_directory == "logs/"
