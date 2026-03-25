# Chain System

Multi-session workflow chains for maintaining linked context across conversations.

## Overview

Manage conversation "chains" - structured context across multiple sessions. Each chain link captures detailed technical state, making it easy to pause and resume complex projects without losing context.

**vs `/compact`**: `/compact` reduces context in single sessions; chains preserve detailed history across sessions for multi-session projects.

## Commands

### `/chain-link [chain-name]`
Saves current conversation chunk as a chain link, then benchmarks it.

**Captures**: User requests, code changes (files/lines), unresolved bugs with solutions attempted, pending tasks, next step.

**Saves to**: `.claude/chains/[chain-name]/[timestamp]-[slug].md`

**Benchmark**: After saving, spawns a clean agent with no prior context that reads ONLY the chain link and answers 10 verification questions. Scores 0-100 per question. If average < 85, the link is iteratively improved (up to 3 attempts) by filling gaps the clean agent couldn't answer. Shows final score breakdown.

### `/chain-load [chain-name]`
Loads most recent chain link to continue work.

**Shows**: Summary, next step, list of 5 most recent links, option to load additional links.

### `/chain-list`
Lists all available chains with link count and most recent work.

## Workflow

1. Work on feature → `/chain-link my-feature` when done
2. New session → `/chain-load my-feature` to continue
3. Multiple chains → `/chain-list` to see all ongoing work

## Installation

```bash
/plugin marketplace add git@github.com:DeevsDeevs/agent-system.git
/plugin install chain-system@deevs-agent-system
```

### Verification Hook

Add the following to your project's `.claude/settings.json` to enable automatic chain link verification:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "bash chain-system/hooks/verify-chain-link.sh"
          }
        ]
      }
    ]
  }
}
```

When enabled, every chain link write is verified by an isolated CLI process. If the benchmark score is below 85/100, the write is blocked and gaps are fed back to the agent for correction.

## File Structure

```
.claude/chains/
├── my-feature/
│   └── 2025-11-24-0145-implement-auth.md
└── bug-fixes/
    └── 2025-11-20-1000-investigate-timeout.md
```
