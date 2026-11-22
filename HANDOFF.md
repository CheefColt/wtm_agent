# Handoff

Update this with every commit: rewrite **Now**, add one line to the top of **Log**.

## Now
- **State:** planning done, no code yet. Docs are in `PLAN.md` and `context/`.
- **Agreed build order:**
  1. persona data with traps;
  2. tools and the safety module;
  3. push-blocking tests;
  4. agent loop with Gemini and the rate limiter;
  5. UI;
  6. README.
- **Next step:** 1 — synthetic persona data (3–4 personas, 2–3 traps each, every trap with a clean twin).
- **Open questions:**
  - exact Gemini model ID strings (user to copy from AI Studio);
  - the tool list needs about 3 more than PLAN.md lists (`decode_qr`, bill fetch, parsing a pasted message);
  - a few more may be needed later.
- **Working branch:** `ccr-c57dee27-oogryd`.

## Log (newest first)
- 22 Nov 08:43 UTC · Testing split agreed: code-level attack tests block the push and use a scripted fake model; real-Gemini trap and injection checks are a manual script. Added this handoff system.
- 22 Nov 08:30 UTC · `e2ffe78` · Added `context/MODELS.md`: Gemini limits, with 3.5 Flash Lite primary and a fallback order.
