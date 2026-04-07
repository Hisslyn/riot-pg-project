"""
SQLAlchemy models for Riot Games data.
Covers: Shared accounts, League of Legends, TFT, and Valorant.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, BigInteger, Boolean,
    Float, DateTime, ForeignKey, Text, ARRAY, UniqueConstraint, Index,
    CheckConstraint,
)
from database.connection import Base


def _utcnow():
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

class Account(Base):
    """
    Riot account (shared across all games).
    Identified by PUUID — a universal player identifier.
    game_name + tag_line is the human-readable Riot ID and is globally unique.
    """
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("game_name", "tag_line", name="uq_accounts_riot_id"),
    )

    puuid      = Column(String(78), primary_key=True)
    game_name  = Column(String(64), nullable=False)
    tag_line   = Column(String(16), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    def __repr__(self):
        return f"<Account {self.game_name}#{self.tag_line}>"


# ---------------------------------------------------------------------------
# League of Legends
# ---------------------------------------------------------------------------

class LoLSummoner(Base):
    """Summoner profile data (LoL-specific)."""
    __tablename__ = "lol_summoners"

    puuid            = Column(String(78), ForeignKey("accounts.puuid", ondelete="CASCADE"), primary_key=True)
    profile_icon_id  = Column(Integer)
    summoner_level   = Column(BigInteger)
    region           = Column(String(8))
    last_updated     = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class LoLRankedStats(Base):
    """Ranked queue standings for a summoner."""
    __tablename__ = "lol_ranked_stats"
    __table_args__ = (UniqueConstraint("puuid", "queue_type", name="uq_lol_ranked_puuid_queue"),)

    id           = Column(Integer, primary_key=True, autoincrement=True)
    puuid        = Column(String(78), ForeignKey("lol_summoners.puuid", ondelete="CASCADE"), nullable=False)
    queue_type   = Column(String(32), nullable=False)  # e.g. RANKED_SOLO_5x5
    tier         = Column(String(16))   # e.g. GOLD
    rank         = Column(String(4))    # e.g. II
    league_points = Column(Integer)
    wins         = Column(Integer)
    losses       = Column(Integer)
    hot_streak   = Column(Boolean)
    last_updated = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class LoLMatch(Base):
    """High-level LoL match metadata."""
    __tablename__ = "lol_matches"
    __table_args__ = (
        Index("ix_lol_matches_game_start", "game_start"),
    )

    match_id      = Column(String(32), primary_key=True)
    game_duration = Column(Integer)       # seconds
    game_version  = Column(String(32))
    queue_id      = Column(Integer)
    game_mode     = Column(String(32))
    game_type     = Column(String(32))
    game_start    = Column(DateTime(timezone=True))


class LoLMatchParticipant(Base):
    """One player's stats within a LoL match."""
    __tablename__ = "lol_match_participants"
    __table_args__ = (
        UniqueConstraint("match_id", "puuid", name="uq_lol_match_participants_match_puuid"),
        Index("ix_lol_match_participants_puuid", "puuid"),
        Index("ix_lol_match_participants_match_id", "match_id"),
    )

    id              = Column(Integer, primary_key=True, autoincrement=True)
    match_id        = Column(String(32), ForeignKey("lol_matches.match_id", ondelete="CASCADE"), nullable=False)
    puuid           = Column(String(78), nullable=True)  # all 10 participants; no FK since only tracked players have accounts
    summoner_name   = Column(String(64))
    champion_name   = Column(String(32))
    champion_id     = Column(Integer)
    team_id         = Column(Integer)
    win             = Column(Boolean)
    kills           = Column(Integer)
    deaths          = Column(Integer)
    assists         = Column(Integer)
    total_damage    = Column(BigInteger)
    gold_earned     = Column(Integer)
    vision_score    = Column(Integer)
    cs              = Column(Integer)   # total minions + jungle CS
    position        = Column(String(16))


# ---------------------------------------------------------------------------
# Teamfight Tactics
# ---------------------------------------------------------------------------

