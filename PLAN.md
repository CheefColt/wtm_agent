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
One page, desktop width (about 1440px), in two halves. The layout is fixed: chat on the left, records on the right. "UPI style" changes only the look.

### Top bar (full width)
- App name "Pay Check" on the left.
- A persona picker in the middle: 3–4 avatar pills with name and city, e.g. "Priya · Bengaluru". Switching persona resets the chat and memory.
- A small "Mock data · no real money" tag on the right.

### Left: phone frame (about 400 × 820px, centred in the left half)
A UPI-style chat app inside a phone outline.

**Header**
- The persona's avatar and name.
- The balance, e.g. "₹42,310".

**Chat**
- User messages: right-aligned, in a light blue bubble.
- Agent messages: left-aligned, in a white bubble.
- Tool calls: small grey lines under the agent's turn, such as "🔍 looked up 98xxxx1234 → Rakesh Yadav". They show it acts, not just chats.

**Three card types** (cards, not plain text)
- **Approval card (pay).** Shows:
  - payee name and initials avatar;
  - UPI ID;
  - amount, in large type;
  - a note;
  - "Paid before: 6 times, last ₹15,000 on 2 Nov";
  - a big **Approve** button and a **Cancel** link.

  After Approve, it turns into a green success receipt with a ✓, a transaction ID and the time.
- **Question card (ask).** Amber border, with:
  - one sentence naming the mismatch;
  - one or two quick-reply buttons, e.g. "Yes, it's her new number" / "Cancel";
  - a "why?" link that highlights the record on the right.
- **Block card (stop).** Red border, with:
  - what the request really does, e.g. "This *takes* ₹4,999 from you";
  - the reason;
  - no pay button.

**Composer**
- A text box with a 📎 "Paste a message" toggle. That toggle switches the input to "What am I approving?" mode for an SMS, collect request or link.
- 2–3 "try this" chips above the composer for each persona, at least one clean request and one with a trap.

### Right: the account (the rest of the width)
Four stacked sections, as compact tables or cards. All read from the same data file the tools use.
1. **Contacts and saved payees:**
   - name;
   - number or UPI ID;
   - "added on" date;
   - a "changed recently" badge where it applies.
2. **Recent payments,** last 3 months:
   - date;
   - payee;
   - amount;
   - note.
3. **Bills and subscriptions:** biller, usual amount and due day.
4. **Balance and daily limit.**

**Highlight:** when the agent asks or blocks, the exact rows it used flash amber or red and scroll into view, e.g. both "Meera" contacts, or the landlord's old and new UPI IDs. The agent returns the IDs of the records it used with every decision, and the page highlights those rows.

### Look
- **Background:** light grey; white cards with 12px rounded corners.
- **Colours:**
  - one accent: UPI-like blue #0F4C81;
  - green for paid;
  - amber for ask;
  - red for block.
- **Font:** a system sans-serif; amounts in tabular numbers.
- **What to leave out:** no dark mode, no animations beyond the highlight flash and the card turning into the receipt, and no logos of real apps or banks.

## Stack
- Python and FastAPI.
- One HTML page.
- Gemini API (key in `.env`, never on screen).

## Submission
- A public repo and README.
- A 10-second clip: a scam SMS gets caught, then a normal payment goes straight through.

## Credit
The approach comes from our research project What They Meant (github.com/nsharan2000/what-they-meant). This build's code and data are new.
