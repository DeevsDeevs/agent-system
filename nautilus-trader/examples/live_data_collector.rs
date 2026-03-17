use std::{
    fmt::Debug,
    num::NonZeroUsize,
    ops::{Deref, DerefMut},
    path::PathBuf,
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
    actor::{DataActor, DataActorCore, DataActorConfig},
    enums::Environment,
};
use nautilus_live::builder::LiveNodeBuilder;
use nautilus_model::{
    data::{OrderBookDelta, OrderBookDeltas, QuoteTick, TradeTick},
    enums::BookType,
    identifiers::{InstrumentId, TraderId},
    instruments::{Instrument, InstrumentAny},
};
use nautilus_persistence::backend::catalog::ParquetDataCatalog;

const COLLECTION_SECS: u64 = 60;
const CATALOG_PATH: &str = "./data/catalog";
const L2_DEPTH: usize = 20;
const MAX_ITEMS: usize = 5_000_000;

struct DataCollector {
    core: DataActorCore,
    instrument_ids: Vec<InstrumentId>,
    quotes: Arc<Mutex<Vec<QuoteTick>>>,
    trades: Arc<Mutex<Vec<TradeTick>>>,
    deltas: Arc<Mutex<Vec<OrderBookDelta>>>,
    instruments: Arc<Mutex<Vec<InstrumentAny>>>,
}

impl DataCollector {
    fn new(
        instrument_ids: Vec<InstrumentId>,
        quotes: Arc<Mutex<Vec<QuoteTick>>>,
        trades: Arc<Mutex<Vec<TradeTick>>>,
        deltas: Arc<Mutex<Vec<OrderBookDelta>>>,
        instruments: Arc<Mutex<Vec<InstrumentAny>>>,
    ) -> Self {
        Self {
            core: DataActorCore::new(DataActorConfig::default()),
            instrument_ids,
            quotes,
            trades,
            deltas,
            instruments,
        }
    }
}

// Deref/DerefMut → DataActorCore via self.core (see ema_crossover_backtest.rs)
impl Debug for DataCollector {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("DataCollector")
            .field("quotes", &self.quotes.lock().unwrap().len())
            .field("trades", &self.trades.lock().unwrap().len())
            .field("deltas", &self.deltas.lock().unwrap().len())
            .finish()
    }
}

impl DataActor for DataCollector {
    fn on_stop(&mut self) -> Result<()> {
        Ok(())
    }

    fn on_start(&mut self) -> Result<()> {
        let ids: Vec<InstrumentId> = self.instrument_ids.clone();

        let cache = self.cache_rc();
        for id in &ids {
            if let Some(instrument) = cache.borrow().instrument(id) {
                self.instruments.lock().unwrap().push(instrument.clone());
            }
        }

        for id in ids {
            self.subscribe_quotes(id, None, None);
            self.subscribe_trades(id, None, None);
            self.subscribe_book_deltas(id, BookType::L2_MBP, NonZeroUsize::new(L2_DEPTH), None, false, None);
        }
        Ok(())
    }

    fn on_instrument(&mut self, instrument: &InstrumentAny) -> Result<()> {
        let mut guard = self.instruments.lock().unwrap();
        if !guard.iter().any(|i| i.id() == instrument.id()) {
            guard.push(instrument.clone());
        }
        Ok(())
    }

    fn on_quote(&mut self, quote: &QuoteTick) -> Result<()> {
        let mut guard = self.quotes.lock().unwrap();
        if guard.len() < MAX_ITEMS { guard.push(*quote); }
        Ok(())
    }

    fn on_trade(&mut self, trade: &TradeTick) -> Result<()> {
        let mut guard = self.trades.lock().unwrap();
        if guard.len() < MAX_ITEMS { guard.push(*trade); }
        Ok(())
    }

    fn on_book_deltas(&mut self, deltas: &OrderBookDeltas) -> Result<()> {
        let mut guard = self.deltas.lock().unwrap();
        if guard.len() < MAX_ITEMS { guard.extend_from_slice(&deltas.deltas); }
        Ok(())
    }
}

