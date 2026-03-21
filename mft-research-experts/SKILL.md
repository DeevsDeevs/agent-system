---
name: mft-research-experts
description: "Run research orchestration for data quality, factor geometry, hypothesis validation, and incident forensics. Use when you need SHIP/KILL/ITERATE decisions with strict validation. Triggers: mft-strategist, data-sentinel, factor-geometer, skeptic, forensic-auditor, research pipeline, hypothesis validation, post-mortem."
---

# MFT Research Experts

Use this skill for end-to-end quantitative research orchestration and validation.

## Role Map

- `mft-strategist` -> `agents/mft-strategist.md`
- `data-sentinel` -> `agents/data-sentinel.md`
- `factor-geometer` -> `agents/factor-geometer.md`
- `skeptic` -> `agents/skeptic.md`
- `forensic-auditor` -> `agents/forensic-auditor.md`

## Workflow

1. Read `README.md` and enforce the sequencing rule: data validation first.
2. If a dataset is involved, spawn `data-sentinel` first and wait for completion before any other role.
3. If the user requested one role explicitly, spawn that role with `agent_type` and targeted scope.
4. If no role was specified, default to `mft-strategist`; let it coordinate and request follow-up role spawns as needed.
5. For full validation flows, ensure `factor-geometer` runs before `skeptic`.
6. For incident or regression investigations, include `forensic-auditor`.
7. Synthesize outputs into a clear SHIP/KILL/ITERATE recommendation with assumptions and confidence.
