// Verifies the DataActor pattern from battle_tested.md (FundingRateCapture).
// If this compiles, the pattern is correct for the current nautilus version.

use std::ops::{Deref, DerefMut};

use nautilus_common::actor::{DataActor, DataActorConfig, DataActorCore};
use nautilus_model::data::FundingRateUpdate;
use nautilus_model::identifiers::InstrumentId;

#[derive(Debug)]
struct FundingRateCapture {
    core: DataActorCore,
    instrument_id: InstrumentId,
}

impl FundingRateCapture {
    fn new(instrument_id: InstrumentId) -> Self {
        Self {
            core: DataActorCore::new(DataActorConfig {
                actor_id: Some("FundingCapture-001".into()),
                ..Default::default()
            }),
            instrument_id,
        }
    }
}

impl Deref for FundingRateCapture {
    type Target = DataActorCore;
    fn deref(&self) -> &Self::Target {
        &self.core
    }
}

impl DerefMut for FundingRateCapture {
    fn deref_mut(&mut self) -> &mut Self::Target {
        &mut self.core
    }
}

impl DataActor for FundingRateCapture {
    fn on_start(&mut self) -> anyhow::Result<()> {
        self.subscribe_funding_rates(self.instrument_id, None, None);
        Ok(())
    }

    fn on_funding_rate(&mut self, update: &FundingRateUpdate) -> anyhow::Result<()> {
        log::info!("{} rate={}", update.instrument_id, update.rate);
        Ok(())
    }

    fn on_stop(&mut self) -> anyhow::Result<()> {
        self.unsubscribe_funding_rates(self.instrument_id, None, None);
        Ok(())
    }
}

#[test]
fn data_actor_funding_rate_capture_compiles() {
    let id = InstrumentId::from("BTCUSDT-PERP.BINANCE");
    let actor = FundingRateCapture::new(id);
    assert_eq!(actor.instrument_id.to_string(), "BTCUSDT-PERP.BINANCE");
}
