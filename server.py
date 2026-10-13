"""Minimal standard-library web server for the Executive Agents frontend."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import os

from cfo import CFOAgent
from cmo import CMOAgent
from coo import COOAgent

ROOT = Path(__file__).resolve().parent
AGENTS = {"cfo": CFOAgent, "cmo": CMOAgent, "coo": COOAgent}

class Handler(BaseHTTPRequestHandler):
    def _send(self, status, payload, content_type="application/json; charset=utf-8"):
        body = payload if isinstance(payload, bytes) else (
            json.dumps(payload).encode("utf-8") if content_type.startswith("application/json") else payload.encode("utf-8")
        )
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/status":
            self._send(200, {
                "ok": True,
                "mode": "Claude API with tool use" if os.environ.get("ANTHROPIC_API_KEY") else "Offline keyword routing",
                "model": os.environ.get("EXEC_AGENTS_MODEL", "claude-sonnet-5-5"),
                "agents": list(AGENTS.keys())
            })
        else:
            self._send(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/api/ask":
            self._send(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length > 20000:
                self._send(413, {"error": "Request too large"})
                return
            data = json.loads(self.rfile.read(length) or b"{}")
            role = str(data.get("agent", "")).lower()
            question = str(data.get("question", "")).strip()
            if role not in AGENTS:
                self._send(400, {"error": "Choose CFO, CMO, or COO."})
                return
            if not question:
                self._send(400, {"error": "Enter a question first."})
                return
            agent = AGENTS[role]()
            answer = agent.ask(question)
            self._send(200, {
                "agent": role.upper(),
                "answer": answer,
                "tools": [call.get("tool") for call in agent.calls],
                "mode": "Claude API with tool use" if os.environ.get("ANTHROPIC_API_KEY") else "Offline keyword routing"
            })
        except Exception as exc:
            self._send(500, {"error": f"Agent error: {exc}"})

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    print(f"Executive Agents UI: http://{host}:{port}")
    print("Offline mode works without extra dependencies.")
    ThreadingHTTPServer((host, port), Handler).serve_forever()
