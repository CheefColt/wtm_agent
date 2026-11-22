"""Loads persona data and holds one chat session's state.

The UI panel and the tools read the same persona data. Each session works on its own copy,
so payments made in a demo land in that session's ledger only.
"""

import base64
import copy
import hashlib
import hmac
import json
import os
import secrets
import time
import zlib
from datetime import datetime, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def load_persona(pid: str) -> dict:
    path = DATA / "personas" / f"{pid}.json"
    if not path.is_file() or "/" in pid or "\\" in pid:
        raise KeyError(f"unknown persona {pid!r}")
    return json.loads(path.read_text())


def list_personas() -> list[dict]:
    out = []
    order = ["priya", "sunita", "aman", "lakshmi"]
    for f in sorted((DATA / "personas").glob("*.json"), key=lambda f: (order.index(f.stem) if f.stem in order else 99, f.stem)):
        p = json.loads(f.read_text())
        out.append({k: p[k] for k in ("id", "name", "city", "initials")})
    return out


_DIRECTORY = None


def directory() -> dict:
    global _DIRECTORY
    if _DIRECTORY is None:
        _DIRECTORY = json.loads((DATA / "upi_directory.json").read_text())
    return _DIRECTORY


class Session:
    def __init__(self, persona_id: str):
        self.persona = copy.deepcopy(load_persona(persona_id))
        self.as_of = datetime.fromisoformat(self.persona["as_of"])
        self._started = time.time()
        self.cards = {}             # card_id -> card (see safety.py)
        self.blocked_handles = set()  # handles the agent stopped on; can't be paid this session
        self.confirmed = []         # what the user really confirmed (clicked), for memory
        self.fail_tools = {}        # tests only: tool name -> "timeout" | "error" | "garbage"
        self.txn_counter = 0
        self.history = []           # chat turns sent to the model (no tool dumps)
        self.last_question = None   # the agent's last 'ask', for recording quick-reply taps

    def now(self) -> datetime:
        """The fixed demo clock plus real time elapsed in this session."""
        return self.as_of + timedelta(seconds=max(time.time() - self._started, 0))

    def spent_today_paise(self) -> int:
        today = self.now().date().isoformat()
        return sum(round(p["amount"] * 100) for p in self.persona["payments"]
                   if p["date"].startswith(today) and p["status"] in ("completed", "pending"))

    # ---- stateless hosting (e.g. Vercel): the session travels as a signed blob ----
    def to_state(self) -> str:
        new = [p for p in self.persona["payments"] if p["id"].startswith("new-pay")]
        data = {"pid": self.persona["id"], "started": self._started, "balance": self.persona["balance"],
                "new_payments": new, "cards": self.cards, "blocked": sorted(self.blocked_handles),
                "confirmed": self.confirmed[-20:], "txn": self.txn_counter, "history": self.history[-16:],
                "last_question": self.last_question}
        raw = base64.urlsafe_b64encode(zlib.compress(json.dumps(data, ensure_ascii=False).encode())).decode()
        return raw + "." + _sign(raw)

    @classmethod
    def from_state(cls, state: str) -> "Session | None":
        """Rebuilds a session from to_state(). Returns None if the blob is missing, tampered or broken."""
        try:
            raw, sig = str(state).rsplit(".", 1)
            if len(raw) > 200_000 or not hmac.compare_digest(sig, _sign(raw)):
                return None
            d = json.loads(zlib.decompress(base64.urlsafe_b64decode(raw)))
            s = cls(d["pid"])
            s._started = float(d["started"])
            s.persona["balance"] = d["balance"]
            s.persona["payments"] = d["new_payments"] + s.persona["payments"]
            s.cards, s.blocked_handles = d["cards"], set(d["blocked"])
            s.confirmed, s.txn_counter = d["confirmed"], d["txn"]
            s.history, s.last_question = d["history"], d["last_question"]
            return s
        except Exception:  # noqa: BLE001 - any bad blob is just "session expired"
            return None


def _secret() -> bytes:
    if os.environ.get("SESSION_SECRET"):
        return os.environ["SESSION_SECRET"].encode()
    if os.environ.get("GEMINI_API_KEY"):   # stable across serverless instances without extra setup
        return hashlib.sha256(b"paycheck-session|" + os.environ["GEMINI_API_KEY"].encode()).digest()
    return _LOCAL_SECRET


_LOCAL_SECRET = secrets.token_bytes(32)


def _sign(raw: str) -> str:
    return hmac.new(_secret(), raw.encode(), hashlib.sha256).hexdigest()[:40]
