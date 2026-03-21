import os
import pickle
import tempfile
from typing import Any


def save_preferences(path: str, prefs: Any) -> None:
    path = os.path.abspath(path)
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=directory or None, prefix=".prefs_", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as f:
            pickle.dump(prefs, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_preferences(path: str) -> Any:
    path = os.path.abspath(path)
    with open(path, "rb") as f:
        return pickle.load(f)