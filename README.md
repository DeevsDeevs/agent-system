# HFT Research Agents — The "Street HFT" Squad

ROI-driven research agents for High-Frequency Trading. Two modes: **BRAINSTORM** (new ideas) or **IMPROVE** (existing implementation). Full research cycle with rejection tracking.

## Philosophy

- **ROI over elegance** — a heuristic that works 51% at 10ns beats a "correct" model at 10ms
- **Explicit mechanism** — no data mining, every signal has a causal story
- **Linear baselines first** — no ML until OLS/LARS fails
- **C++ first** — if it needs Python, it's research, not production
- **ASK USER** — at every stage where judgment is needed

## Installation

```bash
/plugin marketplace add git@github.com:yk4r2/research-agents.git
/plugin install hft-experts@research-agents
```

## Two Modes

| Mode | User has | Focus | Output |
|------|----------|-------|--------|
| **BRAINSTORM** | Ideas, no results | Formalize, challenge, improve | Ranked testable hypotheses |
| **IMPROVE** | Data/code/charts | Find gaps, debug, enhance | Prioritized improvements |

## The Full Research Cycle

```
1. INTAKE          → ASK USER: Mode? Venue? Constraints?
2. DECOMPOSE       → Break into tasks (data-sentinel FIRST)
3. GATHER          → Collect hypotheses from alpha agents
4. CHALLENGE #1    → dummy-check: simplicity + causality
5. CHALLENGE #2    → business-planner: ROI + signal-validator: speed
6. DIG DEEPER      → Detailed analysis on survivors
7. VALIDATION PLAN → What tests prove/disprove each hypothesis?
8. FINAL OUTPUT    → Ranked hypotheses + rejection log + next actions
```

## Agents

| Agent | Color | Role |
|-------|-------|------|
| `business-planner` | 🟢 GREEN | ROI gatekeeper. Scorecard (< 15/25 = KILL). |
| `dummy-check` | 🩷 PINK | Simplicity + causal interrogator. Blocks jargon. |
| `hft-strategist` | 🔴 RED | Tech Lead. Orchestrates the full cycle. |
| `data-sentinel` | 🔵 CYAN | Data validator. ALWAYS FIRST. Grades A/B/C/F. |
| `microstructure-mechanic` | 🔵 BLUE | Book dynamics. OBI, queue, print reactions. |
| `arb-hunter` | 💛 YELLOW | Cross-venue. Lead-lag, basis, speed plays. |
| `signal-validator` | 🟣 PURPLE | LARS/OLS/Gram-Schmidt. Speed constraint. |
| `post-hoc-analyst` | 🟠 ORANGE | Forensics. PnL decomposition into 6 suspects. |

## Rejection Tracking

Every rejected hypothesis is documented:
```
REJECTED: [Name]
Stage: [agent]
Reason: [specific]
Devil's advocate: [what might be wrong with rejection]
Reconsider if: [conditions]
```

## Key Rules

1. **ASK USER at every stage** — never proceed without validation
2. **data-sentinel FIRST** — always validate data before research
3. **dummy-check PASSES** — no deployment without simple explanation
4. **business-planner APPROVES** — no research without ROI scorecard
5. **Rejections documented** — every rejection has reasoning + reconsider conditions

## External Skills

Agents proactively use skills from the parent repository ([DeevsDeevs/agent-system](https://github.com/DeevsDeevs/agent-system)):

- **venue-expert** — Exchange-specific data characteristics and known issues
- **polars-expertise** — Fast DataFrame analysis for PnL, fills, book data
- **arxiv-search** — Check if ideas are published (published = crowded = Edge drops)
- **datetime** — Timestamp handling and timezone alignment

Install skills:
```bash
/plugin marketplace add git@github.com:DeevsDeevs/agent-system.git
/plugin install polars-expertise@deevs-agent-system
```

## Details

See [hft-experts/README.md](hft-experts/README.md) for full agent documentation.

## Credits

Fork of [DeevsDeevs/agent-system](https://github.com/DeevsDeevs/agent-system).
