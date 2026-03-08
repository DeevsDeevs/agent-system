# Rust Adapter Development

Building production-grade NautilusTrader adapters in Rust with PyO3 bindings.

## Why Rust Adapters

- WebSocket/HTTP parsing at native speed (critical for HFT tick processing)
- Request signing without Python GIL contention
- Automatic reconnection with backoff (no asyncio complexity)
- Type-safe message parsing (serde + venue-specific types)
- Memory-safe concurrent networking

## Crate Structure

```
crates/adapters/myexchange/
├── Cargo.toml
├── src/
│   ├── lib.rs              # Crate root, module declarations
│   ├── common/
│   │   ├── mod.rs
│   │   ├── types.rs        # Venue-specific enums, types
│   │   ├── urls.rs         # URL resolution (mainnet/testnet)
│   │   ├── credentials.rs  # API key management
│   │   └── error.rs        # Error types
│   ├── http/
│   │   ├── mod.rs
│   │   ├── client.rs       # HTTP client with signing
│   │   ├── account.rs      # Account endpoints
│   │   ├── market.rs       # Market data endpoints
│   │   └── order.rs        # Order endpoints
│   ├── websocket/
│   │   ├── mod.rs
│   │   ├── client.rs       # WS client with reconnection
│   │   ├── handler.rs      # Message routing
│   │   └── messages.rs     # WS message types (serde)
│   ├── parsing/
│   │   ├── mod.rs
│   │   ├── instruments.rs  # Venue → Nautilus Instrument
│   │   ├── orderbook.rs    # Venue → OrderBookDelta
│   │   ├── trades.rs       # Venue → TradeTick
│   │   ├── quotes.rs       # Venue → QuoteTick
│   │   ├── orders.rs       # Venue → order events
│   │   └── account.rs      # Venue → account updates
│   └── python/
│       ├── mod.rs           # PyO3 module registration
│       ├── http.rs          # Python bindings for HTTP client
│       ├── websocket.rs     # Python bindings for WS client
│       └── config.rs        # Python-exposed config types
└── tests/
    ├── http_tests.rs
    ├── parsing_tests.rs
    └── websocket_tests.rs
```

## Cargo.toml

```toml
[package]
name = "nautilus-myexchange"
version.workspace = true
edition.workspace = true
rust-version.workspace = true

[lib]
name = "nautilus_myexchange"
crate-type = ["rlib"]

[dependencies]
nautilus-common = { path = "../../common" }
nautilus-core = { path = "../../core" }
nautilus-model = { path = "../../model" }

# Networking
reqwest = { version = "0.12", features = ["json", "rustls-tls"] }
tokio = { workspace = true, features = ["full"] }
tokio-tungstenite = { version = "0.24", features = ["rustls-tls-webpki-roots"] }
futures-util = "0.3"

# Serialization
serde = { workspace = true, features = ["derive"] }
serde_json = { workspace = true }

# Crypto (for request signing)
hmac = "0.12"
sha2 = "0.10"
hex = "0.4"

# Python bindings
pyo3 = { workspace = true, optional = true }

# Error handling
thiserror = { workspace = true }
anyhow = { workspace = true }

# Logging
tracing = { workspace = true }

[features]
default = []
python = ["pyo3"]
```

## HTTP Client Implementation

```rust
use nautilus_common::runtime::get_runtime;
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
    pub fn new(
        api_key: String,
        api_secret: String,
        testnet: bool,
    ) -> Self {
        let base_url = if testnet {
            "https://api-testnet.myexchange.com".to_string()
        } else {
            "https://api.myexchange.com".to_string()
        };

        Self {
            client: Client::builder()
                .tcp_nodelay(true)  // critical for HFT
                .pool_max_idle_per_host(10)
                .build()
                .expect("Failed to build HTTP client"),
            base_url,
            api_key,
            api_secret,
            recv_window: 5000,
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
            .send()
            .await?
            .json::<ApiResponse<InstrumentList>>()
            .await?;
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
            .header("X-API-RECV-WINDOW", self.recv_window.to_string())
            .json(req)
            .send()
            .await?
            .json::<ApiResponse<OrderResponse>>()
            .await?;

        if resp.ret_code != 0 {
            return Err(Error::ApiError(resp.ret_msg));
        }
        Ok(resp.result)
    }

    pub async fn get_order_book(
        &self,
        symbol: &str,
        depth: u32,
    ) -> Result<OrderBookSnapshot, Error> {
        let resp = self.client
            .get(format!("{}/v5/market/orderbook", self.base_url))
            .query(&[("category", "linear"), ("symbol", symbol), ("limit", &depth.to_string())])
            .send()
            .await?
            .json::<ApiResponse<OrderBookSnapshot>>()
            .await?;
        Ok(resp.result)
    }
}
```

## WebSocket Client Implementation

