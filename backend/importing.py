"""Site auto-detection + parse dispatch, shared by the CLI (cli.py) and
the authenticated upload endpoint (api/routes.py) so the two never drift
into detecting/parsing files differently.
"""

from __future__ import annotations

from pathlib import Path

from parsers import ggpoker_parser, pokerstars_parser
from parsers.common import Hand

# Ordered by how specific the hand-start marker is — PokerStars' is a
# strict superset-looking prefix ("PokerStars Hand #" vs GGPoker's
# "Poker Hand #"), but the two never actually collide since "PokerStars"
# and "Poker " diverge at the 6th character, so order doesn't matter.
SITE_ADAPTERS = {
    "pokerstars": (pokerstars_parser, "PokerStars Hand #"),
    "ggpoker": (ggpoker_parser, "Poker Hand #"),
}


def detect_site(path: Path) -> str | None:
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


def parse_path(path: str, site: str = "auto") -> tuple[list[Hand], str | None]:
    """Detects (or uses the forced) site and parses the file. Returns
    (hands, resolved_site) — resolved_site is None if the header wasn't
    recognized at all, or a site name that may not have a registered
    parser (caller should check `resolved_site in SITE_ADAPTERS`)."""
    resolved_site = site if site != "auto" else detect_site(Path(path))
    if resolved_site is None or resolved_site not in SITE_ADAPTERS:
        return [], resolved_site
    module, _prefix = SITE_ADAPTERS[resolved_site]
    return module.parse_file(path), resolved_site
