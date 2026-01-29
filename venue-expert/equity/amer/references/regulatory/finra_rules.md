# FINRA Rules for Equity Trading

FINRA (Financial Industry Regulatory Authority) rules governing broker-dealer conduct in equity markets.

## FINRA Role

FINRA is the self-regulatory organization (SRO) for broker-dealers. Key functions:
- Rulemaking for member firms
- Examination and enforcement
- Trade reporting infrastructure (TRFs)
- Dispute resolution

## Rule 5310 - Best Execution

### Core Obligation

Broker-dealers must use "reasonable diligence" to ascertain the best market for a security and buy/sell at the most favorable terms reasonably available.

### Factors to Consider

| Factor | Description |
|--------|-------------|
| Character of market | Liquidity, volatility |
| Size and type of transaction | Block vs retail |
| Number of markets checked | Venue coverage |
| Accessibility of quotation | Can you actually access? |
| Terms and conditions | Price, speed, likelihood |

### Regular and Rigorous Review

Firms must conduct regular, systematic evaluation of execution quality received from market centers.

**Required analysis:**
- Compare executions to industry benchmarks
- Evaluate speed of execution
- Assess price improvement statistics
- Review fill rates

### Order-by-Order vs Firm-Wide

Best execution can be assessed:
- On individual order basis (difficult)
- Through systematic review of execution quality across order flow

Most firms use systematic review with exception handling.

## Rule 5320 - Manning Rule (Limit Order Protection)

### Prohibition

Broker-dealer holding customer limit order cannot trade ahead of that order for its own account at the same or better price.

### Exceptions

| Exception | Condition |
|-----------|-----------|
| Riskless principal | Offsetting customer order |
| Institutional order | Specific size thresholds |
| Not held orders | Customer grants discretion |
| Block positioning | Facilitating customer block |

### Practical Impact

Market makers must manage their proprietary trading relative to customer order flow.

## Rule 6100 Series - Trade Reporting

### TRF Overview

Trade Reporting Facilities capture off-exchange trades:
- OTC trades between members
- ATS executions
- Internalization

### Reporting Deadlines

| Trade Type | Deadline |
|------------|----------|
| Regular hours | 10 seconds |
| Extended hours | As soon as practicable |

### Required Information

- Security identifier
- Price and quantity
- Time of execution
- Capacity (principal/agent)
- Reporting party
- Contra party (if applicable)

### Tape Assignment

TRF trades disseminated on appropriate tape:
- Tape A/B for NYSE/regional listings
- Tape C for Nasdaq listings

## Rule 6400 Series - Quoting Obligations

### Market Maker Obligations

Registered market makers must:
- Maintain two-sided quotes
- Honor quoted size
- Meet minimum quoting requirements

### Quote Size Requirements

Minimum quote sizes vary by security tier and price.

## Rule 6700 Series - ATS Requirements

### ATS Reporting

ATSs must report:
- Weekly volume and transactions
- Fair access compliance
- System capacity

### Reg ATS-N

Enhanced disclosure requirements for ATSs:
- Operation description
- Order types
- Segmentation practices

## Rule 11000 Series - Customer Order Handling

### Order Handling Procedures

Requirements for:
- Order receipt timestamps
- Order routing procedures
- Customer notification

### Time-in-Force Handling

Proper handling of:
- Day orders
- GTC orders
- IOC/FOK orders

## FINRA Infrastructure

### FINRA/Nasdaq TRF

Joint facility operated by FINRA and Nasdaq for Tape C trade reporting.

### FINRA/NYSE TRF

Facility for Tape A/B trade reporting.

### ORF (Over-the-Counter Reporting Facility)

For OTC equity securities not on NMS.

## Examination Focus Areas

FINRA examination priorities often include:

| Area | Focus |
|------|-------|
| Best execution | Systematic review processes |
| Order routing | PFOF conflicts |
| Trade reporting | Timeliness, accuracy |
| Books and records | Complete audit trail |

## Enforcement

### Common Violations

- Failure to use reasonable diligence
- Trading ahead of customer orders
- Late/inaccurate trade reporting
- Inadequate supervisory procedures

### Penalties

- Fines (often $100K-$1M+ for large firms)
- Censure
- Suspension
- Bars for individuals

## Official Sources

**FINRA Rulebook:**
- https://www.finra.org/rules-guidance/rulebooks/finra-rules

**Best Execution:**
- Rule 5310: https://www.finra.org/rules-guidance/rulebooks/finra-rules/5310

**Trade Reporting:**
- TRF overview: https://www.finra.org/filing-reporting/trade-reporting-facility-trf

**Regulatory Notices:**
- Guidance on best execution reviews
- Trade reporting updates

## Quant Implications

### For Execution Analysis

- Best execution audits need quantitative metrics
- Compare execution quality vs benchmarks
- Document venue selection rationale

### For Trade Data

- TRF prints are real volume but not queue-driven
- Separate analysis for lit vs TRF flow
- Report timing affects real-time analytics

### For Compliance

- Systematic best execution review required
- Manning rule affects proprietary trading
- Trade reporting accuracy is audited
