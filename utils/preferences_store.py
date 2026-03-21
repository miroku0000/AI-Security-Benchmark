"""Utilities for persisting complex user preference objects."""

from __future__ import annotations

import os
import pickle
import tempfile
from pathlib import Path
from typing import Any, Dict, Tuple


_PREF_CACHE: Dict[Path, Tuple[int, int, Any]] = {}


def save_preferences(preferences: Any, file_path: str | Path) -> None:
    """Serialize preferences to disk using Python's fastest binary protocol.

    Notes:
    - This uses pickle, which supports nested dict/list/primitive structures
      and most custom Python objects.
    - Only load files you trust. Unpickling untrusted data is unsafe.
    """
    target = Path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(prefix=f"{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as tmp_file:
            pickle.dump(preferences, tmp_file, protocol=pickle.HIGHEST_PROTOCOL)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())

        os.replace(tmp_path, target)
        _PREF_CACHE.pop(target, None)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def load_preferences(file_path: str | Path, use_cache: bool = True) -> Any:
    """Load serialized preferences from disk.

    If use_cache is True, this function returns a cached object when file size
    and mtime are unchanged, avoiding repeated disk reads in long-lived
    processes.
    """
    target = Path(file_path)

    if not target.exists():
        raise FileNotFoundError(f"Preferences file not found: {target}")

    stat = target.stat()
    cache_key = target
    signature = (stat.st_mtime_ns, stat.st_size)

    if use_cache:
        cached = _PREF_CACHE.get(cache_key)
        if cached and cached[0] == signature[0] and cached[1] == signature[1]:
            return cached[2]

    with target.open("rb") as pref_file:
        preferences = pickle.load(pref_file)

    if use_cache:
        _PREF_CACHE[cache_key] = (signature[0], signature[1], preferences)

    return preferences
