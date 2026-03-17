use std::{
    fmt::Debug,
    ops::{Deref, DerefMut},
    sync::{Arc, Mutex},
    time::Duration,
};

use anyhow::Result;
use nautilus_binance::{
    common::enums::{BinanceEnvironment, BinanceProductType},
    config::{BinanceDataClientConfig, BinanceExecClientConfig},
    factories::{BinanceDataClientFactory, BinanceExecutionClientFactory},
};
use nautilus_common::{
    actor::{DataActor, DataActorCore},
    enums::Environment,
};
use nautilus_live::builder::LiveNodeBuilder;
use nautilus_model::{
    data::TradeTick,
    enums::{OrderSide, TimeInForce},
    events::{
        OrderAccepted, OrderCanceled, OrderModifyRejected, OrderRejected, OrderUpdated,
    },
    identifiers::{AccountId, ClientOrderId, InstrumentId, StrategyId, TraderId},
    orders::Order,
    types::{Price, Quantity},
};
use nautilus_trading::strategy::{Strategy, StrategyConfig, StrategyCore};

const INSTRUMENT_ID: &str = "XRPUSDT-PERP.BINANCE";
const TRADE_SIZE: &str = "5";
const TICK_SIZE: f64 = 0.0001;

#[derive(Debug, Clone, PartialEq)]
enum Phase {
    WaitingForPrice,
    LimitSubmitted,
    ModifySubmitted,
    InvalidModifySubmitted,
    CancelSubmitted,
    RejectionTestSubmitted,
    Done,
}

struct EventLog {
    accepted: Vec<String>,
    updated: Vec<String>,
    modify_rejected: Vec<String>,
    rejected: Vec<String>,
    canceled: Vec<String>,
}

impl EventLog {
    fn new() -> Self {
        Self {
            accepted: Vec::new(),
            updated: Vec::new(),
            modify_rejected: Vec::new(),
            rejected: Vec::new(),
            canceled: Vec::new(),
        }
    }
}

struct ModifyOrderStrategy {
    core: StrategyCore,
    instrument_id: InstrumentId,
    phase: Phase,
    order_id: Option<ClientOrderId>,
    last_price: Option<f64>,
    events: Arc<Mutex<EventLog>>,
}

impl ModifyOrderStrategy {
    fn new(instrument_id: InstrumentId, events: Arc<Mutex<EventLog>>) -> Self {
        let config = StrategyConfig {
            strategy_id: Some(StrategyId::from("MODIFY-TEST-001")),
            order_id_tag: Some("002".to_string()),
            ..Default::default()
        };
        Self {
            core: StrategyCore::new(config),
            instrument_id,
            phase: Phase::WaitingForPrice,
            order_id: None,
            last_price: None,
            events,
        }
    }

    fn modify_current_order(&mut self, new_price: Price) -> Result<()> {
        if let Some(order_id) = self.order_id {
            let order_opt = {
                let cache = self.cache_rc();
                let guard = cache.borrow();
                guard.order(&order_id).cloned()
            };
            if let Some(order) = order_opt {
                if order.is_open() {
                    self.modify_order(order, None, Some(new_price), None, None)?;
                }
            }
        }
        Ok(())
    }
}

// Deref/DerefMut → DataActorCore via self.core (see ema_crossover_backtest.rs)
impl Debug for ModifyOrderStrategy {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("ModifyOrderStrategy")
            .field("phase", &self.phase)
            .finish()
    }
}

impl DataActor for ModifyOrderStrategy {
    fn on_start(&mut self) -> Result<()> {
        self.subscribe_trades(self.instrument_id, None, None);
        Ok(())
    }

    fn on_stop(&mut self) -> Result<()> {
        Ok(())
    }

