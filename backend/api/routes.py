"""FastAPI backend for the dashboard: hero stats, profit-over-time graph
data, and filter options, all computed from the local SQLite database.

Run with: uvicorn api.routes:app --port 8001
(avoid --reload here — it's been unreliable on Windows in this project;
restart the process manually after editing backend code)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from db.importer import get_connection
from replay.builder import get_hand_replay
from stats.calculators import HandFilters, compute_hero_stats, filter_options, hero_profit_series, list_hero_hands
from stats.leak_finder import find_leaks

DB_PATH = str(Path(__file__).resolve().parent.parent / "poker.db")

app = FastAPI(title="Poker Hand Tracker API")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://localhost:\d+",
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _connect():
    return get_connection(DB_PATH)


def _filters_from_query(
    date_from: str | None,
    date_to: str | None,
    format: str | None,
    stakes: str | None,
    position: str | None,
) -> HandFilters:
    return HandFilters(
        date_from=date_from,
        date_to=date_to,
        format=format,
        stakes=stakes,
        position=position,
    )


@app.get("/api/hero/stats")
def get_hero_stats(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    format: str | None = Query(None),
    stakes: str | None = Query(None),
    position: str | None = Query(None),
):
    conn = _connect()
    filters = _filters_from_query(date_from, date_to, format, stakes, position)
    stats = compute_hero_stats(conn, filters)
    conn.close()
    return stats


@app.get("/api/hero/graph")
def get_hero_graph(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    format: str | None = Query(None),
    stakes: str | None = Query(None),
    position: str | None = Query(None),
):
    conn = _connect()
    filters = _filters_from_query(date_from, date_to, format, stakes, position)
    series = hero_profit_series(conn, filters)
    conn.close()
    formats_present = {point["format"] for point in series}
    return {"series": series, "mixed_formats": len(formats_present) > 1}


@app.get("/api/filters/options")
def get_filter_options():
    conn = _connect()
    options = filter_options(conn)
    conn.close()
    return options


@app.get("/api/hands")
def get_hands(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    format: str | None = Query(None),
    stakes: str | None = Query(None),
    position: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    conn = _connect()
    filters = _filters_from_query(date_from, date_to, format, stakes, position)
    hands = list_hero_hands(conn, filters, limit=limit, offset=offset)
    conn.close()
    return {"hands": hands}


@app.get("/api/hands/{hand_id}/replay")
def get_replay(hand_id: int):
    conn = _connect()
    replay = get_hand_replay(conn, hand_id)
    conn.close()
    if replay is None:
        raise HTTPException(status_code=404, detail=f"Hand {hand_id} not found")
    return replay


@app.get("/api/leaks")
def get_leaks(
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    format: str | None = Query(None),
    stakes: str | None = Query(None),
):
    conn = _connect()
    filters = HandFilters(date_from=date_from, date_to=date_to, format=format, stakes=stakes)
    flags = find_leaks(conn, filters)
    conn.close()
    return {"flags": flags}
