---
name: chain-system
description: "Create, list, and load multi-session chain links that capture work context for later continuation. Use when you want to save current progress, resume a project from a prior session, or inspect chain history. Triggers: chain link, chain load, chain list, save context, resume work, continue later, session handoff."
---

# Chain System

## Overview

Capture durable, structured summaries of work so a later session can resume without re-discovery. Provide three subcommands under one skill: `link`, `load`, and `list`.

## Usage

Invoke with a subcommand:

```text
$chain-system link <chain-name>
$chain-system load <chain-name>
$chain-system list
```

If the chain name is missing for `link` or `load`, ask the user for it.

## Chain Root

Default to `.claude/chains` to remain compatible with the existing Claude chain-system plugin. If the user explicitly wants Codex-only storage, switch to `.codex/chains` and confirm.

## Subcommands

### `link`

Create a new chain link summarizing the current work.

Steps:
1. Build a concise but complete summary using this structure:
   - Primary Request and Intent
   - Key Technical Concepts
   - Work Completed
   - Decisions and Rationale
   - Files and Code Changes (Created/Modified/Read)
   - Unresolved Issues and Blockers (only if any)
   - Pending Tasks
   - Current Work
   - Next Step
2. Create a slug (kebab-case) and a human readable title.
3. Create the directory: `mkdir -p .claude/chains/<chain-name>`.
4. Generate timestamp in local time: `date '+%Y-%m-%d-%H%M'`.
5. Write the summary to:
   `.claude/chains/<chain-name>/<timestamp>-<slug>.md`
6. Write only the summary (no analysis), then tell the user the file path and how to load it.

Use the same file format each time so `load` can extract summary and next step reliably.

### `load`

Load the most recent chain link for a named chain.

Steps:
1. Find the most recent link:
   - `ls .claude/chains/<chain-name>/*.md 2>/dev/null | sort -r | head -1`
2. If none, tell the user the chain does not exist and suggest `list`.
3. Read the file fully and internalize it as working context.
4. List the 5 most recent links:
   - `ls .claude/chains/<chain-name>/*.md 2>/dev/null | sort -r | head -5`
5. Detect insufficiency and ask questions if needed:
   - Missing context referenced by the link
   - Ambiguous "Next Step"
   - Stale link (>7 days old)
6. Show the user: chain name, most recent link filename, short summary, next step, and the 5 most recent links.
7. If any insufficiency flags exist, stop and clarify before proceeding.

### `list`

List all chains with counts and most recent link.

Steps:
1. Check for chains:
   - `ls -d .claude/chains/*/ 2>/dev/null`
2. For each chain, show:
   - chain name (directory)
   - link count (`ls .claude/chains/<chain-name>/*.md 2>/dev/null | wc -l`)
   - most recent link filename (`ls .claude/chains/<chain-name>/*.md 2>/dev/null | sort -r | head -1`)
3. If no chains exist, suggest `link` to start one.
