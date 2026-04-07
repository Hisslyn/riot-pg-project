# Riot Games → PostgreSQL Database Project

A PostgreSQL database system that ingests player and match data from the Riot Games API for **League of Legends**, **Teamfight Tactics**, and **Valorant**. The project demonstrates relational database design principles: normalization, referential integrity, constraint enforcement, indexing, and idempotent ETL.

---

## Database Design

### Entity-Relationship Overview

The database is built around one core idea: a **Riot account** (identified by a globally unique PUUID) can participate in matches across three different games. Each game has its own set of tables, but all share the central `accounts` table.

```
                              ┌──────────────┐
                              │   accounts   │  ← shared root entity
                              │  PK: puuid   │
                              │  UQ: (game_  │
                              │   name,tag)  │
                              └──────┬───────┘
                   ┌─────────────────┼─────────────────┐
                   │                 │                 │
           ┌───────▼──────┐   ┌──────▼───────┐         │
           │lol_summoners │   │tft_summoners │         │
           │ PK/FK: puuid │   │ PK/FK: puuid │         │
           └───────┬──────┘   └──────┬───────┘         │
                   │                 │                 │
        ┌──────────▼───┐      ┌──────▼────────┐        │
        │lol_ranked_   │      │tft_ranked_    │        │
        │   stats      │      │   stats       │        │
        │FK→summoners  │      │FK→summoners   │        │
        └──────────────┘      └───────────────┘        │
                                                       │
  ┌────────────────┐    ┌────────────────┐    ┌────────▼───────┐
  │  lol_matches   │    │  tft_matches   │    │  val_matches   │
  │ PK: match_id   │    │ PK: match_id   │    │ PK: match_id   │
  └───────┬────────┘    └───────┬────────┘    └────────┬───────┘
          │                     │                      │
  ┌───────▼────────┐     ┌──────▼─────────┐    ┌───────▼────────┐
  │ lol_match_     │     │ tft_match_     │    │ val_match_     │
  │ participants   │     │ participants   │    │ players        │
  │ FK→lol_matches │     │ FK→tft_matches │    │ FK→val_matches │
  └────────────────┘     └────────────────┘    └────────────────┘
```

**11 tables total** — 1 shared, 4 LoL, 4 TFT, 2 Valorant.

### Normalization

The schema is in **Third Normal Form (3NF)**:

- **1NF:** Every column holds atomic values. The one exception is `tft_match_participants.augments` which uses a PostgreSQL `TEXT[]` array — this is a deliberate choice because augments are always read/written as a set and never queried individually.
- **2NF:** No partial dependencies. Composite natural keys like `(puuid, queue_type)` in ranked stats are enforced via `UNIQUE` constraints on top of a surrogate `SERIAL` primary key.
- **3NF:** No transitive dependencies. Player profile data lives in `lol_summoners` / `tft_summoners`, not in the match participant rows. Ranked stats reference summoners, not accounts directly, reflecting the real-world dependency chain (you need a summoner profile before you can have ranked stats).

### Constraints and Data Integrity

| Constraint Type | Where Used | Purpose |
|---|---|---|
| **PRIMARY KEY** | Every table | Unique row identification |
| **FOREIGN KEY (CASCADE)** | All child tables | Referential integrity — deleting an account cascades to summoners, ranked stats; deleting a match cascades to all participant rows |
| **UNIQUE** | `accounts(game_name, tag_line)`, `ranked_stats(puuid, queue_type)`, all participant tables `(match_id, puuid)` | Prevents duplicate Riot IDs, duplicate ranked rows per queue, and duplicate player entries per match |
| **NOT NULL** | `accounts.game_name`, `accounts.tag_line`, all FK columns, `queue_type`, timestamps | Guarantees required data is always present |
| **CHECK** | `tft_match_participants.placement BETWEEN 1 AND 8` | Domain validation — TFT lobbies have exactly 8 players |
| **DEFAULT** | `created_at`, `updated_at`, `last_updated` default to `NOW()` | Automatic timestamping on INSERT |
| **TRIGGER** | `BEFORE UPDATE` on `accounts`, all summoner and ranked tables | Auto-updates `updated_at` / `last_updated` on every modification (PostgreSQL has no `ON UPDATE CURRENT_TIMESTAMP`) |

