import os
import sqlite3
import hashlib

from backend.config import DB_PATH, UPLOAD_DIR

RESUME_STATUS_OPTIONS = ["待筛选", "初筛通过", "不合适"]


def _conn():
    c = sqlite3.connect(DB_PATH)
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


def _build_where(search: str = "", parse_status: str = "", experience_years: str = "", candidate_status: str = "") -> tuple[str, list]:
    sql = " WHERE 1=1"
    params = []
    if candidate_status:
        sql += " AND candidate_status=?"
        params.append(candidate_status)
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


def list_all(search: str = "", parse_status: str = "", experience_years: str = "", candidate_status: str = "") -> list[dict]:
    where, params = _build_where(search, parse_status, experience_years, candidate_status)
    sql = f"SELECT * FROM resumes{where} ORDER BY id DESC"
    with _conn() as conn:
        rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    return [_enrich_jd_fields(row) for row in rows]


def list_paged(search: str = "", parse_status: str = "", experience_years: str = "", candidate_status: str = "", page: int = 1, page_size: int = 10) -> tuple[list[dict], int]:
    page = max(1, int(page or 1))
    page_size = min(max(1, int(page_size or 10)), 100)
    where, params = _build_where(search, parse_status, experience_years, candidate_status)
    offset = (page - 1) * page_size
    with _conn() as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM resumes{where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM resumes{where} ORDER BY id DESC LIMIT ? OFFSET ?",
            params + [page_size, offset],
        ).fetchall()
    return [_enrich_jd_fields(dict(row)) for row in rows], total


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
        row = conn.execute("SELECT * FROM resumes WHERE id=?", (rid,)).fetchone()
        return _enrich_jd_fields(dict(row)) if row else None


def get_by_file_path(file_path: str) -> dict | None:
    if not file_path:
        return None
    with _conn() as conn:
        row = conn.execute("SELECT * FROM resumes WHERE file_path=? ORDER BY id DESC LIMIT 1", (file_path,)).fetchone()
        return _enrich_jd_fields(dict(row)) if row else None


def create(data: dict) -> dict:
    with _conn() as conn:
        cur = conn.execute(
            "INSERT INTO resumes (name, target_position, education, experience_years, skills, file_path, file_type, parse_status, candidate_status, jd_id, jd_name, original_name, file_md5) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (data.get("name", ""), data.get("target_position", ""), data.get("education", ""),
             data.get("experience_years", ""), data.get("skills", ""), data.get("file_path", ""),
             data.get("file_type", ""), data.get("parse_status", "wait"),
             normalize_candidate_status(data.get("candidate_status", "待筛选")),
             data.get("jd_id"), data.get("jd_name", ""), data.get("original_name", ""), data.get("file_md5", "")),
        )
        return get_by_id(cur.lastrowid)


def update(rid: int, data: dict) -> dict | None:
    existing = get_by_id(rid)
    if not existing:
        return None
    if "candidate_status" in data:
        data["candidate_status"] = normalize_candidate_status(data.get("candidate_status"))
    allowed = ["name", "target_position", "education", "experience_years", "skills", "file_path", "file_type", "parse_status", "candidate_status", "structured_data", "jd_id", "jd_name", "original_name", "file_md5"]
    sets = [f"{f}=?" for f in allowed if f in data]
    vals = [data[f] for f in allowed if f in data]
    if not sets:
        return existing
    vals.append(rid)
    with _conn() as conn:
        conn.execute(f"UPDATE resumes SET {', '.join(sets)} WHERE id=?", vals)
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
        return conn.execute("DELETE FROM resumes WHERE id=?", (rid,)).rowcount > 0


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
