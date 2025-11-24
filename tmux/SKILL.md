---
name: tmux
description: Control interactive CLI programs in tmux panes
---

# tmux - Interactive Terminal Control

Control interactive CLI programs (REPLs, debuggers, servers) in separate tmux panes.

## Core Commands

```bash
# Simple execution (auto-cleanup)
tmux-ctl eval "npm test"

# REPL one-shot
tmux-ctl repl python "2+2"          # → 4
tmux-ctl repl node "console.log(42)" # → 42
tmux-ctl repl psql mydb "SELECT * FROM users LIMIT 5"

# REPL session (persistent, maintains state)
tmux-ctl repl python
tmux-ctl exec "import sys"
tmux-ctl exec "x = 42"
tmux-ctl exec "x + 10"              # → 52
tmux-ctl close

# Long-running processes
tmux-ctl start "npm run dev" --name=server --wait="Server started"
tmux-ctl logs server --tail=20
tmux-ctl stop server

# Parallel execution
tmux-ctl start "npm run build" --name=build
tmux-ctl start "npm test" --name=test
tmux-ctl ps                         # list all
tmux-ctl wait build test            # wait for completion
tmux-ctl logs build | grep "Success"
tmux-ctl stop build test

# Context switching
tmux-ctl use server                 # switch to named process
tmux-ctl exec "ls"                  # runs in server context
```

## When to Use

- **eval**: One-off commands, get output
- **repl**: Python/Node/psql REPLs (one-shot or persistent)
- **exec**: Execute in current context
- **start/stop**: Long-running processes with named tracking
- **ps/logs**: Monitor running processes
- **use**: Switch between contexts

## Supported REPLs

Auto-configured: `python`, `node`, `psql`

## Patterns

**Testing interactive script:**
```bash
tmux-ctl start "./installer.sh" --name=installer
tmux-ctl use installer
tmux-ctl exec "username"            # answer prompts
tmux-ctl exec "y"
tmux-ctl logs installer | grep "Success"
```

**Parallel builds:**
```bash
tmux-ctl start "npm run build" --name=build
tmux-ctl start "npm run lint" --name=lint
tmux-ctl wait build lint
```

**Database queries:**
```bash
tmux-ctl repl psql mydb "SELECT COUNT(*) FROM users"
```

For low-level API, troubleshooting, and advanced usage: see `reference.md`
