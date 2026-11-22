"""Amount parsing in code. If an amount is unclear, say so; never guess."""

import re
from decimal import Decimal, InvalidOperation

WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}
SCALES = {"hundred": 100, "thousand": 1_000, "hazar": 1_000, "hazaar": 1_000, "k": 1_000,
          "lakh": 100_000, "lakhs": 100_000, "lac": 100_000, "lacs": 100_000, "l": 100_000,
          "crore": 10_000_000, "crores": 10_000_000, "cr": 10_000_000}
MAX_RUPEES = 10_000_000  # 1 crore; anything above is not a UPI payment


def fail(reason):
    return {"ok": False, "reason": reason}


def ok(paise):
    return {"ok": True, "paise": paise, "display": rupees(paise)}


def rupees(paise: int) -> str:
    """Indian grouping: 150000000 paise -> '₹15,00,000'."""
    r, p = divmod(int(paise), 100)
    s = str(r)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        head = re.sub(r"(\d)(?=(\d\d)+$)", r"\1,", head)
        s = f"{head},{tail}"
    return f"₹{s}" + (f".{p:02d}" if p else "")


def _words(tokens):
    total, chunk = 0, 0
    for t in tokens:
        if t in WORDS:
            chunk += WORDS[t]
        elif t == "hundred":
            chunk = (chunk or 1) * 100
        elif t in SCALES:
            total += (chunk or 1) * SCALES[t]
            chunk = 0
        elif t != "and":
            return None
    return total + chunk


def parse_amount(value) -> dict:
    """Returns {'ok': True, 'paise': int, 'display': str} or {'ok': False, 'reason': str}."""
    if isinstance(value, bool) or value is None:
        return fail("no amount given")
    if isinstance(value, (int, float)):
        value = repr(value) if isinstance(value, float) else str(value)
    s = str(value).strip().lower()
    if not s or len(s) > 40:
        return fail("amount missing or too long")
    s = re.sub(r"(₹|\brs\.?|\binr\b|\brupees?\b|/-)", " ", s)
    s = " ".join(s.split())
    if s.startswith("-") or "minus" in s:
        return fail("amount is negative")

    m = re.fullmatch(r"(\d[\d,]*(?:\.\d+)?)\s*([a-z]+)?", s)
    if m:
        num, unit = m.group(1), m.group(2)
        if "," in num and not re.fullmatch(r"\d{1,3}(,\d{2})*,\d{3}(\.\d+)?|\d{1,3}(,\d{3})+(\.\d+)?", num):
            return fail(f"unclear comma placement in '{value}'")
        num = num.replace(",", "")
        try:
            d = Decimal(num)
        except InvalidOperation:
            return fail(f"can't read '{value}' as an amount")
        if unit:
            if unit not in SCALES:
                return fail(f"unknown unit '{unit}'")
            d *= SCALES[unit]
        elif "." in num and len(num.split(".")[1]) > 2:
            return fail(f"more than 2 decimal places in '{value}'")
        paise = d * 100
        if paise != paise.to_integral_value():
            return fail(f"amount '{value}' has fractions of a paisa")
        paise = int(paise)
    else:
        n = _words(re.findall(r"[a-z]+", s.replace("-", " ")))
        if n is None or re.search(r"\d", s):
            return fail(f"can't read '{value}' as one amount")
        paise = n * 100

    if paise <= 0:
        return fail("amount must be more than zero")
    if paise > MAX_RUPEES * 100:
        return fail("amount is above ₹1 crore")
    return ok(paise)


def find_amounts(text: str) -> list[int]:
    """All rupee amounts written with digits in a pasted message, in paise."""
    out = []
    for m in re.finditer(r"(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d{1,2})?)", text, re.I):
        r = parse_amount(m.group(1))
        if r["ok"]:
            out.append(r["paise"])
    return out
