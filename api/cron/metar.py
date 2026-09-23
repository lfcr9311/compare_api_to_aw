import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from weather import jobs  # noqa: E402
from weather.http import CronJob  # noqa: E402


class handler(CronJob, BaseHTTPRequestHandler):
    def run(self, params):
        return jobs.metar(backfill=params.get("backfill") == "1")
