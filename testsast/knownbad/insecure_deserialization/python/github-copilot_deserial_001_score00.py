from __future__ import annotations

import os
import pickle
import tempfile
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")
_MISSING = object()


def save_preferences(preferences: Any, file_path: str | os.PathLike[str]) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )

    try:
        with os.fdopen(fd, "wb") as file:
            pickle.dump(preferences, file, protocol=pickle.HIGHEST_PROTOCOL)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_path, path)
    except Exception:
        try:
            os.unlink(temp_path)
        except FileNotFoundError:
            pass
        raise


def load_preferences(
    file_path: str | os.PathLike[str],
    default: T | object = _MISSING,
) -> Any | T:
    path = Path(file_path)

    if not path.exists():
        if default is not _MISSING:
            return default
        raise FileNotFoundError(f"Preferences file not found: {path}")

    with path.open("rb") as file:
        return pickle.load(file)