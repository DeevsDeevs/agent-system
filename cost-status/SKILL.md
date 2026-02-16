---
name: cost-status
description: "Configure the Claude Code cost/status line plugin that shows session, monthly, total cost, and context usage. Use when a user wants cost tracking, status line setup, or context usage display. Triggers: cost status, status line, show cost, context usage, Claude cost tracking."
---

# Cost Status

This skill configures the Claude Code status-line plugin that reads session JSON from stdin and tracks costs in `~/.claude/cost-tracking.json`.

## Workflow

1. Install the plugin if needed.
2. Add the status line command to `~/.claude/settings.json` as documented in `cost-status/README.md`.
3. If the user needs the exact script path, use the `find` command in the README.
4. Confirm dependencies: `jq`, `awk`, Bash 4+.
