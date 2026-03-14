use std::{
    fmt::Debug,
    ops::{Deref, DerefMut},
    sync::{Arc, Mutex},
    time::Duration,
};

use anyhow::Result;
use nautilus_binance::{
    common::enums::{BinanceEnvironment, BinanceProductType},
    config::BinanceDataClientConfig,
    factories::BinanceDataClientFactory,
};
use nautilus_common::{
    actor::{DataActor, DataActorConfig, DataActorCore},
    enums::Environment,
};
use nautilus_live::builder::LiveNodeBuilder;
use nautilus_model::{
    data::{QuoteTick, TradeTick},
    identifiers::{InstrumentId, TraderId},
    instruments::{Instrument, InstrumentAny},
};

const COLLECTION_SECS: u64 = 15;

#[derive(Default)]
struct Counts {
    btc_quotes: usize,
    btc_trades: usize,
    shib_quotes: usize,
    shib_trades: usize,
    instruments: Vec<String>,
}

struct SpotCollector {
    core: DataActorCore,
    btc_id: InstrumentId,
    shib_id: InstrumentId,
    counts: Arc<Mutex<Counts>>,
}

impl SpotCollector {
    fn new(
        btc_id: InstrumentId,
        shib_id: InstrumentId,
        counts: Arc<Mutex<Counts>>,
    ) -> Self {
        Self {
            core: DataActorCore::new(DataActorConfig::default()),
            btc_id,
            shib_id,
            counts,
        }
    }
}

impl Deref for SpotCollector {
    type Target = DataActorCore;
    fn deref(&self) -> &Self::Target {
        &self.core
    }
}

impl DerefMut for SpotCollector {
    fn deref_mut(&mut self) -> &mut Self::Target {
        &mut self.core
    }
}

impl Debug for SpotCollector {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("SpotCollector").finish()
    }
}

impl DataActor for SpotCollector {
    fn on_stop(&mut self) -> Result<()> {
        Ok(())
    }

    fn on_start(&mut self) -> Result<()> {
        let cache = self.cache_rc();
        let guard = cache.borrow();
        let mut c = self.counts.lock().unwrap();
        if let Some(inst) = guard.instrument(&self.btc_id) {
            c.instruments.push(format!("{} (tick_size={})", inst.id(), inst.price_precision()));
        }
        if let Some(inst) = guard.instrument(&self.shib_id) {
            c.instruments.push(format!("{} (tick_size={})", inst.id(), inst.price_precision()));
        }
        drop(c);
        drop(guard);

        self.subscribe_quotes(self.btc_id, None, None);
        self.subscribe_trades(self.btc_id, None, None);
        self.subscribe_quotes(self.shib_id, None, None);
        self.subscribe_trades(self.shib_id, None, None);
        Ok(())
    }

    fn on_instrument(&mut self, instrument: &InstrumentAny) -> Result<()> {
        println!("[SPOT] on_instrument: {}", instrument.id());
        Ok(())
    }

    fn on_quote(&mut self, quote: &QuoteTick) -> Result<()> {
        let mut c = self.counts.lock().unwrap();
        if quote.instrument_id == self.btc_id {
            c.btc_quotes += 1;
            if c.btc_quotes == 1 {
                println!("[SPOT] First BTC quote: bid={} ask={}", quote.bid_price, quote.ask_price);
            }
        } else if quote.instrument_id == self.shib_id {
            c.shib_quotes += 1;
            if c.shib_quotes == 1 {
                println!("[SPOT] First SHIB quote: bid={} ask={}", quote.bid_price, quote.ask_price);
            }
        }
        Ok(())
    }

    fn on_trade(&mut self, trade: &TradeTick) -> Result<()> {
        let mut c = self.counts.lock().unwrap();
        if trade.instrument_id == self.btc_id {
            c.btc_trades += 1;
            if c.btc_trades == 1 {
                println!("[SPOT] First BTC trade: price={} size={}", trade.price, trade.size);
            }
        } else if trade.instrument_id == self.shib_id {
            c.shib_trades += 1;
            if c.shib_trades == 1 {
                println!("[SPOT] First SHIB trade: price={} size={}", trade.price, trade.size);
            }
        }
        Ok(())
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let _ = dotenvy::from_filename("../../.env");

    let api_key = std::env::var("BINANCE_SPOT_API_KEY")
        .ok()
        .filter(|s| !s.is_empty());
    let api_secret = std::env::var("BINANCE_SPOT_API_SECRET")
        .ok()
        .filter(|s| !s.is_empty());

    if api_key.is_none() {
        anyhow::bail!("BINANCE_SPOT_API_KEY must be set in .env");
    }

    let binance_config = BinanceDataClientConfig {
        product_types: vec![BinanceProductType::Spot],
        environment: BinanceEnvironment::Mainnet,
        base_url_http: None,
        base_url_ws: None,
        api_key,
        api_secret,
    };

    let trader_id = TraderId::from("SPOT-TEST-001");
    let btc_id = InstrumentId::from("BTCUSDT.BINANCE");
    let shib_id = InstrumentId::from("SHIBUSDT.BINANCE");
    let counts: Arc<Mutex<Counts>> = Arc::new(Mutex::new(Counts::default()));

    let mut node = LiveNodeBuilder::new(trader_id, Environment::Live)?
        .with_timeout_connection(30)
        .with_reconciliation(false)
        .add_data_client(
            None,
            Box::new(BinanceDataClientFactory::new()),
            Box::new(binance_config),
        )?
        .build()?;

    node.add_actor(SpotCollector::new(btc_id, shib_id, Arc::clone(&counts)))?;

    println!("Connecting to Binance Spot for {COLLECTION_SECS}s...");
    println!("Watching BTCUSDT + SHIBUSDT (high-precision test)");

    tokio::select! {
        result = node.run() => result?,
        _ = tokio::time::sleep(Duration::from_secs(COLLECTION_SECS)) => {
            node.stop().await?;
        }
        _ = tokio::signal::ctrl_c() => {
            println!("Interrupted — stopping node");
            node.stop().await?;
        }
    }

    let c = counts.lock().unwrap();
    println!("\n=== Spot Test Results ===");
    println!("Instruments loaded at startup: {}", c.instruments.len());
    for inst in &c.instruments {
        println!("  {inst}");
    }
    println!("BTC  quotes={} trades={}", c.btc_quotes, c.btc_trades);
    println!("SHIB quotes={} trades={}", c.shib_quotes, c.shib_trades);

    let pass = c.btc_quotes > 0 && c.shib_quotes > 0 && c.instruments.len() >= 2;
    if pass {
        println!("\nPASS: Spot + high-precision working");
    } else {
        println!("\nFAIL: Missing data — check output above");
    }

    Ok(())
}
