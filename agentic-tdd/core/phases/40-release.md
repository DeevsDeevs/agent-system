# Phase: RELEASE

Validate the complete evidence chain and operational readiness, then make the final
deterministic transition. The release reviewer is mandatory and internal.

## Enter

`engine transition <feature> RELEASING`, `engine verify <feature>` clean.

## Mandatory release reviewer

Spawn `roles/release-reviewer.md` fresh-context, read-only. Packet: frozen artifacts,
summarized evidence index, manifest, challenge dispositions, waivers — never the
development transcript. The reviewer checks:

- **Integrity** — assessed commit equals candidate commit; plan/contract/oracle/protected
  versions match; nothing protected changed after assessment; every challenge finding has
  a disposition; accepted critical/major findings verified closed.
- **Completeness** — required checks actually ran against the candidate commit; replay
  and performance obligations met where required; no unresolved blocking question;
  residual risks explicit.
- **Scope and readiness** — final diff matches approved scope; interface and migration
  effects documented; rollout, monitoring, rollback/kill-switch paths exist where
  required; waivers have owner, rationale, expiration, follow-up.

Output: a report naming the exact `candidate_tree` it reviewed, with decision
`RELEASE_APPROVED | RETURN_TO_PLAN | RETURN_TO_LOOP | RETURN_TO_ASSESS |
USER_SIGNOFF_REQUIRED | RELEASE_BLOCKED | INSUFFICIENT_EVIDENCE`
(`templates/reviewer-report.json`). `INSUFFICIENT_EVIDENCE` is a legitimate verdict —
it routes to ASSESS rather than forcing a guess. Ingest it:

```text
engine review ingest <feature> --report .tdd/<feature>/release/report.json
```

The engine rejects a report bound to any other candidate tree, and `CLOSED` is
unreachable without an ingested `RELEASE_APPROVED`, dispositioned challenges, zero open
blocking questions, and unexpired waivers. The reviewer never edits artifacts and never
authors waivers; waivers exist only via `engine waiver authorize` with USER authority.

## User sign-off

Ask the USER (via `WAITING_FOR_USER_RELEASE`) only for: accepting a known
performance/risk deviation, unresolved compatibility impact, residual semantic
uncertainty, or a temporary waiver (record per `templates/release-decision.json`).

## Exit

- `RELEASE_APPROVED` → write `release/release-decision.json`, `rollout-plan.md`,
  `rollback-plan.md`, `monitoring-plan.md`, `retro.md`; then
  `engine transition <feature> CLOSED --result release/result.json`;
  append observations to `.tdd/memory.jsonl`; `engine unprotect <feature>`.
- `RETURN_TO_*` → transition to the owning phase with the reviewer finding attached.
- `RELEASE_BLOCKED` → transition, report blockers to the USER, stop.
  `engine unprotect` is also legal here if the USER abandons the feature.

Retro records: phase/repair/challenge counts, escaped vs caught defect classes, controls
that paid off, controls that were dead weight, user decisions and waivers.
