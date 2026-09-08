"""Plain-assert smoke tests for the PokerStars parser, DB import, and
VPIP/PFR/3-bet% calculators. Run with: python tests/test_parser.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from datetime import datetime, timezone

from auth.security import hash_password
from db.importer import get_connection, import_hands, init_db
from parsers.pokerstars_parser import parse_file
from parsers.ggpoker_parser import parse_file as parse_ggpoker_file
from replay.builder import get_hand_replay
from stats.calculators import (
    HandFilters,
    PlayerStats,
    compute_hero_stats,
    compute_player_stats,
    compute_position_stats,
    list_hero_hands,
)
from stats.leak_finder import (
    _check_fold_to_raise_by_position,
    _check_limping,
    _check_overall_vpip,
    _check_three_bet_by_position,
    find_leaks,
)

SAMPLE = Path(__file__).parent / "sample_hands" / "hero_test_hands.txt"
SIDE_POT_SAMPLE = Path(__file__).parent / "sample_hands" / "side_pot_hands.txt"
TOURNAMENT_SAMPLE = Path(__file__).parent / "sample_hands" / "tournament_hand.txt"
GGPOKER_SAMPLE = Path(__file__).parent / "sample_hands" / "ggpoker_hand.txt"
LEAK_SAMPLE = Path(__file__).parent / "sample_hands" / "leak_test_hands.txt"


def _create_user(conn, email: str) -> int:
    cur = conn.execute(
        "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
        (email, hash_password("testpassword123"), datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    return cur.lastrowid


def test_parse_count_and_positions():
    hands = parse_file(str(SAMPLE))
    assert len(hands) == 5, f"expected 5 hands, got {len(hands)}"

    assert hands[0].hero_position == "UTG"
    assert hands[1].hero_position == "CO"
    assert hands[4].board == ["Ah", "9c", "2d", "5h", "Kc"]


def test_hero_results():
    hands = parse_file(str(SAMPLE))
    expected_results = [0.0, 0.75, -1.5, 2.25, 13.75]
    for h, expected in zip(hands, expected_results):
        actual = h.hero_result
        assert abs(actual - expected) < 0.01, (
            f"hand #{h.hand_number}: expected hero_result {expected}, got {actual}"
        )


def test_shown_cards_parsed():
    hands = parse_file(str(SAMPLE))
    h = hands[4]  # showdown hand: Hero and Player4 both show
    assert h.shown_cards.get("Hero") == "Ac Ad"
    assert h.shown_cards.get("Player4") == "Kd Qh"


def test_side_pot_split():
    hands = parse_file(str(SIDE_POT_SAMPLE))
    assert len(hands) == 2, f"expected 2 hands, got {len(hands)}"

    h = hands[0]  # 3-way all-in: main pot + side pot
    expected = {"Hero": -100.0, "Player2": 100.0, "Player3": 0.0}
    for name, exp in expected.items():
        actual = h.results.get(name)
        assert actual is not None and abs(actual - exp) < 0.01, (
            f"{name}: expected {exp}, got {actual}"
        )
    # Zero-sum check: whatever the exact split, total money in must equal total money out.
    assert abs(sum(h.results.values())) < 0.01, f"results don't sum to zero: {h.results}"


def test_short_stack_all_in_blind():
    hands = parse_file(str(SIDE_POT_SAMPLE))
    h = hands[1]  # Player2 posts big blind for less than a full BB, "and is all-in"
    assert h.hero_result is not None and abs(h.hero_result - 3.0) < 0.01, (
        f"expected hero_result 3.0, got {h.hero_result}"
    )
    assert abs(h.results.get("Player2", 0.0) - (-3.0)) < 0.01


def test_db_import_roundtrip(tmp_db="__test_poker.db"):
    db_path = Path(tmp_db)
    if db_path.exists():
        db_path.unlink()
    conn = get_connection(str(db_path))
    init_db(conn)
    user_id = _create_user(conn, "roundtrip@test.com")

    hands = parse_file(str(SAMPLE))
    imported, duplicates = import_hands(conn, hands, user_id)
    assert imported == 5, f"expected 5 imported, got {imported}"
    assert duplicates == 0

    # Re-importing the same hands should be a no-op (dedup on user+site+hand_number).
    imported2, duplicates2 = import_hands(conn, hands, user_id)
    assert imported2 == 0
    assert duplicates2 == 5

    row = conn.execute("SELECT COUNT(*) FROM hands").fetchone()
    assert row[0] == 5

    conn.close()
    db_path.unlink()


def test_vpip_pfr_3bet():
    db_path = Path("__test_poker2.db")
    if db_path.exists():
        db_path.unlink()
    conn = get_connection(str(db_path))
    init_db(conn)
    user_id = _create_user(conn, "vpip@test.com")

    hands = parse_file(str(SAMPLE))
    import_hands(conn, hands, user_id)

    stats = compute_player_stats(conn, "Hero", user_id)
    assert stats.hands == 5
    assert stats.vpip_pct == 80.0, f"expected VPIP 80.0, got {stats.vpip_pct}"
    assert stats.pfr_pct == 60.0, f"expected PFR 60.0, got {stats.pfr_pct}"
    assert stats.three_bet_opportunities == 2, (
        f"expected 2 three-bet opportunities, got {stats.three_bet_opportunities}"
    )
    assert stats.three_bet_pct == 50.0, f"expected 3-bet% 50.0, got {stats.three_bet_pct}"

    conn.close()
    db_path.unlink()


def test_replay_builder_pot_and_stacks():
    """Hand #200000002: Hero opens to $1.50, everyone folds, $1.00 uncalled
    is returned, Hero collects $1.25. Pot should end at 0 and Hero's stack
    should end at 50 (start) + 0.75 (hero_result) = 50.75."""
    db_path = Path("__test_replay.db")
    if db_path.exists():
        db_path.unlink()
    conn = get_connection(str(db_path))
    init_db(conn)
    user_id = _create_user(conn, "replay@test.com")

    hands = parse_file(str(SAMPLE))
    import_hands(conn, hands, user_id)

    row = conn.execute("SELECT id FROM hands WHERE hand_number = ?", ("200000002",)).fetchone()
    hand_id = row[0]
    replay = get_hand_replay(conn, hand_id, user_id)

    assert replay is not None
    assert len(replay["steps"]) == len(hands[1].actions)
    last_step = replay["steps"][-1]
    assert abs(last_step["pot_after"] - 0.0) < 0.01, f"expected pot 0.0, got {last_step['pot_after']}"
    assert abs(last_step["stacks_after"]["Hero"] - 50.75) < 0.01, (
        f"expected Hero stack 50.75, got {last_step['stacks_after']['Hero']}"
    )

    assert conn.execute("SELECT COUNT(*) FROM hands WHERE id = -1").fetchone()[0] == 0
    assert get_hand_replay(conn, -1, user_id) is None

    conn.close()
    db_path.unlink()


def test_ggpoker_parses():
    """The tournament header format is now verified against a real
    PokerCraft export (see ggpoker_parser.py's docstring) — this fixture
    matches that confirmed structure: buy-in embedded inside the
    tournament-name segment ("Mystery Battle Royale $5 Hold'em No
    Limit"), and the ante nested inside the blinds parens ("200(25)")
    rather than slash-separated. The cash header remains unverified."""
    hands = parse_ggpoker_file(str(GGPOKER_SAMPLE))
    assert len(hands) == 2, f"expected 2 hands, got {len(hands)}"

    cash, tourney = hands
    assert cash.site == "GGPoker"
    assert cash.format == "cash"
    assert cash.hero_position == "CO"
    assert abs(cash.hero_result - 0.15) < 0.01, f"expected 0.15, got {cash.hero_result}"

    assert tourney.format == "tournament"
    assert tourney.tournament_id == "555666777"
    assert tourney.buyin == "$5"
    assert tourney.game_type == "Hold'em No Limit"
    assert tourney.level == "1"
    assert tourney.big_blind == 200.0
    assert tourney.ante == 25.0
    assert tourney.hero_position == "SB"
    assert abs(tourney.hero_result - 625.0) < 0.01, f"expected 625.0, got {tourney.hero_result}"


def test_tournament_bb_per_100_excluded():
    """bb/100 is a cash-game concept — mixing in tournament chip-denominated
    blinds would silently produce a meaningless number."""
    db_path = Path("__test_poker3.db")
    if db_path.exists():
        db_path.unlink()
    conn = get_connection(str(db_path))
    init_db(conn)
    user_id = _create_user(conn, "bb100@test.com")

    cash_hands = parse_file(str(SAMPLE))
    tourney_hands = parse_file(str(TOURNAMENT_SAMPLE))
    import_hands(conn, cash_hands, user_id)
    import_hands(conn, tourney_hands, user_id)

    tourney_stats = compute_hero_stats(conn, HandFilters(user_id=user_id, format="tournament"))
    assert tourney_stats.hands == 1
    assert abs(tourney_stats.total_result - 625.0) < 0.01
    assert tourney_stats.bb_per_100 is None, (
        f"expected bb_per_100 None for tournament-only hands, got {tourney_stats.bb_per_100}"
    )

    cash_stats = compute_hero_stats(conn, HandFilters(user_id=user_id, format="cash"))
    assert cash_stats.bb_per_100 is not None

    conn.close()
    db_path.unlink()


def test_position_stats_and_fold_to_raise():
    """Hand 1: Hero (BB) folds to an MP raise. Hand 2: Hero (BB) calls the
    same spot, then folds postflop (shouldn't count as folding-to-raise,
    since that flag is preflop-only). Expect VPIP 50%, PFR 0%, 2 three-bet
    opportunities, 0 three-bets taken, and fold-to-raise 50% (1 of 2)."""
    db_path = Path("__test_leaks.db")
    if db_path.exists():
        db_path.unlink()
    conn = get_connection(str(db_path))
    init_db(conn)
    user_id = _create_user(conn, "leaks@test.com")

    hands = parse_file(str(LEAK_SAMPLE))
    import_hands(conn, hands, user_id)

    by_position = compute_position_stats(conn, HandFilters(user_id=user_id))
    assert "BB" in by_position, f"expected BB in position stats, got {list(by_position.keys())}"
    bb = by_position["BB"]
    assert bb.hands == 2
    assert bb.vpip_pct == 50.0, f"expected VPIP 50.0, got {bb.vpip_pct}"
    assert bb.pfr_pct == 0.0
    assert bb.three_bet_opportunities == 2
    assert bb.three_bet_pct == 0.0
    assert bb.fold_to_raise_pct == 50.0, f"expected fold_to_raise_pct 50.0, got {bb.fold_to_raise_pct}"

    conn.close()
    db_path.unlink()


def test_leak_finder_insufficient_data():
    """With well under MIN_HANDS_OVERALL hands imported, find_leaks must
    say so rather than confidently flagging leaks off a handful of hands —
    the same failure mode as the earlier bb/100-on-one-hand bug."""
    db_path = Path("__test_leaks2.db")
    if db_path.exists():
        db_path.unlink()
    conn = get_connection(str(db_path))
    init_db(conn)
    user_id = _create_user(conn, "insufficient@test.com")

    import_hands(conn, parse_file(str(SAMPLE)), user_id)
    flags = find_leaks(conn, HandFilters(user_id=user_id))
    assert len(flags) == 1 and flags[0].rule_id == "insufficient_data", (
        f"expected a single insufficient_data flag, got {flags}"
    )

    conn.close()
    db_path.unlink()


def test_leak_rule_thresholds():
    """White-box checks on the individual rule functions with hand-built
    PlayerStats, so the comparison directions (too high vs too low, which
    baseline applies to which position) are verified directly rather than
    requiring dozens of synthetic hands to hit each threshold via the DB."""
    loose = PlayerStats("Hero", hands=40, vpip_pct=40.0, pfr_pct=35.0, three_bet_pct=8.0, three_bet_opportunities=20)
    flags = _check_overall_vpip(loose)
    assert len(flags) == 1 and flags[0].rule_id == "vpip_too_high"

    normal = PlayerStats("Hero", hands=40, vpip_pct=24.0, pfr_pct=20.0, three_bet_pct=8.0, three_bet_opportunities=20)
    assert _check_overall_vpip(normal) == []

    limpy = PlayerStats("Hero", hands=40, vpip_pct=25.0, pfr_pct=10.0, three_bet_pct=8.0, three_bet_opportunities=20)
    flags = _check_limping(limpy)
    assert len(flags) == 1 and flags[0].rule_id == "limping_too_much"

    pos_stats = {
        "BB": PlayerStats("Hero", hands=25, vpip_pct=40.0, pfr_pct=5.0, three_bet_pct=2.0, three_bet_opportunities=20),
        "BTN": PlayerStats("Hero", hands=25, vpip_pct=40.0, pfr_pct=30.0, three_bet_pct=10.0, three_bet_opportunities=20),
    }
    flags = _check_three_bet_by_position(pos_stats)
    assert len(flags) == 1 and flags[0].position == "BB", f"expected only BB flagged, got {flags}"

    fold_stats = {
        "BB": PlayerStats("Hero", hands=25, vpip_pct=40.0, pfr_pct=5.0, three_bet_pct=5.0,
                           three_bet_opportunities=20, fold_to_raise_pct=85.0),
        "CO": PlayerStats("Hero", hands=25, vpip_pct=30.0, pfr_pct=25.0, three_bet_pct=10.0,
                           three_bet_opportunities=20, fold_to_raise_pct=50.0),
    }
    flags = _check_fold_to_raise_by_position(fold_stats)
    assert len(flags) == 1 and flags[0].position == "BB", f"expected only BB flagged, got {flags}"


def test_multi_user_isolation():
    """Two users each import the same fixture — each must only ever see
    their own hands (stats, hands-list, replay), and dedup must be
    per-user (not global), since two different people can legitimately
    hold "the same" hand from having played at the same table."""
    db_path = Path("__test_multiuser.db")
    if db_path.exists():
        db_path.unlink()
    conn = get_connection(str(db_path))
    init_db(conn)

    alice = _create_user(conn, "alice@test.com")
    bob = _create_user(conn, "bob@test.com")

    hands = parse_file(str(SAMPLE))
    imported_a, _ = import_hands(conn, hands, alice)
    assert imported_a == 5

    bob_stats = compute_hero_stats(conn, HandFilters(user_id=bob))
    assert bob_stats.hands == 0, f"expected Bob to see 0 hands before importing, got {bob_stats.hands}"
    assert list_hero_hands(conn, HandFilters(user_id=bob)) == []

    alice_stats = compute_hero_stats(conn, HandFilters(user_id=alice))
    assert alice_stats.hands == 5

    # Same (site, hand_number) pairs as Alice's — must import cleanly for
    # Bob since dedup is scoped per-user, not global.
    imported_b, duplicates_b = import_hands(conn, hands, bob)
    assert imported_b == 5, f"expected Bob's import to succeed independently of Alice's, got {imported_b}"
    assert duplicates_b == 0

    alice_hand_id = conn.execute("SELECT id FROM hands WHERE user_id = ? LIMIT 1", (alice,)).fetchone()[0]
    assert get_hand_replay(conn, alice_hand_id, bob) is None, "Bob must not see Alice's hand by id"
    assert get_hand_replay(conn, alice_hand_id, alice) is not None

    conn.close()
    db_path.unlink()


if __name__ == "__main__":
    tests = [
        test_parse_count_and_positions,
        test_hero_results,
        test_shown_cards_parsed,
        test_side_pot_split,
        test_short_stack_all_in_blind,
        test_db_import_roundtrip,
        test_vpip_pfr_3bet,
        test_replay_builder_pot_and_stacks,
        test_ggpoker_parses,
        test_tournament_bb_per_100_excluded,
        test_position_stats_and_fold_to_raise,
        test_leak_finder_insufficient_data,
        test_leak_rule_thresholds,
        test_multi_user_isolation,
    ]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {t.__name__}: {e}")
    if failures:
        print(f"\n{failures} test(s) failed")
        sys.exit(1)
    print("\nAll tests passed")
