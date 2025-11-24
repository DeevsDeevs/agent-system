---
name: tmux
description: Control interactive CLI programs in tmux panes
---

# tmux - Interactive Terminal Control

Use `tmux-ctl` to run and control interactive CLI programs (REPLs, debuggers, servers) in separate tmux panes.

## When to Use

- Testing interactive scripts that prompt for input
- Running REPLs (Python, Node, database clients)
- Debugging with lldb/gdb/pdb
- Long-running processes (servers, watchers)
- Parallel command execution
- Any CLI program that requires back-and-forth interaction

## Basic Pattern

```bash
# 1. Launch shell first (safety - prevents losing output)
PANE=$(tmux-ctl launch zsh)

# 2. Send commands
tmux-ctl send "python3" --pane=$PANE

# 3. Wait for prompt
tmux-ctl wait-for ">>>" --pane=$PANE

# 4. Interact
tmux-ctl send "2+2" --pane=$PANE

# 5. Capture output
tmux-ctl capture --pane=$PANE

# 6. Clean up
tmux-ctl kill --pane=$PANE
```

## Core Commands

```bash
tmux-ctl launch <command>           # Create pane, returns pane ID
tmux-ctl send <text> --pane=<id>    # Send text (literal mode, safe)
tmux-ctl capture --pane=<id>        # Get output
tmux-ctl wait-for <pattern> --pane=<id>  # Wait for text
tmux-ctl wait-idle --pane=<id>      # Wait until output stops
tmux-ctl kill --pane=<id>           # Kill pane
tmux-ctl interrupt --pane=<id>      # Send Ctrl+C
tmux-ctl list-panes                 # List all panes (JSON)
tmux-ctl state                      # View tracked state
```

## Critical Rules

### 1. Python REPL
**ALWAYS** use `PYTHON_BASIC_REPL=1`:
```bash
tmux-ctl send "PYTHON_BASIC_REPL=1 python3" --pane=$PANE
```
Without this, the fancy console interferes with send-keys.

### 2. Launch Shell First
```bash
# GOOD
PANE=$(tmux-ctl launch zsh)
tmux-ctl send "my-command" --pane=$PANE

# BAD - pane dies if command exits
PANE=$(tmux-ctl launch "my-command")
```

### 3. Always Wait
```bash
# GOOD
tmux-ctl send "node" --pane=$PANE
tmux-ctl wait-for ">" --pane=$PANE
tmux-ctl send "2+2" --pane=$PANE

# BAD - race condition
tmux-ctl send "node" --pane=$PANE
tmux-ctl send "2+2" --pane=$PANE  # Might arrive too early
```

## Process-Specific Patterns

### Python Debugging (pdb)
```bash
PANE=$(tmux-ctl launch zsh)
tmux-ctl send "PYTHON_BASIC_REPL=1 python3 -m pdb script.py" --pane=$PANE
tmux-ctl wait-for "(Pdb)" --pane=$PANE
tmux-ctl send "break main" --pane=$PANE
tmux-ctl wait-for "(Pdb)" --pane=$PANE
tmux-ctl send "continue" --pane=$PANE
```

### lldb (default debugger)
```bash
PANE=$(tmux-ctl launch zsh)
tmux-ctl send "lldb ./app" --pane=$PANE
tmux-ctl wait-for "(lldb)" --pane=$PANE
tmux-ctl send "breakpoint set -n main" --pane=$PANE
tmux-ctl wait-for "(lldb)" --pane=$PANE
```

### Database Clients (psql, mysql)
```bash
PANE=$(tmux-ctl launch zsh)
tmux-ctl send "psql mydb" --pane=$PANE
tmux-ctl wait-for "mydb=#" --pane=$PANE
tmux-ctl send "SELECT * FROM users;" --pane=$PANE
tmux-ctl wait-for "mydb=#" --pane=$PANE
```

### Long-Running Servers
```bash
PANE=$(tmux-ctl launch zsh)
tmux-ctl send "npm run dev" --pane=$PANE
tmux-ctl wait-for "Server started" --pane=$PANE --timeout=30
# Do work...
tmux-ctl interrupt --pane=$PANE  # Ctrl+C to stop
tmux-ctl kill --pane=$PANE
```

## State Management

All sessions/panes tracked in `.claude/tmux/sessions.json`.

**Inside tmux**: operates on current session
**Outside tmux**: auto-creates `claude-main` session in `.claude/tmux/sockets/`

State updates automatically on launch/kill.

## Tips

- Use `wait-idle` when you don't know the exact prompt
- Set timeouts: `--timeout=60` for slow commands
- Capture after each operation to verify
- `tmux-ctl list-panes` shows what's running
- `tmux-ctl state` for debugging

See `reference.md` for detailed workflows, troubleshooting, and advanced usage.
