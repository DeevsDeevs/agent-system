# Git policy

The workflow only observes and records git state; it never rewrites history or publishes.

## Ground rules

- `.tdd/` is gitignored in the target repository. Add the ignore entry at init if missing.
- Commit only functional code changes. Never commit `.tdd/`, plans, scratch files,
  editor droppings, or generated reports. Never `git add -A` / `git add .` — stage an
  explicit allowlist of files the phase actually changed.
- Never push, amend, rebase, merge, reset, tag, or force-update anything. Committing at
  all requires explicit USER approval per repository session.
- Clean tracked worktree required at init and at every phase gate (`engine verify`
  reports `modified`). Untracked garbage is reported, not blocking — but ask the USER
  once about untracked files that look like they belong in `.gitignore`.

## Commit binding

- `init` records `baseline_commit`; reaching `CANDIDATE_READY` records the exact
  `candidate_commit`; entering `ASSESSING` fails on any other HEAD.
- All evidence (test runs, replay, benchmarks) is only valid for the commit recorded
  with it. New commits invalidate downstream evidence — the engine enforces this;
  re-run, do not argue.
- New assessment tests route back through LOOP and produce a new candidate commit before
  reassessment.