### Indexes

| Index | Table | Rationale |
|---|---|---|
| `ix_lol_matches_game_start` | `lol_matches` | All match queries sort by `game_start DESC` |
| `ix_tft_matches_game_datetime` | `tft_matches` | Same — sort by date |
| `ix_val_matches_game_start` | `val_matches` | Same — sort by date |
| `ix_*_participants_puuid` | All 3 participant tables | Filter a player's match history by PUUID |
| `ix_*_participants_match_id` | All 3 participant tables | Join participants back to their match |

Primary keys and unique constraints also generate implicit B-tree indexes.

### Design Decisions

**Why participant `puuid` is nullable with no FK to `accounts`:**
Each match stores stats for all players (10 in LoL, 8 in TFT, 10 in Valorant), but only the tracked player has a row in `accounts`. Adding an FK would require inserting an `accounts` row for every opponent — noise that adds no value. The `puuid` column is left nullable and un-referenced by design.

**Why `val_match_players` stores `game_name` + `tag_line`:**
This is intentional denormalization. For tracked players this data also exists in `accounts`, but for the other 9 opponents in a Valorant match, `accounts` has no row. Storing the name at match time also preserves the player's identity as it was during that match (Riot IDs can be changed).

**Why surrogate keys (`SERIAL id`) instead of composite natural keys:**
Tables like `lol_ranked_stats` could use `(puuid, queue_type)` as a composite PK. A surrogate `id` simplifies ORM operations and JOIN syntax while the natural key is still enforced via `UNIQUE`.

---

## Schema — Full DDL

See [`schema.sql`](schema.sql) — a standalone script that creates all 11 tables, indexes, constraints, and triggers. Can be run directly against PostgreSQL:

```bash
psql -d riot_data -f schema.sql
```

Or use the Python ORM (creates identical tables via SQLAlchemy):

```bash
python main.py init-db
```

### Table Reference

#### Shared
| Table | PK | Key Constraints | Description |
|---|---|---|---|
| `accounts` | `puuid` | `UNIQUE(game_name, tag_line)` | Riot account — central entity shared across all games |

#### League of Legends
| Table | PK | Key Constraints | Description |
|---|---|---|---|
| `lol_summoners` | `puuid` | FK → `accounts` CASCADE | Summoner profile (level, icon, region) |
| `lol_ranked_stats` | `id` | FK → `lol_summoners` CASCADE, `UNIQUE(puuid, queue_type)` | Ranked standings per queue |
| `lol_matches` | `match_id` | INDEX on `game_start` | Match metadata (duration, patch, mode) |
| `lol_match_participants` | `id` | FK → `lol_matches` CASCADE, `UNIQUE(match_id, puuid)` | All 10 players' stats per match |

#### Teamfight Tactics
| Table | PK | Key Constraints | Description |
|---|---|---|---|
| `tft_summoners` | `puuid` | FK → `accounts` CASCADE | Summoner profile |
| `tft_ranked_stats` | `id` | FK → `tft_summoners` CASCADE, `UNIQUE(puuid, queue_type)` | Ranked standings per queue |
| `tft_matches` | `match_id` | INDEX on `game_datetime` | Match metadata (set, length) |
| `tft_match_participants` | `id` | FK → `tft_matches` CASCADE, `UNIQUE(match_id, puuid)`, `CHECK(placement 1-8)` | Placement, level, augments per player |

#### Valorant
| Table | PK | Key Constraints | Description |
|---|---|---|---|
| `val_matches` | `match_id` | INDEX on `game_start` | Match metadata (map, mode, queue) |
| `val_match_players` | `id` | FK → `val_matches` CASCADE, `UNIQUE(match_id, puuid)` | Per-player stats (agent, KDA, headshots) |

> **Units:** `lol_matches.game_duration` → seconds; `tft_matches.game_length` → seconds (float); `val_matches.game_length` → milliseconds.

---

## Relational Schema (Formal Notation)

