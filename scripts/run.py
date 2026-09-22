"""Execução local: python scripts/run.py <schema|snapshot|accuweather|tomorrow|metar|metar-backfill>"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for line in (ROOT / ".env").read_text().splitlines():
    if "=" in line and not line.startswith("#"):
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))

from weather import db, jobs  # noqa: E402

COMMANDS = {
    "schema": lambda: db.create_schema() or {"ok": True},
    "snapshot": jobs.accuweather_snapshot,
    "accuweather": jobs.accuweather,
    "tomorrow": jobs.tomorrow,
    "metar": jobs.metar,
    "metar-backfill": lambda: jobs.metar(backfill=True),
}

if len(sys.argv) != 2 or sys.argv[1] not in COMMANDS:
    sys.exit(__doc__)
print(json.dumps(COMMANDS[sys.argv[1]](), default=str, indent=2))
