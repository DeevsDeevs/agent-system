# Testing & Error Handling

Principles for testing, error handling, and debugging.

## Testing Is the Engineering Rigor of Software Development (Essay 83)

**Core argument:** Traditional engineers use mathematics and physics to validate designs before construction. Software lacks such theoretical frameworks, but has a crucial advantage: software is cheap to build and test repeatedly.

**The equivalence:** Testing serves as software's primary verification mechanism - the equivalent of structural analysis in engineering. "Testing is indeed the path to reproducibility and quality."

**Professional responsibility:** Testing isn't optional - it's a professional obligation. Just as bridge builders must perform structural analysis despite deadlines, developers should reject "we don't have time to test."

**Tools:** Unit testing, mock objects, test harnesses - leverage these to ensure quality.

**Bottom line:** "Testing alone isn't sufficient, but it is necessary."

## Don't Ignore That Error (Essay 26)

Pete Goodliffe: "No matter how unlikely you think an error is in your code, you should always check for it, and always handle it. Every time."

**The analogy:** Ignoring errors is like ignoring physical pain - dismissing them as unlikely leads to compounded problems.

**Error reporting methods:**
- Return codes - easily overlooked, lack visibility
- errno - global variable, problematic in multi-threaded environments
- Exceptions - structured but still ignorable via empty catch blocks

**Consequences of ignoring errors:**
- Brittle, bug-ridden code
- Security vulnerabilities hackers exploit
- Poorly structured interfaces

**Common excuses:** "It won't happen" / "It's just a demo" / "I'll handle it later" / "Performance concerns" - none withstand scrutiny.

## Check Your Code First Before Looking to Blame Others (Essay 09)

Allan Kelly: "I once had a genuine problem with a compiler bug optimizing away a loop variable, but I have imagined my compiler or OS had a bug many more times."

**Reality:** Compiler bugs are exceptionally rare despite how frequently developers suspect them. Mature, widely-used tools deserve confidence.

**When to suspect tools:** Early releases, niche tools, version 0.1 open-source projects, alpha commercial software.

**Debugging strategy:**
- Isolate the problem systematically
- Test assumptions and conventions
- Check for stack corruption and type mismatches
- Run code across different machines and configurations

**Multi-threaded systems:** Particular debugging challenge where traditional testing proves unreliable. Code simplicity becomes essential.

**Sherlock Holmes principle:** Embrace the improbable truth over the impossible one when investigating mysterious bugs.

## Comment Only What the Code Cannot Say (Essay 17)

**The problem:** "A comment is of zero (or negative) value if it is wrong." Bad comments persist longer than coding errors, creating constant distraction and misinformation.

**Types of wasteful comments:**
- Comments that restate code logic (noise)
- Commented-out code that becomes stale
- Version history comments (use version control instead)

**When comments matter:** Useful comments address gaps between what code expresses and what needs explanation.

**The principle:** Don't comment what code should say - improve the code instead:
- Rename unclear methods
- Extract functions with descriptive names
- Let code speak for itself

**What to comment:** *Why* decisions were made, business context, non-obvious solutions that code alone cannot convey.
