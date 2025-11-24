# tmux

Interactive terminal control for REPLs, debuggers, and servers.

## Overview

Control interactive CLI programs in separate tmux panes. High-level API for common tasks, low-level API for advanced control.

## Quick Start

```bash
# Simple execution
tmux-ctl eval "npm test"

# REPL one-shot
tmux-ctl repl python "2+2"  # → 4

# Long-running process
tmux-ctl start "npm run dev" --name=server --wait="Server started"
tmux-ctl logs server
tmux-ctl stop server

# Parallel execution
tmux-ctl start "npm run build" --name=build
tmux-ctl start "npm test" --name=test
tmux-ctl wait build test
tmux-ctl stop build test
```

## High-Level Commands

- `eval <cmd>` - Run and return output (auto-cleanup)
- `repl <type> [cmd]` - Python/Node/psql REPL (one-shot or session)
- `exec <cmd>` - Execute in current context
- `close` - Close current context
- `use <name>` - Switch to named process
- `start/stop/ps/logs/wait` - Named process management

## Low-Level Commands

For advanced control:
- `launch/send/capture/kill` - Pane management
- `wait-for/wait-idle` - Synchronization
- `interrupt/escape` - Control keys

See SKILL.md and reference.md for details.

## Installation

```bash
/plugin marketplace add git@github.com:DeevsDeevs/agent-system.git
/plugin install tmux@deevs-agent-system
```

Add to PATH:
```bash
export PATH="$PATH:$HOME/.claude/plugins/tmux@deevs-agent-system/bin"
```

## State Management

State stored in `.claude/tmux/`:
- `sessions.json` - Session/pane tracking
- `context.json` - Current context
- `named_panes.json` - Named processes
- `sockets/` - tmux sockets (outside tmux mode)

**Inside tmux**: operates on current session
**Outside tmux**: auto-creates isolated session

## Dependencies

- bash 4.0+
- tmux 2.0+
- jq (JSON)
- md5sum or md5 (idle detection)
