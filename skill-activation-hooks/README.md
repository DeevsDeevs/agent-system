# skill-activation-hooks

Automatic skill activation reminders and self-check for Claude Code.

## How It Works

Two prompt-based hooks that improve skill awareness:

1. **UserPromptSubmit** - Analyzes your prompt before Claude sees it, injects skill reminders based on keywords and intent patterns

2. **Stop** - When Claude finishes, checks edited files for patterns that warrant self-check reminders (advisory, non-blocking)

3. **SessionStart** - Loads skill-rules.json into context for the prompt hooks to reference

## Configuration

Edit `config/skill-rules.json` to add your own skills. Each skill can define:

### promptTriggers

Activates when user submits a prompt:

- `keywords` - Exact words/phrases to match (case-insensitive)
- `intentPatterns` - Regex patterns to catch user intent

### fileTriggers

Activates based on files being edited:

- `pathPatterns` - Glob patterns for file paths
- `contentPatterns` - Regex patterns for file content

### stopChecks

What to look for when Claude finishes:

- `patterns` - Regex patterns to search in edited files
- `reminders` - Human-readable reminders shown if patterns found

## Example Rule

```json
{
  "my-skill": {
    "description": "Brief description",
    "type": "domain",
    "enforcement": "suggest",
    "priority": "high",

    "promptTriggers": {
      "keywords": ["keyword1", "keyword2"],
      "intentPatterns": ["(create|add).*?thing"]
    },

    "fileTriggers": {
      "pathPatterns": ["src/**/*.ts"],
      "contentPatterns": ["import.*MyLib"]
    },

    "stopChecks": {
      "patterns": ["antiPattern", "badPractice"],
      "reminders": ["Did you avoid the anti-pattern?"]
    }
  }
}
```

## Installation

This plugin is part of the deevs-agent-system marketplace. Install via:

```bash
claude plugins add deevs-agent-system/skill-activation-hooks
```

Or add to your local plugins directory.

## Testing

Run Claude Code with debug mode to see hook execution:

```bash
claude --debug
```

## Notes

- All hooks are advisory - they never block Claude from completing
- Prompt hooks use the session's model (no external API calls)
- Skill rules are loaded once at session start via SessionStart hook
