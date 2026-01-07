---
name: quarto
description: Create, edit, and fix Quarto qmd files for technical documentation. Use when working with .qmd files, Quarto rendering, Python code cells, YAML frontmatter issues, or publishing to HTML/Confluence. Triggers: qmd files, quarto render, quarto preview, code-fold, execute options, Confluence macros.
---

# quarto: Technical Documentation

Create and manage Quarto qmd files for HTML and Confluence output with Python code execution.

## Quick Reference

| Command | Description |
|---------|-------------|
| `quarto render file.qmd` | Render to default format |
| `quarto render file.qmd --to html` | Render to HTML |
| `quarto render file.qmd --to confluence-html` | Render for Confluence preview |
| `quarto preview file.qmd` | Live preview with auto-reload |
| `quarto publish confluence` | Publish to Confluence |
| `quarto check` | Verify Quarto installation |

## qmd File Structure

```markdown
---
title: "Document Title"
format: html
jupyter: python3
execute:
  echo: true
  warning: false
---

# Section Header

Regular markdown text with **bold** and *italic*.

```{python}
#| label: fig-example
#| fig-cap: "Example visualization"
import polars as pl
import matplotlib.pyplot as plt

df = pl.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
plt.plot(df["x"], df["y"])
plt.show()
```

## Another Section

More content here.
```

## YAML Frontmatter Essentials

```yaml
---
title: "Document Title"
format: html                  # or confluence-html
jupyter: python3
execute:
  echo: true                  # Show code
  warning: false              # Hide warnings
  cache: true                 # Cache results
---
```

See [references/yaml-options.md](references/yaml-options.md) for complete options.

## Python Code Cell Options

Use `#|` comments at the start of code cells:

| Option | Values | Description |
|--------|--------|-------------|
| `label` | string | Cell identifier for cross-refs |
| `fig-cap` | string | Figure caption |
| `echo` | true/false/fenced | Show source code |
| `eval` | true/false | Execute code |
| `output` | true/false/asis | Include output |
| `warning` | true/false | Show warnings |
| `code-fold` | true/false/show | Collapsible code |
| `code-summary` | string | Fold button text |

Example:

```python
#| label: tbl-summary
#| tbl-cap: "Data Summary"
#| echo: false
#| warning: false
df.describe()
```

## Confluence Publishing

### Setup

1. Add to YAML frontmatter:
   ```yaml
   format: confluence-html
   ```

2. Or create `_quarto.yml` for projects:
   ```yaml
   project:
     type: confluence
   ```

3. Publish:
   ```bash
   quarto publish confluence document.qmd
   ```

### Raw Confluence Blocks

Insert Confluence-specific markup:

```markdown
```{=confluence}
<ac:structured-macro ac:name="status">
  <ac:parameter ac:name="colour">Green</ac:parameter>
  <ac:parameter ac:name="title">DONE</ac:parameter>
</ac:structured-macro>
```
```

See [references/confluence-macros.md](references/confluence-macros.md) for all macros.

## Detailed References

### [references/yaml-options.md](references/yaml-options.md)
**When:** Need detailed YAML configuration for HTML format, execute options, TOC, theming, or code display settings.

### [references/confluence-macros.md](references/confluence-macros.md)
**When:** Adding Confluence-specific macros like status badges, task lists, info/warning panels, or collapsible sections.

## Common Issues

**Kernel not found:**
```bash
quarto check                  # Verify installation
python -m ipykernel install --user --name python3
```

**YAML parse error:**
- Check indentation (use spaces, not tabs)
- Ensure colons have space after: `key: value`
- Quote strings with special characters

**Code not executing:**
- Check `execute: eval: true` in frontmatter
- Verify kernel is specified: `jupyter: python3`
- Run `quarto preview` to see errors

**Confluence publish fails:**
- Verify credentials: `quarto publish accounts`
- Check format is `confluence-html`
- Ensure you have page edit permissions
