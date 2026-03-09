"""Test OKX Swap (Perpetual): connection, data, order lifecycle."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from conftest import get_env, TestReport
from nautilus_trader.adapters.okx import OKX, OKXDataClientConfig, OKXExecClientConfig
from nautilus_trader.adapters.okx.factories import OKXLiveDataClientFactory, OKXLiveExecClientFactory
from nautilus_trader.config import InstrumentProviderConfig, LiveExecEngineConfig, LoggingConfig, TradingNodeConfig
from nautilus_trader.core.nautilus_pyo3 import OKXContractType, OKXInstrumentType
from nautilus_trader.live.node import TradingNode
from nautilus_trader.model.identifiers import InstrumentId
from venue_test_strategy import VenueTestConfig, VenueTestStrategy

INSTRUMENT = InstrumentId.from_str("BTC-USDT-SWAP.OKX")
PROVIDER = InstrumentProviderConfig(load_all=False, load_ids=frozenset({INSTRUMENT}))

def main():
    report = TestReport("OKX_SWAP")
    try:
        api_key = get_env("OKX_API_KEY")
        api_secret = get_env("OKX_API_SECRET")
        passphrase = get_env("OKX_API_PASSPHRASE")
    except EnvironmentError as e:
        report.phase_fail("credentials", str(e)); report.save(); return
    report.phase_ok("credentials", "Keys loaded (IP-restricted)")

    config = TradingNodeConfig(
        trader_id="TEST-OKX-001",
        logging=LoggingConfig(log_level="INFO"),
        exec_engine=LiveExecEngineConfig(reconciliation=False),
        data_clients={
            OKX: OKXDataClientConfig(
                api_key=api_key, api_secret=api_secret, api_passphrase=passphrase,
                instrument_types=(OKXInstrumentType.SWAP,),
                contract_types=(OKXContractType.LINEAR,),
                instrument_provider=PROVIDER,
                is_demo=False,
            ),
        },
        exec_clients={
            OKX: OKXExecClientConfig(
                api_key=api_key, api_secret=api_secret, api_passphrase=passphrase,
                instrument_types=(OKXInstrumentType.SWAP,),
                contract_types=(OKXContractType.LINEAR,),
                instrument_provider=PROVIDER,
                is_demo=False,
            ),
        },
        timeout_connection=20.0, timeout_reconciliation=5.0,
        timeout_portfolio=5.0, timeout_disconnection=3.0, timeout_post_stop=2.0,
    )
    node = TradingNode(config=config)
    node.add_data_client_factory(OKX, OKXLiveDataClientFactory)
    node.add_exec_client_factory(OKX, OKXLiveExecClientFactory)
    node.trader.add_strategy(VenueTestStrategy(
        VenueTestConfig(instrument_id=INSTRUMENT, data_phase_secs=10, max_run_secs=25, supports_modify=True),
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
