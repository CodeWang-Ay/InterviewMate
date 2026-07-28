import sqlite3
import json

import bcrypt

from backend.config import DB_PATH
from backend.repositories import jd_repo


def _hash_password(password: str) -> str:
    if not password:
        return ""
    # 如果已经是 bcrypt 哈希（以 $2 开头），不再重复哈希
    if password.startswith("$2"):
        return password
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

PLAN_STATUSES = {"pending", "wait", "running", "finish", "cancel"}


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS workflow_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                stages TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        cols = [c[1] for c in conn.execute("PRAGMA table_info(plans)").fetchall()]
        text_cols = [
            "interview_round", "candidate_username", "candidate_password", "workflow_id", "workflow_name", "active_session_id",
            "scheduled_at", "interviewer", "meeting_url", "interview_result", "result_note",
            "recruitment_type",
        ]
        for col in text_cols:
            if col not in cols:
                conn.execute(f"ALTER TABLE plans ADD COLUMN {col} TEXT DEFAULT ''")
        int_cols = ["stage_order", "stage_count", "result_score"]
        for col in int_cols:
            if col not in cols:
                conn.execute(f"ALTER TABLE plans ADD COLUMN {col} INTEGER DEFAULT 1")
        for col in ("application_id", "resume_id", "jd_id"):
            if col not in cols:
                conn.execute(f"ALTER TABLE plans ADD COLUMN {col} INTEGER DEFAULT NULL")
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
        _seed_workflow_templates(conn)


def _seed_workflow_templates(conn) -> None:
    cnt = conn.execute("SELECT COUNT(*) FROM workflow_templates").fetchone()[0]
    if cnt > 0:
        return
    defaults = [
        {
            "name": "标准技术岗流程",
            "description": "技术一面、技术二面、HR 面，适合研发/算法/测试岗位",
            "stages": [
                {"name": "技术一面", "question_count": 10},
                {"name": "技术二面", "question_count": 8},
                {"name": "HR 面", "question_count": 6},
            ],
        },
        {
            "name": "快速招聘流程",
            "description": "综合面试、HR 面，适合应届生和批量初筛",
            "stages": [
                {"name": "综合面试", "question_count": 10},
                {"name": "HR 面", "question_count": 6},
            ],
        },
        {
            "name": "高级岗位流程",
            "description": "技术一面、技术二面、交叉面、终面，适合专家/管理岗位",
            "stages": [
                {"name": "技术一面", "question_count": 10},
                {"name": "技术二面", "question_count": 10},
                {"name": "交叉面", "question_count": 8},
                {"name": "终面", "question_count": 6},
            ],
        },
    ]
    conn.executemany(
        "INSERT INTO workflow_templates (name, description, stages) VALUES (?,?,?)",
        [(item["name"], item["description"], json.dumps(item["stages"], ensure_ascii=False)) for item in defaults],
    )


def list_workflow_templates() -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("SELECT * FROM workflow_templates ORDER BY id ASC").fetchall()
    return [_decode_workflow_template(dict(row)) for row in rows]


def save_workflow_template(data: dict, template_id: int | None = None) -> dict:
    payload = {
        "name": (data.get("name") or "未命名流程").strip() or "未命名流程",
        "description": (data.get("description") or data.get("desc") or "").strip(),
        "stages": _normalize_template_stages(data.get("stages") or []),
    }
    stages_json = json.dumps(payload["stages"], ensure_ascii=False)
    with _conn() as conn:
        if template_id:
            existing = conn.execute("SELECT * FROM workflow_templates WHERE id=?", (template_id,)).fetchone()
            if not existing:
                return {}
            conn.execute(
                "UPDATE workflow_templates SET name=?, description=?, stages=?, updated_at=datetime('now') WHERE id=?",
                (payload["name"], payload["description"], stages_json, template_id),
            )
            row = conn.execute("SELECT * FROM workflow_templates WHERE id=?", (template_id,)).fetchone()
        else:
            cur = conn.execute(
                "INSERT INTO workflow_templates (name, description, stages) VALUES (?,?,?)",
                (payload["name"], payload["description"], stages_json),
            )
            row = conn.execute("SELECT * FROM workflow_templates WHERE id=?", (cur.lastrowid,)).fetchone()
    return _decode_workflow_template(dict(row)) if row else {}


