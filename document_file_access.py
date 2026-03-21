#!/usr/bin/env python3
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional


@dataclass
class AccessResult:
    ok: bool
    content: Optional[bytes] = None
    error: Optional[str] = None


class DocumentFileAccessControl:
    def __init__(self, db_path: str, storage_root: str) -> None:
        self._db_path = db_path
        self._storage_root = Path(storage_root).resolve()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    logical_name TEXT NOT NULL,
                    storage_relpath TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS document_permissions (
                    user_id INTEGER NOT NULL,
                    document_id INTEGER NOT NULL,
                    access_level TEXT NOT NULL CHECK (access_level IN ('none', 'read', 'write', 'admin')),
                    PRIMARY KEY (user_id, document_id),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_perm_user_doc ON document_permissions(user_id, document_id);
                """
            )

    def _resolved_path(self, storage_relpath: str) -> Path:
        base = self._storage_root
        candidate = (base / storage_relpath).resolve()
        try:
            candidate.relative_to(base)
        except ValueError as exc:
            raise PermissionError("path escapes storage root") from exc
        return candidate

    def user_can_read(self, user_id: int, document_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT access_level FROM document_permissions
                WHERE user_id = ? AND document_id = ?
                """,
                (user_id, document_id),
            ).fetchone()
            if row is None:
                return False
            level = row["access_level"]
            return level in ("read", "write", "admin")

    def read_file(self, user_id: int, document_id: int) -> AccessResult:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT d.storage_relpath, p.access_level
                FROM documents d
                LEFT JOIN document_permissions p
                  ON p.document_id = d.id AND p.user_id = ?
                WHERE d.id = ?
                """,
                (user_id, document_id),
            ).fetchone()
            if row is None:
                return AccessResult(ok=False, error="document_not_found")
            level = row["access_level"]
            if level is None or level == "none":
                return AccessResult(ok=False, error="forbidden")
            if level not in ("read", "write", "admin"):
                return AccessResult(ok=False, error="forbidden")
            relpath = row["storage_relpath"]
        try:
            full = self._resolved_path(relpath)
        except PermissionError:
            return AccessResult(ok=False, error="invalid_path")
        if not full.is_file():
            return AccessResult(ok=False, error="file_missing")
        try:
            data = full.read_bytes()
        except OSError as e:
            return AccessResult(ok=False, error=f"read_error:{e}")
        return AccessResult(ok=True, content=data)


def _demo() -> None:
    import tempfile

    tmp = tempfile.mkdtemp()
    db = os.path.join(tmp, "acl.db")
    root = os.path.join(tmp, "store")
    os.makedirs(root, exist_ok=True)
    ctl = DocumentFileAccessControl(db, root)
    ctl.init_schema()
    with ctl._connect() as c:
        c.execute("INSERT INTO users (username) VALUES (?)", ("alice",))
        c.execute("INSERT INTO documents (logical_name, storage_relpath) VALUES (?, ?)", ("notes", "a/notes.txt"))
        doc_id = c.execute("SELECT last_insert_rowid()").fetchone()[0]
        uid = c.execute("SELECT id FROM users WHERE username = ?", ("alice",)).fetchone()[0]
        c.execute(
            "INSERT INTO document_permissions (user_id, document_id, access_level) VALUES (?, ?, ?)",
            (uid, doc_id, "read"),
        )
    path = Path(root) / "a" / "notes.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"hello")
    r = ctl.read_file(uid, doc_id)
    assert r.ok and r.content == b"hello"
    r2 = ctl.read_file(uid + 999, doc_id)
    assert not r2.ok and r2.error == "forbidden"
    print("ok", r.content)


if __name__ == "__main__":
    _demo()
