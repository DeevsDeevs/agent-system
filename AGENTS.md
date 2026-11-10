# agent-system

Skills that work the same in Claude Code, Codex and pi. One folder per skill under
`skills/<name>/` with a `SKILL.md`; `npx skills` installs them.

- A skill here must not depend on one agent's tools. Describe the job ("run it in hc",
  "a subagent"), not a tool name only one agent has. pi-only tools live in deevs-pi-kit.
- Long-running work points at the `hc` skill; durable context points at `chains`.
- `chains/chain.mjs`: one file, Node built-ins only, no build step. Keep the `.chains`
  file format stable; other agents and a Herdr mod read it. Run `node --test test/`
  after changing it.
- `hc-flow/flow.mjs`: same rules, Node built-ins only. Its tests run against a fake `hc`
  (`test/fake-hc.mjs`); real runs need an hc core.
- Keep `SKILL.md` short; put details in sibling files the skill links to.
- Commits: lowercase conventional commits, no AI attribution.
