"""VPIP / PFR / 3-bet% calculators, computed from the `actions` table.

Each stat is (occurrences / opportunities) over a set of hands, scoped to
one player. Opportunities exclude hands the player wasn't dealt into.

Hero-scoped stats (compute_hero_stats) resolve the hero's in-hand name
per hand via hand_players.is_hero, since the same real person can appear
under different screen names across sites/hands.

Note on results: hand-level net_result is in real money for cash-game
hands, but in tournament chips for tournament hands (hand histories don't
carry finishing place or payout, so true $ ROI isn't derivable from them
alone). Callers that mix formats should filter by `format` first.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass


@dataclass
class PlayerStats:
    player_name: str
    hands: int
    vpip_pct: float
    pfr_pct: float
    three_bet_pct: float
    three_bet_opportunities: int
    total_result: float = 0.0
    avg_result: float = 0.0
    bb_per_100: float | None = None  # only meaningful when all hands are cash-game
    fold_to_raise_pct: float | None = None  # % folded when facing a single raise preflop


@dataclass
class HandFilters:
    date_from: str | None = None
    date_to: str | None = None
    format: str | None = None  # 'cash' or 'tournament'
    stakes: str | None = None
    position: str | None = None


def _hand_ids_for_player(conn: sqlite3.Connection, player_name: str) -> list[int]:
    rows = conn.execute(
        "SELECT DISTINCT hand_id FROM hand_players WHERE player_name = ?",
        (player_name,),
    ).fetchall()
    return [r[0] for r in rows]


def _preflop_flags(conn: sqlite3.Connection, hand_id: int, player_name: str) -> dict:
    actions = conn.execute(
        """SELECT player_name, action_type, action_order FROM actions
           WHERE hand_id = ? AND street = 'preflop' ORDER BY action_order""",
        (hand_id,),
    ).fetchall()

    raise_count = 0
    voluntary_in = False
    raised = False
    had_3bet_chance = False
    took_3bet_chance = False
    folded_to_raise = False

    for name, action_type, _order in actions:
        if name == player_name:
            if action_type in ("calls", "bets", "raises"):
                voluntary_in = True
            if action_type == "raises":
                raised = True
            if action_type in ("folds", "calls", "raises") and raise_count == 1:
                had_3bet_chance = True
                if action_type == "raises":
                    took_3bet_chance = True
                elif action_type == "folds":
                    folded_to_raise = True
        if action_type == "raises":
            raise_count += 1

    return {
        "voluntary_in": voluntary_in,
        "raised": raised,
        "had_3bet_chance": had_3bet_chance,
        "took_3bet_chance": took_3bet_chance,
        "folded_to_raise": folded_to_raise,
    }


def _aggregate(
    player_name: str,
    per_hand_flags: list[dict],
    results: list[float],
    big_blinds: list[float | None],
) -> PlayerStats:
    n_hands = len(per_hand_flags)
    if n_hands == 0:
        return PlayerStats(player_name, 0, 0.0, 0.0, 0.0, 0)

    vpip_hands = sum(1 for f in per_hand_flags if f["voluntary_in"])
    pfr_hands = sum(1 for f in per_hand_flags if f["raised"])
    three_bet_opportunities = sum(1 for f in per_hand_flags if f["had_3bet_chance"])
    three_bet_hands = sum(1 for f in per_hand_flags if f["took_3bet_chance"])
    folded_to_raise_hands = sum(1 for f in per_hand_flags if f["folded_to_raise"])

    total_result = round(sum(results), 2)
    avg_result = round(total_result / n_hands, 2) if n_hands else 0.0

    bb_values = [r / bb for r, bb in zip(results, big_blinds) if bb]
    bb_per_100 = round(100 * sum(bb_values) / len(bb_values), 2) if bb_values else None

    three_bet_pct = (
        round(100 * three_bet_hands / three_bet_opportunities, 1)
        if three_bet_opportunities
        else 0.0
    )
    fold_to_raise_pct = (
        round(100 * folded_to_raise_hands / three_bet_opportunities, 1)
        if three_bet_opportunities
        else None
    )

    return PlayerStats(
        player_name=player_name,
        hands=n_hands,
        vpip_pct=round(100 * vpip_hands / n_hands, 1),
        pfr_pct=round(100 * pfr_hands / n_hands, 1),
        three_bet_pct=three_bet_pct,
        three_bet_opportunities=three_bet_opportunities,
        total_result=total_result,
        avg_result=avg_result,
        bb_per_100=bb_per_100,
        fold_to_raise_pct=fold_to_raise_pct,
    )


def compute_player_stats(conn: sqlite3.Connection, player_name: str) -> PlayerStats:
    hand_ids = _hand_ids_for_player(conn, player_name)
    flags = [_preflop_flags(conn, hid, player_name) for hid in hand_ids]
    results = []
    big_blinds = []
    for hid in hand_ids:
        row = conn.execute(
            """SELECT hp.net_result, h.big_blind, h.format FROM hand_players hp
               JOIN hands h ON h.id = hp.hand_id
               WHERE hp.hand_id = ? AND hp.player_name = ?""",
            (hid, player_name),
        ).fetchone()
        results.append(row[0] or 0.0)
        big_blinds.append(row[1] if row[2] == "cash" else None)
    return _aggregate(player_name, flags, results, big_blinds)


def _filtered_hero_hands(conn: sqlite3.Connection, filters: HandFilters | None) -> list[tuple]:
    """Returns rows of (hand_id, hero_name, net_result, big_blind, date) for
    hero-flagged hands matching the given filters, ordered by date."""
    filters = filters or HandFilters()
    query = """
        SELECT hp.hand_id, hp.player_name, hp.net_result, h.big_blind, h.date, h.format
        FROM hand_players hp
        JOIN hands h ON h.id = hp.hand_id
        WHERE hp.is_hero = 1
    """
    params: list = []
    if filters.date_from:
        query += " AND h.date >= ?"
        params.append(filters.date_from)
    if filters.date_to:
        query += " AND h.date <= ?"
        params.append(filters.date_to)
    if filters.format:
        query += " AND h.format = ?"
        params.append(filters.format)
    if filters.stakes:
        query += " AND h.stakes = ?"
        params.append(filters.stakes)
    if filters.position:
        query += " AND hp.position = ?"
        params.append(filters.position)
    query += " ORDER BY h.date ASC"
    return conn.execute(query, params).fetchall()


def compute_hero_stats(conn: sqlite3.Connection, filters: HandFilters | None = None) -> PlayerStats:
    rows = _filtered_hero_hands(conn, filters)
    flags = [_preflop_flags(conn, hand_id, hero_name) for hand_id, hero_name, _r, _bb, _d, _f in rows]
    results = [r or 0.0 for _hid, _name, r, _bb, _d, _f in rows]
    big_blinds = [bb if fmt == "cash" else None for _hid, _name, _r, bb, _d, fmt in rows]
    return _aggregate("Hero", flags, results, big_blinds)


def compute_position_stats(
    conn: sqlite3.Connection, filters: HandFilters | None = None
) -> dict[str, PlayerStats]:
    """Hero stats broken out by position, for positional-leak analysis.
    Positions with zero hero hands in range are omitted."""
    filters = filters or HandFilters()
    positions = [
        r[0]
        for r in conn.execute(
            "SELECT DISTINCT position FROM hand_players WHERE is_hero = 1 AND position IS NOT NULL"
        ).fetchall()
    ]
    result = {}
    for pos in positions:
        pos_filters = HandFilters(**{**filters.__dict__, "position": pos})
        stats = compute_hero_stats(conn, pos_filters)
        if stats.hands > 0:
            result[pos] = stats
    return result


def hero_profit_series(conn: sqlite3.Connection, filters: HandFilters | None = None) -> list[dict]:
    """Cumulative hero result over time. Units are real money for cash
    hands and tournament chips for tournament hands — don't mix formats
    in one series without filtering by `format` first (the `mixed_formats`
    flag on the response tells the caller when that's happening)."""
    rows = _filtered_hero_hands(conn, filters)
    series = []
    cumulative = 0.0
    for hand_id, _name, result, _bb, date, fmt in rows:
        cumulative += result or 0.0
        series.append({
            "hand_id": hand_id,
            "date": date,
            "format": fmt,
            "result": round(result or 0.0, 2),
            "cumulative": round(cumulative, 2),
        })
    return series


def list_hero_hands(
    conn: sqlite3.Connection,
    filters: HandFilters | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Hand summaries for the hands-list view, most recent first."""
    filters = filters or HandFilters()
    query = """
        SELECT h.id, h.date, h.format, h.game_type, h.stakes, hp.position,
               h.hero_cards, h.board, h.pot_size, hp.net_result
        FROM hand_players hp
        JOIN hands h ON h.id = hp.hand_id
        WHERE hp.is_hero = 1
    """
    params: list = []
    if filters.date_from:
        query += " AND h.date >= ?"
        params.append(filters.date_from)
    if filters.date_to:
        query += " AND h.date <= ?"
        params.append(filters.date_to)
    if filters.format:
        query += " AND h.format = ?"
        params.append(filters.format)
    if filters.stakes:
        query += " AND h.stakes = ?"
        params.append(filters.stakes)
    if filters.position:
        query += " AND hp.position = ?"
        params.append(filters.position)
    query += " ORDER BY h.date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    return [
        {
            "hand_id": r[0],
            "date": r[1],
            "format": r[2],
            "game_type": r[3],
            "stakes": r[4],
            "position": r[5],
            "hero_cards": r[6],
            "board": r[7].split() if r[7] else [],
            "pot_size": r[8],
            "hero_result": r[9],
        }
        for r in rows
    ]


def filter_options(conn: sqlite3.Connection) -> dict:
    """Distinct values available for the filter panel, derived from hero hands."""
    stakes = conn.execute(
        """SELECT DISTINCT h.stakes FROM hands h
           JOIN hand_players hp ON hp.hand_id = h.id
           WHERE hp.is_hero = 1 ORDER BY h.stakes"""
    ).fetchall()
    formats = conn.execute(
        """SELECT DISTINCT h.format FROM hands h
           JOIN hand_players hp ON hp.hand_id = h.id
           WHERE hp.is_hero = 1 ORDER BY h.format"""
    ).fetchall()
    positions = conn.execute(
        """SELECT DISTINCT hp.position FROM hand_players hp
           WHERE hp.is_hero = 1 AND hp.position IS NOT NULL ORDER BY hp.position"""
    ).fetchall()
    date_range = conn.execute(
        """SELECT MIN(h.date), MAX(h.date) FROM hands h
           JOIN hand_players hp ON hp.hand_id = h.id
           WHERE hp.is_hero = 1"""
    ).fetchone()

    return {
        "stakes": [r[0] for r in stakes],
        "formats": [r[0] for r in formats],
        "positions": [r[0] for r in positions],
        "date_min": date_range[0] if date_range else None,
        "date_max": date_range[1] if date_range else None,
    }


def list_players(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute("SELECT DISTINCT player_name FROM hand_players ORDER BY player_name").fetchall()
    return [r[0] for r in rows]
