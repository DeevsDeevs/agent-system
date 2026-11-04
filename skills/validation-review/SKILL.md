---
name: validation-review
description: "Bounded test and review pass for completed or proposed changes: verify, review before merge, check requirements, run e2e or smoke tests."
---

# Validation Review

Answer one question: **is this change good enough to ship under the user's review budget?** This is post-change validation, not open-ended debugging — if checks expose a concrete failure, report it in the verdict; switch to `diagnose` only when asked to root-cause.

## 1. Set the budget

Identify or ask for scope (files/diff/branch), budget (max time, commands, subagents, e2e depth), and required evidence (unit/integration/e2e/manual smoke/signoff). Default budget when none given: inspect the diff and nearby tests, run narrow relevant checks, at most one focused subagent, and ask before full-workspace, expensive, destructive, or full-e2e runs.

## 2. Review matrix

Four angles — for each, know what evidence would change the verdict:

1. **Requirements** — satisfies the request and acceptance criteria?
2. **Logic** — edge cases, invariants, errors, state, concurrency, security.
3. **Evidence** — tests/e2e/smoke that prove behavior.
4. **Slop** — overbuild, fake confidence, brittle mocks, ignored failures, noisy docs.

## 3. Inspect and run checks

Use project-native facts (changed files, callers, tests, CI conventions, specs/chains) and the narrowest meaningful command — e.g. `cargo check -p <crate>`, `cargo test -p <crate> <filter>`, `cargo clippy -p <crate> --all-targets` — full workspace or e2e only when budget and conventions justify it.

Build a small dependency graph before running checks. Launch independent read-only checks and perspectives together; do not wait for typecheck before starting an unrelated docs/security review. Keep fix → targeted recheck and final-diff → review gates sequential. Do not parallelize commands that write the same outputs, contend heavily for the same resource, or would review a changing diff. Once the diff is frozen, full validation and independent final review should usually run concurrently, then be reconciled into one verdict.

For servers/browsers/e2e: run them in hc (`hc run --bg`, `hc wait --output <ready line>`; see the `hc` skill); run the smoke action with real assertions; capture concise evidence; `hc kill` and `hc rm` what you started when done. No large log dumps.

## 4. Perspectives

Subagents only within budget, each scoped with `cwd`, exact files/diff, command limits, and output shape. Launch independent perspectives as several `Agent` calls in one message and continue other runnable checks; each reports back by itself. Useful angles: tests (missing tests, e2e plan), review (requirements, correctness), slop (overbuild, fake tests), and a language or ops specialist when the change needs one. Never delegate what one local command or file read proves.

Ask each reviewer an open question (what breaks, what is missing, which requirement is unmet), never to confirm that the change works. Change work that already passes only for a finding backed by a stated requirement or a failing check; for a concrete defect, such as a security hole, a race, data loss or a missed edge case, write the check that reproduces it first, then fix it; record the rest as follow-ups.

## 5. Judge test quality

Good evidence exercises observable behavior through the right public seam, would catch the regression, is deterministic, and asserts meaning — not just "does not crash". Bad evidence: implementation-detail tests, unexplained snapshot updates, mocks bypassing the risky path, e2e actions without assertions, green checks unrelated to the change, expected values computed with the production formula, coverage numbers offered instead of proven behaviors, bug fixes without a reproducer that failed pre-fix, tests that pass only in one order.

Altitude check: pure refactor → zero existing tests change; new feature or bug fix → tests added, existing unchanged; behavior change → the only case existing tests may change. A test breaking outside its case is a change-detector finding — flag it, never fix the test to green the diff.

## Verdict format

```text
Verdict: Ship | Ship with follow-ups | Do not ship yet

Requirements
- met/missing: ...

Checks run
- command/e2e action — observed/planned/not run — pass/fail — what it proves

Review findings
- Blocker/Major/Minor/Nit — file/path — issue — recommended fix

Subagent perspectives
- perspective: key finding or "not used: reason"

Remaining risk / Next action
- ...
```

Severity: **Blocker** wrong behavior, data loss, security, failing required check · **Major** requirement gap or untested risky path · **Minor** maintainability · **Nit** optional polish, never blocks.

## Pitfalls

- "Tests pass" is not proof requirements are met; a proposed command or coverage number is not evidence at all.
- Never run expensive checks just to look thorough, ignore failed commands, or fake e2e coverage with unasserted actions.
- Keep subagents inside budget; name remaining risk instead of shipping hidden uncertainty.