```
accounts(puuid PK, game_name, tag_line, created_at, updated_at)
    UNIQUE(game_name, tag_line)

lol_summoners(puuid PK FK→accounts, profile_icon_id, summoner_level, region, last_updated)
lol_ranked_stats(id PK, puuid FK→lol_summoners, queue_type, tier, rank, league_points, wins, losses, hot_streak, last_updated)
    UNIQUE(puuid, queue_type)
lol_matches(match_id PK, game_duration, game_version, queue_id, game_mode, game_type, game_start)
lol_match_participants(id PK, match_id FK→lol_matches, puuid, summoner_name, champion_name, champion_id, team_id, win, kills, deaths, assists, total_damage, gold_earned, vision_score, cs, position)
    UNIQUE(match_id, puuid)

tft_summoners(puuid PK FK→accounts, summoner_level, region, last_updated)
tft_ranked_stats(id PK, puuid FK→tft_summoners, queue_type, tier, rank, league_points, wins, losses, last_updated)
    UNIQUE(puuid, queue_type)
tft_matches(match_id PK, game_datetime, game_length, game_variation, tft_set_number)
tft_match_participants(id PK, match_id FK→tft_matches, puuid, placement, level, last_round, players_eliminated, augments, total_damage_to_players)
    UNIQUE(match_id, puuid)  CHECK(placement BETWEEN 1 AND 8)

val_matches(match_id PK, map_id, game_mode, game_length, queue_id, game_start, region)
val_match_players(id PK, match_id FK→val_matches, puuid, game_name, tag_line, agent_id, team_id, win, kills, deaths, assists, score, headshots, bodyshots, legshots)
    UNIQUE(match_id, puuid)
```

---

## Example Queries

See [`queries.sql`](queries.sql) for the full set. Highlights:

```sql
-- Recent LoL matches for a tracked player (uses FK chain: participants → matches)
SELECT m.match_id, m.game_mode, p.champion_name,
       p.kills, p.deaths, p.assists, p.win
FROM lol_matches m
JOIN lol_match_participants p ON m.match_id = p.match_id
JOIN accounts a ON p.puuid = a.puuid
WHERE a.game_name = 'Hide on bush' AND a.tag_line = 'KR1'
ORDER BY m.game_start DESC
LIMIT 10;

-- Champion win rate (aggregate with GROUP BY)
SELECT champion_name,
       COUNT(*) AS games,
       ROUND(AVG(CASE WHEN win THEN 1.0 ELSE 0.0 END) * 100, 1) AS win_pct,
       ROUND(AVG(kills::numeric), 2) AS avg_kills,
       ROUND(AVG(deaths::numeric), 2) AS avg_deaths
FROM lol_match_participants
WHERE puuid = (SELECT puuid FROM accounts
               WHERE game_name = 'Hide on bush' AND tag_line = 'KR1')
GROUP BY champion_name
ORDER BY games DESC;

-- TFT average placement per set (FILTER clause, PostgreSQL-specific)
SELECT m.tft_set_number,
       COUNT(*) AS games,
       ROUND(AVG(p.placement), 2) AS avg_placement,
       COUNT(*) FILTER (WHERE p.placement <= 4) AS top4s,
       COUNT(*) FILTER (WHERE p.placement = 1)  AS wins
FROM tft_match_participants p
JOIN tft_matches m ON p.match_id = m.match_id
WHERE p.puuid = (SELECT puuid FROM accounts
                 WHERE game_name = 'YourName' AND tag_line = 'NA1')
GROUP BY m.tft_set_number
ORDER BY m.tft_set_number DESC;

-- Valorant headshot rate (safe division with NULLIF)
SELECT game_name, tag_line,
       COUNT(*) AS matches,
       ROUND(
           SUM(headshots) * 100.0 /
           NULLIF(SUM(headshots + bodyshots + legshots), 0), 1
       ) AS hs_pct
FROM val_match_players
GROUP BY puuid, game_name, tag_line
ORDER BY hs_pct DESC;
```

---

## Project Structure

