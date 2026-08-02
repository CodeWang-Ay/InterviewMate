import os
import sqlite3
import hashlib
import time

from backend.config import DB_PATH, UPLOAD_DIR

RESUME_STATUS_OPTIONS = ["待筛选", "初筛通过", "不合适"]


class _ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def _conn():
    c = sqlite3.connect(DB_PATH, timeout=5, factory=_ClosingConnection)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=5000")
    return c


def init_db():
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS resumes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT DEFAULT '',
                target_position TEXT DEFAULT '',
                education TEXT DEFAULT '',
                experience_years TEXT DEFAULT '',
                skills TEXT DEFAULT '',
                file_path TEXT DEFAULT '',
                file_type TEXT DEFAULT '',
                parse_status TEXT DEFAULT 'wait',
                candidate_status TEXT DEFAULT '待筛选',
                structured_data TEXT DEFAULT '{}',
                jd_id INTEGER DEFAULT NULL,
                jd_name TEXT DEFAULT '',
                file_md5 TEXT DEFAULT '',
                candidate_username TEXT DEFAULT '',
                source TEXT DEFAULT 'admin',
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        _ensure_columns(conn)
        _normalize_existing_candidate_status(conn)
        _backfill_file_md5(conn)
        cnt = conn.execute("SELECT COUNT(*) FROM resumes").fetchone()[0]
        if cnt == 0:
            samples = [
                ("李明", "后端开发工程师", "本科", "3年", "Java, SpringBoot, MySQL, Redis, 微服务", "", "", "success"),
                ("王小雨", "前端开发工程师", "硕士", "2年", "Vue3, TypeScript, Vite, ElementPlus, Axios", "", "", "success"),
                ("张伟", "算法工程师", "硕士", "5年", "Python, PyTorch, NLP, LLM", "张伟_算法.pdf", "pdf", "wait"),
                ("陈琳", "测试工程师", "本科", "4年", "Selenium, JMeter, Python", "陈琳_测试.docx", "docx", "fail"),
            ]
            conn.executemany(
                "INSERT INTO resumes (name, target_position, education, experience_years, skills, file_path, file_type, parse_status) VALUES (?,?,?,?,?,?,?,?)",
                samples,
            )


def _ensure_columns(conn) -> None:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(resumes)").fetchall()}
    if "candidate_status" not in cols:
        conn.execute("ALTER TABLE resumes ADD COLUMN candidate_status TEXT DEFAULT '待筛选'")
    if "file_md5" not in cols:
        conn.execute("ALTER TABLE resumes ADD COLUMN file_md5 TEXT DEFAULT ''")
    if "original_name" not in cols:
        conn.execute("ALTER TABLE resumes ADD COLUMN original_name TEXT DEFAULT ''")
    if "candidate_username" not in cols:
        conn.execute("ALTER TABLE resumes ADD COLUMN candidate_username TEXT DEFAULT ''")
    if "source" not in cols:
        conn.execute("ALTER TABLE resumes ADD COLUMN source TEXT DEFAULT 'admin'")
    if "deleted_at" not in cols:
        conn.execute("ALTER TABLE resumes ADD COLUMN deleted_at TEXT DEFAULT NULL")
    if "deleted_by" not in cols:
        conn.execute("ALTER TABLE resumes ADD COLUMN deleted_by TEXT DEFAULT ''")
    if "delete_reason" not in cols:
        conn.execute("ALTER TABLE resumes ADD COLUMN delete_reason TEXT DEFAULT ''")
    if "parsed_at" not in cols:
        conn.execute("ALTER TABLE resumes ADD COLUMN parsed_at TEXT DEFAULT ''")
    if "parse_error" not in cols:
        conn.execute("ALTER TABLE resumes ADD COLUMN parse_error TEXT DEFAULT ''")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_resumes_candidate ON resumes(candidate_username)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_resumes_file_md5 ON resumes(file_md5)")


def _normalize_existing_candidate_status(conn) -> None:
    for row in conn.execute("SELECT id, candidate_status FROM resumes").fetchall():
        normalized = normalize_candidate_status(row["candidate_status"])
        if normalized != (row["candidate_status"] or ""):
            conn.execute("UPDATE resumes SET candidate_status=? WHERE id=?", (normalized, row["id"]))


