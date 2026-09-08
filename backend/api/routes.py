"""FastAPI backend: auth, hero stats, profit-over-time graph data, filter
options, hand list/replay, leak finder, and hand-history upload — all
scoped per authenticated user.

Run with: uvicorn api.routes:app --port 8001
(avoid --reload here — it's been unreliable on Windows in this project;
restart the process manually after editing backend code)
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.auth_routes import router as auth_router
from auth.security import get_current_user_id
from db.importer import get_connection, import_hands
from importing import SITE_ADAPTERS, parse_path
from replay.builder import get_hand_replay
from stats.calculators import HandFilters, compute_hero_stats, filter_options, hero_profit_series, list_hero_hands
from stats.leak_finder import find_leaks

app = FastAPI(title="Poker Hand Tracker API")
app.include_router(auth_router)

# Overridable for a hosted deployment (Stage C) where the frontend lives
# on a different origin than localhost — a comma-separated list of exact
# origins, e.g. "https://poker-hud.pages.dev". Defaults to any localhost
# port for local dev.
_CORS_ORIGINS = os.environ.get("CORS_ORIGINS")
if _CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in _CORS_ORIGINS.split(",")],
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://localhost:\d+",
        allow_methods=["*"],
        allow_headers=["*"],
    )


def _connect():
    return get_connection()


def _filters_from_query(
    user_id: int,
    date_from: str | None,
    date_to: str | None,
    format: str | None,
    stakes: str | None,
    position: str | None,
) -> HandFilters:
    return HandFilters(
        user_id=user_id,
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
    user_id: int = Depends(get_current_user_id),
):
    conn = _connect()
    filters = _filters_from_query(user_id, date_from, date_to, format, stakes, position)
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
    user_id: int = Depends(get_current_user_id),
):
    conn = _connect()
    filters = _filters_from_query(user_id, date_from, date_to, format, stakes, position)
    series = hero_profit_series(conn, filters)
    conn.close()
    formats_present = {point["format"] for point in series}
    return {"series": series, "mixed_formats": len(formats_present) > 1}


@app.get("/api/filters/options")
def get_filter_options(user_id: int = Depends(get_current_user_id)):
    conn = _connect()
    options = filter_options(conn, user_id)
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
    user_id: int = Depends(get_current_user_id),
):
    conn = _connect()
    filters = _filters_from_query(user_id, date_from, date_to, format, stakes, position)
    hands = list_hero_hands(conn, filters, limit=limit, offset=offset)
    conn.close()
    return {"hands": hands}


@app.get("/api/hands/{hand_id}/replay")
def get_replay(hand_id: int, user_id: int = Depends(get_current_user_id)):
    conn = _connect()
    replay = get_hand_replay(conn, hand_id, user_id)
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
    user_id: int = Depends(get_current_user_id),
):
    conn = _connect()
    filters = HandFilters(user_id=user_id, date_from=date_from, date_to=date_to, format=format, stakes=stakes)
    flags = find_leaks(conn, filters)
    conn.close()
    return {"flags": flags}


@app.post("/api/import")
async def import_hand_histories(
    files: list[UploadFile] = File(...),
    user_id: int = Depends(get_current_user_id),
):
    conn = _connect()
    results = []
    total_imported = 0
    total_duplicates = 0

    for upload in files:
        content = await upload.read()
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        try:
            hands, site = parse_path(tmp_path)
            if site is None:
                results.append({"filename": upload.filename, "error": "unrecognized hand history format"})
                continue
            if site not in SITE_ADAPTERS:
                results.append({"filename": upload.filename, "error": f"no parser available for '{site}' yet"})
                continue
            imported, duplicates = import_hands(conn, hands, user_id)
            results.append({
                "filename": upload.filename,
                "site": site,
                "parsed": len(hands),
                "imported": imported,
                "duplicates": duplicates,
            })
            total_imported += imported
            total_duplicates += duplicates
        finally:
            os.unlink(tmp_path)

    conn.close()
    return {"files": results, "total_imported": total_imported, "total_duplicates": total_duplicates}
