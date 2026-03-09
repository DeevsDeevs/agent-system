"""Test dYdX v4 Perpetuals: connection, data, order lifecycle."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from conftest import get_env, TestReport
from nautilus_trader.adapters.dydx import (
    DYDX, DydxDataClientConfig, DydxExecClientConfig,
    DydxLiveDataClientFactory, DydxLiveExecClientFactory,
)
from nautilus_trader.config import InstrumentProviderConfig, LiveExecEngineConfig, LoggingConfig, TradingNodeConfig
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.identifiers import InstrumentId
from venue_test_strategy import VenueTestConfig, VenueTestStrategy

INSTRUMENT = InstrumentId.from_str("BTC-USD-PERP.DYDX")
PROVIDER = InstrumentProviderConfig(load_all=False, load_ids=frozenset({INSTRUMENT}))

def main():
    report = TestReport("DYDX_V4")
    try:
        wallet = get_env("DYDX_PERP_WALLET_ADDRESS")
        pk = get_env("DYDX_PRIVATE_KEY")
    except EnvironmentError as e:
        report.phase_fail("credentials", str(e)); report.save(); return
    report.phase_ok("credentials", "OK")

    config = TradingNodeConfig(
        trader_id="TEST-DYDX-001",
        logging=LoggingConfig(log_level="INFO"),
        exec_engine=LiveExecEngineConfig(reconciliation=False),
        data_clients={
            DYDX: DydxDataClientConfig(
                wallet_address=wallet,
                instrument_provider=PROVIDER,
                is_testnet=False,
            ),
        },
        exec_clients={
            DYDX: DydxExecClientConfig(
                wallet_address=wallet, private_key=pk, subaccount=0,
                instrument_provider=PROVIDER,
                is_testnet=False,
            ),
        },
        timeout_connection=20.0, timeout_reconciliation=5.0,
        timeout_portfolio=5.0, timeout_disconnection=3.0, timeout_post_stop=2.0,
    )
    node = TradingNode(config=config)
    node.add_data_client_factory(DYDX, DydxLiveDataClientFactory)
    node.add_exec_client_factory(DYDX, DydxLiveExecClientFactory)
    node.trader.add_strategy(VenueTestStrategy(
        VenueTestConfig(instrument_id=INSTRUMENT, data_phase_secs=10, max_run_secs=25, supports_modify=False),
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
