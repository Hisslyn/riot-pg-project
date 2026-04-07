"""
Teamfight Tactics API endpoints.
Docs: https://developer.riotgames.com/apis#tft-match-v1
"""

from config import REGIONAL_ROUTES
from api.base_client import RiotClient


class TFTAPI(RiotClient):

    def get_summoner_by_puuid(self, puuid: str, region: str) -> dict:
        """Fetch TFT summoner profile by PUUID."""
        url = f"https://{region}.api.riotgames.com/tft/summoner/v1/summoners/by-puuid/{puuid}"
        return self.get(url)

    def get_ranked_stats(self, puuid: str, region: str) -> list[dict]:
        """Fetch TFT ranked entries for a player by PUUID."""
        url = f"https://{region}.api.riotgames.com/tft/league/v1/entries/by-puuid/{puuid}"
        return self.get(url)

    def get_match_ids(self, puuid: str, region: str, count: int = 20) -> list[str]:
        """Return a list of recent TFT match IDs."""
        routing = REGIONAL_ROUTES.get(region, "americas")
        url = f"https://{routing}.api.riotgames.com/tft/match/v1/matches/by-puuid/{puuid}/ids"
        return self.get(url, params={"count": count})

    def get_match(self, match_id: str, region: str) -> dict:
        """Fetch full TFT match data."""
        routing = REGIONAL_ROUTES.get(region, "americas")
        url = f"https://{routing}.api.riotgames.com/tft/match/v1/matches/{match_id}"
        return self.get(url)
