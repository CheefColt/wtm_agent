"""Tools the agent can call. They return plain facts, never verdicts.

Design rule (context/LESSONS.md): evidence in code, judgement in the model. Each tool puts the
deciding facts in their own fields (registered_name, times_paid_before, ratio_to_usual,
upi_id_changed_on, account_age_days, request_type, ...) and lists the record IDs it used in
"ids", so the UI can highlight them.

Every value that came from data or from pasted text is data, not instructions. The agent layer
wraps tool output to say so.
"""

import re
from collections import Counter
from datetime import date, datetime
from urllib.parse import parse_qs, unquote, urlsplit

from . import config, safety
from .amounts import find_amounts, parse_amount, rupees
from .store import Session, directory
from .text import PHONE_RE, UPI_RE, clip, edit_distance, fold, has_lookalikes, norm_handle, norm_phone


# ---------------------------------------------------------------- helpers
def _tokens(s):
    return re.findall(r"[a-z0-9]+", fold(s))


def _name_matches(query, *fields):
    q = _tokens(query)
    hay = [t for f in fields for t in _tokens(f or "")]
    return bool(q) and all(any(h.startswith(t) for h in hay) for t in q)


def _days_between(d1: str, d2: datetime) -> int:
    return (d2.date() - date.fromisoformat(d1[:10])).days


