"""
Base HTTP client for the Riot Games API.
Handles authentication headers, rate limiting, and error handling.

Riot developer key limits:
  - 20 requests / 1 second
  - 100 requests / 2 minutes
"""

import threading
import time
import requests
import config


class RiotAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"[{status_code}] {message}")


class RiotClient:
    # Class-level (intentionally shared across all subclasses and instances)
    # so that LoLAPI, TFTAPI, and ValorantAPI all draw from the same rate-limit budget.
    _request_times: list[float] = []
    _rate_lock = threading.Lock()

    @property
    def _headers(self) -> dict:
        return {"X-Riot-Token": config.RIOT_API_KEY}

    def get_account_by_riot_id(self, game_name: str, tag_line: str, region: str) -> dict:
        """Fetch PUUID and account info by Riot ID. Shared endpoint across all games."""
        from config import REGIONAL_ROUTES
        routing = REGIONAL_ROUTES.get(region, "americas")
        url = f"https://{routing}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
        return self.get(url)

    def _throttle(self):
        """Block until it's safe to fire the next request."""
        while True:
            sleep_for = 0.0

            with self._rate_lock:
                now = time.monotonic()

                # Short window: 20 req / 1 s
                recent_1s = [t for t in self._request_times if now - t < 1.0]
                if len(recent_1s) >= 20:
                    sleep_for = max(sleep_for, 1.0 - (now - recent_1s[0]))

                # Long window: 100 req / 120 s
                recent_2m = [t for t in self._request_times if now - t < 120.0]
                if len(recent_2m) >= 100:
                    sleep_for = max(sleep_for, 120.0 - (now - recent_2m[0]))

                if sleep_for <= 0:
                    # Safe to proceed — record this request and return
                    self._request_times.append(time.monotonic())
                    cutoff = time.monotonic() - 120.0
                    self._request_times = [t for t in self._request_times if t > cutoff]
                    return

            # Sleep outside the lock so other threads can check freely
            time.sleep(sleep_for)

    def get(self, url: str, params: dict | None = None, _retries: int = 3) -> dict:
        """Make a rate-limited GET request and return parsed JSON."""
        for attempt in range(_retries):
            self._throttle()
            resp = requests.get(url, headers=self._headers, params=params, timeout=10)

            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                print(f"⚠️  Rate limited. Sleeping {retry_after}s... (attempt {attempt + 1}/{_retries})")
                time.sleep(retry_after)
                continue
            elif resp.status_code == 404:
                raise RiotAPIError(404, f"Not found: {url}")
            elif resp.status_code == 403:
                raise RiotAPIError(403, "Forbidden — check your API key.")
            else:
                raise RiotAPIError(resp.status_code, resp.text)

        raise RiotAPIError(429, f"Still rate limited after {_retries} retries: {url}")
