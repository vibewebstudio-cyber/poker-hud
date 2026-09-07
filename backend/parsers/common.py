"""Shared hand-history parsing engine used by every site adapter.

Text-based hand histories (PokerStars, GGPoker, and most other sites
that export in this style) share the same skeleton once you're past the
header line: a seat list, blinds/antes, then action lines grouped by
street, ending in a summary. Only the header format and site label
differ meaningfully between sites, so each site module (pokerstars_parser.py,
ggpoker_parser.py, ...) supplies just a header parser and calls into the
generic engine here for everything else.

Only No Limit Hold'em is handled. Other games are skipped with a warning
on stderr rather than raising, so a mixed-game export can still be
imported for the hands we do understand.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

STREET_PREFLOP = "preflop"
STREET_FLOP = "flop"
STREET_TURN = "turn"
STREET_RIVER = "river"

POSITIONS_BY_SIZE = {
    2: ["BTN", "BB"],  # heads-up: button is also SB
    3: ["BTN", "SB", "BB"],
    4: ["BTN", "SB", "BB", "CO"],
    5: ["BTN", "SB", "BB", "UTG", "CO"],
    6: ["BTN", "SB", "BB", "UTG", "MP", "CO"],
    7: ["BTN", "SB", "BB", "UTG", "UTG+1", "MP", "CO"],
    8: ["BTN", "SB", "BB", "UTG", "UTG+1", "MP", "HJ", "CO"],
    9: ["BTN", "SB", "BB", "UTG", "UTG+1", "UTG+2", "MP", "HJ", "CO"],
    10: ["BTN", "SB", "BB", "UTG", "UTG+1", "UTG+2", "MP", "MP+1", "HJ", "CO"],
}


class ParseError(ValueError):
    pass


@dataclass
class Seat:
    seat_num: int
    name: str
    stack: float


@dataclass
class Action:
    player: str
    street: str
    action_type: str  # posts_sb, posts_bb, posts_ante, folds, checks, calls, bets, raises
    amount: float | None
    order: int
    position: str | None = None


@dataclass
class Hand:
    site: str = ""
    hand_number: str = ""
    format: str = "cash"  # 'cash' or 'tournament'
    game_type: str = "Hold'em No Limit"
    tournament_id: str | None = None
    buyin: str | None = None
    level: str | None = None
    small_blind: float = 0.0
    big_blind: float = 0.0
    ante: float = 0.0
    currency: str | None = None
    table_name: str = ""
    table_size: int = 0
    button_seat: int = 0
    date: str = ""
    hero_name: str | None = None
    hero_cards: str | None = None
    board: list[str] = field(default_factory=list)
    pot_size: float = 0.0
    rake: float = 0.0
    seats: list[Seat] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    positions: dict[str, str] = field(default_factory=dict)
    results: dict[str, float] = field(default_factory=dict)
    shown_cards: dict[str, str] = field(default_factory=dict)
    raw_text: str = ""

    @property
    def hero_seat(self) -> int | None:
        for s in self.seats:
            if s.name == self.hero_name:
                return s.seat_num
        return None

    @property
    def hero_position(self) -> str | None:
        if self.hero_name is None:
            return None
        return self.positions.get(self.hero_name)

    @property
    def hero_result(self) -> float | None:
        if self.hero_name is None:
            return None
        return self.results.get(self.hero_name, 0.0)


# Header parsers return (lines_consumed) and populate `hand` in place;
# they raise ParseError on an unrecognized header line.
HeaderParser = Callable[[list[str], Hand], int]

_TABLE_RE = re.compile(
    r"^Table '(?P<name>.+)' (?P<size>\d+)-max Seat #(?P<button>\d+) is the button$"
)

_SEAT_RE = re.compile(
    r"^Seat (?P<num>\d+): (?P<name>.+?) \(\$?(?P<stack>[\d,.]+) in chips\)"
)

_POSTS_SB_RE = re.compile(r"^(?P<name>.+?): posts small blind \$?(?P<amt>[\d,.]+)")
_POSTS_BB_RE = re.compile(r"^(?P<name>.+?): posts big blind \$?(?P<amt>[\d,.]+)")
_POSTS_ANTE_RE = re.compile(r"^(?P<name>.+?): posts the ante \$?(?P<amt>[\d,.]+)")
_POSTS_DEAD_RE = re.compile(r"^(?P<name>.+?): posts small \& big blinds \$?(?P<amt>[\d,.]+)")

_DEALT_RE = re.compile(r"^Dealt to (?P<name>.+?) \[(?P<cards>.+?)\]$")
_SHOWS_RE = re.compile(r"^(?P<name>.+?): shows \[(?P<cards>.+?)\]")

_FOLDS_RE = re.compile(r"^(?P<name>.+?): folds$")
_CHECKS_RE = re.compile(r"^(?P<name>.+?): checks$")
_CALLS_RE = re.compile(r"^(?P<name>.+?): calls \$?(?P<amt>[\d,.]+)")
_BETS_RE = re.compile(r"^(?P<name>.+?): bets \$?(?P<amt>[\d,.]+)")
_RAISES_RE = re.compile(r"^(?P<name>.+?): raises \$?(?P<by>[\d,.]+) to \$?(?P<to>[\d,.]+)")

_UNCALLED_RE = re.compile(r"^Uncalled bet \(\$?(?P<amt>[\d,.]+)\) returned to (?P<name>.+)$")
_COLLECTED_RE = re.compile(r"^(?P<name>.+?) collected \$?(?P<amt>[\d,.]+) from")

_STREET_TAG_RE = re.compile(r"^\*\*\* (FLOP|TURN|RIVER|HOLE CARDS|SHOW DOWN|SUMMARY) \*\*\*")
_FLOP_BOARD_RE = re.compile(r"^\*\*\* FLOP \*\*\* \[(?P<cards>.+?)\]")
_NEW_CARD_RE = re.compile(r"\[(?P<cards>[^\[\]]+)\]\s*$")

_TOTAL_POT_RE = re.compile(r"^Total pot \$?(?P<pot>[\d,.]+)(?: \| Rake \$?(?P<rake>[\d,.]+))?")


def num(s: str | None) -> float:
    if s is None:
        return 0.0
    return float(s.replace(",", ""))


def parse_date(raw: str) -> str:
    try:
        dt = datetime.strptime(raw, "%Y/%m/%d %H:%M:%S")
        return dt.isoformat()
    except ValueError:
        return raw


def assign_positions(seats: list[Seat], button_seat: int) -> dict[str, str]:
    n = len(seats)
    if n < 2 or n > 10:
        return {}
    labels = POSITIONS_BY_SIZE.get(n)
    if labels is None:
        return {}
    ordered = sorted(seats, key=lambda s: s.seat_num)
    seat_nums = [s.seat_num for s in ordered]
    try:
        start = seat_nums.index(button_seat)
    except ValueError:
        return {}
    rotated = ordered[start:] + ordered[:start]
    return {seat.name: label for seat, label in zip(rotated, labels)}


def split_hands(text: str, hand_start_re: re.Pattern) -> list[str]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    chunks = re.split(r"\n\s*\n(?=" + hand_start_re.pattern + r")", text.strip())
    return [c.strip() for c in chunks if c.strip()]


def _parse_summary(summary_lines: list[str], hand: Hand) -> None:
    for line in summary_lines:
        m = _TOTAL_POT_RE.match(line)
        if m:
            hand.pot_size = num(m.group("pot"))
            hand.rake = num(m.group("rake"))
            continue
        if line.startswith("Board ["):
            cards = line[line.index("[") + 1 : line.index("]")]
            hand.board = cards.split()
            continue


def compute_results(hand: Hand) -> dict[str, float]:
    """Net chips/$ won or lost per player for this hand.

    invested = everything they posted/called/bet/raised to, minus
    uncalled-bet returns and pot collections (which count as money back).
    """
    invested: dict[str, float] = {s.name: 0.0 for s in hand.seats}
    street_totals: dict[tuple[str, str], float] = {}

    for a in hand.actions:
        invested.setdefault(a.player, 0.0)
        if a.action_type == "posts_ante":
            # Antes are dead money: they count toward what the player put
            # in, but "raises X to Y" amounts never include them.
            invested[a.player] += a.amount or 0.0
        elif a.action_type in ("posts_sb", "posts_bb"):
            invested[a.player] += a.amount or 0.0
            street_totals[(a.player, a.street)] = street_totals.get((a.player, a.street), 0.0) + (a.amount or 0.0)
        elif a.action_type in ("calls", "bets"):
            invested[a.player] += a.amount or 0.0
            street_totals[(a.player, a.street)] = street_totals.get((a.player, a.street), 0.0) + (a.amount or 0.0)
        elif a.action_type == "raises":
            prior = street_totals.get((a.player, a.street), 0.0)
            to_amount = a.amount or 0.0
            invested[a.player] += to_amount - prior
            street_totals[(a.player, a.street)] = to_amount
        elif a.action_type == "uncalled_return":
            invested[a.player] -= a.amount or 0.0
        elif a.action_type == "collected":
            invested[a.player] -= a.amount or 0.0

    return {name: round(-amt, 2) for name, amt in invested.items()}


def parse_hand(raw_hand: str, site: str, parse_header: HeaderParser) -> Hand | None:
    """Parse a single hand-history block using a site-specific header
    parser for the first line(s). Returns None for non-NLHE games."""
    lines = [l for l in raw_hand.split("\n") if l.strip() != ""]
    if not lines:
        return None

    hand = Hand(site=site, raw_text=raw_hand)
    idx = parse_header(lines, hand)

    if "Hold'em No Limit" not in hand.game_type and "Hold'em" not in hand.game_type:
        print(f"Skipping non-NLHE hand #{hand.hand_number}: {hand.game_type}", file=sys.stderr)
        return None

    m = _TABLE_RE.match(lines[idx])
    if not m:
        raise ParseError(f"Expected table line, got: {lines[idx]!r}")
    hand.table_name = m.group("name")
    hand.table_size = int(m.group("size"))
    hand.button_seat = int(m.group("button"))
    idx += 1

    while idx < len(lines):
        m = _SEAT_RE.match(lines[idx])
        if not m:
            break
        hand.seats.append(Seat(int(m.group("num")), m.group("name"), num(m.group("stack"))))
        idx += 1

    hand.positions = assign_positions(hand.seats, hand.button_seat)

    street = STREET_PREFLOP
    order = 0

    while idx < len(lines):
        line = lines[idx]
        idx += 1

        m = _STREET_TAG_RE.match(line)
        if m:
            tag = m.group(1)
            if tag == "FLOP":
                street = STREET_FLOP
                fm = _FLOP_BOARD_RE.match(line)
                if fm:
                    hand.board = fm.group("cards").split()
            elif tag == "TURN":
                street = STREET_TURN
                nm = _NEW_CARD_RE.search(line)
                if nm:
                    hand.board = hand.board + [nm.group("cards").strip()]
            elif tag == "RIVER":
                street = STREET_RIVER
                nm = _NEW_CARD_RE.search(line)
                if nm:
                    hand.board = hand.board + [nm.group("cards").strip()]
            elif tag == "SUMMARY":
                _parse_summary(lines[idx:], hand)
                break
            continue

        m = _DEALT_RE.match(line)
        if m:
            if hand.hero_name is None:
                hand.hero_name = m.group("name")
                hand.hero_cards = m.group("cards")
            continue

        m = _SHOWS_RE.match(line)
        if m:
            hand.shown_cards[m.group("name")] = m.group("cards")
            continue

        m = _POSTS_SB_RE.match(line)
        if m:
            hand.actions.append(Action(m.group("name"), STREET_PREFLOP, "posts_sb", num(m.group("amt")), order))
            order += 1
            continue
        m = _POSTS_BB_RE.match(line)
        if m:
            hand.actions.append(Action(m.group("name"), STREET_PREFLOP, "posts_bb", num(m.group("amt")), order))
            order += 1
            continue
        m = _POSTS_ANTE_RE.match(line)
        if m:
            hand.actions.append(Action(m.group("name"), STREET_PREFLOP, "posts_ante", num(m.group("amt")), order))
            order += 1
            continue
        m = _POSTS_DEAD_RE.match(line)
        if m:
            hand.actions.append(Action(m.group("name"), STREET_PREFLOP, "posts_bb", num(m.group("amt")), order))
            order += 1
            continue

        m = _FOLDS_RE.match(line)
        if m:
            hand.actions.append(Action(m.group("name"), street, "folds", None, order))
            order += 1
            continue
        m = _CHECKS_RE.match(line)
        if m:
            hand.actions.append(Action(m.group("name"), street, "checks", None, order))
            order += 1
            continue
        m = _CALLS_RE.match(line)
        if m:
            hand.actions.append(Action(m.group("name"), street, "calls", num(m.group("amt")), order))
            order += 1
            continue
        m = _BETS_RE.match(line)
        if m:
            hand.actions.append(Action(m.group("name"), street, "bets", num(m.group("amt")), order))
            order += 1
            continue
        m = _RAISES_RE.match(line)
        if m:
            hand.actions.append(Action(m.group("name"), street, "raises", num(m.group("to")), order))
            order += 1
            continue

        m = _UNCALLED_RE.match(line)
        if m:
            hand.actions.append(Action(m.group("name"), street, "uncalled_return", num(m.group("amt")), order))
            order += 1
            continue
        m = _COLLECTED_RE.match(line)
        if m:
            hand.actions.append(Action(m.group("name"), street, "collected", num(m.group("amt")), order))
            order += 1
            continue

    for a in hand.actions:
        a.position = hand.positions.get(a.player)

    hand.results = compute_results(hand)
    return hand


def parse_file(
    path: str,
    site: str,
    parse_header: HeaderParser,
    hand_start_re: re.Pattern,
) -> list[Hand]:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        text = f.read()
    hands = []
    for raw in split_hands(text, hand_start_re):
        try:
            h = parse_hand(raw, site, parse_header)
        except ParseError as e:
            print(f"Failed to parse hand in {path}: {e}", file=sys.stderr)
            continue
        if h is not None:
            hands.append(h)
    return hands
