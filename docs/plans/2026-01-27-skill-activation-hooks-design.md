# Skill Activation Hooks - Design Document

**Date:** 2026-01-27
**Status:** Approved

## Overview

Two prompt-based hooks to improve Claude's skill awareness:

1. **UserPromptSubmit** - Analyzes prompts before Claude sees them, injects skill activation reminders
2. **Stop** - Advisory self-check reminders based on edited files (non-blocking)

## Decisions

- **Location:** New plugin in this marketplace (`skill-activation-hooks/`)
- **Config approach:** Minimal framework + examples (polars-expertise, arxiv-search)
- **Hook type:** Prompt-based for both hooks (native, no external API)
- **Stop behavior:** Advisory only, never blocks

## Plugin Structure

```
skill-activation-hooks/
├── plugin.json
├── hooks/
│   └── hooks.json
├── config/
│   └── skill-rules.json
└── README.md
```

## Configuration Schema: skill-rules.json

```json
{
  "$schema": "./skill-rules-schema.json",
  "version": "1.0",

  "skills": {
    "polars-expertise": {
      "description": "Polars DataFrame library for Python/Rust - expressions, lazy evaluation, performance",
      "type": "domain",
      "enforcement": "suggest",
      "priority": "high",

      "promptTriggers": {
        "keywords": [
          "polars", "dataframe", "lazyframe", "parquet",
          "scan_parquet", "group_by_dynamic", "rolling_mean",
          "asof join", "OHLCV", "window function"
        ],
        "intentPatterns": [
          "(convert|migrate).*?(pandas|pyspark|kdb).*?polars",
          "(lazy|eager).*?(evaluation|execution)",
          "(read|write|scan).*?parquet",
          "(rolling|window).*?(mean|std|sum)",
          "time series.*?(resample|aggregate)"
        ]
      },

      "fileTriggers": {
        "pathPatterns": ["**/*.py", "**/*.rs"],
        "contentPatterns": [
          "import polars",
          "use polars::",
          "pl\\.scan_",
          "pl\\.read_",
          "LazyFrame",
          "\\.collect\\(\\)"
        ]
      },

      "stopChecks": {
        "patterns": ["map_elements", "iter_rows", "apply\\(", "pandas"],
        "reminders": [
          "Using native expressions instead of map_elements?",
          "Early projection (select columns before filter)?",
          "Lazy evaluation for large data?"
        ]
      }
    },

    "arxiv-search": {
      "description": "Search arXiv for academic papers and preprints",
      "type": "research",
      "enforcement": "suggest",
      "priority": "medium",

      "promptTriggers": {
        "keywords": [
          "arxiv", "preprint", "research paper", "academic paper",
          "scientific literature", "paper search", "find papers",
          "ML research", "recent research"
        ],
        "intentPatterns": [
          "(find|search|look up).*?(paper|research|preprint)",
          "(latest|recent).*?(research|paper|work).*?(on|about)",
          "what does the (literature|research) say",
          "(state of the art|SOTA).*?(in|for)"
        ]
      },

      "fileTriggers": {
        "pathPatterns": [],
        "contentPatterns": []
      },

      "stopChecks": {
        "patterns": [],
        "reminders": []
      }
    }
  }
}
```

## Hook Configuration: hooks.json

```json
{
  "description": "Skill activation hooks - prompt analysis and self-check reminders",
  "hooks": {
    "UserPromptSubmit": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "prompt",
            "prompt": "You are a skill activation analyzer. Read the skill rules from the project's skill-rules.json and analyze the user's prompt.\n\nUser prompt: $USER_PROMPT\n\nFor each skill in skill-rules.json, check:\n1. Does the prompt contain any keywords from promptTriggers.keywords?\n2. Does the prompt match any regex in promptTriggers.intentPatterns?\n\nIf ANY skill matches, return a systemMessage in this format:\n\n{\"systemMessage\": \"SKILL ACTIVATION CHECK\\n\\nRelevant skills detected:\\n- [skill-name]: [brief reason]\\n\\nConsider invoking these skills before responding.\"}\n\nIf NO skills match, return: {\"systemMessage\": \"\"}\n\nBe concise. Only list genuinely relevant skills.",
            "timeout": 30
          }
        ]
      }
    ],

    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "prompt",
            "prompt": "You are a self-check reminder. Analyze what was done in this session.\n\nReview the conversation and any files that were edited. For each skill in skill-rules.json that has stopChecks defined:\n\n1. Check if edited files match the skill's fileTriggers (pathPatterns or contentPatterns)\n2. If they match, check if the file content contains any stopChecks.patterns\n3. If patterns found, include the corresponding reminders\n\nReturn format:\n{\"decision\": \"approve\", \"systemMessage\": \"Self-check reminders:\\n- [reminder 1]\\n- [reminder 2]\"}\n\nIf no relevant patterns found, return:\n{\"decision\": \"approve\", \"systemMessage\": \"\"}\n\nAlways approve (advisory only). Keep reminders brief and actionable.",
            "timeout": 30
          }
        ]
      }
    ],

    "SessionStart": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "cat ${CLAUDE_PLUGIN_ROOT}/config/skill-rules.json 2>/dev/null || echo '{}'",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

## Plugin Manifest: plugin.json

```json
{
  "name": "skill-activation-hooks",
  "version": "1.0.0",
  "description": "Prompt-based hooks for skill activation reminders and self-check",
  "author": "Deevs",
  "hooks": ["./hooks/"]
}
```

## Implementation Steps

1. Create `skill-activation-hooks/` directory
2. Create `plugin.json`
3. Create `hooks/hooks.json`
4. Create `config/skill-rules.json` with examples
5. Create `README.md`
6. Register in `marketplace.json`
7. Test with `claude --debug`
