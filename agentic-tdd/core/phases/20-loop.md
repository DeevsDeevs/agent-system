# Phase: LOOP

Produce a candidate implementation against frozen planning artifacts. Mechanical
iteration is cheap and unrestricted; semantic iteration returns to PLAN.

## Enter

Preconditions (engine-checked): state `PLAN_APPROVED`, `verify` clean. Then:

1. Tester-qa (fresh context) writes the protected acceptance tests from the frozen
   contract — designed from the plan, not from any patch. Verify each red test fails for
   the intended reason.
2. `engine protect <feature> <acceptance tests...> <runner configs...>` — locks them
   before implementation exists.
3. `engine transition <feature> LOOP_RUNNING`.

## Implementation

Spawn the developer packet (`roles/developer.md` + frozen plan/contract/oracle paths +
`loop/run-NNN/handoff.md` template). The developer:

- edits production code; compiles and runs focused tests freely; adds developer-local
  tests; red–green–refactor per atomic behavioral gap;
- records exact commands in `loop/run-NNN/commands.log`;
- records discoveries in `loop/run-NNN/discoveries.json`, classified:
  `MECHANICAL | IMPLEMENTATION_DEFECT` → fix in LOOP;
  `TESTABILITY_PROBLEM` → record, may stay in LOOP;
  `SPECIFICATION_AMBIGUITY | ORACLE_CONFLICT | ARCHITECTURE_DRIFT` → stop, route PLAN;
  `ENVIRONMENT_FAILURE` → stop, route environment;
- never edits protected files, tolerances, oracle semantics, benchmark thresholds, or
  scope; never special-cases known test data; never invents domain policy to unblock.

## Exit

Candidate handoff (`loop/run-NNN/` via `run begin`/`run publish`): `handoff.md` (behavior
implemented, files/interfaces changed, known limitations, recommended assessment focus),
`changes.patch`, `tests-added.md`, `discoveries.json`, `result.json`.

```text
engine transition <feature> CANDIDATE_READY --result .tdd/<feature>/loop/run-NNN/result.json
```

The transition self-verifies protected surfaces and then snapshots the exact worktree —
committed or not — into an engine-owned candidate ref. From this point every piece of
evidence binds to that tree; touching any non-`.tdd` file invalidates it until the state
machine routes back through LOOP.

Blockers transition to `BLOCKED_SPEC | BLOCKED_ORACLE | BLOCKED_ENVIRONMENT`, which route
to `PLANNING` (amend, consumes `semantic_replans`) or back to `LOOP_RUNNING` when the
environment is fixed. Repair rounds after assessment findings consume
`implementation_repairs` and re-enter via `CHANGES_REQUIRED → LOOP_RUNNING`.

If `options.challenges.loop`: run `phases/90-external-challenge.md` against the frozen
candidate before assessment; the candidate commit stays frozen.