def _backfill_file_md5(conn) -> None:
    rows = conn.execute("SELECT id, file_path FROM resumes WHERE IFNULL(file_md5, '')='' AND IFNULL(file_path, '')!=''").fetchall()
    for row in rows:
        fpath = os.path.join(UPLOAD_DIR, "resume", row["file_path"])
        if not os.path.exists(fpath):
            continue
        digest = hashlib.md5()
        with open(fpath, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(chunk)
        conn.execute("UPDATE resumes SET file_md5=? WHERE id=?", (digest.hexdigest(), row["id"]))


def _build_where(search: str = "", parse_status: str = "", experience_years: str = "", candidate_status: str = "", source: str = "") -> tuple[str, list]:
    sql = " WHERE 1=1"
    params = []
    if candidate_status:
        sql += " AND candidate_status=?"
        params.append(candidate_status)
    if source:
        sql += " AND source=?"
        params.append(source)
    if parse_status:
        sql += " AND parse_status=?"
        params.append(parse_status)
    if experience_years:
        sql += " AND experience_years=?"
        params.append(experience_years)
    if search:
        sql += " AND (name LIKE ? OR skills LIKE ? OR target_position LIKE ? OR jd_name LIKE ? OR original_name LIKE ?)"
        p = f"%{search}%"
        params.extend([p, p, p, p, p])
    return sql, params


def list_all(search: str = "", parse_status: str = "", experience_years: str = "", candidate_status: str = "", source: str = "") -> list[dict]:
    where, params = _build_where(search, parse_status, experience_years, candidate_status, source)
    where = (" WHERE IFNULL(deleted_at, '')=''" + (" AND " + where[7:] if where.startswith(" WHERE ") else where)) if where else " WHERE IFNULL(deleted_at, '')=''"
    sql = f"SELECT * FROM resumes{where} ORDER BY id DESC"
    with _conn() as conn:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    return [_enrich_jd_fields(row) for row in rows]


def list_paged(search: str = "", parse_status: str = "", experience_years: str = "", candidate_status: str = "", source: str = "", page: int = 1, page_size: int = 10) -> tuple[list[dict], int]:
    page = max(1, int(page or 1))
    page_size = min(max(1, int(page_size or 10)), 10000)
    where, params = _build_where(search, parse_status, experience_years, candidate_status, source)
    where = (" WHERE IFNULL(deleted_at, '')=''" + (" AND " + where[7:] if where.startswith(" WHERE ") else where)) if where else " WHERE IFNULL(deleted_at, '')=''"
    offset = (page - 1) * page_size
    with _conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM resumes{where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM resumes{where} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()
    return [_enrich_jd_fields(dict(row)) for row in rows], total


def _management_where(
    search: str = "",
    parse_status: str = "",
    experience_years: str = "",
    candidate_status: str = "",
    recruitment_type: str = "",
    source: str = "",
    archived: str = "",
    scope: str = "applications",
) -> tuple[str, list]:
    sql = " WHERE IFNULL(r.deleted_at, '')" + ("<>''" if archived == "archived" else "=''")
    params = []
    if candidate_status:
        # 已投递简历的页面状态来自 application；未投递简历才使用简历自身状态。
        sql += " AND CASE WHEN a.id IS NOT NULL THEN COALESCE(a.screening_status, '待筛选') ELSE COALESCE(r.candidate_status, '待筛选') END=?"
        params.append(candidate_status)
    if recruitment_type:
        sql += " AND COALESCE(a.recruitment_type, '')=?"
        params.append(recruitment_type)
    if source:
        if source == "admin":
            sql += " AND COALESCE(a.source, r.source) IN ('admin', 'import')"
        else:
            sql += " AND COALESCE(a.source, r.source)=?"
            params.append(source)
    if parse_status:
        sql += " AND r.parse_status=?"
        params.append(parse_status)
    if experience_years:
        sql += " AND r.experience_years=?"
        params.append(experience_years)
    if search:
        sql += """
            AND (
                r.name LIKE ? OR r.skills LIKE ? OR r.target_position LIKE ?
                OR COALESCE(a.jd_name, r.jd_name) LIKE ? OR r.original_name LIKE ?
                OR r.candidate_username LIKE ?
            )
        """
        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern, pattern, pattern, pattern])
    return sql, params


