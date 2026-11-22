"""The payment gate. Money moves only through approve(), never on the model's word.

Rules enforced here (not in the prompt):
- A card can be created only for a payee the UPI directory knows, with an amount parsed in code,
  within the per-payment cap, the daily cap (all of today's payments count) and the balance.
- A new card voids every earlier open card, so changing the payee or amount needs a fresh card.
- approve() needs the card's one-time token, which goes only to the UI, never to the model.
- The payee and amount the UI showed must equal the card exactly.
- Handles the agent stopped on stay blocked for the rest of the session.
"""

import hmac
import secrets

from . import config
from .amounts import parse_amount, rupees
from .store import Session, directory
from .text import clip, norm_handle


def _paise(p: dict) -> int:
    return round(p["amount"] * 100)


def _refuse(reason: str) -> dict:
    return {"ok": False, "reason": reason}


def _limits_check(s: Session, paise: int) -> str | None:
    if paise > config.PER_PAYMENT_CAP_RUPEES * 100:
        return f"amount is above the per-payment cap of {rupees(config.PER_PAYMENT_CAP_RUPEES * 100)}"
    cap = min(config.APP_DAILY_CAP_RUPEES, s.persona["daily_limit"]) * 100
    spent = s.spent_today_paise()
    if spent + paise > cap:
        return (f"daily cap is {rupees(cap)}; already paid today {rupees(spent)}, "
                f"so at most {rupees(max(cap - spent, 0))} more")
    if paise > s.persona["balance"] * 100:
        return f"balance is {rupees(s.persona['balance'] * 100)}"
    return None


def create_card(s: Session, payee: str, amount, note: str = "", warning: str = "") -> dict:
    """Returns {'ok': True, 'card': <public card>, 'token': str} or {'ok': False, 'reason': str}.
    The caller must hand 'token' to the UI only."""
    handle = norm_handle(str(payee or ""))
    info = directory().get(handle)
    if not info:
        return _refuse(f"payee '{clip(payee, 80)}' is not found in the UPI directory")
    if handle in s.blocked_handles:
        return _refuse("this payee was blocked earlier in this session")
    if handle in (s.persona["upi_id"].lower(), s.persona["phone"]):
        return _refuse("payee is the user's own account")
    amt = parse_amount(amount)
    if not amt["ok"]:
        return _refuse(f"amount unclear: {amt['reason']}")
    why = _limits_check(s, amt["paise"])
    if why:
        return _refuse(why)

    for c in s.cards.values():       # any change voids earlier approvals
        if c["status"] == "open":
            c["status"] = "voided"

    past = [p for p in s.persona["payments"]
            if p["payee_upi"].lower() == handle and p["status"] == "completed"]
    card_id = "card_" + secrets.token_hex(4)
    card = {
        "card_id": card_id,
        "payee_name": info["registered_name"],
        "payee_upi": handle,
        "amount_paise": amt["paise"],
        "amount_display": amt["display"],
        "note": clip(note, config.MAX_NOTE_CHARS),
        "warning": clip(warning, config.MAX_WARNING_CHARS),
        "paid_before": {
            "times": len(past),
            "last_amount_display": rupees(_paise(past[0])) if past else None,
            "last_date": past[0]["date"][:10] if past else None,
        },
        "status": "open",
    }
    s.cards[card_id] = {**card, "_token": secrets.token_urlsafe(16)}
    return {"ok": True, "card": card, "token": s.cards[card_id]["_token"]}


def cancel(s: Session, card_id: str) -> dict:
    c = s.cards.get(card_id)
    if c and c["status"] == "open":
        c["status"] = "cancelled"
    return {"ok": True}


def approve(s: Session, card_id: str, token: str, shown_payee_upi: str, shown_amount_paise) -> dict:
    """Called only from the UI's Approve click. Returns a receipt or a refusal; never raises."""
    c = s.cards.get(str(card_id))
    if not c:
        return _refuse("unknown card")
    if c["status"] != "open":
        return _refuse(f"card is {c['status']}")
    if not isinstance(token, str) or not hmac.compare_digest(token, c["_token"]):
        return _refuse("approval token is missing or wrong")
    if norm_handle(str(shown_payee_upi)) != c["payee_upi"] or shown_amount_paise != c["amount_paise"]:
        c["status"] = "voided"
        return _refuse("the payee or amount differs from the card that was shown")
    if c["payee_upi"] in s.blocked_handles:
        c["status"] = "voided"
        return _refuse("this payee was blocked earlier in this session")
    why = _limits_check(s, c["amount_paise"])
    if why:
        c["status"] = "voided"
        return _refuse(why)
    c["status"] = "approved"          # single use, set before money moves
    return _send_payment(s, c)


def _send_payment(s: Session, c: dict) -> dict:
    """Private. Only approve() calls this, after every check above."""
    s.txn_counter += 1
    now = s.now()
    txn = f"PC{now:%y%m%d}{s.txn_counter:05d}"
    amount = c["amount_paise"] / 100
    amount = int(amount) if amount == int(amount) else amount
    s.persona["payments"].insert(0, {
        "id": f"new-pay{s.txn_counter}", "date": now.isoformat(timespec="seconds"),
        "payee_name": c["payee_name"], "payee_upi": c["payee_upi"], "amount": amount,
        "note": c["note"], "status": "completed", "txn_id": txn,
    })
    s.persona["balance"] = round(s.persona["balance"] - amount, 2)
    return {"ok": True, "receipt": {"txn_id": txn, "time": now.isoformat(timespec="seconds"),
                                    "payee_name": c["payee_name"], "payee_upi": c["payee_upi"],
                                    "amount_display": c["amount_display"]}}
