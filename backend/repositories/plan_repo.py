import sqlite3
from backend.config import DB_PATH


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_name TEXT DEFAULT '',
                jd_name TEXT DEFAULT '',
                match_score INTEGER DEFAULT 0,
                question_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'wait',
                jd_filename TEXT DEFAULT '',
                resume_filename TEXT DEFAULT '',
                questions TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        cnt = conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
        if cnt == 0:
            samples = [
                ("李明", "后端开发工程师", 82, 12, "wait", "2026-07-10 16:20"),
                ("王小雨", "前端开发工程师", 75, 10, "finish", "2026-07-09 20:15"),
                ("张伟", "大模型算法工程师", 63, 14, "running", "2026-07-08 11:32"),
                ("陈琳", "测试工程师", 78, 9, "cancel", "2026-07-07 15:40"),
            ]
            conn.executemany(
                "INSERT INTO plans (candidate_name, jd_name, match_score, question_count, status, created_at) VALUES (?,?,?,?,?,?)",
                samples,
            )


def list_all(search: str = "", status: str = "") -> list[dict]:
    sql = "SELECT * FROM plans WHERE 1=1"
    params = []
    if status:
        sql += " AND status=?"
        params.append(status)
    if search:
        sql += " AND (candidate_name LIKE ? OR jd_name LIKE ?)"
        p = f"%{search}%"
        params.extend([p, p])
    sql += " ORDER BY id DESC"
    with _conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_by_id(pid: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM plans WHERE id=?", (pid,)).fetchone()
        return dict(row) if row else None


def create(data: dict) -> dict:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO plans (candidate_name, jd_name, match_score, question_count, status, jd_filename, resume_filename, questions) VALUES (?,?,?,?,?,?,?,?)",
            (data.get("candidate_name", ""), data.get("jd_name", ""), data.get("match_score", 0),
             data.get("question_count", 0), data.get("status", "wait"),
             data.get("jd_filename", ""), data.get("resume_filename", ""),
             data.get("questions", "[]")),
        )
        return get_by_id(cur.lastrowid)


def update(pid: int, data: dict) -> dict | None:
    existing = get_by_id(pid)
    if not existing:
        return None
    allowed = ["candidate_name", "jd_name", "match_score", "question_count", "status",
               "jd_filename", "resume_filename", "questions"]
    sets = [f"{f}=?" for f in allowed if f in data]
    vals = [data[f] for f in allowed if f in data]
    if not sets:
        return existing
    vals.append(pid)
    with _conn() as conn:
        conn.execute(f"UPDATE plans SET {', '.join(sets)} WHERE id=?", vals)
    return get_by_id(pid)


def delete(pid: int) -> bool:
    with _conn() as conn:
        return conn.execute("DELETE FROM plans WHERE id=?", (pid,)).rowcount > 0