def _minutes_ago(s: Session, iso: str):
    delta = s.now() - datetime.fromisoformat(iso)
    return int(delta.total_seconds() // 60) if delta.days == 0 else None


def _pay_row(s: Session, p: dict) -> dict:
    row = {"id": p["id"], "date": p["date"][:16], "payee_name": p["payee_name"],
           "payee_upi": p["payee_upi"], "amount": p["amount"], "note": p["note"], "status": p["status"]}
    m = _minutes_ago(s, p["date"])
    if m is not None:
        row["minutes_ago"] = m
    return row


def _paid(s: Session, handle: str):
    return [p for p in s.persona["payments"]
            if p["payee_upi"].lower() == handle and p["status"] == "completed"]


def _contact_handles(c):
    return {c["upi_id"].lower(), c["phone"], c.get("previous_upi_id", "").lower()} - {""}


def _known_handles(s: Session) -> set:
    hs = {p["payee_upi"].lower() for p in s.persona["payments"]}
    for c in s.persona["contacts"]:
        hs |= _contact_handles(c)
    return hs


def _stats(s: Session, handle: str) -> dict:
    past = _paid(s, handle)
    amounts = [p["amount"] for p in past]
    common = Counter(amounts).most_common(1)
    return {
        "times_paid_before": len(past),
        "last_paid": _pay_row(s, past[0]) if past else None,
        "most_common_amount": common[0][0] if common else None,
        "amount_range": [min(amounts), max(amounts)] if amounts else None,
    }


# ---------------------------------------------------------------- tools
def search_contacts(s: Session, name: str = "") -> dict:
    """Saved contacts whose name or relation matches. Also reports lookalike letters in the query."""
    out = []
    for c in s.persona["contacts"]:
        if not _name_matches(name, c["name"], c.get("relation")):
            continue
        st = _stats(s, c["upi_id"].lower())
        row = {**{k: c[k] for k in ("id", "name", "relation", "phone", "upi_id", "added_on")},
               "days_since_added": _days_between(c["added_on"], s.now()),
               "times_paid_before": st["times_paid_before"],
               "most_common_amount": st["most_common_amount"],
               "last_paid": st["last_paid"]}
        if c.get("upi_id_changed_on"):
            prev = _stats(s, c["previous_upi_id"].lower())
            row.update({"previous_upi_id": c["previous_upi_id"],
                        "upi_id_changed_on": c["upi_id_changed_on"],
                        "days_since_upi_id_change": _days_between(c["upi_id_changed_on"], s.now()),
                        "change_note": c.get("change_note", ""),
                        "times_paid_to_previous_upi_id": prev["times_paid_before"],
                        "last_paid_to_previous_upi_id": prev["last_paid"]})
        out.append(row)
    ids = [r["id"] for r in out] + [r["last_paid"]["id"] for r in out if r.get("last_paid")]
    return {"query": clip(name, 80), "query_contains_lookalike_letters": has_lookalikes(name or ""),
            "matches": out, "match_count": len(out), "ids": ids}


def payment_history(s: Session, payee: str = "", amount=None) -> dict:
    """Past payments to a payee (name, relation, UPI ID or number). Empty payee: the 10 most recent.
    With amount: also its ratio to the payee's most common amount."""
    pays = s.persona["payments"]
    if not (payee or "").strip():
        rows = [_pay_row(s, p) for p in pays[:10]]
        return {"payee": "", "recent": rows, "ids": [r["id"] for r in rows]}
    h = norm_handle(payee)
    if "@" in h or norm_phone(h):
        handles = {h} | {f"{h}@ybl"} if norm_phone(h) else {h}
    else:
        handles = {p["payee_upi"].lower() for p in pays if _name_matches(payee, p["payee_name"])}
        for c in s.persona["contacts"]:
            if _name_matches(payee, c["name"], c.get("relation")):
                handles |= _contact_handles(c)
    groups = []
    for hd in sorted(handles):
        past = [p for p in pays if p["payee_upi"].lower() == hd]
        if not past:
            continue
        st = _stats(s, hd)
        g = {"payee_name": past[0]["payee_name"], "payee_upi": hd, **st,
             "recent": [_pay_row(s, p) for p in past[:5]]}
        if amount is not None and st["most_common_amount"]:
            a = parse_amount(amount)
            if a["ok"]:
                g["asked_amount"] = a["paise"] / 100
                g["ratio_to_most_common_amount"] = round(a["paise"] / 100 / st["most_common_amount"], 2)
        groups.append(g)
    ids = [r["id"] for g in groups for r in g["recent"]]
    return {"payee": clip(payee, 80), "payees": groups, "payee_count": len(groups), "ids": ids}


def resolve_upi(s: Session, id_or_number: str) -> dict:
    """Who a UPI ID or phone number is registered to, plus how it relates to this account."""
    h = norm_handle(id_or_number or "")
    info = directory().get(h)
    res = {"handle": h, "found": bool(info), "query_contains_lookalike_letters": has_lookalikes(id_or_number or "")}
    if info:
        res.update({k: info[k] for k in ("registered_name", "kind", "verified_merchant", "account_age_days")})
    ids = []
    saved = [c for c in s.persona["contacts"] if h in (c["upi_id"].lower(), c["phone"])]
    res["saved_contact"] = [{"id": c["id"], "name": c["name"]} for c in saved]
    prev = [c for c in s.persona["contacts"] if h == c.get("previous_upi_id", "").lower()]
    res["is_previous_upi_id_of"] = [{"id": c["id"], "name": c["name"], "current_upi_id": c["upi_id"],
                                     "changed_on": c["upi_id_changed_on"]} for c in prev]
    st = _stats(s, h)
    res["times_paid_to_this_handle"] = st["times_paid_before"]
    similar = []
    for k in sorted(_known_handles(s) - {h}):
        if abs(len(k) - len(h)) <= 2 and edit_distance(k, h) <= 2:
            owner = directory().get(k, {}).get("registered_name")
            similar.append({"handle": k, "registered_name": owner, "edit_distance": edit_distance(k, h),
                            "times_paid": _stats(s, k)["times_paid_before"]})
    res["similar_handles_on_this_account"] = similar
    ids += [c["id"] for c in saved + prev]
    if st["last_paid"]:
        ids.append(st["last_paid"]["id"])
    for c in s.persona["contacts"]:
        if any(x["handle"] in _contact_handles(c) for x in similar):
            ids.append(c["id"])
    res["ids"] = ids
    return res


def get_balance(s: Session) -> dict:
    cap = min(config.APP_DAILY_CAP_RUPEES, s.persona["daily_limit"])
    spent = s.spent_today_paise() / 100
    return {"balance": s.persona["balance"], "bank_daily_limit": s.persona["daily_limit"],
            "app_daily_cap": cap, "per_payment_cap": config.PER_PAYMENT_CAP_RUPEES,
            "paid_today": spent, "can_still_pay_today": max(cap - spent, 0), "ids": ["balance"]}


def lookup_bills(s: Session, query: str = "") -> dict:
    """Bills, subscriptions and offers (e.g. trials) matching the query; empty query: all of them."""
    month = s.now().strftime("%Y-%m")
    bills = []
    for b in s.persona["bills"]:
        if query and not _name_matches(query, b["biller"], b["category"]):
            continue
        this_month = [_pay_row(s, p) for p in s.persona["payments"]
                      if p["payee_upi"].lower() == b["biller_upi"] and p["date"].startswith(month)]
        bills.append({**b, "ratio_current_to_usual": round(b["current_amount"] / b["usual_amount"], 2),
                      "payments_this_month": this_month})
    subs = []
    for x in s.persona["subscriptions"]:
        if query and not _name_matches(query, x["name"], "subscription"):
            continue
        st = _stats(s, x["merchant_upi"])
        subs.append({**x, "times_paid_before": st["times_paid_before"], "last_paid": st["last_paid"]})
    offers = []
    for o in s.persona["offers"]:
        if query and not _name_matches(query, o["merchant"], "trial offer"):
            continue
        offers.append({**o, "yearly_cost_after_trial": o["then_amount"] * 12 if o["then_frequency"] == "monthly" else None,
                       "times_paid_before": _stats(s, o["merchant_upi"])["times_paid_before"]})
    ids = ([b["id"] for b in bills] + [p["id"] for b in bills for p in b["payments_this_month"]]
           + [x["id"] for x in subs] + [o["id"] for o in offers])
    return {"query": clip(query, 80), "bills": bills, "subscriptions": subs, "offers": offers, "ids": ids}


def get_orders(s: Session, query: str = "") -> dict:
    """Shopping orders matching merchant, item or order number; empty query: all."""
    out = []
    for o in s.persona["orders"]:
        if query and not _name_matches(query, o["merchant"], o["item"], o["order_no"]):
            continue
        pays = [_pay_row(s, p) for p in s.persona["payments"] if o["order_no"] in p["note"]]
        out.append({**o, "payments_for_this_order": pays})
    ids = [o["id"] for o in out] + [p["id"] for o in out for p in o["payments_for_this_order"]]
    return {"query": clip(query, 80), "orders": out, "ids": ids}


def incoming_payments(s: Session, sender: str = "") -> dict:
    """Money received, newest first; optionally only from one sender (name, UPI ID or number)."""
    rows = []
    for x in sorted(s.persona["incoming"], key=lambda x: x["date"], reverse=True):
        fh = x["from_upi"].lower()
        if sender and not (_name_matches(sender, x["from_name"]) or norm_handle(sender) in (fh, fh.split("@")[0])):
            continue
        rows.append({**x, "minutes_ago": _minutes_ago(s, x["date"]),
                     "sender_is_saved_contact": any(fh in _contact_handles(c) for c in s.persona["contacts"]),
                     "sender_account_age_days": directory().get(fh, {}).get("account_age_days")})
    rows = rows[:10]
    return {"sender": clip(sender, 80), "incoming": rows, "ids": [r["id"] for r in rows]}


def decode_qr(s: Session, text: str) -> dict:
    """Reads a upi://pay link (what a UPI QR code contains)."""
    m = re.search(r"upi://pay\?[^\s\"'<>]+", text or "", re.I)
    if not m:
        return {"is_upi_link": False, "ids": []}
    q = parse_qs(urlsplit(m.group(0)).query)
    pa = unquote(q.get("pa", [""])[0])
    pn = unquote(q.get("pn", [""])[0])
    am = q.get("am", [None])[0]
    r = resolve_upi(s, pa) if pa else {"found": False, "ids": []}
    named = [c for c in s.persona["contacts"] if pn and fold(c["name"]) == fold(pn)]
    out = {
        "is_upi_link": True, "payee_upi": norm_handle(pa), "name_written_in_qr": clip(pn, 80),
        "amount_in_qr": am, "note_in_qr": clip(unquote(q.get("tn", [""])[0]), 80),
        "registered_name": r.get("registered_name"), "found_in_directory": r["found"],
        "kind": r.get("kind"), "verified_merchant": r.get("verified_merchant"),
        "account_age_days": r.get("account_age_days"),
        "name_in_qr_equals_registered_name": bool(pn) and fold(pn) == fold(r.get("registered_name") or ""),
        "times_paid_to_this_handle": r.get("times_paid_to_this_handle", 0),
        "saved_contacts_with_the_name_in_qr": [{"id": c["id"], "name": c["name"], "upi_id": c["upi_id"]}
                                                for c in named],
    }
    out["ids"] = r["ids"] + [c["id"] for c in named]
    return out


COLLECT = re.compile(r"request(ed)? to (receive|pay)|collect request|requested (money|payment)|"
                     r"approve (the |this )?(payment )?request|money request", re.I)
RETURN = re.compile(r"by mistake|wrongly sent|sent (you )?.{0,20}wrong|return|refund|send (it )?back", re.I)


def read_message(s: Session, text: str) -> dict:
    """Facts about a pasted SMS, payment request, link or chat message."""
    t = (text or "")[:4000]
    low = t.lower()
    if "upi://" in low:
        kind = "upi_link"
    elif COLLECT.search(t):
        kind = "collect_request"
    elif re.search(r"\bcredited\b|\breceived rs|\breceived ₹", low):
        kind = "credit_notice"
    elif re.search(r"\bdebited\b", low):
        kind = "debit_notice"
    elif RETURN.search(t):
        kind = "return_request"
    else:
        kind = "other"
    handles = sorted({h.lower() for h in UPI_RE.findall(t)})
    phones = sorted({norm_phone(m.group(1)) for m in PHONE_RE.finditer(t)} - {None})
    res = {
        "request_type": kind,
        "length": len(text or ""),
        "asks_for_upi_pin": bool(re.search(r"\bpin\b", low)),
        "mentions_kyc": "kyc" in low,
        "links": re.findall(r"https?://[^\s]+", t)[:5],
        "amounts_in_message": [a / 100 for a in find_amounts(t)],
        "urgency_words": sorted({w for w in ("urgent", "immediately", "hospital", "blocked", "expire",
                                             "suspend", "last chance", "police") if w in low}),
        "handles_in_message": [resolve_upi(s, h) for h in handles + phones][:5],
    }
    if res["asks_for_upi_pin"]:
        res["upi_fact"] = "In UPI, entering a PIN always sends money out; receiving money never needs a PIN."
    if kind == "upi_link":
        res["qr"] = decode_qr(s, t)
    ids = [i for h in res["handles_in_message"] for i in h["ids"]]
    amounts = set(res["amounts_in_message"])
    if kind == "credit_notice":
        match = [x for x in s.persona["incoming"]
                 if x["amount"] in amounts and (not handles or x["from_upi"].lower() in handles)]
        res["matching_incoming_credits"] = match
        ids += [x["id"] for x in match]
    if kind == "return_request":
        today = s.now().date().isoformat()
        credits = []
        for x in s.persona["incoming"]:
            if x["date"].startswith(today):
                fh = x["from_upi"].lower()
                credits.append({**x, "minutes_ago": _minutes_ago(s, x["date"]),
                                "sender_is_saved_contact": any(fh in _contact_handles(c) for c in s.persona["contacts"]),
                                "sender_account_age_days": directory().get(fh, {}).get("account_age_days"),
                                "return_to_handle_is_this_sender": [h == fh or h == fh.split("@")[0] for h in handles + phones]})
        res["incoming_credits_today"] = credits
        res["return_to_handles"] = handles + phones
        ids += [x["id"] for x in credits]
    res["ids"] = ids + (res["qr"]["ids"] if "qr" in res else [])
    return res


def propose_payment(s: Session, payee_upi: str, amount, note: str = "", warning: str = "") -> dict:
    """Puts an approval card in front of the user. It does not pay: only the user's Approve click can."""
    r = safety.create_card(s, payee_upi, amount, note, warning)
    if not r["ok"]:
        return {"card_created": False, "reason": r["reason"], "ids": []}
    return {"card_created": True, "card": r["card"], "_ui_token": r["token"], "ids": []}


# ---------------------------------------------------------------- registry
TOOLS = {
    "search_contacts": (search_contacts, {"name": "string"}),
    "payment_history": (payment_history, {"payee": "string", "amount": "string"}),
    "resolve_upi": (resolve_upi, {"id_or_number": "string"}),
    "get_balance": (get_balance, {}),
    "lookup_bills": (lookup_bills, {"query": "string"}),
    "get_orders": (get_orders, {"query": "string"}),
    "read_message": (read_message, {"text": "string"}),
    "incoming_payments": (incoming_payments, {"sender": "string"}),
    "decode_qr": (decode_qr, {"text": "string"}),
    "propose_payment": (propose_payment, {"payee_upi": "string", "amount": "string",
                                          "note": "string", "warning": "string"}),
}


def call_tool(s: Session, name: str, args) -> dict:
    """Runs one tool. Never raises: bad names, bad args and failures come back as {'ok': False}."""
    if name not in TOOLS:
        return {"ok": False, "error": f"unknown tool {clip(name, 40)!r}"}
    fn, params = TOOLS[name]
    if not isinstance(args, dict):
        return {"ok": False, "error": "arguments must be an object"}
    clean = {k: (v if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v))
             for k, v in args.items() if k in params and v is not None}
    failure = s.fail_tools.get(name)
    if failure == "timeout":
        return {"ok": False, "error": f"{name} timed out"}
    if failure == "error":
        return {"ok": False, "error": f"{name} failed"}
    try:
        out = fn(s, **clean)
    except Exception as e:  # noqa: BLE001 - a tool bug must not crash the chat
        return {"ok": False, "error": f"{name} failed ({type(e).__name__})"}
    if failure == "garbage":
        return {"ok": True, "result": "\x00{{<<garbled>>}}", "ids": []}
    return {"ok": True, **out}