```rust
use futures_util::{SinkExt, StreamExt};
use tokio::sync::mpsc;
use tokio_tungstenite::{connect_async, tungstenite::Message};

pub struct MyExchangeWebSocketClient {
    url: String,
    sender: Option<mpsc::UnboundedSender<WsCommand>>,
    handler: Arc<dyn Fn(Vec<u8>) + Send + Sync>,
}

enum WsCommand {
    Subscribe(String),
    Unsubscribe(String),
    Close,
}

impl MyExchangeWebSocketClient {
    pub fn new(
        url: String,
        handler: Arc<dyn Fn(Vec<u8>) + Send + Sync>,
    ) -> Self {
        Self { url, sender: None, handler }
    }

    pub async fn connect(&mut self) -> Result<(), Error> {
        let (ws_stream, _) = connect_async(&self.url).await?;
        let (mut write, mut read) = ws_stream.split();
        let (cmd_tx, mut cmd_rx) = mpsc::unbounded_channel::<WsCommand>();
        let handler = self.handler.clone();

        // Read task
        let read_handle = tokio::spawn(async move {
            while let Some(msg) = read.next().await {
                match msg {
                    Ok(Message::Text(text)) => {
                        (handler)(text.into_bytes());
                    }
                    Ok(Message::Binary(data)) => {
                        (handler)(data.to_vec());
                    }
                    Ok(Message::Ping(data)) => {
                        // Pong handled automatically by tungstenite
                        tracing::trace!("Received ping");
                    }
                    Ok(Message::Close(_)) => {
                        tracing::warn!("WebSocket closed by server");
                        break;
                    }
                    Err(e) => {
                        tracing::error!("WebSocket error: {e}");
                        break;
                    }
                    _ => {}
                }
            }
        });

        // Write task
        tokio::spawn(async move {
            while let Some(cmd) = cmd_rx.recv().await {
                match cmd {
                    WsCommand::Subscribe(channel) => {
                        let msg = serde_json::json!({
                            "op": "subscribe",
                            "args": [channel]
                        });
                        if let Err(e) = write.send(Message::Text(msg.to_string().into())).await {
                            tracing::error!("Failed to send subscribe: {e}");
                        }
                    }
                    WsCommand::Unsubscribe(channel) => {
                        let msg = serde_json::json!({
                            "op": "unsubscribe",
                            "args": [channel]
                        });
                        if let Err(e) = write.send(Message::Text(msg.to_string().into())).await {
                            tracing::error!("Failed to send unsubscribe: {e}");
                        }
                    }
                    WsCommand::Close => {
                        let _ = write.close().await;
                        break;
                    }
                }
            }
        });

        self.sender = Some(cmd_tx);
        Ok(())
    }

    pub fn subscribe(&self, channel: &str) -> Result<(), Error> {
        self.sender
            .as_ref()
            .ok_or(Error::NotConnected)?
            .send(WsCommand::Subscribe(channel.to_string()))
            .map_err(|_| Error::ChannelClosed)
    }

    pub fn unsubscribe(&self, channel: &str) -> Result<(), Error> {
        self.sender
            .as_ref()
            .ok_or(Error::NotConnected)?
            .send(WsCommand::Unsubscribe(channel.to_string()))
            .map_err(|_| Error::ChannelClosed)
    }
}
```

## Parsing: Venue Types → Nautilus Types

