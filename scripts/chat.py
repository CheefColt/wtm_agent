"""Try the agent from the command line (uses real Gemini).

  python scripts/chat.py priya "Send Meera ₹15,000"
  python scripts/chat.py lakshmi --paste "You have received a request to RECEIVE Rs 4,999 ..."
Several messages in a row share one session; prefix a message with 'tap:' for a quick-reply tap
and use 'approve' to tap Approve on the last card.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from paycheck import agent  # noqa: E402
from paycheck.store import Session  # noqa: E402


def show(r):
    for line in r["tool_log"]:
        print("   ", line)
    print(f"  [{r['decision'].upper()}] {r['message']}  ({r['model']})")
    if r["quick_replies"]:
        print("   replies:", r["quick_replies"])
    if r["card"]:
        c = r["card"]
        print(f"   card: {c['payee_name']} {c['payee_upi']} {c['amount_display']} paid_before={c['paid_before']}"
              + (f" warning={c['warning']!r}" if c["warning"] else ""))
    print("   evidence:", r["evidence_ids"])


def main(argv):
    s = Session(argv[0])
    mode, last = "chat", None
    for msg in argv[1:]:
        if msg == "--paste":
            mode = "paste"
            continue
        if msg == "approve" and last and last["card"]:
            c = last["card"]
            print("> [Approve]", agent.approve(s, c["card_id"], c["token"], c["payee_upi"], c["amount_paise"]))
            continue
        tap = msg.startswith("tap:")
        text = msg[4:] if tap else msg
        print(">", ("[tap] " if tap else "") + ("[paste] " if mode == "paste" else "") + text)
        last = agent.handle(s, text, mode=mode, quick_reply=tap)
        show(last)
        mode = "chat"


if __name__ == "__main__":
    main(sys.argv[1:])
