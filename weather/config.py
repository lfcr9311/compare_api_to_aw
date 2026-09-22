from datetime import datetime, timezone

# Janela fixa de comparação: 22/09 00Z até 29/09 23Z (inclusive).
WINDOW_START = datetime(2026, 9, 22, 0, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 9, 29, 23, tzinfo=timezone.utc)

# Sempre a mesma URL; o intervalo de datas fixo cobre toda a janela.
ACCUWEATHER_URL = "https://xml.efas.aes.accuweather.com/[09/22/2026-09/29/2026]:ABAHM:{icao}"
TOMORROW_URL = "https://api.tomorrow.io/v4/weather/forecast"
REDEMET_URL = "https://api-redemet.decea.mil.br/mensagens/metar/{icaos}"

# ICAO -> (lat, lon) do aeródromo, usado na Tomorrow.io.
STATIONS = {
    "SBKP": (-23.0074, -47.1345),
    "SBPA": (-29.9944, -51.1714),
    "SBFL": (-27.6703, -48.5525),
    "SBGR": (-23.4356, -46.4731),
    "SBGL": (-22.8100, -43.2506),
    "SBCF": (-19.6244, -43.9719),
    "SBBR": (-15.8711, -47.9186),
    "SBRF": (-8.1265, -34.9236),
}


def in_window(dt: datetime) -> bool:
    return WINDOW_START <= dt <= WINDOW_END
