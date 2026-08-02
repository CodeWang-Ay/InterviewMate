import sqlite3
import time

from backend.config import DB_PATH


APPLICATION_SOURCES = {"candidate", "admin", "import"}
APPLICATION_LIMIT_PER_SIX_MONTHS = 3
RECRUITMENT_TYPES = ("社招", "校招", "实习生")
SCREENING_STATUSES = {"待筛选", "初筛通过", "不合适"}
OFFER_STATUSES = {"", "pending", "offered", "accepted", "declined", "rejected"}
APPLICATION_STATUSES = {"active", "rejected", "withdrawn", "hired", "closed"}
APPLICATION_STAGES = {"screening", "interview", "offer", "completed"}


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


def init_db() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_username TEXT DEFAULT '',
                candidate_name TEXT DEFAULT '',
                jd_id INTEGER DEFAULT NULL,
                jd_name TEXT DEFAULT '',
                resume_id INTEGER DEFAULT NULL,
                match_score INTEGER DEFAULT 0,
                match_details TEXT DEFAULT '{}',
                recruitment_type TEXT DEFAULT '社招',
                source TEXT DEFAULT 'candidate',
                status TEXT DEFAULT 'active',
                current_stage TEXT DEFAULT 'screening',
                screening_status TEXT DEFAULT '待筛选',
                workflow_id TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_candidate ON applications(candidate_username)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_resume ON applications(resume_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_applications_workflow ON applications(workflow_id)")
        cols = {row[1] for row in conn.execute("PRAGMA table_info(applications)").fetchall()}
        if "match_score" not in cols:
            conn.execute("ALTER TABLE applications ADD COLUMN match_score INTEGER DEFAULT 0")
        if "match_details" not in cols:
            conn.execute("ALTER TABLE applications ADD COLUMN match_details TEXT DEFAULT '{}'")
        if "recruitment_type" not in cols:
            conn.execute("ALTER TABLE applications ADD COLUMN recruitment_type TEXT DEFAULT '社招'")
        if "screening_status" not in cols:
            conn.execute("ALTER TABLE applications ADD COLUMN screening_status TEXT DEFAULT '待筛选'")
            conn.execute("""
                UPDATE applications
                SET screening_status=COALESCE(
                    (SELECT candidate_status FROM resumes WHERE resumes.id=applications.resume_id),
                    '待筛选'
                )
            """)
        if "offer_status" not in cols:
            conn.execute("ALTER TABLE applications ADD COLUMN offer_status TEXT DEFAULT ''")
        if "offer_updated_at" not in cols:
            conn.execute("ALTER TABLE applications ADD COLUMN offer_updated_at TEXT DEFAULT ''")
        if "current_stage" not in cols:
            conn.execute("ALTER TABLE applications ADD COLUMN current_stage TEXT DEFAULT 'screening'")
        if "deleted_at" not in cols:
            conn.execute("ALTER TABLE applications ADD COLUMN deleted_at TEXT DEFAULT NULL")
        if "deleted_by" not in cols:
            conn.execute("ALTER TABLE applications ADD COLUMN deleted_by TEXT DEFAULT ''")
        if "delete_reason" not in cols:
            conn.execute("ALTER TABLE applications ADD COLUMN delete_reason TEXT DEFAULT ''")
        conn.execute("""
            UPDATE applications
            SET status=CASE status
                WHEN 'pending' THEN 'active'
                WHEN 'reject' THEN 'rejected'
                WHEN 'cancel' THEN 'withdrawn'
                ELSE status
            END
        """)
        conn.execute("""
            UPDATE applications
            SET current_stage=CASE
                WHEN status IN ('rejected', 'withdrawn', 'hired', 'closed') THEN 'completed'
                WHEN offer_status IN ('pending', 'offered') THEN 'offer'
                WHEN offer_status='accepted' THEN 'completed'
                WHEN IFNULL(workflow_id, '') LIKE 'apply_%' THEN 'screening'
                WHEN screening_status='初筛通过' AND IFNULL(workflow_id, '')<>'' THEN 'interview'
                ELSE 'screening'
            END
        """)
        _backfill_existing_plans(conn)


def _backfill_existing_plans(conn) -> None:
    tables = {
        row[0]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    plan_cols = {row[1] for row in conn.execute("PRAGMA table_info(plans)").fetchall()}
    if not {"application_id", "resume_id", "workflow_id"}.issubset(plan_cols):
        return

    resume_cols = {row[1] for row in conn.execute("PRAGMA table_info(resumes)").fetchall()}
    has_owner = "candidate_username" in resume_cols
    owner_sql = ", candidate_username" if has_owner else ""
    resumes = conn.execute(f"SELECT id, file_path, jd_id{owner_sql} FROM resumes WHERE IFNULL(file_path, '')<>''").fetchall()
    resume_by_file = {row["file_path"]: dict(row) for row in resumes}
    jd_by_name = {}
    if "jds" in tables:
        jd_by_name = {
            row["name"]: row["id"]
            for row in conn.execute("SELECT id, name FROM jds WHERE IFNULL(name, '')<>''").fetchall()
        }

    if has_owner and "candidates" in tables:
        current_resumes = conn.execute(
            "SELECT username, resume_filename FROM candidates WHERE IFNULL(resume_filename, '')<>''"
        ).fetchall()
        for candidate in current_resumes:
            resume = resume_by_file.get(candidate["resume_filename"])
            if resume:
                conn.execute(
                    "UPDATE resumes SET candidate_username=?, source='candidate' WHERE id=?",
                    (candidate["username"], resume["id"]),
                )

    groups = conn.execute("""
        SELECT
            workflow_id,
            MIN(id) AS seed_id,
            MAX(application_id) AS seed_application_id,
            MAX(candidate_username) AS candidate_username,
            MAX(candidate_name) AS candidate_name,
            MAX(jd_name) AS jd_name,
            MAX(resume_filename) AS resume_filename
        FROM plans
        WHERE IFNULL(workflow_id, '')<>''
        GROUP BY workflow_id
    """).fetchall()
    for group in groups:
        existing = conn.execute("SELECT id FROM applications WHERE workflow_id=?", (group["workflow_id"],)).fetchone()
        if not existing and group["seed_application_id"]:
            owner = conn.execute(
                "SELECT id, workflow_id FROM applications WHERE id=?",
                (group["seed_application_id"],),
            ).fetchone()
            if owner and str(group["workflow_id"]).startswith("apply_") and not str(owner["workflow_id"] or "").startswith("apply_"):
                # 该投递已经升级为正式流程，旧 apply_* 只是历史占位，不能反向创建第二条 application。
                continue
            if owner:
                existing = owner
        resume = resume_by_file.get(group["resume_filename"] or "")
        resume_id = resume["id"] if resume else None
        jd_id = (resume or {}).get("jd_id") or jd_by_name.get(group["jd_name"] or "")
        if not jd_id and str(group["workflow_id"]).startswith("apply_"):
            try:
                jd_id = int(str(group["workflow_id"]).split("_", 2)[1])
            except (IndexError, TypeError, ValueError):
                jd_id = None
        source = "candidate" if str(group["workflow_id"]).startswith("apply_") else "admin"
        if existing:
            application_id = existing["id"]
            recruitment_sql = (
                "COALESCE((SELECT recruitment_type FROM jds "
                "WHERE id=COALESCE(applications.jd_id, ?)), recruitment_type)"
                if "jds" in tables else "recruitment_type"
            )
            recruitment_params = [jd_id] if "jds" in tables else []
            conn.execute(
                f"""
                UPDATE applications
                SET candidate_username=?, candidate_name=?, jd_id=COALESCE(jd_id, ?),
                    jd_name=?, resume_id=COALESCE(resume_id, ?),
                    source=CASE WHEN applications.source='candidate' THEN 'candidate' ELSE ? END,
                    recruitment_type={recruitment_sql},
                    updated_at=datetime('now')
                WHERE id=?
                """,
                tuple([
                    group["candidate_username"] or "",
                    group["candidate_name"] or "",
                    jd_id,
                    group["jd_name"] or "",
                    resume_id,
                    source,
                    *recruitment_params,
                    application_id,
                ]),
            )
        else:
            cur = conn.execute(
                """
                INSERT INTO applications (
                    candidate_username, candidate_name, jd_id, jd_name, resume_id, source, workflow_id,
                    status, current_stage, screening_status
                ) VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    group["candidate_username"] or "",
                    group["candidate_name"] or "",
                    jd_id,
                    group["jd_name"] or "",
                    resume_id,
                    source,
                    group["workflow_id"],
                    "active",
                    "screening" if str(group["workflow_id"]).startswith("apply_") else "interview",
                    "待筛选" if str(group["workflow_id"]).startswith("apply_") else "初筛通过",
                ),
            )
            application_id = cur.lastrowid
        conn.execute(
            "UPDATE plans SET application_id=?, resume_id=COALESCE(resume_id, ?) WHERE workflow_id=?",
            (application_id, resume_id, group["workflow_id"]),
        )
        if resume and has_owner and not (resume["candidate_username"] or "") and group["candidate_username"]:
            conn.execute(
                "UPDATE resumes SET candidate_username=?, source=? WHERE id=?",
                (group["candidate_username"], source, resume_id),
            )


def create(data: dict) -> dict:
    source = str(data.get("source") or "candidate").strip()
    if source not in APPLICATION_SOURCES:
        source = "candidate"
    with _conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO applications (
                candidate_username, candidate_name, jd_id, jd_name, resume_id,
                match_score, match_details, recruitment_type, source, status, workflow_id
                , screening_status, current_stage
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                data.get("candidate_username", ""),
                data.get("candidate_name", ""),
                data.get("jd_id"),
                data.get("jd_name", ""),
                data.get("resume_id"),
                data.get("match_score", 0),
                data.get("match_details", "{}"),
                normalize_recruitment_type(data.get("recruitment_type")),
                source,
                normalize_application_status(data.get("status")),
                data.get("workflow_id", ""),
                normalize_screening_status(data.get("screening_status")),
                normalize_application_stage(data.get("current_stage")),
            ),
        )
        row = conn.execute("SELECT * FROM applications WHERE id=?", (cur.lastrowid,)).fetchone()
    return dict(row) if row else {}


def create_candidate_once(data: dict) -> tuple[dict, bool]:
    """原子地创建候选人岗位投递，防止双击或网络重试产生重复记录。"""
    username = str(data.get("candidate_username") or "").strip()
    jd_id = data.get("jd_id")
    if not username or not jd_id:
        return create(data), True
    source = str(data.get("source") or "candidate").strip()
    if source not in APPLICATION_SOURCES:
        source = "candidate"
    with _conn() as conn:
        conn.execute("BEGIN IMMEDIATE")
        existing = conn.execute(
            """
            SELECT * FROM applications
            WHERE candidate_username=? AND jd_id=?
              AND status NOT IN ('withdrawn', 'cancel')
            ORDER BY id DESC LIMIT 1
            """,
            (username, jd_id),
        ).fetchone()
        if existing:
            return dict(existing), False
        cur = conn.execute(
            """
            INSERT INTO applications (
                candidate_username, candidate_name, jd_id, jd_name, resume_id,
                match_score, match_details, recruitment_type, source, status, workflow_id,
                screening_status, current_stage
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                username,
                data.get("candidate_name", ""),
                jd_id,
                data.get("jd_name", ""),
                data.get("resume_id"),
                data.get("match_score", 0),
                data.get("match_details", "{}"),
                normalize_recruitment_type(data.get("recruitment_type")),
                source,
                normalize_application_status(data.get("status")),
                data.get("workflow_id", ""),
                normalize_screening_status(data.get("screening_status")),
                normalize_application_stage(data.get("current_stage")),
            ),
        )
        row = conn.execute("SELECT * FROM applications WHERE id=?", (cur.lastrowid,)).fetchone()
    return (dict(row) if row else {}), True


def update_match(application_id: int, match_score: int, match_details: str) -> dict | None:
    for attempt in range(3):
        try:
            with _conn() as conn:
                conn.execute(
                    """
                    UPDATE applications
                    SET match_score=?, match_details=?, updated_at=datetime('now')
                    WHERE id=?
                    """,
                    (min(max(int(match_score or 0), 0), 100), match_details or "{}", application_id),
                )
                row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
            return dict(row) if row else None
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt == 2:
                raise
            time.sleep(0.12 * (attempt + 1))
    return None


def update_lifecycle(application_id: int, status: str, current_stage: str) -> dict | None:
    normalized_status = normalize_application_status(status)
    normalized_stage = normalize_application_stage(current_stage)
    with _conn() as conn:
        conn.execute(
            """
            UPDATE applications
            SET status=?, current_stage=?, updated_at=datetime('now')
            WHERE id=?
            """,
            (normalized_status, normalized_stage, application_id),
        )
        row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    return dict(row) if row else None


def cancel(application_id: int) -> dict | None:
    with _conn() as conn:
        conn.execute(
            """
            UPDATE applications
            SET status='withdrawn', current_stage='completed', updated_at=datetime('now')
            WHERE id=? AND status<>'withdrawn'
            """,
            (application_id,),
        )
        row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    return dict(row) if row else None


def update_screening(application_id: int, screening_status: str) -> dict | None:
    normalized = normalize_screening_status(screening_status)
    application_status = "rejected" if normalized == "不合适" else "active"
    current_stage = "completed" if normalized == "不合适" else "screening"
    for attempt in range(3):
        try:
            with _conn() as conn:
                conn.execute(
                    """
                    UPDATE applications
                    SET screening_status=?, status=?, current_stage=?, updated_at=datetime('now')
                    WHERE id=?
                    """,
                    (normalized, application_status, current_stage, application_id),
                )
                if normalized == "不合适":
                    conn.execute(
                        """
                        UPDATE plans
                        SET status='cancel', active_session_id=''
                        WHERE application_id=? AND status<>'finish'
                        """,
                        (application_id,),
                    )
                row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
            return dict(row) if row else None
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc).lower() or attempt == 2:
                raise
            time.sleep(0.12 * (attempt + 1))
    return None


def update_offer(application_id: int, offer_status: str) -> dict | None:
    normalized = str(offer_status or "").strip().lower()
    if normalized not in OFFER_STATUSES:
        raise ValueError("不支持的 Offer 状态")
    application_status, current_stage = {
        "accepted": ("hired", "completed"),
        "declined": ("rejected", "completed"),
        "rejected": ("rejected", "completed"),
    }.get(normalized, ("active", "offer"))
    with _conn() as conn:
        conn.execute(
            """
            UPDATE applications
            SET offer_status=?, status=?, current_stage=?,
                offer_updated_at=datetime('now'), updated_at=datetime('now')
            WHERE id=?
            """,
            (normalized, application_status, current_stage, application_id),
        )
        row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    return dict(row) if row else None


def attach_workflow(application_id: int, workflow_id: str) -> dict | None:
    with _conn() as conn:
        conn.execute(
            """
            UPDATE applications
            SET workflow_id=?, screening_status='初筛通过', status='active',
                current_stage='interview',
                updated_at=datetime('now')
            WHERE id=?
            """,
            (workflow_id, application_id),
        )
        row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    return dict(row) if row else None


def get_by_id(application_id: int) -> dict | None:
    with _conn() as conn:
        row = conn.execute("SELECT * FROM applications WHERE id=?", (application_id,)).fetchone()
    return dict(row) if row else None


def list_by_candidate_username(candidate_username: str) -> list[dict]:
    if not candidate_username:
        return []
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM applications WHERE candidate_username=? AND IFNULL(deleted_at, '')='' ORDER BY id DESC",
            (candidate_username,),
        ).fetchall()
    return [_with_status_label(dict(row)) for row in rows]


