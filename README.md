# Deevs' Agent System

Deevs' plugin marketplace for Claude Code with workflow chains, terminal control, and expert agents.

## Installation

```bash
/plugin marketplace add git@github.com:DeevsDeevs/agent-system.git
```

## Codex Setup

Codex loads repo-scoped skills from `.codex/skills`. This repo includes symlinks to each skill folder, so no extra install step is required.

Usage:
- Invoke a skill with `$skill-name` or `/skills`.
- For chain operations: `$chain-system link <name>`, `$chain-system load <name>`, `$chain-system list`.
- For persona workflows: `$dev-experts <persona>`, `$bug-hunters <role>`, `$research-experts <role>`.

If Codex was already running, restart it to reload the skills.

Global (user-scoped) install for any repo:

```bash
git clone git@github.com:DeevsDeevs/agent-system.git ~/src/agent-system
mkdir -p ~/.codex/skills
for d in 97-dev anti-ai-slop datetime golang-pro polars-expertise arxiv-search chain-system dev-experts bug-hunters research-experts cost-status; do
  ln -s ~/src/agent-system/$d ~/.codex/skills/$d
done
```

Installer (interactive by default):

```bash
curl -fsSL https://raw.githubusercontent.com/DeevsDeevs/agent-system/main/scripts/install.sh \\
  | bash -s --
```

Installer flags: `--non-interactive`, `--platform claude|codex|both`, `--repo-ref <tag|branch|commit>`, `--uninstall`, `--skills a,b,c`.

Uninstall:
- Codex: run the installer with `--uninstall`.
- Claude Code: use `/plugin uninstall <plugin>@deevs-agent-system` inside Claude Code.

Install a single skill by URL with `$skill-installer`.

## Plugins

### chain-system

Multi-session workflow chains for maintaining context across conversations.

**Core**: Save conversation state, resume complex projects across sessions without losing technical details.

**Commands**:
- `/chain-link [name]` - Save current work to chain
- `/chain-load [name]` - Resume from saved chain
- `/chain-list` - List all chains

**Use when**: Working on multi-session projects, need to pause and resume with full context.

**Details**: [chain-system/README.md](chain-system/README.md)

```bash
/plugin install chain-system@deevs-agent-system
```

---

### dev-experts

Critical, opinionated developer personas focused on approach and methodology.

**Agents**:

**`/architect`** - Technical lead and architect
- Plans features, explores alternatives with trade-off analysis
- Creates actionable implementation plans
- Use for: Architecture decisions, feature design

**`/devops`** - Production detective
- Methodical bug hunting and failure investigation
- Forms hypotheses, tests systematically
- Use for: Production issues, mysterious bugs, deployment failures

**`/rust-dev`** - Rust purist
- Hunts un-Rusty patterns, ownership issues, safety violations
- Use for: Rust code review, idiom improvements

**`/python-dev`** - Pythonista
- Type safety, async pitfalls, modern Python (3.10+)
- Use for: Python code review, modernization

**`/cpp-dev`** - C++ performance purist
- UB, memory bugs, latency killers, lock-free correctness
- Use for: C++ code review, performance optimization

**`/reviewer`** - Grumpy code wizard, 40 years experience
- Security holes, race conditions, performance sins, edge cases
- Line-by-line analysis with specific fixes
- Use for: Pre-merge review, security audit

**`/tester`** - Testing specialist
- Comprehensive, real-world tests (no fake tests)
- Use for: Writing tests, improving coverage

**Details**: [dev-experts/README.md](dev-experts/README.md)

```bash
/plugin install dev-experts@deevs-agent-system
```

---

### alpha-squad

Five hypothesis generators attacking from complementary angles. Mechanism over fit. Counterparty over correlation.

**Agents**:

**`/fundamentalist`** - Accounting & value lens
- Financial statements, earnings quality, capital efficiency
- Use for: Mispricing from accounting misreads

**`/vulture`** - Flows & constraints lens
- Forced sellers, index reconstitutions, 13F crowding
- Use for: Constraint-driven alpha, calendar flows

**`/network-architect`** - Relationships & propagation lens
- Customer-supplier networks, lead-lag, contagion paths
- Use for: Information propagation, network effects

**`/book-physicist`** - Microstructure & entropy lens
- Order book entropy, informativity decomposition, structural models (Kyle, Hawkes)
- Use for: Microstructure alpha, order flow informativity, entropy regime detection

**`/causal-detective`** - Mechanisms & confounding lens
- Frisch-Waugh-Lovell, Double ML, placebo tests
- Use for: Proving causal mechanisms, killing confounded signals

**Details**: [alpha-squad/README.md](alpha-squad/README.md)

```bash
/plugin install alpha-squad@deevs-agent-system
```

---

### mft-research-experts

Orchestration, data validation, risk geometry, hypothesis execution, and forensic audit. The infrastructure that makes alpha-squad real - or kills it.

**Agents**:

