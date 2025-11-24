# tmux Reference Guide

Low-level API, process patterns, and troubleshooting.

## Low-Level API

### Basic Pattern

```bash
PANE=$(tmux-ctl launch zsh)           # 1. Launch shell
tmux-ctl send "python3" --pane=$PANE  # 2. Send command
tmux-ctl wait-for ">>>" --pane=$PANE  # 3. Wait for prompt
tmux-ctl send "2+2" --pane=$PANE      # 4. Interact
tmux-ctl capture --pane=$PANE         # 5. Capture output
tmux-ctl kill --pane=$PANE            # 6. Cleanup
```

### Commands

| Command | Usage | Notes |
|---------|-------|-------|
| `launch <cmd>` | `PANE=$(tmux-ctl launch zsh)` | Returns pane ID |
| `send <text> --pane=<id>` | `tmux-ctl send "echo hi" --pane=$PANE` | Literal mode, `--no-enter` to skip Enter |
| `capture --pane=<id>` | `tmux-ctl capture --pane=$PANE` | All visible output |
| `wait-for <pattern> --pane=<id>` | `tmux-ctl wait-for ">>>" --pane=$PANE` | Regex, `--timeout=N` |
| `wait-idle --pane=<id>` | `tmux-ctl wait-idle --pane=$PANE` | MD5-based, `--idle-time=N` |
| `kill --pane=<id>` | `tmux-ctl kill --pane=$PANE` | Cannot kill current pane |
| `interrupt --pane=<id>` | `tmux-ctl interrupt --pane=$PANE` | Sends Ctrl+C |
| `escape --pane=<id>` | `tmux-ctl escape --pane=$PANE` | Sends Escape |
| `list-panes` | `tmux-ctl list-panes` | JSON output |

## Process-Specific Patterns

### Python REPL
**Critical:** Use `PYTHON_BASIC_REPL=1` to disable fancy console.
```bash
tmux-ctl send "PYTHON_BASIC_REPL=1 python3" --pane=$PANE
tmux-ctl wait-for ">>>" --pane=$PANE
```

### Python Debugger (pdb)
```bash
tmux-ctl send "PYTHON_BASIC_REPL=1 python3 -m pdb script.py" --pane=$PANE
tmux-ctl wait-for "(Pdb)" --pane=$PANE
tmux-ctl send "break main" --pane=$PANE
```

### lldb
```bash
tmux-ctl send "lldb ./app" --pane=$PANE
tmux-ctl wait-for "(lldb)" --pane=$PANE
tmux-ctl send "breakpoint set -n main" --pane=$PANE
```

### Node REPL
```bash
tmux-ctl send "node" --pane=$PANE
tmux-ctl wait-for ">" --pane=$PANE
```

### PostgreSQL
```bash
tmux-ctl send "psql mydb" --pane=$PANE
tmux-ctl wait-for "mydb=#" --pane=$PANE
tmux-ctl send "SELECT * FROM users;" --pane=$PANE
```

## Critical Rules

1. **Launch shell first** - `launch zsh` then `send "command"` (prevents pane death)
2. **Always wait** - Never send consecutive commands without waiting
3. **Use wait-idle** - When prompt unknown or complex output

## Troubleshooting

**Pane not responding:**
```bash
tmux-ctl interrupt --pane=$PANE  # Try Ctrl+C
tmux-ctl kill --pane=$PANE       # Force kill
```

**Pattern not found:**
```bash
tmux-ctl capture --pane=$PANE | tail -20  # Check actual output
tmux-ctl wait-idle --pane=$PANE           # Use idle instead
```

**Python REPL not working:**
Missing `PYTHON_BASIC_REPL=1` - fancy console interferes with send-keys.

**State out of sync:**
```bash
tmux list-panes              # Check actual panes
tmux-ctl state | jq .        # Check tracked state
```

## State Files

- `.claude/tmux/sessions.json` - Session/pane tracking
- `.claude/tmux/context.json` - Current context (high-level API)
- `.claude/tmux/named_panes.json` - Named processes
- `.claude/tmux/sockets/` - tmux socket files

**Inside tmux:** Uses current session
**Outside tmux:** Creates `claude-main` in `.claude/tmux/sockets/`

## Command Reference

### High-Level API
```bash
eval <cmd>                    # Run, return output, auto-cleanup
repl <type> [cmd]             # REPL (python/node/psql)
exec <cmd>                    # Execute in current context
close                         # Close current context
use <name>                    # Switch to named process
start <cmd> --name=<n>        # Start long-running process
  [--wait=<pattern>]
stop <name...>                # Stop process(es)
ps                            # List processes
logs <name> [--tail=N]        # View logs
wait <name...>                # Wait for processes
```

### System Commands
```bash
status                        # Show tmux status
state                         # Show tracked state
help                          # Show help
version                       # Show version
```
