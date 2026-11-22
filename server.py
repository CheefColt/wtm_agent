"""Pay Check web app.  Run:  uvicorn server:app --port 8000"""

import os
import secrets
import threading
import time
from collections import OrderedDict, defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from paycheck import agent, config
from paycheck.store import Session, list_personas, load_persona

app = FastAPI(title="Pay Check")
SESSIONS: "OrderedDict[str, Session]" = OrderedDict()
MAX_SESSIONS = 300
INDEX = Path(__file__).parent / "static" / "index.html"

# Visitor limits, so a public link can't burn the Gemini quota (about 4 model calls per chat).
PER_MINUTE = int(os.environ.get("CHATS_PER_MINUTE_PER_VISITOR", "10"))
PER_DAY = int(os.environ.get("CHATS_PER_DAY", "100"))
_visits = defaultdict(deque)
_day = {"start": time.time(), "count": 0}
_rl_lock = threading.Lock()


def _visitor(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "?")


def _rate_limited(request: Request) -> JSONResponse | None:
    now = time.time()
    with _rl_lock:
        if now - _day["start"] >= 86400:
            _day.update(start=now, count=0)
        if _day["count"] >= PER_DAY:
            return JSONResponse({"error": "The demo has used today's checks. Nothing was paid."}, status_code=429)
        q = _visits[_visitor(request)]
        while q and now - q[0] >= 60:
            q.popleft()
        if len(q) >= PER_MINUTE:
            return JSONResponse({"error": "Too many messages. Wait a minute and try again. Nothing was paid."},
                                status_code=429)
        q.append(now)
        _day["count"] += 1
        if len(_visits) > 5000:
            _visits.clear()
    return None


@app.exception_handler(Exception)
async def no_stack_traces(request: Request, exc: Exception):
    return JSONResponse({"error": "Something went wrong. Nothing was paid."}, status_code=500)


def _get(sid: str) -> Session | None:
    s = SESSIONS.get(sid)
    if s:
        SESSIONS.move_to_end(sid)
    return s


def _missing():
    return JSONResponse({"error": "Session expired. Pick a persona again."}, status_code=404)


def _account(s: Session) -> dict:
    p = s.persona
    return {
        "persona": {k: p[k] for k in ("id", "name", "city", "initials", "upi_id", "phone")},
        "balance": p["balance"], "daily_limit": p["daily_limit"],
        "app_daily_cap": min(config.APP_DAILY_CAP_RUPEES, p["daily_limit"]),
        "paid_today": s.spent_today_paise() / 100,
        "contacts": p["contacts"], "payments": p["payments"], "incoming": p["incoming"],
        "bills": p["bills"], "subscriptions": p["subscriptions"], "offers": p["offers"], "orders": p["orders"],
        "try_this": p["try_this"],
    }


@app.get("/")
def index():
    return FileResponse(INDEX)


@app.get("/api/personas")
def personas():
    return list_personas()


class NewSession(BaseModel):
    persona: str


@app.post("/api/session")
def new_session(body: NewSession):
    try:
        load_persona(body.persona)
    except KeyError:
        return JSONResponse({"error": "Unknown persona."}, status_code=404)
    sid = secrets.token_urlsafe(12)
    SESSIONS[sid] = Session(body.persona)
    while len(SESSIONS) > MAX_SESSIONS:
        SESSIONS.popitem(last=False)
    return {"session_id": sid, "account": _account(SESSIONS[sid])}


class Chat(BaseModel):
    session_id: str
    text: str = ""
    mode: str = "chat"
    quick_reply: bool = False


@app.post("/api/chat")
def chat(body: Chat, request: Request):
    s = _get(body.session_id)
    if not s:
        return _missing()
    limited = _rate_limited(request)
    if limited:
        return limited
    r = agent.handle(s, body.text, mode="paste" if body.mode == "paste" else "chat", quick_reply=body.quick_reply)
    return {**r, "account": _account(s)}


class Approve(BaseModel):
    session_id: str
    card_id: str
    token: str
    payee_upi: str
    amount_paise: int


@app.post("/api/approve")
def approve(body: Approve):
    s = _get(body.session_id)
    if not s:
        return _missing()
    r = agent.approve(s, body.card_id, body.token, body.payee_upi, body.amount_paise)
    return {**r, "account": _account(s)}


class Cancel(BaseModel):
    session_id: str
    card_id: str


@app.post("/api/cancel")
def cancel(body: Cancel):
    s = _get(body.session_id)
    if not s:
        return _missing()
    return {**agent.cancel(s, body.card_id), "account": _account(s)}
