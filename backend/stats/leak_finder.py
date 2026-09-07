"""Rule-based leak detection: compares hero's overall and per-position
preflop stats against rough "reasonable reg" baselines and flags
deviations worth a look.

These baselines are generic heuristics, not solved-game/GTO numbers or
anything stake/format-specific — they're a starting point for noticing
patterns, not a verdict. Every flag also states the sample size behind
it, since a stat built on a handful of hands is noise, not a leak.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from stats.calculators import HandFilters, PlayerStats, compute_hero_stats, compute_position_stats

MIN_HANDS_OVERALL = 30
MIN_HANDS_POSITION = 20
MIN_OPPORTUNITIES = 15

VPIP_HIGH = 32.0
VPIP_LOW = 15.0
LIMP_GAP_MAX = 8.0  # VPIP - PFR: how much of VPIP is limping rather than raising

IN_POSITION = {"BTN", "CO"}
THREE_BET_LOW_IP = 6.0
THREE_BET_LOW_OOP = 4.0

FOLD_TO_RAISE_HIGH = {"BB": 75.0, "SB": 82.0}
FOLD_TO_RAISE_HIGH_DEFAULT = 70.0


@dataclass
class LeakFlag:
    rule_id: str
    severity: str  # 'warning' | 'info'
    title: str
    detail: str
    position: str | None
    value: float | None
    sample_size: int


def _check_overall_vpip(overall: PlayerStats) -> list[LeakFlag]:
    if overall.hands < MIN_HANDS_OVERALL:
        return []
    flags = []
    if overall.vpip_pct > VPIP_HIGH:
        flags.append(LeakFlag(
            rule_id="vpip_too_high",
            severity="warning",
            title="Playing too many hands preflop",
            detail=(
                f"Your overall VPIP is {overall.vpip_pct}% over {overall.hands} hands — "
                f"most solid regs sit under {VPIP_HIGH}%. You may be entering pots too "
                f"loosely, especially from early position."
            ),
            position=None,
            value=overall.vpip_pct,
            sample_size=overall.hands,
        ))
    elif overall.vpip_pct < VPIP_LOW:
        flags.append(LeakFlag(
            rule_id="vpip_too_low",
            severity="info",
            title="Playing quite tight preflop",
            detail=(
                f"Your overall VPIP is {overall.vpip_pct}% over {overall.hands} hands — "
                f"below {VPIP_LOW}% usually means missing out on profitable steals and "
                f"speculative hands, especially in position."
            ),
            position=None,
            value=overall.vpip_pct,
            sample_size=overall.hands,
        ))
    return flags


def _check_limping(overall: PlayerStats) -> list[LeakFlag]:
    if overall.hands < MIN_HANDS_OVERALL:
        return []
    gap = round(overall.vpip_pct - overall.pfr_pct, 1)
    if gap > LIMP_GAP_MAX:
        return [LeakFlag(
            rule_id="limping_too_much",
            severity="warning",
            title="Limping instead of raising",
            detail=(
                f"The gap between your VPIP ({overall.vpip_pct}%) and PFR ({overall.pfr_pct}%) "
                f"is {gap} points over {overall.hands} hands — a gap over {LIMP_GAP_MAX} usually "
                f"means a lot of your voluntary pots are limps rather than raises. Open-raising "
                f"instead of limping generally wins more, both by taking down uncontested pots "
                f"and by playing bigger pots in position."
            ),
            position=None,
            value=gap,
            sample_size=overall.hands,
        )]
    return []


def _check_three_bet_by_position(position_stats: dict[str, PlayerStats]) -> list[LeakFlag]:
    flags = []
    for position, stats in position_stats.items():
        if stats.three_bet_opportunities < MIN_OPPORTUNITIES:
            continue
        baseline = THREE_BET_LOW_IP if position in IN_POSITION else THREE_BET_LOW_OOP
        if stats.three_bet_pct < baseline:
            flags.append(LeakFlag(
                rule_id="three_bet_too_low",
                severity="warning",
                title=f"Low 3-bet% from {position}",
                detail=(
                    f"Your 3-bet% from {position} is {stats.three_bet_pct}% over "
                    f"{stats.three_bet_opportunities} opportunities — under {baseline}% "
                    f"from {'in position' if position in IN_POSITION else 'out of position'} "
                    f"usually means folding or flat-calling too often instead of "
                    f"re-raising with your strongest hands."
                ),
                position=position,
                value=stats.three_bet_pct,
                sample_size=stats.three_bet_opportunities,
            ))
    return flags


def _check_fold_to_raise_by_position(position_stats: dict[str, PlayerStats]) -> list[LeakFlag]:
    flags = []
    for position, stats in position_stats.items():
        if stats.three_bet_opportunities < MIN_OPPORTUNITIES or stats.fold_to_raise_pct is None:
            continue
        baseline = FOLD_TO_RAISE_HIGH.get(position, FOLD_TO_RAISE_HIGH_DEFAULT)
        if stats.fold_to_raise_pct > baseline:
            flags.append(LeakFlag(
                rule_id="folding_too_much_to_raise",
                severity="warning",
                title=f"Folding too much from {position}",
                detail=(
                    f"You fold to a preflop raise from {position} {stats.fold_to_raise_pct}% "
                    f"of the time over {stats.three_bet_opportunities} opportunities — above "
                    f"{baseline}% usually means giving up pots your pot odds and position "
                    f"justify continuing with more often."
                ),
                position=position,
                value=stats.fold_to_raise_pct,
                sample_size=stats.three_bet_opportunities,
            ))
    return flags


def find_leaks(conn: sqlite3.Connection, filters: HandFilters | None = None) -> list[LeakFlag]:
    overall = compute_hero_stats(conn, filters)
    if overall.hands < MIN_HANDS_OVERALL:
        return [LeakFlag(
            rule_id="insufficient_data",
            severity="info",
            title="Not enough hands yet",
            detail=(
                f"Leak detection needs at least {MIN_HANDS_OVERALL} hands in range to say "
                f"anything reliable — you have {overall.hands}. Import more hands or widen "
                f"the date range."
            ),
            position=None,
            value=overall.hands,
            sample_size=overall.hands,
        )]

    position_stats = compute_position_stats(conn, filters)

    flags: list[LeakFlag] = []
    flags += _check_overall_vpip(overall)
    flags += _check_limping(overall)
    flags += _check_three_bet_by_position(position_stats)
    flags += _check_fold_to_raise_by_position(position_stats)
    return flags
