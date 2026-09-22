import os

import psycopg

SCHEMA = """
-- Previsão congelada: gravada uma única vez, nunca atualizada.
CREATE TABLE IF NOT EXISTS accuweather_snapshot (
    icao          text        NOT NULL,
    valid_time    timestamptz NOT NULL,
    temperature_c numeric(5,1) NOT NULL,
    issued_at     timestamptz,
    fetched_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (icao, valid_time)
);

-- Previsão mais recente de cada hora (upsert a cada rodada).
CREATE TABLE IF NOT EXISTS accuweather_forecast (
    icao          text        NOT NULL,
    valid_time    timestamptz NOT NULL,
    temperature_c numeric(5,1) NOT NULL,
    issued_at     timestamptz,
    updated_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (icao, valid_time)
);

CREATE TABLE IF NOT EXISTS tomorrow_forecast (
    icao          text        NOT NULL,
    valid_time    timestamptz NOT NULL,
    temperature_c numeric(5,1) NOT NULL,
    updated_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (icao, valid_time)
);

-- Observado (METAR, sem SPECI).
CREATE TABLE IF NOT EXISTS metar_obs (
    icao          text        NOT NULL,
    obs_time      timestamptz NOT NULL,
    temperature_c integer     NOT NULL,
    raw           text        NOT NULL,
    fetched_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (icao, obs_time)
);
"""


def connect() -> psycopg.Connection:
    return psycopg.connect(os.environ["DATABASE_URL"])


def create_schema() -> None:
    with connect() as conn:
        conn.execute(SCHEMA)
