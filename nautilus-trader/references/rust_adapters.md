# Rust Adapter Development

## Crate Structure

```
crates/adapters/your_adapter/
├── Cargo.toml
├── src/
│   ├── lib.rs              # Crate root, module declarations
│   ├── common/
│   │   ├── mod.rs
│   │   ├── types.rs         # Venue-specific types, enums
│   │   ├── enums.rs         # Account types, order types
│   │   ├── credentials.rs   # API key management, signing
│   │   └── urls.rs          # Base URLs, endpoint paths
│   ├── http/
│   │   ├── mod.rs
│   │   ├── client.rs        # High-level HTTP client (business logic)
│   │   ├── account.rs       # Account/balance endpoints
│   │   ├── market.rs        # Market data endpoints
│   │   ├── order.rs         # Order submission endpoints
│   │   └── urls.rs          # URL builders
│   ├── websocket/
│   │   ├── mod.rs
│   │   ├── client.rs        # Outer WebSocket client
│   │   ├── handler.rs       # Inner message handler
│   │   ├── types.rs         # WS message types
│   │   └── streams.rs       # Stream subscription management
│   ├── parsing/
│   │   ├── mod.rs
│   │   ├── instruments.rs   # Venue JSON → Nautilus Instrument
│   │   ├── orders.rs        # Venue order format ↔ Nautilus
│   │   ├── account.rs       # Balance/margin parsing
│   │   └── data.rs          # Market data parsing (trades, books, ticks)
│   └── python/
│       ├── mod.rs
│       ├── config.rs        # PyO3-wrapped config types
│       ├── data.rs          # Python data client bindings
│       ├── execution.rs     # Python execution client bindings
│       └── providers.rs     # Python instrument provider bindings
```

## Implementation Phases

### Phase 1: Types and Configuration
Define venue-specific enums, credential structs, base URLs. Create `Cargo.toml` with dependencies on `nautilus-core`, `nautilus-model`, `reqwest`, `tokio-tungstenite`.

### Phase 2: HTTP Client (Two-Layer Architecture)

**Inner layer** — raw HTTP transport:
```rust
pub struct YourHttpClient {
    client: reqwest::Client,
    base_url: String,
    credentials: Credentials,
    rate_limiter: RateLimiter,
}

impl YourHttpClient {
    pub async fn send_signed_request(
        &self,
        method: Method,
        endpoint: &str,
        params: Option<&str>,
    ) -> Result<Response, HttpError> {
        let timestamp = Utc::now().timestamp_millis();
        let signature = self.credentials.sign(params, timestamp);
        // Build request with auth headers, enforce rate limit
        self.rate_limiter.acquire().await;
        self.client.request(method, url)
            .headers(auth_headers)
            .send()
            .await
    }
}
```

**Outer layer** — business-logic methods:
```rust
impl YourHttpClient {
    pub async fn fetch_instruments(&self) -> Result<Vec<InstrumentAny>, Error> {
        let response = self.send_signed_request(Method::GET, "/api/instruments", None).await?;
        let raw: Vec<VenueInstrument> = response.json().await?;
        raw.into_iter().map(parse_instrument).collect()
    }

    pub async fn submit_order(&self, order: &OrderSubmit) -> Result<VenueOrderId, Error> {
        let body = serde_json::to_string(order)?;
        let response = self.send_signed_request(Method::POST, "/api/order", Some(&body)).await?;
        // Parse venue order ID from response
    }
}
```

**Rate limiting**: Use a token-bucket or sliding-window limiter. Most exchanges enforce per-endpoint and global limits.

**Request signing**: HMAC-SHA256 is standard. Sign `timestamp + method + endpoint + body`. Use `zeroize` crate for credential cleanup.

### Phase 3: WebSocket Client (Outer + Inner Pattern)

**Outer client** — connection lifecycle, subscription management:
```rust
pub struct YourWebSocketClient {
    url: String,
    handler: Arc<Mutex<YourMessageHandler>>,
    subscriptions: DashMap<String, SubscriptionState>,
    reconnect_policy: ReconnectPolicy,
}

impl YourWebSocketClient {
    pub async fn connect(&self) -> Result<(), Error> {
        let (ws_stream, _) = connect_async(&self.url).await?;
        let (write, read) = ws_stream.split();
        // Spawn read loop, ping/pong, resubscription on reconnect
    }

    pub async fn subscribe(&self, channel: &str, symbol: &str) -> Result<(), Error> {
        let msg = json!({"op": "subscribe", "channel": channel, "symbol": symbol});
        self.subscriptions.insert(channel_key, SubscriptionState::Subscribing);
        self.send(msg).await?;
        Ok(())
    }
}
```

