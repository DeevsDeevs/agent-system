---
name: hc
description: "Run work through herdr-core (hc): servers, builds, test suites, CI watches and anything slow; commands and files on other machines; another agent or model (Claude Code, Codex, pi) as a peer; messages between agent sessions. Use whenever $HC_TERMINAL_ID is set and work would block your shell, outlive your turn, or leave this machine."
---

# hc

You run in an hc terminal (`$HC_TERMINAL_ID` is your address). The person watches every hc
terminal in the Herdr app and can take any of them over. Full manual: `hc --skill`; read
it before anything not covered here.

## What goes where

| Work | Use |
|---|---|
| A sub-task inside your turn: research, a review pass, a workflow | your own subagents / workflows, not hc |
| A server, build, test suite, CI watch, anything slow | `hc run --bg`, then `hc wait` |
| Another agent or model as a peer you or the person can steer | `hc run --bg <agent>` (see `peers.md`) |
| A command or file on another machine | `hc exec` / `hc file` / `hc run --on` (see `remote.md`) |
| Talking to another agent's session | `hc send`, `hc wait`, `hc read` |

Never `&`, `nohup`, `setsid`, `disown`, or a foreground `sleep` to wait: hc keeps the
process visible, outlives your turn, and `hc wait` returns the moment it's done.

## Recipes

```sh
# slow command: you stay free while it runs
hc run --bg --rm --no-notify --name build cargo build --release
hc wait build                       # exit code; --rm removes it after

# server: start, wait until ready, use it, stop it
hc run --bg --name web --cwd app bun dev
hc wait web --output "ready"        # matches output printed after the wait starts
hc read web --lines 50
hc kill web; hc rm web

# several at once
hc run --bg --name unit cargo test
hc run --bg --name lint cargo clippy --all-targets
hc wait --children any              # next one to finish; repeat or use --children all
```

- `hc wait` times out after 180 s by default: that's a check-in, not a failure; wait again.
- `hc run` without `--bg` streams output and returns after 180 s with `[hc] still running
  as tN`: wait on that address, don't start it twice.
- Clean up what you started (`hc kill`, `hc rm`). `hc ls` shows the person's other work
  too: never touch terminals you didn't start.

## Gotchas

- Never `hc server stop`, and never restart the core: every terminal on it dies.
- Starting `hc` when no core is running starts one with your shell's environment, and
  every later terminal inherits it. On the person's own machine, check `hc ls` works
  before running anything else.
- From inside an hc terminal, `hc run` children end when you end; add `--outlive-parent`
  for something that must keep running.
- `hc send` wraps the text as a message, so `/compact` or any slash command arrives as
  chat. Type it as keys: `hc keys <t> / c o m p a c t`, then `hc keys <t> enter`.
- Codex under hc needs `--no-daemon`.
