import hashlib
import secrets
import sqlite3

from backend.config import DB_PATH


class _ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def _conn(db_path: str = DB_PATH):
    connection = sqlite3.connect(db_path, timeout=5, factory=_ClosingConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA busy_timeout=5000")
    return connection


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def init_db(db_path: str = DB_PATH) -> None:
    with _conn(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_hash TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                identity_kind TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_auth_sessions_identity "
            "ON auth_sessions(identity_kind, username)"
        )
        conn.execute("DELETE FROM auth_sessions WHERE datetime(expires_at) <= datetime('now')")


def create(username: str, identity_kind: str, remember_me: bool = False, db_path: str = DB_PATH) -> str:
    init_db(db_path)
    token = secrets.token_urlsafe(32)
    lifetime = "+30 days" if remember_me else "+12 hours"
    with _conn(db_path) as conn:
        conn.execute(
            """
            INSERT INTO auth_sessions (token_hash, username, identity_kind, expires_at)
            VALUES (?, ?, ?, datetime('now', ?))
            """,
            (_token_hash(token), username, identity_kind, lifetime),
        )
    return token


def get_username(token: str, identity_kind: str, db_path: str = DB_PATH) -> str | None:
    if not token:
        return None
    init_db(db_path)
    with _conn(db_path) as conn:
        row = conn.execute(
            """
            SELECT username
            FROM auth_sessions
            WHERE token_hash=? AND identity_kind=?
              AND datetime(expires_at) > datetime('now')
            """,
            (_token_hash(token), identity_kind),
        ).fetchone()
    return row["username"] if row else None


def delete(token: str, identity_kind: str | None = None, db_path: str = DB_PATH) -> None:
    if not token:
        return
    init_db(db_path)
    with _conn(db_path) as conn:
        if identity_kind:
            conn.execute(
                "DELETE FROM auth_sessions WHERE token_hash=? AND identity_kind=?",
                (_token_hash(token), identity_kind),
            )
        else:
            conn.execute("DELETE FROM auth_sessions WHERE token_hash=?", (_token_hash(token),))


def delete_by_identity(username: str, identity_kind: str, db_path: str = DB_PATH) -> None:
    init_db(db_path)
    with _conn(db_path) as conn:
        conn.execute(
            "DELETE FROM auth_sessions WHERE username=? AND identity_kind=?",
            (username, identity_kind),
        )
