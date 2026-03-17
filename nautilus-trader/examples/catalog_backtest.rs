use std::{
    fmt::Debug,
    ops::{Deref, DerefMut},
};

use anyhow::Result;
use nautilus_backtest::{
    config::{
        BacktestDataConfig, BacktestEngineConfig, BacktestRunConfig, BacktestVenueConfig,
        NautilusDataType,
    },
    node::BacktestNode,
};
use nautilus_common::actor::{DataActor, DataActorCore};
use nautilus_indicators::{
    average::ema::ExponentialMovingAverage,
    indicator::{Indicator, MovingAverage},
};
use nautilus_model::{
    data::QuoteTick,
    enums::{AccountType, BookType, OmsType, OrderSide, PriceType},
    identifiers::{InstrumentId, StrategyId},
    types::Quantity,
};
use nautilus_trading::strategy::{Strategy, StrategyConfig, StrategyCore};
use ustr::Ustr;

const CATALOG_PATH: &str = "./data/catalog";

struct EmaCrossover {
    core: StrategyCore,
    instrument_id: InstrumentId,
    trade_size: Quantity,
    ema_fast: ExponentialMovingAverage,
    ema_slow: ExponentialMovingAverage,
    prev_fast_above: Option<bool>,
}

impl EmaCrossover {
    fn new(instrument_id: InstrumentId, trade_size: Quantity, fast: usize, slow: usize) -> Self {
        let config = StrategyConfig {
            strategy_id: Some(StrategyId::from("EMA_CROSSOVER-001")),
            order_id_tag: Some("001".to_string()),
            ..Default::default()
        };
        Self {
            core: StrategyCore::new(config),
            instrument_id,
            trade_size,
            ema_fast: ExponentialMovingAverage::new(fast, Some(PriceType::Mid)),
            ema_slow: ExponentialMovingAverage::new(slow, Some(PriceType::Mid)),
            prev_fast_above: None,
        }
    }
}

// Deref/DerefMut → DataActorCore via self.core (see ema_crossover_backtest.rs)
impl Debug for EmaCrossover {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("EmaCrossover")
            .field("instrument_id", &self.instrument_id)
            .finish()
    }
}

impl DataActor for EmaCrossover {
    fn on_start(&mut self) -> Result<()> {
        self.subscribe_quotes(self.instrument_id, None, None);
        Ok(())
    }

    fn on_stop(&mut self) -> Result<()> {
        self.unsubscribe_quotes(self.instrument_id, None, None);
        Ok(())
    }

    fn on_quote(&mut self, quote: &QuoteTick) -> Result<()> {
        self.ema_fast.handle_quote(quote);
        self.ema_slow.handle_quote(quote);

        if !self.ema_fast.initialized() || !self.ema_slow.initialized() {
            return Ok(());
        }

        let fast_above = self.ema_fast.value() > self.ema_slow.value();

        let cache = self.cache_rc();
        let is_long = !cache.borrow()
            .positions_open(None, Some(&self.instrument_id), None, None, None)
            .is_empty();

        if let Some(prev) = self.prev_fast_above {
            if fast_above && !prev && !is_long {
                let order = self.core.order_factory().market(
                    self.instrument_id,
                    OrderSide::Buy,
                    self.trade_size,
                    None, None, None, None, None, None, None,
                );
                self.submit_order(order, None, None)?;
            } else if !fast_above && prev && is_long {
                self.close_all_positions(self.instrument_id, None, None, None, None, None, None)?;
            }
        }

        self.prev_fast_above = Some(fast_above);
        Ok(())
    }
}

impl Strategy for EmaCrossover {
    fn core(&self) -> &StrategyCore {
        &self.core
    }

    fn core_mut(&mut self) -> &mut StrategyCore {
        &mut self.core
    }
}

fn main() -> Result<()> {
    let catalog_path = std::path::Path::new(CATALOG_PATH);
    if !catalog_path.exists() {
        anyhow::bail!(
            "Catalog not found at {CATALOG_PATH}. Run live_data_collector first."
        );
    }

    let instrument_id = InstrumentId::from("BTCUSDT-PERP.BINANCE");

    // Positional Nones: upstream API has no builder (see rust_trading.md)
    let venue_config = BacktestVenueConfig::new(
        Ustr::from("BINANCE"), OmsType::Netting, AccountType::Margin, BookType::L1_MBP,
        None, None, None, None, None, None, None, None,
        None, None, None, None, None, None, None, None,
        vec!["100000 USDT".to_string()],
        None, None, None, None,
    );

    let data_config = BacktestDataConfig::new(
        NautilusDataType::QuoteTick, CATALOG_PATH.to_string(),
        None, None, Some(instrument_id),
        None, None, None, None, None, None, None, None, None,
    );

    let run_config = BacktestRunConfig::new(
        None, vec![venue_config], vec![data_config],
        BacktestEngineConfig::default(),
        None, None, None, None,
    );

    let mut node = BacktestNode::new(vec![run_config])?;
    node.build()?;

    let config_id = node.configs()[0].id().to_string();
    let engine = node
        .get_engine_mut(&config_id)
        .ok_or_else(|| anyhow::anyhow!("Engine not found"))?;

    engine.add_strategy(EmaCrossover::new(
        instrument_id,
        Quantity::from("0.001"),
        10,
        30,
    ))?;

    let results = node.run()?;
    let result = &results[0];

    println!(
        "Backtest on live catalog data: {} quote ticks, {} orders submitted",
        result.iterations, result.total_orders
    );

    Ok(())
}
