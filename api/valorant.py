"""
Valorant API endpoints.
Docs: https://developer.riotgames.com/apis#val-match-v1
"""

from api.base_client import RiotClient


class ValorantAPI(RiotClient):

    def get_match_ids_by_puuid(self, puuid: str, region: str) -> list[str]:
        """Return recent Valorant match IDs for a player."""
        url = f"https://{region}.api.riotgames.com/val/match/v1/matchlists/by-puuid/{puuid}"
        data = self.get(url)
        # Response: {"puuid": ..., "history": [{"matchId": ..., ...}]}
        return [entry["matchId"] for entry in data.get("history", [])]

    def get_match(self, match_id: str, region: str) -> dict:
        """Fetch full Valorant match data."""
        url = f"https://{region}.api.riotgames.com/val/match/v1/matches/{match_id}"
        return self.get(url)

    def get_recent_matches(self, queue: str, region: str) -> dict:
        """
        Fetch recent matches for a queue (e.g. 'competitive').
        Note: only available with a production API key.
        """
        url = f"https://{region}.api.riotgames.com/val/match/v1/recent-matches/by-queue/{queue}"
        return self.get(url)
