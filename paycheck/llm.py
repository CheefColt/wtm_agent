"""Gemini client: OpenAI-compatible endpoint, per-model rate limiting, fallback on quota errors.

Limits and order come from context/MODELS.md. Usage counts are kept in memory per process.
"""

import os
import threading
import time
from collections import deque

import requests

URL = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"

# (model id, requests per minute, requests per day) in fallback order.
MODELS = [
    ("gemini-3.5-flash-lite", 15, 500),
    ("gemini-3.1-flash-lite", 15, 500),
    ("gemini-2.5-flash-lite", 10, 20),
    ("gemini-3.8-flash", 5, 20),
    ("gemini-3.6-flash", 5, 20),
    ("gemini-3-flash-preview", 5, 20),
    ("gemini-4-hydrogen", 5, 20),
    ("gemini-2.5-flash", 5, 20),
]
MAX_WAIT_S = 12      # wait this long for a free slot on a model before trying the next
TIMEOUT_S = 30


class LLMError(Exception):
    """No model could answer. The caller must fail closed."""


class _Limiter:
    def __init__(self, rpm, rpd):
        self.rpm, self.rpd = max(rpm - 1, 1), rpd - 1   # keep one spare
        self.minute = deque()
        self.day = deque()
        self.cool_until = 0.0

    def wait_time(self, now):
        if now < self.cool_until:
            return None
        while self.minute and now - self.minute[0] >= 60:
            self.minute.popleft()
        while self.day and now - self.day[0] >= 86400:
            self.day.popleft()
        if len(self.day) >= self.rpd:
            return None
        if len(self.minute) < self.rpm:
            return 0.0
        return 60 - (now - self.minute[0]) + 0.1

    def record(self, now):
        self.minute.append(now)
        self.day.append(now)


_limiters = {m: _Limiter(rpm, rpd) for m, rpm, rpd in MODELS}
_lock = threading.Lock()


def _key():
    # In the cloud session the proxy injects the real key; elsewhere set GEMINI_API_KEY.
    return os.environ.get("GEMINI_API_KEY") or "proxy-injected"


def _models():
    only = os.environ.get("GEMINI_MODELS")
    if only:
        wanted = [m.strip() for m in only.split(",") if m.strip()]
        return [m for m in wanted if m in _limiters]
    return [m for m, _, _ in MODELS]


def chat(messages, tools, temperature=0.2) -> tuple[dict, str]:
    """One completion. Returns (assistant message dict, model used). Raises LLMError."""
    errors = []
    retried = False
    for model in _models():
        lim = _limiters[model]
        with _lock:
            w = lim.wait_time(time.monotonic())
        if w is None:
            errors.append(f"{model}: out of quota")
            continue
        if w > MAX_WAIT_S:
            errors.append(f"{model}: busy")
            continue
        if w:
            time.sleep(w)
        while True:
            with _lock:
                lim.record(time.monotonic())
            try:
                r = requests.post(URL, timeout=TIMEOUT_S,
                                  headers={"Authorization": f"Bearer {_key()}"},
                                  json={"model": model, "messages": messages, "tools": tools,
                                        "tool_choice": "auto", "temperature": temperature})
            except requests.RequestException as e:
                r, err = None, type(e).__name__
            if r is not None and r.status_code == 200:
                try:
                    msg = r.json()["choices"][0]["message"]
                    if isinstance(msg, dict):
                        return msg, model
                    err = "malformed response"
                except (ValueError, KeyError, IndexError, TypeError):
                    err = "malformed response"
            elif r is not None and r.status_code == 429:
                daily = "day" in r.text.lower()
                lim.cool_until = time.monotonic() + (86400 if daily else 60)
                errors.append(f"{model}: 429")
                break                       # next model
            elif r is not None:
                err = f"HTTP {r.status_code}"
            if retried:                     # one retry in total, then fail closed
                raise LLMError("; ".join(errors + [f"{model}: {err}"]))
            retried = True
            errors.append(f"{model}: {err} (retrying)")
    raise LLMError("; ".join(errors) or "no model available")
