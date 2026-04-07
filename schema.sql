-- ============================================================
-- Riot Games PostgreSQL Project — CREATE DDL Script
-- ============================================================
--
-- 11 tables across 3 games, unified by a shared accounts table.
-- Enforces:  PKs, FKs (CASCADE), UNIQUE, CHECK, NOT NULL, triggers.
-- Run once against a fresh database:
--     psql -d riot_data -f schema.sql
-- Or let the Python ORM create them:
--     python main.py init-db
-- ============================================================


-- ----------------------------------------------------------------
-- Trigger functions  (PostgreSQL has no ON UPDATE CURRENT_TIMESTAMP;
-- these BEFORE UPDATE triggers keep timestamp columns accurate.)
-- ----------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION set_last_updated()
RETURNS TRIGGER AS $$
BEGIN
    NEW.last_updated = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


-- ================================================================
-- SHARED
-- ================================================================

CREATE TABLE accounts (
    puuid       VARCHAR(78)  PRIMARY KEY,
    game_name   VARCHAR(64)  NOT NULL,
    tag_line    VARCHAR(16)  NOT NULL,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_accounts_riot_id UNIQUE (game_name, tag_line)
);

CREATE TRIGGER trg_accounts_updated_at
    BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();


-- ================================================================
-- LEAGUE OF LEGENDS
-- ================================================================

