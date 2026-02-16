# Baseline Project Guidelines

## MCP Tools

### Context7 - MUST USE
**When to use**:
- Always when looking up library documentation
- When troubleshooting library-specific issues
- Before implementing features with external dependencies

**How to use**:
1. `mcp__context7__resolve-library-id` - Find the library ID
2. `mcp__context7__get-library-docs` - Get documentation with the ID from step 1

**Why**: Ensures current, accurate documentation rather than outdated knowledge.

## Code Quality

### Comments
**Only write comments for**:
- Complex algorithms that aren't immediately obvious
- Non-obvious workarounds for known issues/bugs
- Critical "why" explanations that code cannot express

**99% of code should be self-explanatory through**:
- Clear, descriptive naming
- Proper structure and organization
- Following language best practices

## Git Workflow

### Commit Messages
Use **Conventional Commits** format:
- `feat:` - New features
- `fix:` - Bug fixes
- `refactor:` - Code refactoring
- `docs:` - Documentation changes
- `test:` - Test updates
- `chore:` - Maintenance tasks

Example: `feat: add user authentication system`

### Branch Naming
Use **type prefixes**:
- `feature/` - New features
- `fix/` - Bug fixes
- `refactor/` - Code refactoring

Example: `feature/user-authentication`

## Engineering Philosophy

### Approach
- **Pragmatic over perfect** - Ship working solutions, iterate if needed
- **Question assumptions** - Always ask clarifying questions before building
- **YAGNI** - Don't over-engineer; build what's needed now
- **KISS** - Prefer simple solutions over complex ones

### Communication Style
- **Ask questions** when requirements are unclear or ambiguous
- **Brainstorm ideas** - discuss different approaches
- **Find optimal approach** - balance simplicity, maintainability, and effectiveness
- **Avoid over-engineering** - question if complexity is truly necessary
- **Be concise** - get to the point, focus on solutions

## Venue Context

Use the **venue-expert** skill for exchange-specific context. Invoke it when:
- Starting any research involving exchange data
- Debugging trading system issues (feed, order, session problems)
- Needing venue mechanics: order types, matching rules, session times, data formats, regulatory quirks

## Testing
- Tests will be specified when needed
- Don't assume - ask if testing is required

---

*This is the baseline for all projects. Project-specific guidelines may extend or override these.*
