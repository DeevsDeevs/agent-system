# YAML Frontmatter Reference

Complete reference for qmd YAML frontmatter options.

## Document Metadata

```yaml
title: "Document Title"
subtitle: "Optional subtitle"
author: "Author Name"
date: "2025-01-07"
date-format: "long"           # short, medium, long, full, or custom
abstract: "Brief summary"
keywords: [quarto, python]
```

## Format Options

### HTML Format

```yaml
format:
  html:
    theme: default            # cosmo, flatly, darkly, etc.
    toc: true
    toc-depth: 3
    toc-location: left        # left, right, body
    toc-title: "Contents"
    number-sections: true
    code-fold: true           # Collapsible code blocks
    code-summary: "Show code"
    code-line-numbers: true
    code-copy: true
    code-overflow: scroll     # scroll, wrap
    anchor-sections: true
    smooth-scroll: true
```

### Confluence Format

```yaml
format: confluence-html
```

For Confluence projects, use `_quarto.yml`:

```yaml
project:
  type: confluence
```

## Execute Options

Control code execution behavior:

```yaml
execute:
  eval: true          # Execute code (true/false)
  echo: true          # Show code in output (true/false/fenced)
  output: true        # Include results (true/false/asis)
  warning: false      # Show warnings
  error: false        # Continue on error
  include: true       # Include cell in output
  cache: false        # Cache results (true/false/refresh)
  freeze: auto        # Never re-execute (true/false/auto)
  daemon: false       # Keep kernel running
```

### Per-Cell Override

Override in individual cells:

```python
#| eval: false
#| echo: true
```

## Jupyter/Kernel Options

```yaml
jupyter: python3              # Kernel name
# Or with options:
jupyter:
  kernel: python3
  kernelspec:
    display_name: Python 3
    language: python
    name: python3
```

## Code Display Options

```yaml
code-fold: true               # Collapse code by default
code-fold: show               # Show code, allow collapse
code-summary: "Click to show" # Collapse button text
code-tools: true              # Add code tools menu
code-line-numbers: true       # Line numbers
code-copy: true               # Copy button
code-overflow: scroll         # scroll or wrap
highlight-style: github       # Syntax highlighting theme
```

## Table of Contents

```yaml
toc: true
toc-depth: 3                  # Heading levels to include
toc-location: left            # left, right, body
toc-title: "On this page"
toc-expand: 2                 # Levels to expand by default
```

## Theming and Styling

```yaml
theme: cosmo                  # Bootstrap theme
css: custom.css               # Custom CSS file
fontsize: 1.1em
linestretch: 1.5
mainfont: "Source Sans Pro"
monofont: "Fira Code"
fontcolor: "#333333"
linkcolor: "#0066cc"
backgroundcolor: "#ffffff"
```

### Available Themes

`default`, `cerulean`, `cosmo`, `cyborg`, `darkly`, `flatly`, `journal`, `litera`, `lumen`, `lux`, `materia`, `minty`, `morph`, `pulse`, `quartz`, `sandstone`, `simplex`, `sketchy`, `slate`, `solar`, `spacelab`, `superhero`, `united`, `vapor`, `yeti`, `zephyr`

## Common Patterns

### Data Analysis Document

```yaml
---
title: "Analysis Report"
author: "Data Team"
date: today
format:
  html:
    toc: true
    code-fold: true
    code-tools: true
jupyter: python3
execute:
  warning: false
  cache: true
---
```

### Confluence Technical Doc

```yaml
---
title: "Technical Specification"
format: confluence-html
jupyter: python3
execute:
  echo: false
  warning: false
---
```

### Presentation-Ready Report

```yaml
---
title: "Quarterly Review"
subtitle: "Q4 2024"
author: "Analytics"
date: today
format:
  html:
    theme: cosmo
    toc: true
    toc-location: left
    number-sections: true
    code-fold: true
    fig-width: 8
    fig-height: 5
jupyter: python3
execute:
  echo: false
  warning: false
---
```
