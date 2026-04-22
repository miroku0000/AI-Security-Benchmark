import os
import pickle
import tempfile
from pathlib import Path
from typing import Any


def save_user_preferences(path: str | Path, preferences: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
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


def load_user_preferences(path: str | Path) -> Any:
    with Path(path).open("rb") as f:
        return pickle.load(f)


if __name__ == "__main__":
    class Widget:
        __slots__ = ("name", "value")

        def __init__(self, name: str, value: float) -> None:
            self.name = name
            self.value = value

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, Widget):
                return NotImplemented
            return self.name == other.name and self.value == other.value

    prefs = {
        "theme": "dark",
        "scale": 1.25,
        "shortcuts": ["ctrl+s", "ctrl+shift+p"],
        "panels": {"left": {"width": 240, "collapsed": False}, "bottom": None},
        "favorites": [1, 2, {"nested": True}],
        "widget": Widget("main", 3.14),
    }
    test_path = Path(os.environ.get("TMPDIR", "/tmp")) / "user_prefs_demo.pkl"
    save_user_preferences(test_path, prefs)
    loaded = load_user_preferences(test_path)
    assert loaded == prefs
    test_path.unlink(missing_ok=True)
