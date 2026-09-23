"""Cada job devolve um resumo (dict) que vira a resposta JSON do cron."""

import logging
import time
from datetime import datetime, timedelta, timezone

from . import sources
from .config import STATIONS, WINDOW_END, WINDOW_START
from .db import connect

log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _window_closed(grace: timedelta = timedelta(0)) -> bool:
    closed = _now() > WINDOW_END + grace
    if closed:
        log.info("janela encerrada, nada a fazer")
    return closed


def _accuweather(table: str, on_conflict: str) -> dict:
    summary = {"rows": {}, "errors": {}}
    with connect() as conn:
        for icao in STATIONS:
            try:
                issued_at, rows = sources.fetch_accuweather(icao)
            except Exception as e:
                log.error("%s: falha ao buscar dados: %r", icao, e)
                summary["errors"][icao] = repr(e)
                continue
            with conn.cursor() as cur:
                cur.executemany(
                    f"""INSERT INTO {table} (icao, valid_time, temperature_c, issued_at)
                        VALUES (%s, %s, %s, %s) {on_conflict}""",
                    [(icao, valid, temp, issued_at) for valid, temp in rows],
                )
            conn.commit()
            log.info("%s: %d linhas gravadas", icao, len(rows))
            summary["rows"][icao] = len(rows)
    return summary


def accuweather_snapshot() -> dict:
    """Gravação única. Se rodar de novo, não altera o que já existe."""
    return _accuweather("accuweather_snapshot", "ON CONFLICT (icao, valid_time) DO NOTHING")


def accuweather() -> dict:
    if _window_closed():
        return {"skipped": "janela encerrada"}
    return _accuweather(
        "accuweather_forecast",
        """ON CONFLICT (icao, valid_time) DO UPDATE
           SET temperature_c = EXCLUDED.temperature_c,
               issued_at = EXCLUDED.issued_at,
               updated_at = now()""",
    )


def tomorrow() -> dict:
    if _window_closed():
        return {"skipped": "janela encerrada"}
    summary = {"rows": {}, "errors": {}}
    with connect() as conn:
        for i, icao in enumerate(STATIONS):
            if i:
                time.sleep(0.5)  # limite do plano gratuito: 3 req/s
            try:
                rows = sources.fetch_tomorrow(icao)
            except Exception as e:
                log.error("%s: falha ao buscar dados: %r", icao, e)
                summary["errors"][icao] = repr(e)
                continue
            with conn.cursor() as cur:
                cur.executemany(
                    """INSERT INTO tomorrow_forecast (icao, valid_time, temperature_c)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (icao, valid_time) DO UPDATE
                       SET temperature_c = EXCLUDED.temperature_c, updated_at = now()""",
                    [(icao, valid, temp) for valid, temp in rows],
                )
            conn.commit()
            log.info("%s: %d linhas gravadas", icao, len(rows))
            summary["rows"][icao] = len(rows)
    return summary


def metar(backfill: bool = False) -> dict:
    # Folga de 2h para pegar o METAR das 23Z do dia 29.
    if _window_closed(timedelta(hours=2)):
        return {"skipped": "janela encerrada"}
    end = _now()
    start = WINDOW_START if backfill else max(WINDOW_START, end - timedelta(hours=3))
    rows = sources.fetch_metar(list(STATIONS), start, end)
    log.info("metar: %d observações de %s a %s", len(rows), start.isoformat(), end.isoformat())
    with connect() as conn, conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO metar_obs (icao, obs_time, temperature_c, raw)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (icao, obs_time) DO UPDATE
               SET temperature_c = EXCLUDED.temperature_c, raw = EXCLUDED.raw, fetched_at = now()""",
            rows,
        )
    return {"from": start.isoformat(), "to": end.isoformat(), "rows": len(rows)}
