from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any


def save_preferences(path: str | Path, preferences: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("wb") as f:
        pickle.dump(preferences, f, protocol=pickle.HIGHEST_PROTOCOL)


def load_preferences(path: str | Path) -> Any:
    with Path(path).open("rb") as f:
        return pickle.load(f)