# Detailed Chain Link Rubric

Use this for important handoffs, forks, or multi-agent work. The saved link should be concise enough to reload, but complete enough to avoid rediscovery.

## Process

Before saving, reason through the conversation chronologically:

- user requests and intent changes
- approach taken and alternatives rejected
- key technical decisions and why
- files created, modified, read, or intentionally left alone
- exact command/test outcomes
- bugs, blockers, failed attempts, and current status
- running work: subagents and workflows (their ids), hc terminals (their addresses)
- what the next session should do first

Do not save private analysis. Save only the final markdown summary.

## Required saved structure

```markdown
# Short Human Title

## 1. Primary Request and Intent
[What the user asked for, including later refinements.]

## 2. Key Technical Concepts
- [Framework/API/tooling/pattern]

## 3. Work Completed
- [Completed item] — status: [tested/working/manual]

## 4. Decisions and Rationale
- **Decision**: [What was chosen]
  - **Rationale**: [Why, including rejected alternatives]

## 5. Files and Code Changes

### Created: path/to/file
- Purpose: [why]
- Key contents/exports: [brief]

### Modified: path/to/file
- Changes: [what changed]
- Important functions/types: [names]

### Read: path/to/file
- Why: [reason]

## 6. Unresolved Issues and Blockers
[Skip if none. Include exact errors, symptoms, attempted fixes, and current status.]

## 7. Pending Tasks
- [Explicit incomplete work]

## 8. Current Work
[What is in progress now: files, branch, command, subagent/process IDs.]

## 9. Next Step
[One immediate action aligned with the user request.]
```

## Fork-specific additions

For branch links, include:

- source branch/link and why the fork exists
- scope of this branch
- what should merge back into parent/main
- what should stay branch-local

## Subagent-specific additions

When chains are used to coordinate subagents, include:

- agent, workflow run and hc terminal ids
- each subagent's role and final recommendation
- which recommendations were accepted/rejected
- what context was passed to subagents
- whether subagents had write access

## Anti-bloat rules

- Prefer exact paths and IDs over prose.
- Include snippets only when needed to resume safely.
- Do not include full files unless the content is small and central.
- Do not narrate obvious tool calls.
