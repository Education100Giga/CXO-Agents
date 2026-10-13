"""Vercel serverless health/status endpoint."""
import json
import os
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        payload = {
            "ok": True,
            "mode": "Claude API with tool use" if os.environ.get("ANTHROPIC_API_KEY") else "Offline keyword routing",
            "model": os.environ.get("EXEC_AGENTS_MODEL", "claude-sonnet-5-5"),
            "agents": ["cfo", "cmo", "coo"]
        }
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
