---
description: Drive the agentic TDD workflow (plan | loop | assess | release | challenge | status) for a feature
argument-hint: <plan|loop|assess|release|challenge|status> <feature> [--resume | --from-finding ID | --amend ID]
---

Drive the agentic-tdd skill for: $ARGUMENTS

1. Load the `agentic-tdd` skill and read its `core/ORCHESTRATOR.md`.
2. Run `node <skill-dir>/core/scripts/tdd-engine.mjs status <feature> --root <repo>`.
   If the feature is not initialized and the subcommand is `plan`, follow the
   initialization protocol (ask the USER the batched init questions first).
3. Validate that the requested subcommand matches an allowed transition from the current
   engine state; if not, report the typed state and the legal next steps instead of
   forcing it.
4. Execute the matching phase file (`core/phases/`), honoring `--resume`,
   `--from-finding`, and `--amend` by re-entering the owning phase with the referenced
   finding attached.
5. For `status`: print the engine status plus open questions, budgets, and the next
   required command. Never mutate state from a status call.
