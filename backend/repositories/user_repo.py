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
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
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
    return {"token": token, "username": username, "nickname": row["nickname"] or username}


def get_user_by_token(token: str) -> str | None:
    return tokens.get(token)


def logout(token: str):
    tokens.pop(token, None)
