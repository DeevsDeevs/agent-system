use std::{
    fmt::Debug,
    ops::{Deref, DerefMut},
};

use ahash::AHashMap;
use anyhow::Result;
use nautilus_backtest::{config::BacktestEngineConfig, engine::BacktestEngine};
use nautilus_common::actor::{DataActor, DataActorCore};
use nautilus_core::UnixNanos;
use nautilus_execution::models::{fee::FeeModelAny, fill::FillModelAny};
use nautilus_model::{
    data::{Data, TradeTick},
    enums::{AccountType, AggressorSide, BookType, OmsType, OrderSide, TimeInForce, TriggerType},
    events::OrderFilled,
    identifiers::{ClientOrderId, InstrumentId, StrategyId, TradeId, Venue},
    instruments::{Instrument, InstrumentAny, stubs::crypto_perpetual_ethusdt},
    orders::Order,
    types::{Money, Price, Quantity},
};
use nautilus_trading::strategy::{Strategy, StrategyConfig, StrategyCore};

const TRADE_SIZE: &str = "0.010";
const SL_PCT: f64 = 0.015;
const TP_PCT: f64 = 0.015;

// BUG: order_factory().bracket() + submit_order_list() panics in backtest due to
// double borrow_mut on RefCell<Cache> when assigning position IDs to OTO children
// (execution/src/engine/mod.rs:1520). Implement brackets manually until fixed.
//
// BUG: StopMarket + BookType::L1_MBP hits todo!("Exhausted simulated book volume")
// in matching_engine/engine.rs:3431. Use StopLimit (trigger == limit) as workaround.

#[derive(Debug, Clone, PartialEq)]
enum Phase {
    Flat,
    EntrySubmitted,
    Active,
}

struct BracketStrategy {
    core: StrategyCore,
    instrument_id: InstrumentId,
    trade_size: Quantity,
    last_price: Option<f64>,
    phase: Phase,
    sl_order_id: Option<ClientOrderId>,
    tp_order_id: Option<ClientOrderId>,
    brackets_placed: usize,
    exits: usize,
}

impl BracketStrategy {
    fn new(instrument_id: InstrumentId, trade_size: Quantity) -> Self {
        let config = StrategyConfig {
            strategy_id: Some(StrategyId::from("BRACKET-001")),
            order_id_tag: Some("001".to_string()),
            ..Default::default()
        };
        Self {
            core: StrategyCore::new(config),
            instrument_id,
            trade_size,
            last_price: None,
            phase: Phase::Flat,
            sl_order_id: None,
            tp_order_id: None,
            brackets_placed: 0,
            exits: 0,
        }
    }

    fn price(raw: f64, decimals: u8) -> Price {
        Price::new(raw, decimals)
    }
}

// Deref/DerefMut → DataActorCore via self.core (see ema_crossover_backtest.rs)
impl Debug for BracketStrategy {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("BracketStrategy")
            .field("phase", &self.phase)
            .field("brackets", &self.brackets_placed)
            .field("exits", &self.exits)
            .finish()
    }
}

impl DataActor for BracketStrategy {
    fn on_start(&mut self) -> Result<()> {
        self.subscribe_trades(self.instrument_id, None, None);
        Ok(())
    }

    fn on_stop(&mut self) -> Result<()> {
        self.unsubscribe_trades(self.instrument_id, None, None);
        Ok(())
    }

    fn on_trade(&mut self, trade: &TradeTick) -> Result<()> {
        let price: f64 = (&trade.price).into();
        self.last_price = Some(price);

        if self.phase != Phase::Flat {
            return Ok(());
        }

        let entry = self.core.order_factory().market(
            self.instrument_id,
            OrderSide::Buy,
            self.trade_size,
            None, None, None, None, None, None, None,
        );
        println!("[BRACKET] Market entry at ~{price:.2} (sl={:.2}, tp={:.2})",
            price * (1.0 - SL_PCT), price * (1.0 + TP_PCT));
        self.submit_order(entry, None, None)?;
        self.phase = Phase::EntrySubmitted;
        self.brackets_placed += 1;

        Ok(())
    }

