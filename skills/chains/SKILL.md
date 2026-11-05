---
name: chains
description: "Save, load, fork and search .chains links: work context that survives sessions, compaction and handoffs between agents (Claude Code, Codex, pi). Use on 'continue', 'resume', 'pick up', 'where were we', 'save progress', before a long task switch, and when handing work to another agent."
---

# Chains

A chain is a folder of markdown links in the project: `.chains/<chain>/<timestamp>-<slug>.md`.
Each link is a handoff: what was asked, what's done, what was decided, what's next. Any
agent on any machine reads the same files.

Run the bundled script from this skill's folder (Node is on PATH):

```sh
C=<this skill's folder>/chain.mjs
node $C list [--max N]               # chains here, newest first, with next steps (sessions start with this)
node $C list <chain>                 # its links, newest first
node $C load <chain>                 # newest link on main (--branch B, --link FILE)
node $C context <chain>              # newest link + 2 parents + recent titles: for resuming or a delegate
node $C search <words> [--chain C]   # ranked hits with the matching line
node $C save <chain> --next "…" < link.md     # parent = the branch's newest link
node $C fork <chain> <branch>        # prints the parent for the branch's first save
```

`.chains` is found by walking up from the current folder, no further than the git root (outside
git, no further than just below `~`); a new one goes at the git root, else in the current folder.
`--json` on any command gives JSON. Chain and branch names: letters, digits, `.`, `_`, `-`.

## When to load

- "Continue", "resume", "pick up", or a reference to earlier work: `load` or `context`
  the named chain; if you don't know which, `list`, then `search`.
- Before non-trivial work in a project with a `.chains` folder: one quick `search` before
  rediscovering old decisions.
- A link older than 7 days (marked stale), or one that conflicts with the files: treat it
  as a lead to verify, not as fact.

## When to save

- After a milestone: feature works, fix verified, design decided, approach rejected for a
  reason worth keeping, review done.
- Before context may be lost: long session, before compacting, task switch, handoff,
  stopping with work pending.
- Not for one-shot answers, tiny edits, or what the git diff already says, and never when
  the user says not to.

Always pass `--next` with the single next step. Write the link as a handoff another agent
could act on without this conversation:

1. Request and intent
2. Key decisions and why
3. Work completed (files, commands, results)
4. Open issues, blockers, risks
5. Next step

For important handoffs, follow `link-rubric.md` in this folder. Include exact paths,
commands, ids and unresolved errors; skip routine tool chatter.

## Branches

`main` is the default. Branch only for a different hypothesis: a competing design, a risky
spike, a delegate's research track. Continuations, fixes and end-of-session handoffs stay
on the current branch.

```sh
node $C fork work spike              # → parent: <file>
node $C save work --branch spike --parent <file> --next "…" < link.md
```

When a branch is accepted or dropped, save an outcome link on `main`.

## Handing work to another agent

Put `node $C context <chain>` output (or the chain name and "run the chains skill's
`context`") in the delegate's task, whether it's a subagent or an agent started with hc.
When its report changes decisions, exposes a risk or creates follow-up work, save a link
naming who reported and what changed.

## Without Node

Write the file yourself, same layout: `.chains/<chain>/YYYY-MM-DD-HHMMSSmmm-<slug>.md`
(local time), starting with

```yaml
---
chain: "<chain>"
branch: "main"
parent: "<previous link's file name>"
nextStep: "<next step>"
created: "<ISO time>"
---
```

Load = read the newest file; search = `rg` in `.chains`.
