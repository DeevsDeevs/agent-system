// Verifies the Strategy pattern from battle_tested.md (MyStrategy with Deref chain).
// If this compiles, the full Strategy + DataActor trait wiring is correct.

use std::ops::{Deref, DerefMut};

use nautilus_common::actor::{DataActor, DataActorCore};
use nautilus_model::data::TradeTick;
use nautilus_model::identifiers::InstrumentId;
use nautilus_trading::strategy::{Strategy, StrategyConfig, StrategyCore};

#[derive(Debug)]
struct MyStrategy {
    core: StrategyCore,
    instrument_id: InstrumentId,
}

impl MyStrategy {
    fn new(instrument_id: InstrumentId) -> Self {
        Self {
            core: StrategyCore::new(StrategyConfig {
                strategy_id: Some("MY-001".into()),
                ..Default::default()
            }),
            instrument_id,
        }
    }
}

// CRITICAL: Deref target is DataActorCore, NOT StrategyCore.
// StrategyCore implements Deref<Target = DataActorCore>, so this chains through.
impl Deref for MyStrategy {
    type Target = DataActorCore;
    fn deref(&self) -> &Self::Target {
        &self.core // auto-derefs StrategyCore → DataActorCore
    }
}

impl DerefMut for MyStrategy {
    fn deref_mut(&mut self) -> &mut Self::Target {
        &mut self.core
    }
}

impl DataActor for MyStrategy {
    fn on_start(&mut self) -> anyhow::Result<()> {
        self.subscribe_trades(self.instrument_id, None, None);
        Ok(())
    }

    fn on_trade(&mut self, trade: &TradeTick) -> anyhow::Result<()> {
        log::info!("trade px={}", trade.price.as_f64());
        Ok(())
    }

    fn on_stop(&mut self) -> anyhow::Result<()> {
        self.unsubscribe_trades(self.instrument_id, None, None);
        Ok(())
    }
}

impl Strategy for MyStrategy {
    fn core(&self) -> &StrategyCore {
        &self.core
    }
    fn core_mut(&mut self) -> &mut StrategyCore {
        &mut self.core
    }
}

#[test]
fn strategy_pattern_compiles_and_constructs() {
    let id = InstrumentId::from("BTCUSDT-PERP.BINANCE");
    let strat = MyStrategy::new(id);
    assert_eq!(strat.instrument_id.to_string(), "BTCUSDT-PERP.BINANCE");

    // Verify Deref chain: MyStrategy → DataActorCore
    let _core_ref: &DataActorCore = &strat;

    // Verify Strategy trait: core() returns StrategyCore reference
    let _strat_core: &StrategyCore = strat.core();
}
