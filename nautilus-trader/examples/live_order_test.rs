use std::{
    fmt::Debug,
    ops::{Deref, DerefMut},
    sync::{Arc, Mutex},
    time::{Duration, Instant},
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
    events::{OrderAccepted, OrderCanceled, OrderFilled},
    identifiers::{AccountId, ClientOrderId, InstrumentId, StrategyId, TraderId},
    orders::Order,
    types::{Price, Quantity},
};
use nautilus_trading::strategy::{Strategy, StrategyConfig, StrategyCore};

const INSTRUMENT_ID: &str = "XRPUSDT-PERP.BINANCE";
const TRADE_SIZE: &str = "5";
const TICK_SIZE: f64 = 0.0001;
const CANCEL_AFTER_SECS: u64 = 5;

#[derive(Debug, Clone, PartialEq)]
enum Phase {
    WaitingForPrice,
    MarketBuySubmitted,
    LimitSellSubmitted,
    FlatteningWithMarketSell,
    Done,
}

struct OrderTestStrategy {
    core: StrategyCore,
    instrument_id: InstrumentId,
    phase: Phase,
    limit_order_id: Option<ClientOrderId>,
    last_price: Option<f64>,
    limit_accepted_at: Option<Instant>,
    fills_received: Arc<Mutex<Vec<String>>>,
}

impl OrderTestStrategy {
    fn new(instrument_id: InstrumentId, fills_received: Arc<Mutex<Vec<String>>>) -> Self {
        let config = StrategyConfig {
            strategy_id: Some(StrategyId::from("ORDER-TEST-001")),
            order_id_tag: Some("001".to_string()),
            ..Default::default()
        };
        Self {
            core: StrategyCore::new(config),
            instrument_id,
            phase: Phase::WaitingForPrice,
            limit_order_id: None,
            last_price: None,
            limit_accepted_at: None,
            fills_received,
        }
    }
}

impl Deref for OrderTestStrategy {
    type Target = DataActorCore;
    fn deref(&self) -> &Self::Target {
        &self.core
    }
}

impl DerefMut for OrderTestStrategy {
    fn deref_mut(&mut self) -> &mut Self::Target {
        &mut self.core
    }
}

impl Debug for OrderTestStrategy {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("OrderTestStrategy")
            .field("phase", &self.phase)
            .field("fills", &self.fills_received.lock().unwrap().len())
            .finish()
    }
}

impl DataActor for OrderTestStrategy {
    fn on_start(&mut self) -> Result<()> {
        self.subscribe_trades(self.instrument_id, None, None);
        Ok(())
    }

    fn on_stop(&mut self) -> Result<()> {
        self.unsubscribe_trades(self.instrument_id, None, None);
        Ok(())
    }

    fn on_trade(&mut self, trade: &TradeTick) -> Result<()> {
        match self.phase {
            Phase::WaitingForPrice => {
                let last_price: f64 = (&trade.price).into();
                self.last_price = Some(last_price);
                println!("[ORDER-TEST] Last trade price: {last_price:.4} USDT");

                let market_order = self.core.order_factory().market(
                    self.instrument_id,
                    OrderSide::Buy,
                    Quantity::from(TRADE_SIZE),
                    None, None, None, None, None, None, None,
                );
                println!("[ORDER-TEST] Submitting market buy {TRADE_SIZE} XRP");
                self.submit_order(market_order, None, None)?;
                self.phase = Phase::MarketBuySubmitted;
            }

            Phase::LimitSellSubmitted => {
                // Cancel from on_trade (while live) keeps trading channel open,
                // unlike on_stop where the channel is already closed
                if let Some(accepted_at) = self.limit_accepted_at {
                    if accepted_at.elapsed() >= Duration::from_secs(CANCEL_AFTER_SECS) {
                        println!("[ORDER-TEST] {CANCEL_AFTER_SECS}s elapsed — canceling limit sell");
                        self.cancel_all_orders(self.instrument_id, None, None)?;
                        self.limit_accepted_at = None;
                    }
                }
            }

            _ => {}
        }

        Ok(())
    }

    fn on_order_filled(&mut self, event: &OrderFilled) -> Result<()> {
        let msg = format!(
            "[FILL] side={} qty={} price={}",
            event.order_side, event.last_qty, event.last_px
        );
        println!("{msg}");
        self.fills_received.lock().unwrap().push(msg);

        if self.phase == Phase::MarketBuySubmitted && event.order_side == OrderSide::Buy {
            let last_price = self.last_price.unwrap_or((&event.last_px).into());
            let limit_price_f64 = (last_price * 1.10 / TICK_SIZE).round() * TICK_SIZE;
            let limit_price = Price::from(format!("{:.4}", limit_price_f64).as_str());

            let limit_order = self.core.order_factory().limit(
                self.instrument_id,
                OrderSide::Sell,
                Quantity::from(TRADE_SIZE),
                limit_price,
                Some(TimeInForce::Gtc),
                None, None, None, None, None, None, None, None, None, None, None,
            );
            self.limit_order_id = Some(limit_order.client_order_id());
            println!("[ORDER-TEST] Market buy filled — submitting limit sell at {limit_price} USDT (GTC)");
            self.submit_order(limit_order, None, None)?;
            self.phase = Phase::LimitSellSubmitted;
        } else if self.phase == Phase::FlatteningWithMarketSell {
            println!("[ORDER-TEST] Market sell filled — position flat. Done.");
            self.phase = Phase::Done;
        }

        Ok(())
    }

    fn on_order_canceled(&mut self, event: &OrderCanceled) -> Result<()> {
        println!("[CANCELED] order={}", event.client_order_id);
        if Some(event.client_order_id) == self.limit_order_id
            && self.phase == Phase::LimitSellSubmitted
        {
            let market_sell = self.core.order_factory().market(
                self.instrument_id,
                OrderSide::Sell,
                Quantity::from(TRADE_SIZE),
                None, None, None, None, None, None, None,
            );
            println!("[ORDER-TEST] Limit canceled — submitting market sell to flatten");
            self.submit_order(market_sell, None, None)?;
            self.phase = Phase::FlatteningWithMarketSell;
        }
        Ok(())
    }
}

impl Strategy for OrderTestStrategy {
    fn core(&self) -> &StrategyCore {
        &self.core
    }

    fn core_mut(&mut self) -> &mut StrategyCore {
        &mut self.core
    }

    fn on_order_accepted(&mut self, event: OrderAccepted) {
        println!("[ACCEPTED] order={}", event.client_order_id);
        if Some(event.client_order_id) == self.limit_order_id {
            self.limit_accepted_at = Some(Instant::now());
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
        anyhow::bail!("BINANCE_LINEAR_API_KEY must be set in .env to run order tests");
    }

    let trader_id = TraderId::from("ORDER-TESTER-001");

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
        account_id: AccountId::from("BINANCE-001"),
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
    let fills: Arc<Mutex<Vec<String>>> = Arc::new(Mutex::new(Vec::new()));

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

    node.add_strategy(OrderTestStrategy::new(instrument_id, Arc::clone(&fills)))?;

    println!("Connecting to Binance UsdM for order test...");
    println!("Will submit {TRADE_SIZE} XRP market buy → GTC limit sell → cancel → market sell");

    // "channel closed" errors at shutdown are a nautilus-binance shutdown race — harmless
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

    let fills = fills.lock().unwrap();
    println!("\nOrder test complete. Fills received: {}", fills.len());
    for fill in fills.iter() {
        println!("  {fill}");
    }

    Ok(())
}
