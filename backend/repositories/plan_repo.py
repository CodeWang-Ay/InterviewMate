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
                workflow_id TEXT DEFAULT '',
                workflow_name TEXT DEFAULT '',
                stage_order INTEGER DEFAULT 1,
                stage_count INTEGER DEFAULT 1,
                interview_round TEXT DEFAULT '',
                match_score INTEGER DEFAULT 0,
                question_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'wait',
                jd_filename TEXT DEFAULT '',
                resume_filename TEXT DEFAULT '',
                questions TEXT DEFAULT '[]',
                candidate_username TEXT DEFAULT '',
                candidate_password TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        cols = [c[1] for c in conn.execute("PRAGMA table_info(plans)").fetchall()]
        text_cols = ["interview_round", "candidate_username", "candidate_password", "workflow_id", "workflow_name", "active_session_id"]
        for col in text_cols:
            if col not in cols:
                conn.execute(f"ALTER TABLE plans ADD COLUMN {col} TEXT DEFAULT ''")
        int_cols = ["stage_order", "stage_count"]
        for col in int_cols:
            if col not in cols:
                conn.execute(f"ALTER TABLE plans ADD COLUMN {col} INTEGER DEFAULT 1")
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
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    _reconcile_workflows(rows)
    with _conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def list_by_candidate_username(username: str) -> list[dict]:
    with _conn() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM plans WHERE candidate_username=? ORDER BY workflow_id DESC, stage_order ASC, id ASC",
            (username,),
        ).fetchall()]
    _reconcile_workflows(rows)
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM plans WHERE candidate_username=? ORDER BY workflow_id DESC, stage_order ASC, id ASC",
            (username,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_by_id(pid: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM plans WHERE id=?", (pid,)).fetchone()
        return dict(row) if row else None


def list_by_workflow_id(workflow_id: str) -> list[dict]:
    if not workflow_id:
        return []
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM plans WHERE workflow_id=? ORDER BY stage_order ASC, id ASC",
            (workflow_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def list_by_resume_filename(resume_filename: str) -> list[dict]:
    if not resume_filename:
        return []
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM plans WHERE resume_filename=? ORDER BY stage_order ASC, id ASC",
            (resume_filename,),
        ).fetchall()
        return [dict(r) for r in rows]


def find_latest_by_resume_filename(resume_filename: str) -> dict | None:
    if not resume_filename:
        return None
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM plans WHERE resume_filename=? ORDER BY id DESC LIMIT 1",
            (resume_filename,),
        ).fetchone()
        return dict(row) if row else None


def create(data: dict) -> dict:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO plans (candidate_name, jd_name, workflow_id, workflow_name, stage_order, stage_count, interview_round, match_score, question_count, status, jd_filename, resume_filename, questions, candidate_username, candidate_password) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (data.get("candidate_name", ""), data.get("jd_name", ""),
             data.get("workflow_id", ""), data.get("workflow_name", ""),
             data.get("stage_order", 1), data.get("stage_count", 1),
             data.get("interview_round", ""),
             data.get("match_score", 0),
             data.get("question_count", 0), data.get("status", "wait"),
             data.get("jd_filename", ""), data.get("resume_filename", ""),
             data.get("questions", "[]"), data.get("candidate_username", ""),
             data.get("candidate_password", "")),
        )
        row = conn.execute("SELECT * FROM plans WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row) if row else {}


def update(pid: int, data: dict) -> dict | None:
    existing = get_by_id(pid)
    if not existing:
        return None
    allowed = ["candidate_name", "jd_name", "interview_round", "match_score", "question_count", "status",
               "jd_filename", "resume_filename", "questions", "candidate_username", "candidate_password",
               "workflow_id", "workflow_name", "stage_order", "stage_count", "active_session_id"]
    sets = [f"{f}=?" for f in allowed if f in data]
    vals = [data[f] for f in allowed if f in data]
    if not sets:
        return existing
    vals.append(pid)
    with _conn() as conn:
        conn.execute(f"UPDATE plans SET {', '.join(sets)} WHERE id=?", vals)
    return get_by_id(pid)


def activate_next_stage(pid: int) -> dict | None:
    current = get_by_id(pid)
    if not current or not current.get("workflow_id"):
        return None
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM plans WHERE workflow_id=? AND stage_order>? AND status='pending' ORDER BY stage_order ASC, id ASC LIMIT 1",
            (current["workflow_id"], current.get("stage_order", 0)),
        ).fetchone()
        if not row:
            return None
        next_id = row["id"]
        conn.execute("UPDATE plans SET status='wait' WHERE id=?", (next_id,))
    return get_by_id(next_id)


def _reconcile_workflows(rows: list[dict]) -> None:
    workflow_ids = {row.get("workflow_id") for row in rows if row.get("workflow_id")}
    for workflow_id in workflow_ids:
        _reconcile_workflow_status(workflow_id)


def _reconcile_workflow_status(workflow_id: str) -> None:
    plans = list_by_workflow_id(workflow_id)
    if not plans:
        return

    updates: list[tuple[str, int]] = []
    for index, plan in enumerate(plans):
        status = plan.get("status") or "pending"
        if index == 0:
            expected = "wait" if status == "pending" else status
        else:
            prev_status = plans[index - 1].get("status")
            expected = "wait" if prev_status == "finish" else "pending"
            if status in {"finish", "running", "cancel"}:
                expected = status
        if status != expected:
            updates.append((expected, plan["id"]))
            plan["status"] = expected

    if updates:
        with _conn() as conn:
            conn.executemany("UPDATE plans SET status=? WHERE id=?", updates)


def delete(pid: int) -> bool:
    with _conn() as conn:
        return conn.execute("DELETE FROM plans WHERE id=?", (pid,)).rowcount > 0
