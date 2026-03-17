use std::{
    fmt::Debug,
    ops::{Deref, DerefMut},
    sync::Arc,
};

use ahash::AHashMap;
use anyhow::Result;
use nautilus_backtest::{config::BacktestEngineConfig, engine::BacktestEngine};
use nautilus_common::{
    actor::{DataActor, DataActorCore, DataActorConfig},
    msgbus,
    msgbus::switchboard::get_custom_topic,
};
use nautilus_core::UnixNanos;
use nautilus_execution::models::{fee::FeeModelAny, fill::FillModelAny};
use nautilus_indicators::{
    average::ema::ExponentialMovingAverage,
    indicator::{Indicator, MovingAverage},
};
use nautilus_model::{
    data::{CustomData, DataType, TradeTick},
    enums::{AccountType, AggressorSide, BookType, OmsType, OrderSide},
    identifiers::{InstrumentId, StrategyId, Venue},
    instruments::{Instrument, InstrumentAny, stubs::crypto_perpetual_ethusdt},
    types::{Money, Price, Quantity},
};
use nautilus_persistence_macros::custom_data;
use nautilus_trading::strategy::{Strategy, StrategyConfig, StrategyCore};

#[custom_data]
pub struct MomentumSignal {
    pub value: f64,
    pub ts_event: UnixNanos,
    pub ts_init: UnixNanos,
}

fn register_signal() {
    nautilus_serialization::ensure_custom_data_registered::<MomentumSignal>();
}

struct MomentumActor {
    core: DataActorCore,
    instrument_id: InstrumentId,
    ema_fast: ExponentialMovingAverage,
    ema_slow: ExponentialMovingAverage,
    emit_interval: usize,
    tick_count: usize,
    signals_published: usize,
}

impl MomentumActor {
    fn new(instrument_id: InstrumentId, fast: usize, slow: usize, emit_interval: usize) -> Self {
        Self {
            core: DataActorCore::new(DataActorConfig::default()),
            instrument_id,
            ema_fast: ExponentialMovingAverage::new(fast, None),
            ema_slow: ExponentialMovingAverage::new(slow, None),
            emit_interval,
            tick_count: 0,
            signals_published: 0,
        }
    }
}

// Deref/DerefMut → DataActorCore via self.core (see ema_crossover_backtest.rs)
impl Debug for MomentumActor {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("MomentumActor")
            .field("ticks", &self.tick_count)
            .field("signals", &self.signals_published)
            .finish()
    }
}

impl DataActor for MomentumActor {
    fn on_start(&mut self) -> Result<()> {
        self.subscribe_trades(self.instrument_id, None, None);
        Ok(())
    }

    fn on_stop(&mut self) -> Result<()> {
        self.unsubscribe_trades(self.instrument_id, None, None);
        Ok(())
    }

    fn on_trade(&mut self, trade: &TradeTick) -> Result<()> {
        self.tick_count += 1;
        self.ema_fast.handle_trade(trade);
        self.ema_slow.handle_trade(trade);

        if !self.ema_slow.initialized() {
            return Ok(());
        }

        if self.tick_count % self.emit_interval == 0 {
            let momentum = self.ema_fast.value() - self.ema_slow.value();
            let signal = MomentumSignal {
                value: momentum,
                ts_event: trade.ts_event,
                ts_init: trade.ts_init,
            };
            let custom = CustomData::from_arc(Arc::new(signal));
            let topic = get_custom_topic(&custom.data_type);
            msgbus::publish_any(topic, &custom);
            self.signals_published += 1;
        }

        Ok(())
    }
}

struct MomentumTrader {
    core: StrategyCore,
    instrument_id: InstrumentId,
    trade_size: Quantity,
    entry_threshold: f64,
    prev_momentum: Option<f64>,
    signals_received: usize,
}