CREATE TABLE lol_summoners (
    puuid            VARCHAR(78)  PRIMARY KEY
                         REFERENCES accounts(puuid) ON DELETE CASCADE,
    profile_icon_id  INTEGER,
    summoner_level   BIGINT,
    region           VARCHAR(8),
    last_updated     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_lol_summoners_last_updated
    BEFORE UPDATE ON lol_summoners
    FOR EACH ROW EXECUTE FUNCTION set_last_updated();


CREATE TABLE lol_ranked_stats (
    id              SERIAL       PRIMARY KEY,
    puuid           VARCHAR(78)  NOT NULL
                        REFERENCES lol_summoners(puuid) ON DELETE CASCADE,
    queue_type      VARCHAR(32)  NOT NULL,        -- e.g. RANKED_SOLO_5x5
    tier            VARCHAR(16),                   -- e.g. GOLD
    rank            VARCHAR(4),                    -- e.g. II
    league_points   INTEGER,
    wins            INTEGER,
    losses          INTEGER,
    hot_streak      BOOLEAN,
    last_updated    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_lol_ranked_puuid_queue UNIQUE (puuid, queue_type)
);

CREATE TRIGGER trg_lol_ranked_stats_last_updated
    BEFORE UPDATE ON lol_ranked_stats
    FOR EACH ROW EXECUTE FUNCTION set_last_updated();


CREATE TABLE lol_matches (
    match_id       VARCHAR(32)  PRIMARY KEY,
    game_duration  INTEGER,                        -- seconds
    game_version   VARCHAR(32),
    queue_id       INTEGER,
    game_mode      VARCHAR(32),
    game_type      VARCHAR(32),
    game_start     TIMESTAMPTZ
);

CREATE INDEX ix_lol_matches_game_start ON lol_matches (game_start);


CREATE TABLE lol_match_participants (
    id              SERIAL       PRIMARY KEY,
    match_id        VARCHAR(32)  NOT NULL
                        REFERENCES lol_matches(match_id) ON DELETE CASCADE,
    puuid           VARCHAR(78),                   -- all 10 players; nullable because
                                                   -- non-tracked players have no accounts row
    summoner_name   VARCHAR(64),
    champion_name   VARCHAR(32),
    champion_id     INTEGER,
    team_id         INTEGER,
    win             BOOLEAN,
    kills           INTEGER,
    deaths          INTEGER,
    assists         INTEGER,
    total_damage    BIGINT,
    gold_earned     INTEGER,
    vision_score    INTEGER,
    cs              INTEGER,                       -- creep score: minions + jungle
    position        VARCHAR(16),

    CONSTRAINT uq_lol_participants_match_puuid UNIQUE (match_id, puuid)
);

CREATE INDEX ix_lol_participants_puuid    ON lol_match_participants (puuid);
CREATE INDEX ix_lol_participants_match_id ON lol_match_participants (match_id);


-- ================================================================
-- TEAMFIGHT TACTICS
-- ================================================================

CREATE TABLE tft_summoners (
    puuid          VARCHAR(78)  PRIMARY KEY
                       REFERENCES accounts(puuid) ON DELETE CASCADE,
    summoner_level BIGINT,
    region         VARCHAR(8),
    last_updated   TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TRIGGER trg_tft_summoners_last_updated
    BEFORE UPDATE ON tft_summoners
    FOR EACH ROW EXECUTE FUNCTION set_last_updated();


CREATE TABLE tft_ranked_stats (
    id              SERIAL       PRIMARY KEY,
    puuid           VARCHAR(78)  NOT NULL
                        REFERENCES tft_summoners(puuid) ON DELETE CASCADE,
    queue_type      VARCHAR(32)  NOT NULL,
    tier            VARCHAR(16),
    rank            VARCHAR(4),
    league_points   INTEGER,
    wins            INTEGER,
    losses          INTEGER,
    last_updated    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_tft_ranked_puuid_queue UNIQUE (puuid, queue_type)
);

CREATE TRIGGER trg_tft_ranked_stats_last_updated
    BEFORE UPDATE ON tft_ranked_stats
    FOR EACH ROW EXECUTE FUNCTION set_last_updated();


CREATE TABLE tft_matches (
    match_id        VARCHAR(32)  PRIMARY KEY,
    game_datetime   TIMESTAMPTZ,
    game_length     FLOAT,                         -- seconds
    game_variation  VARCHAR(64),
    tft_set_number  INTEGER
);

CREATE INDEX ix_tft_matches_game_datetime ON tft_matches (game_datetime);


CREATE TABLE tft_match_participants (
    id                       SERIAL       PRIMARY KEY,
    match_id                 VARCHAR(32)  NOT NULL
                                 REFERENCES tft_matches(match_id) ON DELETE CASCADE,
    puuid                    VARCHAR(78),           -- nullable: non-tracked players
    placement                INTEGER,
    level                    INTEGER,
    last_round               INTEGER,
    players_eliminated       INTEGER,
    augments                 TEXT[],                -- PostgreSQL array of augment IDs
    total_damage_to_players  INTEGER,

    CONSTRAINT uq_tft_participants_match_puuid UNIQUE (match_id, puuid),
    CONSTRAINT ck_tft_placement_range CHECK (placement BETWEEN 1 AND 8)
);

CREATE INDEX ix_tft_participants_puuid    ON tft_match_participants (puuid);
CREATE INDEX ix_tft_participants_match_id ON tft_match_participants (match_id);


-- ================================================================
-- VALORANT
-- ================================================================

CREATE TABLE val_matches (
    match_id    VARCHAR(64)  PRIMARY KEY,
    map_id      VARCHAR(128),
    game_mode   VARCHAR(32),
    game_length INTEGER,                           -- milliseconds
    queue_id    VARCHAR(32),
    game_start  TIMESTAMPTZ,
    region      VARCHAR(8)
);

CREATE INDEX ix_val_matches_game_start ON val_matches (game_start);


CREATE TABLE val_match_players (
    id          SERIAL       PRIMARY KEY,
    match_id    VARCHAR(64)  NOT NULL
                    REFERENCES val_matches(match_id) ON DELETE CASCADE,
    puuid       VARCHAR(78),                       -- nullable: non-tracked players
    game_name   VARCHAR(64),
    tag_line    VARCHAR(16),
    agent_id    VARCHAR(64),
    team_id     VARCHAR(8),
    win         BOOLEAN,
    kills       INTEGER,
    deaths      INTEGER,
    assists     INTEGER,
    score       INTEGER,                           -- combat score
    headshots   INTEGER,
    bodyshots   INTEGER,
    legshots    INTEGER,

    CONSTRAINT uq_val_players_match_puuid UNIQUE (match_id, puuid)
);

CREATE INDEX ix_val_players_puuid    ON val_match_players (puuid);
CREATE INDEX ix_val_players_match_id ON val_match_players (match_id);
