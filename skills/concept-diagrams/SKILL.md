---
name: concept-diagrams
description: "Source-grounded diagrams: codebase maps, flows, sequences, state machines, architecture views. Compact Mermaid by default."
---

# Concept Diagrams

Make a system or idea easier to reason about with the smallest useful diagram. Visual reasoning, not decorative graphics.

Default to **Mermaid in Markdown** (reviewable, diffable). Use **standalone HTML/SVG** only when the user asks for a polished/printable file or geometry Mermaid cannot express.

Use when asked to diagram, visualize, map, or explain visually: architecture/boundaries/dependencies, request/data/control flow, sequence/protocol/lifecycle, state machines and failure paths, concept maps, docs/wiki diagrams grounded in code. Not for decorative graphics, production UI comps, animation, unresearched systems, or one giant "everything diagram". If diagramming code, inspect relevant files first — orient or use a scoped explore subagent for broad unfamiliar codebases.

## Diagram brief

Answer internally before drawing (ask the user only if the answer materially changes the diagram):

1. **Question:** what should the viewer understand after 20 seconds?
2. **Audience:** maintainer, reviewer, planner, user, or newcomer?
3. **View:** structure, runtime flow, sequence, state, concept, or comparison?
4. **Evidence:** what files/docs/sources back the nodes and edges?
5. **Artifact:** inline answer, Markdown doc, wiki page, or standalone HTML/SVG?

A diagram has a thesis. Do not draw boxes to restate prose.

## Choose the view

Source/architecture map (ownership, modules, trust boundaries) · runtime/data flow (what moves where) · sequence (order between actors) · state/lifecycle (statuses, transitions, failure modes) · concept map (labeled relationships) · comparison — use a table when classification beats arrows. For complex systems, ship a pack of 2–4 small diagrams instead of one monster view.

## Codebase diagram protocol

1. Read obvious entrypoints first: README, package config, route files, command registration, module roots, extension indexes.
2. Trace only the relevant path; distinguish facts from inferred relationships.
3. List inspected file paths in node notes or a `Sources inspected` list.
4. For docs or wiki diagrams, check the existing pages and their conventions first.

## Mermaid guardrails

Stable ASCII IDs (`WikiContext`, not `wiki-context()`) with human labels in brackets (`WikiContext[wiki context action]`); short labels; no raw `<`, `>`, `|`, `{`, `}` in labels; short subgraph names; edge labels only when they add meaning; explain dashed vs solid if both appear.

Readability budget (split by view if exceeded): 5–9 primary nodes, 1–3 subgraphs, 0–2 edge styles, 3–5 sequence participants, 5–8 states, 4–6 words per label.

## Standalone HTML/SVG mode

Self-contained HTML from `templates/standalone-svg.html` in this skill's folder: inline SVG only, no CDN/remote assets, light/dark CSS variables, flat minimal style, title/subtitle/diagram/notes, written to the user path or `docs/diagrams/<slug>.html`. No preview server unless asked; if one is needed, run it in hc (`hc run --bg`).

## Quality bar

The diagram answers one clear question; reading direction is obvious; every node/edge is backed by source, user input, or explicit assumption; boundaries mean something real; no unlabeled arrows between vague boxes; codebase diagrams list inspected paths; Mermaid syntax renders.

Reject: prose restated as bubbles, architecture invented from filenames, arrows meaning several unrelated things, false certainty on inferred relationships, decorative colors implying fake categories, missing source/assumption notes.
