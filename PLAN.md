# Pay Check: plan

A UPI payment assistant that pays what you meant, not what you typed.
Track 02 (Commerce & payments), The Agentic Room, 22 Nov 2026.

## The idea
People are slightly wrong all the time: the wrong Meera, an extra zero, an old number. The facts that catch it are already in the account. Pay Check looks before it pays. It asks one short question, naming the mismatch, only when something doesn't match. Otherwise it gets out of the way and shows an approval card.

It is judged on both sides: catch the risky request AND let the normal one through. An assistant that questions everything trains people to click "yes".

Two kinds of input, one agent:
1. A typed request: "Send Meera ₹15,000 on her new number."
2. A pasted incoming message (a collect request, SMS or payment link): "What am I approving?" The agent explains in one line what it really does, checked against the records.

## How it works
1. The request comes in.
2. Gemini calls tools to look things up.
3. It decides one of three: **pay** (approval card), **ask** (one question naming the mismatch), or **stop** (clear fraud).
4. Money moves only after the user taps Approve.

## Tools (about 5)
- `search_contacts(name)`
- `payment_history(payee)`
- `resolve_upi(id_or_number)`: the registered name behind a number or UPI ID
- `get_balance()`
- `send_payment(payee, amount)`: only callable after approval, enforced in code

## Data
Fresh, synthetic and hand-made for this build. 3–4 personas, each with contacts, about 3 months of payments, bills and subscriptions, and a few planted traps:
- two contacts with the same name;
- a landlord whose UPI ID recently changed;
- a usual bill amount, so an extra zero stands out;
- a number that is registered to someone else.

No real data and no real money.

## Unbreakable (25 pts)
- **Honest mistakes:** wrong person, amount typo, a never-paid number.
- **Pressure:** "urgent, don't ask".
- **Prompt injection:** in a payee name, note or pasted SMS. Tool output is treated as data, never as instructions.
- **Tool failure:** on a timeout or garbage result, say so and never pay on a guess.
- **Hard rules in code, not the prompt:**
  - no payment without approval;
  - an amount cap;
  - the approved payee and amount must match what was shown.

## Agent design (25 pts)
- Plans: look up, then decide.
- Short memory within the session, e.g. "you confirmed this new number earlier".
- It acts: the payment lands in the mock ledger.

## UI
One page:
- a persona picker;
- chat on the left;
- that persona's records on the right, with the record that triggered a question highlighted;
- 2–3 "try this" chips per persona.

## Stack
- Python and FastAPI.
- One HTML page.
- Gemini API (key in `.env`, never on screen).

## Submission
- A public repo and README.
- A 10-second clip: a scam SMS gets caught, then a normal payment goes straight through.

## Credit
The approach comes from our research project What They Meant (github.com/nsharan2000/what-they-meant). This build's code and data are new.