    fn on_trade(&mut self, trade: &TradeTick) -> Result<()> {
        if self.phase == Phase::WaitingForPrice {
            let price: f64 = (&trade.price).into();
            self.last_price = Some(price);
            println!("[MODIFY-TEST] Last price: {price:.4} USDT");

            let limit_price_f64 = (price * 0.95 / TICK_SIZE).round() * TICK_SIZE;
            let limit_price = Price::new(limit_price_f64, 4);

            let order = self.core.order_factory().limit(
                self.instrument_id,
                OrderSide::Buy,
                Quantity::from(TRADE_SIZE),
                limit_price,
                Some(TimeInForce::Gtc),
                None, None, None, None, None, None, None, None, None, None, None,
            );
            self.order_id = Some(order.client_order_id());
            println!("[MODIFY-TEST] Submitting limit buy at {limit_price} (-5%)");
            self.submit_order(order, None, None)?;
            self.phase = Phase::LimitSubmitted;
        }
        Ok(())
    }

    fn on_order_filled(&mut self, _event: &nautilus_model::events::OrderFilled) -> Result<()> {
        Ok(())
    }

    fn on_order_canceled(&mut self, event: &OrderCanceled) -> Result<()> {
        let msg = format!("order={}", event.client_order_id);
        println!("[CANCELED] {msg}");
        self.events.lock().unwrap().canceled.push(msg);

        if self.phase == Phase::CancelSubmitted {
            let Some(last_price) = self.last_price else {
                return Ok(());
            };
            let absurd_price_f64 = (last_price * 10.0 / TICK_SIZE).round() * TICK_SIZE;
            let absurd_price = Price::new(absurd_price_f64, 4);

            let order = self.core.order_factory().limit(
                self.instrument_id,
                OrderSide::Buy,
                Quantity::from(TRADE_SIZE),
                absurd_price,
                Some(TimeInForce::Gtc),
                None, None, None, None, None, None, None, None, None, None, None,
            );
            println!("[MODIFY-TEST] Submitting limit buy at {absurd_price} (10x — should be rejected)");
            self.submit_order(order, None, None)?;
            self.phase = Phase::RejectionTestSubmitted;
        }
        Ok(())
    }
}

impl Strategy for ModifyOrderStrategy {
    fn core(&self) -> &StrategyCore {
        &self.core
    }

    fn core_mut(&mut self) -> &mut StrategyCore {
        &mut self.core
    }

    fn on_order_accepted(&mut self, event: OrderAccepted) {
        let msg = format!("order={}", event.client_order_id);
        println!("[ACCEPTED] {msg}");
        self.events.lock().unwrap().accepted.push(msg);

        if self.phase == Phase::LimitSubmitted && Some(event.client_order_id) == self.order_id {
            let Some(last_price) = self.last_price else {
                return;
            };
            let new_price_f64 = (last_price * 0.96 / TICK_SIZE).round() * TICK_SIZE;
            let new_price = Price::new(new_price_f64, 4);
            println!("[MODIFY-TEST] Order accepted — modifying to {new_price} (-4%)");
            if let Err(e) = self.modify_current_order(new_price) {
                println!("[MODIFY-TEST] modify_order error: {e}");
            }
            self.phase = Phase::ModifySubmitted;
        }
    }

    fn on_order_updated(&mut self, event: OrderUpdated) {
        let msg = format!("order={} new_price={}", event.client_order_id, event.price.unwrap_or_default());
        println!("[UPDATED] {msg}");
        self.events.lock().unwrap().updated.push(msg);

        if self.phase == Phase::ModifySubmitted && Some(event.client_order_id) == self.order_id {
            let zero_price = Price::from("0.0001");
            println!("[MODIFY-TEST] Order updated — attempting invalid modify to {zero_price}");
            if let Err(e) = self.modify_current_order(zero_price) {
                println!("[MODIFY-TEST] modify_order error: {e}");
            }
            self.phase = Phase::InvalidModifySubmitted;
        }
    }

    fn on_order_modify_rejected(&mut self, event: OrderModifyRejected) {
        let msg = format!("order={} reason={}", event.client_order_id, event.reason);
        println!("[MODIFY-REJECTED] {msg}");
        self.events.lock().unwrap().modify_rejected.push(msg);

        if self.phase == Phase::InvalidModifySubmitted {
            println!("[MODIFY-TEST] Modify rejected as expected — canceling order");
            self.cancel_all_orders(self.instrument_id, None, None)
                .unwrap_or_else(|e| println!("[MODIFY-TEST] cancel error: {e}"));
            self.phase = Phase::CancelSubmitted;
        }
    }

