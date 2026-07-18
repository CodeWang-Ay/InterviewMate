import json
import sqlite3
from datetime import datetime

from backend.config import DB_PATH


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS async_tasks (
                id TEXT PRIMARY KEY,
                task_type TEXT DEFAULT '',
                title TEXT DEFAULT '',
                status TEXT DEFAULT 'queued',
                progress INTEGER DEFAULT 0,
                message TEXT DEFAULT '',
                result_json TEXT DEFAULT '{}',
                error TEXT DEFAULT '',
                owner_kind TEXT DEFAULT 'admin',
                owner_username TEXT DEFAULT '',
                created_at TEXT DEFAULT '',
                updated_at TEXT DEFAULT ''
            )
        """)


def create(task_id: str, task_type: str, title: str, owner: dict | None = None) -> dict:
    owner = owner or {}
    now = _now()
    with _conn() as conn:
        conn.execute(
            """
            INSERT INTO async_tasks (
                id, task_type, title, status, progress, message, result_json, error,
                owner_kind, owner_username, created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                task_id,
                task_type,
                title,
                "queued",
                0,
                "任务已创建，等待处理",
                "{}",
                "",
                owner.get("kind", "admin"),
                owner.get("username", ""),
                now,
                now,
            ),
        )
    return get(task_id) or {}


def update(task_id: str, **fields) -> dict | None:
    allowed = ["status", "progress", "message", "result_json", "error"]
    if "result" in fields:
        fields["result_json"] = json.dumps(fields.pop("result") or {}, ensure_ascii=False)
    sets = [f"{key}=?" for key in allowed if key in fields]
    vals = [fields[key] for key in allowed if key in fields]
    if not sets:
        return get(task_id)
    vals.extend([_now(), task_id])
    with _conn() as conn:
        conn.execute(
            f"UPDATE async_tasks SET {', '.join(sets)}, updated_at=? WHERE id=?",
            vals,
        )
    return get(task_id)


def get(task_id: str) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM async_tasks WHERE id=?", (task_id,)).fetchone()
    return _decode(dict(row)) if row else None


def list_recent(owner: dict | None = None, limit: int = 30) -> list[dict]:
    limit = min(max(int(limit or 30), 1), 100)
    sql = "SELECT * FROM async_tasks"
    params: list = []
    if owner and owner.get("kind") != "admin":
        sql += " WHERE owner_kind=? AND owner_username=?"
        params.extend([owner.get("kind", ""), owner.get("username", "")])
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with _conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [_decode(dict(row)) for row in rows]


def _decode(row: dict) -> dict:
    try:
        result = json.loads(row.get("result_json") or "{}")
    except Exception:
        result = {}
    row["result"] = result
    row.pop("result_json", None)
    return row
