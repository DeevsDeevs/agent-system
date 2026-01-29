# Research Experts

Opinionated hypothesis generation agents for quantitative research. Mechanism over fit. Counterparty over correlation. Every hypothesis must identify who loses money and why.

## Philosophy

- **Mechanism first** - no hypothesis without a causal diagram
- **Counterparty required** - who loses money? why are they forced?
- **Data Sentinel first** - always validate data before research
- **User decides** - agents advise and ask, never assume
- **Deep by default** - dig until you understand
- **Complementary** - Alpha Squad attacks from four angles simultaneously

## Agents

### strategist - Obsessive Coordinator
The single brain that orchestrates hypothesis generation and destruction. Routes to Data Sentinel FIRST, always, no exceptions. Sequences Alpha Squad → Factor Geometer → Skeptic. Synthesizes SHIP/KILL/ITERATE.

**Invokes**: All research agents + validators
**Key trait**: Refuses to let any step proceed without understanding the full chain

---

### data-sentinel - Paranoid Gatekeeper
MUST BE INVOKED FIRST on any data. Trusts nothing. Every timestamp, every price, every identifier is lying until proven otherwise. Asks user before any filter/transform.

**Invoked by**: Strategist (always first), any agent needing data
**Key trait**: Point-in-time or point-in-lie

---

### Alpha Squad - Hypothesis Engine

Four specialists who jointly attack hypothesis generation from complementary angles. They argue with each other. They demand mechanisms. Every hypothesis must identify counterparty, constraint, decay, and Paleologo source.

#### fundamentalist - Accounting & Value Lens
Financial statements, earnings quality, capital efficiency. Finds mispricing by understanding what the market misreads in the accounting.

**Key trait**: Accruals revert. Cash flow persists.

#### vulture - Flows & Constraints Lens
Forced sellers, index reconstitutions, 13F crowding, liquidation signatures. Finds alpha from someone else's mandate, not someone else's mistake.

**Key trait**: Every forced seller has a signature

#### graph-architect - Relationships & Propagation Lens
Customer-supplier networks, lead-lag structures, contagion paths. Models how information travels along graph edges.

**Key trait**: Sector correlation is symptom. Supply chain is cause.

#### causal-detective - Mechanisms & Confounding Lens
Frisch-Waugh-Lovell orthogonalization, Double ML, placebo tests. Proves that the squad's hypotheses are causal, not confounded.

**Key trait**: Correlation is unobserved confounding until proven otherwise

---

## Flow

```mermaid
flowchart TD
    USER([USER]) --> strategist[/"strategist<br/>🔴 Obsessive Coordinator"/]

    subgraph sentinel [Data Gate]
        data-sentinel[/"data-sentinel<br/>🔵 ALWAYS FIRST"/]
    end

    subgraph squad [Alpha Squad]
        fundamentalist["fundamentalist 🔵<br/>Value"]
        vulture["vulture 🔵<br/>Flows"]
        graph-architect["graph-architect 🔵<br/>Networks"]
        causal-detective["causal-detective 🔵<br/>Mechanisms"]

        fundamentalist <-->|"value or flow?"| vulture
        graph-architect <-->|"real or spurious?"| causal-detective
        fundamentalist --> causal-detective
        vulture --> causal-detective
    end

    strategist --> data-sentinel
    data-sentinel --> squad

    squad -->|"hypothesis bundle"| validators["research-validators<br/>Factor Geometer → Skeptic"]
    validators -->|"SHIP/KILL/ITERATE"| strategist
```

**Alpha Squad Output** (every hypothesis):
- Mechanism diagram (DAG)
- Counterparty identification
- Constraint specification
- Decay estimate
- Paleologo source (risk preferences, liquidity, funding, predictable flows, information)
- Required data (to Data Sentinel)

## Key Rules

1. **Data Sentinel FIRST** - always validate data before research
2. **Counterparty required** - no hypothesis without identifying who loses
3. **Mechanism required** - no hypothesis without a causal diagram
4. **Strategist ASKS** - complementary questions every time
5. **USER DECIDES** - agents present options, never assume

## Venue Context

All agents read `EXCHANGE_CONTEXT.md` first and ask which venue mode applies.

---

## Color Scheme

❤️ RED = `strategist` (orchestrator)
💚 CYAN = `data-sentinel`, `fundamentalist`, `vulture`, `graph-architect`, `causal-detective` (researchers)

## Installation

```bash
/plugin marketplace add git@github.com:DeevsDeevs/agent-system.git
/plugin install research-experts@deevs-agent-system
```
