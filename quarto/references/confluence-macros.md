# Confluence Macros Reference

Confluence Storage Format markup for use in qmd files via raw blocks.

## Raw Block Syntax

```markdown
```{=confluence}
<!-- Confluence Storage Format XML here -->
```
```

## Status Macro

Display colored status badges:

```{=confluence}
<ac:structured-macro ac:name="status">
  <ac:parameter ac:name="colour">Green</ac:parameter>
  <ac:parameter ac:name="title">DONE</ac:parameter>
</ac:structured-macro>
```

**Colors:** `Green`, `Yellow`, `Red`, `Blue`, `Grey`

**Common statuses:**
- Green: DONE, APPROVED, LIVE
- Yellow: IN PROGRESS, REVIEW, PENDING
- Red: BLOCKED, FAILED, CRITICAL
- Blue: INFO, NEW, TODO
- Grey: DRAFT, NA, ARCHIVED

## Task List

```{=confluence}
<ac:task-list>
  <ac:task>
    <ac:task-status>incomplete</ac:task-status>
    <ac:task-body>First task item</ac:task-body>
  </ac:task>
  <ac:task>
    <ac:task-status>complete</ac:task-status>
    <ac:task-body>Completed task</ac:task-body>
  </ac:task>
</ac:task-list>
```

## Info/Note/Warning Panels

### Info Panel

```{=confluence}
<ac:structured-macro ac:name="info">
  <ac:parameter ac:name="title">Note</ac:parameter>
  <ac:rich-text-body>
    <p>Informational content here.</p>
  </ac:rich-text-body>
</ac:structured-macro>
```

### Warning Panel

```{=confluence}
<ac:structured-macro ac:name="warning">
  <ac:parameter ac:name="title">Warning</ac:parameter>
  <ac:rich-text-body>
    <p>Warning content here.</p>
  </ac:rich-text-body>
</ac:structured-macro>
```

### Note Panel

```{=confluence}
<ac:structured-macro ac:name="note">
  <ac:parameter ac:name="title">Important</ac:parameter>
  <ac:rich-text-body>
    <p>Note content here.</p>
  </ac:rich-text-body>
</ac:structured-macro>
```

### Tip Panel

```{=confluence}
<ac:structured-macro ac:name="tip">
  <ac:parameter ac:name="title">Tip</ac:parameter>
  <ac:rich-text-body>
    <p>Helpful tip here.</p>
  </ac:rich-text-body>
</ac:structured-macro>
```

## Table of Contents

```{=confluence}
<ac:structured-macro ac:name="toc">
  <ac:parameter ac:name="maxLevel">3</ac:parameter>
  <ac:parameter ac:name="minLevel">1</ac:parameter>
  <ac:parameter ac:name="style">disc</ac:parameter>
</ac:structured-macro>
```

## Expand/Collapse Section

```{=confluence}
<ac:structured-macro ac:name="expand">
  <ac:parameter ac:name="title">Click to expand</ac:parameter>
  <ac:rich-text-body>
    <p>Hidden content that expands on click.</p>
  </ac:rich-text-body>
</ac:structured-macro>
```

## Code Block with Syntax Highlighting

```{=confluence}
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">python</ac:parameter>
  <ac:parameter ac:name="title">Example Code</ac:parameter>
  <ac:parameter ac:name="linenumbers">true</ac:parameter>
  <ac:plain-text-body><![CDATA[
import polars as pl

df = pl.read_csv("data.csv")
print(df.head())
]]></ac:plain-text-body>
</ac:structured-macro>
```

**Languages:** `python`, `bash`, `sql`, `json`, `yaml`, `javascript`, `java`, `go`, `rust`, `xml`, `html`, `css`

## Anchor/Bookmark

```{=confluence}
<ac:structured-macro ac:name="anchor">
  <ac:parameter ac:name="0">section-name</ac:parameter>
</ac:structured-macro>
```

Link to anchor: `[Link text](#section-name)`

## Page Include

Include content from another page:

```{=confluence}
<ac:structured-macro ac:name="include">
  <ac:parameter ac:name="0">
    <ri:page ri:content-title="Page Title"/>
  </ac:parameter>
</ac:structured-macro>
```

## Common Patterns

### Document Header with Status

```markdown
# Project Specification

```{=confluence}
<ac:structured-macro ac:name="status">
  <ac:parameter ac:name="colour">Yellow</ac:parameter>
  <ac:parameter ac:name="title">IN REVIEW</ac:parameter>
</ac:structured-macro>
```

**Owner:** @username
**Last Updated:** 2025-01-07
```

### Checklist Section

```markdown
## Tasks

```{=confluence}
<ac:task-list>
  <ac:task>
    <ac:task-status>complete</ac:task-status>
    <ac:task-body>Define requirements</ac:task-body>
  </ac:task>
  <ac:task>
    <ac:task-status>incomplete</ac:task-status>
    <ac:task-body>Implement feature</ac:task-body>
  </ac:task>
  <ac:task>
    <ac:task-status>incomplete</ac:task-status>
    <ac:task-body>Write tests</ac:task-body>
  </ac:task>
</ac:task-list>
```
```

### Collapsible Details

```markdown
## Implementation Details

```{=confluence}
<ac:structured-macro ac:name="expand">
  <ac:parameter ac:name="title">Technical Details</ac:parameter>
  <ac:rich-text-body>
    <p>Detailed technical information that most readers can skip.</p>
  </ac:rich-text-body>
</ac:structured-macro>
```
```
