---
name: diagnose
description: "Disciplined debugging loop for broken behaviour, failing builds, flaky commands, hung processes or regressions. Use when asked to debug or find a root cause."
---

# Diagnose

Use when correctness is uncertain. Do not patch from vibes: make the bug observable, prove the cause, fix the smallest thing, verify against the original symptom. Use the target repo's native build/test/runtime commands as the evidence loop.

## 1. Define the symptom

```text
Expected: ...
Actual: ...
Observed in: command/log/file/process id/agent id/artifact id
```

If the report is vague, ask for the missing observable (exact command, stack trace, id, log path, repro steps). Do not chase unrelated warnings until they connect to this symptom.

## 2. Orient just enough

Identify only the smallest relevant area: repo root/cwd, package/crate/service, entrypoint triggering the symptom, closest test/fixture/log source, and expensive commands to avoid. Never map the whole codebase.

## 3. Build the feedback loop

Find the fastest deterministic loop that reaches the bug, e.g. `cargo test -p <crate> <filter> -- --nocapture`, a focused unit test, a CLI run on fixture input, a request script against a dev server, a replay of a captured event, or a small throwaway harness when no seam exists.

- Slow repro loops and servers: run them in hc (`hc run --bg`, then `hc wait` or `hc wait --output <ready line>`; see the `hc` skill) — never `&`, `nohup`, `disown`, `setsid`.
- Subagents only for independent investigation, tightly scoped with `cwd` and exact files; continue other runnable probes while it runs; its report arrives by itself.
- For long diagnoses, save a chain link (`chains` skill) with the symptom, repro command, hypotheses tested, files touched, ids, and next step.

Do not proceed until the loop reproduces the bug or proves more evidence is needed.

## 4. Reproduce and minimize

Confirm the loop matches the user's symptom, not a nearby failure. Then reduce to the smallest file set, command, input, and package, and the shortest log excerpt that proves the problem. For flaky bugs, raise the reproduction rate: repeat, isolate shared state, pin cwd, tune concurrency/stress, record pass/fail counts.

## 5. Hypothesize before probing

Non-obvious bugs: 3–5 ranked hypotheses before changing code. Obvious ones: state the single likely cause and its confirming check.

```text
Hypothesis: [cause]
Prediction: if true, [specific check] shows [specific result].
Probe: [command/read/log inspection]
```

"The retry budget is shared across requests; two concurrent fixture calls will exhaust the same counter" is a hypothesis. "State bug" is not.

## 6. Probe narrowly

One hypothesis, one variable per probe. Prefer existing logs/tests/traces before adding instrumentation; tag any added debug output with a unique marker like `[DEBUG-7f3a]`; probe decision boundaries, never "log everything". Keep notes: hypothesis → probe → result → next.

Rust probes: `RUST_BACKTRACE=1`, targeted `RUST_LOG=<module>=debug`, focused assertions, trait impl/feature-flag/cfg inspection, shared state through `Arc`/locks/caches/globals, behavior with/without concurrency/retries/timeouts. For performance regressions, measure a baseline (command, input, sample size, variance) before fixing; then bisect or profile.

## 7. Fix with a regression guard

State the minimal fix and what will prove it. After editing: rerun the minimized loop, the original loop, and the narrowest relevant package checks; add a durable regression check when a good test seam exists — if none does, say so and recommend the smallest future validation improvement.

## 8. Cleanup and report

Remove `[DEBUG-...]` probes and throwaway harnesses, stop unneeded background processes, reference useful artifacts by id/path. Report: root cause, fix, verified-by, remaining risk / follow-up.

## Pitfalls

- No patching before reproducing unless the user explicitly accepts a speculative fix.
- No whole-workspace runs when a package-level loop proves the symptom.
- A passing narrow check counts only after the original repro also passes.
- Broad subagent sweeps are not "diagnosis"; bound cwd, files, and tool count.
