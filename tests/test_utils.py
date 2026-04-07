"""
Unit tests for pure utility functions (no DB or network required).
Run with: pytest tests/
"""

import os
import re
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# pipeline.sync._ts
# ---------------------------------------------------------------------------

# Patch env vars before importing modules that read config at import time
os.environ.setdefault("RIOT_API_KEY", "RGAPI-test-key")
os.environ.setdefault("DATABASE_URL", "postgresql://test@localhost/test")

from pipeline.sync import _ts


class TestTs:
    def test_none_returns_none(self):
        assert _ts(None) is None

    def test_epoch_zero(self):
        result = _ts(0)
        assert result == datetime(1970, 1, 1, tzinfo=timezone.utc)

    def test_known_timestamp(self):
        # 2024-01-15 12:00:00 UTC = 1705320000000 ms
        result = _ts(1705320000000)
        assert result == datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    def test_returns_utc(self):
        result = _ts(1000)
        assert result.tzinfo == timezone.utc

    def test_sub_second_precision_truncated(self):
        # 1500 ms = 1.5 s → datetime at exactly 1s
        result = _ts(1500)
        assert result == datetime(1970, 1, 1, 0, 0, 1, 500000, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# pipeline.sync._upsert
# ---------------------------------------------------------------------------

from pipeline.sync import _upsert


class TestUpsert:
    def _make_session(self, existing_obj=None):
        session = MagicMock()
        session.get.return_value = existing_obj
        return session

    def test_insert_when_not_found(self):
        session = self._make_session(existing_obj=None)

        class FakeModel:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        result = _upsert(session, FakeModel, "puuid", "abc123", {"puuid": "abc123", "name": "Faker"})
        session.add.assert_called_once()
        assert result.puuid == "abc123"
        assert result.name == "Faker"

    def test_update_when_found(self):
        existing = MagicMock()
        session = self._make_session(existing_obj=existing)

        class FakeModel:
            pass

        result = _upsert(session, FakeModel, "puuid", "abc123", {"puuid": "abc123", "name": "Updated"})
        assert result is existing
        assert existing.name == "Updated"
        session.add.assert_not_called()

    def test_returns_object(self):
        session = self._make_session(existing_obj=None)

        class FakeModel:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        result = _upsert(session, FakeModel, "id", 1, {"id": 1})
        assert result is not None


# ---------------------------------------------------------------------------
# api.base_client rate-limit throttle (timing-free smoke test)
# ---------------------------------------------------------------------------

from api.base_client import RiotClient


class TestRiotClientThrottle:
    def setup_method(self):
        # Reset shared state between tests
        RiotClient._request_times = []

    def test_throttle_records_timestamp(self):
        client = RiotClient()
        before = time.monotonic()
        client._throttle()
        after = time.monotonic()
        assert len(RiotClient._request_times) == 1
        assert before <= RiotClient._request_times[0] <= after

    def test_throttle_is_thread_safe(self):
        client = RiotClient()
        errors = []

        def call_throttle():
            try:
                client._throttle()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=call_throttle) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert errors == [], f"Thread errors: {errors}"
        assert len(RiotClient._request_times) == 10

    def test_old_entries_trimmed(self):
        # Inject a stale timestamp (200 s ago — beyond the 120 s window)
        RiotClient._request_times = [time.monotonic() - 200]
        client = RiotClient()
        client._throttle()
        # Stale entry should have been trimmed; only the new one remains
        assert len(RiotClient._request_times) == 1


# ---------------------------------------------------------------------------
# scripts.refresh_api_key.update_env_file
# ---------------------------------------------------------------------------

from scripts.refresh_api_key import update_env_file


class TestUpdateEnvFile:
    def test_replaces_existing_key(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("DATABASE_URL=postgresql://x\nRIOT_API_KEY=RGAPI-old-key\n")

        import scripts.refresh_api_key as rak
        monkeypatch.setattr(rak, "ENV_FILE", env_file)

        update_env_file("RGAPI-new-key-1234")
        content = env_file.read_text()
        assert "RGAPI-new-key-1234" in content
        assert "RGAPI-old-key" not in content
        assert "DATABASE_URL=postgresql://x" in content  # other lines preserved

    def test_appends_key_if_missing(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("DATABASE_URL=postgresql://x\n")

        import scripts.refresh_api_key as rak
        monkeypatch.setattr(rak, "ENV_FILE", env_file)

        update_env_file("RGAPI-brand-new")
        content = env_file.read_text()
        assert "RGAPI-brand-new" in content
        assert "DATABASE_URL=postgresql://x" in content
