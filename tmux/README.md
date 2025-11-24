# tmux

Interactive terminal control for REPLs, debuggers, and servers.

## Overview

Control interactive CLI programs in separate tmux panes. Send commands, wait for output, capture results - all programmatically.

**Use for**: Testing scripts with prompts, running REPLs (Python, Node, psql), debugging (lldb, pdb), long-running servers, parallel execution.

## Commands

**Core:**
- `tmux-ctl launch <command>` - Create pane, returns pane ID
- `tmux-ctl send <text> --pane=<id>` - Send text (literal mode, safe)
- `tmux-ctl capture --pane=<id>` - Get output
- `tmux-ctl kill --pane=<id>` - Kill pane

**Synchronization:**
- `tmux-ctl wait-for <pattern> --pane=<id>` - Wait for text
- `tmux-ctl wait-idle --pane=<id>` - Wait until output stops

**Control:**
- `tmux-ctl interrupt --pane=<id>` - Send Ctrl+C
- `tmux-ctl escape --pane=<id>` - Send Escape

**Info:**
- `tmux-ctl list-panes` - List all panes (JSON)
- `tmux-ctl state` - View tracked state
- `tmux-ctl status` - Show mode and sessions

## Workflow

```bash
# 1. Launch shell (safety - pane persists if command fails)
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

## Critical Rules

**Python REPL** - Always use `PYTHON_BASIC_REPL=1`:
```bash
tmux-ctl send "PYTHON_BASIC_REPL=1 python3" --pane=$PANE
```

**Always wait** - Never send commands without waiting for prompts:
```bash
tmux-ctl send "node" --pane=$PANE
tmux-ctl wait-for ">" --pane=$PANE  # Wait before next command
```

## Installation

```bash
/plugin marketplace add git@github.com:DeevsDeevs/agent-system.git
/plugin install tmux@deevs-agent-system
```

Add `tmux-ctl` to PATH:
```bash
export PATH="$PATH:$HOME/.claude/plugins/tmux@deevs-agent-system/bin"
```

## State Management

All sessions/panes tracked in `.claude/tmux/`:
```
.claude/tmux/
├── sessions.json          # Session metadata, panes
└── sockets/              # Unix sockets (outside tmux mode)
    └── claude-main
```

**Inside tmux**: operates on current session
**Outside tmux**: auto-creates isolated session

## Dependencies

- bash 4.0+
- tmux 2.0+
- jq (JSON output)
- md5sum or md5 (idle detection)

## Architecture

Pure bash implementation combining:
- **pchalasani/tmux-cli** - Clean interface, safety features
- **mitsuhiko/tmux skill** - Process intelligence (Python, debuggers)
- **Custom** - Bash-only, project-scoped state management
