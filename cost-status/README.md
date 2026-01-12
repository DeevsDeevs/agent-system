# cost-status

Status bar showing session cost, monthly cost, total cost, and context window usage.

## Display Format

```
$0.52/$30.00/$150.00 | 38k/200k (19%)
 │     │      │         │    │     │
 │     │      │         │    │     └─ Percentage used
 │     │      │         │    └─ Context window size
 │     │      │         └─ Current context usage
 │     │      └─ Total cost (all time)
 │     └─ Monthly cost
 └─ Current session cost
```

## Installation

After installing the plugin:

```bash
/plugin install cost-status@deevs-agent-system
```

Add to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "bash ~/.claude/plugins/cache/deevs-agent-system/cost-status/<version>/scripts/show-cost.sh"
  }
}
```

To find the exact path after installation:

```bash
find ~/.claude -name "show-cost.sh" -path "*/cost-status/*" 2>/dev/null | head -1
```

## How It Works

- Reads session data via stdin (JSON)
- Tracks costs across sessions in `~/.claude/cost-tracking.json`
- Handles multiple concurrent sessions correctly
- Monthly costs reset automatically each month
- Context usage = input_tokens + cache_creation_tokens + cache_read_tokens

## Requirements

- `jq` - JSON parsing
- `awk` - floating point arithmetic
- Bash 4.0+
