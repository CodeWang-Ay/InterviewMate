import sqlite3
from backend.config import DB_PATH


def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS operation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_username TEXT NOT NULL,
                actor_role TEXT DEFAULT '',
                action TEXT NOT NULL,
                resource_type TEXT DEFAULT '',
                resource_id TEXT DEFAULT '',
                before_data TEXT DEFAULT '{}',
                after_data TEXT DEFAULT '{}',
                result TEXT DEFAULT 'success',
                reason TEXT DEFAULT '',
                ip_address TEXT DEFAULT '',
                user_agent TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_operation_logs_created ON operation_logs(created_at DESC)")


def record(actor: dict, action: str, resource_type: str = '', resource_id: str = '',
           before_data: str = '{}', after_data: str = '{}', reason: str = '',
           result: str = 'success', ip_address: str = '', user_agent: str = ''):
    with _conn() as conn:
        conn.execute("""INSERT INTO operation_logs
            (actor_username, actor_role, action, resource_type, resource_id,
             before_data, after_data, result, reason, ip_address, user_agent)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (actor.get('username', ''), actor.get('role', ''), action, resource_type,
             str(resource_id), before_data, after_data, result, reason, ip_address, user_agent))


def list_logs(limit: int = 100):
    with _conn() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM operation_logs ORDER BY id DESC LIMIT ?", (max(1, min(limit, 500)),)
        ).fetchall()]