```rust
use nautilus_model::data::{OrderBookDelta, TradeTick, QuoteTick};
use nautilus_model::enums::{BookAction, OrderSide, RecordFlag, AggressorSide};
use nautilus_model::types::{Price, Quantity};
use nautilus_model::identifiers::{InstrumentId, TradeId};

// Venue-specific serde types
#[derive(Debug, serde::Deserialize)]
pub struct VenueOrderBookUpdate {
    pub s: String,      // symbol
    pub b: Vec<[String; 2]>,  // bids [[price, size], ...]
    pub a: Vec<[String; 2]>,  // asks [[price, size], ...]
    pub u: u64,         // update id / sequence
    #[serde(rename = "ts")]
    pub timestamp: u64, // milliseconds
}

pub fn parse_order_book_deltas(
    instrument_id: InstrumentId,
    update: &VenueOrderBookUpdate,
    ts_init: u64,
) -> Vec<OrderBookDelta> {
    let mut deltas = Vec::new();
    let total = update.b.len() + update.a.len();

    for (i, bid) in update.b.iter().enumerate() {
        let size = Quantity::from_str(&bid[1]);
        let action = if size.raw == 0 { BookAction::Delete } else { BookAction::Update };
        let is_last = update.a.is_empty() && i == update.b.len() - 1;
        let flags = if is_last { RecordFlag::F_LAST } else { 0 };

        deltas.push(OrderBookDelta::new(
            instrument_id,
            action,
            BookOrder::new(
                OrderSide::Buy,
                Price::from_str(&bid[0]),
                size,
                0, // order_id for L2
            ),
            flags,
            update.u,
            millis_to_nanos(update.timestamp),
            ts_init,
        ));
    }

    for (i, ask) in update.a.iter().enumerate() {
        let size = Quantity::from_str(&ask[1]);
        let action = if size.raw == 0 { BookAction::Delete } else { BookAction::Update };
        let is_last = i == update.a.len() - 1;
        let flags = if is_last { RecordFlag::F_LAST } else { 0 };

        deltas.push(OrderBookDelta::new(
            instrument_id,
            action,
            BookOrder::new(
                OrderSide::Sell,
                Price::from_str(&ask[0]),
                size,
                0,
            ),
            flags,
            update.u,
            millis_to_nanos(update.timestamp),
            ts_init,
        ));
    }

    deltas
}

pub fn parse_trade(
    instrument_id: InstrumentId,
    raw: &VenueTradeMsg,
    ts_init: u64,
) -> TradeTick {
    TradeTick::new(
        instrument_id,
        Price::from_str(&raw.price),
        Quantity::from_str(&raw.qty),
        if raw.is_buyer_maker { AggressorSide::Seller } else { AggressorSide::Buyer },
        TradeId::new(&raw.trade_id),
        millis_to_nanos(raw.timestamp),
        ts_init,
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
        Self {
            inner: Arc::new(MyExchangeHttpClient::new(api_key, api_secret, testnet)),
        }
    }

    #[pyo3(name = "get_instruments")]
    fn py_get_instruments<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let client = self.inner.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let result = client.get_instruments().await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            // Convert Vec<InstrumentResponse> to Python list
            Python::with_gil(|py| {
                let list = pyo3::types::PyList::empty(py);
                for inst in result {
                    list.append(inst.into_pyobject(py)?)?;
                }
                Ok(list.into())
            })
        })
    }

    #[pyo3(name = "place_order")]
    fn py_place_order<'py>(
        &self,
        py: Python<'py>,
        symbol: String,
        side: String,
        order_type: String,
        qty: String,
        price: Option<String>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let client = self.inner.clone();
        pyo3_async_runtimes::tokio::future_into_py(py, async move {
            let req = OrderRequest { symbol, side, order_type, qty, price };
            let result = client.place_order(&req).await
                .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
            Ok(result.order_id)
        })
    }
}

// Module registration
pub fn myexchange_module(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<MyExchangeHttpClientPy>()?;
    m.add_class::<MyExchangeWebSocketClientPy>()?;
    // Add enums, config types, etc.
    Ok(())
}
```

## FFI Memory Contract

When passing data across the Rust/Python boundary:

### CVec Lifecycle (for Cython legacy layer)

1. **Rust**: Build `Vec<T>`, convert with `into()` — leaks memory, transfers ownership to foreign code
2. **Foreign**: Use data while `CVec` is in scope. Never modify `ptr`, `len`, or `cap` fields
3. **Foreign**: Call type-specific drop helper **exactly once** to free memory

Violating these rules = UB (double-free or memory leak).

### PyO3 (preferred for new code)

- Use `PyCapsule::new_with_destructor` for heap-allocated values pushed to Python
- The destructor reconstructs `Box<T>` or `Vec<T>` and lets it drop
- Rust panics must NOT unwind across `extern "C"` functions
- Every exported symbol wrapped in `crate::ffi::abort_on_panic` → calls `process::abort()` on panic

## Recommended Adapter Implementation Sequence

1. **Phase 1: Rust core infrastructure**
   - HTTP client with signing, rate limiting, retry logic
   - WebSocket client with auth, heartbeat, reconnection
   - Serde types for all venue API responses
   - Unit tests for parsing

2. **Phase 2: Instrument definitions**
   - Parse venue instrument response → Nautilus `Instrument` types
   - InstrumentProvider with caching and filtering
   - PyO3 bindings for InstrumentProvider

3. **Phase 3: Market data**
   - OrderBookDelta parsing (snapshots + incremental)
   - TradeTick, QuoteTick parsing
   - LiveMarketDataClient (Python) using Rust WS client
   - Integration tests with venue testnet

4. **Phase 4: Execution**
   - Order submission/cancellation/modification
   - Fill and execution event parsing
   - LiveExecutionClient (Python) using Rust HTTP + WS
   - Reconciliation reports
   - Integration tests with venue testnet

## Testing

```bash
# Rust unit tests (fast, isolated per test)
cargo nextest run -p nautilus-myexchange

# Run specific test
cargo nextest run -p nautilus-myexchange parse_order_book_deltas

# Python integration tests
pytest tests/integration_tests/adapters/myexchange/
```

Test patterns:
- Parse known venue JSON responses → assert correct Nautilus types
- Snapshot → incremental update sequence → verify book state
- Order lifecycle: submit → accept → fill → verify events
- Reconnection: disconnect → reconnect → verify subscription recovery
