# agent-system

Skills I use in every coding agent: Claude Code, Codex and pi, on every machine.

| Skill | What it does |
|---|---|
| [chains](skills/chains) | Markdown handoffs in `.chains/` that survive sessions, compaction and agent switches. Ships `chain.mjs` (Node, no dependencies). |
| [hc](skills/hc) | Run servers, builds and other agents through [herdr-core](https://herdr.dev), and reach other machines. |
| [diagnose](skills/diagnose) | A debugging loop: reproduce, hypothesize, probe, fix with a regression check. |
| [codebase-orientation](skills/codebase-orientation) | Map an unfamiliar code area just enough to act safely. |
| [validation-review](skills/validation-review) | A bounded test-and-review pass with a ship verdict. |
| [concept-diagrams](skills/concept-diagrams) | Architecture, flow and state diagrams grounded in the code. |
| [datadog-pup](skills/datadog-pup) | Read Datadog safely with the `pup` CLI. |

## Install

```sh
npx skills add DeevsDeevs/agent-system -g -a claude-code -a codex -a pi
npx skills update -g
```

Claude Code reads `~/.claude/skills`, Codex and pi read `~/.agents/skills`.

The old plugins (dev-experts, venue-expert, mft-research-experts and the rest) are on the
[`legacy`](https://github.com/DeevsDeevs/agent-system/tree/legacy) branch.

## Test

```sh
node --test test/
```
