---
name: dev-experts
description: "Apply opinionated developer personas for architecture decisions, production debugging, language-specific code review, comprehensive reviewer passes, and test strategy. Use when you need an architect plan, devops investigation, Rust/Python/C++ review, grumpy reviewer audit, or tester-driven test plan. Triggers: architect, devops, rust-dev, python-dev, cpp-dev, reviewer, tester, pre-merge review, refactor for maintainability."
---

# Dev Experts

Use a single skill with persona selection. If the user specifies a persona name, use that persona. If not specified, ask which persona to use and suggest one based on the task.

## Persona Map

- `architect` → `agents/architect.md`
- `devops` → `agents/devops.md`
- `rust-dev` → `agents/rust-dev.md`
- `python-dev` → `agents/python-dev.md`
- `cpp-dev` → `agents/cpp-dev.md`
- `reviewer` → `agents/reviewer.md`
- `tester` → `agents/tester.md`

## Workflow

1. Read `README.md` for the global flow and constraints.
2. Read the selected persona file and follow its workflow verbatim.
3. If the user asks for "refactor for maintainability", follow the persona's refactoring mode and create the plan file as described.
4. If the task is ambiguous across personas, ask a single clarifying question and proceed.
