---
name: bug-hunters
description: "Run systematic bug hunting with spec reconstruction, adversarial validation, and confidence scoring. Use when you want to hunt bugs (not fix them), validate correctness, or run logic-first/code-first investigations. Triggers: bug hunt, spec reconstruction, logic-first, code-first, orchestrator, logic-hunter, cpp-hunter, python-hunter."
---

# Bug Hunters

Use a single skill with role selection. If the user specifies a hunter, use that role; otherwise start with the orchestrator and ask which mode applies.

## Role Map

- `orchestrator` → `bug-hunters/agents/orchestrator.md`
- `logic-hunter` → `bug-hunters/agents/logic-hunter.md`
- `cpp-hunter` → `bug-hunters/agents/cpp-hunter.md`
- `python-hunter` → `bug-hunters/agents/python-hunter.md`

## Workflow

1. Read `bug-hunters/README.md` and follow the “hunt, don’t fix” rule.
2. Choose mode:
   - Logic-first when the problem is algorithm/spec correctness.
   - Code-first when the problem is language-specific failures or UB.
3. Use adversarial validation and only report MEDIUM+ confidence findings.
4. Present a bug report, not remediation.
