# Pay Check: start here

**Picking up mid-build? Read `HANDOFF.md` first.** It says where we are and what's next.

Then read these before doing anything:
1. `PLAN.md`: what we're building, the tools, and the UI spec.
2. `context/DECISIONS.md`: what's already decided. Don't reopen these without asking.
3. `context/EVENT.md`: hackathon rules and the judging rubric.
4. `context/LESSONS.md`: the design rule ("evidence in code, judgement in the model") and how a good question looks.
5. `context/TRAPS.md`: the traps to plant in persona data, each with a clean twin.
6. `context/ATTACKS.md`: what other teams will try. Test all of it.
7. `context/MODELS.md`: Gemini models, rate limits and fallback order.

Unbreakable is a build requirement, not a nice-to-have (25 pts plus the Most Unbreakable prize, and other teams will attack us):
- **Push-blocking tests (`tests/test_attacks.py`, no Gemini calls):** every code-level item in `context/ATTACKS.md` — approval gate, payee/amount match, daily cap, amount parsing, tool failure, injected text. Use a scripted fake model that misbehaves (e.g. calls `send_payment` without approval) to prove a fooled model still can't move money.
- **Manual live check (`scripts/live_check.py`, real Gemini through the rate limiter):** the risky and clean twin of every trap in `context/TRAPS.md`, plus model-level injections. Run by hand before the demo; not a push gate, to save quota.
- Keep the push-blocking tests passing; a failing one blocks the push.

## Handoff rule
After every commit or finished piece of work, update `HANDOFF.md` in the same commit:
- rewrite the **Now** section (state, next step, open questions);
- add one line at the top of the **Log**.

Keep it short and plain. Another agent must be able to continue from it alone.

How the user likes to work:
- Short, plain answers.
- Plan and agree before coding; no slop or extra features.
- Commit or push only when asked.
