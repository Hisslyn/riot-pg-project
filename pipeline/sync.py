"""
Data sync pipeline — fetches from the Riot API and upserts into PostgreSQL.
Each function is idempotent: safe to re-run without creating duplicates.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from api.base_client import RiotClient
from api.lol import LoLAPI
from api.tft import TFTAPI
from api.valorant import ValorantAPI
from database.models import (
    Account,
    LoLSummoner, LoLRankedStats, LoLMatch, LoLMatchParticipant,
    TFTSummoner, TFTRankedStats, TFTMatch, TFTMatchParticipant,
    ValMatch, ValMatchPlayer,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upsert(session: Session, model_class, pk_field: str, pk_value, data: dict):
    """
    Insert or update a single row.
    pk_field: name of the primary-key attribute on the model.
    """
    obj = session.get(model_class, pk_value)
    if obj is None:
        obj = model_class(**data)
        session.add(obj)
    else:
        for k, v in data.items():
            setattr(obj, k, v)
    return obj


def _ts(ms: int | None) -> datetime | None:
    """Convert epoch milliseconds to a UTC datetime, or None if missing."""
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)


# ---------------------------------------------------------------------------
# Account (shared)
# ---------------------------------------------------------------------------

def sync_account(session: Session, game_name: str, tag_line: str, region: str) -> str:
    """
    Resolve a Riot ID → PUUID and store in accounts table.
    Returns the PUUID.
    """
    api = RiotClient()
    data = api.get_account_by_riot_id(game_name, tag_line, region)
    puuid = data["puuid"]
    _upsert(session, Account, "puuid", puuid, {
        "puuid":      puuid,
        "game_name":  data["gameName"],
        "tag_line":   data["tagLine"],
        "updated_at": datetime.now(timezone.utc),
    })
    session.commit()
    print(f"✅ Account synced: {game_name}#{tag_line} → {puuid[:8]}...")
    return puuid


# ---------------------------------------------------------------------------
# League of Legends
# ---------------------------------------------------------------------------

def sync_lol_player(
    session: Session,
    game_name: str,
    tag_line: str,
    region: str,
    match_count: int = 10,
):
    """Full LoL sync: account → summoner → ranked → matches."""
    api = LoLAPI()

    puuid = sync_account(session, game_name, tag_line, region)

    # Summoner
    summoner = api.get_summoner_by_puuid(puuid, region)
    _upsert(session, LoLSummoner, "puuid", puuid, {
        "puuid":           puuid,
        "profile_icon_id": summoner.get("profileIconId"),
        "summoner_level":  summoner.get("summonerLevel"),
        "region":          region,
    })
    session.commit()
    print(f"  LoL summoner synced (level {summoner.get('summonerLevel')})")

    # Ranked stats — upsert per (puuid, queue_type) to stay atomic
    ranked_entries = api.get_ranked_stats(puuid, region)
    for entry in ranked_entries:
        obj = session.query(LoLRankedStats).filter_by(
            puuid=puuid, queue_type=entry.get("queueType")
        ).first()
        data = dict(
            puuid=puuid,
            queue_type=entry.get("queueType"),
            tier=entry.get("tier"),
            rank=entry.get("rank"),
            league_points=entry.get("leaguePoints"),
            wins=entry.get("wins"),
            losses=entry.get("losses"),
            hot_streak=entry.get("hotStreak", False),
        )
        if obj is None:
            session.add(LoLRankedStats(**data))
        else:
            for k, v in data.items():
                setattr(obj, k, v)
    session.commit()
    print(f"  LoL ranked stats synced ({len(ranked_entries)} queues)")

    # Matches — bulk-prefetch existing IDs to avoid N+1 queries
    match_ids = api.get_match_ids(puuid, region, count=match_count)
    existing = {r for (r,) in session.query(LoLMatch.match_id).filter(LoLMatch.match_id.in_(match_ids))}
    new_matches = 0
    for match_id in match_ids:
        if match_id in existing:
            continue
        raw = api.get_match(match_id, region)
        info = raw["info"]

        session.add(LoLMatch(
            match_id=match_id,
            game_duration=info.get("gameDuration"),
            game_version=info.get("gameVersion"),
            queue_id=info.get("queueId"),
            game_mode=info.get("gameMode"),
            game_type=info.get("gameType"),
            game_start=_ts(info.get("gameStartTimestamp")),
        ))

        for p in info.get("participants", []):
            session.add(LoLMatchParticipant(
                match_id=match_id,
                puuid=p.get("puuid"),
                summoner_name=p.get("summonerName"),
                champion_name=p.get("championName"),
                champion_id=p.get("championId"),
                team_id=p.get("teamId"),
                win=p.get("win"),
                kills=p.get("kills"),
                deaths=p.get("deaths"),
                assists=p.get("assists"),
                total_damage=p.get("totalDamageDealtToChampions"),
                gold_earned=p.get("goldEarned"),
                vision_score=p.get("visionScore"),
                cs=p.get("totalMinionsKilled", 0) + p.get("neutralMinionsKilled", 0),
                position=p.get("teamPosition"),
            ))
        new_matches += 1

    session.commit()
    print(f"  LoL matches synced: {new_matches} new / {len(match_ids)} total")


# ---------------------------------------------------------------------------
# Teamfight Tactics
# ---------------------------------------------------------------------------

def sync_tft_player(
    session: Session,
    game_name: str,
    tag_line: str,
    region: str,
    match_count: int = 10,
):
    """Full TFT sync: account → summoner → ranked → matches."""
    api = TFTAPI()

    puuid = sync_account(session, game_name, tag_line, region)

    # Summoner
    summoner = api.get_summoner_by_puuid(puuid, region)
    _upsert(session, TFTSummoner, "puuid", puuid, {
        "puuid":          puuid,
        "summoner_level": summoner.get("summonerLevel"),
        "region":         region,
    })
    session.commit()

    # Ranked stats — upsert per (puuid, queue_type)
    ranked_entries = api.get_ranked_stats(puuid, region)
    for entry in ranked_entries:
        obj = session.query(TFTRankedStats).filter_by(
            puuid=puuid, queue_type=entry.get("queueType")
        ).first()
        data = dict(
            puuid=puuid,
            queue_type=entry.get("queueType"),
            tier=entry.get("tier"),
            rank=entry.get("rank"),
            league_points=entry.get("leaguePoints"),
            wins=entry.get("wins"),
            losses=entry.get("losses"),
        )
        if obj is None:
            session.add(TFTRankedStats(**data))
        else:
            for k, v in data.items():
                setattr(obj, k, v)
    session.commit()
    print(f"  TFT ranked stats synced ({len(ranked_entries)} queues)")

    # Matches — bulk-prefetch existing IDs to avoid N+1 queries
    match_ids = api.get_match_ids(puuid, region, count=match_count)
    existing = {r for (r,) in session.query(TFTMatch.match_id).filter(TFTMatch.match_id.in_(match_ids))}
    new_matches = 0
    for match_id in match_ids:
        if match_id in existing:
            continue
        raw = api.get_match(match_id, region)
        info = raw["info"]

        session.add(TFTMatch(
            match_id=match_id,
            game_datetime=_ts(info.get("game_datetime")),
            game_length=info.get("game_length"),
            game_variation=info.get("game_variation", ""),
            tft_set_number=info.get("tft_set_number"),
        ))

        for p in info.get("participants", []):
            session.add(TFTMatchParticipant(
                match_id=match_id,
                puuid=p.get("puuid"),
                placement=p.get("placement"),
                level=p.get("level"),
                last_round=p.get("last_round"),
                players_eliminated=p.get("players_eliminated"),
                augments=p.get("augments", []),
                total_damage_to_players=p.get("total_damage_to_players"),
            ))
        new_matches += 1

    session.commit()
    print(f"  TFT matches synced: {new_matches} new / {len(match_ids)} total")


# ---------------------------------------------------------------------------
# Valorant
# ---------------------------------------------------------------------------

def sync_val_player(
    session: Session,
    game_name: str,
    tag_line: str,
    region: str,
    match_count: int = 10,
):
    """Sync Valorant match history for a player."""
    api = ValorantAPI()

    puuid = sync_account(session, game_name, tag_line, region)

    # Matches — bulk-prefetch existing IDs to avoid N+1 queries
    match_ids = api.get_match_ids_by_puuid(puuid, region)[:match_count]
    existing = {r for (r,) in session.query(ValMatch.match_id).filter(ValMatch.match_id.in_(match_ids))}
    new_matches = 0
    for match_id in match_ids:
        if match_id in existing:
            continue
        raw = api.get_match(match_id, region)

        m_info = raw.get("matchInfo", {})
        session.add(ValMatch(
            match_id=match_id,
            map_id=m_info.get("mapId"),
            game_mode=m_info.get("gameMode"),
            game_length=m_info.get("gameLength"),
            queue_id=m_info.get("queueId"),
            game_start=_ts(m_info.get("gameStartMillis")),
            region=region,
        ))

        # Determine winning team
        winning_team = None
        for team in raw.get("teams", []):
            if team.get("won"):
                winning_team = team.get("teamId")

        for p in raw.get("players", []):
            stats = p.get("stats", {})
            session.add(ValMatchPlayer(
                match_id=match_id,
                puuid=p.get("puuid"),
                game_name=p.get("gameName"),
                tag_line=p.get("tagLine"),
                agent_id=p.get("characterId"),
                team_id=p.get("teamId"),
                win=(p.get("teamId") == winning_team),
                kills=stats.get("kills"),
                deaths=stats.get("deaths"),
                assists=stats.get("assists"),
                score=stats.get("score"),
                headshots=stats.get("headShots"),
                bodyshots=stats.get("bodyShots"),
                legshots=stats.get("legShots"),
            ))
        new_matches += 1

    session.commit()
    print(f"  Valorant matches synced: {new_matches} new / {len(match_ids)} total")
