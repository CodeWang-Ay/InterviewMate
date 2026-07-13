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
            CREATE TABLE IF NOT EXISTS admins (
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
        cols = [c[1] for c in conn.execute("PRAGMA table_info(admins)").fetchall()]
        for col in ["avatar", "email", "phone", "company", "bio"]:
            if col not in cols:
                conn.execute(f"ALTER TABLE admins ADD COLUMN {col} TEXT DEFAULT ''")

        _migrate_legacy_admins(conn)

        conn.execute(
            "INSERT OR IGNORE INTO admins (username, password_hash, nickname) VALUES (?,?,?)",
            ("admin", _hash("admin123"), "管理员"),
        )


def _migrate_legacy_admins(conn) -> None:
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "users" not in tables:
        return

    user_cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    has_role = "role" in user_cols
    select_cols = ["username", "password_hash", "nickname"]
    if "avatar" in user_cols:
        select_cols.append("avatar")
    if "email" in user_cols:
        select_cols.append("email")
    if "phone" in user_cols:
        select_cols.append("phone")
    if "company" in user_cols:
        select_cols.append("company")
    if "bio" in user_cols:
        select_cols.append("bio")
    if has_role:
        select_cols.append("role")
    sql = f"SELECT {', '.join(select_cols)} FROM users"
    for row in conn.execute(sql).fetchall():
        data = dict(row)
        role = data.get("role", "user") if has_role else ("admin" if data.get("username") == "admin" else "user")
        if role != "admin":
            continue
        conn.execute(
            """
            INSERT OR IGNORE INTO admins
            (username, password_hash, nickname, avatar, email, phone, company, bio)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                data.get("username", ""),
                data.get("password_hash", ""),
                data.get("nickname", "") or data.get("username", ""),
                data.get("avatar", "") or "",
                data.get("email", "") or "",
                data.get("phone", "") or "",
                data.get("company", "") or "",
                data.get("bio", "") or "",
            ),
        )


def register(username: str, password: str, nickname: str = "") -> dict | None:
    if len(password) < 6:
        return None
    try:
        with _conn() as conn:
            cur = conn.execute(
                "INSERT INTO admins (username, password_hash, nickname) VALUES (?,?,?)",
                (username, _hash(password), nickname or username),
            )
            return {"id": cur.lastrowid, "username": username, "nickname": nickname or username}
    except sqlite3.IntegrityError:
        return None


def login(username: str, password: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM admins WHERE username=? AND password_hash=?",
            (username, _hash(password)),
        ).fetchone()
    if not row:
        return None
    token = uuid.uuid4().hex
    tokens[token] = username
    return {
        "token": token,
        "username": username,
        "nickname": row["nickname"] or username,
        "avatar": row["avatar"] or "",
        "email": row["email"] or "",
        "phone": row["phone"] or "",
        "company": row["company"] or "",
        "bio": row["bio"] or "",
        "role": "admin",
    }


def get_admin_by_token(token: str) -> str | None:
    return tokens.get(token)


def get_admin_info(username: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM admins WHERE username=?", (username,)).fetchone()
    return dict(row) if row else None


def update_profile(username: str, data: dict) -> bool:
    allowed = ["nickname", "email", "phone", "company", "bio"]
    sets = [f"{k}=?" for k in allowed if k in data]
    vals = [data[k] for k in allowed if k in data]
    if not sets:
        return False
    vals.append(username)
    with _conn() as conn:
        cur = conn.execute(f"UPDATE admins SET {', '.join(sets)} WHERE username=?", vals)
        return cur.rowcount > 0


def change_password(username: str, old_password: str, new_password: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT id FROM admins WHERE username=? AND password_hash=?",
            (username, _hash(old_password)),
        ).fetchone()
        if not row:
            return False
        conn.execute("UPDATE admins SET password_hash=? WHERE username=?", (_hash(new_password), username))
        return True


def update_avatar(username: str, avatar_url: str) -> bool:
    with _conn() as conn:
        cur = conn.execute("UPDATE admins SET avatar=? WHERE username=?", (avatar_url, username))
        return cur.rowcount > 0


def logout(token: str):
    tokens.pop(token, None)
