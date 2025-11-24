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

## Final Step

Create directory and save file:
1. Create directory: `mkdir -p .claude/chains/[chain-name]` (substitute actual chain name)
2. Generate timestamp using local time: `date '+%Y-%m-%d-%H%M'` (e.g., `2025-11-24-0230`)
3. Write to: `.claude/chains/[chain-name]/[timestamp]-[slug].md`
4. Save only the content inside `<plan>` tags to the file
5. Inform user: file path and how to load with `/chain-load [chain-name]`
