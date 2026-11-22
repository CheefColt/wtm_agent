# Pay Check: start here

Read these before doing anything:
1. `PLAN.md`: what we're building, the tools, and the UI spec.
2. `context/DECISIONS.md`: what's already decided. Don't reopen these without asking.
3. `context/EVENT.md`: hackathon rules and the judging rubric.
4. `context/LESSONS.md`: the design rule ("evidence in code, judgement in the model") and how a good question looks.
5. `context/TRAPS.md`: the traps to plant in persona data, each with a clean twin.
6. `context/ATTACKS.md`: what other teams will try. Test all of it.

Unbreakable is a build requirement, not a nice-to-have (25 pts plus the Most Unbreakable prize, and other teams will attack us):
- Turn every item in `context/ATTACKS.md`, and the risky and clean twin of every trap in `context/TRAPS.md`, into automated tests in `tests/test_attacks.py`.
- Keep the tests passing before each push.
- A failing attack test blocks the push.

How the user likes to work:
- Short, plain answers.
- Plan and agree before coding; no slop or extra features.
- Commit or push only when asked.
