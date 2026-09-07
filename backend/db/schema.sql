-- Poker Hand Tracker schema (Phase 1: PokerStars only)

CREATE TABLE IF NOT EXISTS hands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site TEXT NOT NULL,
    hand_number TEXT NOT NULL,
    format TEXT NOT NULL,              -- 'cash' or 'tournament'
    game_type TEXT NOT NULL,           -- e.g. "Hold'em No Limit"
    tournament_id TEXT,
    buyin TEXT,
    level TEXT,                        -- tournament level label, e.g. "V"
    stakes TEXT,                       -- "0.25/0.50" (cash) or "100/200" (tourney level blinds)
    small_blind REAL,
    big_blind REAL,
    ante REAL,
    currency TEXT,
    table_name TEXT,
    table_size INTEGER,
    button_seat INTEGER,
    date TEXT NOT NULL,                -- ISO 8601
    hero_name TEXT,
    hero_seat INTEGER,
    hero_position TEXT,
    hero_cards TEXT,
    board TEXT,
    pot_size REAL,
    rake REAL,
    hero_result REAL,
    raw_text TEXT NOT NULL,
    UNIQUE(site, hand_number)
);

CREATE TABLE IF NOT EXISTS hand_players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hand_id INTEGER NOT NULL REFERENCES hands(id) ON DELETE CASCADE,
    player_name TEXT NOT NULL,
    seat INTEGER NOT NULL,
    starting_stack REAL,
    position TEXT,
    is_hero INTEGER NOT NULL DEFAULT 0,
    net_result REAL,
    shown_cards TEXT
);

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hand_id INTEGER NOT NULL REFERENCES hands(id) ON DELETE CASCADE,
    player_name TEXT NOT NULL,
    street TEXT NOT NULL,              -- preflop, flop, turn, river
    action_type TEXT NOT NULL,         -- posts_sb, posts_bb, posts_ante, folds, checks, calls, bets, raises
    amount REAL,
    action_order INTEGER NOT NULL,
    position TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    site TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    hands_played INTEGER,
    net_result REAL
);

CREATE INDEX IF NOT EXISTS idx_actions_hand_id ON actions(hand_id);
CREATE INDEX IF NOT EXISTS idx_hand_players_hand_id ON hand_players(hand_id);
CREATE INDEX IF NOT EXISTS idx_hand_players_player_name ON hand_players(player_name);
CREATE INDEX IF NOT EXISTS idx_hands_date ON hands(date);
