---
name: anti-ai-slop
description: "After working on the code, ensure the branch contains only the minimal, idiomatic changes by removing AI-generated slop introduced on this branch."
---

## Intent

This skill reviews the **diff against main** and removes changes that are likely “AI slop”: unnecessary, non-idiomatic, or inconsistent additions that do not materially contribute to the intended feature/fix.

**Guiding principle:** keep the **smallest change that accomplishes the goal**, and match the **local conventions** of each touched file.

## Scope and diff source

Operate only on changes introduced on this branch relative to main.

Determine the diff source **in this order**:

1. `git diff --cached` (if non-empty)
2. `git diff` (if non-empty)
3. `git diff main..HEAD` (fallback)  
   If `main` does not exist locally, use `git diff master..HEAD`.

Do not refactor unrelated code outside the displayed diff hunks.

## Non-goals

- Do **not** redesign architecture, rename APIs, or move code unless required by the feature/fix in the diff.
- Do **not** remove meaningful domain comments that encode invariants, reasoning, constraints, or known pitfalls.
- Do **not** remove validation at genuine trust boundaries (I/O, parsing, network, user input, third-party callbacks).
- Do **not** change formatting rules; follow repository tooling and the file’s established style.

## What counts as AI slop

### A) Comment and documentation bloat

Remove comments/docstrings that merely narrate the code, restate names, or are inconsistent with the file’s comment density and tone.

**Python (before):**
```python
def clamp(x: float, lo: float, hi: float) -> float:
    # Ensure x is not less than lo and not greater than hi
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x
```

**Python (after):**
```python
def clamp(x: float, lo: float, hi: float) -> float:
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x
```

### B) Unnecessary defensive checks inside trusted codepaths

Remove checks that are redundant because upstream validation/types/invariants already guarantee inputs.

**Rust (before):**
```rust
pub fn normalize_tag(tag: &str) -> String {
    if tag.is_empty() {
        return String::new();
    }
    tag.trim().to_ascii_lowercase()
}
```

If the rest of the codebase treats empty tags as impossible here (validated earlier), keep only the essential logic:

**Rust (after):**
```rust
pub fn normalize_tag(tag: &str) -> String {
    tag.trim().to_ascii_lowercase()
}
```

### C) Try/catch / try blocks that add no value

Remove wrappers that only rethrow, add inconsistent logging, or hide errors without providing recovery.

**C++ (before):**
```cpp
void SaveRow(Db& db, const Row& row) {
  try {
    db.Save(row);
  } catch (const std::exception& e) {
    std::cerr << "Error saving row: " << e.what() << std::endl;
    throw;
  }
}
```

If the repository does not use log-and-rethrow at this layer, prefer:

**C++ (after):**
```cpp
void SaveRow(Db& db, const Row& row) {
  db.Save(row);
}
```

### D) Single-use variables and one-off helpers that should be inlined

Prefer inlining when it improves clarity and matches surrounding style.

**Python (before):**
```python
clean = s.strip().lower()
return clean
```

**Python (after):**
```python
return s.strip().lower()
```

**Rust (before):**
```rust
let key = format!("{}:{}", user.id, user.region);
cache.insert(key, value);
```

If `key` is not reused and inlining remains readable:

**Rust (after):**
```rust
cache.insert(format!("{}:{}", user.id, user.region), value);
```

### E) Redundant checks/casts duplicated at caller and callee

If a caller guarantees an invariant, remove repeated checks in the callee unless the subsystem consistently enforces invariants at every boundary.

**Python (before):**
```python
def handle(req: Request) -> Response:
    user = parse_user(req)  # guarantees user.id is present
    return do_work(user)

def do_work(user: User) -> Response:
    assert user.id is not None
    return Response(user.id)
```

**Python (after):**
```python
def do_work(user: User) -> Response:
    return Response(user.id)
```

### F) Style drift and inconsistency with the file

Remove or rewrite changes that introduce new patterns inconsistent with the file or repository norms, such as:

- Adding type annotations in a Python file that otherwise does not use them.
- Introducing novel error-handling idioms in Rust (e.g., custom `Result` wrappers) where the module uses simple `anyhow::Result` (or vice versa).
- Adding complex abstractions (factories/providers/managers) for small local logic.

### G) Noisy logging and narration

Remove logs that restate the line of code, are inconsistent with the module’s logging level, or spam hot paths.

**Rust (before):**
```rust
log::info!("Starting normalization");
let out = normalize_tag(tag);
log::info!("Finished normalization");
out
```

**Rust (after):**
```rust
normalize_tag(tag)
```

(Keep logs that support production debugging when the module’s convention calls for them.)

### H) Placeholder TODOs without a ticket/reference

Remove “TODO: handle edge cases” style notes that add no actionable guidance and are not aligned with repository practices.

### I) Unicode hazards and emoji noise in code/comments

Remove suspicious or unnecessary Unicode in **code and configs**, including:

- non-breaking spaces (`U+00A0`)
- zero-width characters (`U+200B`, `U+200D`)
- “smart quotes” (`“ ” ‘ ’`) in code/config
- homoglyphs in identifiers
- emojis in code comments/docs unless the repository explicitly uses them

**Python (before):**
```python
# ✅ Done! 🚀
name = "ab​c"  # zero-width space
```

**Python (after):**
```python
name = "abc"
```

(Do not “sanitize” legitimate localized/user-facing content unless it appears to be accidental.)

## Trust boundaries: when defensive checks are appropriate

Defensive checks are generally appropriate at **untrusted boundaries**, such as:

- request/CLI/env input handling
- parsing and decoding (JSON, CSV, protobuf, HTML, etc.)
- network/RPC boundaries
- filesystem reads/writes of external data
- third-party callbacks and plugin systems

Defensive checks are often slop within **trusted internal pipelines**, such as:

- post-validated domain objects
- post-auth/permission middleware
- post-schema validation
- internal-only transforms with strong invariants

When in doubt, follow existing patterns in the same module/subsystem.

## Workflow checklist

1. Identify the diff source (cached, working tree, or `main..HEAD`).
2. For each changed hunk:
   - Determine the intended behavior change.
   - Remove additions that are not required to achieve it.
   - Align with local style (naming, typing, error strategy, comment density).
3. Remove unused imports, dead code, and redundant helper layers introduced by the branch.
4. Keep changes minimal: avoid unrelated refactors.
5. Ensure changes still satisfy **AGENTS.md** (and other repo policies).
6. If repository tooling exists (formatters/linters/tests), avoid introducing new warnings.

## Final report requirement

At the end, output **only a 1–3 sentence summary** describing what you changed. No bullet points. No emojis. No extended explanation.

Example acceptable summary:
> Removed redundant input checks and log-and-rethrow blocks added in this branch, and inlined single-use helpers to match existing style. No functional behavior changes beyond the intended diff; all edits were confined to the branch’s modified hunks.
