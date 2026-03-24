"""Tests for disk-backed API response cache with TTL expiration."""

from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

# Add parent directory to path for utils import
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.api_response_cache import APIResponseCache


def test_cache_round_trip_with_nested_response():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = APIResponseCache(cache_dir=Path(tmpdir), default_ttl_seconds=60)
        key = "GET:/v1/users?page=1"
        payload = {
            "items": [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Grace"}],
            "meta": {"page": 1, "total": 2},
        }

        cache.set(key=key, response=payload, metadata={"source": "unit-test"})
        loaded = cache.get(key)
        loaded_with_meta = cache.get(key, include_metadata=True)

        assert loaded == payload
        assert loaded_with_meta is not None
        assert loaded_with_meta["response"] == payload
        assert loaded_with_meta["metadata"]["source"] == "unit-test"


def test_cache_expiration_removes_entry():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = APIResponseCache(cache_dir=Path(tmpdir), default_ttl_seconds=1)
        key = "GET:/v1/expiring"
        payload = {"ok": True}

        cache.set(key=key, response=payload, ttl_seconds=0)
        loaded = cache.get(key)

        assert loaded is None


def test_cache_reload_across_instances():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir)
        key = "GET:/v1/reload"
        payload = {"numbers": [1, 2, 3], "nested": {"a": "b"}}

        writer = APIResponseCache(cache_dir=cache_dir, default_ttl_seconds=60)
        writer.set(key=key, response=payload)

        reader = APIResponseCache(cache_dir=cache_dir, default_ttl_seconds=60)
        loaded = reader.get(key)
        assert loaded == payload


def test_get_or_set_uses_cache_until_expiry():
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = APIResponseCache(cache_dir=Path(tmpdir), default_ttl_seconds=1)
        key = "GET:/v1/expensive"
        calls = {"count": 0}

        def fetch():
            calls["count"] += 1
            return {"value": calls["count"]}

        first = cache.get_or_set(key, fetch_fn=fetch, ttl_seconds=1)
        second = cache.get_or_set(key, fetch_fn=fetch, ttl_seconds=1)
        time.sleep(1.05)
        third = cache.get_or_set(key, fetch_fn=fetch, ttl_seconds=1)

        assert first == {"value": 1}
        assert second == {"value": 1}
        assert third == {"value": 2}
        assert calls["count"] == 2
