import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from app.config import get_settings


@dataclass(frozen=True)
class UserRecord:
    id: int
    username: str
    password_hash: str
    created_at: str


def _db_path() -> Path:
    path = Path(get_settings().auth_database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_database() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def get_user_by_username(username: str) -> UserRecord | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, username, password_hash, created_at FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    if row is None:
        return None
    return UserRecord(
        id=row["id"],
        username=row["username"],
        password_hash=row["password_hash"],
        created_at=row["created_at"],
    )


def create_user(username: str, password_hash: str) -> UserRecord:
    created_at = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
            (username.strip(), password_hash, created_at),
        )
        conn.commit()
        user_id = cursor.lastrowid
    if user_id is None:
        raise RuntimeError("Failed to create user")
    return UserRecord(
        id=user_id,
        username=username.strip(),
        password_hash=password_hash,
        created_at=created_at,
    )
