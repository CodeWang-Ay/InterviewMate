import hashlib
import sqlite3
import uuid

from backend.config import DB_PATH


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


tokens: dict[str, str] = {}


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                candidate_name TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        cols = [c[1] for c in conn.execute("PRAGMA table_info(candidates)").fetchall()]
        if "candidate_name" not in cols:
            conn.execute("ALTER TABLE candidates ADD COLUMN candidate_name TEXT DEFAULT ''")

        _migrate_legacy_candidates(conn)


def _migrate_legacy_candidates(conn) -> None:
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "users" not in tables:
        return

    user_cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    has_role = "role" in user_cols
    select_cols = ["username", "password_hash", "nickname"]
    if has_role:
        select_cols.append("role")
    sql = f"SELECT {', '.join(select_cols)} FROM users"
    for row in conn.execute(sql).fetchall():
        data = dict(row)
        role = data.get("role", "user") if has_role else ("admin" if data.get("username") == "admin" else "user")
        if role == "admin":
            continue
        conn.execute(
            "INSERT OR IGNORE INTO candidates (username, password_hash, candidate_name) VALUES (?,?,?)",
            (
                data.get("username", ""),
                data.get("password_hash", ""),
                data.get("nickname", "") or data.get("username", ""),
            ),
        )


def register(username: str, password: str, candidate_name: str = "") -> dict | None:
    if len(password) < 6:
        return None
    try:
        with _conn() as conn:
            cur = conn.execute(
                "INSERT INTO candidates (username, password_hash, candidate_name) VALUES (?,?,?)",
                (username, _hash(password), candidate_name or username),
            )
            return {"id": cur.lastrowid, "username": username, "candidate_name": candidate_name or username}
    except sqlite3.IntegrityError:
        return None


def login(username: str, password: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM candidates WHERE username=? AND password_hash=?",
            (username, _hash(password)),
        ).fetchone()
    if not row:
        return None
    token = uuid.uuid4().hex
    tokens[token] = username
    return {
        "token": token,
        "username": username,
        "nickname": row["candidate_name"] or username,
        "role": "candidate",
    }


def get_candidate_by_token(token: str) -> str | None:
    return tokens.get(token)


def get_candidate_info(username: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM candidates WHERE username=?", (username,)).fetchone()
    return dict(row) if row else None


def logout(token: str):
    tokens.pop(token, None)
