"""Tests order book patterns from battle_tested.md and anti-hallucination table."""

from nautilus_trader.model.objects import Price


def test_price_is_not_float():
    """book.best_bid_price() returns Price, not float — must cast with float()."""
    p = Price.from_str("50000.00")
    assert not isinstance(p, float)
    assert isinstance(float(p), float)


def test_price_arithmetic_requires_cast():
    """Price objects need float() for arithmetic with regular numbers."""
    p = Price.from_str("100.50")
    result = float(p) * 2
    assert result == 201.0


def test_book_order_import_from_data():
    """BookOrder import from model.data, NOT model.book."""
    from nautilus_trader.model.data import BookOrder


def test_order_book_depth10_exists():
    """OrderBookDepth10 pre-aggregated type exists."""
    from nautilus_trader.model.data import OrderBookDepth10


def test_order_book_delta_exists():
    """OrderBookDelta type exists for L2 data."""
    from nautilus_trader.model.data import OrderBookDelta
