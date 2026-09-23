import json
import logging
import os
import time
import traceback
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

log = logging.getLogger(__name__)


def make_handler(job):
    """Cria o handler Vercel para um job. A Vercel envia `Authorization: Bearer $CRON_SECRET`."""

    class handler(BaseHTTPRequestHandler):
        def do_GET(self):
            log.info("chamada %s (user-agent=%s)", self.path, self.headers.get("User-Agent"))
            missing = [k for k in ("CRON_SECRET", "DATABASE_URL", "TOMORROW_API_KEY", "REDEMET_API_KEY")
                       if not os.environ.get(k)]
            if missing:
                log.error("variáveis de ambiente ausentes: %s", ", ".join(missing))
            secret = os.environ.get("CRON_SECRET")
            if not secret:
                return self._send(401, {"error": "CRON_SECRET não configurada"})
            if self.headers.get("Authorization") != f"Bearer {secret}":
                log.warning("401: header Authorization %s", "ausente" if not self.headers.get("Authorization") else "não confere")
                return self._send(401, {"error": "unauthorized"})
            params = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
            t0 = time.monotonic()
            try:
                result = job(params)
            except Exception as e:
                log.error("job falhou após %.1fs:\n%s", time.monotonic() - t0, traceback.format_exc())
                return self._send(500, {"error": repr(e)})
            status = 500 if result.get("errors") and not result.get("rows") else 200
            log.info("job terminou em %.1fs, status %d: %s", time.monotonic() - t0, status,
                     json.dumps(result, default=str))
            self._send(status, result)

        def _send(self, status, body):
            data = json.dumps(body, default=str).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)

    return handler
