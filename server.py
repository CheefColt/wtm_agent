"""Pay Check web app.  Run:  uvicorn server:app --port 8000"""

import secrets
from collections import OrderedDict
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
def chat(body: Chat):
    s = _get(body.session_id)
    if not s:
        return _missing()
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
