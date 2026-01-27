# Binance Platform Rules and Compliance

Reference for Binance operational rules, compliance requirements, and regulatory considerations.

## Platform Overview

### Legal Entities

Binance operates through multiple legal entities with different jurisdictions:

| Entity                | Jurisdiction        | Target Users          |
|-----------------------|--------------------|-----------------------|
| Binance Holdings      | Cayman Islands     | Global (non-restricted)|
| Binance.US            | United States      | US residents only     |
| Binance Europe        | Various EU states  | European users        |
| Binance Japan         | Japan              | Japanese users        |

**Critical:** Each entity has different:
- Available products
- Trading pairs
- API endpoints
- Compliance requirements

### Restricted Jurisdictions

**Binance Global restrictions (as of knowledge cutoff):**

| Region              | Status             | Notes                 |
|--------------------|--------------------|-----------------------|
| United States      | Blocked            | Must use Binance.US   |
| United Kingdom     | Restricted         | Limited derivatives   |
| Japan              | Blocked            | Must use Binance Japan|
| Canada (Ontario)   | Blocked            |                       |
| Netherlands        | Blocked            |                       |
| Germany            | Restricted         | Limited products      |

**Note:** Restrictions change frequently. Verify current status before deployment.

## Account Requirements

### KYC/AML Tiers

**Binance Global verification levels:**

| Level      | Requirements              | Withdrawal Limit (24h) |
|------------|---------------------------|------------------------|
| Unverified | Email only                | None (trading disabled)|
| Basic      | Government ID             | 0.06 BTC equivalent    |
| Intermediate| ID + Selfie + Address    | 100 BTC equivalent     |
| Advanced   | Full verification         | Higher limits          |

**Binance.US:**
- KYC required for all trading
- Must verify US residency
- Social Security Number required

### Account Restrictions

**Prohibited activities:**
- Market manipulation (wash trading, spoofing, layering)
- Unauthorized automated trading (must comply with API ToS)
- Accessing from restricted jurisdictions via VPN
- Operating multiple accounts
- Using exchange for money laundering

**Enforcement:**
- Account suspension
- Funds frozen pending investigation
- Permanent ban
- Reporting to authorities

## API Usage Rules

### Terms of Service Compliance

**Permitted uses:**
- Personal trading automation
- Portfolio management
- Market data analysis
- Research and backtesting

**Prohibited uses:**
- Reselling market data without agreement
- Interfering with platform operations
- Exploiting system vulnerabilities
- Excessive load causing service degradation

### Rate Limit Compliance

**Obligations:**
- Monitor rate limit headers
- Implement backoff on 429 responses
- Do not retry during ban periods
- Spread requests to avoid bursts

**Penalties:**
- 2 minute to 3 day IP bans
- Account restrictions for repeated violations
- Permanent API access revocation

### Data Usage Rights

**Market data:**
- Free for personal/internal use
- Commercial redistribution requires data license
- Attribution may be required

**Restrictions:**
- Cannot claim ownership of Binance data
- Cannot modify data in misleading ways
- Cannot use for competitive benchmark publication

## Trading Rules

### Order Requirements

**Minimum notional:**
- Varies by trading pair
- Typically 10 USDT equivalent
- Query via /exchangeInfo filters

**Precision requirements:**

| Parameter | Filter                | Description              |
|-----------|----------------------|--------------------------|
| Price     | PRICE_FILTER         | Tick size compliance     |
| Quantity  | LOT_SIZE             | Step size compliance     |
| Notional  | MIN_NOTIONAL         | Minimum order value      |
| Percent   | PERCENT_PRICE        | Price vs mark price      |

### Self-Trade Prevention

**Binance policy:**
- Self-trades may execute (no built-in STP)
- User responsible for avoiding self-trades
- Excessive self-trading may trigger review

### Market Manipulation

**Prohibited practices:**

| Practice    | Description                              |
|-------------|------------------------------------------|
| Wash trading| Simultaneous buy/sell to inflate volume  |
| Spoofing    | Large orders intended to be canceled     |
| Layering    | Multiple orders to create false depth    |
| Pump & dump | Coordinated price manipulation           |

**Detection:**
- Automated surveillance systems
- Cross-reference with other venues
- Pattern analysis on order/trade data

## Listing and Delisting

