Loads the most recent chain link to continue work from a previous session.

Chain name: `$ARGUMENTS`

If no chain name provided, ask the user which chain to load (suggest using `/chain-list`).

## Steps

1. Check chain exists and find most recent link (by timestamp in filename):
```bash
ls .claude/chains/[chain-name]/*.md 2>/dev/null | sort -r | head -1
```
If no result, inform user chain doesn't exist and suggest `/chain-list`.

2. Read the file fully - this is your working context

3. List the 5 most recent links:
```bash
ls .claude/chains/[chain-name]/*.md 2>/dev/null | sort -r | head -5
```

4. **Detect Insufficiency** - check for gaps requiring user input:
   - **Missing Context**: Link references files/decisions not captured. Ask: "Link references [X] - verify current state?"
   - **Ambiguous Next-Steps**: "Next Step" is vague. Ask: "Next step unclear: [quote]. What specifically?"
   - **Stale Data**: Link older than 7 days. Ask: "Link [N] days old. Project diverged?"

   If ANY gap detected: STOP. Interview user. No interpolation or assumptions.

5. Show the user:
   - Chain name and most recent link filename
   - Brief summary (from Readable Summary if present)
   - Next Step from loaded file
   - Insufficiency flags with specific questions (if any)
   - List of 5 most recent links

6. If gaps flagged, clarify before proceeding. Otherwise ask about loading additional links

**Note**: Fully internalize the loaded content - it's your working context. Only show the user a brief summary.
