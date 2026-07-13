import hashlib
import sqlite3
import uuid
from datetime import datetime

from backend.config import DB_PATH


def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


# 简单的 token 存储（内存）
tokens: dict[str, str] = {}


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                nickname TEXT DEFAULT '',
                avatar TEXT DEFAULT '',
                email TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                company TEXT DEFAULT '',
                bio TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        # 兼容旧表：添加 avatar 列
        cols = [c[1] for c in conn.execute("PRAGMA table_info(users)").fetchall()]
        for col in ["avatar", "email", "phone", "company", "bio"]:
            if col not in cols:
                conn.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT ''")
        # 默认管理员
        conn.execute(
            "INSERT OR IGNORE INTO users (username, password_hash, nickname) VALUES (?,?,?)",
            ("admin", _hash("admin123"), "管理员"),
        )


def register(username: str, password: str, nickname: str = "") -> dict | None:
    if len(password) < 6:
        return None
    try:
        with _conn() as conn:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash, nickname) VALUES (?,?,?)",
                (username, _hash(password), nickname or username),
            )
            return {"id": cur.lastrowid, "username": username, "nickname": nickname or username}
    except sqlite3.IntegrityError:
        return None


def login(username: str, password: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username=? AND password_hash=?",
            (username, _hash(password)),
        ).fetchone()
    if not row:
        return None
    # 生成 token
    token = uuid.uuid4().hex
    tokens[token] = username
    return {
        "token": token, "username": username,
        "nickname": row["nickname"] or username,
        "avatar": row["avatar"] or "",
        "email": row["email"] or "",
        "phone": row["phone"] or "",
        "company": row["company"] or "",
        "bio": row["bio"] or "",
        "role": row["role"] or "user",
    }


def get_user_by_token(token: str) -> str | None:
    return tokens.get(token)


def get_user_info(username: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    return dict(row) if row else None


def update_profile(username: str, data: dict) -> bool:
    allowed = ["nickname", "email", "phone", "company", "bio"]
    sets = [f"{k}=?" for k in allowed if k in data]
    vals = [data[k] for k in allowed if k in data]
    if not sets:
        return False
    vals.append(username)
    with _conn() as conn:
        cur = conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE username=?", vals)
        return cur.rowcount > 0


def change_password(username: str, old_password: str, new_password: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE username=? AND password_hash=?",
            (username, _hash(old_password)),
        ).fetchone()
        if not row:
            return False
        conn.execute("UPDATE users SET password_hash=? WHERE username=?", (_hash(new_password), username))
        return True


def update_avatar(username: str, avatar_url: str) -> bool:
    with _conn() as conn:
        cur = conn.execute("UPDATE users SET avatar=? WHERE username=?", (avatar_url, username))
        return cur.rowcount > 0


def logout(token: str):
    tokens.pop(token, None)
