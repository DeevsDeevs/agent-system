# Rust Adapter Development

## Crate Structure

```
crates/adapters/myexchange/
├── Cargo.toml
├── src/
│   ├── lib.rs
│   ├── common/       # types, urls, credentials, error
│   ├── http/         # client (signing), account, market, order endpoints
│   ├── websocket/    # client (reconnection), handler, messages
│   ├── parsing/      # instruments, orderbook, trades, quotes, orders, account
│   └── python/       # PyO3 bindings: http, websocket, config
└── tests/
```

## Cargo.toml

```toml
[package]
name = "nautilus-myexchange"
version.workspace = true
edition.workspace = true

[lib]
name = "nautilus_myexchange"
crate-type = ["rlib"]

[dependencies]
nautilus-common = { path = "../../common" }
nautilus-core = { path = "../../core" }
nautilus-model = { path = "../../model" }
reqwest = { version = "0.12", features = ["json", "rustls-tls"] }
tokio = { workspace = true, features = ["full"] }
tokio-tungstenite = { version = "0.24", features = ["rustls-tls-webpki-roots"] }
futures-util = "0.3"
serde = { workspace = true, features = ["derive"] }
serde_json = { workspace = true }
hmac = "0.12"
sha2 = "0.10"
pyo3 = { workspace = true, optional = true }
thiserror = { workspace = true }
anyhow = { workspace = true }
tracing = { workspace = true }

[features]
python = ["pyo3"]
```

## HTTP Client

```rust
use reqwest::Client;
use hmac::{Hmac, Mac};
use sha2::Sha256;

pub struct MyExchangeHttpClient {
    client: Client,
    base_url: String,
    api_key: String,
    api_secret: String,
    recv_window: u64,
}

impl MyExchangeHttpClient {
    pub fn new(api_key: String, api_secret: String, testnet: bool) -> Self {
        let base_url = if testnet {
            "https://api-testnet.myexchange.com"
        } else {
            "https://api.myexchange.com"
        };
        Self {
            client: Client::builder()
                .tcp_nodelay(true)
                .pool_max_idle_per_host(10)
                .build().expect("Failed to build HTTP client"),
            base_url: base_url.to_string(),
            api_key, api_secret, recv_window: 5000,
        }
    }

    fn sign(&self, params: &str, timestamp: u64) -> String {
        let payload = format!("{timestamp}{}{params}{}", self.api_key, self.recv_window);
        let mut mac = Hmac::<Sha256>::new_from_slice(self.api_secret.as_bytes())
            .expect("HMAC key error");
        mac.update(payload.as_bytes());
        hex::encode(mac.finalize().into_bytes())
    }

    pub async fn get_instruments(&self) -> Result<Vec<InstrumentResponse>, Error> {
        let resp = self.client
            .get(format!("{}/v5/market/instruments-info", self.base_url))
            .query(&[("category", "linear")])
            .send().await?
            .json::<ApiResponse<InstrumentList>>().await?;
        Ok(resp.result.list)
    }

    pub async fn place_order(&self, req: &OrderRequest) -> Result<OrderResponse, Error> {
        let timestamp = chrono::Utc::now().timestamp_millis() as u64;
        let body = serde_json::to_string(req)?;
        let signature = self.sign(&body, timestamp);
        let resp = self.client
            .post(format!("{}/v5/order/create", self.base_url))
            .header("X-API-KEY", &self.api_key)
            .header("X-API-SIGN", &signature)
            .header("X-API-TIMESTAMP", timestamp.to_string())
            .json(req).send().await?
            .json::<ApiResponse<OrderResponse>>().await?;
        if resp.ret_code != 0 { return Err(Error::ApiError(resp.ret_msg)); }
        Ok(resp.result)
    }
}
```

Rate limiting: token-bucket or sliding-window, track per-endpoint and global limits.

## WebSocket Client

```rust
use futures_util::{SinkExt, StreamExt};
use tokio::sync::mpsc;
use tokio_tungstenite::{connect_async, tungstenite::Message};

pub struct MyExchangeWebSocketClient {
    url: String,
    sender: Option<mpsc::UnboundedSender<WsCommand>>,
    handler: Arc<dyn Fn(Vec<u8>) + Send + Sync>,
}

enum WsCommand { Subscribe(String), Unsubscribe(String), Close }

impl MyExchangeWebSocketClient {
    pub async fn connect(&mut self) -> Result<(), Error> {
        let (ws_stream, _) = connect_async(&self.url).await?;
        let (mut write, mut read) = ws_stream.split();
        let (cmd_tx, mut cmd_rx) = mpsc::unbounded_channel::<WsCommand>();
        let handler = self.handler.clone();

        tokio::spawn(async move {
            while let Some(msg) = read.next().await {
                match msg {
                    Ok(Message::Text(text)) => (handler)(text.into_bytes()),
                    Ok(Message::Binary(data)) => (handler)(data.to_vec()),
                    Ok(Message::Close(_)) => break,
                    Err(e) => { tracing::error!("WebSocket error: {e}"); break; }
                    _ => {}
                }
            }
        });

        tokio::spawn(async move {
            while let Some(cmd) = cmd_rx.recv().await {
                match cmd {
                    WsCommand::Subscribe(ch) => {
                        let msg = serde_json::json!({"op": "subscribe", "args": [ch]});
                        let _ = write.send(Message::Text(msg.to_string().into())).await;
                    }
                    WsCommand::Unsubscribe(ch) => {
                        let msg = serde_json::json!({"op": "unsubscribe", "args": [ch]});
                        let _ = write.send(Message::Text(msg.to_string().into())).await;
                    }
                    WsCommand::Close => { let _ = write.close().await; break; }
                }
            }
        });

        self.sender = Some(cmd_tx);
        Ok(())
    }

    pub fn subscribe(&self, channel: &str) -> Result<(), Error> {
        self.sender.as_ref().ok_or(Error::NotConnected)?
            .send(WsCommand::Subscribe(channel.to_string()))
            .map_err(|_| Error::ChannelClosed)
    }
}
```

