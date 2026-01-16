---
name: arxiv-search
description: "Search arXiv preprint repository for research papers in physics, mathematics, computer science, quantitative biology, finance, and statistics. Use when finding academic papers, preprints, ML research, scientific publications. Triggers: arxiv, preprint, research paper, academic paper, scientific literature."
---

# arxiv-search: Academic Paper Search

Search the arXiv preprint repository for scholarly articles across physics, mathematics, computer science, quantitative biology, quantitative finance, statistics, and economics.

## Quick Reference

```bash
# Basic search (auto-selects best implementation)
${CLAUDE_PLUGIN_ROOT}/arxiv_search "transformer attention mechanism"

# Limit results
${CLAUDE_PLUGIN_ROOT}/arxiv_search "protein folding" --max-papers 5
```

## Implementation

The skill auto-detects the best available implementation:

1. **Python** (preferred): If `uv` + `arxiv` package or `python3` + `arxiv` are available
2. **Bash** (fallback): Uses `curl` + `awk` - works everywhere, no dependencies

To enable Python implementation:
```bash
uv pip install arxiv
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

## Examples

**Machine learning research:**
```bash
${CLAUDE_PLUGIN_ROOT}/arxiv_search "large language models reasoning" --max-papers 5
```

**Physics papers:**
```bash
${CLAUDE_PLUGIN_ROOT}/arxiv_search "quantum computing error correction"
```

**Statistics and methods:**
```bash
${CLAUDE_PLUGIN_ROOT}/arxiv_search "bayesian inference neural networks"
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
- Python implementation is more robust for edge cases
- Bash fallback works on any Unix system with curl
