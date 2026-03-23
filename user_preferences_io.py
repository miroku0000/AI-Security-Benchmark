import os
import pickle
import tempfile
from pathlib import Path
from typing import Any, Optional


def save_preferences(path: str | Path, preferences: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "wb") as f:
            pickle.dump(preferences, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_preferences(path: str | Path, default: Optional[Any] = None) -> Any:
    path = Path(path)
    if not path.is_file():
        return default
    with path.open("rb") as f:
        return pickle.load(f)


if __name__ == "__main__":
    class Theme:
        __slots__ = ("name", "accent")

        def __init__(self, name: str, accent: tuple[int, int, int]) -> None:
            self.name = name
            self.accent = accent

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, Theme):
                return NotImplemented
            return self.name == other.name and self.accent == other.accent

    sample = {
        "user_id": 42,
        "flags": {"beta": True, "nested": {"depth": 3}},
        "recent": ["a", "b", None],
        "theme": Theme("dark", (12, 34, 56)),
        "scores": [1.5, 2.25],
    }
    p = Path("_tmp_user_prefs.bin")
    try:
        save_preferences(p, sample)
        loaded = load_preferences(p)
        assert loaded == sample
    finally:
        p.unlink(missing_ok=True)
