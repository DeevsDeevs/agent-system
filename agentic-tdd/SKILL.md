---
name: agentic-tdd
description: Phase-based resumable agentic TDD loop (PLAN → LOOP → ASSESS → RELEASE) with protected test evidence, deterministic engine gates, fresh-context falsification, and optional external challenges. Use when the user asks for a tdd loop, agentic tdd, /tdd, protected tests, or to plan/implement/assess/release a feature under the TDD workflow.
---

# Agentic TDD (Claude Code shim)

The runtime-agnostic workflow lives in `core/`. Read `core/ORCHESTRATOR.md` first and
follow it; this shim only binds it to the Claude Code runtime.

## Runtime bindings

- **Engine**: `node <this-skill-dir>/core/scripts/tdd-engine.mjs <cmd> <feature> --root <target repo>`
  via Bash (requires node >= 22 on PATH). Treat only its typed JSON output as
  authoritative.
- **Roles**: launch packets with the Agent tool (general-purpose, or a matching
  specialist agent when available). Critique, tester-qa acceptance authoring, assess,
  release-review, and challenge runs always start as fresh agents — never reuse the
  implementing context to judge its own work. Apply `options.models.<step>` via the
  Agent tool's model parameter. Launch independent perspectives in one message so they
  run in parallel.
- **Recurrence**: the main session drives the state machine — after each phase completes,
  read `engine status` and dispatch the next phase until `CLOSED`, a `WAITING_FOR_USER_*`
  state, or `BUDGET_EXHAUSTED`. Resume in a fresh session from `engine status` alone.

## Boundaries

- Never bypass the engine to edit `manifest.json` or protection state by hand.
- Verdicts, transitions, and blockers come from engine enums and structured role
  reports, never from prose.
- This directory's `core/` is a byte-identical mirror; canonical source is
  `deevs-pi-kit/skills/agentic-tdd/core/`. Edit there and copy.