def _management_row(row: sqlite3.Row) -> dict:
    item = dict(row)
    item["avatar"] = item.pop("candidate_avatar", "") or item.get("avatar", "") or ""
    application_id = item.pop("joined_application_id", None)
    application_jd_id = item.pop("application_jd_id", None)
    application_jd_name = item.pop("application_jd_name", "")
    application_recruitment_type = item.pop("application_recruitment_type", "")
    application_source = item.pop("application_source", "")
    application_status = item.pop("joined_application_status", "")
    application_current_stage = item.pop("application_current_stage", "")
    application_workflow_id = item.pop("application_workflow_id", "")
    application_plan_count = item.pop("application_plan_count", 0)
    application_screening_status = item.pop("application_screening_status", "")
    application_created_at = item.pop("application_created_at", "")
    if application_id:
        item["application_id"] = application_id
        item["application_status"] = application_status
        item["application_current_stage"] = application_current_stage
        item["application_workflow_id"] = application_workflow_id
        item["application_plan_count"] = int(application_plan_count or 0)
        item["jd_id"] = application_jd_id
        item["jd_name"] = application_jd_name or ""
        item["recruitment_type"] = application_recruitment_type or item.get("recruitment_type") or ""
        item["source"] = application_source or item.get("source") or "candidate"
        item["candidate_status"] = application_screening_status or item.get("candidate_status") or "待筛选"
        item["record_created_at"] = application_created_at or item.get("created_at") or ""
        item["record_key"] = f"application:{application_id}"
        # 投递表保存的是投递当时绑定的 JD，后台列表必须以它为准。
        return item
    else:
        item["application_id"] = None
        item["application_status"] = ""
        item["record_key"] = f"resume:{item['id']}"
        item["record_created_at"] = item.get("created_at") or ""
    return _enrich_jd_fields(item)


def list_management_paged(
    search: str = "",
    parse_status: str = "",
    experience_years: str = "",
    candidate_status: str = "",
    recruitment_type: str = "",
    source: str = "",
    archived: str = "",
    scope: str = "applications",
    page: int = 1,
    page_size: int = 10,
) -> tuple[list[dict], int]:
    """后台按投递展开简历；同一份物理简历可对应多条岗位投递记录。"""
    page = max(1, int(page or 1))
    page_size = min(max(1, int(page_size or 10)), 100)
    where, params = _management_where(search, parse_status, experience_years, candidate_status, recruitment_type, source, archived)
    offset = (page - 1) * page_size
    join_sql = f"""
        FROM resumes r
        LEFT JOIN candidates c ON c.username=r.candidate_username
        {"JOIN applications a ON a.resume_id=r.id AND a.status NOT IN ('withdrawn', 'cancel')" if scope == "applications" else "LEFT JOIN applications a ON 1=0"}
    """
    select_sql = """
        SELECT r.*,
               a.id AS joined_application_id,
               a.jd_id AS application_jd_id,
               a.jd_name AS application_jd_name,
               a.recruitment_type AS application_recruitment_type,
               a.source AS application_source,
               a.status AS joined_application_status,
               a.current_stage AS application_current_stage,
               a.workflow_id AS application_workflow_id,
               (SELECT COUNT(*) FROM plans p WHERE p.application_id=a.id AND IFNULL(p.workflow_id, '') NOT LIKE 'apply_%') AS application_plan_count,
               a.screening_status AS application_screening_status,
               a.created_at AS application_created_at,
               (SELECT COUNT(*) FROM applications ax WHERE ax.resume_id=r.id AND IFNULL(ax.deleted_at, '')='') AS application_count,
               CASE WHEN c.resume_filename = r.file_path THEN 1 ELSE 0 END AS is_current_resume,
               c.avatar AS candidate_avatar
    
    """
    with _conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) {join_sql}{where}", params).fetchone()[0]
        rows = conn.execute(
            f"""
            {select_sql}
            {join_sql}
            {where}
            ORDER BY COALESCE(a.created_at, r.created_at) DESC, r.id DESC
            LIMIT ? OFFSET ?
            """,
            params + [page_size, offset],
        ).fetchall()
    return [_management_row(row) for row in rows], total


def find_duplicates(file_md5: str = "", exclude_id: int | None = None) -> list[dict]:
    if not file_md5:
        return []
    sql = "SELECT * FROM resumes WHERE file_md5=?"
    params: list = [file_md5]
    if exclude_id:
        sql += " AND id<>?"
        params.append(exclude_id)
    sql += " ORDER BY id DESC LIMIT 5"
    with _conn() as conn:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    return [_enrich_jd_fields(row) for row in rows]


