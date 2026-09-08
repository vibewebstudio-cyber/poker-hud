"""Loads parsed Hand objects into the SQLite database."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from parsers.pokerstars_parser import Hand

SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Overridable via env var so a hosted deployment (Stage C) can point at
# a persistent volume instead of the repo-local default used for
# local/dev use.
DB_PATH = os.environ.get("DB_PATH", str(Path(__file__).resolve().parent.parent / "poker.db"))


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def import_hand(conn: sqlite3.Connection, hand: Hand, user_id: int) -> int | None:
    """Insert one hand and its seats/actions for the given user. Returns
    the new hand id, or None if this (user, site, hand_number) already
    exists — two different users can hold "the same" hand (they played
    at the same table), each with their own copy since each export only
    reveals that user's own hole cards."""
    existing = conn.execute(
        "SELECT id FROM hands WHERE user_id = ? AND site = ? AND hand_number = ?",
        (user_id, hand.site, hand.hand_number),
    ).fetchone()
    if existing:
        return None

    cur = conn.execute(
        """INSERT INTO hands (
            user_id, site, hand_number, format, game_type, tournament_id, buyin, level,
            stakes, small_blind, big_blind, ante, currency, table_name,
            table_size, button_seat, date, hero_name, hero_seat, hero_position,
            hero_cards, board, pot_size, rake, hero_result, raw_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id,
            hand.site,
            hand.hand_number,
            hand.format,
            hand.game_type,
            hand.tournament_id,
            hand.buyin,
            hand.level,
            f"{hand.small_blind}/{hand.big_blind}",
            hand.small_blind,
            hand.big_blind,
            hand.ante,
            hand.currency,
            hand.table_name,
            hand.table_size,
            hand.button_seat,
            hand.date,
            hand.hero_name,
            hand.hero_seat,
            hand.hero_position,
            hand.hero_cards,
            " ".join(hand.board),
            hand.pot_size,
            hand.rake,
            hand.hero_result,
            hand.raw_text,
        ),
    )
    hand_id = cur.lastrowid

    for seat in hand.seats:
        conn.execute(
            """INSERT INTO hand_players (hand_id, player_name, seat, starting_stack, position, is_hero, net_result, shown_cards)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                hand_id,
                seat.name,
                seat.seat_num,
                seat.stack,
                hand.positions.get(seat.name),
                1 if seat.name == hand.hero_name else 0,
                hand.results.get(seat.name, 0.0),
                hand.shown_cards.get(seat.name),
            ),
        )

    for a in hand.actions:
        conn.execute(
            """INSERT INTO actions (hand_id, player_name, street, action_type, amount, action_order, position)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (hand_id, a.player, a.street, a.action_type, a.amount, a.order, a.position),
        )

    return hand_id


def import_hands(conn: sqlite3.Connection, hands: list[Hand], user_id: int) -> tuple[int, int]:
    """Returns (imported_count, duplicate_count)."""
    imported = 0
    duplicates = 0
    for h in hands:
        hand_id = import_hand(conn, h, user_id)
        if hand_id is None:
            duplicates += 1
        else:
            imported += 1
    conn.commit()
    return imported, duplicates


def get_or_create_local_user(conn: sqlite3.Connection) -> int:
    """Returns the id of a fixed local-use account, creating it if
    needed, so the CLI keeps working without requiring a login for
    local/personal use (see README)."""
    row = conn.execute("SELECT id FROM users WHERE email = ?", ("local@localhost",)).fetchone()
    if row:
        return row[0]
    from datetime import datetime, timezone

    from auth.security import hash_password

    cur = conn.execute(
        "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
        ("local@localhost", hash_password(os.urandom(16).hex()), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return cur.lastrowid
