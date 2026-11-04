---
name: codebase-orientation
description: "Map an unfamiliar code area before editing: 'orient me', 'zoom out', 'where does this fit', multi-file or subsystem relationships."
---

# Codebase Orientation

Build the smallest accurate map that makes the next action safe. Orientation, not diagnosis or architecture critique — with a concrete failing symptom, orient only far enough to find the area, then switch to `diagnose`.

## Contract

Bound the map before exploring; ask one scope question if scope is unclear. Never map the whole repo by default.

```text
Target: [feature/module/crate/error path]
Scope: [repo root + allowed dirs]
Question: [what the map must answer]
Stop when: [next safe action is clear]
```

## Operating loop

1. Find repo shape and rules: project instructions, workspace layout, entrypoints, docs, tests, scripts.
2. Trace the relevant path from user-visible trigger or public API to the code that matters.
3. Name core concepts: types, traits, modules, services, state, invariants.
4. Find callers/callees — enough to understand impact, not every reference.
5. Find validation hooks: narrow build/test/check commands and fixtures.
6. Stop and summarize: map plus recommended next step.

Bounded searches only: `rg`, `find`, package metadata, obvious entrypoints. Source-of-truth order: source/tests/config/CI beat project docs; project docs beat chains. Mark uncertainty instead of smoothing conflicts.

Tools: read files directly, shell for bounded searches, an explore subagent only when the area spans enough files that a bounded read-only map helps (explicit `cwd`, paths, output shape; continue other mapping work while it runs), a small Mermaid diagram only when it beats prose, a chain save only when the map is useful future context.

## Rust checklist (inspect only what is relevant)

Workspace/crate boundaries (`Cargo.toml`, `cargo metadata --no-deps`, features) · command conventions (README, AGENTS.md, Justfile, CI) · entrypoints (`lib.rs`, `main.rs`, `mod.rs`) · public API and module tree · key structs/enums/traits · state sharing (`Arc`, locks, caches, globals) · async boundaries, channels, retries, timeouts · error types and `Result` flow · feature flags and `cfg` gates · tests/fixtures and narrow commands (`cargo check -p`, `cargo test -p <crate> <filter>`). No full-workspace checks unless narrower ones are impossible.

## Output

Compress small orientations; skip empty headings. Include file paths; distinguish facts from inferences.

```text
What this area does
Main files/modules — path, why it matters
Entrypoints
Important types/contracts
Call/data flow
State and invariants
Validation hooks — command, what it proves
Risks before editing
Recommended next step
```

## Pitfalls

No implementing or root-causing during orientation, no giant repo maps, no asking the user for cheaply readable facts, no trusting docs over source, no hiding uncertainty. A list of files is not an orientation — explain why each file matters.