def _normalize_template_stages(stages: list) -> list[dict]:
    normalized = []
    for index, item in enumerate(stages, start=1):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or f"第 {index} 轮面试").strip()
        try:
            question_count = int(item.get("question_count") or 6)
        except (TypeError, ValueError):
            question_count = 6
        item_data = {"name": name, "question_count": min(max(question_count, 1), 30)}
        for key in ("x", "y"):
            if key in item:
                try:
                    item_data[key] = int(float(item.get(key) or 0))
                except (TypeError, ValueError):
                    item_data[key] = 0
        normalized.append(item_data)
    return normalized or [{"name": "综合面试", "question_count": 8}]


def _decode_workflow_template(row: dict) -> dict:
    try:
        stages = json.loads(row.get("stages") or "[]")
    except Exception:
        stages = []
    return {
        "id": row.get("id"),
        "name": row.get("name", ""),
        "desc": row.get("description", ""),
        "stages": _normalize_template_stages(stages),
        "created_at": row.get("created_at", ""),
        "updated_at": row.get("updated_at", ""),
    }


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
    if not any(row.get("workflow_id") for row in rows):
        return rows
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
        return _hydrate_recruitment_types([dict(r) for r in rows])


def update_resume_filename_for_candidate(username: str, filename: str) -> None:
    with _conn() as conn:
        conn.execute("UPDATE plans SET resume_filename=? WHERE candidate_username=?", (filename, username))


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


