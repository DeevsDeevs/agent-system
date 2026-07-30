# Permissions and protected surfaces

Separation is useful only when it creates different information exposure, different
writable surfaces, different evidence obligations, independent falsification, or
deterministic gates outside the authoring agent's control.

| Surface | Coordinator | Architect | Logic-hunter | Developer | Tester-qa | Release reviewer | External challenger |
|---|---|---|---|---|---|---|---|
| Production code | protect | read | read | **write in LOOP** | read | read | read |
| Architecture | version/freeze | **propose in PLAN** | comment | critique | critique | read | challenge |
| Contract | version/freeze | comment | **propose in PLAN** | critique | critique | read | challenge |
| Protected acceptance tests | protect via engine | read | propose semantic cases | read/run only | **write outside DEV control** | read | read/challenge |
| Developer-local tests | record | read | read | **write** | read | read | read |
| Oracle/reference | freeze | review | **propose/supervise** | review/run | test/challenge | read | challenge |
| Tolerances | freeze | comment | propose | no write | challenge | verify | challenge |
| Performance harness | protect | propose constraints | comment | run, never weaken | propose/validate | verify | inspect |
| Findings | version/dispose | submit | submit/classify | respond | submit/classify | review dispositions | submit |
| Waivers | record | no | no | no | no | verify | no |

Authors may propose revisions to their own artifacts; a revision becomes authoritative
only after independent review and a coordinator version bump. The implementation agent
never controls the evidence that judges it.

## Threat model

Protected hashes, immutable flags/chmod, engine-validated transitions, and candidate
tree binding defend against **cooperative-agent drift and accidents** — an agent
forgetting the rules, silently weakening a test, or assessing the wrong code. They are
NOT isolation from a malicious or compromised same-user process, which could restore
permissions, rewrite `manifest.json`, or re-freeze hashes. The practical mitigations the
engine does provide: evidence executes through `run-check` (assessors interpret, they
cannot fabricate records), assessment runs in a clean detached worktree of the exact
candidate snapshot, and every mutation lands in the append-only event log for after-the-
fact audit. Stronger guarantees require a second user or containerized evaluator —
out of scope for this kit.
