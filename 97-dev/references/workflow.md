# Working Effectively

Principles for effective day-to-day development workflow.

## Know Your Next Commit (Essay 47)

Dan Bergh Johnsson: "Know your next commit. If you cannot finish, throw away your changes, then define a new task you believe in."

**Task-focused developers:**
- Break work into small, achievable chunks (1-2 hours each)
- Understand exactly which files they'll modify
- Commit changes with clear purpose
- When tasks exceed estimates, discard experimental work and redefine approach
- Preserve learned insights while maintaining repository quality

**Problem-decomposition strugglers:**
- Attempt too much simultaneously
- Extended sessions lack defined endpoints
- Result: speculative code that doesn't align with eventual solution
- Feel pressured to commit vague changes rather than restart

**Role of experimentation:** Even experienced developers engage in exploratory coding. But: speculative work serves learning purposes and gets discarded before committing.

**Crucial habit:** Recognize when you've strayed into unmapped territory. Deliberately reset your approach.

**Central message:** Commit only intentional work. Use experimentation to gain understanding, then translate into focused, bounded tasks with clear completion criteria.

## You Are Not the User (Essay 03)

**False consensus bias:** Developers assume others think like them. "Users don't think like programmers. For a start, they spend much less time using computers."

**Observation over assumption:** Watch real users complete authentic tasks. "Spending an hour watching users is more informative than spending a day guessing what they want."

**What you'll notice:**
- Users complete tasks in predictable sequences
- Make identical mistakes at the same points
- Narrow focus when confused (don't explore broadly)
- Stick with functional solutions, however inefficient

**Design implications:**
- "It's better to provide one really obvious way of doing things than two or three shortcuts"
- Avoid elaborate features based on speculative "what if" scenarios
- Place help text adjacent to problem areas (narrowed attention prevents finding distant solutions)
- Users' stated preferences often diverge from actual behaviors

**Bottom line:** Design decisions should reflect observed user behavior, not programmer assumptions or user testimony alone.

## Don't Be Afraid to Break Things (Essay 24)

**Core insight:** Fear of breaking things leads to stagnation. Legacy code becomes untouchable, accumulating complexity.

**The problem:** Without willingness to refactor, code calcifies. Small workarounds accumulate into unmaintainable messes.

**The solution:**
- Comprehensive test coverage enables confident refactoring
- Break dependencies that make code fragile
- Refactor incrementally but persistently
- Accept temporary breakage as cost of long-term health

**Practice:** When encountering code that "cannot be changed," question why. Often the answer is fear, not technical impossibility.

## Put Everything Under Version Control (Essay 68)

**The rule:** Everything. Not just source code.

**What to version:**
- Source code
- Build scripts and configurations
- Documentation
- Database schemas and migrations
- Test data and fixtures
- Deployment configurations
- Dependencies (or lockfiles)

**Benefits:**
- Reproducible builds
- Bisection for debugging
- Fearless experimentation (can always revert)
- Collaboration without chaos
- Audit trail

**Anti-pattern:** "I'll just make a quick fix" without committing. Every change should flow through version control.

## The Boy Scout Rule Applied to Workflow

**Daily practice:**
- Start each task with clear scope and completion criteria
- Leave code cleaner than you found it
- Commit logical, atomic changes
- Write commit messages that explain *why*
- Review your own diff before committing
- Run tests before pushing

**Weekly practice:**
- Review code you wrote last week - what would you change?
- Identify one area of codebase that needs cleanup
- Learn one new technique or tool
- Share knowledge with teammates
