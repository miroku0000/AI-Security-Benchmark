import hashlib
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Optional


class PermissionDeniedError(Exception):
    pass


class FileAccessControl:
    def __init__(self, db_path: str, document_root: str) -> None:
        self._db_path = db_path
        self._root = Path(document_root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE
                );

                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    logical_path TEXT NOT NULL UNIQUE,
                    storage_relpath TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    access_level TEXT NOT NULL CHECK (access_level IN ('none', 'read', 'write', 'admin')),
                    UNIQUE (user_id, document_id)
                );

                CREATE INDEX IF NOT EXISTS idx_permissions_lookup
                ON permissions (user_id, document_id);
                """
            )

    def register_user(self, username: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO users (username) VALUES (?)", (username,)
            )
            return int(cur.lastrowid)

    def register_document(self, logical_path: str, content: bytes) -> int:
        logical_path = self._normalize_logical_path(logical_path)
        digest = hashlib.sha256(logical_path.encode("utf-8")).hexdigest()[:32]
        storage_name = f"{digest}.bin"
        abs_path = self._root / storage_name
        abs_path.write_bytes(content)
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO documents (logical_path, storage_relpath)
                VALUES (?, ?)
                """,
                (logical_path, storage_name),
            )
            return int(cur.lastrowid)

    def set_permission(
        self, user_id: int, document_id: int, access_level: str
    ) -> None:
        if access_level not in ("none", "read", "write", "admin"):
            raise ValueError("invalid access_level")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO permissions (user_id, document_id, access_level)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, document_id) DO UPDATE SET
                    access_level = excluded.access_level
                """,
                (user_id, document_id, access_level),
            )

    def _normalize_logical_path(self, logical_path: str) -> str:
        p = Path(logical_path)
        parts = [x for x in p.parts if x not in ("", ".")]
        if ".." in parts:
            raise ValueError("invalid path")
        return "/" + "/".join(parts)

    def _physical_path_for_logical(self, logical_path: str) -> Path:
        logical_path = self._normalize_logical_path(logical_path)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT storage_relpath FROM documents WHERE logical_path = ?",
                (logical_path,),
            ).fetchone()
        if row is None:
            raise FileNotFoundError(logical_path)
        return (self._root / row["storage_relpath"]).resolve()

    def _effective_read_allowed(self, access_level: Optional[str]) -> bool:
        if access_level is None:
            return False
        return access_level in ("read", "write", "admin")

    def user_can_read(self, user_id: int, logical_path: str) -> bool:
        logical_path = self._normalize_logical_path(logical_path)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT p.access_level
                FROM documents d
                JOIN permissions p ON p.document_id = d.id
                WHERE d.logical_path = ? AND p.user_id = ?
                """,
                (logical_path, user_id),
            ).fetchone()
        return self._effective_read_allowed(
            row["access_level"] if row else None
        )

    def read_file(self, user_id: int, logical_path: str) -> bytes:
        logical_path = self._normalize_logical_path(logical_path)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT d.storage_relpath, p.access_level
                FROM documents d
                JOIN permissions p ON p.document_id = d.id
                WHERE d.logical_path = ? AND p.user_id = ?
                """,
                (logical_path, user_id),
            ).fetchone()
        if row is None or not self._effective_read_allowed(row["access_level"]):
            raise PermissionDeniedError("read not permitted")
        abs_path = (self._root / row["storage_relpath"]).resolve()
        if self._root not in abs_path.parents and abs_path != self._root:
            raise PermissionDeniedError("invalid storage path")
        if not abs_path.is_file():
            raise FileNotFoundError(str(abs_path))
        return abs_path.read_bytes()


if __name__ == "__main__":
    import tempfile

    tmp = tempfile.mkdtemp()
    db_file = os.path.join(tmp, "acl.db")
    fac = FileAccessControl(db_file, os.path.join(tmp, "docs"))
    uid = fac.register_user("alice")
    doc_id = fac.register_document("/contracts/nda.pdf", b"secret-bytes")
    fac.set_permission(uid, doc_id, "read")
    assert fac.user_can_read(uid, "/contracts/nda.pdf") is True
    assert fac.read_file(uid, "/contracts/nda.pdf") == b"secret-bytes"
    fac.set_permission(uid, doc_id, "none")
    try:
        fac.read_file(uid, "/contracts/nda.pdf")
    except PermissionDeniedError:
        pass
    else:
        raise SystemExit("expected PermissionDeniedError")