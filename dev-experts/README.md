# Dev Experts

Critical, opinionated developer personas as autonomous agents. Claude invokes them automatically based on task context, or you can invoke manually.

## Agents

### architect - Technical Lead & Architect
Auto-invoked for feature design and implementation planning. Critical, explores alternatives, creates actionable plans.

**Workflow**:
- Interrogates requirements
- Challenges assumptions
- Explores 2-3 alternatives with trade-off analysis
- Asks you to choose
- Creates implementation plan in `.claude/experts/plans/[slug].md`

**Auto-invoked when**: Designing features, architecture decisions, implementation planning

---

### devops - Production Detective
Auto-invoked for debugging production issues and infrastructure problems. Methodical and systematic.

**Workflow**:
- Gathers evidence (symptoms, timing, changes)
- Forms hypotheses (2-3 root causes)
- Tests systematically
- Provides diagnostic commands and investigation path

**Auto-invoked when**: Production issues, mysterious bugs, deployment failures

---

### rust-dev - Rust Purist
Auto-invoked for Rust code review and refactoring. Hunts un-Rusty patterns.

**Focus**:
- Ownership & borrowing issues
- Error handling patterns
- Type system usage
- Async correctness
- Performance optimizations
- Safety violations

**Refactoring Mode**: Invoke with "refactor for maintainability" to get comprehensive refactoring plans saved to `.claude/plans/[slug]-ref.md`

**Auto-invoked when**: Rust code review, idiom improvements, refactoring requests

---

### python-dev - Pythonista
Auto-invoked for Python code review and refactoring. Hunts un-Pythonic code. Mandates UV and msgspec.

**Focus**:
- Type safety (hints, msgspec validation)
- Async pitfalls
- Error handling
- Modern Python features (3.10+)
- Data structures (dataclasses, TypedDict)
- Code smells

**Mandates**: UV for package management, msgspec for validation (not Pydantic)

**Refactoring Mode**: Invoke with "refactor for maintainability" to get comprehensive refactoring plans saved to `.claude/plans/[slug]-ref.md`

**Auto-invoked when**: Python code review, modernization, refactoring requests

---

### cpp-dev - C++ Performance Purist
Auto-invoked for C++ code review and refactoring. HFT mindset. Hunts UB, memory bugs, latency killers.

**Focus**:
- Use-after-free, dangling refs, missing RAII
- Hot path allocations, cache misses, false sharing
- Memory ordering bugs, ABA problems
- Integer overflow, bounds violations
- Concepts over SFINAE, constexpr everywhere

**Refactoring Mode**: Invoke with "refactor for maintainability" to get comprehensive refactoring plans saved to `.claude/plans/[slug]-ref.md`

**Auto-invoked when**: C++ code review, performance optimization, modernization, refactoring requests

---

### cpp-bug-hunter - C++ Bug Hunter
Auto-invoked for hunting C++ bugs from symptoms. Paranoid interrogator who demands proof.

**Focus**:
- Use-after-free, double-free, buffer overflow
- Data races, deadlocks, memory ordering
- Signed overflow, strict aliasing, ODR violations

**Auto-invoked when**: Crash debugging, memory corruption, mysterious failures

---

### reviewer - Grumpy Code Wizard
Auto-invoked for comprehensive code review before commits/PRs. 40 years experience. Reads EVERY line.

**Catches**:
- Security holes
- Race conditions
- Performance sins (O(n²), N+1 queries)
- Edge cases (empty inputs, overflow, concurrent access)
- Maintainability issues

**Output**: Line-by-line analysis with specific fixes

**Auto-invoked when**: Pre-merge review, security audit, bug hunting

---

### tester - Testing Specialist
Auto-invoked when writing tests for new features. Writes comprehensive, real-world tests. No fake tests or useless comments.

**Workflow**:
- Understands test infrastructure
- Analyzes changes
- Identifies test cases (happy path, edge cases, errors)
- Writes real tests with actual data

**Auto-invoked when**: Writing tests, improving coverage

## Installation

```bash
/plugin marketplace add git@github.com:DeevsDeevs/agent-system.git
/plugin install dev-experts@deevs-agent-system
```
