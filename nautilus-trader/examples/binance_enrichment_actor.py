"""
BinanceEnrichmentActor: Extracts funding rates from mark price WS stream,
polls Open Interest via REST. Publishes FundingRateUpdate + OpenInterestData.
"""

import json
from datetime import timedelta
from decimal import Decimal

from nautilus_trader.common.actor import Actor
from nautilus_trader.config import ActorConfig
from nautilus_trader.core.data import Data
from nautilus_trader.model.data import DataType, FundingRateUpdate
from nautilus_trader.model.identifiers import InstrumentId



class OpenInterestData(Data):
    """Open interest snapshot from Binance REST API."""

    def __init__(
        self,
        instrument_id: InstrumentId,
        open_interest: float,
        ts_event: int,
        ts_init: int,
    ) -> None:
        self.instrument_id = instrument_id
        self.open_interest = open_interest
        self._ts_event = ts_event
        self._ts_init = ts_init

    @property
    def ts_event(self) -> int:
        return self._ts_event

    @property
    def ts_init(self) -> int:
        return self._ts_init

    def __repr__(self) -> str:
        return (
            f"OpenInterestData("
            f"instrument_id={self.instrument_id}, "
            f"open_interest={self.open_interest}, "
            f"ts_event={self.ts_event})"
        )



class BinanceEnrichmentActorConfig(ActorConfig, frozen=True):
    instrument_id: InstrumentId
    oi_poll_interval_secs: int = 5
    oi_enabled: bool = True
    funding_enabled: bool = True



class BinanceEnrichmentActor(Actor):

    def __init__(self, config: BinanceEnrichmentActorConfig) -> None:
        super().__init__(config)
        self._instrument_id = config.instrument_id
        self._oi_poll_interval = config.oi_poll_interval_secs
        self._oi_enabled = config.oi_enabled
        self._funding_enabled = config.funding_enabled
        self._http_client = None
        self._binance_symbol = None

        self.funding_count = 0
        self.oi_count = 0

    def on_start(self) -> None:
        # Derive raw Binance symbol from instrument_id (e.g. "BTCUSDT-PERP.BINANCE" -> "BTCUSDT")
        raw = self._instrument_id.symbol.value  # "BTCUSDT-PERP"
        self._binance_symbol = raw.replace("-PERP", "")

        if self._funding_enabled:
            self._subscribe_mark_price()

        if self._oi_enabled:
            self._setup_oi_polling()

    def _subscribe_mark_price(self) -> None:
        from nautilus_trader.adapters.binance.futures.types import BinanceFuturesMarkPriceUpdate

        data_type = DataType(
            BinanceFuturesMarkPriceUpdate,
            metadata={"instrument_id": self._instrument_id},
        )
        self.subscribe_data(data_type=data_type)
        self.log.info(f"Subscribed to mark price for {self._instrument_id}")

    def _setup_oi_polling(self) -> None:
        from nautilus_trader.core.nautilus_pyo3 import HttpClient

        self._http_client = HttpClient()
        self.clock.set_timer(
            name=f"oi_poll_{self._binance_symbol}",
            interval=timedelta(seconds=self._oi_poll_interval),
            callback=self._poll_open_interest,
        )
        self.log.info(
            f"OI polling enabled for {self._binance_symbol} "
            f"every {self._oi_poll_interval}s",
        )

    def on_data(self, data) -> None:
        from nautilus_trader.adapters.binance.futures.types import BinanceFuturesMarkPriceUpdate

        if not isinstance(data, BinanceFuturesMarkPriceUpdate):
            return

        fr = FundingRateUpdate(
            instrument_id=data.instrument_id,
            rate=data.funding_rate,
            ts_event=data.ts_event,
            ts_init=data.ts_init,
            next_funding_ns=data.next_funding_ns,
        )
        self.publish_data(
            data_type=DataType(FundingRateUpdate, metadata={"instrument_id": data.instrument_id}),
            data=fr,
        )
        self.funding_count += 1

    def _poll_open_interest(self, event) -> None:
        self.queue_for_executor(self._fetch_oi)

    async def _fetch_oi(self) -> None:
        try:
            url = "https://fapi.binance.com/fapi/v1/openInterest"
            resp = await self._http_client.get(url, params={"symbol": self._binance_symbol})
            body = json.loads(resp.body)

            ts_now = self.clock.timestamp_ns()
            oi_data = OpenInterestData(
                instrument_id=self._instrument_id,
                open_interest=float(body["openInterest"]),
                ts_event=int(body["time"]) * 1_000_000 if "time" in body else ts_now,
                ts_init=ts_now,
            )
            self.publish_data(
                data_type=DataType(OpenInterestData, metadata={"instrument_id": self._instrument_id}),
                data=oi_data,
            )
            self.oi_count += 1
            self.log.debug(f"OI: {body['openInterest']} for {self._binance_symbol}")

        except Exception as e:
            self.log.error(f"OI fetch failed: {e}")

    def on_stop(self) -> None:
        if self._oi_enabled:
            self.clock.cancel_timer(f"oi_poll_{self._binance_symbol}")