def find_by_candidate_and_jd(candidate_username: str, jd_id: int) -> dict | None:
    if not candidate_username or not jd_id:
        return None
    with _conn() as conn:
        row = conn.execute(
            """
            SELECT * FROM applications
            WHERE candidate_username=? AND jd_id=? AND status NOT IN ('withdrawn', 'cancel')
            ORDER BY id DESC LIMIT 1
            """,
            (candidate_username, jd_id),
        ).fetchone()
    return dict(row) if row else None


def get_candidate_quota(candidate_username: str) -> dict:
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT id, jd_id, jd_name, recruitment_type, status, created_at
            FROM applications
            WHERE candidate_username=? AND source='candidate'
              AND status NOT IN ('withdrawn', 'cancel')
              AND datetime(created_at) >= datetime('now', '-6 months')
            ORDER BY datetime(created_at) ASC, id ASC
            """,
            (candidate_username,),
        ).fetchall()
        buckets = {}
        for recruitment_type in RECRUITMENT_TYPES:
            type_rows = [
                row for row in rows
                if normalize_recruitment_type(row["recruitment_type"]) == recruitment_type
            ]
            available_at = ""
            if len(type_rows) >= APPLICATION_LIMIT_PER_SIX_MONTHS:
                value = conn.execute(
                    "SELECT datetime(?, '+6 months') AS available_at",
                    (type_rows[0]["created_at"],),
                ).fetchone()
                available_at = value["available_at"] if value else ""
            buckets[recruitment_type] = {
                "limit": APPLICATION_LIMIT_PER_SIX_MONTHS,
                "used": len(type_rows),
                "remaining": max(0, APPLICATION_LIMIT_PER_SIX_MONTHS - len(type_rows)),
                "available_at": available_at,
            }
    return {
        "limit_per_type": APPLICATION_LIMIT_PER_SIX_MONTHS,
        "window_months": 6,
        "buckets": buckets,
        "applications": [dict(row) for row in rows],
    }


def normalize_recruitment_type(value: str | None) -> str:
    text = str(value or "").strip()
    if "实习" in text:
        return "实习生"
    if "校" in text:
        return "校招"
    return "社招"


def normalize_screening_status(value: str | None) -> str:
    text = str(value or "").strip()
    return text if text in SCREENING_STATUSES else "待筛选"


def normalize_application_status(value: str | None) -> str:
    text = str(value or "").strip().lower()
    legacy = {"pending": "active", "reject": "rejected", "cancel": "withdrawn"}
    text = legacy.get(text, text)
    return text if text in APPLICATION_STATUSES else "active"


def normalize_application_stage(value: str | None) -> str:
    text = str(value or "").strip().lower()
    return text if text in APPLICATION_STAGES else "screening"


def list_by_resume_id(resume_id: int) -> list[dict]:
    if not resume_id:
        return []
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM applications WHERE resume_id=? AND IFNULL(deleted_at, '')='' ORDER BY id DESC",
            (resume_id,),
        ).fetchall()
    return [_with_status_label(dict(row)) for row in rows]


def _with_status_label(item: dict) -> dict:
    status = item.get("status")
    screening = item.get("screening_status")
    stage = item.get("current_stage")
    if status == "withdrawn": label = "已取消"
    elif status == "rejected" and screening == "不合适": label = "初筛不通过"
    elif status == "rejected": label = "面试不通过"
    elif status == "hired": label = "已录用"
    elif item.get("offer_status") in {"pending", "offered"}: label = "Offer 待处理"
    elif stage == "interview": label = "面试中"
    elif screening == "初筛通过": label = "初筛通过"
    else: label = "待初筛"
    item["status_label"] = label
    return item
