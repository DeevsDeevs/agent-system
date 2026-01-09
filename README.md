# Deevs' Agent System

Deevs' plugin marketplace for Claude Code with workflow chains, terminal control, and expert agents.

## Installation

```bash
/plugin marketplace add git@github.com:DeevsDeevs/agent-system.git
```

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

### tmux

Interactive terminal control for REPLs, debuggers, and servers.

**Core**: Run and control interactive CLI programs in separate tmux panes with high-level API.

**Quick start**:
```bash
# One-shot execution
tmux-ctl eval "npm test"

# REPL interaction
tmux-ctl repl python "2+2"

# Long-running process
tmux-ctl start "npm run dev" --name=server --wait="Server started"
tmux-ctl logs server
tmux-ctl stop server

# Parallel execution
tmux-ctl start "npm run build" --name=build
tmux-ctl start "npm test" --name=test
tmux-ctl wait build test
```

**Use when**: Need to interact with REPLs (Python, Node, psql), control debuggers, monitor servers, run parallel tasks.

**Details**: [tmux/README.md](tmux/README.md) | [tmux/SKILL.md](tmux/SKILL.md) | [tmux/reference.md](tmux/reference.md)

**Setup**: Add to PATH after installation:
```bash
export PATH="$PATH:$HOME/.claude/plugins/tmux@deevs-agent-system/bin"
```

**Dependencies**: bash 4.0+, tmux 2.0+, jq, md5sum/md5

```bash
/plugin install tmux@deevs-agent-system
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

**`/cpp-bug-hunter`** - C++ bug hunter
- Symptom-driven debugging, hypothesis testing, demands proof
- Use for: Crash debugging, memory corruption, mysterious failures

**`/reviewer`** - Grumpy code wizard (40 years experience)
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

## Credits

Inspired by:
- [claude-code-tools](https://github.com/pchalasani/claude-code-tools/) by pchalasani
- [superpowers](https://github.com/obra/superpowers/) by obra
- [agent-commands](https://github.com/mitsuhiko/agent-commands) by mitsuhiko
