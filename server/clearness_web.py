"""Sitting in Clearness: the question server.

Run:  python server/clearness_web.py      then open http://127.0.0.1:8450
It serves the page (web/index.html) and /api/committee, which accepts only
committee data and builds every prompt itself, so it can't be used as a general
AI service. The same API also serves the Vercel-hosted copy of the page (CORS).

Safe for the public internet behind Tailscale Funnel:
  - no free-form prompts; strict size limits on every field
  - per-visitor and whole-site rate limits, and a cap on calls waiting
  - one model call at a time (protects the machine's memory)
  - nothing a visitor writes is logged or stored
Public:        tailscale funnel --bg 8450     (off: tailscale funnel --https=443 off)
Tailnet only:  tailscale serve --bg 8450
"""
import os
import re
import sys
import threading
import time
from collections import defaultdict, deque

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass
HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(os.path.dirname(HERE), "web")
sys.path.insert(0, HERE)

from flask import Flask, Response, jsonify, request, send_from_directory
import clearness

HOST = os.environ.get("CLEARNESS_HOST", "127.0.0.1")
PORT = int(os.environ.get("CLEARNESS_PORT", "8450"))
PER_VISITOR = (int(os.environ.get("CLEARNESS_PER_VISITOR", "60")), 3600)
SITE_PER_DAY = int(os.environ.get("CLEARNESS_SITE_PER_DAY", "800"))
MAX_WAITING = int(os.environ.get("CLEARNESS_MAX_WAITING", "8"))
ORIGINS = [o.strip() for o in os.environ.get(
    "CLEARNESS_ORIGINS",
    "https://clearness.whiteknightlaw.org,https://sycpartners.co,https://www.sycpartners.co,https://clearness.sycpartners.co").split(",") if o.strip()]
ORIGIN_RE = re.compile(r"^https://sitting-in-clearness[a-z0-9-]*\.vercel\.app$")

_model_lock = threading.Lock()
_state_lock = threading.Lock()
_visitor_calls = defaultdict(deque)
_site_calls = deque()
_waiting = 0

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 40_000


def _visitor() -> str:
    # Behind Tailscale serve/funnel, requests come from tailscaled, which passes the real address.
    xff = request.headers.get("X-Forwarded-For", "")
    return (xff.split(",")[0].strip() or request.remote_addr or "?")[:64]


def _admit(visitor: str):
    global _waiting
    now = time.time()
    with _state_lock:
        q = _visitor_calls[visitor]
        while q and now - q[0] > PER_VISITOR[1]:
            q.popleft()
        while _site_calls and now - _site_calls[0] > 86400:
            _site_calls.popleft()
        if len(q) >= PER_VISITOR[0]:
            return 429, "You've reached this hour's limit. Please rest a while and come back."
        if len(_site_calls) >= SITE_PER_DAY:
            return 429, "The questions have been asked as often as they can be today. Please come back tomorrow."
        if _waiting >= MAX_WAITING:
            return 503, "Several people are sitting in clearness right now. Please wait a minute and try again."
        q.append(now)
        _site_calls.append(now)
        _waiting += 1
        if len(_visitor_calls) > 5000:
            for k in [k for k, v in _visitor_calls.items() if not v]:
                del _visitor_calls[k]
    return None


def _allowed_origin():
    o = request.headers.get("Origin", "")
    return o if (o in ORIGINS or ORIGIN_RE.match(o)) else None


@app.after_request
def headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    resp.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
    o = _allowed_origin()
    if o and request.path.startswith("/api/"):
        resp.headers["Access-Control-Allow-Origin"] = o
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Max-Age"] = "600"
    return resp


@app.get("/")
def index():
    return send_from_directory(WEB, "index.html")


@app.get("/config.js")
def config_js():
    return Response('window.CLEARNESS_API = "";\n', mimetype="application/javascript")


@app.get("/healthz")
def health():
    return jsonify({"ok": True})


@app.route("/api/committee", methods=["OPTIONS"])
def preflight():
    return ("", 204) if _allowed_origin() else ("", 403)


@app.post("/api/committee")
def committee():
    global _waiting
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "bad request"}), 400
    action = data.get("action")
    if action not in ("question", "reflect", "affirm", "queries"):
        return jsonify({"error": "unknown action"}), 400
    member = clearness.BY_ID.get(str(data.get("member") or ""))
    if action == "question" and not member:
        return jsonify({"error": "unknown member"}), 400
    try:
        meeting = clearness.Meeting.from_dict(data.get("meeting"))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    refusal = _admit(_visitor())
    if refusal:
        return jsonify({"error": refusal[1]}), refusal[0]
    try:
        with _model_lock:
            if action == "question":
                return jsonify({"question": meeting.question_for(member)})
            if action == "reflect":
                return jsonify({"quotes": meeting.reflect()})
            if action == "queries":
                return jsonify({"queries": meeting.queries()})
            return jsonify({"text": meeting.affirm()})
    except Exception as e:
        print(f"[clearness] model call failed: {type(e).__name__}")  # visitor text is never logged
        return jsonify({"error": "The computer that forms the questions isn't answering right now. Please try again."}), 502
    finally:
        with _state_lock:
            _waiting -= 1


if __name__ == "__main__":
    print(f"[clearness] http://{HOST}:{PORT}  (visitor text is never logged)")
    from waitress import serve
    serve(app, host=HOST, port=PORT, threads=12, connection_limit=200, channel_timeout=300)
