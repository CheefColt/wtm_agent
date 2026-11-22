# Gemini models and rate limits (our AI Studio key, read 22 Nov 2026)

Source: AI Studio → Rate limit page, "last 28 days" view. Limits are per project. Re-check there if calls start failing with 429.

RPM = requests per minute, TPM = tokens per minute, RPD = requests per day.

## Usable text models (in fallback order)
| Order | Model (as shown in AI Studio) | RPM | TPM | RPD | Use |
|---|---|---|---|---|---|
| 1 | **Gemini 3.5 Flash Lite** | 15 | 250K | 500 | **Primary.** All app traffic and live tests. |
| 2 | Gemini 3.1 Flash Lite | 15 | 250K | 500 | First fallback (same budget, separate quota). |
| 3 | Gemini 2.5 Flash Lite | 10 | 250K | 20 | Fallback. |
| 4 | Gemini 3.8 Flash | 5 | 250K | 20 | Fallback. |
| 5 | Gemini 3.6 Flash | 5 | 250K | 20 | Fallback. |
| 6 | Gemini 3 Flash | 5 | 250K | 20 | Fallback. |
| 7 | Gemini 4 Hydrogen | 5 | 250K | 20 | Fallback. |
| 8 | Gemini 2.5 Flash | 5 | 250K | 20 | Last fallback. |

Exact API model ID strings: copy them from AI Studio into `.env` / config; don't guess them.

Peak usage seen on 3.5 Flash Lite over the 28 days: 11 RPM, 48.78K TPM, 145 RPD.

## Not usable on this key (limit 0 / 0)
Gemini 2 Flash, Gemini 2 Flash Lite, Gemini 2.5 Pro, Gemini 3.1 Pro, Gemini 4 Argon, Gemini 4 Carbon, Gemini 4 Neon, Deep Research Pro Preview, Computer Use Preview, and all image models (Nano Banana family).
A Pro subscription does not lift these API limits.

## Not relevant to Pay Check
- TTS models (2.5 Flash TTS, 3.1 Flash TTS, 3.8 Flash TTS, 3.8 Flash Lite TTS): 3 RPM, 10K TPM, 10 RPD.
- Gemini 3.5 Transcribe (Live API): 3 RPM, 10K TPM, 25 RPD.
- Antigravity (agents product): 60 RPM, 100K TPM, 100 RPD.

## Rules for our code
- **Client-side limiter per model:** stay under its RPM (e.g. ≤ 14/min on the primary, so ≥ 4.3 s apart in bursts) and track RPD.
- **On 429 or quota exhausted:** move to the next model in the table. On any other error: one retry, then fail closed (no payment, a plain message).
- **Budget:** one user turn ≈ 2–4 model calls (tool loop), so ~500 RPD ≈ 125–250 turns per day on the primary. Keep the demo-day quota for the demo.
- **Tests:**
  - safety-gate tests (approval token, payee/amount match, daily cap, amount parsing) call code directly and use no model calls;
  - agent-behaviour tests (trap twins, injections) run against real Gemini through the same limiter, and can be run in a subset.