def get_by_id(rid: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute(
            """SELECT r.*, c.avatar AS candidate_avatar
               FROM resumes r LEFT JOIN candidates c ON c.username=r.candidate_username
               WHERE r.id=?""",
            (rid,),
        ).fetchone()
        if not row:
            return None
        item = dict(row)
        item["avatar"] = item.pop("candidate_avatar", "") or item.get("avatar", "") or ""
        return _enrich_jd_fields(item)


def get_by_file_path(file_path: str) -> dict | None:
    if not file_path:
        return None
    with _conn() as conn:
        row = conn.execute("SELECT * FROM resumes WHERE file_path=? ORDER BY id DESC LIMIT 1", (file_path,)).fetchone()
        return _enrich_jd_fields(dict(row)) if row else None


def list_by_candidate_username(username: str) -> list[dict]:
    if not username:
        return []
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM resumes WHERE candidate_username=? ORDER BY id DESC",
            (username,),
        ).fetchall()
    return [_enrich_jd_fields(dict(row)) for row in rows]


def create(data: dict) -> dict:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO resumes (name, target_position, education, experience_years, skills, file_path, file_type, parse_status, candidate_status, jd_id, jd_name, original_name, file_md5, candidate_username, source) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (data.get("name", ""), data.get("target_position", ""), data.get("education", ""),
             data.get("experience_years", ""), data.get("skills", ""), data.get("file_path", ""),
             data.get("file_type", ""), data.get("parse_status", "wait"),
             normalize_candidate_status(data.get("candidate_status", "待筛选")),
             data.get("jd_id"), data.get("jd_name", ""), data.get("original_name", ""), data.get("file_md5", ""),
             data.get("candidate_username", ""), data.get("source", "admin")),
        )
        row = conn.execute("SELECT * FROM resumes WHERE id=?", (cur.lastrowid,)).fetchone()
        return dict(row) if row else None


def update(rid: int, data: dict) -> dict | None:
    existing = get_by_id(rid)
    if not existing:
        return None
    if "candidate_status" in data:
        data["candidate_status"] = normalize_candidate_status(data.get("candidate_status"))
    allowed = ["name", "target_position", "education", "experience_years", "skills", "file_path", "file_type", "parse_status", "parse_error", "parsed_at", "candidate_status", "structured_data", "jd_id", "jd_name", "original_name", "file_md5", "candidate_username", "source"]
    sets = [f"{f}=?" for f in allowed if f in data]
    vals = [data[f] for f in allowed if f in data]
    if not sets:
        return existing
    vals.append(rid)
    for attempt in range(3):
        try:
            with _conn() as conn:
                conn.execute(f"UPDATE resumes SET {', '.join(sets)} WHERE id=?", vals)
            break
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt == 2:
                raise
            time.sleep(0.12 * (attempt + 1))
    return get_by_id(rid)


def sync_jd_name(jd_id: int, jd_name: str) -> None:
    if not jd_id:
        return
    with _conn() as conn:
        conn.execute(
            "UPDATE resumes SET jd_name=? WHERE jd_id=?",
            (jd_name or "", jd_id),
        )


def delete(rid: int) -> bool:
    with _conn() as conn:
        return conn.execute("UPDATE resumes SET deleted_at=datetime('now') WHERE id=? AND IFNULL(deleted_at, '')=''", (rid,)).rowcount > 0

def restore(rid: int) -> bool:
    with _conn() as conn:
        return conn.execute("UPDATE resumes SET deleted_at=NULL WHERE id=? AND IFNULL(deleted_at, '')<>''", (rid,)).rowcount > 0


def _enrich_jd_fields(resume: dict) -> dict:
    if not resume:
        return resume

    jd_id = resume.get("jd_id")
    if jd_id:
        from backend.repositories import jd_repo
        jd = jd_repo.get_by_id(int(jd_id))
        if jd:
            resume["jd_name"] = jd.get("name", "")
    return resume


def normalize_candidate_status(value: str | None) -> str:
    text = str(value or "").strip()
    if text in ("已进入面试", "已录用"):
        return "初筛通过"
    if text == "已淘汰":
        return "不合适"
    return text if text in RESUME_STATUS_OPTIONS else "待筛选"
