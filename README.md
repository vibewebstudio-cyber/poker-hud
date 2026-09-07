# Poker Hand Tracker

Self-built hand history tracker/analyzer (PokerTracker 4-style, no live HUD).
Imports hand history exports, stores them in SQLite, computes preflop stats,
replays hands action-by-action, and flags rule-of-thumb preflop leaks.

## Status

| Site | Parser status |
|---|---|
| PokerStars | Working, tested against synthetic hands. **Not yet run against a real export.** |
| GGPoker (tournament) | **Verified against a real PokerCraft export** (292 Mystery Battle Royale tournament files, 7,313 hands, 0 parse errors, hand count matched PokerCraft's own total exactly). |
| GGPoker (cash) | Implemented against a best-guess format. **Still unverified** — the real sample used only had tournament hands. |
| CoinPoker | Not implemented. Export format is unconfirmed; `parsers/coinpoker_parser.py` fails loudly with what's needed to build it. |

The dashboard/replayer/leak-finder pipeline has now also been run end-to-end
on the real GGPoker data above with zero errors. One caveat surfaced by that
run: the leak finder's baselines (`stats/leak_finder.py`) are generic
heuristics tuned for roughly normal ring-game/MTT dynamics — a fast,
bounty-driven, rapidly-shortening-field format like Mystery Battle Royale
may not fit them well (e.g. folding a lot to raises from late position when
frequently short-stacked near the bubble isn't necessarily a leak). Treat
flags against unusual formats skeptically until the baselines are tuned
per format.

PokerStars and GGPoker cash games still haven't been checked against real
files — do that before trusting numbers from either.

## Setup

### Backend

Requires Python 3.10+.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### Frontend

Requires Node 18+.

```bash
cd frontend
npm install
```

## Running it

Two processes, in two terminals:

```bash
cd backend
uvicorn api.routes:app --port 8001
```

```bash
cd frontend
npm run dev -- --port 5174
```

Then open http://localhost:5174.

(Ports 8000/5173 are avoided here because another unrelated app on this
machine already uses them — adjust freely if that's not true for you, just
keep `frontend/src/lib/api.js`'s `API_BASE` and the backend port in sync.)

`uvicorn --reload` has been unreliable on Windows in this project (the file
watcher fires but the old worker keeps serving stale code) — after editing
backend code, stop and restart the process rather than relying on reload.

## Importing hand histories

```bash
cd backend
python cli.py import <file_or_folder>          # site auto-detected per file
python cli.py import <file> --site pokerstars  # force a specific adapter
python cli.py stats Hero                       # quick VPIP/PFR/3-bet check, no UI needed
```

Auto-detection reads each file's first line to pick PokerStars vs GGPoker.
A file it doesn't recognize is skipped with a message rather than silently
mis-parsed.

## Running the tests

```bash
cd backend
python tests/test_parser.py
```

Plain-assert tests, no pytest dependency. All money math (pot sizes, stack
tracking, side pots, ante handling) is verified against hand-checked
expected values, not just "it parsed without crashing."

## Project layout

```
backend/
  parsers/          # one adapter per site, sharing parsers/common.py
  db/                # SQLite schema + import
  stats/             # VPIP/PFR/3-bet/position calculators + leak_finder.py
  replay/            # reconstructs pot/stack state action-by-action
  api/               # FastAPI routes consumed by the frontend
  cli.py             # import/stats without the web UI
  tests/             # test_parser.py + hand-verified sample hand histories
frontend/
  src/pages/         # Dashboard, Hands, Replayer, Leaks
  src/components/    # StatCard, FilterPanel, ProfitGraph, ReplayTable, ReplayControls
  src/lib/           # api.js (fetch wrappers), format.js (money/action formatting)
```

## Known gaps

- No session tracking yet (the `sessions` table exists in the schema but
  nothing writes to it).
- No WTSD, W$SD, or aggression-factor stats — only VPIP/PFR/3-bet%/
  fold-to-raise are implemented.
- No positional-stats page in the UI (the backend computes it for the leak
  finder, but there's no dedicated view for it).
- No variance/EV line on the profit graph.
- Tournament hand results are in tournament chips, not real money — hand
  histories don't carry finishing place or payout, so true $ ROI isn't
  derivable from them alone.
