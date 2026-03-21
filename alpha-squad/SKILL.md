---
name: alpha-squad
description: "Run multi-lens hypothesis generation across accounting, flows, networks, microstructure, and causal checks. Use when you need market hypotheses with mechanism, counterparty, and decay. Triggers: alpha squad, fundamentalist, vulture, network-architect, book-physicist, causal-detective, hypothesis generation, mechanism first."
---

# Alpha Squad

Use this skill when the user wants market hypotheses generated from complementary lenses.

## Role Map

- `fundamentalist` -> `agents/fundamentalist.md`
- `vulture` -> `agents/vulture.md`
- `network-architect` -> `agents/network-architect.md`
- `book-physicist` -> `agents/book-physicist.md`
- `causal-detective` -> `agents/causal-detective.md`

## Workflow

1. Read `README.md` and enforce mechanism-first reasoning.
2. If the user specified one role, spawn exactly that role with `agent_type` and task context.
3. If no role was specified, spawn all five roles in parallel and ask each for 1-3 high-conviction hypotheses.
4. Use `wait` to gather results, then synthesize a single hypothesis slate.
5. Ensure every proposed hypothesis includes counterparty, constraint, decay horizon, and mechanism sketch.
6. If confidence is weak or confounding is likely, run a follow-up pass with `causal-detective` before presenting final output.