impl MomentumTrader {
    fn new(instrument_id: InstrumentId, trade_size: Quantity, entry_threshold: f64) -> Self {
        let config = StrategyConfig {
            strategy_id: Some(StrategyId::from("MOMENTUM_TRADER-001")),
            order_id_tag: Some("001".to_string()),
            ..Default::default()
        };
        Self {
            core: StrategyCore::new(config),
            instrument_id,
            trade_size,
            entry_threshold,
            prev_momentum: None,
            signals_received: 0,
        }
    }
}

// Deref/DerefMut → DataActorCore via self.core (see ema_crossover_backtest.rs)
impl Debug for MomentumTrader {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("MomentumTrader")
            .field("signals_received", &self.signals_received)
            .finish()
    }
}

impl DataActor for MomentumTrader {
    fn on_start(&mut self) -> Result<()> {
        let data_type = DataType::new(stringify!(MomentumSignal), None, None);
        self.subscribe_data(data_type, None, None);
        Ok(())
    }

    fn on_stop(&mut self) -> Result<()> {
        Ok(())
    }

    fn on_data(&mut self, data: &CustomData) -> Result<()> {
        let Some(signal) = data.data.as_any().downcast_ref::<MomentumSignal>() else {
            return Ok(());
        };

        self.signals_received += 1;
        let momentum = signal.value;

        if let Some(prev) = self.prev_momentum {
            let crossed_up = prev <= self.entry_threshold && momentum > self.entry_threshold;
            let crossed_down = prev >= self.entry_threshold && momentum < self.entry_threshold;

            let cache = self.cache_rc();
            let is_long = !cache.borrow()
                .positions_open(None, Some(&self.instrument_id), None, None, None)
                .is_empty();

            if crossed_up && !is_long {
                let order = self.core.order_factory().market(
                    self.instrument_id, OrderSide::Buy, self.trade_size,
                    None, None, None, None, None, None, None,
                );
                self.submit_order(order, None, None)?;
            } else if crossed_down && is_long {
                self.close_all_positions(
                    self.instrument_id, None, None, None, None, None, None,
                )?;
            }
        }

        self.prev_momentum = Some(momentum);
        Ok(())
    }
}

impl Strategy for MomentumTrader {
    fn core(&self) -> &StrategyCore {
        &self.core
    }

    fn core_mut(&mut self) -> &mut StrategyCore {
        &mut self.core
    }
}

fn main() -> Result<()> {
    register_signal();

    let instrument = InstrumentAny::CryptoPerpetual(crypto_perpetual_ethusdt());
    let instrument_id = instrument.id();

    let config = BacktestEngineConfig::default();
    let mut engine = BacktestEngine::new(config)?;

    engine.add_venue(
        Venue::from("BINANCE"),
        OmsType::Netting,
        AccountType::Margin,
        BookType::L1_MBP,
        vec![Money::from("100000 USDT")],
        None, None, AHashMap::new(), None, vec![],
        FillModelAny::default(), FeeModelAny::default(),
        None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
    )?;
    engine.add_instrument(&instrument)?;

    let trades = synthetic_trades(instrument_id, 500);
    engine.add_data(trades, None, true, true);

    engine.add_actor(MomentumActor::new(instrument_id, 10, 30, 20))?;
    engine.add_strategy(MomentumTrader::new(
        instrument_id,
        Quantity::from("0.100"),
        0.0,
    ))?;

    engine.run(None, None, None, false)?;

    let result = engine.get_result();
    println!("Signals actor: {} trades -> strategy: {} orders",
        result.iterations, result.total_orders);

    Ok(())
}

fn synthetic_trades(instrument_id: InstrumentId, n: usize) -> Vec<nautilus_model::data::Data> {
    use nautilus_model::data::Data;
    (0..n).map(|i| {
        let price = 2000.0 + 50.0 * (i as f64 * 0.05).sin();
        let ts = (i as u64) * 500_000_000;
        Data::Trade(TradeTick::new(
            instrument_id,
            Price::new(price, 2),
            Quantity::from("0.100"),
            AggressorSide::Buyer,
            nautilus_model::identifiers::TradeId::new(&format!("T{i}")),
            ts.into(),
            ts.into(),
        ))
    }).collect()
}
