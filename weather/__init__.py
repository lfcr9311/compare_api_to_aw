import logging
import sys

# Na Vercel, tudo que vai para stdout aparece em Logs do projeto.
_log = logging.getLogger("weather")
if not _log.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    _log.addHandler(_h)
    _log.setLevel(logging.INFO)
    _log.propagate = False
