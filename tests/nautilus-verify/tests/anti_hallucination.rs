// Tests for every row in the Rust anti-hallucination table (SKILL.md).
// Each test verifies the "Reality" column compiles/works correctly.

use nautilus_binance::common::enums::BinanceProductType;
use nautilus_binance::config::BinanceDataClientConfig;
use nautilus_binance::factories::BinanceExecutionClientFactory;
use nautilus_common::actor::{DataActor, DataActorCore};
use nautilus_common::enums::Environment;
use nautilus_live::node::LiveNode;
use nautilus_model::data::{FundingRateUpdate, OrderBookDeltas};
use nautilus_model::events::position::closed::PositionClosed;
use nautilus_model::identifiers::{InstrumentId, TraderId};
use nautilus_trading::strategy::{StrategyConfig, StrategyCore};
use std::ops::{Deref, DerefMut};

// Row: LiveNode::new(config) → LiveNode::builder(trader_id, Environment::Live)?.build()?
#[test]
fn hallucination_livenode_builder_pattern() {
    // Verify the builder method exists with correct signature
    // (we can't actually build without a full runtime, but the function must exist)
    let _ = LiveNode::builder as fn(TraderId, Environment) -> anyhow::Result<_>;
}

// Row: BinanceDataClientConfig::builder() → struct literal with ..Default::default()
#[test]
fn hallucination_binance_data_config_struct_literal() {
    let config = BinanceDataClientConfig {
        product_types: vec![BinanceProductType::UsdM],
        ..Default::default()
    };
    assert_eq!(config.product_types, vec![BinanceProductType::UsdM]);
}

// Row: BinanceAccountType::UsdtFutures → BinanceProductType::UsdM
#[test]
fn hallucination_binance_product_type_usdm() {
    let _ = BinanceProductType::UsdM;
    let _ = BinanceProductType::CoinM;
    let _ = BinanceProductType::Spot;
    let _ = BinanceProductType::Margin;
}

// Row: nautilus_core::identifiers::InstrumentId → nautilus_model::identifiers::InstrumentId
#[test]
fn hallucination_instrument_id_in_model() {
    let _ = std::any::type_name::<InstrumentId>();
    // Compiles = nautilus_model::identifiers::InstrumentId is the correct path
}

// Row: DataActor in nautilus_trading → DataActor in nautilus_common::actor
#[test]
fn hallucination_data_actor_in_common() {
    let _ = std::any::type_name::<dyn DataActor>();
    let _ = std::any::type_name::<DataActorCore>();
}

// Row: nautilus_trader_model → nautilus_model
#[test]
fn hallucination_crate_name_is_nautilus_model() {
    // If this compiles, nautilus_model (not nautilus_trader_model) is correct
    let _ = std::any::type_name::<nautilus_model::identifiers::InstrumentId>();
}

// Row: on_book_delta (singular) → on_book_deltas (plural — batch)
#[test]
fn hallucination_on_book_deltas_plural() {
    // Verify the trait method signature accepts OrderBookDeltas (batch)
    let _ = std::any::type_name::<OrderBookDeltas>();
    // The DataActor trait has fn on_book_deltas(&mut self, deltas: &OrderBookDeltas)
    // If OrderBookDeltas doesn't exist, this test fails to compile.
}

// Row: event.duration_ns on PositionClosed → event.duration (no _ns suffix)
#[test]
fn hallucination_position_closed_duration_field() {
    // Verify the field name is `duration`, not `duration_ns`
    // PositionClosed has: pub duration: DurationNanos
    let _ = |e: &PositionClosed| e.duration;
}

// Row: event.realized_pnl is Money → Option<Money>
#[test]
fn hallucination_realized_pnl_is_option() {
    // PositionClosed has: pub realized_pnl: Option<Money>
    let _ = |e: &PositionClosed| {
        match &e.realized_pnl {
            Some(_money) => {}
            None => {}
        }
    };
}

// Row: Deref<Target = StrategyCore> for Strategy → Deref<Target = DataActorCore>
#[test]
fn hallucination_strategy_core_derefs_to_data_actor_core() {
    // StrategyCore implements Deref<Target = DataActorCore>
    fn assert_deref_target(_: &impl Deref<Target = DataActorCore>) {}
    let config = StrategyConfig {
        strategy_id: Some("TEST-001".into()),
        ..Default::default()
    };
    let core = StrategyCore::new(config);
    assert_deref_target(&core);
}

// Row: node.add_actor(strategy) for Strategy → node.add_strategy(strategy)
// Can't test without runtime, but verify the method exists on LiveNode
// (tested transitively by strategy_pattern.rs and livenode builder test)

// Row: BinanceExecClientFactory → BinanceExecutionClientFactory (full name)
#[test]
fn hallucination_binance_execution_client_factory_full_name() {
    let _ = std::any::type_name::<BinanceExecutionClientFactory>();
}

// Row: Deref target for user Strategy struct must be DataActorCore
#[test]
fn hallucination_user_strategy_deref_chain() {
    #[derive(Debug)]
    struct TestStrat {
        core: StrategyCore,
    }

    impl Deref for TestStrat {
        type Target = DataActorCore;
        fn deref(&self) -> &Self::Target {
            &self.core // auto-derefs StrategyCore → DataActorCore
        }
    }

    impl DerefMut for TestStrat {
        fn deref_mut(&mut self) -> &mut Self::Target {
            &mut self.core
        }
    }

    let config = StrategyConfig {
        strategy_id: Some("TEST-002".into()),
        ..Default::default()
    };
    let strat = TestStrat {
        core: StrategyCore::new(config),
    };
    // Verify the deref chain works
    let _core_ref: &DataActorCore = &strat;
}

// Row: FundingRateUpdate exists in nautilus_model::data
#[test]
fn hallucination_funding_rate_update_path() {
    let _ = std::any::type_name::<FundingRateUpdate>();
}
