import sqlite3

from backend.config import DB_PATH


class _ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=5, factory=_ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    with _conn() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS assistant_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, identity_kind TEXT NOT NULL, username TEXT NOT NULL,
            title TEXT DEFAULT '新对话', created_at TEXT DEFAULT (datetime('now')), updated_at TEXT DEFAULT (datetime('now'))
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS assistant_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER NOT NULL, role TEXT NOT NULL,
            content TEXT DEFAULT '', feedback TEXT DEFAULT '', created_at TEXT DEFAULT (datetime('now'))
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_assistant_conversation_owner ON assistant_conversations(identity_kind,username,id DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_assistant_messages_conversation ON assistant_messages(conversation_id,id)")


def create_conversation(kind: str, username: str, title: str = "新对话") -> dict:
    init_db()
    with _conn() as conn:
        cur = conn.execute("INSERT INTO assistant_conversations (identity_kind,username,title) VALUES (?,?,?)", (kind, username, title[:60] or "新对话"))
        row = conn.execute("SELECT * FROM assistant_conversations WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)


def list_conversations(kind: str, username: str) -> list[dict]:
    init_db()
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM assistant_conversations WHERE identity_kind=? AND username=? ORDER BY updated_at DESC,id DESC", (kind, username)).fetchall()
    return [dict(row) for row in rows]


def owned_conversation(conversation_id: int, kind: str, username: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM assistant_conversations WHERE id=? AND identity_kind=? AND username=?", (conversation_id, kind, username)).fetchone()
    return dict(row) if row else None


def add_message(conversation_id: int, role: str, content: str) -> dict:
    with _conn() as conn:
        cur = conn.execute("INSERT INTO assistant_messages (conversation_id,role,content) VALUES (?,?,?)", (conversation_id, role, content))
        conn.execute("UPDATE assistant_conversations SET updated_at=datetime('now') WHERE id=?", (conversation_id,))
        row = conn.execute("SELECT * FROM assistant_messages WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row)


def update_message(message_id: int, content: str) -> dict | None:
    with _conn() as conn:
        conn.execute("UPDATE assistant_messages SET content=? WHERE id=?", (content, message_id))
        row = conn.execute("SELECT * FROM assistant_messages WHERE id=?", (message_id,)).fetchone()
    return dict(row) if row else None


def list_messages(conversation_id: int, kind: str, username: str) -> list[dict] | None:
    if not owned_conversation(conversation_id, kind, username):
        return None
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM assistant_messages WHERE conversation_id=? ORDER BY id", (conversation_id,)).fetchall()
    return [dict(row) for row in rows]


def set_feedback(message_id: int, conversation_id: int, kind: str, username: str, feedback: str) -> bool:
    if not owned_conversation(conversation_id, kind, username):
        return False
    with _conn() as conn:
        cur = conn.execute("UPDATE assistant_messages SET feedback=? WHERE id=? AND conversation_id=? AND role='assistant'", (feedback, message_id, conversation_id))
    return cur.rowcount > 0


def delete_conversation(conversation_id: int, kind: str, username: str) -> bool:
    if not owned_conversation(conversation_id, kind, username):
        return False
    with _conn() as conn:
        conn.execute("DELETE FROM assistant_messages WHERE conversation_id=?", (conversation_id,))
        conn.execute("DELETE FROM assistant_conversations WHERE id=?", (conversation_id,))
    return True
