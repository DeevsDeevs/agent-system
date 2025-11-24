# Dev Experts

Critical, opinionated developer personas focused on approach and methodology.

## Experts

### /architect - Technical Lead & Architect
Plans features and implementation. Critical, explores alternatives, creates actionable plans.

**Workflow**:
- Interrogates requirements
- Challenges assumptions
- Explores 2-3 alternatives with trade-off analysis
- Asks you to choose
- Creates implementation plan in `.claude/experts/plans/[slug].md`

**Use when**: Designing features, architecture decisions, implementation planning

---

### /devops - Production Detective
Hunts bugs, investigates failures, debugs infrastructure. Methodical and systematic.

**Workflow**:
- Gathers evidence (symptoms, timing, changes)
- Forms hypotheses (2-3 root causes)
- Tests systematically
- Provides diagnostic commands and investigation path

**Use when**: Production issues, mysterious bugs, deployment failures

---

### /rust-dev - Rust Purist
Idiomatic, safe Rust. Hunts un-Rusty patterns.

**Focus**:
- Ownership & borrowing issues
- Error handling patterns
- Type system usage
- Async correctness
- Performance optimizations
- Safety violations

**Use when**: Rust code review, idiom improvements

---

### /python-dev - Pythonista
Clean, type-safe, modern Python. Hunts un-Pythonic code.

**Focus**:
- Type safety (hints, validation)
- Async pitfalls
- Error handling
- Modern Python features (3.10+)
- Data structures (dataclasses, TypedDict)
- Code smells

**Use when**: Python code review, modernization

---

### /reviewer - Grumpy Code Wizard
40 years experience. Infinite attention span. Brutally honest but helpful.

**Notices**:
- Security holes
- Race conditions
- Performance sins (O(n²), N+1 queries)
- Edge cases (empty inputs, overflow, concurrent access)
- Maintainability issues

**Output**: Line-by-line analysis with specific fixes

**Use when**: Pre-merge review, security audit, bug hunting

---

### /tester - Testing Specialist
Writes comprehensive, real-world tests. No fake tests or useless comments.

**Workflow**:
- Understands test infrastructure
- Analyzes changes
- Identifies test cases (happy path, edge cases, errors)
- Writes real tests with actual data

**Use when**: Writing tests, improving coverage

## Installation

```bash
/plugin marketplace add git@github.com:DeevsDeevs/agent-system.git
/plugin install dev-experts@deevs-agent-system
```
