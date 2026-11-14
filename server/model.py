"""The AI that forms the questions.

Cloud by default (OpenRouter free open-source models), so the site works without any
particular computer being on. Set CLEARNESS_BACKEND=ollama to run on a local Ollama instead.

  OPENROUTER_API_KEY   required for the cloud backend
  CLEARNESS_MODELS     comma-separated OpenRouter model ids, tried in order (free models by default)
"""
import json
import os
import urllib.error
import urllib.request

BACKEND = os.environ.get("CLEARNESS_BACKEND", "gateway").lower()
# Vercel AI Gateway: on Vercel, the project's own OIDC identity authenticates; no API key to manage.
GATEWAY_MODELS = [m.strip() for m in os.environ.get(
    "CLEARNESS_GATEWAY_MODELS", "google/gemma-4-31b-it,google/gemini-2.5-flash-lite,openai/gpt-4o-mini").split(",") if m.strip()]
MODELS = [m.strip() for m in os.environ.get(
    "CLEARNESS_MODELS",
    "google/gemma-4-31b-it:free,google/gemma-4-26b-a4b-it:free,nvidia/nemotron-3.5-lightning:free").split(",") if m.strip()]
PREFERRED_FAMILIES = ("gemma", "llama", "qwen", "mistral", "nemotron")  # used if every listed model has been retired
_discovered = []
LOCAL_MODEL = os.environ.get("CLEARNESS_MODEL", "llama3.2")
TIMEOUT = 40


def _post(url, payload, headers):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read())


def _discover():
    """Free chat models OpenRouter offers today, from familiar families. Looked up once per process."""
    if _discovered:
        return _discovered
    try:
        with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=10) as r:
            ids = [m["id"] for m in json.loads(r.read())["data"] if m["id"].endswith(":free")]
        _discovered.extend([i for f in PREFERRED_FAMILIES for i in ids if f in i and i not in MODELS][:4])
    except Exception:
        pass
    return _discovered


def _openrouter(system, user, temperature, max_tokens):
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json",
               "X-Title": "Sitting in Clearness"}
    last = None
    for model in MODELS + _discover():  # free models are sometimes busy or retired; fall through
        try:
            r = _post("https://openrouter.ai/api/v1/chat/completions",
                      {"model": model, "temperature": temperature, "max_tokens": max_tokens,
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
                      headers)
            text = (r.get("choices") or [{}])[0].get("message", {}).get("content") or ""
            if text.strip():
                return text
            last = RuntimeError(f"{model}: empty reply")
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as e:
            last = e
    raise RuntimeError(f"no model answered ({type(last).__name__})")


def _ollama(system, user, temperature, max_tokens, json_mode):
    payload = {"model": LOCAL_MODEL, "stream": False,
               "options": {"num_ctx": 4096, "temperature": temperature, "num_predict": max_tokens},
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if json_mode:
        payload["format"] = "json"
    return _post("http://127.0.0.1:11434/api/chat", payload, {"Content-Type": "application/json"})["message"]["content"]


def _gateway_token() -> str:
    tok = os.environ.get("AI_GATEWAY_API_KEY", "")
    if not tok:
        try:
            from flask import has_request_context, request
            if has_request_context():
                tok = request.headers.get("x-vercel-oidc-token", "")
        except ImportError:
            pass
    return tok or os.environ.get("VERCEL_OIDC_TOKEN", "")


def _gateway(system, user, temperature, max_tokens):
    tok = _gateway_token()
    if not tok:
        raise RuntimeError("no AI Gateway credential (deploy on Vercel, or set AI_GATEWAY_API_KEY)")
    headers = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}
    last = None
    for model in GATEWAY_MODELS:
        try:
            r = _post("https://ai-gateway.vercel.sh/v1/chat/completions",
                      {"model": model, "temperature": temperature, "max_tokens": max_tokens,
                       "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]},
                      headers)
            text = (r.get("choices") or [{}])[0].get("message", {}).get("content") or ""
            if text.strip():
                return text
            last = RuntimeError(f"{model}: empty reply")
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as e:
            last = e
    raise RuntimeError(f"no model answered ({type(last).__name__})")


def ask(system: str, user: str, *, temperature=0.7, max_tokens=120, json_mode=False) -> str:
    if BACKEND == "ollama":
        return _ollama(system, user, temperature, max_tokens, json_mode)
    if BACKEND == "openrouter":
        return _openrouter(system, user, temperature, max_tokens)
    return _gateway(system, user, temperature, max_tokens)
