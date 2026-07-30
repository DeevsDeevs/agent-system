# Mission adapter (Pi runtime only)

A TDD Mission is a normal Mission whose objective names the feature and whose operating
procedure is this skill's state machine. Missions stay usable for ad-hoc (non-TDD) work;
nothing here changes Mission mechanics. Mission owns recurrence, controller identity,
takeover, limits, child settlement, and final review. The TDD engine owns the nested
state machine, artifacts, gates, and budgets.

## Wiring

- Create via `mission_create` only when the USER asks for a continuing TDD objective;
  run `engine init` immediately after and record feature id + `.tdd/<feature>/` path in
  the first `mission_progress` entry.
- Record a `mission_progress` milestone at every checkpoint transition: `PLAN_READY`,
  `PLAN_APPROVED`, `CANDIDATE_READY`, `ASSESSMENT_READY`, `ASSESSMENT_ACCEPTED`,
  reviewer decision, `CLOSED`.
- `WAITING_FOR_USER_*` and `BUDGET_EXHAUSTED` are genuine typed blockers: record them
  via `mission_progress` with the engine's state string and the open question ids, then
  pause substantive work.
- Complete the Mission only when the engine state is `CLOSED` (or the USER explicitly
  abandons at `RELEASE_BLOCKED`). Mission completion gates (requirement audit,
  independent review, child settlement, Chain checkpoints) still apply on top —
  engine `CLOSED` does not waive them.

## Resume and takeover

- On resume or takeover, authority comes from `engine status` and `engine verify` —
  never from `mission.md`, `log.md`, or transcript memory. If `verify` reports drift,
  that is the first blocker to record and resolve.
- Before takeover, settle or explicitly cancel known Jobs/Subagents in the old session;
  after takeover, review state is invalid — fresh-context assessment/review runs are
  required for any phase whose evidence predates the takeover generation.

## Subagent mapping

Launch role packets with `subagent` (fresh context for critique/assess/release/challenge;
one `subagent_wait` per group; parallel-first for independent perspectives). Apply
`options.models.<step>` when the runtime supports per-run model selection; otherwise
record the deviation in the phase result provenance.
