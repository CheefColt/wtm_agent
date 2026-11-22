# Decisions made while planning (22 Nov 2026)

1. **Track:** 02, Commerce & payments.
2. **Idea:** Pay Check. It pays what you meant, not what you typed: ask one named question on a real mismatch, and otherwise show the approval card.
3. **Second input mode:** "What am I approving?", where the user pastes an incoming SMS, collect request, link or QR. Same agent, tools and records.
4. **Model:** Gemini API, hosted. Not our Tiny Aya adapter.
5. **Interface:** simple web chat. A UPI-style phone frame on the left, the persona's account on the right; see the UI section in PLAN.md.
6. **Several personas (3–4), free-typed requests.** The scenario is whatever the user types. Traps live in the data, never in scripts or prompts.
7. **Right panel is for the human only.** The agent sees data only through tools. The panel and the tools read the same data file.
8. **Data is fresh and synthetic**, made for this build. Nothing is copied from What They Meant.
   - Not hiding the link: one credit line in the README.
   - That dataset is CC-BY-4.0, so a direct copy would need credit anyway.
9. **No twins-score button as a headline.** A fixed test set is still useful for us to check both twins of each trap.
10. **Demo clip (10 s):** a pasted scam message gets blocked, then a normal payment goes straight through to the receipt.

Rejected:
- Invoice gatekeeper: good, but further from our strengths.
- Bill explainer: weak on "act".
- Merchant refund checker: less personal.
- A single scripted customer.
