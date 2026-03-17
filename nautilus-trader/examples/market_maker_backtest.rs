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
    data::{Data, QuoteTick},
    enums::{AccountType, BookType, OmsType, OrderSide, TimeInForce},
    identifiers::{ClientOrderId, InstrumentId, StrategyId, Venue},
    instruments::{Instrument, InstrumentAny, stubs::crypto_perpetual_ethusdt},
    orders::Order,
    types::{Money, Price, Quantity},
};
use nautilus_trading::strategy::{Strategy, StrategyConfig, StrategyCore};

const HALF_SPREAD: f64 = 0.5;
const TRADE_SIZE: &str = "0.010";

struct SimpleMarketMaker {
    core: StrategyCore,
    instrument_id: InstrumentId,
    trade_size: Quantity,
    bid_order_id: Option<ClientOrderId>,
    ask_order_id: Option<ClientOrderId>,
    quote_count: usize,
    order_count: usize,
    modify_count: usize,
}

impl SimpleMarketMaker {
    fn new(instrument_id: InstrumentId, trade_size: Quantity) -> Self {
        let config = StrategyConfig {
            strategy_id: Some(StrategyId::from("MARKET-MAKER-001")),
            order_id_tag: Some("001".to_string()),
            ..Default::default()
        };
        Self {
            core: StrategyCore::new(config),
            instrument_id,
            trade_size,
            bid_order_id: None,
            ask_order_id: None,
            quote_count: 0,
            order_count: 0,
            modify_count: 0,
        }
    }

    fn price(raw: f64, decimals: u8) -> Price {
        Price::new(raw, decimals)
    }

    fn manage_side(
        &mut self,
        side: OrderSide,
        new_price: Price,
        stored_id: Option<ClientOrderId>,
    ) -> Result<Option<ClientOrderId>> {
        if let Some(id) = stored_id {
            let order_opt = {
                let cache = self.cache_rc();
                let guard = cache.borrow();
                guard.order(&id).cloned()
            };
            if let Some(order) = order_opt {
                if order.is_open() {
                    self.modify_order(order, None, Some(new_price), None, None)?;
                    self.modify_count += 1;
                    return Ok(Some(id));
                }
            }
        }

        let order = self.core.order_factory().limit(
            self.instrument_id,
            side,
            self.trade_size,
            new_price,
            Some(TimeInForce::Gtc),
            None, None, None, None, None, None, None, None, None, None, None,
        );
        let new_id = order.client_order_id();
        self.submit_order(order, None, None)?;
        self.order_count += 1;
        Ok(Some(new_id))
    }
}

// Deref/DerefMut → DataActorCore via self.core (see ema_crossover_backtest.rs)
impl Debug for SimpleMarketMaker {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SimpleMarketMaker")
            .field("quotes", &self.quote_count)
            .field("orders", &self.order_count)
            .field("modifies", &self.modify_count)
            .finish()
    }
}

impl DataActor for SimpleMarketMaker {
    fn on_start(&mut self) -> Result<()> {
        self.subscribe_quotes(self.instrument_id, None, None);
        Ok(())
    }

    fn on_stop(&mut self) -> Result<()> {
        self.unsubscribe_quotes(self.instrument_id, None, None);
        Ok(())
    }

    fn on_quote(&mut self, quote: &QuoteTick) -> Result<()> {
        self.quote_count += 1;

        let bid_px: f64 = (&quote.bid_price).into();
        let ask_px: f64 = (&quote.ask_price).into();
        let mid = (bid_px + ask_px) / 2.0;

        let new_bid = Self::price(mid - HALF_SPREAD, 2);
        let new_ask = Self::price(mid + HALF_SPREAD, 2);

        let bid_id = self.bid_order_id;
        self.bid_order_id = self.manage_side(OrderSide::Buy, new_bid, bid_id)?;

        let ask_id = self.ask_order_id;
        self.ask_order_id = self.manage_side(OrderSide::Sell, new_ask, ask_id)?;

        Ok(())
    }
}

impl Strategy for SimpleMarketMaker {
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
        vec![Money::from("10000 USDT")],
        None, None, AHashMap::new(), None, vec![],
        FillModelAny::default(), FeeModelAny::default(),
        None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
    )?;
    engine.add_instrument(&instrument)?;

    engine.add_data(synthetic_quotes(instrument_id, 300), None, true, true);

    engine.add_strategy(SimpleMarketMaker::new(instrument_id, Quantity::from(TRADE_SIZE)))?;

    engine.run(None, None, None, false)?;

    let result = engine.get_result();
    println!(
        "Market maker: {} quotes, {} orders submitted",
        result.iterations, result.total_orders,
    );

    Ok(())
}

fn synthetic_quotes(instrument_id: InstrumentId, n: usize) -> Vec<Data> {
    (0..n)
        .map(|i| {
            let mid = 2000.0_f64 + 30.0 * (i as f64 * 0.05).sin();
            let bid = mid - 0.25;
            let ask = mid + 0.25;
            let ts = UnixNanos::from((i as u64) * 1_000_000_000);
            Data::Quote(QuoteTick::new(
                instrument_id,
                Price::new(bid, 2),
                Price::new(ask, 2),
                Quantity::from("1.000"),
                Quantity::from("1.000"),
                ts,
                ts,
            ))
        })
        .collect()
}
