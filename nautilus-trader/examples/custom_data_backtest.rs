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
use nautilus_model::{
    data::{CustomData, DataType, TradeTick},
    enums::{AccountType, AggressorSide, BookType, OmsType},
    identifiers::{InstrumentId, Venue},
    instruments::{Instrument, InstrumentAny, stubs::crypto_perpetual_ethusdt},
    types::{Money, Price, Quantity},
};
use nautilus_persistence_macros::custom_data;

#[custom_data]
pub struct TradeImbalance {
    pub instrument_id: InstrumentId,
    pub buy_volume: f64,
    pub sell_volume: f64,
    pub imbalance: f64,
    pub window_size: u32,
    pub ts_event: UnixNanos,
    pub ts_init: UnixNanos,
}

fn imbalance_data_type() -> DataType {
    DataType::new(stringify!(TradeImbalance), None, None)
}

fn register_types() {
    nautilus_serialization::ensure_custom_data_registered::<TradeImbalance>();
}

struct ImbalanceCollector {
    core: DataActorCore,
    instrument_id: InstrumentId,
    window: usize,
    buy_vol: f64,
    sell_vol: f64,
    count: usize,
    snapshots_published: usize,
}

impl ImbalanceCollector {
    fn new(instrument_id: InstrumentId, window: usize) -> Self {
        Self {
            core: DataActorCore::new(DataActorConfig::default()),
            instrument_id,
            window,
            buy_vol: 0.0,
            sell_vol: 0.0,
            count: 0,
            snapshots_published: 0,
        }
    }
}

impl Deref for ImbalanceCollector {
    type Target = DataActorCore;
    fn deref(&self) -> &Self::Target {
        &self.core
    }
}

impl DerefMut for ImbalanceCollector {
    fn deref_mut(&mut self) -> &mut Self::Target {
        &mut self.core
    }
}

impl Debug for ImbalanceCollector {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ImbalanceCollector")
            .field("snapshots_published", &self.snapshots_published)
            .finish()
    }
}

impl DataActor for ImbalanceCollector {
    fn on_start(&mut self) -> Result<()> {
        self.subscribe_trades(self.instrument_id, None, None);
        Ok(())
    }

    fn on_stop(&mut self) -> Result<()> {
        self.unsubscribe_trades(self.instrument_id, None, None);
        Ok(())
    }

    fn on_trade(&mut self, trade: &TradeTick) -> Result<()> {
        let qty: f64 = (&trade.size).into();

        if trade.aggressor_side == AggressorSide::Buyer {
            self.buy_vol += qty;
        } else {
            self.sell_vol += qty;
        }

        self.count += 1;

        if self.count % self.window == 0 {
            let total = self.buy_vol + self.sell_vol;
            let imbalance = if total > 0.0 { (self.buy_vol - self.sell_vol).abs() / total } else { 0.0 };

            let snapshot = TradeImbalance {
                instrument_id: self.instrument_id,
                buy_volume: self.buy_vol,
                sell_volume: self.sell_vol,
                imbalance,
                window_size: self.window as u32,
                ts_event: trade.ts_event,
                ts_init: trade.ts_init,
            };

            let custom = CustomData::from_arc(Arc::new(snapshot));
            let topic = get_custom_topic(&custom.data_type);
            msgbus::publish_any(topic, &custom);

            self.buy_vol = 0.0;
            self.sell_vol = 0.0;
            self.snapshots_published += 1;
        }

        Ok(())
    }
}

struct ImbalanceObserver {
    core: DataActorCore,
    snapshots_received: usize,
}

impl ImbalanceObserver {
    fn new() -> Self {
        Self {
            core: DataActorCore::new(DataActorConfig::default()),
            snapshots_received: 0,
        }
    }
}

impl Deref for ImbalanceObserver {
    type Target = DataActorCore;
    fn deref(&self) -> &Self::Target {
        &self.core
    }
}

impl DerefMut for ImbalanceObserver {
    fn deref_mut(&mut self) -> &mut Self::Target {
        &mut self.core
    }
}

impl Debug for ImbalanceObserver {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ImbalanceObserver")
            .field("snapshots_received", &self.snapshots_received)
            .finish()
    }
}

impl DataActor for ImbalanceObserver {
    fn on_start(&mut self) -> Result<()> {
        self.subscribe_data(imbalance_data_type(), None, None);
        Ok(())
    }

    fn on_stop(&mut self) -> Result<()> {
        Ok(())
    }

    fn on_data(&mut self, data: &CustomData) -> Result<()> {
        if let Some(snap) = data.data.as_any().downcast_ref::<TradeImbalance>() {
            self.snapshots_received += 1;
            println!(
                "[IMB] {:.4}  buy={:.3}  sell={:.3}  (window={})",
                snap.imbalance, snap.buy_volume, snap.sell_volume, snap.window_size
            );
        }
        Ok(())
    }
}

fn main() -> Result<()> {
    register_types();

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

    let trades = synthetic_trades(instrument_id, 200);
    engine.add_data(trades, None, true, true);

    engine.add_actor(ImbalanceCollector::new(instrument_id, 20))?;
    engine.add_actor(ImbalanceObserver::new())?;

    engine.run(None, None, None, false)?;

    let result = engine.get_result();
    println!("\nBacktest complete: {} trade ticks processed", result.iterations);

    Ok(())
}

fn synthetic_trades(instrument_id: InstrumentId, n: usize) -> Vec<nautilus_model::data::Data> {
    use nautilus_model::data::Data;
    (0..n).map(|i| {
        let price = 2000.0 + 10.0 * (i as f64 * 0.1).sin();
        let side = if i % 3 == 0 { AggressorSide::Seller } else { AggressorSide::Buyer };
        let ts = (i as u64) * 1_000_000_000;
        Data::Trade(TradeTick::new(
            instrument_id,
            Price::new(price, 2),
            Quantity::from("0.100"),
            side,
            nautilus_model::identifiers::TradeId::new(&format!("T{i}")),
            ts.into(),
            ts.into(),
        ))
    }).collect()
}
