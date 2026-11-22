"""Vercel entry point: serves the FastAPI app from server.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from server import app as _app  # noqa: E402

PREFIX = "/api/index"


async def app(scope, receive, send):
    # If Vercel hands us the function's own path instead of the visitor's, map it back.
    if scope.get("type") in ("http", "websocket"):
        path = scope.get("path", "/")
        if path == PREFIX or path.startswith(PREFIX + "/"):
            scope = dict(scope, path=path[len(PREFIX):] or "/", raw_path=None)
    await _app(scope, receive, send)
