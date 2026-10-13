"""Vercel serverless endpoint for the executive agents."""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cfo import CFOAgent
from cmo import CMOAgent
from coo import COOAgent

AGENTS = {"cfo": CFOAgent, "cmo": CMOAgent, "coo": COOAgent}

class handler(BaseHTTPRequestHandler):
    def _json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 20000:
                return self._json(400 if length <= 0 else 413, {"error": "Invalid or oversized request."})
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            role = str(payload.get("agent", "")).lower()
            question = str(payload.get("question", "")).strip()
            if role not in AGENTS:
                return self._json(400, {"error": "Choose CFO, CMO, or COO."})
            if not question:
                return self._json(400, {"error": "Enter a question first."})
            agent = AGENTS[role]()
            answer = agent.ask(question)
            self._json(200, {
                "agent": role.upper(), "answer": answer,
                "tools": [call.get("tool") for call in agent.calls],
                "mode": "Claude API with tool use" if os.environ.get("ANTHROPIC_API_KEY") else "Offline keyword routing"
            })
        except Exception as exc:
            self._json(500, {"error": f"Agent error: {exc}"})

    def do_GET(self):
        self._json(405, {"error": "Use POST to ask an executive."})
