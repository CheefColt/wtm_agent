# What What They Meant taught us (apply these here)

Source: github.com/nsharan2000/what-they-meant, our research on when payment agents should ask. Only ideas are carried over; no code or data.

## Core ideas
1. **People are slightly wrong, rarely malicious.**
   - Most real losses come from honest slips: the wrong same-name person, an extra digit, an old number, a stale account.
   - The fact that catches the slip is almost always one lookup away.
2. **Twin pairs.**
   - Every trap has a twin: the same request where everything checks out.
   - The agent gets credit only if it **asks on the risky twin AND pays on the clean twin**.
   - "Always ask" and "always pay" both score zero.
3. **Over-asking is a real failure, not a safe default.**
   - Needless questions train users to click "yes", which kills the safety.
   - When frontier models were told to "be careful", Opus asked needlessly on 73% of harmless requests inside a realistic app.
   - Our trained model's needless questions rose from 7% to 37% after RL.
4. **The realism gap.**
   - Models do well when the deciding fact sits next to the question, and badly when it's buried in a real app's data.
   - Opus: 66% of pairs in the test-style version, 27% in the app version.
   - In more than half our pairs, the twins differ in a single tool result by a median of 28 characters, about 0.3% of the prompt.
   - LLM attention alone is not reliable for spotting these.

## So the design rule for this build
**Evidence in code, judgement in the model.**
- **Tools compute plain facts and return them in their own fields.** For example:
  - `registered_name` vs `saved_name`;
  - `times_paid_before`;
  - `usual_amount` and `ratio_to_usual`;
  - `upi_id_changed_on`;
  - `account_age_days`;
  - `request_type` (collect vs pay).

  Don't make Gemini dig a 28-character difference out of a wall of JSON.
- **Tools return facts with no verdict words.** Write "registered_name: Rakesh Yadav", not "MISMATCH!". The model decides, and the facts stay honest.
- **The model decides pay / ask / stop and words the message.**
- **Hard safety lives in code.** For example: no approval → no `send_payment`, and the payee and amount must equal what was shown on the card.

## How a good question looks
- **One** question that **names the mismatch with the evidence** and **offers the likely fix**.
  > "98765-43210 is registered to Rakesh Yadav, not Meera Joshi. Her saved number is 98765-43211. Use that one?"
- **Bad:** "Are you sure?", "Please confirm the details", or listing generic risks. These count as needless or generic.
- **When nothing clashes,** go straight to the approval card. No "just to double-check".

## When the user insists (pushback)
- **After an informed question, the user owns the decision.** If they've seen the evidence and still say "yes, send it", show the approval card, with the warning stated once on it.
- **Exception: clear-fraud "stop" cases.** For example a collect request disguised as receiving money, or a "KYC update" link. These stay blocked.
- **Generic pressure is not informed consent.** "Urgent, don't ask me anything" before seeing the evidence doesn't count.
