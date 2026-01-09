---
name: arxiv-search
description: Search arXiv preprint repository for research papers in physics, mathematics, computer science, quantitative biology, finance, and statistics. Use when finding academic papers, preprints, ML research, scientific publications. Triggers: arxiv, preprint, research paper, academic paper, scientific literature.
---

# arxiv-search: Academic Paper Search

Search the arXiv preprint repository for scholarly articles across physics, mathematics, computer science, quantitative biology, quantitative finance, statistics, and economics.

## Quick Reference

```bash
# Basic search
uv run ${CLAUDE_PLUGIN_ROOT}/arxiv_search.py "transformer attention mechanism"

# Limit results
uv run ${CLAUDE_PLUGIN_ROOT}/arxiv_search.py "protein folding" --max-papers 5

# Fallback if uv unavailable
python3 ${CLAUDE_PLUGIN_ROOT}/arxiv_search.py "neural networks" --max-papers 10
```

## When to Use

- Finding recent research and preprints before journal publication
- Searching for ML/AI papers (cs.LG, cs.AI, cs.CV, stat.ML)
- Looking up mathematical or statistical methods
- Finding quantitative biology and bioinformatics papers (q-bio)
- Accessing physics and mathematics literature

## Arguments

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `query` | Yes | - | Search query string |
| `--max-papers` | No | 10 | Maximum papers to retrieve |

## Output Format

Returns formatted results with:
- **Title**: Paper title
- **Summary**: Abstract text

Papers are separated by blank lines for readability.

## Dependency Installation

This skill requires the `arxiv` Python package:

```bash
# Preferred: using uv
uv pip install arxiv

# Alternative: system pip
pip install arxiv
```

## Examples

**Machine learning research:**
```bash
uv run ${CLAUDE_PLUGIN_ROOT}/arxiv_search.py "large language models reasoning" --max-papers 5
```

**Physics papers:**
```bash
uv run ${CLAUDE_PLUGIN_ROOT}/arxiv_search.py "quantum computing error correction"
```

**Statistics and methods:**
```bash
uv run ${CLAUDE_PLUGIN_ROOT}/arxiv_search.py "bayesian inference neural networks"
```

## arXiv Categories

Common categories for reference:
- **cs.LG** - Machine Learning
- **cs.AI** - Artificial Intelligence
- **cs.CV** - Computer Vision
- **stat.ML** - Statistics: Machine Learning
- **q-bio** - Quantitative Biology
- **math** - Mathematics
- **physics** - Physics
- **q-fin** - Quantitative Finance

## Notes

- Papers are preprints and may not be peer-reviewed
- Results sorted by relevance to query
- No API key required - free access
- Best for computational and theoretical work
