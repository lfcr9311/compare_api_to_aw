import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from weather import jobs  # noqa: E402
from weather.http import make_handler  # noqa: E402

handler = make_handler(lambda params: jobs.tomorrow())
