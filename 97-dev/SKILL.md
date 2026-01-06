---
name: 97-dev
description: Apply timeless programming wisdom from "97 Things Every Programmer Should Know" when writing, reviewing, or refactoring code. Use for design decisions, code quality checks, and professional development guidance.
---

# 97-dev: Programmer's Wisdom

Distilled principles from 97 Things Every Programmer Should Know. Apply when writing, reviewing, or making design decisions.

## Core Philosophy

**Code is design.** Software development is a creative discipline, not mechanical construction. Treat code as a composition worthy of careful crafting.

**The code tells the truth.** Documentation lies, comments decay - only executable code cannot deceive about actual behavior. Make code self-explanatory through structure and naming.

## Simplicity

**Beauty is in simplicity.** Simplicity enables readability, maintainability, and testability. Aim for 5-10 line methods with single clear purposes.

**Simplicity comes from reduction.** Remove everything unnecessary. Extra lines, extra variables, extra anything should be purged. Sometimes deletion and rewriting beats incremental fixes.

**Improve code by removing it.** Less is more. Question features: "Is it all needed?" Remove what was added because it was interesting, not valuable.

## Code Quality

**Boy Scout Rule.** Leave code cleaner than you found it. Small improvements (better names, extracted functions, removed dependencies) compound over time.

**Don't Repeat Yourself (DRY).** Every piece of knowledge should have a single, authoritative representation. Duplication breeds inconsistency and maintenance burden.

**Single Responsibility Principle.** Gather things that change for the same reason; separate things that change for different reasons. One class/module/function = one reason to change.

**Make interfaces easy to use correctly and hard to use incorrectly.** Design from the user's perspective. The path of least resistance should be the correct path.

## Comments & Communication

**Comment only what code cannot say.** Don't narrate what code does - improve the code instead. Comments should explain *why*, not *what*. Rename unclear methods, extract functions with descriptive names.

**Write code as if you had to support it forever.** Your code creates a permanent professional legacy. Future programmers (including you) will read it long after you've moved on.

## Technical Debt

**Act with prudence.** Incur technical debt only when absolutely necessary, then repay immediately. Track the "interest" accumulating. Deferred work becomes exponentially harder.

## Testing & Errors

**Testing is engineering rigor.** Testing is software's answer to structural analysis. It's a professional obligation, not optional. "We don't have time to test" is never acceptable.

**Don't ignore that error.** Always check for and handle every potential error. No exceptions. Ignored errors produce brittle code and security vulnerabilities.

**Check your code first before blaming others.** Compiler bugs are rare. Invest effort isolating problems and testing assumptions before suspecting tools.

## Professional Practice

**The professional programmer.** Take personal responsibility for: career development, code quality, team accountability, and craftsmanship. Strengthen discipline under pressure, never compromise it.

**You gotta care about the code.** Excellence stems from attitude, not just technical knowledge. Refuse to settle for code that merely appears functional - craft elegant code that is clearly correct.

**Continuous learning.** Technology changes fast. Read, experiment, seek mentorship, teach others, learn new languages annually. Treat education as an ongoing professional responsibility.

**Deliberate practice.** Expertise requires focused repetition on areas where you struggle - not areas where you excel. ~10,000 hours of deliberate practice, challenging yourself with tasks just beyond current ability.

## Working Effectively

**Know your next commit.** Break work into 1-2 hour chunks with clear completion criteria. If you can't finish, discard experimental work and redefine the task. Never commit speculative code.

**Know your limits.** Respect finite boundaries: time, money, processing power, memory. Understand complexity classes and hardware performance hierarchies. Theoretical analysis must meet empirical measurement.

**You are not the user.** False consensus bias makes developers assume users think like them. Observe real users on real tasks. One hour watching users beats a day guessing.

**Read code.** Reading others' code accelerates growth. Notice what makes code hard to read (poor formatting, unclear naming, mixed concerns) and what makes it elegant.

## Quick Reference Checklist

When writing code:
- [ ] Does each function/class have a single responsibility?
- [ ] Is there any duplication that should be extracted?
- [ ] Can anything be removed without losing functionality?
- [ ] Are names descriptive enough that comments aren't needed?
- [ ] Would I want to maintain this code for years?

When reviewing code:
- [ ] Does this change leave the codebase cleaner?
- [ ] Are error cases handled explicitly?
- [ ] Is the interface easy to use correctly?
- [ ] Does the code match existing patterns in the file/repo?

When debugging:
- [ ] Have I ruled out my own code first?
- [ ] Have I isolated the problem systematically?
- [ ] Am I testing assumptions, not just looking for confirmation?

## References

Based on essays from [97 Things Every Programmer Should Know](https://github.com/97-things/97-things-every-programmer-should-know):

| Principle | Essay |
|-----------|-------|
| Technical debt | Act with Prudence (01) |
| You're not the user | Ask What Would the User Do (03) |
| Simplicity | Beauty Is in Simplicity (05) |
| Boy Scout Rule | The Boy Scout Rule (08) |
| Blame yourself first | Check Your Code First (09) |
| Code is design | Code Is Design (12) |
| Comments | Comment Only What Code Cannot Say (17) |
| Continuous learning | Continuous Learning (18) |
| Deliberate practice | Do Lots of Deliberate Practice (22) |
| Don't ignore errors | Don't Ignore that Error (26) |
| DRY | Don't Repeat Yourself (30) |
| Remove code | Improve Code by Removing It (39) |
| Know your limits | Know Your Limits (46) |
| Know next commit | Know Your Next Commit (47) |
| Easy interfaces | Make Interfaces Easy to Use (55) |
| Code tells truth | Only the Code Tells the Truth (62) |
| Professionalism | The Professional Programmer (67) |
| Read code | Read Code (70) |
| Reduction | Simplicity Comes from Reduction (75) |
| SRP | The Single Responsibility Principle (76) |
| Testing rigor | Testing Is Engineering Rigor (83) |
| Support forever | Write Code as If Supporting Forever (93) |
| Care about code | You Gotta Care about the Code (96) |
