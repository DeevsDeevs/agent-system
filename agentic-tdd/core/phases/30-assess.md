# Phase: ASSESS

Attempt to falsify that the candidate satisfies the frozen plan and contract.
Fresh context, initially read-only. Assessment never silently repairs code.

## Enter

`engine transition <feature> ASSESSING` — self-verifies; any drift from the candidate
tree fails the transition. Then create the clean evaluation environment:

```text
engine assess-worktree <feature>     # detached checkout of the exact candidate snapshot
```

All builds and checks run in that worktree, not in the developer's tree.

Spawn assessment packets fresh: logic-hunter (semantic), tester-qa (verification), plus
language/systems review where the profile requires. Packets receive: feature brief,
frozen plan/contract/oracle, baseline commit + candidate tree, diff, protected test
manifest, loop handoff and discoveries, challenge focus items. They do NOT receive the
implementation transcript, developer confidence, or failed-approach narratives.

## Layers

A. **Artifact integrity** — `engine verify` plus: did the candidate weaken/skip tests,
   change tolerances, replace reference outputs, alter benchmark inputs, disable checks,
   expand scope beyond the plan? Any hit is a finding, not a discussion.
B. **Deterministic verification** — run the applicable subset per profile through the
   engine, never self-reported:

   ```text
   engine run-check <feature> acceptance-tests --cwd .tdd/<feature>/assess/worktree -- <test argv>
   engine run-check <feature> build --cwd ... -- <build argv>
   ```

   The engine records exit codes and output hashes bound to the candidate tree; the
   `ASSESSMENT_READY` gate requires a passing bound record for every profile-required
   check id (`engine status` lists them). Property/metamorphic, differential, replay,
   fuzz, sanitizer, static-analysis, and performance runs use the same mechanism with
   their own check ids.
C. **Semantic** — P/Q/invariant conformance, violation and recovery policy, numerical
   and rounding semantics, temporal ordering, sequence/duplicate/gap/reset/idempotence,
   oracle applicability and common-mode risk, lookahead/data leakage, downstream
   compatibility.
D. **Systems** (per profile) — lifetime/ownership, UB, overflow/narrowing, exceptions,
   atomics and memory ordering, races, allocations and layout on hot paths, build flags.

## Findings

Every blocking finding follows `templates/finding.json`: falsifiable claim, violated
clause or exact code path, evidence or minimal counterexample, discriminating check,
route. Routing: implementation defect / test hole → tester-qa stages the new failing
test under `assess/run-NNN/proposed-tests/` (the candidate tree stays immutable while
judged), then `CHANGES_REQUIRED → LOOP_RUNNING`, where the test is applied, protected,
and a new candidate is produced; contract/architecture defect → `PLANNING` (direct
route, `assess/PLAN_AMENDMENT_REQUIRED` result); oracle disagreement → `PLANNING` or
user authority; missing/noisy evidence → rerun ASSESS; waiver-class decisions →
`WAITING_FOR_USER_ASSESS`.

The assessor never asks the USER to judge ordinary technical correctness.

## Exit

`assess/run-NNN/`: `assessment.md`, `findings.json`, `verdict.json`, machine results,
`result.json` with status `PASS | PASS_WITH_NONBLOCKING_FINDINGS | CHANGES_REQUIRED |
PLAN_AMENDMENT_REQUIRED | HUMAN_DECISION_REQUIRED | ASSESSMENT_INCONCLUSIVE |
BUDGET_EXHAUSTED`.

```text
engine transition <feature> ASSESSMENT_READY --result .tdd/<feature>/assess/run-NNN/result.json
```

If `options.challenges.assess`: run `phases/90-external-challenge.md` (it challenges the
assessment's coverage and verdict, not a free-form re-review), then
`transition ASSESSMENT_ACCEPTED`. Otherwise transition directly.
