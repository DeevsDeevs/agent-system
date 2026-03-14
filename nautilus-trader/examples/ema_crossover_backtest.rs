use std::{
    fmt::Debug,
    ops::{Deref, DerefMut},
};

use ahash::AHashMap;
use anyhow::Result;
use nautilus_backtest::{config::BacktestEngineConfig, engine::BacktestEngine};
use nautilus_common::actor::{DataActor, DataActorCore};
use nautilus_execution::models::{fee::FeeModelAny, fill::FillModelAny};
use nautilus_indicators::{
    average::ema::ExponentialMovingAverage,
    indicator::{Indicator, MovingAverage},
};
use nautilus_model::{
    data::{Data, QuoteTick},
    enums::{AccountType, BookType, OmsType, OrderSide, PriceType},
    identifiers::{InstrumentId, StrategyId, Venue},
    instruments::{Instrument, InstrumentAny, stubs::crypto_perpetual_ethusdt},
    types::{Money, Price, Quantity},
};
use nautilus_trading::strategy::{Strategy, StrategyConfig, StrategyCore};

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

    fn enter(&mut self, side: OrderSide) -> Result<()> {
        let order = self.core.order_factory().market(
            self.instrument_id,
            side,
            self.trade_size,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
        );
        self.submit_order(order, None, None)
    }
}

impl Deref for EmaCrossover {
    type Target = DataActorCore;
    fn deref(&self) -> &Self::Target {
        &self.core
    }
}

impl DerefMut for EmaCrossover {
    fn deref_mut(&mut self) -> &mut Self::Target {
        &mut self.core
    }
}

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

        if let Some(prev) = self.prev_fast_above {
            if fast_above && !prev {
                self.enter(OrderSide::Buy)?;
            } else if !fast_above && prev {
                self.enter(OrderSide::Sell)?;
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
        None,
        None,
        AHashMap::new(),
        None,
        vec![],
        FillModelAny::default(),
        FeeModelAny::default(),
        None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
    )?;
    engine.add_instrument(&instrument)?;

    let quotes = synthetic_quotes(instrument_id, 500);
    engine.add_data(quotes, None, true, true);

    engine.add_strategy(EmaCrossover::new(
        instrument_id,
        Quantity::from("0.100"),
        10,
        30,
    ))?;

    engine.run(None, None, None, false)?;

    let result = engine.get_result();
    println!("Backtest complete: {} iterations, {} orders",
        result.iterations, result.total_orders);

    Ok(())
}

fn synthetic_quotes(instrument_id: InstrumentId, n: usize) -> Vec<Data> {
    (0..n).map(|i| {
        let mid = 2000.0 + 50.0 * (i as f64 * 0.05).sin();
        let bid = Price::from(format!("{:.2}", mid - 0.25).as_str());
        let ask = Price::from(format!("{:.2}", mid + 0.25).as_str());
        let qty = Quantity::from("1.000");
        let ts = (i as u64) * 1_000_000_000;
        Data::Quote(QuoteTick::new(instrument_id, bid, ask, qty, qty, ts.into(), ts.into()))
    }).collect()
}
