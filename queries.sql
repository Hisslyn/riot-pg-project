-- ============================================================
-- riot_pg_project — example analytical queries
-- Replace 'Hide on bush' / 'KR1' / 'YourName' / 'NA1'
-- with your tracked player's game_name and tag_line.
-- ============================================================


-- ----------------------------------------------------------------
-- LEAGUE OF LEGENDS
-- ----------------------------------------------------------------

-- Last 5 matches for a player (champion, KDA, win)
SELECT p.champion_name, p.kills, p.deaths, p.assists, p.win, p.position
FROM lol_match_participants p
JOIN lol_matches m ON p.match_id = m.match_id
WHERE p.puuid = (SELECT puuid FROM accounts WHERE game_name = 'Hide on bush' AND tag_line = 'KR1')
ORDER BY m.game_start DESC
LIMIT 5;

-- Win rate and average KDA per champion
SELECT champion_name,
       COUNT(*)                                                      AS games,
       ROUND(AVG(CASE WHEN win THEN 1.0 ELSE 0.0 END) * 100, 1)   AS win_pct,
       ROUND(AVG(kills::numeric), 2)                                AS avg_kills,
       ROUND(AVG(deaths::numeric), 2)                               AS avg_deaths,
       ROUND(AVG(assists::numeric), 2)                              AS avg_assists,
       ROUND(AVG(cs::numeric), 1)                                   AS avg_cs
FROM lol_match_participants
WHERE puuid = (SELECT puuid FROM accounts WHERE game_name = 'Hide on bush' AND tag_line = 'KR1')
GROUP BY champion_name
ORDER BY games DESC;

-- Current ranked standings
SELECT queue_type, tier, "rank", league_points, wins, losses,
       ROUND(wins * 100.0 / NULLIF(wins + losses, 0), 1) AS win_pct
FROM lol_ranked_stats
WHERE puuid = (SELECT puuid FROM accounts WHERE game_name = 'Hide on bush' AND tag_line = 'KR1');

-- All stored matches ordered by date
SELECT match_id, game_mode, game_type,
       ROUND(game_duration / 60.0, 1) AS duration_min,
       game_start
FROM lol_matches
ORDER BY game_start DESC;

-- Average CS per minute by position
SELECT position,
       COUNT(*) AS games,
       ROUND(AVG(cs * 60.0 / NULLIF(m.game_duration, 0)), 1) AS avg_cspm
FROM lol_match_participants p
JOIN lol_matches m ON p.match_id = m.match_id
WHERE p.puuid = (SELECT puuid FROM accounts WHERE game_name = 'Hide on bush' AND tag_line = 'KR1')
  AND m.game_duration > 0
GROUP BY position
ORDER BY games DESC;


-- ----------------------------------------------------------------
-- TEAMFIGHT TACTICS
-- ----------------------------------------------------------------

-- TFT placement history (most recent first)
SELECT m.match_id, m.tft_set_number, p.placement, p.level,
       ROUND(m.game_length / 60.0, 1) AS duration_min,
       m.game_datetime
FROM tft_match_participants p
JOIN tft_matches m ON p.match_id = m.match_id
WHERE p.puuid = (SELECT puuid FROM accounts WHERE game_name = 'YourName' AND tag_line = 'NA1')
ORDER BY m.game_datetime DESC;

-- Average placement per TFT set
SELECT m.tft_set_number,
       COUNT(*) AS games,
       ROUND(AVG(p.placement), 2) AS avg_placement,
       COUNT(*) FILTER (WHERE p.placement <= 4) AS top4_count,
       COUNT(*) FILTER (WHERE p.placement = 1)  AS wins
FROM tft_match_participants p
JOIN tft_matches m ON p.match_id = m.match_id
WHERE p.puuid = (SELECT puuid FROM accounts WHERE game_name = 'YourName' AND tag_line = 'NA1')
GROUP BY m.tft_set_number
ORDER BY m.tft_set_number DESC;


-- ----------------------------------------------------------------
-- VALORANT
-- ----------------------------------------------------------------

-- Recent Valorant matches for a player
SELECT m.match_id, m.map_id, m.game_mode,
       p.agent_id, p.kills, p.deaths, p.assists, p.score, p.win,
       m.game_start
FROM val_match_players p
JOIN val_matches m ON p.match_id = m.match_id
WHERE p.puuid = (SELECT puuid FROM accounts WHERE game_name = 'YourName' AND tag_line = 'NA1')
ORDER BY m.game_start DESC
LIMIT 10;

-- Headshot percentage per tracked player
SELECT game_name, tag_line,
       COUNT(*) AS matches,
       SUM(kills) AS total_kills,
       ROUND(
           SUM(headshots) * 100.0 /
           NULLIF(SUM(headshots + bodyshots + legshots), 0), 1
       ) AS hs_pct
FROM val_match_players
GROUP BY puuid, game_name, tag_line
ORDER BY hs_pct DESC;

-- Win rate per map
SELECT m.map_id,
       COUNT(*) AS games,
       ROUND(AVG(CASE WHEN p.win THEN 1.0 ELSE 0.0 END) * 100, 1) AS win_pct
FROM val_match_players p
JOIN val_matches m ON p.match_id = m.match_id
WHERE p.puuid = (SELECT puuid FROM accounts WHERE game_name = 'YourName' AND tag_line = 'NA1')
GROUP BY m.map_id
ORDER BY games DESC;


-- ----------------------------------------------------------------
-- CROSS-GAME
-- ----------------------------------------------------------------

-- All tracked accounts
SELECT puuid, game_name, tag_line, created_at, updated_at
FROM accounts
ORDER BY created_at;
