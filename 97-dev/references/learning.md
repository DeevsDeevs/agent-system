# Learning & Growth

Principles for continuous improvement and professional development.

## Continuous Learning (Essay 18)

**Reality:** "You need to keep learning to stay marketable. Otherwise, you'll become a dinosaur." Technology changes fast.

**Strategies:**
- **Consume actively:** Read blogs, books, follow industry voices
- **Get hands-on:** Write code, experiment with technologies
- **Seek mentorship:** Learn from those with greater expertise
- **Study frameworks:** Especially open-source where you can review quality code
- **Learn from failures:** Investigate bugs and problems thoroughly
- **Teach others:** Presentations and discussion groups deepen understanding
- **Attend conferences:** Listen to podcasts during commutes
- **Expand horizons:** Learn new programming languages and tools annually
- **Study business domain:** Understand real-world problems you're solving

**Key insight:** Treat education as ongoing professional responsibility. Don't wait for employers to provide training. Success requires consistent, modest effort over time.

## Do Lots of Deliberate Practice (Essay 22)

**Definition:** Performing a task with the goal of improving your skill - not simply completing it. Focused repetition aimed at mastering specific aspects.

**The investment:** Research suggests ~10,000 hours for expertise. Peter Norvig: "about 20 hours per week for 10 years." Talent isn't destiny - time invested matters more than innate ability.

**The key:** Work on areas where you struggle, not where you excel.

Peter Norvig: "Challenging yourself with a task that is just beyond your current ability, trying it, analyzing your performance while and after doing it, and correcting any mistakes."

Mary Poppendieck: "It means challenging yourself, doing what you are not good at."

**Critical distinction:** Unlike paid development (aims to finish products), deliberate practice aims to improve performance.

**Question:** How much time do you spend developing yourself versus developing for others?

**Bottom line:** Greatness stems from deliberate choice and commitment. Expertise arrives gradually through consistent, focused effort.

## Read Code (Essay 70)

**Core idea:** Reading code - whether others' or your past self's - accelerates your development as a programmer.

**Learning from others:**
- Identify both strengths and weaknesses
- When code is hard to read, ask why: poor formatting? unclear naming? mixed concerns?
- Well-written code teaches design patterns and expressive naming

**Key insight:** "Reading other people's code is particularly hard. Not necessarily because other people's code is bad, but because they probably think and solve problems in a different way to you."

**Reviewing your own work:** Examining earlier code reveals skill evolution. Humbling and motivating - shows improvement while highlighting persistent bad habits.

**Recommendation:** Rather than buying another programming book, invest time reading actual code from open-source projects or your own archives.

**Principle:** Code review - of others' work or your own - is professional development in action.

## Know Your Limits (Essay 46)

**Core concept:** Respect finite boundaries - time, money, processing power, storage. Success depends on understanding constraints.

**Self-knowledge required:**
- Understand yourself, team, budget, technical expertise
- Grasp space and time complexity of algorithms
- Know performance characteristics of systems

**Complexity classes matter:** As data grows, O(ln(n)) vastly outperforms O(n²) and O(e^n). For practical data sizes, classes reduce to "near-constant, near-linear, or near-infinite."

**Hardware hierarchy (orders of magnitude):**
- Registers: < 1 ns
- L1/L2 cache: 1-10 ns
- Main memory: 100 ns
- SSD: 100 μs
- Network: 100 ms

Modern systems use caching and lookahead, but only predictable access patterns work effectively.

**Practical application:** Theoretical complexity analysis must meet real-world measurement. Test on actual hardware with actual data.

**Bottom line:** "You pays your money and you takes your choice." Match algorithms to both theoretical requirements and actual system architecture.
