# CTP SDK Version History

CTP (综合交易平台) developed by SFIT (上海期货信息技术有限公司). No public changelog — reconstructed from community sources (openctp, CSDN, vnpy, PyPI).

---

## Version Table

| Version | Date (approx) | Key Changes | Breaking? | 看穿式 Status | SimNow |
|---------|--------------|-------------|-----------|--------------|--------|
| 6.3.11 | 2018-01-09 | Pre-穿透式 baseline | N/A | Not supported | Dead after 2019-06-14 |
| 6.3.13 | 2018-11-19 | 穿透式评测版; adds ReqAuthenticate for AppID/AuthCode | Yes (new auth flow) | Evaluation only | Eval only |
| **6.3.15** | **2019-02-20** | **穿透式生产版**; InstrumentID = char[31] | Yes from 6.3.11 | Mandatory | Yes (_se suffix) |
| 6.3.19_P1 | ~2020-04-23 | Fixed Windows采集库 memory leak; CTP_GetDataCollectApiVersion; new error codes | Minor | Full | Yes |
| **6.5.1** | **2020-09-08** | **InstrumentID char[31] to char[81]**; IPv6; ReqQryClassifiedInstrument; UnSubscribeMarketData | **CRITICAL** | Full | Yes |
| 6.6.1_P1 | ~2021 | 8 new SPBM (郑商所组保) query interfaces | Moderate | Full | Yes |
| 6.6.7 | ~2022 early | SPBM updates; OpenSSL optimization; ExchangeID encoding fix | Minor | Full | Yes |
| 6.6.9 | 2022-08-20 | Further SPBM/combination margin updates | Minor | Full | Yes |
| **6.7.0** | ~2023 early | **LZ4 query compression** (~30% bandwidth); 12 new RCAMS/SPBM interfaces | Yes (protocol) | Full | Depends |
| 6.7.1 | ~2023 | Incremental | Minor | Full | Yes |
| 6.7.2 | 2023-09-13 | SHFE SPMM新组保; 4 new query interfaces | Minor | Full | Yes |
| 6.7.7 | ~2024 | Available on PyPI as ctp_python-6.7.7 | Likely minor | Full | Yes |
| 6.7.8 | ~2024 | Incremental | Unknown | Full | Yes |
| 6.7.9 | 2025-02-25 eval / 2025-03-19 prod | Latest confirmed production | Unknown | Full | Yes |
| 6.7.10 | ~2025 | Listed in openctp | Unknown | Full | Yes |
| 6.7.11 | ~2025 | Latest known | Unknown | Full | Yes |

Versions 6.7.3-6.7.6 appear skipped in public numbering.

---

## The InstrumentID Breaking Change (v6.5.1)

Single most important struct change in CTP history for binary compatibility.

| Attribute | Old (v6.3.x) | New (v6.5.1+) |
|-----------|-------------|---------------|
| Typedef | `char TThostFtdcInstrumentIDType[31]` | `char TThostFtdcInstrumentIDType[81]` |
| Build tag | N/A | `6.5.1_20200908` |
| Purpose | Standard instrument codes | DCE long combination option contract codes (组合合约代码) |

Impact:
- +50 bytes per InstrumentID across dozens of structs
- `CThostFtdcDepthMarketDataField` contains both InstrumentID and ExchangeInstID (both changed), adding ~100 bytes
- Struct sizes: ~440-480 bytes (v6.3.x) to ~540-580 bytes (v6.5.1+)
- Code compiled against v6.3.x headers CANNOT work with v6.5.1+ DLLs
- Evidence: CTPIIMini API V1.5.8 manual from SFIT states "TFtdcInstrumentIDType 由31扩展到81，支持组合合约代码"

---

## API Compatibility Matrix

| API Version | Min Backend | Max Backend | IPv6 | DCE Long Combo | LZ4 |
|-------------|-----------|-------------|------|---------------|-----|
| v6.3.X | 6.3.X | 6.6.X+ | No | No | No |
| v6.5.X/6.6.X | 6.5.X | 6.7.X+ | Yes | Yes | No |
| v6.7.X | 6.7.X | Current | Yes | Yes | Yes |

v6.3.X APIs can connect to newer backends but lose newer features.
v6.5.X+ CANNOT connect to v6.3.X backends.

---

## 看穿式监管 Authentication Timeline

Mandatory enforcement: **June 14, 2019**.

| Step | Detail |
|------|--------|
| Cutoff date | 2019-06-14 |
| Effect | All non-穿透式 frontends (v6.3.11 and older) taken offline |
| Required flow | `ReqAuthenticate(AppID, AuthCode)` then `ReqUserLogin` |
| SimNow AppID | `simnow_client_test` |
| SimNow AuthCode | `0000000000000000` |

Skipping ReqAuthenticate results in immediate disconnect on all production frontends post-cutoff.

---

## Three Major Breaking Upgrades

| Transition | Required Action | Severity |
|-----------|----------------|----------|
| 6.3.11 to 6.3.15 | Add ReqAuthenticate call; use _se suffix DLLs | High |
| 6.3.x to 6.5.1 | Full recompilation; all struct sizes change due to InstrumentID expansion | Critical |
| 6.6.x to 6.7.0 | LZ4 compression protocol; requires broker backend upgrade to 6.7.X | High |

---

## Sources

| Tag | File |
|-----|------|
| research-5.1 Q5 | research/research-5.1-completed.md |
| research-2 Q9 | research/research-2-completed.md |
