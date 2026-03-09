# Rust Adapter Development

Building production-grade NautilusTrader adapters in Rust with PyO3 bindings.

## Why Rust Adapters

- WebSocket/HTTP parsing at native speed — critical for HFT tick processing
- Request signing without Python GIL contention
- Automatic reconnection with backoff (no asyncio complexity)
- Type-safe message parsing via serde
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
│   │   └── error.rs        # Error types (thiserror)
│   ├── http/
│   │   ├── mod.rs
│   │   ├── client.rs       # HTTP client with signing
│   │   ├── account.rs      # Account/balance endpoints
│   │   ├── market.rs       # Market data endpoints
│   │   └── order.rs        # Order submission endpoints
│   ├── websocket/
│   │   ├── mod.rs
│   │   ├── client.rs       # WS client with reconnection
│   │   ├── handler.rs      # Message routing/dispatch
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

reqwest = { version = "0.12", features = ["json", "rustls-tls"] }
tokio = { workspace = true, features = ["full"] }
tokio-tungstenite = { version = "0.24", features = ["rustls-tls-webpki-roots"] }
futures-util = "0.3"

serde = { workspace = true, features = ["derive"] }
serde_json = { workspace = true }

hmac = "0.12"
sha2 = "0.10"
hex = "0.4"

pyo3 = { workspace = true, optional = true }
thiserror = { workspace = true }
anyhow = { workspace = true }
tracing = { workspace = true }

[features]
default = []
python = ["pyo3"]
```

## Implementation Roadmap

1. **Phase 1**: Types, config, credentials, URLs, error types
2. **Phase 2**: HTTP client with signing and rate limiting
3. **Phase 3**: WebSocket client with reconnection and heartbeat
4. **Phase 4**: Data parsing (instruments, book deltas, trades, quotes)
5. **Phase 5**: PyO3 bindings for HTTP and WS clients
6. **Phase 6**: Python adapter layer (`nautilus_trader/adapters/myexchange/`)
7. **Phase 7**: Testing (Rust unit + integration, Python integration)

## HTTP Client

Two-layer architecture: inner (raw transport) + outer (business methods).

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
                .tcp_nodelay(true)  // critical for HFT
                .pool_max_idle_per_host(10)
                .build()
                .expect("Failed to build HTTP client"),
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
        if resp.ret_code != 0 {
            return Err(Error::ApiError(resp.ret_msg));
        }
        Ok(resp.result)
    }
}
```

**Rate limiting**: Use token-bucket or sliding-window. Track per-endpoint and global limits.

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

enum WsCommand {
    Subscribe(String),
    Unsubscribe(String),
    Close,
}

impl MyExchangeWebSocketClient {
    pub async fn connect(&mut self) -> Result<(), Error> {
        let (ws_stream, _) = connect_async(&self.url).await?;
        let (mut write, mut read) = ws_stream.split();
        let (cmd_tx, mut cmd_rx) = mpsc::unbounded_channel::<WsCommand>();
        let handler = self.handler.clone();

        // Read task
        tokio::spawn(async move {
            while let Some(msg) = read.next().await {
                match msg {
                    Ok(Message::Text(text)) => (handler)(text.into_bytes()),
                    Ok(Message::Binary(data)) => (handler)(data.to_vec()),
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

**Reconnection**: Track subscription state. On disconnect → exponential backoff (1s→2s→4s→max 60s) → reconnect → resubscribe all active channels.

**Ping/pong**: Most venues require periodic pings. Spawn background task with interval timer.

## Data Parsing

```rust
use nautilus_model::data::OrderBookDelta;
use nautilus_model::enums::{BookAction, OrderSide, RecordFlag};
use nautilus_model::types::{Price, Quantity};

#[derive(Debug, serde::Deserialize)]
pub struct VenueBookUpdate {
    pub s: String,
    pub b: Vec<[String; 2]>,  // [[price, size], ...]
    pub a: Vec<[String; 2]>,
    pub u: u64,
    #[serde(rename = "ts")]
    pub timestamp: u64,
}

pub fn parse_order_book_deltas(
    instrument_id: InstrumentId,
    update: &VenueBookUpdate,
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
                for inst in result {
                    list.append(inst.into_pyobject(py)?)?;
                }
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

### CVec (Legacy Cython)

```
1. Rust: Vec<T> → CVec (leaks memory, transfers ownership)
2. Foreign: Use data, never modify ptr/len/cap
3. Foreign: Call drop helper EXACTLY ONCE

Violations → UB: forget drop = leak, double drop = crash, modify fields = corruption
```

### PyO3 (New Code — Always Use This)

- `PyCapsule::new_with_destructor` for heap values to Python
- Destructor reconstructs `Box<T>` / `Vec<T>` and drops
- Panics must NOT cross `extern "C"`:

```rust
pub fn abort_on_panic<F, R>(f: F) -> R
where F: FnOnce() -> R {
    match std::panic::catch_unwind(std::panic::AssertUnwindSafe(f)) {
        Ok(result) => result,
        Err(_) => std::process::abort(),
    }
}
```

## Naming Conventions

| Category | Convention | Example |
|----------|-----------|---------|
| Channels | Lowercase venue names | `"trades"`, `"orderbook"` |
| Types | Venue prefix + concept | `BinanceTrade`, `BybitBookDelta` |
| Fields | Snake case matching venue | `order_id`, `client_order_id` |
| Crate name | `nautilus-{venue}` | `nautilus-binance` |

## Instrument Cache

Dual-tier for performance:

| Tier | Type | Purpose |
|------|------|---------|
| Hot | `DashMap<InstrumentId, InstrumentAny>` | Concurrent read/write during live |
| Cold | `AHashMap<InstrumentId, InstrumentAny>` | Fast read-only after initial load |

Provider loads via HTTP → populates both. WS updates modify hot. Strategy lookups hit hot first.

## Credential Management

```rust
use zeroize::Zeroize;

#[derive(Zeroize)]
#[zeroize(drop)]
pub struct Credentials {
    api_key: String,
    api_secret: String,
}
```

Load from env vars. Never log credentials. `zeroize` clears memory on drop.

## Testing

```bash
# Rust unit tests
cargo nextest run -p nautilus-myexchange

# Specific test
cargo nextest run -p nautilus-myexchange parse_order_book_deltas

# Python integration
pytest tests/integration_tests/adapters/myexchange/
```

### Mock Server Pattern

```rust
#[tokio::test]
async fn test_fetch_instruments() {
    let mock_server = axum::Router::new()
        .route("/api/instruments", get(|| async { Json(mock_instruments()) }));
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();
    tokio::spawn(axum::serve(listener, mock_server).into_future());

    let client = MyExchangeHttpClient::new(
        "key".into(), "secret".into(), false,
    );
    let instruments = client.fetch_instruments().await.unwrap();
    assert_eq!(instruments.len(), 2);
}
```

Test patterns:
- Parse known venue JSON → assert correct Nautilus types
- Snapshot → incremental update → verify book state
- Order lifecycle: submit → accept → fill → verify events
- Reconnection: disconnect → reconnect → verify subscription recovery
