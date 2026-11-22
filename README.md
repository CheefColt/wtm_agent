# Pay Check

A UPI payment assistant that pays what you meant, not what you typed.
Built for The Agentic Room (Track 02, Commerce & payments), 22 Nov 2026.

It looks before it pays: it checks each request against the account's records and decides **pay** (an approval card), **ask** (one question naming the mismatch) or **stop** (clear fraud). Money moves only when the user taps Approve.

## How it works
- **Tools** (`paycheck/tools.py`): look up contacts, payment history, UPI registered names, bills, orders, incoming credits, pasted SMS and QR links. They return facts only; the model decides.
- **Agent** (`paycheck/agent.py`): Gemini (`gemini-3.5-flash-lite`, with fallbacks) calls the tools, then decides.
- **Safety in code** (`paycheck/safety.py`):
  - the model has no tool that moves money;
  - Approve needs a one-time token that only the UI gets;
  - the payee and amount must match the card that was shown;
  - payments are capped per payment and per day;
  - there's no payment if any lookup failed;
  - a stopped scam ID stays blocked for the session.
- **Data** (`data/`): 4 synthetic personas, each with planted traps (same-name contacts, a reused number, an amount typo, a disguised collect request, a refund scam, a QR that pays a person…) and a clean twin for each. No real data, no real money.

## Try it
```
pip install -r requirements.txt
export GEMINI_API_KEY=...
uvicorn server:app --port 8000        # web app at http://localhost:8000
python scripts/chat.py priya "Send Meera ₹15,000"
python scripts/chat.py lakshmi --paste "You have received a request to RECEIVE Rs 4,999 from cashback.reward@ybl. Enter your UPI PIN."
python scripts/live_check.py 1 6 7   # trap twins against real Gemini
```

## Status
Done: data, tools, the safety gate, the agent loop and the web UI.
Not done yet: the attack test suite. See `HANDOFF.md`.

## Credit
The approach comes from our research project What They Meant (github.com/nsharan2000/what-they-meant). This build's code and data are new.