#[tokio::main]
async fn main() -> Result<()> {
    let _ = dotenvy::from_filename("../../.env");

    let api_key = std::env::var("BINANCE_LINEAR_API_KEY").ok();
    let api_secret = std::env::var("BINANCE_LINEAR_API_SECRET").ok();

    if api_key.is_none() {
        eprintln!("Warning: BINANCE_LINEAR_API_KEY not set — unauthenticated streams only");
    }

    let binance_config = BinanceDataClientConfig {
        product_types: vec![BinanceProductType::UsdM],
        environment: BinanceEnvironment::Mainnet,
        base_url_http: None,
        base_url_ws: None,
        api_key,
        api_secret,
    };

    let trader_id = TraderId::from("DATA-COLLECTOR-001");

    let quotes: Arc<Mutex<Vec<QuoteTick>>> = Arc::new(Mutex::new(Vec::with_capacity(100_000)));
    let trades: Arc<Mutex<Vec<TradeTick>>> = Arc::new(Mutex::new(Vec::with_capacity(100_000)));
    let deltas: Arc<Mutex<Vec<OrderBookDelta>>> = Arc::new(Mutex::new(Vec::with_capacity(500_000)));
    let instruments: Arc<Mutex<Vec<InstrumentAny>>> = Arc::new(Mutex::new(Vec::with_capacity(16)));

    let instrument_ids = vec![
        InstrumentId::from("BTCUSDT-PERP.BINANCE"),
        InstrumentId::from("ETHUSDT-PERP.BINANCE"),
    ];

    let mut node = LiveNodeBuilder::new(trader_id, Environment::Live)?
        .with_timeout_connection(30)
        .with_reconciliation(false)
        .add_data_client(
            None,
            Box::new(BinanceDataClientFactory::new()),
            Box::new(binance_config),
        )?
        .build()?;

    node.add_actor(DataCollector::new(
        instrument_ids,
        Arc::clone(&quotes),
        Arc::clone(&trades),
        Arc::clone(&deltas),
        Arc::clone(&instruments),
    ))?;

    println!("Collecting data for {COLLECTION_SECS}s...");

    tokio::select! {
        result = node.run() => result?,
        _ = tokio::time::sleep(Duration::from_secs(COLLECTION_SECS)) => {
            node.stop().await?;
        }
        _ = tokio::signal::ctrl_c() => {
            println!("Interrupted — shutting down...");
            node.stop().await?;
        }
    }

    let quotes = quotes.lock().unwrap().clone();
    let trades = trades.lock().unwrap().clone();
    let deltas = deltas.lock().unwrap().clone();
    let instruments = instruments.lock().unwrap().clone();

    println!(
        "Collected: {} quotes, {} trades, {} book deltas, {} instruments",
        quotes.len(), trades.len(), deltas.len(), instruments.len()
    );

    if quotes.is_empty() && trades.is_empty() && deltas.is_empty() {
        println!("No data collected — check API credentials and network.");
        return Ok(());
    }

    let catalog_path = PathBuf::from(CATALOG_PATH);
    std::fs::create_dir_all(&catalog_path)?;

    // ParquetDataCatalog creates its own tokio runtime internally
    tokio::task::spawn_blocking(move || -> Result<()> {
        let catalog = ParquetDataCatalog::new(&catalog_path, None, None, None, None);

        if !instruments.is_empty() {
            catalog.write_instruments(instruments.clone())?;
            println!("Wrote {} instrument definitions", instruments.len());
        }

        if !quotes.is_empty() {
            catalog.write_to_parquet(quotes.clone(), None, None, None)?;
            println!("Wrote {} quotes to {CATALOG_PATH}/quote_tick/", quotes.len());
        }

        if !trades.is_empty() {
            catalog.write_to_parquet(trades.clone(), None, None, None)?;
            println!("Wrote {} trades to {CATALOG_PATH}/trade_tick/", trades.len());
        }

        if !deltas.is_empty() {
            catalog.write_to_parquet(deltas.clone(), None, None, None)?;
            println!("Wrote {} book deltas to {CATALOG_PATH}/order_book_delta/", deltas.len());
        }

        println!("Catalog written to {CATALOG_PATH}");
        Ok(())
    })
    .await??;

    Ok(())
}
