"""Tests the SpreadEMA custom indicator pattern from battle_tested.md."""

from nautilus_trader.indicators.base import Indicator


class SpreadEMA(Indicator):
    def __init__(self, period: int):
        super().__init__([])
        self.period = period
        self._values = []
        self.value = 0.0

    def handle_quote_tick(self, tick) -> None:
        spread = float(tick.ask_price - tick.bid_price)
        self._values.append(spread)
        if len(self._values) > self.period:
            self._values.pop(0)
        self.value = sum(self._values) / len(self._values)
        # _set_initialized is inherited from Cython Indicator base — do NOT override it
        self._set_initialized(len(self._values) >= self.period)

    def reset(self) -> None:
        self._values.clear()
        self.value = 0.0
        self._set_initialized(False)


def test_spread_ema_instantiates():
    ema = SpreadEMA(period=10)
    assert ema.period == 10
    assert ema.value == 0.0
    assert not ema.initialized


def test_spread_ema_warmup_and_reset():
    ema = SpreadEMA(period=3)
    ema._values = [1.0, 2.0, 3.0]
    ema.value = 2.0
    ema._set_initialized(True)
    assert ema.initialized

    ema.reset()
    assert ema._values == []
    assert ema.value == 0.0
    assert not ema.initialized


def test_spread_ema_is_indicator():
    ema = SpreadEMA(period=5)
    assert isinstance(ema, Indicator)
