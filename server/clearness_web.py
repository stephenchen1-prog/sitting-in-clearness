"""Sitting in Clearness: the question server.

In production this runs on Vercel as the function api/committee.py (see vercel.json).
To run it yourself:  python server/clearness_web.py   then open http://127.0.0.1:8450

/api/committee accepts only committee data and builds every prompt itself, so it
can't be used as a general AI service:
  - no free-form prompts; strict size limits on every field
  - per-visitor and whole-site rate limits, and a cap on calls in flight
  - nothing a visitor writes is logged or stored by this code
"""
import ipaddress
import os
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
    "https://clearness.whiteknightlaw.org,https://sycpartners.co,https://www.sycpartners.co,https://clearness.sycpartners.co,"
    "https://nimble-gorge-v0gdavi.tmp.now").split(",") if o.strip()]
PER_VISITOR_INFLIGHT = 2

_model_lock = threading.Lock()
_state_lock = threading.Lock()
_visitor_calls = defaultdict(deque)
_inflight = defaultdict(int)
_site_calls = deque()
_waiting = 0

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 40_000


def _visitor() -> str:
    """On Vercel, use the address Vercel's edge sets (x-real-ip). Elsewhere, trust
    X-Forwarded-For only from a local proxy (tailscaled), and only its last entry.
    Group IPv6 users by /64."""
    ra = request.remote_addr or "?"
    if os.environ.get("VERCEL"):
        ip = request.headers.get("x-real-ip") or ra
    elif ra not in ("127.0.0.1", "::1"):
        return ra[:64]
    else:
        ip = request.headers.get("X-Forwarded-For", "").split(",")[-1].strip() or ra
    if ":" in ip:
        try:
            ip = str(ipaddress.ip_network(ip + "/64", strict=False).network_address)
        except ValueError:
            pass
    return ip[:64]


def _admit(visitor: str):
    global _waiting
    now = time.time()
    with _state_lock:
        if _inflight[visitor] >= PER_VISITOR_INFLIGHT:
            return 429, "One question at a time, please. The last one is still forming."
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
        _inflight[visitor] += 1
        if len(_visitor_calls) > 5000:
            for k in [k for k, v in _visitor_calls.items() if not v]:
                del _visitor_calls[k]
    return None


def _allowed_origin():
    o = request.headers.get("Origin", "")
    return o if o in ORIGINS else None


@app.after_request
def headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Cache-Control"] = "no-store"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    resp.headers["Strict-Transport-Security"] = "max-age=31536000"
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
    try:
        data = request.get_json(silent=True)
    except (ValueError, RecursionError):
        data = None
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
    except (ValueError, TypeError, RecursionError):
        return jsonify({"error": "bad meeting data"}), 400

    visitor = _visitor()
    refusal = _admit(visitor)
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
        # No AI reachable: fall back to hand-written open questions so the sitting can continue.
        print(f"[clearness] model call failed, using fallback: {type(e).__name__}")  # visitor text is never logged
        if action == "question":
            return jsonify({"question": clearness.fallback_question(meeting, member), "fallback": True})
        if action == "reflect":
            return jsonify({"quotes": clearness.fallback_reflect(meeting), "fallback": True})
        if action == "queries":
            return jsonify({"queries": clearness.fallback_queries(meeting), "fallback": True})
        return jsonify({"text": None, "fallback": True})
    finally:
        with _state_lock:
            _waiting -= 1
            _inflight[visitor] -= 1
            if _inflight[visitor] <= 0:
                del _inflight[visitor]


if __name__ == "__main__":
    print(f"[clearness] http://{HOST}:{PORT}  (visitor text is never logged)")
    from waitress import serve
    serve(app, host=HOST, port=PORT, threads=12, connection_limit=100, channel_timeout=60,
          max_request_body_size=65536)
