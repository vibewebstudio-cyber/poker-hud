"""Site adapter for PokerStars Hold'em No Limit hand history text files.

Supplies PokerStars' header format to the shared parsing engine in
parsers.common — everything after the header (seats, actions, streets,
summary) is identical across sites and handled there.
"""

from __future__ import annotations

import re

from parsers import common
from parsers.common import Action, Hand, ParseError, Seat  # re-exported for callers

SITE = "PokerStars"

_HAND_START_RE = re.compile(r"PokerStars Hand #")

_HEADER_CASH_RE = re.compile(
    r"^PokerStars Hand #(?P<hand_number>\d+):\s+"
    r"(?P<game_type>.+?) \((?P<currency>\$|€|£)?(?P<sb>[\d.]+)/(?P<currency2>\$|€|£)?(?P<bb>[\d.]+)(?: (?P<curcode>\w+))?\) - "
    r"(?P<date>[\d/]+ [\d:]+) \w+$"
)

_HEADER_TOURNEY_RE = re.compile(
    r"^PokerStars Hand #(?P<hand_number>\d+): Tournament #(?P<tourney_id>\d+), "
    r"(?P<buyin>[^ ]+(?: \+ [^ ]+)?) (?:\w+ )?(?P<game_type>.+?) - "
    r"Level (?P<level>\S+) \((?P<sb>[\d.]+)/(?P<bb>[\d.]+)(?:/(?P<ante>[\d.]+))?\) - "
    r"(?P<date>[\d/]+ [\d:]+) \w+$"
)


def _parse_header(lines: list[str], hand: Hand) -> int:
    line = lines[0]
    m = _HEADER_TOURNEY_RE.match(line)
    if m:
        hand.format = "tournament"
        hand.hand_number = m.group("hand_number")
        hand.tournament_id = m.group("tourney_id")
        hand.buyin = m.group("buyin")
        hand.game_type = m.group("game_type").strip()
        hand.level = m.group("level")
        hand.small_blind = common.num(m.group("sb"))
        hand.big_blind = common.num(m.group("bb"))
        hand.ante = common.num(m.group("ante")) if m.group("ante") else 0.0
        hand.date = common.parse_date(m.group("date"))
        return 1

    m = _HEADER_CASH_RE.match(line)
    if m:
        hand.format = "cash"
        hand.hand_number = m.group("hand_number")
        hand.game_type = m.group("game_type").strip()
        hand.small_blind = common.num(m.group("sb"))
        hand.big_blind = common.num(m.group("bb"))
        hand.currency = m.group("currency") or m.group("curcode") or "$"
        hand.date = common.parse_date(m.group("date"))
        return 1

    raise ParseError(f"Unrecognized header line: {line!r}")


def parse_hand(raw_hand: str) -> Hand | None:
    """Parse a single hand-history block. Returns None for non-NLHE games."""
    return common.parse_hand(raw_hand, SITE, _parse_header)


def parse_file(path: str) -> list[Hand]:
    return common.parse_file(path, SITE, _parse_header, _HAND_START_RE)
