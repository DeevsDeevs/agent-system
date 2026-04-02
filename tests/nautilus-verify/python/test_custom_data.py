"""Tests the ImbalanceData custom data pattern from battle_tested.md."""

from nautilus_trader.core.data import Data


class ImbalanceData(Data):
    def __init__(self, imbalance: float, volume: float, ts_event: int, ts_init: int):
        self.imbalance = imbalance
        self.volume = volume
        self._ts_event = ts_event
        self._ts_init = ts_init

    @property
    def ts_event(self) -> int:
        return self._ts_event

    @property
    def ts_init(self) -> int:
        return self._ts_init


def test_imbalance_data_instantiates():
    data = ImbalanceData(
        imbalance=0.75,
        volume=1000.0,
        ts_event=1_000_000_000,
        ts_init=1_000_000_001,
    )
    assert data.imbalance == 0.75
    assert data.volume == 1000.0
    assert data.ts_event == 1_000_000_000
    assert data.ts_init == 1_000_000_001


def test_imbalance_data_is_data():
    data = ImbalanceData(
        imbalance=0.5,
        volume=500.0,
        ts_event=0,
        ts_init=0,
    )
    assert isinstance(data, Data)
