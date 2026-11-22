"""Loads persona data and holds one chat session's state.

The UI panel and the tools read the same persona data. Each session works on its own copy,
so payments made in a demo land in that session's ledger only.
"""

import copy
import json
import time
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
    for f in sorted((DATA / "personas").glob("*.json")):
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
        self._started = time.monotonic()
        self.cards = {}             # card_id -> card (see safety.py)
        self.blocked_handles = set()  # handles the agent stopped on; can't be paid this session
        self.confirmed = []         # what the user really confirmed (clicked), for memory
        self.fail_tools = {}        # tests only: tool name -> "timeout" | "error" | "garbage"
        self.txn_counter = 0
        self.history = []           # chat turns sent to the model (no tool dumps)
        self.last_question = None   # the agent's last 'ask', for recording quick-reply taps

    def now(self) -> datetime:
        """The fixed demo clock plus real time elapsed in this session."""
        return self.as_of + timedelta(seconds=time.monotonic() - self._started)

    def spent_today_paise(self) -> int:
        today = self.now().date().isoformat()
        return sum(round(p["amount"] * 100) for p in self.persona["payments"]
                   if p["date"].startswith(today) and p["status"] in ("completed", "pending"))
