"""Talks to a local Ollama model. Never calls a cloud service, by design:
what people write here is personal, so it stays on the machine that runs this server.
The address is fixed to this machine, and Ollama's hosted "-cloud" models are refused."""
import json
import os
import urllib.request

OLLAMA_URL = "http://127.0.0.1:11434"
MODEL = os.environ.get("CLEARNESS_MODEL", "llama3.2")
if "cloud" in MODEL.lower():
    raise SystemExit(f"Refusing model {MODEL!r}: Sitting in Clearness only runs on a local model.")


def ask(system: str, user: str, *, num_ctx=4096, temperature=0.7, max_tokens=120, json_mode=False) -> str:
    payload = {"model": MODEL, "stream": False,
               "options": {"num_ctx": num_ctx, "temperature": temperature, "num_predict": max_tokens},
               "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    if json_mode:
        payload["format"] = "json"
    req = urllib.request.Request(f"{OLLAMA_URL}/api/chat", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read())["message"]["content"]
