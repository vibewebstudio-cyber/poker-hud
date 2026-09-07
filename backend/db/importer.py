"""Loads parsed Hand objects into the SQLite database."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from parsers.pokerstars_parser import Hand

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def import_hand(conn: sqlite3.Connection, hand: Hand) -> int | None:
    """Insert one hand and its seats/actions. Returns the new hand id,
    or None if this (site, hand_number) already exists."""
    existing = conn.execute(
        "SELECT id FROM hands WHERE site = ? AND hand_number = ?",
        (hand.site, hand.hand_number),
    ).fetchone()
    if existing:
        return None

    cur = conn.execute(
        """INSERT INTO hands (
            site, hand_number, format, game_type, tournament_id, buyin, level,
            stakes, small_blind, big_blind, ante, currency, table_name,
            table_size, button_seat, date, hero_name, hero_seat, hero_position,
            hero_cards, board, pot_size, rake, hero_result, raw_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
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


def import_hands(conn: sqlite3.Connection, hands: list[Hand]) -> tuple[int, int]:
    """Returns (imported_count, duplicate_count)."""
    imported = 0
    duplicates = 0
    for h in hands:
        hand_id = import_hand(conn, h)
        if hand_id is None:
            duplicates += 1
        else:
            imported += 1
    conn.commit()
    return imported, duplicates
