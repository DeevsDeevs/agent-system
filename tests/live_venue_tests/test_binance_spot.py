"""Test Binance Spot: connection, data, order lifecycle."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from conftest import get_env, TestReport
from nautilus_trader.adapters.binance import (
    BINANCE, BinanceAccountType, BinanceDataClientConfig,
    BinanceExecClientConfig, BinanceLiveDataClientFactory, BinanceLiveExecClientFactory,
)
from nautilus_trader.config import InstrumentProviderConfig, LiveExecEngineConfig, LoggingConfig, TradingNodeConfig
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.identifiers import InstrumentId
from venue_test_strategy import VenueTestConfig, VenueTestStrategy

INSTRUMENT = InstrumentId.from_str("BTCUSDT.BINANCE")
PROVIDER = InstrumentProviderConfig(load_all=False, load_ids=frozenset({INSTRUMENT}))

def main():
    report = TestReport("BINANCE_SPOT")
    try:
        api_key = get_env("BINANCE_SPOT_API_KEY")
        api_secret = get_env("BINANCE_SPOT_API_SECRET")
    except EnvironmentError as e:
        report.phase_fail("credentials", str(e)); report.save(); return
    report.phase_ok("credentials", "OK")

    config = TradingNodeConfig(
        trader_id="TEST-BN-SPOT-001",
        logging=LoggingConfig(log_level="INFO"),
        exec_engine=LiveExecEngineConfig(reconciliation=False),
        data_clients={
            BINANCE: BinanceDataClientConfig(
                api_key=api_key, api_secret=api_secret,
                account_type=BinanceAccountType.SPOT,
                instrument_provider=PROVIDER,
            ),
        },
        exec_clients={
            BINANCE: BinanceExecClientConfig(
                api_key=api_key, api_secret=api_secret,
                account_type=BinanceAccountType.SPOT,
                instrument_provider=PROVIDER,
            ),
        },
        timeout_connection=40.0, timeout_reconciliation=5.0,
        timeout_portfolio=5.0, timeout_disconnection=3.0, timeout_post_stop=2.0,
    )
    node = TradingNode(config=config)
    node.add_data_client_factory(BINANCE, BinanceLiveDataClientFactory)
    node.add_exec_client_factory(BINANCE, BinanceLiveExecClientFactory)
    node.trader.add_strategy(VenueTestStrategy(
        VenueTestConfig(instrument_id=INSTRUMENT, data_phase_secs=10, max_run_secs=30, supports_modify=False),
        report=report,
    ))
    node.build()
    report.phase_ok("node_build", "OK")
    try:
        node.run()
    except KeyboardInterrupt:
        node.stop()
    except Exception as e:
        report.phase_fail("runtime", str(e)); report.save()

if __name__ == "__main__":
    main()
