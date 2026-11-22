"""Small text helpers: normalising names, phone numbers and UPI IDs."""

import re
import unicodedata

# Letters from other scripts that look like Latin ones (e.g. Cyrillic "е" in "Меera").
LOOKALIKES = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i",
    "ј": "j", "ѕ": "s", "к": "k", "м": "m", "т": "t", "н": "h", "в": "b",
    "А": "A", "Е": "E", "О": "O", "Р": "P", "С": "C", "У": "Y", "Х": "X", "І": "I",
    "К": "K", "М": "M", "Т": "T", "Н": "H", "В": "B",
    "α": "a", "ο": "o", "ρ": "p", "ε": "e", "ι": "i", "κ": "k", "ν": "v",
    "Α": "A", "Ο": "O", "Ρ": "P", "Ε": "E", "Ι": "I", "Κ": "K", "Μ": "M", "Τ": "T",
})

UPI_RE = re.compile(r"[a-z0-9][a-z0-9._-]{1,63}@[a-z][a-z0-9]{1,31}", re.I)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{4}[\s-]?\d{5})(?!\d)")


def has_lookalikes(s: str) -> bool:
    s = unicodedata.normalize("NFKC", s)
    return s.translate(LOOKALIKES) != s


def fold(s: str) -> str:
    """Lowercase, NFKC, map lookalike letters to Latin, drop zero-width and extra spaces."""
    s = unicodedata.normalize("NFKC", s or "").translate(LOOKALIKES)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Cf")
    return " ".join(s.lower().split())


def norm_phone(s: str) -> str | None:
    digits = re.sub(r"\D", "", s or "")
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    return digits if len(digits) == 10 and digits[0] in "6789" else None


def norm_handle(s: str) -> str:
    """A UPI ID (lowercased) or a bare 10-digit phone number."""
    s = fold(s).strip()
    if "@" in s:
        return s.replace(" ", "")
    return norm_phone(s) or s


def edit_distance(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def clip(s, n: int) -> str:
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"
