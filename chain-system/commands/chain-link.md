Creates a detailed summary of the conversation chunk for continuing work in future sessions.

Chain name: `$ARGUMENTS`

If no chain name provided, ask the user for one.

## Goal

Create a thorough summary capturing technical details, code patterns, architectural decisions, unresolved bugs, and solutions attempted. This enables seamless continuation without losing context.

## Process

Before your final summary, wrap analysis in `<analysis>` tags to organize thoughts. Chronologically analyze each message, identifying:
- User's explicit requests and intents
- Your approach to addressing requests
- Key decisions, technical concepts, code patterns
- Specific details: file names, full code snippets, function signatures, line numbers
- Bugs encountered and solutions attempted (successful and failed)

Your summary should include:

1. **Primary Request and Intent**: Capture all user's explicit requests in detail
2. **Key Technical Concepts**: Technologies, frameworks, and patterns discussed
3. **Work Completed**: What was successfully finished and is working (e.g., "Auth handler fully implemented and tested")
4. **Decisions and Rationale**: Key decisions made (approach A over B) and why
5. **Files and Code Changes**:
   - **Created**: New files with full code
   - **Modified**: Changed files with before/after snippets and line numbers
   - **Read**: Files examined for context (brief note on why)
6. **Unresolved Issues and Blockers**: ONLY unresolved problems with:
   - Complete error messages and stack traces
   - Symptoms and when discovered
   - All solutions attempted (what worked, what didn't, why)
   - Current status
7. **Pending Tasks**: Explicitly requested but incomplete tasks
8. **Current Work**: What was in progress when this link was created (file names, line numbers, code snippets)
9. **Next Step**: Immediate next action, directly aligned with user's requests

Create a slug (e.g., `implement-auth-handler`) and readable summary (e.g., "Implement Auth Handler")

## Output Structure

```markdown
# Readable Summary

<analysis>
[Your thorough chronological analysis for organizing thoughts - not saved to file]
</analysis>

<plan>
# Chain Link Summary

## 1. Primary Request and Intent
[Detailed description of all user requests]

## 2. Key Technical Concepts
- [Technology/framework/pattern 1]
- [Technology/framework/pattern 2]

## 3. Work Completed
- [Completed item 1] - status: working/tested
- [Completed item 2] - status: working/tested

## 4. Decisions and Rationale
- **Decision**: [What was chosen]
  - **Rationale**: [Why this approach over alternatives]

## 5. Files and Code Changes

### Created: [Full/Path/To/NewFile.ext]
- **Purpose**: [Why created]
- **Code**:
```language
[Complete file content]
```

### Modified: [Full/Path/To/ChangedFile.ext]
- **Changes**: [Description]
- **Lines**: [Line numbers]
- **Code**:
```language
[Before/after snippets]
```

### Read: [Full/Path/To/ReadFile.ext]
- **Why**: [Reason for reading]

## 6. Unresolved Issues and Blockers

### [Issue Title]
- **Error**:
```
[Complete error message/stack trace]
```
- **Symptoms**: [How it manifests]
- **Discovered**: [When/context]
- **Attempts**:
  - [Approach 1]: [Result and why failed]
  - [Approach 2]: [Result and why failed]
- **Status**: [Blocked/Investigating/Partial workaround]

[Skip if no unresolved issues]

## 7. Pending Tasks
- [Task 1]
- [Task 2]

## 8. Current Work
[What was in progress, with files and code]

## 9. Next Step
[Immediate next action]
</plan>
```

## Save Step

Create directory and save file:
1. Create directory: `mkdir -p .claude/chains/[chain-name]` (substitute actual chain name)
2. Generate timestamp using local time: `date '+%Y-%m-%d-%H%M'` (e.g., `2025-11-24-0230`)
3. Write to: `.claude/chains/[chain-name]/[timestamp]-[slug].md`
4. Save only the content inside `<plan>` tags to the file

## Verification (Automatic via Hook)

Verification is **not a manual step** — it is enforced by a `PostToolUse` hook on `Write|Edit`. When you save the chain link file to `.claude/chains/**/*.md`, the hook automatically:

1. Detects the file is a chain link
2. Runs `chain-system/scripts/chain-verify.sh` — spawns an **isolated CLI process** (`claude --print --bare`) with zero shared context
3. The isolated process reads ONLY the chain link content and answers 10 verification questions
4. Scores each answer 0-100

**If score >= 85**: Hook exits 0, write succeeds. Benchmark score is shown.

**If score < 85**: Hook exits 2, **write is blocked**. The gaps are fed back to you as feedback. You must:
- Read the gap analysis in the hook feedback
- Re-examine the conversation for the missing information
- Rewrite the chain link addressing the specific gaps
- Save again (which re-triggers the hook automatically)

This loop continues until the chain link passes or you've addressed all available information from the conversation.

### Setup

The hook must be registered in `.claude/settings.json` (see Installation section in README). The hook script lives at `chain-system/hooks/verify-chain-link.sh` and calls `chain-system/scripts/chain-verify.sh`.

### Why a hook and not instructions?

Subagents (Agent tool) share the parent conversation context — they already know the answers and would pass every time, making verification meaningless. Instructions in markdown can be skipped or forgotten. The hook is a **hard gate**: the file literally cannot be saved unless the isolated verifier confirms a fresh session could resume from it.
