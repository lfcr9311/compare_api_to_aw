import json
import logging
import os
import time
import traceback
from urllib.parse import parse_qs, urlparse

log = logging.getLogger(__name__)


class CronJob:
    """Mixin dos handlers Vercel (sem autenticação). Subclasses implementam `run(params)`.

    A Vercel só reconhece a função se o arquivo em api/ definir no topo
    `class handler(CronJob, BaseHTTPRequestHandler)`.
    """

    def run(self, params: dict) -> dict:
        raise NotImplementedError

    def do_GET(self):
        log.info("chamada %s (user-agent=%s)", self.path, self.headers.get("User-Agent"))
        missing = [k for k in ("DATABASE_URL", "TOMORROW_API_KEY", "REDEMET_API_KEY")
                   if not os.environ.get(k)]
        if missing:
            log.error("variáveis de ambiente ausentes: %s", ", ".join(missing))
        params = {k: v[0] for k, v in parse_qs(urlparse(self.path).query).items()}
        t0 = time.monotonic()
        try:
            result = self.run(params)
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