```
riot_pg_project/
├── database/
│   ├── connection.py      # SQLAlchemy engine + session factory
│   └── models.py          # ORM table definitions (11 tables)
├── api/
│   ├── base_client.py     # HTTP client: rate limiting, retries
│   ├── lol.py             # League of Legends API endpoints
│   ├── tft.py             # TFT API endpoints
│   └── valorant.py        # Valorant API endpoints
├── pipeline/
│   └── sync.py            # API → DB upsert logic (idempotent)
├── tests/
│   └── test_utils.py      # Unit tests for utility functions
├── scripts/
│   └── refresh_api_key.py # Browser-automated dev key rotation
├── schema.sql             # Standalone DDL script (all tables + triggers)
├── queries.sql            # Analytical SQL queries
├── config.py              # Environment variables + regional routing
├── main.py                # CLI entry point
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

---

## ETL Pipeline

The sync pipeline is **idempotent** — safe to re-run without creating duplicates:

1. **Account resolution:** Riot ID → PUUID via the Account API, upserted into `accounts`
2. **Profile sync:** Summoner data upserted by PUUID (INSERT or UPDATE)
3. **Ranked sync:** Upserted by natural key `(puuid, queue_type)`
4. **Match sync:** Bulk-prefetch existing `match_id` values into a Python set, skip any that already exist, fetch + INSERT only new ones. All participants for a match are inserted in a single transaction.

Each step commits separately so partial progress is preserved on failure.

---

## Setup

### Prerequisites
- Python 3.11+
- PostgreSQL (local or Docker)
- Riot Games API key from [developer.riotgames.com](https://developer.riotgames.com/)

### Steps

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your RIOT_API_KEY, DATABASE_URL, and (optionally) RIOT_USERNAME / RIOT_PASSWORD

# 3. Create database
psql -c "CREATE DATABASE riot_data;"

# 4. Initialize tables (either method works)
python main.py init-db          # via ORM
# OR
psql -d riot_data -f schema.sql # via raw DDL
```

### Sync data

```bash
python main.py lol --name "Hide on bush" --tag KR1 --region kr
python main.py tft --name "Hide on bush" --tag KR1 --region kr
python main.py val --name "YourName" --tag NA1 --val-region na
python main.py all --name "YourName" --tag NA1 --region na1 --val-region na

# Control match history depth (default: 10)
python main.py lol --name "Hide on bush" --tag KR1 --region kr --matches 20

# Auto-rotate an expired dev key before syncing (requires RIOT_USERNAME + RIOT_PASSWORD in .env)
python main.py lol --name "YourName" --tag NA1 --region na1 --refresh-key
```

### Dev setup (tests + key rotation)

```bash
pip install -r requirements-dev.txt
playwright install chromium   # only needed for scripts/refresh_api_key.py
```

---

## Region Codes

| Region | LoL/TFT (`--region`) | Valorant (`--val-region`) |
|---|---|---|
| North America | `na1` | `na` |
| Europe West | `euw1` | `eu` |
| Korea | `kr` | `kr` |
| Japan | `jp1` | `ap` |
| Brazil | `br1` | `na` |
| OCE | `oc1` | `ap` |
| Latin America | `la1` / `la2` | `na` |
| Southeast Asia | `sg2` / `ph2` etc. | `sea` |

---

## Testing

```bash
pytest tests/
```

Tests cover the `_ts` timestamp helper, the `_upsert` idempotency logic, rate-limit thread safety in `RiotClient`, and the `update_env_file` key-rotation utility. No database or network connection required.

---

## Rate Limiting

The API client enforces Riot's developer key limits:
- 20 requests / 1 second
- 100 requests / 2 minutes

On a `429` response, the client reads the `Retry-After` header and waits before retrying (up to 3 attempts).

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `403 Forbidden` | Expired API key | Regenerate at developer portal or use `--refresh-key` |
| `404 Not Found` | Wrong name / tag / region | Verify Riot ID and region code |
| `EnvironmentError: DATABASE_URL is not set` | Missing `.env` | `cp .env.example .env` and fill in values |
| `connection refused` | PostgreSQL not running | Start PostgreSQL; check `DATABASE_URL` |
| Tables not found | `init-db` not run | `python main.py init-db` or `psql -f schema.sql` |
