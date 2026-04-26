import argparse
import sqlite3
from pathlib import Path
from typing import Optional

READ_ACCESS_LEVELS = {"reader", "editor", "owner"}


class AccessControlError(Exception):
    pass


class UserNotFoundError(AccessControlError):
    pass


class DocumentNotFoundError(AccessControlError):
    pass


class PermissionDeniedError(AccessControlError):
    pass


def connect_db(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def initialize_database(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY
        );

        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            relative_path TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS document_permissions (
            user_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            access_level TEXT NOT NULL CHECK (access_level IN ('none', 'reader', 'editor', 'owner')),
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, document_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
        );
        """
    )
    conn.commit()


def seed_demo_data(conn: sqlite3.Connection, storage_dir: Path) -> None:
    storage_dir.mkdir(parents=True, exist_ok=True)

    demo_files = {
        "employee-handbook.txt": "Welcome to the document management system.\nThis is the employee handbook.\n",
        "finance-report.txt": "Q1 Finance Report\nRevenue: 125000\nExpenses: 83000\n",
    }

    for filename, content in demo_files.items():
        file_path = storage_dir / filename
        if not file_path.exists():
            file_path.write_text(content, encoding="utf-8")

    conn.executemany(
        "INSERT OR IGNORE INTO users (id) VALUES (?)",
        [("alice",), ("bob",), ("charlie",)],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO documents (id, relative_path) VALUES (?, ?)",
        [
            ("employee-handbook", "employee-handbook.txt"),
            ("finance-report", "finance-report.txt"),
        ],
    )
    conn.executemany(
        """
        INSERT INTO document_permissions (user_id, document_id, access_level)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, document_id) DO UPDATE SET
            access_level = excluded.access_level,
            updated_at = CURRENT_TIMESTAMP
        """,
        [
            ("alice", "employee-handbook", "owner"),
            ("alice", "finance-report", "editor"),
            ("bob", "employee-handbook", "reader"),
            ("charlie", "finance-report", "none"),
        ],
    )
    conn.commit()


def user_exists(conn: sqlite3.Connection, user_id: str) -> bool:
    row = conn.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone()
    return row is not None


def get_document_record(conn: sqlite3.Connection, document_id: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT id, relative_path FROM documents WHERE id = ?",
        (document_id,),
    ).fetchone()


def get_user_access_level(conn: sqlite3.Connection, user_id: str, document_id: str) -> Optional[str]:
    row = conn.execute(
        """
        SELECT access_level
        FROM document_permissions
        WHERE user_id = ? AND document_id = ?
        """,
        (user_id, document_id),
    ).fetchone()
    return None if row is None else row["access_level"]


def resolve_safe_path(storage_dir: Path, relative_path: str) -> Path:
    base = storage_dir.resolve()
    target = (base / relative_path).resolve()
    if base != target and base not in target.parents:
        raise AccessControlError("Resolved document path escapes the storage directory.")
    return target


def open_document_for_user(
    conn: sqlite3.Connection,
    storage_dir: Path,
    user_id: str,
    document_id: str,
) -> str:
    if not user_exists(conn, user_id):
        raise UserNotFoundError(f"Unknown user: {user_id}")

    document = get_document_record(conn, document_id)
    if document is None:
        raise DocumentNotFoundError(f"Unknown document: {document_id}")

    access_level = get_user_access_level(conn, user_id, document_id)
    if access_level not in READ_ACCESS_LEVELS:
        raise PermissionDeniedError(
            f"User '{user_id}' does not have permission to read document '{document_id}'."
        )

    file_path = resolve_safe_path(storage_dir, document["relative_path"])
    if not file_path.is_file():
        raise FileNotFoundError(f"Document file not found: {file_path}")

    return file_path.read_text(encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Document access control system.")
    parser.add_argument("--db", default="access_control.db", help="SQLite database path.")
    parser.add_argument(
        "--storage-dir",
        default="documents",
        help="Directory where document files are stored.",
    )
    parser.add_argument("--user", default="alice", help="User ID requesting access.")
    parser.add_argument(
        "--document",
        default="employee-handbook",
        help="Document ID to read.",
    )
    parser.add_argument(
        "--init-demo",
        action="store_true",
        help="Initialize the database and seed demo data.",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    storage_dir = Path(args.storage_dir)

    with connect_db(db_path) as conn:
        initialize_database(conn)
        if args.init_demo or not db_path.exists() or not any(storage_dir.glob("*")):
            seed_demo_data(conn, storage_dir)

        try:
            contents = open_document_for_user(conn, storage_dir, args.user, args.document)
        except AccessControlError as exc:
            print(f"ACCESS ERROR: {exc}")
            return 1
        except FileNotFoundError as exc:
            print(f"FILE ERROR: {exc}")
            return 1

    print(contents, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())