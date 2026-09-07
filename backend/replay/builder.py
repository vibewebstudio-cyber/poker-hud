"""Reconstructs a hand's action-by-action state (pot size, each player's
stack, and revealed board) so the frontend replayer can just index into
a list of steps rather than implement any poker logic itself.

Mirrors the invested/pot accounting in parsers.pokerstars_parser, with
the same ante handling: antes count toward what a player put in, but
never toward the street total a "raises X to Y" amount is measured
against.
"""

from __future__ import annotations

import sqlite3


def get_hand_replay(conn: sqlite3.Connection, hand_id: int) -> dict | None:
    hand_row = conn.execute(
        """SELECT id, site, hand_number, format, game_type, stakes, small_blind,
                  big_blind, ante, currency, table_name, table_size, button_seat,
                  date, hero_name, hero_cards, board, pot_size, rake
           FROM hands WHERE id = ?""",
        (hand_id,),
    ).fetchone()
    if hand_row is None:
        return None

    (
        hid, site, hand_number, fmt, game_type, stakes, small_blind, big_blind,
        ante, currency, table_name, table_size, button_seat, date, hero_name,
        hero_cards, board_str, pot_size, rake,
    ) = hand_row

    seat_rows = conn.execute(
        """SELECT seat, player_name, starting_stack, position, is_hero, net_result, shown_cards
           FROM hand_players WHERE hand_id = ? ORDER BY seat""",
        (hand_id,),
    ).fetchall()
    seats = [
        {
            "seat": seat,
            "name": name,
            "starting_stack": starting_stack,
            "position": position,
            "is_hero": bool(is_hero),
            "net_result": net_result,
            "shown_cards": shown_cards,
        }
        for seat, name, starting_stack, position, is_hero, net_result, shown_cards in seat_rows
    ]
    stacks = {s["name"]: s["starting_stack"] for s in seats}

    action_rows = conn.execute(
        """SELECT player_name, street, action_type, amount, action_order, position
           FROM actions WHERE hand_id = ? ORDER BY action_order""",
        (hand_id,),
    ).fetchall()

    full_board = board_str.split() if board_str else []
    board_by_street = {
        "preflop": [],
        "flop": full_board[:3],
        "turn": full_board[:4],
        "river": full_board[:5],
    }

    pot = 0.0
    street_totals: dict[str, float] = {}
    current_street = "preflop"
    steps = []

    for player, street, action_type, amount, _order, position in action_rows:
        if street != current_street:
            street_totals = {}
            current_street = street

        if action_type == "posts_ante":
            stacks[player] -= amount or 0.0
            pot += amount or 0.0
        elif action_type in ("posts_sb", "posts_bb"):
            stacks[player] -= amount or 0.0
            pot += amount or 0.0
            street_totals[player] = street_totals.get(player, 0.0) + (amount or 0.0)
        elif action_type in ("calls", "bets"):
            stacks[player] -= amount or 0.0
            pot += amount or 0.0
            street_totals[player] = street_totals.get(player, 0.0) + (amount or 0.0)
        elif action_type == "raises":
            prior = street_totals.get(player, 0.0)
            to_amount = amount or 0.0
            increment = to_amount - prior
            stacks[player] -= increment
            pot += increment
            street_totals[player] = to_amount
        elif action_type == "uncalled_return":
            stacks[player] += amount or 0.0
            pot -= amount or 0.0
        elif action_type == "collected":
            stacks[player] += amount or 0.0
            pot -= amount or 0.0
        # folds / checks: no money movement

        steps.append({
            "street": street,
            "board": board_by_street.get(street, full_board),
            "player": player,
            "action_type": action_type,
            "amount": amount,
            "position": position,
            "pot_after": round(pot, 2),
            "stacks_after": {name: round(v, 2) for name, v in stacks.items()},
        })

    return {
        "hand_id": hid,
        "site": site,
        "hand_number": hand_number,
        "format": fmt,
        "game_type": game_type,
        "stakes": stakes,
        "small_blind": small_blind,
        "big_blind": big_blind,
        "ante": ante,
        "currency": currency,
        "table_name": table_name,
        "table_size": table_size,
        "button_seat": button_seat,
        "date": date,
        "hero_name": hero_name,
        "hero_cards": hero_cards,
        "board": full_board,
        "pot_size": pot_size,
        "rake": rake,
        "seats": seats,
        "steps": steps,
    }