**Inner handler** — message dispatch:
```rust
pub struct YourMessageHandler {
    pub data_sender: UnboundedSender<Data>,
}

impl YourMessageHandler {
    pub fn handle_message(&self, msg: &str) -> Result<(), Error> {
        let parsed: WsMessage = serde_json::from_str(msg)?;
        match parsed.channel.as_str() {
            "trades" => self.handle_trade(parsed.data),
            "orderbook" => self.handle_book_delta(parsed.data),
            "ticker" => self.handle_quote(parsed.data),
            _ => Ok(()),
        }
    }
}
```

**Reconnection**: Track subscription state. On disconnect → reconnect with exponential backoff → resubscribe all active channels.

**Ping/pong**: Most venues require periodic pings. Spawn a background task with interval timer.

### Phase 4: Data Parsing

Parse venue formats into Nautilus types (`TradeTick`, `QuoteTick`, `OrderBookDelta`, `InstrumentAny`).

**OrderBookDelta RecordFlag requirements**:
- `F_LAST` — must be set on the final delta in a batch/message to signal "this batch is complete, book can be updated"
- `F_SNAPSHOT` — set on deltas that represent a full snapshot (initial subscription response or periodic snapshots)
- Without `F_LAST`, the DataEngine buffers deltas and never applies them

### Phase 5: PyO3 Bindings

```rust
#[pyclass]
pub struct YourDataClient {
    inner: Arc<YourWebSocketClient>,
    http: Arc<YourHttpClient>,
}

#[pymethods]
impl YourDataClient {
    #[new]
    fn new(config: &YourDataClientConfig) -> PyResult<Self> { ... }

    // Async methods return Python awaitables via pyo3-asyncio
    fn connect<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        pyo3_asyncio_0_21::tokio::future_into_py(py, async move {
            inner.connect().await.map_err(to_pyerr)?;
            Ok(())
        })
    }

    fn subscribe_trades<'py>(
        &self,
        py: Python<'py>,
        instrument_id: InstrumentId,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inner = self.inner.clone();
        pyo3_asyncio_0_21::tokio::future_into_py(py, async move {
            inner.subscribe("trades", &instrument_id.symbol.as_str()).await.map_err(to_pyerr)?;
            Ok(())
        })
    }
}
```

### Phase 6: Python Adapter Layer

Standard Python module structure under `nautilus_trader/adapters/your_adapter/`:

| File | Role |
|------|------|
| `__init__.py` | Public exports |
| `config.py` | `YourDataClientConfig(LiveDataClientConfig)`, `YourExecClientConfig(LiveExecClientConfig)` |
| `data.py` | `YourDataClient(LiveMarketDataClient)` — wraps Rust client, implements subscribe/unsubscribe |
| `execution.py` | `YourExecClient(LiveExecutionClient)` — wraps Rust client, implements submit/cancel/modify |
| `providers.py` | `YourInstrumentProvider(InstrumentProvider)` — loads instruments via HTTP client |
| `factories.py` | `YourLiveDataClientFactory`, `YourLiveExecClientFactory` — registered with TradingNode |

### Phase 7: Testing

**Rust unit tests**: Test parsing, signing, serialization in isolation.

**Rust integration tests**: Use `axum` to create mock HTTP/WS servers:
```rust
#[tokio::test]
async fn test_fetch_instruments() {
    let mock_server = axum::Router::new()
        .route("/api/instruments", get(|| async { Json(mock_instruments()) }));
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();
    tokio::spawn(axum::serve(listener, mock_server).into_future());

    let client = YourHttpClient::new(&format!("http://{addr}"), test_credentials());
    let instruments = client.fetch_instruments().await.unwrap();
    assert_eq!(instruments.len(), 2);
}
```

**Python integration tests**: Test full data flow from mock server → Rust client → Python adapter → Nautilus DataEngine.

## Instrument Cache Architecture

Dual-tier caching for performance:

| Tier | Type | Purpose |
|------|------|---------|
| Hot cache | `DashMap<InstrumentId, InstrumentAny>` | Concurrent read/write during live operation |
| Cold cache | `AHashMap<InstrumentId, InstrumentAny>` | Fast read-only lookups after initial load |

Provider loads instruments via HTTP → populates both tiers. WebSocket updates modify hot cache. Strategy lookups hit hot cache first.

## Naming Conventions

| Category | Convention | Example |
|----------|-----------|---------|
| Channels | Lowercase venue channel names | `"trades"`, `"orderbook"`, `"ticker"` |
| Types | Venue prefix + Nautilus concept | `BinanceTrade`, `BybitOrderBookDelta` |
| Fields | Snake case matching venue docs | `order_id`, `client_order_id`, `venue_order_id` |
| Crate name | `nautilus-your-adapter` | `nautilus-binance`, `nautilus-bybit` |

## Connection Lifecycle

**Data client sequence**: `connect()` → load instruments → cache instruments → subscribe channels → receive data → `_handle_data()` → DataEngine

**Execution client sequence**: `connect()` → authenticate → subscribe user data stream → reconcile open orders → ready for order submission

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

Load from environment variables (`VENUE_API_KEY`, `VENUE_API_SECRET`). Never log credentials. Use `zeroize` to clear memory on drop.
