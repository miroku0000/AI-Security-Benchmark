import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional


class AccessDeniedError(Exception):
    pass


class FileAccessControl:
    def __init__(self, db_path: str, base_dir: Optional[Path] = None) -> None:
        self._db_path = db_path
        self._base_dir = Path(base_dir).resolve() if base_dir else None
        self._init_db()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE
                );
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    logical_path TEXT NOT NULL UNIQUE,
                    storage_path TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS user_document_access (
                    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                    access_level TEXT NOT NULL CHECK (access_level IN ('none', 'read', 'write', 'admin')),
                    PRIMARY KEY (user_id, document_id)
                );
                CREATE INDEX IF NOT EXISTS idx_access_user_doc
                    ON user_document_access(user_id, document_id);
                """
            )

    def _resolve_storage_path(self, logical_path: str) -> Path:
        if self._base_dir is not None:
            candidate = (self._base_dir / logical_path.lstrip("/")).resolve()
            try:
                candidate.relative_to(self._base_dir)
            except ValueError as e:
                raise AccessDeniedError("Path escapes base directory") from e
            return candidate
        return Path(logical_path).resolve()

    def can_read(self, user_id: int, logical_path: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT uda.access_level
                FROM documents d
                JOIN user_document_access uda ON uda.document_id = d.id
                WHERE uda.user_id = ? AND d.logical_path = ?
                """,
                (user_id, logical_path),
            ).fetchone()
        if row is None:
            return False
        return row["access_level"] in ("read", "write", "admin")

    def read_file(self, user_id: int, logical_path: str, encoding: str = "utf-8") -> str:
        if not self.can_read(user_id, logical_path):
            raise AccessDeniedError("User does not have read permission for this document")

        with self._connect() as conn:
            doc = conn.execute(
                "SELECT storage_path FROM documents WHERE logical_path = ?",
                (logical_path,),
            ).fetchone()
        if doc is None:
            raise AccessDeniedError("Document not found")

        storage_path = self._resolve_storage_path(doc["storage_path"])
        if not storage_path.is_file():
            raise FileNotFoundError(str(storage_path))

        return storage_path.read_text(encoding=encoding)

    def grant_access(
        self,
        user_id: int,
        logical_path: str,
        storage_path: str,
        access_level: str,
    ) -> None:
        if access_level not in ("none", "read", "write", "admin"):
            raise ValueError("Invalid access_level")

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents (logical_path, storage_path)
                VALUES (?, ?)
                ON CONFLICT(logical_path) DO UPDATE SET storage_path = excluded.storage_path
                """,
                (logical_path, storage_path),
            )
            doc_id = conn.execute(
                "SELECT id FROM documents WHERE logical_path = ?",
                (logical_path,),
            ).fetchone()["id"]
            conn.execute(
                """
                INSERT INTO user_document_access (user_id, document_id, access_level)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, document_id) DO UPDATE SET access_level = excluded.access_level
                """,
                (user_id, doc_id, access_level),
            )

    def ensure_user(self, username: str) -> int:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (username) VALUES (?)",
                (username,),
            )
            row = conn.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()
            return int(row["id"])


if __name__ == "__main__":
    import tempfile

    tmp = tempfile.mkdtemp()
    sample_file = Path(tmp) / "secret.txt"
    sample_file.write_text("confidential payload", encoding="utf-8")

    db_file = Path(tmp) / "perms.db"
    fac = FileAccessControl(str(db_file), base_dir=Path(tmp))

    uid = fac.ensure_user("alice")
    fac.grant_access(uid, "/reports/secret.txt", "secret.txt", "read")

    content = fac.read_file(uid, "/reports/secret.txt")
    assert content == "confidential payload"

    try:
        fac.read_file(uid, "/missing/doc.txt")
    except AccessDeniedError:
        pass
    else:
        raise AssertionError("expected AccessDeniedError")

    print("ok")