## Data Parsing

```rust
use nautilus_model::data::OrderBookDelta;
use nautilus_model::enums::{BookAction, OrderSide, RecordFlag};
use nautilus_model::types::{Price, Quantity};

#[derive(Debug, serde::Deserialize)]
pub struct VenueBookUpdate {
    pub s: String,
    pub b: Vec<[String; 2]>,
    pub a: Vec<[String; 2]>,
    pub u: u64,
    #[serde(rename = "ts")]
    pub timestamp: u64,
}

pub fn parse_order_book_deltas(
    instrument_id: InstrumentId, update: &VenueBookUpdate, ts_init: u64,
) -> Vec<OrderBookDelta> {
    let mut deltas = Vec::new();
    for (i, bid) in update.b.iter().enumerate() {
        let size = Quantity::from_str(&bid[1]);
        let action = if size.raw == 0 { BookAction::Delete } else { BookAction::Update };
        let is_last = update.a.is_empty() && i == update.b.len() - 1;
        let flags = if is_last { RecordFlag::F_LAST } else { 0 };
        deltas.push(OrderBookDelta::new(
            instrument_id, action,
            BookOrder::new(OrderSide::Buy, Price::from_str(&bid[0]), size, 0),
            flags, update.u, millis_to_nanos(update.timestamp), ts_init,
        ));
    }
    for (i, ask) in update.a.iter().enumerate() {
        let size = Quantity::from_str(&ask[1]);
        let action = if size.raw == 0 { BookAction::Delete } else { BookAction::Update };
        let is_last = i == update.a.len() - 1;
        let flags = if is_last { RecordFlag::F_LAST } else { 0 };
        deltas.push(OrderBookDelta::new(
            instrument_id, action,
            BookOrder::new(OrderSide::Sell, Price::from_str(&ask[0]), size, 0),
            flags, update.u, millis_to_nanos(update.timestamp), ts_init,
        ));
    }
    deltas
}

pub fn parse_trade(instrument_id: InstrumentId, raw: &VenueTradeMsg, ts_init: u64) -> TradeTick {
    TradeTick::new(
        instrument_id,
        Price::from_str(&raw.price), Quantity::from_str(&raw.qty),
        if raw.is_buyer_maker { AggressorSide::Seller } else { AggressorSide::Buyer },
        TradeId::new(&raw.trade_id),
        millis_to_nanos(raw.timestamp), ts_init,
    )
}
```

## PyO3 Bindings

```rust
use pyo3::prelude::*;

#[pyclass(name = "MyExchangeHttpClient")]
pub struct MyExchangeHttpClientPy {
    inner: Arc<MyExchangeHttpClient>,
}

#[pymethods]
impl MyExchangeHttpClientPy {
    #[new]
    fn new(api_key: String, api_secret: String, testnet: bool) -> Self {
        Self { inner: Arc::new(MyExchangeHttpClient::new(api_key, api_secret, testnet)) }
    }

    #[pyo3(name = "get_instruments")]
    fn py_get_instruments<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let client = self.inner.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let result = client.get_instruments().await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            Python::with_gil(|py| {
                let list = pyo3::types::PyList::empty(py);
                for inst in result { list.append(inst.into_pyobject(py)?)?; }
                Ok(list.into())
            })
        })
    }
}

pub fn myexchange_module(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<MyExchangeHttpClientPy>()?;
    m.add_class::<MyExchangeWebSocketClientPy>()?;
    Ok(())
}
```

## FFI Memory Contract

**CVec (legacy)**: `Vec<T>` → `CVec` transfers ownership, call drop helper once. **PyO3 (new code)**: `PyCapsule::new_with_destructor`. Panics must NOT cross `extern "C"` — use `catch_unwind` + `abort()`.

## Conventions

Naming: lowercase channels (`"trades"`), venue-prefixed types (`BinanceTrade`), snake_case fields, `nautilus-{venue}` crate name. Instrument cache: `DashMap` hot tier (concurrent), `AHashMap` cold tier (read-only). Credentials: `zeroize` crate with `#[zeroize(drop)]`.

## Testing

`cargo nextest run -p nautilus-myexchange` + `pytest tests/integration_tests/adapters/myexchange/`. Test: parse venue JSON → assert types, snapshot → incremental → verify book, order lifecycle → verify events.