### Listing Process

**New token requirements:**
- Technical review
- Legal compliance
- Community/market interest
- Security audit

**No guaranteed listing:**
- Payment does not ensure listing
- Binance reserves full discretion

### Delisting Process

**Triggers:**
- Regulatory concerns
- Security vulnerabilities
- Project abandonment
- Low trading activity
- Legal issues

**Timeline:**
- Usually 24-48 hours notice
- Trading suspended at announced time
- Withdrawal window (varies, often 30-90 days)
- Remaining balances may be converted

**Impact on trading:**
- Liquidity decreases sharply
- Spreads widen significantly
- Data quality degrades

## Futures-Specific Rules

### Leverage Restrictions

**Retail users:**
- Maximum leverage may be capped (varies by jurisdiction)
- New users may have lower initial limits
- Leverage limits may be reduced during volatility

**Example restrictions:**
- UK users: No futures access
- Some EU jurisdictions: Leverage caps

### Funding Rate Limits

**Cap:** Funding rate typically capped at ±0.75% per period

**Rationale:** Prevents extreme funding payments during market stress

### Liquidation Rules

**Insurance fund priority:**
1. Insurance fund covers losses
2. ADL (Auto-Deleveraging) if fund depleted
3. No socialized loss system

**ADL fairness:**
- Highest leverage + highest P&L liquidated first
- Transparent ranking visible to users

## Compliance Monitoring

### Surveillance Systems

**Trade surveillance:**
- Real-time monitoring of unusual patterns
- Cross-market surveillance
- Blockchain analysis integration

**Account monitoring:**
- Risk scoring
- Geographic access patterns
- Withdrawal behavior

### Reporting Obligations

**Binance may report:**
- Suspicious Activity Reports (SARs)
- Tax information (where required)
- Law enforcement requests

**User obligations:**
- Accurate KYC information
- Tax reporting in home jurisdiction
- Compliance with local laws

## Incident Response

### System Failures

**Binance commitments:**
- Best-effort reliability (no SLA for retail)
- Status page updates during incidents
- Post-incident reports for major events

**User protections:**
- Socialized loss prevention
- Insurance fund for liquidation failures
- Compensation fund (SAFU) for hacks

### Disputes

**Resolution process:**
1. Support ticket
2. Internal review
3. Arbitration (per ToS)
4. Regulatory complaint (varies by jurisdiction)

**Limitations:**
- No class action participation (waived in ToS)
- Binding arbitration clauses
- Limited appeal rights

## Regulatory History

### Significant Events

| Date       | Event                                    |
|------------|------------------------------------------|
| 2019       | US users restricted to Binance.US        |
| 2021       | UK FCA warning                           |
| 2021       | Japan/Germany/Italy regulatory actions   |
| 2022       | Increased KYC requirements globally      |
| 2023       | US SEC lawsuit filed                     |

**Impact on operations:**
- Geographic restrictions expanded
- Product availability reduced
- Compliance overhead increased

### Ongoing Concerns

**Areas of regulatory focus:**
- Securities classification of tokens
- Derivatives access for retail
- Stablecoin reserves
- Consumer protection
- Anti-money laundering

## Implementation Considerations

### Geographic Detection

**Binance checks:**
- IP address geolocation
- KYC document country
- Phone number country code
- Bank account jurisdiction

**Implications:**
- VPN usage may trigger account review
- Inconsistent geographic signals flagged
- Account may be restricted pending verification

### Compliance Automation

**Recommended practices:**
- Check user eligibility before API integration
- Monitor for delisting announcements
- Implement trading halts when required
- Log all API activities for audit trail

### Risk Warnings

**Required disclosures (many jurisdictions):**
- Cryptocurrency is volatile
- Leverage magnifies losses
- Past performance no guarantee
- Only risk capital you can afford to lose

## Implementation Checklist

- [ ] Verify target jurisdiction is not restricted
- [ ] Complete appropriate KYC level
- [ ] Review API ToS before deployment
- [ ] Implement rate limit compliance
- [ ] Monitor delisting announcements
- [ ] Track regulatory changes affecting operations
- [ ] Maintain audit trail of API activities
- [ ] Implement geographic access controls if needed
- [ ] Document compliance measures for audit
- [ ] Review insurance/protection mechanisms
