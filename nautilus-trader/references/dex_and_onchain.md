# DEX & On-Chain Trading

Hyperliquid, dYdX v4 supplements, and common DEX patterns in NautilusTrader v1.224.0.

## Hyperliquid Deep Dive

Hyperliquid is a DEX on its own L1 chain. No API keys — wallet-based authentication.

### Wallet Authentication

```python
from nautilus_trader.adapters.hyperliquid import (
    HYPERLIQUID, HyperliquidExecClientConfig,
)

exec_config = HyperliquidExecClientConfig(
    private_key="0xabc...",             # EVM wallet private key
    vault_address=None,                  # set for vault trading
    testnet=False,
)
```

No API key, no API secret — just the wallet private key. Orders are signed locally and submitted to the Hyperliquid L1.

### normalize_prices

Default `True`. Rounds prices to 5 significant figures before submission.

```
Input: 95123.456 → Normalized: 95123.0
Input: 0.00045678 → Normalized: 0.00045678 (already ≤5 sig figs)
Input: 1.23456 → Normalized: 1.2346
```

This is required because Hyperliquid enforces 5 significant figures on all prices. Setting `normalize_prices=False` means you must handle this precision yourself.

### Vault Trading

```python
exec_config = HyperliquidExecClientConfig(
    private_key="0xabc...",
    vault_address="0xdef...",           # vault contract address
)
```

When `vault_address` is set, orders are executed on behalf of the vault. The wallet must be an authorized trader for that vault.

### Order Book Behavior

Hyperliquid sends **full order book snapshots**, not incremental deltas. This means:
- Higher bandwidth per update
- No gap detection or resync logic needed
- Every update is a complete picture of the book

### Configuration Fields

| Field | Default | Notes |
|-------|---------|-------|
| `private_key` | `None` | EVM wallet key (exec only) |
| `vault_address` | `None` | For vault trading |
| `testnet` | `False` | Use Hyperliquid testnet |
| `normalize_prices` | `True` | Round to 5 sig figs |
| `http_proxy_url` | `None` | HTTP proxy |
| `ws_proxy_url` | `None` | WebSocket proxy |
| `http_timeout_secs` | `10` | HTTP request timeout |

### Instrument Provider Filters

```python
from nautilus_trader.config import InstrumentProviderConfig

# Load only perpetual instruments
instrument_provider=InstrumentProviderConfig(
    load_all=True,
    filters={"market_types": ["perp"]},
)
```

Filter keys: `market_types` (or `kinds`): `["perp"]`, `["spot"]` | `bases`: `["BTC", "ETH"]` | `quotes`: `["USDC"]` | `symbols`: `["BTC-USD-PERP"]`

### Symbology

- Perpetuals: `BTC-USD-PERP.HYPERLIQUID`, `ETH-USD-PERP.HYPERLIQUID`
- Spot: `PURR-USDC-SPOT.HYPERLIQUID`
- Cross-margin only — no isolated margin mode

## dYdX v4 Supplement

See [exchange_adapters.md](exchange_adapters.md) for base dYdX configuration. Additional details:

### Cosmos SDK Transactions

dYdX v4 is a Cosmos SDK appchain. Orders are blockchain transactions submitted via gRPC:
- **Short-term orders**: In-memory on validators, expire within a few blocks. Higher throughput, lower latency
- **Long-term orders**: Written to state (on-chain). Constrained by block time. Use for GTC orders

Short-term orders are preferred for HFT — lower latency, higher rate limits, but they expire automatically. Check dYdX docs for current rate limits.

### Order Classification

dYdX auto-classifies orders:

| Category | Storage | Expiry | Use Case |
|----------|---------|--------|----------|
| Short-term | In-memory | Block height (~10s) | IOC/FOK, or GTC/GTD within short window |
| Long-term | On-chain | UTC timestamp | GTC (defaults 90-day), GTD |
| Conditional | On-chain | UTC timestamp | Stop-loss, take-profit |

- **Market orders**: No native market orders. Adapter sends aggressive IOC limit at `oracle_price × 1.01` (buy) / `× 0.99` (sell)
- Short-term orders: broadcast concurrently, expire silently without cancel events
- Long-term orders: serialized via semaphore, exponential backoff (500ms → 4s, max 5 retries)
- Multiple gRPC fallback: `base_url_grpc="https://primary:443,https://fallback:443"`

### Subaccount Model

dYdX uses subaccounts (0-127) per wallet. Each subaccount has independent:
- Positions
- Orders
- Margin calculations

Configure via `DydxExecClientConfig(subaccount=0)`.

## Common DEX Patterns

### Wallet vs API Key Auth

DEX adapters sign transactions locally with a wallet private key. CEX adapters use API key + secret for authenticated REST/WS requests. The specific auth method differs per venue and may change — check the adapter config class for current fields.

| Venue Type | General Approach | NautilusTrader Config Field |
|------------|-----------------|---------------------------|
| DEX (Hyperliquid, dYdX) | Wallet private key | `private_key` |
| Hybrid (Polymarket) | Wallet + API creds | `private_key` + `api_key/secret/passphrase` |
| CEX (Binance, Bybit, OKX) | API key + secret | `api_key` + `api_secret` |

### On-Chain Settlement Considerations

- **Finality**: DEX trades are final when the block is confirmed. CEX trades are final immediately
- **Gas/fees**: Varies — some DEXes have protocol-level fees, others require chain gas (e.g., Polygon gas for Polymarket)
- **Order signing latency**: On-chain signature adds latency compared to CEX API calls. Varies by chain and signing method
- **Rate limits**: Blockchain throughput replaces traditional rate limits. Some DEXes (like dYdX) add explicit per-block limits

### Testnet

| Venue | Testnet Support | Config |
|-------|----------------|--------|
| Hyperliquid | Yes | `testnet=True` |
| dYdX | Yes | `is_testnet=True` |
| Polymarket | No official testnet | — |
