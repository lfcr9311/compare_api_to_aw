"""Busca e interpreta os dados de cada fonte. Todos os horários em UTC."""

import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from .config import ACCUWEATHER_URL, REDEMET_URL, STATIONS, TOMORROW_URL, in_window


def _get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "compare-api-to-aw/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_accuweather(icao: str) -> tuple[datetime | None, list[tuple[datetime, float]]]:
    """Retorna (hora de emissão, [(hora prevista, temperatura °C)]) dentro da janela."""
    root = ET.fromstring(_get(ACCUWEATHER_URL.format(icao=icao)))

    issued_at = None
    created = root.findtext("CreatedDate")
    if created:
        issued_at = datetime.fromisoformat(created).replace(tzinfo=timezone.utc)

    rows = []
    for period in root.iter("Period"):
        # Formato: "2026-09-22 01:00 GMT"
        when = period.findtext("Time_of_Weather", "").replace(" GMT", "")
        temp = period.findtext("Hourly_Temperature")
        if not when or temp is None:
            continue
        valid = datetime.strptime(when, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        if in_window(valid):
            rows.append((valid, float(temp)))
    return issued_at, rows


def fetch_tomorrow(icao: str) -> list[tuple[datetime, float]]:
    lat, lon = STATIONS[icao]
    query = urllib.parse.urlencode({
        "location": f"{lat},{lon}",
        "fields": "temperature",
        "timesteps": "1h",
        "units": "metric",
        "apikey": os.environ["TOMORROW_API_KEY"],
    })
    data = json.loads(_get(f"{TOMORROW_URL}?{query}"))

    rows = []
    for item in data["timelines"]["hourly"]:
        valid = datetime.fromisoformat(item["time"].replace("Z", "+00:00"))
        temp = item["values"].get("temperature")
        if temp is not None and in_window(valid):
            rows.append((valid, round(float(temp), 1)))
    return rows


_TIME_RE = re.compile(r"^(\d{2})(\d{2})(\d{2})Z$")
_TEMP_RE = re.compile(r"^(M?\d{2})/(M?\d{2})?$")


def parse_metar(mens: str, reference: datetime) -> tuple[datetime, int] | None:
    """Extrai (hora da observação, temperatura) de um METAR. Ignora SPECI.

    `reference` fornece ano/mês, já que o METAR só traz dia/hora/minuto.
    """
    text = mens.strip().rstrip("=").strip()
    if not text.startswith("METAR"):
        return None

    obs_time = temp = None
    for token in text.split():
        if obs_time is None and (m := _TIME_RE.match(token)):
            day, hour, minute = map(int, m.groups())
            year, month = reference.year, reference.month
            if day > reference.day + 1:  # virada de mês (METAR do fim do mês anterior)
                month -= 1
                if month == 0:
                    year, month = year - 1, 12
            obs_time = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
        elif temp is None and (m := _TEMP_RE.match(token)):
            temp = int(m.group(1).replace("M", "-"))
    if obs_time is None or temp is None:
        return None
    return obs_time, temp


def fetch_metar(icaos: list[str], start: datetime, end: datetime) -> list[tuple[str, datetime, int, str]]:
    """Retorna [(icao, hora da observação, temperatura, mensagem)] entre start e end."""
    base = REDEMET_URL.format(icaos=",".join(icaos))
    rows, page = [], 1
    while True:
        query = urllib.parse.urlencode({
            "api_key": os.environ["REDEMET_API_KEY"],
            "data_ini": start.strftime("%Y%m%d%H"),
            "data_fim": end.strftime("%Y%m%d%H"),
            "page": page,
        })
        payload = json.loads(_get(f"{base}?{query}"))
        data = payload.get("data") or {}
        for item in data.get("data", []):
            reference = datetime.strptime(item["validade_inicial"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            parsed = parse_metar(item["mens"], reference)
            if parsed and in_window(parsed[0]):
                rows.append((item["id_localidade"], parsed[0], parsed[1], item["mens"].strip()))
        if page >= int(data.get("last_page") or 1):
            break
        page += 1
    return rows