def list_by_candidate_username_group(username: str) -> list[dict]:
    if not username:
        return []
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM plans WHERE candidate_username=? ORDER BY workflow_id DESC, stage_order ASC, id ASC",
            (username,),
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
    data = {**data}
    data["recruitment_type"] = _resolve_recruitment_type(data)
    with _conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO plans (
                candidate_name, jd_name, workflow_id, workflow_name, stage_order, stage_count,
                interview_round, match_score, question_count, status, jd_filename, resume_filename,
                questions, candidate_username, candidate_password, scheduled_at, interviewer,
                meeting_url, interview_result, result_score, result_note, recruitment_type
                , application_id, resume_id, jd_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (data.get("candidate_name", ""), data.get("jd_name", ""),
             data.get("workflow_id", ""), data.get("workflow_name", ""),
             data.get("stage_order", 1), data.get("stage_count", 1),
             data.get("interview_round", ""),
             data.get("match_score", 0),
             data.get("question_count", 0), data.get("status", "wait"),
             data.get("jd_filename", ""), data.get("resume_filename", ""),
             data.get("questions", "[]"), data.get("candidate_username", ""),
             _hash_password(data.get("candidate_password", "")), data.get("scheduled_at", ""),
             data.get("interviewer", ""), data.get("meeting_url", ""),
             data.get("interview_result", ""), data.get("result_score", 0),
             data.get("result_note", ""), data.get("recruitment_type", "社招"),
             data.get("application_id"), data.get("resume_id"), data.get("jd_id")),
        )
        row = conn.execute("SELECT * FROM plans WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row) if row else {}


def update(pid: int, data: dict) -> dict | None:
    existing = get_by_id(pid)
    if not existing:
        return None
    if "status" in data:
        data["status"] = normalize_status(data.get("status"))
    if "jd_name" in data and "recruitment_type" not in data:
        data["recruitment_type"] = _resolve_recruitment_type(data)
    allowed = ["candidate_name", "jd_name", "interview_round", "match_score", "question_count", "status",
               "jd_filename", "resume_filename", "questions", "candidate_username", "candidate_password",
               "workflow_id", "workflow_name", "stage_order", "stage_count", "active_session_id",
               "scheduled_at", "interviewer", "meeting_url", "interview_result", "result_score", "result_note",
               "recruitment_type"]
    allowed += ["application_id", "resume_id", "jd_id"]
    if "candidate_password" in data:
        data = {**data, "candidate_password": _hash_password(data["candidate_password"])}
    sets = [f"{f}=?" for f in allowed if f in data]
    vals = [data[f] for f in allowed if f in data]
    if not sets:
        return existing
    vals.append(pid)
    with _conn() as conn:
        conn.execute(f"UPDATE plans SET {', '.join(sets)} WHERE id=?", vals)
    return get_by_id(pid)


def normalize_status(status: str | None) -> str:
    text = str(status or "").strip()
    return text if text in PLAN_STATUSES else "pending"


def transition(pid: int, action: str, payload: dict | None = None) -> dict | None:
    payload = payload or {}
    current = get_by_id(pid)
    if not current:
        return None
    action = str(action or "").strip()
    if action == "start":
        if current.get("status") == "pending" and not _previous_stages_finished(current):
            raise ValueError("当前环节还不能发起，请先完成前序面试")
        if current.get("status") not in {"pending", "wait", "running"}:
            raise ValueError("当前环节状态不支持发起")
        return update(pid, {"status": "running", **_pick_plan_payload(payload)})
    if action == "finish":
        data = {"status": "finish", "active_session_id": "", **_pick_result_payload(payload)}
        return update(pid, data)
    if action == "cancel":
        updated = update(pid, {"status": "cancel", "active_session_id": "", **_pick_result_payload(payload)})
        _reconcile_workflow_for_plan(pid)
        return updated
    if action == "reopen":
        target_status = "wait" if _previous_stages_finished(current) else "pending"
        return update(pid, {"status": target_status, "active_session_id": ""})
    if action == "reset":
        target_status = "wait" if int(current.get("stage_order") or 1) == 1 else "pending"
        return update(pid, {"status": target_status, "active_session_id": "", "interview_result": "", "result_score": 0, "result_note": ""})
    raise ValueError("不支持的状态动作")


def mark_finished(pid: int, payload: dict | None = None) -> dict | None:
    return transition(pid, "finish", payload or {})


def _pick_plan_payload(payload: dict) -> dict:
    fields = ["scheduled_at", "interviewer", "meeting_url"]
    return {field: payload[field] for field in fields if field in payload}


def _pick_result_payload(payload: dict) -> dict:
    fields = ["interview_result", "result_score", "result_note"]
    return {field: payload[field] for field in fields if field in payload}


def _previous_stages_finished(plan: dict) -> bool:
    workflow_id = plan.get("workflow_id")
    stage_order = int(plan.get("stage_order") or 1)
    if not workflow_id or stage_order <= 1:
        return True
    previous = [p for p in list_by_workflow_id(workflow_id) if int(p.get("stage_order") or 1) < stage_order and p.get("status") != "cancel"]
    return all(p.get("status") == "finish" for p in previous)


def _reconcile_workflow_for_plan(pid: int) -> None:
    plan = get_by_id(pid)
    if plan and plan.get("workflow_id"):
        _reconcile_workflow_status(plan["workflow_id"])


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
    previous_finished = True
    for index, plan in enumerate(plans):
        status = plan.get("status") or "pending"
        if status in {"finish", "running", "cancel"}:
            expected = status
        elif index == 0:
            expected = "wait"
        elif status == "wait":
            expected = "wait" if previous_finished else "pending"
        else:
            expected = "pending"
        if status != expected:
            updates.append((expected, plan["id"]))
            plan["status"] = expected
        previous_finished = expected == "finish" or expected == "cancel"

    if updates:
        with _conn() as conn:
            conn.executemany("UPDATE plans SET status=? WHERE id=?", updates)


def delete(pid: int) -> bool:
    with _conn() as conn:
        return conn.execute("DELETE FROM plans WHERE id=?", (pid,)).rowcount > 0


def _resolve_recruitment_type(data: dict) -> str:
    current = str(data.get("recruitment_type") or "").strip()
    if current:
        return current
    jd = jd_repo.get_by_name(data.get("jd_name", ""))
    return str((jd or {}).get("recruitment_type") or "社招").strip() or "社招"


def _hydrate_recruitment_types(rows: list[dict]) -> list[dict]:
    cache: dict[str, str] = {}
    updates: list[tuple[str, int]] = []
    for row in rows:
        current = str(row.get("recruitment_type") or "").strip()
        if not current:
            name = str(row.get("jd_name") or "").strip()
            if name not in cache:
                jd = jd_repo.get_by_name(name)
                cache[name] = str((jd or {}).get("recruitment_type") or "社招").strip() or "社招"
            current = cache[name]
            row["recruitment_type"] = current
            if row.get("id"):
                updates.append((current, row["id"]))
    if updates:
        with _conn() as conn:
            conn.executemany("UPDATE plans SET recruitment_type=? WHERE id=?", updates)
    return rows
