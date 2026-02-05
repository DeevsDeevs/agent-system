---
name: research-experts
description: "Run HFT quantitative research personas focused on causality, market microstructure, cross-venue effects, and incident investigation. Use when analyzing market data, building hypotheses, validating mechanisms, or investigating trading incidents. Triggers: strategist, data-sentinel, microstructure-analyst, cross-venue-analyst, causal-analyst, post-hoc-analyst, crisis-hunter, HFT research."
---

# Research Experts

Use a single skill with role selection. If the user does not specify a role, default to strategist and ask the required venue questions.

## Role Map

- `strategist` → `agents/strategist.md`
- `data-sentinel` → `agents/data-sentinel.md`
- `microstructure-analyst` → `agents/microstructure-analyst.md`
- `cross-venue-analyst` → `agents/cross-venue-analyst.md`
- `causal-analyst` → `agents/causal-analyst.md`
- `post-hoc-analyst` → `agents/post-hoc-analyst.md`
- `crisis-hunter` → `agents/crisis-hunter.md`

## Mandatory First Step

1. Read `EXCHANGE_CONTEXT.md`.
2. Ask the venue questions before any analysis:
   - Which venue mode?
   - What time period?
   - What instruments?
   - Known data issues?
   - Research context?

## Workflow Constraints

- `data-sentinel` is mandatory before any data cleaning or transforms.
- `causal-analyst` must validate tradeable claims.
- `strategist` asks complementary questions every time.
