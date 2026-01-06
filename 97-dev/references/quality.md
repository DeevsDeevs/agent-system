# Code Quality

Principles for maintaining and improving code quality.

## The Boy Scout Rule (Essay 08)

Robert Baden-Powell: "Try and leave this world a little bit better than you found it."

**The rule:** Always check a module in cleaner than when you checked it out.

**Practice:**
- Ensure new code meets quality standards
- Improve at least one existing element before committing
- Small enhancements: renaming variables, refactoring functions, removing dependencies
- Doesn't require perfection - just incremental improvement

**Impact:** Prevents software degradation, creates systems that continuously improve, fosters team responsibility rather than individual silos.

**Cultural aspect:** Treating messy code like littering. Teams caring collectively for shared code produces better results than individuals maintaining only their own sections.

## Don't Repeat Yourself - DRY (Essay 30)

Hunt & Thomas, The Pragmatic Programmer: "Every piece of knowledge must have a single, unambiguous, authoritative representation within a system."

**Three applications:**

1. **Code duplication** - Repeated code increases maintenance burden and bug risk. Inflates codebases, makes it harder to track necessary changes across all instances.

2. **Process automation** - Manual processes (testing, integration) are error-prone. Should be automated and standardized: "there is only one way of accomplishing the task."

3. **Logic abstraction** - Repetitive logic patterns (copy-paste conditionals) should be addressed through design patterns: Abstract Factory, Factory Method, Strategy.

**Related principles:** Once and Only Once, Open/Closed Principle, Single Responsibility Principle.

**Caveat:** Legitimate exceptions exist when performance or genuine requirements demand it (e.g., database denormalization).

## Single Responsibility Principle (Essay 76)

Uncle Bob Martin: "Gather together those things that change for the same reason, and separate those things that change for different reasons."

**The rule:** A subsystem, module, class, or function should have only one reason to change.

**Problem example - Employee class with:**
- `calculatePay()` - changes with business rule updates
- `reportHours()` - changes with reporting format requests
- `save()` - changes with database schema modifications

These change for different reasons, making the class volatile.

**Solution - separate into:**
- `Employee` - handles business calculations
- `EmployeeReporter` - manages reporting functionality
- `EmployeeRepository` - handles database persistence

**Benefit:** Independent component deployment. Modifications to reporting don't force redeployment of business rule components.

## Make Interfaces Easy to Use Correctly (Essay 55)

Scott Meyers: "Interfaces should prioritize user convenience over implementer convenience."

**Two qualities of good interfaces:**
1. Intuitive correct usage - the path of least resistance should be correct
2. Built-in error prevention - anticipate and prevent mistakes

**Design approach:**
- Mock up or prototype interfaces before implementation
- Write API calls before declaring functions
- Develop from user's perspective, not implementer's

**Iteration:** Actively observe how users misuse early releases. Modify interfaces to make incorrect use impossible rather than merely discouraged.

**Philosophy:** Interfaces exist to serve their users, not to benefit those building them.

## Only the Code Tells the Truth (Essay 62)

**Core insight:** The running code represents the ultimate truth of program behavior. Requirements, design documents, and comments can become outdated - executable code cannot lie.

**On comments:** Rather than explanatory comments, refactor code to be self-explanatory. Comments can become incorrect and clutter the interface.

**Strategies for clear code:**
- Use meaningful, descriptive names
- Organize code around cohesive functionality
- Decouple systems for orthogonality
- Write automated tests that document intended behavior
- Continuously refactor toward simpler solutions
- Prioritize readability and comprehension

**Perspective:** Treat code as a composition worthy of careful crafting. Code often outlives initial expectations.
