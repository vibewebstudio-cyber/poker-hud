"""Site adapter for CoinPoker — NOT YET IMPLEMENTED.

Unlike GGPoker (whose PokerCraft export format is at least publicly
discussed enough to build a best-effort parser against), CoinPoker's
hand-history export format is genuinely unconfirmed: the spec's own
open questions flagged "check current export options; likely
downloadable hand history similar to GGPoker's model" as unresolved,
and there's no reliable public reference for its exact text/CSV
structure.

Fabricating a parser against a guessed format here would be worse than
not having one — it would silently produce numbers that look plausible
but aren't grounded in anything real. So this module fails loudly
instead, with what's needed to actually implement it.

To implement this adapter:
1. Get one real hand-history export from CoinPoker (Settings > History
   or equivalent in the client).
2. Confirm whether it's a text format similar to PokerStars/GGPoker, or
   CSV, or something else entirely.
3. If it's text-based and structurally similar to the other two sites,
   this can likely follow the same pattern as ggpoker_parser.py: a
   site-specific header regex feeding into parsers.common.parse_hand /
   parse_file. If it's CSV or otherwise structurally different, it'll
   need its own parsing logic rather than reusing parsers.common.
"""

from __future__ import annotations

SITE = "CoinPoker"


def parse_file(path: str) -> list:
    raise NotImplementedError(
        "CoinPoker's hand-history export format hasn't been confirmed yet. "
        "Provide a real exported file so this adapter can be built against "
        "the actual format instead of a guess — see this module's docstring."
    )