    fn on_order_rejected(&mut self, event: OrderRejected) {
        let msg = format!("order={} reason={}", event.client_order_id, event.reason);
        println!("[REJECTED] {msg}");
        self.events.lock().unwrap().rejected.push(msg);

        if self.phase == Phase::RejectionTestSubmitted {
            println!("[MODIFY-TEST] Rejection received as expected — Done.");
            self.phase = Phase::Done;
        }
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let _ = dotenvy::from_filename("../../.env");

    let api_key = std::env::var("BINANCE_LINEAR_API_KEY")
        .ok()
        .filter(|s| !s.is_empty());
    let api_secret = std::env::var("BINANCE_LINEAR_API_SECRET")
        .ok()
        .filter(|s| !s.is_empty());

    if api_key.is_none() {
        anyhow::bail!("BINANCE_LINEAR_API_KEY must be set in .env");
    }

    let trader_id = TraderId::from("MODIFY-TESTER-001");

    let data_config = BinanceDataClientConfig {
        product_types: vec![BinanceProductType::UsdM],
        environment: BinanceEnvironment::Mainnet,
        base_url_http: None,
        base_url_ws: None,
        api_key: api_key.clone(),
        api_secret: api_secret.clone(),
    };

    let exec_config = BinanceExecClientConfig {
        trader_id: trader_id.clone(),
        account_id: AccountId::from("BINANCE-002"),
        product_types: vec![BinanceProductType::UsdM],
        environment: BinanceEnvironment::Mainnet,
        base_url_http: None,
        base_url_ws: None,
        base_url_ws_trading: None,
        use_ws_trading: true,
        api_key,
        api_secret,
    };

    let instrument_id = InstrumentId::from(INSTRUMENT_ID);
    let events: Arc<Mutex<EventLog>> = Arc::new(Mutex::new(EventLog::new()));

    let mut node = LiveNodeBuilder::new(trader_id, Environment::Live)?
        .with_timeout_connection(30)
        .with_reconciliation(false)
        .add_data_client(
            None,
            Box::new(BinanceDataClientFactory::new()),
            Box::new(data_config),
        )?
        .add_exec_client(
            None,
            Box::new(BinanceExecutionClientFactory::new()),
            Box::new(exec_config),
        )?
        .build()?;

    node.add_strategy(ModifyOrderStrategy::new(instrument_id, Arc::clone(&events)))?;

    println!("Connecting to Binance UsdM for modify_order test...");
    println!("Sequence: limit buy → modify → invalid modify → cancel → rejection test");

    tokio::select! {
        result = node.run() => result?,
        _ = tokio::time::sleep(Duration::from_secs(60)) => {
            println!("\n60s elapsed — stopping node");
            node.stop().await?;
        }
        _ = tokio::signal::ctrl_c() => {
            println!("\nInterrupted — stopping node");
            node.stop().await?;
        }
    }

    let ev = events.lock().unwrap();
    println!("\n=== Modify Order Test Results ===");
    println!("on_order_accepted:        {} events", ev.accepted.len());
    for e in &ev.accepted { println!("  {e}"); }
    println!("on_order_updated:         {} events", ev.updated.len());
    for e in &ev.updated { println!("  {e}"); }
    println!("on_order_modify_rejected: {} events", ev.modify_rejected.len());
    for e in &ev.modify_rejected { println!("  {e}"); }
    println!("on_order_canceled:        {} events", ev.canceled.len());
    for e in &ev.canceled { println!("  {e}"); }
    println!("on_order_rejected:        {} events", ev.rejected.len());
    for e in &ev.rejected { println!("  {e}"); }

    let pass = !ev.accepted.is_empty()
        && !ev.updated.is_empty()
        && !ev.modify_rejected.is_empty()
        && !ev.rejected.is_empty();
    if pass {
        println!("\nPASS: All 4 callbacks fired");
    } else {
        println!("\nFAIL: Not all callbacks fired — check output above");
    }

    Ok(())
}
