# Poker Hand Tracker

Self-built hand history tracker/analyzer (PokerTracker 4-style, no live HUD).
Imports hand history exports, stores them in SQLite, computes preflop stats,
replays hands action-by-action, and flags rule-of-thumb preflop leaks.

Supports real accounts — each person's imported hands are private to their
own account, so this can be run as a shared, public instance and not just a
personal local tool.

## Status

| Site | Parser status |
|---|---|
| PokerStars | Working, tested against synthetic hands. **Not yet run against a real export.** |
| GGPoker (tournament) | **Verified against a real PokerCraft export** (292 Mystery Battle Royale tournament files, 7,313 hands, 0 parse errors, hand count matched PokerCraft's own total exactly). |
| GGPoker (cash) | Implemented against a best-guess format. **Still unverified** — the real sample used only had tournament hands. |
| CoinPoker | Not implemented. Export format is unconfirmed; `parsers/coinpoker_parser.py` fails loudly with what's needed to build it. |

One caveat surfaced by the real GGPoker run: the leak finder's baselines
(`stats/leak_finder.py`) are generic heuristics tuned for roughly normal
ring-game/MTT dynamics — a fast, bounty-driven, rapidly-shortening-field
format like Mystery Battle Royale may not fit them well (e.g. folding a lot
to raises from late position when frequently short-stacked near the bubble
isn't necessarily a leak). Treat flags against unusual formats skeptically
until the baselines are tuned per format.

PokerStars and GGPoker cash games still haven't been checked against real
files — do that before trusting numbers from either.

**If you have a `poker.db` from before accounts existed**: it predates the
`users` table and won't work with the current schema. Delete it and
re-import your hands under a real account (CLI import auto-creates a fixed
local account — see below — or use the web Import page after signing up).

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

## Running it locally

Two processes, in two terminals:

```bash
cd backend
uvicorn api.routes:app --port 8001
```

```bash
cd frontend
npm run dev -- --port 5174
```

Then open http://localhost:5174 and sign up (any email/password — this is
your local instance). `uvicorn --reload` has been unreliable on Windows in
this project (the file watcher fires but the old worker keeps serving stale
code) — after editing backend code, stop and restart the process rather
than relying on reload.

(Ports 8000/5173 are avoided here because another unrelated app on this
machine already uses them — adjust freely if that's not true for you, just
keep `frontend/src/lib/api.js`'s `API_BASE` and the backend port in sync.)

Backend env vars (all optional, sensible local defaults):
- `DB_PATH` — SQLite file path (default: `backend/poker.db`)
- `JWT_SECRET` — signs auth tokens (default: an insecure fixed dev value —
  **must** be set to something real for any hosted deployment, or anyone
  who knows the default could forge login tokens)
- `CORS_ORIGINS` — comma-separated allowed origins (default: any
  `localhost` port, for local dev)

## Importing hand histories

Two ways in:

**Web UI** (what a hosted deployment's users do): sign up, then use the
Import page to upload `.txt` files — site is auto-detected per file.

**CLI** (local use, no login needed):
```bash
cd backend
python cli.py import <file_or_folder>          # site auto-detected per file
python cli.py import <file> --site pokerstars  # force a specific adapter
python cli.py stats Hero                       # quick VPIP/PFR/3-bet check, no UI needed
```
CLI imports go under a fixed local account (auto-created on first use), so
this keeps working without ever needing to sign in.

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
expected values, not just "it parsed without crashing" — and a dedicated
multi-user test confirms two accounts never see each other's hands.

## Deploying it publicly

**Frontend → Cloudflare Pages**: connect this repo, build command
`npm run build` (root directory `frontend`), output directory `dist`, env
var `VITE_API_URL` set to your deployed backend URL (below).

**Backend → Fly.io** (chosen specifically because it supports a persistent
disk — SQLite would otherwise be silently wiped on every restart/redeploy
on a typical free serverless host):
```bash
cd backend
fly launch          # interactive first-time setup; reads fly.toml
fly volumes create poker_hud_data --size 1   # persistent disk for poker.db
fly secrets set JWT_SECRET=$(openssl rand -hex 32)
fly secrets set CORS_ORIGINS=https://your-app.pages.dev
fly deploy
```
Both `fly launch` (which needs `fly auth login` with your own account) and
creating the Cloudflare Pages project have to happen on your end — account
creation and interactive login aren't things that can be scripted for you.

After deploying, verify isolation on the live URL exactly like the local
dev checks: sign up, import a hand, confirm it shows up; sign up a second
account and confirm it sees nothing.

## Project layout

```
backend/
  parsers/          # one adapter per site, sharing parsers/common.py
  db/                # SQLite schema + import (now user-scoped)
  auth/              # password hashing + JWT (security.py)
  stats/             # VPIP/PFR/3-bet/position calculators + leak_finder.py
  replay/            # reconstructs pot/stack state action-by-action
  api/               # FastAPI routes (routes.py) + auth endpoints (auth_routes.py)
  importing.py       # site auto-detection, shared by cli.py and the /api/import endpoint
  cli.py             # import/stats without the web UI (local account, no login)
  tests/             # test_parser.py + hand-verified sample hand histories
  Dockerfile, fly.toml  # backend hosting config
frontend/
  src/pages/         # Dashboard, Hands, Replayer, Leaks, Login, Signup, Import
  src/components/    # StatCard, FilterPanel, ProfitGraph, ReplayTable, ReplayControls
  src/lib/           # api.js (fetch wrappers), auth.jsx (login state), format.js
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
- No password reset flow, no email verification — signup/login only.
- Auth tokens live in localStorage rather than an httpOnly cookie (a
  deliberate tradeoff for a frontend/backend split across two hosting
  origins — see `auth/security.py`'s docstring).
