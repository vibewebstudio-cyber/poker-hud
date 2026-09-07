"""Site adapter for GGPoker (PokerCraft-exported) hand histories.

The tournament header format below is now VERIFIED against a real
PokerCraft export (292 Mystery Battle Royale tournament files downloaded
directly from GGPoker) — see tests/sample_hands/ggpoker_hand.txt for a
synthetic fixture built to match the confirmed structure exactly. Real
format, confirmed:

    Poker Hand #BR1213812103: Tournament #304807889, Mystery Battle
    Royale $1 Hold'em No Limit - Level1(10/20(4)) - 2026/08/07 16:54:19

Notably different from the original best-guess: the buy-in is embedded
*inside* the tournament-name segment rather than appearing as a cleanly
delimited token before it, and the ante is nested inside the blinds'
parentheses ("20(4)") rather than slash-separated ("10/20/4"). The
"*** SHOWDOWN ***" marker is one word (PokerStars uses "SHOW DOWN").

Everything after the header (seats, actions, streets, summary) matched
the shared engine in parsers.common without changes — the 292-file
sample used zero straddles, run-it-twice, or other PokerStars-incompatible
constructs, though that's just what this one sample happened to contain,
not a guarantee no GGPoker hand ever uses them.

The CASH header format below remains UNVERIFIED — the sample used to
confirm the tournament format didn't include any cash-game hands. Don't
trust cash-game parsing here until it's checked against a real export.

As the spec notes, GGPoker hand histories only anonymize opponents
(random per-hand usernames) — hero's own hand is always fully visible,
so hero-scoped stats (VPIP/PFR/results) work the same as for PokerStars.
"""

from __future__ import annotations

import re

from parsers import common
from parsers.common import Action, Hand, ParseError, Seat  # re-exported for callers

SITE = "GGPoker"

_HAND_START_RE = re.compile(r"Poker Hand #")

_HEADER_CASH_RE = re.compile(
    r"^Poker Hand #(?P<hand_number>\w+):\s*"
    r"(?P<game_type>.+?) \((?P<currency>\$|€|£)?(?P<sb>[\d.]+)/(?P<currency2>\$|€|£)?(?P<bb>[\d.]+)(?: (?P<curcode>\w+))?\) - "
    r"(?P<date>[\d/]+ [\d:]+)$"
)

# Buy-in is embedded inside the tournament-name segment: "<name> $<buyin> <game_type>"
_HEADER_TOURNEY_RE = re.compile(
    r"^Poker Hand #(?P<hand_number>\w+): Tournament #(?P<tourney_id>\d+), "
    r"(?:(?P<tourney_name>.+?) )?(?P<buyin>\$[\d,.]+(?:\+\$[\d,.]+)?) (?P<game_type>.+?) - "
    r"Level\s*(?P<level>[^\s(]+)\((?P<sb>[\d,.]+)/(?P<bb>[\d,.]+)(?:\((?P<ante>[\d,.]+)\))?\) - "
    r"(?P<date>[\d/]+ [\d:]+)$"
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