class TFTSummoner(Base):
    """TFT summoner profile."""
    __tablename__ = "tft_summoners"

    puuid            = Column(String(78), ForeignKey("accounts.puuid", ondelete="CASCADE"), primary_key=True)
    summoner_level   = Column(BigInteger)
    region           = Column(String(8))
    last_updated     = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class TFTRankedStats(Base):
    """TFT ranked queue standings."""
    __tablename__ = "tft_ranked_stats"
    __table_args__ = (UniqueConstraint("puuid", "queue_type", name="uq_tft_ranked_puuid_queue"),)

    id            = Column(Integer, primary_key=True, autoincrement=True)
    puuid         = Column(String(78), ForeignKey("tft_summoners.puuid", ondelete="CASCADE"), nullable=False)
    queue_type    = Column(String(32), nullable=False)
    tier          = Column(String(16))
    rank          = Column(String(4))
    league_points = Column(Integer)
    wins          = Column(Integer)
    losses        = Column(Integer)
    last_updated  = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)


class TFTMatch(Base):
    """High-level TFT match metadata."""
    __tablename__ = "tft_matches"
    __table_args__ = (
        Index("ix_tft_matches_game_datetime", "game_datetime"),
    )

    match_id       = Column(String(32), primary_key=True)
    game_datetime  = Column(DateTime(timezone=True))
    game_length    = Column(Float)     # seconds
    game_variation = Column(String(64))
    tft_set_number = Column(Integer)


class TFTMatchParticipant(Base):
    """One player's result in a TFT lobby."""
    __tablename__ = "tft_match_participants"
    __table_args__ = (
        UniqueConstraint("match_id", "puuid", name="uq_tft_match_participants_match_puuid"),
        CheckConstraint("placement BETWEEN 1 AND 8", name="ck_tft_placement_range"),
        Index("ix_tft_match_participants_puuid", "puuid"),
        Index("ix_tft_match_participants_match_id", "match_id"),
    )

    id          = Column(Integer, primary_key=True, autoincrement=True)
    match_id    = Column(String(32), ForeignKey("tft_matches.match_id", ondelete="CASCADE"), nullable=False)
    puuid       = Column(String(78), nullable=True)  # all lobby players; no FK since only tracked players have accounts
    placement   = Column(Integer)           # 1–8
    level       = Column(Integer)
    last_round  = Column(Integer)
    players_eliminated = Column(Integer)
    augments    = Column(ARRAY(Text))       # list of augment IDs
    total_damage_to_players = Column(Integer)


# ---------------------------------------------------------------------------
# Valorant
# ---------------------------------------------------------------------------

class ValMatch(Base):
    """High-level Valorant match metadata."""
    __tablename__ = "val_matches"
    __table_args__ = (
        Index("ix_val_matches_game_start", "game_start"),
    )

    match_id    = Column(String(64), primary_key=True)
    map_id      = Column(String(128))
    game_mode   = Column(String(32))
    game_length = Column(Integer)        # milliseconds
    queue_id    = Column(String(32))
    game_start  = Column(DateTime(timezone=True))
    region      = Column(String(8))


class ValMatchPlayer(Base):
    """One player's stats in a Valorant match."""
    __tablename__ = "val_match_players"
    __table_args__ = (
        UniqueConstraint("match_id", "puuid", name="uq_val_match_players_match_puuid"),
        Index("ix_val_match_players_puuid", "puuid"),
        Index("ix_val_match_players_match_id", "match_id"),
    )

    id           = Column(Integer, primary_key=True, autoincrement=True)
    match_id     = Column(String(64), ForeignKey("val_matches.match_id", ondelete="CASCADE"), nullable=False)
    puuid        = Column(String(78), nullable=True)  # all match players; no FK since only tracked players have accounts
    game_name    = Column(String(64))
    tag_line     = Column(String(16))
    agent_id     = Column(String(64))
    team_id      = Column(String(8))
    win          = Column(Boolean)
    kills        = Column(Integer)
    deaths       = Column(Integer)
    assists      = Column(Integer)
    score        = Column(Integer)        # combat score
    headshots    = Column(Integer)
    bodyshots    = Column(Integer)
    legshots     = Column(Integer)
