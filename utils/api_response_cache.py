"""Disk-backed cache for expensive API responses with TTL expiration."""

from __future__ import annotations

import hashlib
import os
import pickle
import struct
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

try:
    import orjson

    def _serialize_record(record: Dict[str, Any]) -> bytes:
        return orjson.dumps(record)

    def _deserialize_record(data: bytes) -> Dict[str, Any]:
        return orjson.loads(data)

except ImportError:
    import json

    def _serialize_record(record: Dict[str, Any]) -> bytes:
        return json.dumps(record, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def _deserialize_record(data: bytes) -> Dict[str, Any]:
        return json.loads(data.decode("utf-8"))

_MAGIC = b"ARC1"
_FILE_HEADER = struct.Struct("!4s d I")
# magic(4) + expires_at(8) + payload_len(4) = 16 bytes before payload


class APIResponseCache:
    """Persist API response payloads to disk and expire them by timestamp.

    Records include response data (nested dicts/lists), optional metadata, and
    created_at / expires_at timestamps. Serialization prefers orjson for speed;
    falls back to stdlib json, then pickle for non-JSON-serializable payloads.
    """

    def __init__(self, cache_dir: str | Path, default_ttl_seconds: int = 300) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.default_ttl_seconds = default_ttl_seconds
        self._lock = threading.RLock()

    def _key_to_path(self, key: str) -> Path:
        key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    @staticmethod
    def _encode_record(record: Dict[str, Any]) -> tuple[float, bytes]:
        expires_at = float(record["expires_at"])
        try:
            payload = _MAGIC + b"\x01" + _serialize_record(record)
        except (TypeError, ValueError):
            payload = _MAGIC + b"\x02" + pickle.dumps(record, protocol=pickle.HIGHEST_PROTOCOL)
        return expires_at, payload

    @staticmethod
    def _decode_payload(payload: bytes) -> Dict[str, Any]:
        if len(payload) < 6 or payload[:4] != _MAGIC:
            raise ValueError("invalid cache magic")
        kind = payload[4]
        body = payload[5:]
        if kind == 1:
            rec = _deserialize_record(body)
            if not isinstance(rec, dict):
                raise ValueError("invalid json record")
            return rec
        if kind == 2:
            rec = pickle.loads(body)
            if not isinstance(rec, dict):
                raise ValueError("invalid pickle record")
            return rec
        raise ValueError("unknown encoding kind")

    def set(
        self,
        key: str,
        response: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        ttl = self.default_ttl_seconds if ttl_seconds is None else ttl_seconds
        now = time.time()
        record = {
            "key": key,
            "response": response,
            "metadata": metadata or {},
            "created_at": now,
            "expires_at": now + ttl,
        }
        expires_at, payload = self._encode_record(record)
        header = _FILE_HEADER.pack(_MAGIC, expires_at, len(payload))
        blob = header + payload

        target = self._key_to_path(key)
        with self._lock:
            fd, tmp_path = tempfile.mkstemp(
                prefix=f"{target.name}.", suffix=".tmp", dir=self.cache_dir
            )
            try:
                with os.fdopen(fd, "wb") as tmp_file:
                    tmp_file.write(blob)
                    tmp_file.flush()
                    os.fsync(tmp_file.fileno())
                os.replace(tmp_path, target)
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

    def _read_expires_from_file(self, path: Path) -> Optional[float]:
        try:
            with path.open("rb") as f:
                head = f.read(_FILE_HEADER.size)
            if len(head) < _FILE_HEADER.size:
                return None
            magic, expires_at, _plen = _FILE_HEADER.unpack(head)
            if magic != _MAGIC:
                return None
            return float(expires_at)
        except Exception:
            return None

    def _read_expires_legacy(self, path: Path) -> Optional[float]:
        try:
            with path.open("rb") as f:
                raw = f.read()
            record = pickle.loads(raw)
            if not isinstance(record, dict):
                return None
            exp = record.get("expires_at")
            return float(exp) if isinstance(exp, (int, float)) else None
        except Exception:
            return None

    def get(self, key: str, include_metadata: bool = False) -> Optional[Dict[str, Any]]:
        target = self._key_to_path(key)
        with self._lock:
            exp = self._read_expires_from_file(target)
            if exp is None and target.exists():
                exp = self._read_expires_legacy(target)
            if exp is not None and exp <= time.time():
                target.unlink(missing_ok=True)
                return None
            record = self._load_record_from_path(target, delete_if_invalid=True)
            if record is None:
                return None
            if record["expires_at"] <= time.time():
                target.unlink(missing_ok=True)
                return None
            if include_metadata:
                return {
                    "response": record["response"],
                    "metadata": record["metadata"],
                    "created_at": record["created_at"],
                    "expires_at": record["expires_at"],
                }
            return record["response"]

    def get_or_set(
        self,
        key: str,
        fetch_fn: Callable[[], Dict[str, Any]],
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cached = self.get(key)
        if cached is not None:
            return cached
        response = fetch_fn()
        self.set(key=key, response=response, ttl_seconds=ttl_seconds, metadata=metadata)
        return response

    def delete(self, key: str) -> bool:
        target = self._key_to_path(key)
        with self._lock:
            if not target.exists():
                return False
            target.unlink()
            return True

    def clear_expired(self) -> int:
        now = time.time()
        removed = 0
        with self._lock:
            for file_path in self.cache_dir.glob("*.cache"):
                exp = self._read_expires_from_file(file_path)
                if exp is None:
                    exp = self._read_expires_legacy(file_path)
                if exp is not None:
                    if exp <= now:
                        file_path.unlink(missing_ok=True)
                        removed += 1
                    continue
                record = self._load_record_from_path(file_path, delete_if_invalid=True)
                if record is None:
                    continue
                if record["expires_at"] <= now:
                    file_path.unlink(missing_ok=True)
                    removed += 1
        return removed

    def _load_record_from_path(
        self, path: Path, delete_if_invalid: bool = False
    ) -> Optional[Dict[str, Any]]:
        if not path.exists():
            return None
        try:
            with path.open("rb") as f:
                raw = f.read()
            if len(raw) < _FILE_HEADER.size:
                raise ValueError("truncated header")
            magic, _expires_at, plen = _FILE_HEADER.unpack_from(raw, 0)
            if magic != _MAGIC:
                record = pickle.loads(raw)
                if not isinstance(record, dict):
                    raise ValueError("legacy record not a dict")
                required_keys = {"response", "metadata", "created_at", "expires_at"}
                if not required_keys.issubset(record.keys()):
                    raise ValueError("missing keys")
                return record
            if len(raw) < _FILE_HEADER.size + plen:
                raise ValueError("truncated payload")
            payload = raw[_FILE_HEADER.size : _FILE_HEADER.size + plen]
            record = self._decode_payload(payload)
            required_keys = {"response", "metadata", "created_at", "expires_at"}
            if not required_keys.issubset(record.keys()):
                raise ValueError("missing keys")
            return record
        except Exception:
            if delete_if_invalid:
                path.unlink(missing_ok=True)
            return None
