# C++/HFT verification matrix (loaded by the cpp-hft profile)

Minimum controls by change class. "Applicable subset" is decided in PLAN and recorded in
`test-plan.md`; ASSESS verifies the recorded subset actually ran.

| Change class | Minimum controls |
|---|---|
| Pure local deterministic function | unit tests, boundary tests, warnings/static checks |
| Numerical formula | analytic anchors, property/metamorphic tests, tolerance policy, differential oracle where possible |
| Parser/protocol change | malformed-input tests, fuzzing, replay, compatibility checks, sanitizer coverage |
| Stateful market-data logic | deterministic replay, sequence/duplicate/gap/reset cases, state invariants, snapshot reconciliation |
| Order/position/risk state | idempotence, partial fill/reject/cancel races, reconciliation invariants, fail-closed paths, shadow validation |
| Concurrent/lock-free code | TSan where applicable, controlled interleavings, memory-order review, false-sharing/layout review |
| Hot-path optimization | protected semantic oracle, allocation checks, repeated relative benchmark, assembly inspection where needed |
| Time-sensitive logic | monotonicity, clock-domain assumptions, reversal/staleness cases, deterministic timestamps in tests |
| Rollout-sensitive change | historical replay, shadow mode, monitoring, rollback/kill switch |

Domain cases where relevant: duplicate/missing/out-of-order messages; sequence reset and
session transition; snapshot/incremental reconciliation; halts and instrument-definition
changes; tick/lot-size transitions; partial fills, rejects, cancel races, duplicated
executions; position/PnL/risk-limit reconciliation; burst load, backpressure, stale
signals; lookahead and data leakage; allocation, cache behavior, tail latency.

## Performance protocol

"p99 within budget" is insufficient without a reproducible protocol. Record in
`performance-plan.json`: machine profile, affinity, NUMA, governor/turbo, compiler and
flags, build type, warmup/measured iterations, repetitions, input dataset, pinned
baseline commit, metric deltas (p50/p99/p999 relative, throughput min, allocations per
event max), and the decision rule. Compare repeated measurements against the pinned
baseline; a single observation decides nothing.

## Systems assessment additions (layer D)

Lifetime/ownership, UB, overflow/narrowing/alignment/aliasing, exception and failure
paths, atomics and memory ordering, races and false sharing, hot-path allocations and
layout, compiler flags and floating-point environment (`fast-math` implications),
ABI/build-system impact.
