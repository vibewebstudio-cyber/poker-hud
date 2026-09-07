"""CLI for importing hand histories into SQLite and printing basic stats,
without needing the web UI running.

Usage:
    python cli.py import <file_or_folder> [--db poker.db] [--site auto|pokerstars|ggpoker]
    python cli.py stats <player_name> [--db poker.db]
    python cli.py players [--db poker.db]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from db.importer import get_connection, import_hands, init_db
from parsers import ggpoker_parser, pokerstars_parser
from stats.calculators import compute_player_stats, list_players

# Ordered by how specific the hand-start marker is — PokerStars' is a
# strict superset-looking prefix ("PokerStars Hand #" vs GGPoker's
# "Poker Hand #"), but the two never actually collide since "PokerStars"
# and "Poker " diverge at the 6th character, so order doesn't matter.
SITE_ADAPTERS = {
    "pokerstars": (pokerstars_parser, "PokerStars Hand #"),
    "ggpoker": (ggpoker_parser, "Poker Hand #"),
}


def _detect_site(path: Path) -> str | None:
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            for site, (_module, prefix) in SITE_ADAPTERS.items():
                if stripped.startswith(prefix):
                    return site
            return None
    return None


def cmd_import(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    init_db(conn)

    target = Path(args.path)
    files = [target] if target.is_file() else sorted(target.glob("*.txt"))
    if not files:
        print(f"No .txt files found at {target}", file=sys.stderr)
        sys.exit(1)

    total_imported = 0
    total_duplicates = 0
    for f in files:
        site = args.site if args.site != "auto" else _detect_site(f)
        if site is None:
            print(f"{f.name}: couldn't detect the site (unrecognized header) — skipped", file=sys.stderr)
            continue
        if site not in SITE_ADAPTERS:
            print(f"{f.name}: no parser available for '{site}' yet — skipped", file=sys.stderr)
            continue

        module, _prefix = SITE_ADAPTERS[site]
        hands = module.parse_file(str(f))
        imported, duplicates = import_hands(conn, hands)
        print(f"{f.name} [{site}]: parsed {len(hands)} hands, imported {imported}, skipped {duplicates} duplicates")
        total_imported += imported
        total_duplicates += duplicates

    print(f"\nTotal: imported {total_imported}, skipped {total_duplicates} duplicates")


def cmd_stats(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    stats = compute_player_stats(conn, args.player)
    if stats.hands == 0:
        print(f"No hands found for player '{args.player}'")
        return
    print(f"Player:    {stats.player_name}")
    print(f"Hands:     {stats.hands}")
    print(f"VPIP:      {stats.vpip_pct}%")
    print(f"PFR:       {stats.pfr_pct}%")
    print(f"3-Bet:     {stats.three_bet_pct}% ({stats.three_bet_opportunities} opportunities)")


def cmd_players(args: argparse.Namespace) -> None:
    conn = get_connection(args.db)
    for name in list_players(conn):
        print(name)


def main() -> None:
    parser = argparse.ArgumentParser(description="Poker hand tracker CLI (Phase 1)")
    parser.add_argument("--db", default="poker.db", help="Path to SQLite database file")
    sub = parser.add_subparsers(dest="command", required=True)

    p_import = sub.add_parser("import", help="Import hand history file(s)")
    p_import.add_argument("path", help="Path to a hand history .txt file or a folder of them")
    p_import.add_argument(
        "--site",
        choices=["auto", *SITE_ADAPTERS.keys()],
        default="auto",
        help="Force a site adapter instead of auto-detecting from the file header",
    )
    p_import.set_defaults(func=cmd_import)

    p_stats = sub.add_parser("stats", help="Show VPIP/PFR/3-bet% for a player")
    p_stats.add_argument("player", help="Exact player name as it appears in hand histories")
    p_stats.set_defaults(func=cmd_stats)

    p_players = sub.add_parser("players", help="List all player names seen in the database")
    p_players.set_defaults(func=cmd_players)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
