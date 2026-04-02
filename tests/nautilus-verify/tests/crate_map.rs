// Verifies all import paths from the SKILL.md crate map.
// If any `use` statement fails to compile, the crate map is stale.

// nautilus-model: identifiers
use nautilus_model::identifiers::{
    AccountId, ActorId, ClientId, ClientOrderId, ComponentId, ExecAlgorithmId, InstrumentId,
    OrderListId, PositionId, StrategyId, Symbol, TradeId, TraderId, Venue, VenueOrderId,
};

// nautilus-model: data types
use nautilus_model::data::{
    Bar, BarSpecification, BarType, BookOrder, FundingRateUpdate, IndexPriceUpdate,
    InstrumentClose, MarkPriceUpdate, OrderBookDelta, OrderBookDeltas, OrderBookDepth10,
    QuoteTick, TradeTick,
};

// nautilus-model: order types
use nautilus_model::orders::{
    LimitOrder, MarketOrder, StopLimitOrder, StopMarketOrder, TrailingStopLimitOrder,
    TrailingStopMarketOrder,
};

// nautilus-model: events
use nautilus_model::events::position::closed::PositionClosed;

// nautilus-common: actor
use nautilus_common::actor::{DataActorConfig, DataActorCore};

// DataActor is a trait — imported via trait bound check
fn _assert_data_actor_trait_exists<T: nautilus_common::actor::DataActor>() {}

// nautilus-common: environment
use nautilus_common::enums::Environment;

// nautilus-trading: strategy
use nautilus_trading::strategy::{StrategyConfig, StrategyCore};

// nautilus-binance: config + enums
use nautilus_binance::common::enums::BinanceProductType;
use nautilus_binance::config::{BinanceDataClientConfig, BinanceExecClientConfig};
use nautilus_binance::factories::{BinanceDataClientFactory, BinanceExecutionClientFactory};

// nautilus-live: node
use nautilus_live::node::LiveNode;

#[test]
fn crate_map_identifiers_compile() {
    let _ = std::any::type_name::<InstrumentId>();
    let _ = std::any::type_name::<TraderId>();
    let _ = std::any::type_name::<Venue>();
    let _ = std::any::type_name::<StrategyId>();
    let _ = std::any::type_name::<AccountId>();
    let _ = std::any::type_name::<ClientOrderId>();
    let _ = std::any::type_name::<VenueOrderId>();
    let _ = std::any::type_name::<TradeId>();
    let _ = std::any::type_name::<PositionId>();
    let _ = std::any::type_name::<Symbol>();
    let _ = std::any::type_name::<ActorId>();
    let _ = std::any::type_name::<ClientId>();
    let _ = std::any::type_name::<ComponentId>();
    let _ = std::any::type_name::<ExecAlgorithmId>();
    let _ = std::any::type_name::<OrderListId>();
}

#[test]
fn crate_map_data_types_compile() {
    let _ = std::any::type_name::<TradeTick>();
    let _ = std::any::type_name::<QuoteTick>();
    let _ = std::any::type_name::<Bar>();
    let _ = std::any::type_name::<BarType>();
    let _ = std::any::type_name::<BarSpecification>();
    let _ = std::any::type_name::<OrderBookDelta>();
    let _ = std::any::type_name::<OrderBookDeltas>();
    let _ = std::any::type_name::<OrderBookDepth10>();
    let _ = std::any::type_name::<BookOrder>();
    let _ = std::any::type_name::<FundingRateUpdate>();
    let _ = std::any::type_name::<MarkPriceUpdate>();
    let _ = std::any::type_name::<IndexPriceUpdate>();
    let _ = std::any::type_name::<InstrumentClose>();
}

#[test]
fn crate_map_order_types_compile() {
    let _ = std::any::type_name::<MarketOrder>();
    let _ = std::any::type_name::<LimitOrder>();
    let _ = std::any::type_name::<StopMarketOrder>();
    let _ = std::any::type_name::<StopLimitOrder>();
    let _ = std::any::type_name::<TrailingStopMarketOrder>();
    let _ = std::any::type_name::<TrailingStopLimitOrder>();
}

#[test]
fn crate_map_actor_and_strategy_compile() {
    let _ = std::any::type_name::<DataActorCore>();
    let _ = std::any::type_name::<DataActorConfig>();
    let _ = std::any::type_name::<StrategyCore>();
    let _ = std::any::type_name::<StrategyConfig>();
}

#[test]
fn crate_map_binance_compile() {
    let _ = BinanceProductType::UsdM;
    let _ = BinanceProductType::CoinM;
    let _ = BinanceProductType::Spot;
    let _ = std::any::type_name::<BinanceDataClientConfig>();
    let _ = std::any::type_name::<BinanceExecClientConfig>();
    let _ = std::any::type_name::<BinanceDataClientFactory>();
    let _ = std::any::type_name::<BinanceExecutionClientFactory>();
}

#[test]
fn crate_map_live_node_compile() {
    let _ = std::any::type_name::<LiveNode>();
    let _ = std::any::type_name::<Environment>();
}

#[test]
fn crate_map_events_compile() {
    let _ = std::any::type_name::<PositionClosed>();
}