**`/mft-strategist`** - Obsessive coordinator
- Orchestrates hypothesis generation and destruction
- Routes Data Sentinel → Alpha Squad → Factor Geometer → Skeptic
- Use for: Starting any research, SHIP/KILL/ITERATE decisions

**`/data-sentinel`** - Paranoid gatekeeper
- MUST be invoked FIRST on any data
- Trusts nothing, asks before filtering
- Use for: Any data validation

**`/factor-geometer`** - Risk architect
- Factor loadings, covariance estimation, alpha-orthogonal decomposition
- Use for: Geometry check, factor exposure analysis

**`/skeptic`** - Hypothesis executioner
- Dual causal + statistical validation gauntlet
- Use for: Full hypothesis validation (Rademacher, walk-forward, placebos)

**`/forensic-auditor`** - Post-mortem investigator
- Traces assumption failures, runs on schedule and crisis
- Use for: Pipeline review, incident investigation, periodic audit

**Details**: [mft-research-experts/README.md](mft-research-experts/README.md)

```bash
/plugin install mft-research-experts@deevs-agent-system
```

---

### bug-hunters

Systematic bug hunting with spec reconstruction, adversarial validation, and confidence-ranked reports.

**Agents**:

**`/orchestrator`** - Central brain (RED)
- Reconstructs spec from code, spawns hunters, challenges findings
- Filters false positives via adversarial validation with dev-experts
- Use for: Starting any bug hunting session

**`/logic-hunter`** - Spec detective (ORANGE)
- Language-agnostic logic bugs, spec-vs-implementation gaps
- Scan mode (hotspots) → Hunt mode (deep trace)
- Use for: Algorithm correctness, data flow issues, design intent verification

**`/cpp-hunter`** - C++ bug hunter (YELLOW)
- Memory corruption, UB, concurrency issues
- Hypothesis-driven, demands proof
- Use for: Crash debugging, memory bugs, mysterious C++ failures

**`/python-hunter`** - Python bug hunter (YELLOW)
- Async pitfalls, None propagation, type violations
- Hypothesis-driven, demands proof
- Use for: Python-specific bugs, type mismatches, async issues

**Flow**: Spec Reconstruction → Hotspot Scan → Hunter Deployment → Adversarial Challenge → Confidence Scoring → Report

**Details**: [bug-hunters/README.md](bug-hunters/README.md)

```bash
/plugin install bug-hunters@deevs-agent-system
```

---

### cost-status

Status bar showing session cost, monthly cost, total cost, and context window usage.

**Display**: `$0.52/$30.00/$150.00 | 38k/200k (19%)`

- `$session/$month/$total` - Cost tracking at three levels
- `used/max (%)` - Context window usage

**Setup**: After installation, add to `~/.claude/settings.json`:
```json
{
  "statusLine": {
     "type": "command",
     "command": "bash ~/.claude/scripts/show-cost.sh"
   },
}
```

Find the path with:
```bash
find ~/.claude -name "show-cost.sh" -path "*/cost-status/*" 2>/dev/null | head -1
```

**Details**: [cost-status/README.md](cost-status/README.md)


```bash
/plugin install cost-status@deevs-agent-system
```

### arxiv-search

Search arXiv preprint repository for academic papers.

**Core**: Query arXiv for research papers across physics, mathematics, computer science, quantitative biology, finance, and statistics.

**Quick start**:
```bash
# Basic search (auto-selects Python or bash)
arxiv_search "transformer attention mechanism"

# Limit results
arxiv_search "protein folding" --max-papers 5
```

**Use when**: Finding preprints, ML/AI papers, mathematical methods, scientific literature before journal publication.

**Dependencies**: None (bash fallback). For better reliability: `uv pip install arxiv`

**Details**: [arxiv-search/SKILL.md](arxiv-search/SKILL.md)

```bash
/plugin install arxiv-search@deevs-agent-system
```

## Agent Color Scheme

Universal color scheme across all agent plugins:

| Color | Role | Examples |
|-------|------|----------|
| ❤️ **RED** | Deciders & Orchestrators | `architect`, `mft-strategist`, `orchestrator`, `devops` |
| 🧡 **ORANGE** | Hybrid (can lead or challenge) | `logic-hunter` |
| 💛 **YELLOW** | Checkers & Validators | `reviewer`, `cpp-hunter`, `python-hunter`, `skeptic`, `forensic-auditor` |
| 💙 **BLUE** | Builders & Implementers | `cpp-dev`, `python-dev`, `rust-dev`, `tester` |
| 💚 **CYAN** | Researchers & Analysts | `data-sentinel`, `fundamentalist`, `vulture`, `network-architect`, `book-physicist`, `causal-detective`, `factor-geometer` |

## Credits

Inspired by:
- [claude-code-tools](https://github.com/pchalasani/claude-code-tools/) by pchalasani
- [superpowers](https://github.com/obra/superpowers/) by obra
- [agent-commands](https://github.com/mitsuhiko/agent-commands) by mitsuhiko