    fn on_order_filled(&mut self, event: &OrderFilled) -> Result<()> {
        let fill_px: f64 = (&event.last_px).into();
        println!("[FILL] side={} qty={} price={}", event.order_side, event.last_qty, event.last_px);

        match event.order_side {
            OrderSide::Buy if self.phase == Phase::EntrySubmitted => {
                let sl_price = Self::price(fill_px * (1.0 - SL_PCT), 2);
                let tp_price = Self::price(fill_px * (1.0 + TP_PCT), 2);

                let sl = self.core.order_factory().stop_limit(
                    self.instrument_id,
                    OrderSide::Sell,
                    self.trade_size,
                    sl_price,
                    sl_price,
                    Some(TriggerType::LastPrice),
                    Some(TimeInForce::Gtc),
                    None, None, None, None, None, None, None, None, None, None, None,
                );
                let tp = self.core.order_factory().limit(
                    self.instrument_id,
                    OrderSide::Sell,
                    self.trade_size,
                    tp_price,
                    Some(TimeInForce::Gtc),
                    None, None, None, None, None, None, None, None, None, None, None,
                );

                self.sl_order_id = Some(sl.client_order_id());
                self.tp_order_id = Some(tp.client_order_id());

                println!("[BRACKET] SL at {sl_price}, TP at {tp_price}");
                self.submit_order(sl, None, None)?;
                self.submit_order(tp, None, None)?;
                self.phase = Phase::Active;
            }

            OrderSide::Sell if self.phase == Phase::Active => {
                self.exits += 1;
                let cancel_id = if Some(event.client_order_id) == self.sl_order_id {
                    self.tp_order_id
                } else {
                    self.sl_order_id
                };

                if let Some(id_to_cancel) = cancel_id {
                    let cache = self.cache_rc();
                    let order_opt = cache.borrow().order(&id_to_cancel).cloned();
                    if let Some(order) = order_opt {
                        if order.is_open() {
                            self.cancel_order(order, None)?;
                        }
                    }
                }

                self.sl_order_id = None;
                self.tp_order_id = None;
                self.phase = Phase::Flat;
            }

            _ => {}
        }

        Ok(())
    }
}

impl Strategy for BracketStrategy {
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

    // Positional Nones: upstream API has no builder (see rust_trading.md)
    engine.add_venue(
        Venue::from("BINANCE"), OmsType::Netting, AccountType::Margin, BookType::L1_MBP,
        vec![Money::from("10000 USDT")],
        None, None, AHashMap::new(), None, vec![],
        FillModelAny::default(), FeeModelAny::default(),
        None, None, None, None, None, None, None, None,
        None, None, Some(true),  // support_contingent_orders
        Some(false),
        None, None, None, None, None,
    )?;
    engine.add_instrument(&instrument)?;

    engine.add_data(zigzag_trades(instrument_id, 800), None, true, true);

    engine.add_strategy(BracketStrategy::new(instrument_id, Quantity::from(TRADE_SIZE)))?;

    engine.run(None, None, None, false)?;

    let result = engine.get_result();
    println!(
        "Bracket backtest: {} ticks, {} orders submitted",
        result.iterations, result.total_orders,
    );

    Ok(())
}

fn zigzag_trades(instrument_id: InstrumentId, n: usize) -> Vec<Data> {
    let period = 200usize;
    (0..n)
        .map(|i| {
            let phase = (i % period) as f64 / period as f64;
            let mid = if phase < 0.5 {
                2000.0 + 100.0 * (phase * 2.0)
            } else {
                2100.0 - 100.0 * ((phase - 0.5) * 2.0)
            };
            let ts = UnixNanos::from((i as u64) * 500_000_000);
            Data::Trade(TradeTick::new(
                instrument_id,
                Price::new(mid, 2),
                Quantity::from("10.000"),
                AggressorSide::Buyer,
                TradeId::new(&format!("T{i}")),
                ts,
                ts,
            ))
        })
        .collect()
}
