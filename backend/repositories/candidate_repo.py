import hashlib
import sqlite3
import uuid

import bcrypt

from backend.config import DB_PATH


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith("$2"):
        return bcrypt.checkpw(password.encode(), stored_hash.encode())
    old_hash = hashlib.sha256(password.encode()).hexdigest()
    return old_hash == stored_hash


def _needs_rehash(stored_hash: str) -> bool:
    return not stored_hash.startswith("$2")


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
                phone TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        cols = [c[1] for c in conn.execute("PRAGMA table_info(candidates)").fetchall()]
        if "candidate_name" not in cols:
            conn.execute("ALTER TABLE candidates ADD COLUMN candidate_name TEXT DEFAULT ''")
        if "phone" not in cols:
            conn.execute("ALTER TABLE candidates ADD COLUMN phone TEXT DEFAULT ''")
        if "email" not in cols:
            conn.execute("ALTER TABLE candidates ADD COLUMN email TEXT DEFAULT ''")

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


def register(username: str, password: str, candidate_name: str = "", phone: str = "") -> dict | None:
    if len(password) < 6:
        return None
    try:
        with _conn() as conn:
            cur = conn.execute(
                "INSERT INTO candidates (username, password_hash, candidate_name, phone) VALUES (?,?,?,?)",
                (username, _hash(password), candidate_name or username, phone),
            )
            return {"id": cur.lastrowid, "username": username, "candidate_name": candidate_name or username, "phone": phone}
    except sqlite3.IntegrityError:
        return None


def login(username: str, password: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM candidates WHERE username=?",
            (username,),
        ).fetchone()
    if not row:
        return None
    stored_hash = row["password_hash"]
    if not _verify_password(password, stored_hash):
        return None
    if _needs_rehash(stored_hash):
        conn.execute(
            "UPDATE candidates SET password_hash=? WHERE username=?",
            (_hash(password), username),
        )
    token = uuid.uuid4().hex
    tokens[token] = username
    return {
        "token": token,
        "username": username,
        "nickname": row["candidate_name"] or username,
        "phone": row["phone"] or "",
        "role": "candidate",
    }


def get_candidate_by_token(token: str) -> str | None:
    return tokens.get(token)


def get_candidate_info(username: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM candidates WHERE username=?", (username,)).fetchone()
    return dict(row) if row else None


def reset_password(username: str, new_password: str) -> bool:
    """重置候选人密码，用于管理员重新生成凭证"""
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE candidates SET password_hash=? WHERE username=?",
            (_hash(new_password), username),
        )
        return cur.rowcount > 0


def update_profile(username: str, data: dict) -> bool:
    allowed = ["phone", "email", "candidate_name"]
    sets = [f"{k}=?" for k in allowed if k in data]
    vals = [data[k] for k in allowed if k in data]
    if not sets:
        return False
    vals.append(username)
    with _conn() as conn:
        cur = conn.execute(f"UPDATE candidates SET {', '.join(sets)} WHERE username=?", vals)
        return cur.rowcount > 0


def logout(token: str):
    tokens.pop(token, None)
