import json
import os
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse


def make_handler(job):
    """Cria o handler Vercel para um job. A Vercel envia `Authorization: Bearer $CRON_SECRET`."""

    class handler(BaseHTTPRequestHandler):
        def do_GET(self):
            secret = os.environ.get("CRON_SECRET")
            if not secret or self.headers.get("Authorization") != f"Bearer {secret}":
                return self._send(401, {"error": "unauthorized"})
            params = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
            try:
                result = job(params)
            except Exception as e:
                return self._send(500, {"error": repr(e)})
            status = 500 if result.get("errors") and not result.get("rows") else 200
            self._send(status, result)

        def _send(self, status, body):
            data = json.dumps(body, default=str).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)

    return handler
