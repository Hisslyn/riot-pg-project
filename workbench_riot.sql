-- ============================================================
-- Riot Games DB — MySQL Workbench Relational Schema
-- ============================================================
-- Import this file into MySQL Workbench:
--   File → New Model → (menu) Database → Reverse Engineer…
--   OR: File → New Model → right-click schema → Forward Engineer from Script
-- This produces the EER diagram / relational schema automatically.
--
-- Note: adapted from PostgreSQL source (schema.sql) for MySQL 8.x.
--   • TIMESTAMPTZ → DATETIME
--   • SERIAL → INT AUTO_INCREMENT
--   • TEXT[] (arrays) → JSON  (Workbench renders it as a column)
--   • Triggers omitted — Workbench shows them separately
-- ============================================================

SET FOREIGN_KEY_CHECKS = 0;

-- ──────────────────────────────────────────
-- SHARED
-- ──────────────────────────────────────────

CREATE TABLE accounts (
    puuid       VARCHAR(78)  NOT NULL,
    game_name   VARCHAR(64)  NOT NULL,
    tag_line    VARCHAR(16)  NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (puuid),
    UNIQUE KEY uq_accounts_riot_id (game_name, tag_line)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ──────────────────────────────────────────
-- LEAGUE OF LEGENDS
-- ──────────────────────────────────────────

CREATE TABLE lol_summoners (
    puuid            VARCHAR(78)  NOT NULL,
    profile_icon_id  INT,
    summoner_level   BIGINT,
    region           VARCHAR(8),
    last_updated     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (puuid),
    CONSTRAINT fk_lol_sum_account
        FOREIGN KEY (puuid) REFERENCES accounts(puuid) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE lol_ranked_stats (
    id              INT          NOT NULL AUTO_INCREMENT,
    puuid           VARCHAR(78)  NOT NULL,
    queue_type      VARCHAR(32)  NOT NULL,
    tier            VARCHAR(16),
    `rank`          VARCHAR(4),
    league_points   INT,
    wins            INT,
    losses          INT,
    hot_streak      TINYINT(1),
    last_updated    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_lol_ranked_puuid_queue (puuid, queue_type),
    CONSTRAINT fk_lol_rank_summoner
        FOREIGN KEY (puuid) REFERENCES lol_summoners(puuid) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE lol_matches (
    match_id       VARCHAR(32)  NOT NULL,
    game_duration  INT,
    game_version   VARCHAR(32),
    queue_id       INT,
    game_mode      VARCHAR(32),
    game_type      VARCHAR(32),
    game_start     DATETIME,

    PRIMARY KEY (match_id),
    INDEX ix_lol_matches_game_start (game_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE lol_match_participants (
    id              INT          NOT NULL AUTO_INCREMENT,
    match_id        VARCHAR(32)  NOT NULL,
    puuid           VARCHAR(78),
    summoner_name   VARCHAR(64),
    champion_name   VARCHAR(32),
    champion_id     INT,
    team_id         INT,
    win             TINYINT(1),
    kills           INT,
    deaths          INT,
    assists         INT,
    total_damage    BIGINT,
    gold_earned     INT,
    vision_score    INT,
    cs              INT,
    position        VARCHAR(16),

    PRIMARY KEY (id),
    UNIQUE KEY uq_lol_part_match_puuid (match_id, puuid),
    INDEX ix_lol_part_puuid    (puuid),
    INDEX ix_lol_part_match_id (match_id),
    CONSTRAINT fk_lol_part_match
        FOREIGN KEY (match_id) REFERENCES lol_matches(match_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ──────────────────────────────────────────
-- TEAMFIGHT TACTICS
-- ──────────────────────────────────────────

CREATE TABLE tft_summoners (
    puuid          VARCHAR(78)  NOT NULL,
    summoner_level BIGINT,
    region         VARCHAR(8),
    last_updated   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (puuid),
    CONSTRAINT fk_tft_sum_account
        FOREIGN KEY (puuid) REFERENCES accounts(puuid) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE tft_ranked_stats (
    id              INT          NOT NULL AUTO_INCREMENT,
    puuid           VARCHAR(78)  NOT NULL,
    queue_type      VARCHAR(32)  NOT NULL,
    tier            VARCHAR(16),
    `rank`          VARCHAR(4),
    league_points   INT,
    wins            INT,
    losses          INT,
    last_updated    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_tft_ranked_puuid_queue (puuid, queue_type),
    CONSTRAINT fk_tft_rank_summoner
        FOREIGN KEY (puuid) REFERENCES tft_summoners(puuid) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE tft_matches (
    match_id        VARCHAR(32)  NOT NULL,
    game_datetime   DATETIME,
    game_length     FLOAT,
    game_variation  VARCHAR(64),
    tft_set_number  INT,

    PRIMARY KEY (match_id),
    INDEX ix_tft_matches_game_datetime (game_datetime)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE tft_match_participants (
    id                       INT          NOT NULL AUTO_INCREMENT,
    match_id                 VARCHAR(32)  NOT NULL,
    puuid                    VARCHAR(78),
    placement                INT,
    level                    INT,
    last_round               INT,
    players_eliminated       INT,
    augments                 JSON,
    total_damage_to_players  INT,

    PRIMARY KEY (id),
    UNIQUE KEY uq_tft_part_match_puuid (match_id, puuid),
    INDEX ix_tft_part_puuid    (puuid),
    INDEX ix_tft_part_match_id (match_id),
    CONSTRAINT ck_tft_placement CHECK (placement BETWEEN 1 AND 8),
    CONSTRAINT fk_tft_part_match
        FOREIGN KEY (match_id) REFERENCES tft_matches(match_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


-- ──────────────────────────────────────────
-- VALORANT
-- ──────────────────────────────────────────

CREATE TABLE val_matches (
    match_id    VARCHAR(64)  NOT NULL,
    map_id      VARCHAR(128),
    game_mode   VARCHAR(32),
    game_length INT,
    queue_id    VARCHAR(32),
    game_start  DATETIME,
    region      VARCHAR(8),

    PRIMARY KEY (match_id),
    INDEX ix_val_matches_game_start (game_start)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE val_match_players (
    id          INT          NOT NULL AUTO_INCREMENT,
    match_id    VARCHAR(64)  NOT NULL,
    puuid       VARCHAR(78),
    game_name   VARCHAR(64),
    tag_line    VARCHAR(16),
    agent_id    VARCHAR(64),
    team_id     VARCHAR(8),
    win         TINYINT(1),
    kills       INT,
    deaths      INT,
    assists     INT,
    score       INT,
    headshots   INT,
    bodyshots   INT,
    legshots    INT,

    PRIMARY KEY (id),
    UNIQUE KEY uq_val_player_match_puuid (match_id, puuid),
    INDEX ix_val_player_puuid    (puuid),
    INDEX ix_val_player_match_id (match_id),
    CONSTRAINT fk_val_player_match
        FOREIGN KEY (match_id) REFERENCES val_matches(match_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
