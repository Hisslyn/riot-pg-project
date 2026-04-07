"""
League of Legends API endpoints.
Docs: https://developer.riotgames.com/apis
"""

from config import REGIONAL_ROUTES
from api.base_client import RiotClient


class LoLAPI(RiotClient):

    def get_summoner_by_puuid(self, puuid: str, region: str) -> dict:
        """Fetch LoL summoner profile by PUUID."""
        url = f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
        return self.get(url)

    def get_ranked_stats(self, puuid: str, region: str) -> list[dict]:
        """Fetch ranked queue standings for a player by PUUID."""
        url = f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
        return self.get(url)

    def get_match_ids(
        self,
        puuid: str,
        region: str,
        count: int = 20,
        queue: int | None = None,
    ) -> list[str]:
        """Return a list of recent match IDs for a player."""
        routing = REGIONAL_ROUTES.get(region, "americas")
        url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
        params = {"count": count}
        if queue:
            params["queue"] = queue
        return self.get(url, params=params)

    def get_match(self, match_id: str, region: str) -> dict:
        """Fetch full match data by match ID."""
        routing = REGIONAL_ROUTES.get(region, "americas")
        url = f"https://{routing}.api.riotgames.com/lol/match/v5/matches/{match_id}"
        return self.get(url)
